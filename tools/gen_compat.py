"""Static gen~ compatibility audit for a .genexpr file.   python3 tools/gen_compat.py FILE

This is code inspection, not compilation. It checks the source against the
official operator lists from the Cycling '74 documentation (gen common operators
and gen~ operators pages, retrieved 2026-11-04):
  * every called function is a documented operator or a user function
  * no user variable, function, Param or History name collides with an operator
    or constant name (e.g. `f`, `e`, `i`, `r`, `s`, `gate`, `step`, `delta`)
  * functions are declared before statements; Params only in the main body
  * History initialisers are constants; no `++`/`--`
It does NOT prove that gen~ accepts the file. Native compilation is required.
"""
import re, sys

COMMON = """!=p neqp gt eq eqp gte gtep gtp lt lte ltep ltp max maximum min minimum neq step
constant degtorad DEGTORAD e E f float halfpi HALFPI i int invpi INVPI ln10 LN10 ln2 LN2 log10e LOG10E
log2e LOG2E PHI phi pi PI radtodeg RADTODEG sqrt1_2 SQRT1_2 sqrt2 SQRT2 twopi TWOPI param Param expr pass
in out not and bool or xor rmod rsub mod add sub div absdiff cartopol mul neg poltocar rdiv abs ceil floor
trunc fract sign exp exp2 fastexp fastpow ln log log10 log2 pow sqrt clamp clip fold scale wrap switch gate
mix r receive s send selector smoothstep gen setparam acos acosh asin asinh atan atan2 atanh cos cosh
degrees fastcos fastsin fasttan hypot radians sin sinh tan tanh noise""".split()
GENTILDE = """buffer channels cycle data dim lookup nearest peek poke sample splat wave atodb dbtoa ftom mstosamps
mtof sampstoms fftfullspect FFTFULLSPECT ffthop FFTHOP fftoffset FFTOFFSET fftsize FFTSIZE samplerate
SAMPLERATE vectorsize VECTORSIZE fixdenorm fixnan isdenorm isnan t60 t60time delay history fftinfo change
dcblock delta interp latch phasewrap sah slide elapsed mc_channel mc_channelcount voice voicecount
mulequals accum plusequals counter round phasor rate train triangle""".split()
RESERVED = set(COMMON) | set(GENTILDE)
CONSTANTS = {"pi", "PI", "twopi", "TWOPI", "halfpi", "HALFPI", "e", "E", "samplerate", "SAMPLERATE",
             "ln2", "LN2", "ln10", "LN10", "invpi", "INVPI", "sqrt2", "SQRT2", "sqrt1_2", "SQRT1_2",
             "log2e", "LOG2E", "log10e", "LOG10E", "phi", "PHI", "degtorad", "radtodeg", "vectorsize"}
KEYWORDS = {"if", "else", "for", "while", "return", "break", "continue", "History", "Param", "Data", "Buffer"}
IO = re.compile(r"^(in|out)\d+$")


def audit(src):
    code = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    code = re.sub(r"//[^\n]*", " ", code)
    issues, notes = [], []
    # user functions: name(args) {   at top level
    funcs = set(re.findall(r"(?m)^\s*([A-Za-z_]\w*)\s*\([^()]*\)\s*\{", code)) - KEYWORDS
    for fn in sorted(funcs):
        if fn in RESERVED:
            issues.append(f"function name '{fn}' collides with a gen operator")
    # first top-level statement must come after the last function definition
    lines = code.split("\n")
    depth, last_fn_end, first_stmt = 0, -1, None
    for n, l in enumerate(lines):
        st = l.strip()
        if depth == 0 and st:
            if re.match(r"^[A-Za-z_]\w*\s*\([^()]*\)\s*\{", st) and st.split("(")[0].strip() not in KEYWORDS:
                pass
            elif first_stmt is None and not st.startswith("}"):
                first_stmt = n
        depth += l.count("{") - l.count("}")
        if depth == 0 and "}" in l:
            last_fn_end = n if first_stmt is None or n < first_stmt else last_fn_end
    # gen~ rule (confirmed by the Max console in Live 12): every function definition must
    # precede ALL statements, including Param and History declarations
    depth, first_stmt_line = 0, None
    for n, l in enumerate(lines, 1):
        st = l.strip()
        if depth == 0 and st and not st.startswith("}"):
            m = re.match(r"^([A-Za-z_]\w*)\s*\([^()]*\)\s*\{", st)
            if m and m.group(1) not in KEYWORDS:
                if first_stmt_line:
                    issues.append(f"line {n}: function '{m.group(1)}' defined after a statement (line "
                                  f"{first_stmt_line}); gen~: function definitions must precede all statements")
            elif first_stmt_line is None:
                first_stmt_line = n
        depth += l.count("{") - l.count("}")
    # declarations
    params = re.findall(r"\bParam\s+([A-Za-z_]\w*)\s*\(", code)
    hist = []
    for m in re.finditer(r"\bHistory\s+([^;]+);", code):
        for d in re.finditer(r"([A-Za-z_]\w*)\s*\(([^()]*)\)", m.group(1)):
            hist.append(d.group(1))
            if not re.fullmatch(r"\s*-?[\d.eE+-]+\s*", d.group(2)):
                issues.append(f"History '{d.group(1)}' initialiser is not a constant: {d.group(2)!r}")
    assigned = set()
    for m in re.finditer(r"(?m)(?:^|[;{}]|\bif\s*\([^)]*\))\s*([A-Za-z_]\w*(?:\s*,\s*[A-Za-z_]\w*)*)\s*(?:=|\+=|-=|\*=|/=)(?!=)", code):
        for v in m.group(1).split(","):
            assigned.add(v.strip())
    for fm in re.finditer(r"(?m)^\s*([A-Za-z_]\w*)\s*\(([^()]*)\)\s*\{", code):
        if fm.group(1) not in KEYWORDS:
            for a in fm.group(2).split(","):
                if a.strip():
                    assigned.add(a.strip())
    for name in sorted(set(params) | set(hist) | assigned):
        if IO.match(name):
            continue
        if name in RESERVED or name in CONSTANTS:
            issues.append(f"name '{name}' (variable/argument/Param/History) collides with a gen operator or constant")
    # calls
    for c in sorted(set(re.findall(r"\b([A-Za-z_]\w*)\s*\(", code)) - KEYWORDS - set(params) - set(hist)):
        if c in funcs:
            continue
        if c not in RESERVED:
            issues.append(f"call to '{c}' is neither a documented operator nor a user function")
    if "++" in code or "--" in code.replace("--", "--"):
        if re.search(r"\+\+|--", code):
            issues.append("'++' or '--' used (not supported in GenExpr)")
    # multiple-return assignment inside a block: documented feature, flagged as a compile risk
    mr = len(re.findall(r"(?m)^\s{4,}[A-Za-z_]\w*\s*,\s*[A-Za-z_]\w*[^=\n]*=\s*[A-Za-z_]\w*\(", code))
    if mr:
        notes.append(f"{mr} multiple-return assignments inside a block (documented GenExpr feature; "
                     "not confirmed inside if/else without native compilation)")
    notes.append(f"{len(funcs)} user functions, {len(params)} Params, {len(hist)} History declarations")
    return issues, notes


if __name__ == "__main__":
    ok = True
    for path in sys.argv[1:]:
        iss, notes = audit(open(path).read())
        print(f"== {path}")
        for n in notes:
            print("  note :", n)
        for i in iss:
            print("  ISSUE:", i)
        print("  result:", "no static issues" if not iss else f"{len(iss)} issue(s)")
        ok &= not iss
    sys.exit(0 if ok else 1)
