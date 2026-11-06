"""GSX — GenExpr Source eXecutor.

Executes the *actual* .genexpr text (not a hand port) by parsing it and
transpiling it to a numba-compiled Python function. This is an independent
implementation of the GenExpr subset this project uses; it is NOT Cycling '74's
gen~ compiler and its results are never evidence of gen~ or Live behaviour.
Its purpose is to catch discrepancies between the hand-written reference model
and the code that actually ships.

Semantics implemented (documented gen~ behaviour, see docs/TEST_METHODOLOGY.md):
  * functions are inlined at each call site; a History declared in a function
    gets separate state per call site
  * Param values are clamped to their min/max
  * comparisons and logic return 1.0 / 0.0; both branches of ?: are evaluated
  * noise() -> uniform [-1, 1)  (sequence differs from gen~'s generator)
  * fixdenorm() flushes |x| < 1.17549435e-38 (single-precision denormal limit,
    the stricter of the two possibilities); fixnan() maps NaN/Inf to 0

Usage:
    prog = compile_genexpr(open("x.genexpr").read())
    out1, out2 = prog.run(in1, in2, sr, {"knob": 3, "reso": 2.0}, seed=1)
    # any param may be a scalar or a per-sample numpy array; sr may be an array
"""
import math
import re
import numpy as np
import numba

# ----------------------------------------------------------------- tokenizer
TOK = re.compile(r"""
    (?P<ws>\s+)|(?P<lc>//[^\n]*)|(?P<bc>/\*.*?\*/)|
    (?P<num>(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?)|
    (?P<id>[A-Za-z_]\w*)|
    (?P<op>==|!=|<=|>=|&&|\|\||\+=|-=|\*=|/=|[-+*/%<>=!?:,;(){}])
""", re.S | re.X)


def tokenize(src):
    out, pos = [], 0
    while pos < len(src):
        m = TOK.match(src, pos)
        if not m:
            raise SyntaxError(f"bad char {src[pos]!r} at {src[:pos].count(chr(10)) + 1}")
        pos = m.end()
        k = m.lastgroup
        if k in ("ws", "lc", "bc"):
            continue
        out.append((k, m.group(k), src[:m.start()].count("\n") + 1))
    out.append(("eof", "", 0))
    return out


# ----------------------------------------------------------------- parser
class P:
    def __init__(self, toks, check_order=True):
        self.t, self.i = toks, 0
        self.check_order = check_order

    def peek(self, o=0):
        return self.t[self.i + o]

    def next(self):
        tok = self.t[self.i]; self.i += 1; return tok

    def accept(self, v):
        if self.peek()[1] == v and self.peek()[0] != "eof":
            self.i += 1; return True
        return False

    def expect(self, v):
        tok = self.next()
        if tok[1] != v:
            raise SyntaxError(f"line {tok[2]}: expected {v!r}, got {tok[1]!r}")
        return tok

    # program := (decl | funcdef | stmt)*
    def program(self):
        params, funcs, body = [], {}, []
        seen_stmt = None   # gen~: "function definitions must precede all statements" (incl. Param)
        while self.peek()[0] != "eof":
            k, v, ln = self.peek()
            if v == "Param":
                seen_stmt = seen_stmt or ln
                params.append(self.param())
            elif k == "id" and v not in ("if", "for", "while") and self.peek(1)[1] == "(" and self._is_funcdef():
                if seen_stmt and self.check_order:
                    raise SyntaxError(f"line {ln}: function definitions not allowed here (function definitions "
                                      f"must precede all statements; first statement at line {seen_stmt})")
                name, args, stmts = self.funcdef()
                funcs[name] = (args, stmts)
            else:
                seen_stmt = seen_stmt or ln
                body.append(self.stmt())
        return params, funcs, body

    def _is_funcdef(self):
        j, depth = self.i + 1, 0
        while True:
            v = self.t[j][1]
            if v == "(":
                depth += 1
            elif v == ")":
                depth -= 1
                if depth == 0:
                    return self.t[j + 1][1] == "{"
            j += 1

    def param(self):
        self.expect("Param")
        name = self.next()[1]
        self.expect("(")
        default = self.expr()
        kw = {}
        while self.accept(","):
            key = self.next()[1]; self.expect("="); kw[key] = self.expr()
        self.expect(")"); self.expect(";")
        return name, default, kw

    def funcdef(self):
        name = self.next()[1]; self.expect("(")
        args = []
        if not self.accept(")"):
            while True:
                args.append(self.next()[1])
                if self.accept(")"):
                    break
                self.expect(",")
        return name, args, self.block()

    def block(self):
        self.expect("{")
        out = []
        while not self.accept("}"):
            out.append(self.stmt())
        return out

    def stmt(self):
        k, v, ln = self.peek()
        if v == "History":
            self.next()
            decls = []
            while True:
                name = self.next()[1]; self.expect("(")
                init = self.expr(); self.expect(")")
                decls.append((name, init))
                if self.accept(";"):
                    break
                self.expect(",")
            return ("history", decls)
        if v == "if":
            self.next(); self.expect("("); c = self.expr(); self.expect(")")
            a = self.block() if self.peek()[1] == "{" else [self.stmt()]
            b = []
            if self.accept("else"):
                b = self.block() if self.peek()[1] == "{" else [self.stmt()]
            return ("if", c, a, b)
        if v == "for":
            self.next(); self.expect("(")
            init = self.simple(); self.expect(";")
            cond = self.expr(); self.expect(";")
            inc = self.simple(); self.expect(")")
            return ("for", init, cond, inc, self.block())
        if v == "return":
            self.next()
            vals = [self.expr()]
            while self.accept(","):
                vals.append(self.expr())
            self.expect(";")
            return ("return", vals)
        s = self.simple(); self.expect(";")
        return s

    def simple(self):
        # targets (a, b, c) = expr   |  a op= expr  |  expr
        save = self.i
        names = []
        while self.peek()[0] == "id":
            names.append(self.next()[1])
            if not self.accept(","):
                break
        op = self.peek()[1]
        if names and op in ("=", "+=", "-=", "*=", "/="):
            self.next()
            rhs = self.expr()
            if op != "=":
                rhs = ("bin", op[0], ("var", names[0]), rhs)
            return ("assign", names, rhs)
        self.i = save
        return ("expr", self.expr())

    # precedence climbing
    def expr(self):
        c = self.lor()
        if self.accept("?"):
            a = self.expr(); self.expect(":"); b = self.expr()
            return ("tern", c, a, b)
        return c

    def _left(self, sub, ops):
        a = sub()
        while self.peek()[1] in ops and self.peek()[0] == "op":
            op = self.next()[1]
            a = ("bin", op, a, sub())
        return a

    def lor(self): return self._left(self.land, ("||",))
    def land(self): return self._left(self.eq, ("&&",))
    def eq(self): return self._left(self.rel, ("==", "!="))
    def rel(self): return self._left(self.add, ("<", ">", "<=", ">="))
    def add(self): return self._left(self.mul, ("+", "-"))
    def mul(self): return self._left(self.unary, ("*", "/", "%"))

    def unary(self):
        if self.accept("-"):
            return ("neg", self.unary())
        if self.accept("!"):
            return ("not", self.unary())
        if self.accept("+"):
            return self.unary()
        return self.primary()

    def primary(self):
        k, v, ln = self.next()
        if k == "num":
            return ("num", float(v))
        if v == "(":
            e = self.expr(); self.expect(")"); return e
        if k == "id":
            if self.accept("("):
                args = []
                if not self.accept(")"):
                    while True:
                        args.append(self.expr())
                        if self.accept(")"):
                            break
                        self.expect(",")
                return ("call", v, args)
            return ("var", v)
        raise SyntaxError(f"line {ln}: unexpected {v!r}")


class SemanticsError(Exception):
    pass


# ----------------------------------------------------------------- codegen
CONST = {"pi": "math.pi", "twopi": "(2.0*math.pi)", "halfpi": "(0.5*math.pi)",
         "e": "math.e", "samplerate": "SR"}
BUILTIN = {  # name -> (min args, max args, template using a0..an)
    "tanh": "math.tanh({0})", "exp": "math.exp({0})", "log": "math.log({0})",
    "tan": "math.tan({0})", "sin": "math.sin({0})", "cos": "math.cos({0})",
    "sqrt": "_sqrt({0})", "abs": "abs({0})", "floor": "math.floor({0})",
    "pow": "_pow({0},{1})", "min": "min({0},{1})", "max": "max({0},{1})",
    "clamp": "min(max({0},{1}),{2})", "mix": "({0}+({1}-{0})*{2})",
    "dbtoa": "(10.0**(({0})/20.0))", "atodb": "(20.0*math.log10(max(abs({0}),1e-300)))",
    "fixdenorm": "_fixdenorm({0})", "fixnan": "_fixnan({0})", "sign": "_sign({0})",
    "noise": "(np.random.random()*2.0-1.0)",
}


class Gen:
    def __init__(self, params, funcs):
        self.params = {p[0]: p for p in params}
        self.funcs = funcs
        self.lines = []          # per-sample body
        self.init = []           # state init before loop
        self.n = 0
        self.locals = set()
        self.written = set()     # History vars already written this frame

    def tmp(self):
        self.n += 1
        nm = f"t{self.n}"
        self.locals.add(nm)
        return nm

    def emit(self, s, ind):
        self.lines.append("    " * ind + s)

    def const_expr(self, e):
        # evaluate initialiser / literal expressions
        if e[0] == "num":
            return e[1]
        if e[0] == "neg":
            return -self.const_expr(e[1])
        if e[0] == "bin":
            a, b = self.const_expr(e[2]), self.const_expr(e[3])
            return {"+": a + b, "-": a - b, "*": a * b, "/": a / b}[e[1]]
        raise SyntaxError(f"non-constant initialiser {e}")

    # expression -> python source string (emits hoisted call code)
    def ex(self, e, env, ind):
        k = e[0]
        if k == "num":
            return repr(e[1])
        if k == "var":
            v = e[1]
            if v in env:
                pv = env[v]
                if pv.startswith("H_") and pv in self.written:
                    raise SemanticsError(
                        f"History '{v}' is read after being written in the same frame; "
                        "gen~ semantics for this are not relied upon (portability lint)")
                return pv
            if v in CONST:
                return CONST[v]
            if v in ("in1", "in2"):
                return f"IN{v[2]}[i]"
            if v in self.params:
                return f"P_{v}"
            raise NameError(f"undefined variable {v}")
        if k == "neg":
            return f"(-{self.ex(e[1], env, ind)})"
        if k == "not":
            return f"(1.0 if {self.ex(e[1], env, ind)} == 0.0 else 0.0)"
        if k == "bin":
            a, b = self.ex(e[2], env, ind), self.ex(e[3], env, ind)
            op = e[1]
            if op in ("<", ">", "<=", ">=", "==", "!="):
                return f"(1.0 if {a} {op} {b} else 0.0)"
            if op == "&&":
                return f"(1.0 if ({a} != 0.0 and {b} != 0.0) else 0.0)"
            if op == "||":
                return f"(1.0 if ({a} != 0.0 or {b} != 0.0) else 0.0)"
            if op == "%":
                return f"_fmod({a},{b})"
            if op == "/":
                return f"_div({a},{b})"
            return f"({a} {op} {b})"
        if k == "tern":
            c = self.ex(e[1], env, ind)
            a, b = self.ex(e[2], env, ind), self.ex(e[3], env, ind)
            return f"({a} if {c} != 0.0 else {b})"
        if k == "call":
            vals = self.call(e, env, ind)
            return vals[0]
        raise SyntaxError(k)

    def call(self, e, env, ind):
        name, args = e[1], e[2]
        if name == "selector":
            idx = self.ex(args[0], env, ind)
            opts = [self.ex(a, env, ind) for a in args[1:]]
            t = self.tmp()
            self.emit(f"_k = int({idx})", ind)
            self.emit(f"{t} = 0.0", ind)
            for j, o in enumerate(opts):
                self.emit(f"if _k == {j + 1}: {t} = {o}", ind)
            return [t]
        if name in BUILTIN:
            a = [self.ex(x, env, ind) for x in args]
            return [BUILTIN[name].format(*a)]
        if name not in self.funcs:
            raise NameError(f"unknown function {name}")
        fargs, body = self.funcs[name]
        if len(fargs) != len(args):
            raise TypeError(f"{name}: expected {len(fargs)} args")
        self.n += 1
        pre = f"f{self.n}_{name}_"
        fenv = {}
        for a, x in zip(fargs, args):
            v = self.ex(x, env, ind)
            self.locals.add(pre + a)
            self.emit(f"{pre}{a} = {v}", ind)
            fenv[a] = pre + a
        ret = []
        self.block(body, fenv, ind, pre, ret)
        if not ret:
            raise SyntaxError(f"{name} has no return")
        return ret[0]

    def block(self, stmts, env, ind, pre, ret):
        for s in stmts:
            k = s[0]
            if k == "history":
                for nm, init in s[1]:
                    sv = f"H_{pre}{nm}"
                    self.init.append(f"{sv} = {self.const_expr(init)!r}")
                    env[nm] = sv
            elif k == "assign":
                names, rhs = s[1], s[2]
                if len(names) == 1:
                    vals = [self.ex(rhs, env, ind)]
                else:
                    if rhs[0] != "call" or rhs[1] in BUILTIN:
                        raise SyntaxError("multi-assign needs a user function")
                    vals = self.call(rhs, env, ind)
                for j, nm in enumerate(names):
                    v = vals[j] if j < len(vals) else "0.0"
                    if nm in ("out1", "out2"):
                        self.emit(f"OUT{nm[3]}[i] = {v}", ind)
                        continue
                    if nm not in env:
                        env[nm] = f"{pre}v_{nm}" if pre else f"v_{nm}"
                        self.locals.add(env[nm])
                    self.emit(f"{env[nm]} = {v}", ind)
                    if env[nm].startswith("H_"):
                        self.written.add(env[nm])
            elif k == "expr":
                self.ex(s[1], env, ind)
            elif k == "return":
                ts = []
                for v in s[1]:
                    t = self.tmp()
                    self.emit(f"{t} = {self.ex(v, env, ind)}", ind)
                    ts.append(t)
                ret.append(ts)
            elif k == "if":
                c = self.ex(s[1], env, ind)
                # gen scoping: names first assigned inside a block stay local to it
                self.emit(f"if {c} != 0.0:", ind)
                self.emit("pass", ind + 1)
                self.block(s[2], dict(env), ind + 1, pre, ret)
                if s[3]:
                    self.emit("else:", ind)
                    self.emit("pass", ind + 1)
                    self.block(s[3], dict(env), ind + 1, pre, ret)
            elif k == "for":
                self.block([s[1]], env, ind, pre, ret)
                self.emit("_guard = 0", ind)
                self.emit("while True:", ind)
                c = self.ex(s[2], env, ind + 1)
                self.emit(f"if {c} == 0.0 or _guard > 100000: break", ind + 1)
                self.emit("_guard += 1", ind + 1)
                inner = dict(env)
                self.block(s[4], inner, ind + 1, pre, ret)
                self.block([s[3]], inner, ind + 1, pre, ret)
            else:
                raise SyntaxError(k)


HELPERS = '''
import math
import numpy as np
from numba import njit

@njit(cache=False, inline="always")
def _fixdenorm(x):
    return 0.0 if abs(x) < 1.17549435e-38 else x

@njit(cache=False, inline="always")
def _fixnan(x):
    return x if math.isfinite(x) else 0.0

@njit(cache=False, inline="always")
def _sign(x):
    return 1.0 if x > 0 else (-1.0 if x < 0 else 0.0)

@njit(cache=False, inline="always")
def _sqrt(x):
    return math.sqrt(x) if x >= 0 else 0.0

@njit(cache=False, inline="always")
def _pow(a, b):
    if a < 0 and b != math.floor(b):
        return 0.0
    if a == 0 and b < 0:
        return 0.0
    return a ** b

@njit(cache=False, inline="always")
def _div(a, b):
    if b == 0.0:
        return 0.0
    return a / b

@njit(cache=False, inline="always")
def _fmod(a, b):
    if b == 0.0:
        return 0.0
    return math.fmod(a, b)
'''


class Program:
    def __init__(self, src_py, fn, params):
        self.source = src_py
        self.fn = fn
        self.params = params

    def run(self, in1, in2, sr, values=None, seed=1):
        n = len(in1)
        values = values or {}
        cols = []
        for name, (_, default, kw) in self.params.items():
            v = values.get(name, None)
            if v is None:
                v = default
            arr = np.broadcast_to(np.asarray(v, dtype=np.float64), (n,))
            cols.append(arr)
        unknown = set(values) - set(self.params)
        if unknown:
            raise KeyError(f"unknown params {unknown}")
        # always pass fresh, writeable, C-contiguous float64 arrays: numba types a
        # read-only view differently and would compile a second (~20 s) copy
        P = np.array(np.stack(cols, axis=1), dtype=np.float64, order="C") if cols else np.zeros((n, 0))
        SR = np.array(np.broadcast_to(np.asarray(sr, dtype=np.float64), (n,)), dtype=np.float64, order="C")
        return self.fn(np.array(in1, dtype=np.float64, order="C"),
                       np.array(in2, dtype=np.float64, order="C"), SR, P, int(seed))


_CACHE = {}


def compile_genexpr(src, name="gsx_prog", check_order=True):
    """Compiled programs are cached per source text within a process.
    check_order=False skips gen~'s 'function definitions must precede all statements'
    rule. Use it ONLY to run frozen historical sources (V2, V2.1, the research
    candidate) as numerical references: those sources do NOT compile in native gen~."""
    key = (src, name, check_order)
    if key not in _CACHE:
        _CACHE[key] = _compile(src, name, check_order)
    return _CACHE[key]


def _compile(src, name, check_order=True):
    params, funcs, body = P(tokenize(src), check_order).program()
    g = Gen(params, funcs)
    env = {}
    g.block(body, env, 2, "", [])
    pinfo = {}
    for p in params:
        nm, d, kw = p
        pinfo[nm] = (nm, g.const_expr(d), {k: g.const_expr(v) for k, v in kw.items()})
    lines = [HELPERS, "@njit(cache=False, fastmath=False)",
             f"def {name}(IN1, IN2, SRA, PA, seed):",
             "    np.random.seed(seed)",
             "    n = IN1.shape[0]",
             "    OUT1 = np.zeros(n); OUT2 = np.zeros(n)",
             "    _k = 0; _guard = 0"]
    for s in g.init:
        lines.append("    " + s)
    for l in sorted(g.locals):
        lines.append(f"    {l} = 0.0")
    lines.append("    for i in range(n):")
    lines.append("        SR = SRA[i]")
    for j, (nm, (_, d, kw)) in enumerate(pinfo.items()):
        lo, hi = kw.get("min", -1e300), kw.get("max", 1e300)
        lines.append(f"        P_{nm} = min(max(PA[i, {j}], {lo!r}), {hi!r})")
    lines += g.lines
    lines.append("    return OUT1, OUT2")
    src_py = "\n".join(lines)
    ns = {}
    exec(compile(src_py, f"<gsx:{name}>", "exec"), ns)
    return Program(src_py, ns[name], pinfo)


if __name__ == "__main__":
    import sys
    prog = compile_genexpr(open(sys.argv[1]).read())
    print(prog.source if "-v" in sys.argv else f"ok: {len(prog.params)} params")
