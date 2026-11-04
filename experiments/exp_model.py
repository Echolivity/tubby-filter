"""Tubby Filter V2.2 RESEARCH model — V2.1 reference + switchable experiments.

NOT the release DSP. Every experiment defaults to off; with all defaults the
output is bit-identical to tests/model_v21.py (checked by experiments/test_exp.py).

Experiment parameters (EX vector, constant per run):
  core   0..1   X1 nonlinear inductance: inductor-current-dependent cutoff/damping
  cmode  0/1/2  X1 variant: 0 = inductance (cutoff) only, 1 = loss (damping) only, 2 = both
  motion 0..1   X2 movement-dependent damping: resonance blooms with cutoff velocity
  mdir  -1..1   X2 direction weighting (+ = rising moves bloom more)
  hyst   oct    X2h rate-independent hysteresis (backlash) on the cutoff, width in octaves
  contact 0..1  X3 signal-dependent switching transient
  ctype  0/1    X3 variant: 0 = break-before-make gate on the output, 1 = inductive kick
                (the shunt-inductor current at the switch instant decays into the output)
  notch  0/1    X4 vari-notch architecture instead of high-pass
  latc   0/1    X7 constant 3-sample latency at >= 60 kHz (so a fixed reported latency is correct)
"""

import math
import numpy as np
from numba import njit

PNAMES = ["knob", "reso", "drive", "glide", "click", "slope", "blend",
          "knobr", "stereo", "comp", "drvonly", "outdb", "active"]
DEFAULTS = dict(knob=0, reso=1.4, drive=20, glide=0, click=30, slope=1, blend=100,
                knobr=0, stereo=0, comp=1, drvonly=0, outdb=0, active=1)
RANGES = dict(knob=(0, 11), reso=(0.5, 8), drive=(0, 100), glide=(0, 2000), click=(0, 100),
              slope=(0, 1), blend=(0, 100), knobr=(0, 11), stereo=(0, 2), comp=(0, 1),
              drvonly=(0, 1), outdb=(-24, 12), active=(0, 1))
STEPS = np.array([20, 70, 100, 150, 250, 500, 1000, 2000, 3000, 5000, 7500, 10000], float)
HB = np.array([0.04063346092419326, 0.1505051290226746, 0.3007570559918741, 0.4607745049614506,
               0.6095243148961883, 0.7385038411188573, 0.8492238103920661, 0.9497427837050002])


@njit(inline="always")
def fx(x):
    if not math.isfinite(x):
        return 0.0
    if abs(x) < 1.17549435e-38:
        return 0.0
    return x


@njit(inline="always")
def coef(ms, sr):
    return 1.0 - math.exp(-1.0 / (max(ms, 0.01) * 0.001 * sr))


@njit
def allpass_branch(x, c, off, st, so):
    # four first-order allpass sections using coefficients c[off], c[off+2], ...
    for j in range(4):
        a = c[off + 2 * j]
        y = a * x + st[so + j]
        st[so + j] = fx(x - a * y)
        x = y
    return x


@njit
def chan(x, G, b, tb, s0, sp, cw, amt, r5, g, k, sl, w, bl, st, o, core, cmode, kmot, notch, ndepth):
    # st[o..o+4] = dc_x, dc_y, ic1, ic2, onepole
    sh = math.tanh(G * x + b) - tb
    if cw >= 1.0:
        yd = sh / s0
    elif cw <= 0.0:
        yd = sh / sp
    else:
        yd = sh / sp + (sh / s0 - sh / sp) * cw
    dy = fx(yd - st[o] + r5 * st[o + 1])
    st[o] = yd; st[o + 1] = dy
    d = x + (dy - x) * amt
    # ---- X1: nonlinear inductance. v1 (band-pass) of the normalised SVF is the
    # shunt-inductor current; core saturation lowers L as |i| grows, which raises
    # the cutoff (cmode 0) and/or adds core loss = damping (cmode 1). Uses the
    # previous-sample state (explicit), so the TPT solve stays linear per sample.
    if core > 0.0:
        ii = 0.5 * st[o + 2]
        ii2 = ii * ii
        if cmode != 1:
            g = min(g * math.sqrt(1.0 + 2.0 * core * ii2), 6.3)
        if cmode != 0:
            k = k * (1.0 + 2.0 * core * ii2)
    # ---- X2: movement-dependent damping (kmot = 1 when off: k * 1.0 == k exactly)
    k = k * kmot
    a1 = 1.0 / (1.0 + g * (g + k)); a2 = g * a1; a3 = g * a2
    v3 = d - st[o + 3]
    v1 = a1 * st[o + 2] + a2 * v3
    v2 = st[o + 3] + a2 * st[o + 2] + a3 * v3
    h = d - k * v1 - v2
    G1 = g / (1.0 + g)
    v = (h - st[o + 4]) * G1
    lp = v + st[o + 4]
    f = h + ((h - lp) - h) * sl
    if notch > 0.5:
        f = d - ndepth * k * v1          # X4: SVF notch (LP + HP), depth per step
    st[o + 2] = fx(2 * v1 - st[o + 2]); st[o + 3] = fx(2 * v2 - st[o + 3]); st[o + 4] = fx(lp + v)
    inner = d + (f - d) * w
    return x + (inner - x) * bl


@njit
def bounce(t):
    if t >= 0.02:
        return 0.0
    tau = 0.0007
    e = math.exp(-t / tau)
    if t >= 0.0011:
        e += 0.45 * math.exp(-(t - 0.0011) / tau)
    if t >= 0.0026:
        e += 0.20 * math.exp(-(t - 0.0026) / tau)
    return e


@njit
def gate(t):
    """X3 contact: open-circuit windows (s) with 30 us raised-cosine edges."""
    g = 0.0
    for t0, t1 in ((0.0, 0.00025), (0.0011, 0.00115), (0.0026, 0.00263)):
        e = 0.00003
        if t >= t0 - e and t <= t1 + e:
            if t < t0:
                v = 0.5 - 0.5 * math.cos(math.pi * (t - (t0 - e)) / e)
            elif t > t1:
                v = 0.5 + 0.5 * math.cos(math.pi * (t - t1) / e)
            else:
                v = 1.0
            g = max(g, v)
    return g


@njit
def safety(x):
    th = 1.9953; kn = 0.5166
    a = abs(x)
    if a > th:
        return math.copysign(th + kn * math.tanh((a - th) / kn), x)
    return x


@njit
def _run(IN1, IN2, SRA, P, seed, EX):
    np.random.seed(seed)
    n = IN1.shape[0]
    o1 = np.zeros(n); o2 = np.zeros(n)
    st = np.zeros(10)            # chan states L (0..4), R (5..9)
    up = np.zeros(16)            # up-sampler states L (0..7), R (8..15)
    dn = np.zeros(16)            # down-sampler states
    sm = np.zeros(4)             # reso, drive, slope, blend smoothers
    xf = np.zeros(4)             # mono, dual, comp, bypass crossfades
    lf0 = math.log(20.0)
    lfL = lf0; lfR = lf0; wL = 0.0; wR = 0.0; pK = 0.0; pKR = 0.0
    tL = 1.0; tR = 1.0; age = 0.0; ogs = 1.0; rw = 0.0; srp = 0.0; actp = 1.0
    nl1 = 0.0; nl2 = 0.0
    core, cmode, motion, mdir, hyst, contact, notch, latc = EX[0], int(EX[1]), EX[2], EX[3], EX[4], EX[5], EX[6], EX[7]
    ctype = int(EX[8])
    kickL = 0.0; kickR = 0.0             # X3 kick: inductor current captured at the switch
    mvL = 0.0; mvR = 0.0                 # X2 motion envelopes
    msm = 0.0                            # X2 smoothed motion amount (20 ms, like the other controls)
    hbL = -1.0; hbR = -1.0               # X2h backlash states (log Hz); <0 = uninitialised
    dl = np.zeros((4, 2)); di = 0        # X7 3-sample delay line
    for i in range(n):
        sr = SRA[i]
        knob, reso, drive, glide, click, slope, blend, knobr, stereo, comp, drvonly, outdb, active = P[i]
        rst = sr != srp or (active > 0.5 and actp < 0.5)
        srp = sr; actp = active
        if rst:
            st[:] = 0.0; up[:] = 0.0; dn[:] = 0.0
            nl1 = 0.0; nl2 = 0.0
        os2 = sr < 60000
        fs = sr * 2 if os2 else sr
        age = 0.0 if rst else min(age + 1 / sr, 1.0)

        # continuous smoothers
        sm[0] = fx(sm[0] + (reso - sm[0]) * coef(20, sr)); q = max(sm[0], 0.5)
        sm[1] = fx(sm[1] + (drive - sm[1]) * coef(20, sr)); dd = min(max(sm[1], 0), 100) * 0.01
        sm[2] = fx(sm[2] + (slope - sm[2]) * coef(10, sr)); sl = min(max(sm[2], 0), 1)
        sm[3] = fx(sm[3] + (blend - sm[3]) * coef(20, sr)); bl = min(max(sm[3], 0), 100) * 0.01
        if rst:
            ogs = 10 ** (outdb / 20)
        else:
            ogs = fx(ogs + (10 ** (outdb / 20) - ogs) * coef(20, sr))
        og = ogs
        rw = 0.0 if rst else min(rw + 1 / (0.01 * sr), 1.0)

        # discrete crossfades (snap within 1e-7)
        mode = math.floor(stereo + 0.5)
        dual = mode == 1
        tg = (1.0 if mode == 2 else 0.0, 1.0 if dual else 0.0, 1.0 if comp > 0.5 else 0.0,
              1.0 if drvonly > 0.5 else 0.0)
        ms = (10.0, 20.0, 20.0, 10.0)
        for j in range(4):
            v = xf[j] + (tg[j] - xf[j]) * coef(ms[j], sr)
            if rst or abs(tg[j] - v) < 1e-7:
                v = tg[j]
            xf[j] = v if math.isfinite(v) else 0.0
        mw, dw, cw, bw = xf[0], xf[1], xf[2], xf[3]

        mono = (IN1[i] + IN2[i]) * 0.5
        if mw <= 0:
            xL = IN1[i]; xR = IN2[i]
        elif mw >= 1:
            xL = mono; xR = mono
        else:
            xL = IN1[i] + (mono - IN1[i]) * mw; xR = IN2[i] + (mono - IN2[i]) * mw

        G = 10 ** (dd * 18 / 20); b = 0.25 * dd; tb = math.tanh(b)
        s0 = G * (1 - tb * tb); sp = (math.tanh(G + b) - math.tanh(b - G)) * 0.5
        amt = min(max(dd * 8, 0), 1); r5 = math.exp(-2 * math.pi * 5 / fs)

        iL = min(max(math.floor(knob + 0.5), 0), 11)
        iRk = min(max(math.floor(knobr + 0.5), 0), 11)
        ltL = math.log(STEPS[int(iL)])
        ltR = ltL if dw <= 0 else ltL + (math.log(STEPS[int(iRk)]) - ltL) * dw
        if hyst > 0.0:                   # X2h: play operator (rate-independent)
            hw = 0.5 * hyst * math.log(2.0)
            if hbL < 0 or rst:
                hbL = ltL; hbR = ltR
            if ltL > hbL + hw: hbL = ltL - hw
            elif ltL < hbL - hw: hbL = ltL + hw
            if ltR > hbR + hw: hbR = ltR - hw
            elif ltR < hbR - hw: hbR = ltR + hw
            ltL = hbL; ltR = hbR
        plL = lfL; plR = lfR
        cg = coef(max(glide, 0.5), sr)
        if rst:
            lfL = ltL; lfR = ltR
        else:
            lfL = lfL + (ltL - lfL) * cg
            lfR = lfR + (ltR - lfR) * cg
        if dw <= 0 and abs(lfR - lfL) < 1e-9:
            lfR = lfL
        # X2: cutoff velocity (oct/s) -> envelope -> damping. Always computed;
        # with motion 0 the factor is exactly 1.0, so V2.1 output is unchanged.
        msm = fx(msm + (motion - msm) * coef(20, sr))
        if True:
            vL = 0.0 if rst else (lfL - plL) * sr / math.log(2.0)
            vR = 0.0 if rst else (lfR - plR) * sr / math.log(2.0)
            if dw > 0 and dw < 1:        # mode crossfade is not a performed gesture
                vR = vL
            vL = abs(vL) * max(0.0, 1.0 + mdir * (1.0 if vL > 0 else -1.0))
            vR = abs(vR) * max(0.0, 1.0 + mdir * (1.0 if vR > 0 else -1.0))
            caL = coef(2.0, sr) if vL > mvL else coef(120.0, sr)
            caR = coef(2.0, sr) if vR > mvR else coef(120.0, sr)
            mvL = fx(mvL + (vL - mvL) * caL); mvR = fx(mvR + (vR - mvR) * caR)
            mnL = mvL / (mvL + 8.0); mnR = mvR / (mvR + 8.0)
            kmL = 1.0 / (1.0 + msm * 4.0 * mnL); kmR = 1.0 / (1.0 + msm * 4.0 * mnR)
        fcL = min(max(math.exp(lfL), 10), fs * 0.45)
        fcR = min(max(math.exp(lfR), 10), fs * 0.45)

        cwf = coef(max(4.0, glide), sr)
        onL = 1.0 if iL > 0 else 0.0
        onR = onL if dw <= 0 else onL + ((1.0 if iRk > 0 else 0.0) - onL) * dw
        if rst:
            wL = 0.0; wR = 0.0
        wL = wL + (onL - wL) * cwf
        wR = wR + (onR - wR) * cwf
        if dw <= 0 and abs(wR - wL) < 1e-9:
            wR = wL
        weL = wL * (1 - bw); weR = wR * (1 - bw)

        k = 1 / q
        ndL = min(0.5 + 0.05 * iL, 1.0); ndR = min(0.5 + 0.05 * (iRk if dual else iL), 1.0)
        gL = math.tan(math.pi * fcL / fs); gR = math.tan(math.pi * fcR / fs)
        if os2:
            # up: sub-sample 0 = even-coef branch, 1 = odd-coef branch
            u0L = allpass_branch(xL, HB, 0, up, 0); u1L = allpass_branch(xL, HB, 1, up, 4)
            u0R = allpass_branch(xR, HB, 0, up, 8); u1R = allpass_branch(xR, HB, 1, up, 12)
            v0L = chan(u0L, G, b, tb, s0, sp, cw, amt, r5, gL, k, sl, weL, bl, st, 0, core, cmode, kmL, notch, ndL)
            v1L = chan(u1L, G, b, tb, s0, sp, cw, amt, r5, gL, k, sl, weL, bl, st, 0, core, cmode, kmL, notch, ndL)
            v0R = chan(u0R, G, b, tb, s0, sp, cw, amt, r5, gR, k, sl, weR, bl, st, 5, core, cmode, kmR, notch, ndR)
            v1R = chan(u1R, G, b, tb, s0, sp, cw, amt, r5, gR, k, sl, weR, bl, st, 5, core, cmode, kmR, notch, ndR)
            # down: (A0(v1) + A1(v0)) / 2
            yL = (allpass_branch(v1L, HB, 0, dn, 0) + allpass_branch(v0L, HB, 1, dn, 4)) * 0.5
            yR = (allpass_branch(v1R, HB, 0, dn, 8) + allpass_branch(v0R, HB, 1, dn, 12)) * 0.5
        else:
            yL = chan(xL, G, b, tb, s0, sp, cw, amt, r5, gL, k, sl, weL, bl, st, 0, core, cmode, kmL, notch, ndL)
            yR = chan(xR, G, b, tb, s0, sp, cw, amt, r5, gR, k, sl, weR, bl, st, 5, core, cmode, kmR, notch, ndR)
        if contact > 0.0 and age > 0.2 and ctype == 0:  # X3a: break-before-make on the processed path
            yL = yL * (1.0 - contact * (1 - bw) * gate(tL))
            yR = yR * (1.0 - contact * (1 - bw) * gate(tR))
        if contact > 0.0 and ctype == 1:  # X3b: inductive kick, i_L(t_switch) * exp(-t / 0.3 ms)
            if tL == 0.0 and age > 0.2:
                kickL = 0.5 * st[2]            # band-pass state = normalised inductor current
            if tR == 0.0 and age > 0.2:
                kickR = 0.5 * st[7]
            yL = yL + contact * (1 - bw) * 2.0 * kickL * math.exp(-tL / 0.0003) * (1.0 if tL < 0.005 else 0.0)
            yR = yR + contact * (1 - bw) * 2.0 * kickR * math.exp(-tR / 0.0003) * (1.0 if tR < 0.005 else 0.0)
        oL = yL * og; oR = yR * og
        if rw < 1:
            oL = IN1[i] + (oL - IN1[i]) * rw
            oR = IN2[i] + (oR - IN2[i]) * rw

        chK = iL != pK; chKR = iRk != pKR
        pK = iL; pKR = iRk
        fireL = chK; fireR = chKR if dual else chK
        tL = 1.0 if rst else (0.0 if fireL else min(tL + 1 / sr, 1.0))
        tR = 1.0 if rst else (0.0 if fireR else min(tR + 1 / sr, 1.0))
        nz = (np.random.random() * 2 - 1) * math.sqrt(sr / 44100)
        nl1 = fx(nl1 + (nz - nl1) * (1 - math.exp(-2 * math.pi * 5000 / sr)))
        nl2 = fx(nl2 + (nl1 - nl2) * (1 - math.exp(-2 * math.pi * 500 / sr)))
        nb = nl1 - nl2
        cgn = click * 0.01 * 0.5 * (1 - bw) * (1.0 if age > 0.2 else 0.0)
        oL += nb * bounce(tL) * cgn * og
        oR += nb * bounce(tR) * cgn * og
        sL = safety(oL); sR = safety(oR)
        sL = sL if math.isfinite(sL) else 0.0
        sR = sR if math.isfinite(sR) else 0.0
        if latc > 0.5 and not os2:       # X7: match the oversampler's ~3-sample delay
            dl[di, 0] = sL; dl[di, 1] = sR
            di = (di + 1) % 4
            sL = dl[di, 0]; sR = dl[di, 1]
        o1[i] = sL
        o2[i] = sR
    return o1, o2


EXN = ["core", "cmode", "motion", "mdir", "hyst", "contact", "notch", "latc", "ctype"]


def run(in1, in2, sr, seed=1, exp=None, **params):
    exp = exp or {}
    for kk in exp:
        if kk not in EXN:
            raise KeyError(kk)
    EX = np.array([float(exp.get(k, 0.0)) for k in EXN])
    n = len(in1)
    for kk in params:
        if kk not in DEFAULTS:
            raise KeyError(kk)
    cols = []
    for nm in PNAMES:
        v = params.get(nm, DEFAULTS[nm])
        lo, hi = RANGES[nm]
        cols.append(np.clip(np.broadcast_to(np.asarray(v, float), (n,)), lo, hi))
    P = np.array(np.stack(cols, 1), dtype=float, order="C")
    SR = np.array(np.broadcast_to(np.asarray(sr, float), (n,)), dtype=float, order="C")  # writeable: avoids a numba recompile
    return _run(np.array(in1, dtype=float, order="C"), np.array(in2, dtype=float, order="C"), SR, P, int(seed), EX)
