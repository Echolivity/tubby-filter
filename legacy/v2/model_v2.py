"""Line-by-line reference models of the v1 and v2 gen~ code (numba).

They mirror tubby_filter.genexpr (v1: original file, v2: src/) so the DSP
can be measured outside Max. Parameters are scalars except the step
selectors, which are per-sample arrays so switching can be tested.
"""
import math
import numpy as np
from numba import njit

STEPS = np.array([20, 70, 100, 150, 250, 500, 1000, 2000, 3000, 5000, 7500, 10000], dtype=np.float64)


@njit(cache=True)
def _fix(x):
    if not math.isfinite(x):
        return 0.0
    if abs(x) < 1.17549435e-38:   # same flush limit as tools/gsx.py
        return 0.0
    return x


# ------------------------------------------------------------------ v1
@njit(cache=True)
def run_v1(in1, in2, knob, sr, reso=1.4, drive=20.0, glide=0.0, click=30.0,
           slope=1.0, blend=100.0, seed=1):
    np.random.seed(seed)
    n = in1.shape[0]
    o1 = np.zeros(n); o2 = np.zeros(n)
    lf = 3.0; wt = 0.0; prev = 0.0; env = 0.0
    sL = np.zeros(3); sR = np.zeros(3)
    for i in range(n):
        idx = min(max(math.floor(knob[i] + 0.5), 0), 11)
        fsel = STEPS[int(idx)]
        kg = 1 - math.exp(-1 / (glide * 0.001 * sr)) if glide > 0.5 else 1.0
        lf = lf + (math.log(fsel) - lf) * kg
        fc = min(max(math.exp(lf), 10), sr * 0.45)
        on = 1.0 if idx > 0 else 0.0
        wt = wt + (on - wt) * (1 - math.exp(-1 / (0.004 * sr)))
        if idx != prev:
            env = click * 0.01
        else:
            env = env * math.exp(-1 / (0.0025 * sr))
        prev = idx
        clk = (np.random.random() * 2 - 1) * env * 0.15
        dg = 1 + drive * 0.03
        dL = math.tanh(in1[i] * dg) / math.sqrt(dg)
        dR = math.tanh(in2[i] * dg) / math.sqrt(dg)
        g = math.tan(math.pi * fc / sr)
        k = 1 / reso
        res = np.zeros(2)
        for c in range(2):
            x = dL if c == 0 else dR
            s = sL if c == 0 else sR
            a1 = 1 / (1 + g * (g + k)); a2 = g * a1; a3 = g * a2
            v3 = x - s[1]
            v1 = a1 * s[0] + a2 * v3
            v2 = s[1] + a2 * s[0] + a3 * v3
            s[0] = 2 * v1 - s[0]; s[1] = 2 * v2 - s[1]
            h = x - k * v1 - v2
            G = g / (1 + g)
            v = (h - s[2]) * G
            lp = v + s[2]
            s[2] = lp + v
            f = h + (h - lp - h) * slope
            res[c] = x + (f - x) * wt
        b = blend * 0.01
        o1[i] = in1[i] + (res[0] - in1[i]) * b + clk
        o2[i] = in2[i] + (res[1] - in2[i]) * b + clk
    return o1, o2


# ------------------------------------------------------------------ v2
@njit(cache=True)
def run_v2(in1, in2, knob, knobr, sr, reso=1.4, drive=20.0, glide=0.0, click=30.0,
           slope=1.0, blend=100.0, stereo=0, comp=1, drvonly=0, outdb=0.0,
           seed=1, settle=True):
    """settle=True starts smoothers at their targets (steady-state tests);
    settle=False starts them from zero exactly like gen~ at load."""
    np.random.seed(seed)
    n = in1.shape[0]
    o1 = np.zeros(n); o2 = np.zeros(n)

    def cms(ms):
        return 1 - math.exp(-1 / (max(ms, 0.01) * 0.001 * sr))

    # smoother states
    sq = reso if settle else 0.0
    sd = drive if settle else 0.0
    ss = slope if settle else 0.0
    sb = blend if settle else 0.0
    so = 10 ** (outdb / 20) if settle else 0.0
    lfL = math.log(20.0); lfR = math.log(20.0)
    wL = 0.0; wR = 0.0; pL = 0.0; pR = 0.0; tL = 1.0; tR = 1.0
    age = 1.0 if settle else 0.0
    if settle:
        i0L = min(max(math.floor(knob[0] + 0.5), 0), 11)
        i0R = min(max(math.floor(knobr[0] + 0.5), 0), 11) if stereo == 1 else i0L
        lfL = math.log(STEPS[int(i0L)]); lfR = math.log(STEPS[int(i0R)])
        wL = 1.0 if (i0L > 0 and drvonly == 0) else 0.0
        wR = 1.0 if (i0R > 0 and drvonly == 0) else 0.0
        pL = i0L; pR = i0R
    svf = np.zeros(6)       # icL1 icL2 opL icR1 icR2 opR
    dc = np.zeros(4)        # xpL ypL xpR ypR
    nlp = np.zeros(2)       # click noise filters
    r_dc = math.exp(-2 * math.pi * 5 / sr)
    c5k = 1 - math.exp(-2 * math.pi * 5000 / sr)
    c500 = 1 - math.exp(-2 * math.pi * 500 / sr)
    dch = np.zeros(2); y2 = np.zeros(2)
    for i in range(n):
        age = min(age + 1 / sr, 1.0)
        sq = _fix(sq + (reso - sq) * cms(20)); q = max(sq, 0.5)
        sd = _fix(sd + (drive - sd) * cms(20)); d = min(max(sd, 0), 100) * 0.01
        ss = _fix(ss + (slope - ss) * cms(10)); sl = min(max(ss, 0), 1)
        sb = _fix(sb + (blend - sb) * cms(20)); bl = min(max(sb, 0), 100) * 0.01
        so = _fix(so + (10 ** (outdb / 20) - so) * cms(20)); og = so

        mono = (in1[i] + in2[i]) * 0.5
        xL = mono if stereo == 2 else in1[i]
        xR = mono if stereo == 2 else in2[i]

        G = 10 ** (d * 18 / 20); b = 0.25 * d; amt = min(max(d * 8, 0), 1)
        tb = math.tanh(b); s0 = G * (1 - tb * tb)
        sp = (math.tanh(G + b) - math.tanh(b - G)) * 0.5
        for c in range(2):
            x = xL if c == 0 else xR
            sh = math.tanh(G * x + b) - tb
            y = sh / s0 if comp == 1 else sh / sp
            yy = _fix(y - dc[2 * c] + r_dc * dc[2 * c + 1])
            dc[2 * c] = y; dc[2 * c + 1] = yy
            dch[c] = x + (yy - x) * amt
        dL = dch[0]; dR = dch[1]

        iL = min(max(math.floor(knob[i] + 0.5), 0), 11)
        iR = min(max(math.floor(knobr[i] + 0.5), 0), 11) if stereo == 1 else iL
        cg = cms(max(glide, 0.5))
        lfL = lfL + (math.log(STEPS[int(iL)]) - lfL) * cg
        lfR = lfR + (math.log(STEPS[int(iR)]) - lfR) * cg
        fcL = min(max(math.exp(lfL), 10), sr * 0.45)
        fcR = min(max(math.exp(lfR), 10), sr * 0.45)
        byp = 1.0 if drvonly == 1 else 0.0
        cw = cms(max(4.0, glide))
        wL = wL + ((1.0 if iL > 0 else 0.0) * (1 - byp) - wL) * cw
        wR = wR + ((1.0 if iR > 0 else 0.0) * (1 - byp) - wR) * cw

        k = 1 / q
        for c in range(2):
            x = dL if c == 0 else dR
            g = math.tan(math.pi * (fcL if c == 0 else fcR) / sr)
            o = 3 * c
            a1 = 1 / (1 + g * (g + k)); a2 = g * a1; a3 = g * a2
            v3 = x - svf[o + 1]
            v1 = a1 * svf[o] + a2 * v3
            v2 = svf[o + 1] + a2 * svf[o] + a3 * v3
            svf[o] = _fix(2 * v1 - svf[o]); svf[o + 1] = _fix(2 * v2 - svf[o + 1])
            h = x - k * v1 - v2
            Gp = g / (1 + g)
            v = (h - svf[o + 2]) * Gp
            lp = v + svf[o + 2]
            svf[o + 2] = _fix(lp + v)
            f = h + ((h - lp) - h) * sl
            w = wL if c == 0 else wR
            y2[c] = x + (f - x) * w

        oL = (xL + (y2[0] - xL) * bl) * og
        oR = (xR + (y2[1] - xR) * bl) * og

        chL = iL != pL; chR = iR != pR
        pL = iL; pR = iR
        tL = 0.0 if chL else min(tL + 1 / sr, 1.0)
        tR = 0.0 if chR else min(tR + 1 / sr, 1.0)
        nz = (np.random.random() * 2 - 1) * math.sqrt(sr / 44100)
        nlp[0] = nlp[0] + (nz - nlp[0]) * c5k
        nlp[1] = nlp[1] + (nlp[0] - nlp[1]) * c500
        nb = nlp[0] - nlp[1]
        cgn = click * 0.01 * 0.5 * (1.0 if glide < 1 else 0.0) * (1 - byp) * (1.0 if age > 0.2 else 0.0)
        oL += nb * _bounce(tL) * cgn * og
        oR += nb * _bounce(tR) * cgn * og

        o1[i] = _fix(_safety(oL)); o2[i] = _fix(_safety(oR))
    return o1, o2


@njit(cache=True)
def _bounce(t):
    if t >= 0.02:
        return 0.0
    tau = 0.0007
    e = math.exp(-t / tau)
    if t >= 0.0011:
        e += 0.45 * math.exp(-(t - 0.0011) / tau)
    if t >= 0.0026:
        e += 0.20 * math.exp(-(t - 0.0026) / tau)
    return e


@njit(cache=True)
def _safety(x):
    th = 1.9953; kn = 0.5166
    a = abs(x)
    if a > th:
        return math.copysign(th + kn * math.tanh((a - th) / kn), x)
    return x


def const(n, v):
    return np.full(n, float(v))
