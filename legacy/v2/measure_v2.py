"""Measurement + validation suite for Tubby Filter (v1 vs v2).

Run:  python3 measure.py      -> writes ../docs/img/*.png and ../docs/results.json
Every number in the docs comes from this script.
"""
import json, math, os, time
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import signal
from model import run_v1, run_v2, const, STEPS

RATES = [44100, 48000, 88200, 96000]
OUT = os.path.join(os.path.dirname(__file__), "..", "docs")
IMG = os.path.join(OUT, "img")
os.makedirs(IMG, exist_ok=True)
R = {}
plt.rcParams.update({"figure.dpi": 110, "font.size": 9, "axes.grid": True, "grid.alpha": .3})


def db(x):
    return 20 * np.log10(np.maximum(np.abs(x), 1e-12))


def ir_v2(sr, step, n=1 << 15, **kw):
    x = np.zeros(n); x[0] = 1e-3        # small: keeps the drive stage linear
    kw.setdefault("click", 0.0)
    y, _ = run_v2(x, x.copy(), const(n, step), const(n, step), sr, **kw)
    return y / 1e-3


def ir_v1(sr, step, n=1 << 15, **kw):
    pre = int(sr * 0.5)                 # v1 has no settle option: pre-roll
    x = np.zeros(n + pre); x[pre] = 1e-3
    kw.setdefault("click", 0.0)
    y, _ = run_v1(x, x.copy(), const(n + pre, step), sr, **kw)
    return y[pre:] / 1e-3


def resp(h, sr):
    H = np.fft.rfft(h)
    f = np.fft.rfftfreq(len(h), 1 / sr)
    return f, db(H), H


def analog_hp(f, fc, Q, slope18):
    s = 1j * f / fc
    H = s * s / (s * s + s / Q + 1)
    if slope18:
        H = H * s / (s + 1)
    return db(H)


# ================================================================ 1. frequency response
print("1. frequency response")
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
cols = plt.cm.viridis(np.linspace(0, .9, 11))
for st in range(1, 12):
    for ver, ls, a in (("v1", ":", ax[0]), ("v2", "-", ax[0])):
        h = ir_v1(48000, st) if ver == "v1" else ir_v2(48000, st)
        f, m, _ = resp(h, 48000)
        a.semilogx(f[1:], m[1:], ls, color=cols[st - 1], lw=1 if ver == "v1" else 1.4)
ax[0].set(xlim=(20, 24000), ylim=(-60, 12), xlabel="Hz", ylabel="dB",
          title="All steps @48 kHz, Q 1.4, 18 dB, drive 20 %\n dotted = v1, solid = v2")
for sl, ls in ((0, "--"), (1, "-")):
    for Q, c in ((0.707, "C0"), (1.4, "C1"), (8, "C3")):
        h = ir_v2(48000, 7, reso=Q, slope=sl)
        f, m, _ = resp(h, 48000)
        ax[1].semilogx(f[1:], m[1:], ls, color=c, label=f"Q {Q}, {'18' if sl else '12'} dB")
ax[1].set(xlim=(100, 24000), ylim=(-60, 24), xlabel="Hz", title="v2 step 2 kHz: slope × resonance")
ax[1].legend(fontsize=7)
fig.tight_layout(); fig.savefig(f"{IMG}/fr_steps.png"); plt.close(fig)

# passband gain (v1 vs v2) at drive 20 % (default) and the cutoff accuracy per rate
pb = {}
for ver in ("v1", "v2"):
    h = ir_v1(48000, 1) if ver == "v1" else ir_v2(48000, 1)
    f, m, _ = resp(h, 48000)
    pb[ver] = float(m[np.argmin(abs(f - 2000))])
R["passband_gain_db_drive20"] = pb

# sample-rate independence: deviation from the analog prototype, 20 Hz..0.4·44.1 k
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
dev = {}
for sr in RATES:
    worst_pb = 0; worst_sk = 0
    for st in range(1, 12):
        for sl in (0, 1):
            for Q in (0.707, 1.4, 8):
                h = ir_v2(sr, st, n=1 << 16, reso=Q, slope=sl, drive=0)
                f, m, _ = resp(h, sr)
                sel = (f > 20) & (f < 17640) & (f > STEPS[st] / 8)
                a = analog_hp(f[sel], STEPS[st], Q, sl)
                e = np.abs(m[sel] - a)
                pbm = f[sel] >= STEPS[st]            # cutoff, resonant peak and passband
                skm = (f[sel] < STEPS[st]) & (a > -20)  # skirt down to -20 dB
                worst_pb = max(worst_pb, e[pbm].max() if pbm.any() else 0)
                worst_sk = max(worst_sk, e[skm].max() if skm.any() else 0)
    dev[sr] = dict(passband_and_peak=float(worst_pb), skirt_to_minus20=float(worst_sk))
    h = ir_v2(sr, 9, n=1 << 16, reso=1.4, drive=0)
    f, m, _ = resp(h, sr)
    ax[0].semilogx(f[1:], m[1:], label=f"{sr/1000:g} kHz")
ax[0].set(xlim=(500, 48000), ylim=(-50, 8), title="v2 step 5 kHz, Q 1.4 at each rate", xlabel="Hz")
ax[0].legend()
xs = np.arange(len(RATES))
ax[1].bar(xs - .2, [dev[s]["passband_and_peak"] for s in RATES], .4, label="f ≥ fc (cutoff, peak, passband)")
ax[1].bar(xs + .2, [dev[s]["skirt_to_minus20"] for s in RATES], .4, label="skirt fc → −20 dB")
ax[1].set_xticks(xs, [f"{s/1000:g}k" for s in RATES])
ax[1].set(ylabel="max |dB| error", title="Worst deviation from analog prototype\n(all 11 steps × 3 Q × 2 slopes, ≤17.6 kHz)")
ax[1].legend(fontsize=7)
fig.tight_layout(); fig.savefig(f"{IMG}/fr_samplerates.png"); plt.close(fig)
R["fr_max_dev_vs_analog_db"] = dev

# gain at cutoff (should be ~ Q·... analog value) and step-to-step passband consistency
pcons = []
for st in range(1, 11):
    h = ir_v2(48000, st, reso=0.707, slope=0, drive=0)
    f, m, _ = resp(h, 48000)
    pcons.append(float(m[np.argmin(abs(f - 20000))]))
R["passband_20k_db_steps1_10_q0707"] = [round(v, 3) for v in pcons]

# ================================================================ 2. drive
print("2. drive")
x = np.linspace(-2, 2, 4001)
fig, ax = plt.subplots(1, 3, figsize=(13, 4))
drives = [0, 25, 50, 75, 100]
ss = {"v1": [], "v2_comp": [], "v2_nocomp": []}
for dv in drives:
    # static transfer, without the DC blocker (memoryless view)
    dg = 1 + dv * 0.03
    y1 = np.tanh(x * dg) / np.sqrt(dg)
    d = dv / 100; G = 10 ** (d * 18 / 20); b = .25 * d; amt = min(d * 8, 1)
    sh = np.tanh(G * x + b) - np.tanh(b)
    s0 = G * (1 - np.tanh(b) ** 2)
    y2 = x + (sh / s0 - x) * amt
    sp = (np.tanh(G + b) - np.tanh(b - G)) / 2
    y2n = x + (sh / sp - x) * amt
    ax[0].plot(x, y1, ":", label=f"v1 {dv}%")
    ax[1].plot(x, y2, label=f"v2 comp {dv}%")
    ss["v1"].append(20 * math.log10(math.sqrt(dg)))
    ss["v2_comp"].append(20 * math.log10(1 - amt + amt * 1.0))
    ss["v2_nocomp"].append(20 * math.log10(1 - amt + amt * s0 / sp))
    ax[1].plot(x, y2n, "--", lw=.8, color=ax[1].lines[-1].get_color())
for a, t in ((ax[0], "v1: tanh(g·x)/√g"), (ax[1], "v2: solid = Unity, dashed = Peak\n(DC blocker omitted)")):
    a.plot(x, x, "k", lw=.5); a.set(xlim=(-2, 2), ylim=(-2, 2), title=t, xlabel="in", ylabel="out")
    a.legend(fontsize=6)
ax[2].plot(drives, ss["v1"], "o:", label="v1")
ax[2].plot(drives, ss["v2_comp"], "o-", label="v2 Unity")
ax[2].plot(drives, ss["v2_nocomp"], "o--", label="v2 Peak")
ax[2].set(xlabel="Drive %", ylabel="dB", title="Small-signal gain (slope at 0)")
ax[2].legend()
fig.tight_layout(); fig.savefig(f"{IMG}/drive_transfer.png"); plt.close(fig)
R["small_signal_gain_db"] = {k: [round(v, 2) for v in vs] for k, vs in ss.items()}

# THD + RMS level change for a 100 Hz sine through drive only (filter FLAT), 48 kHz
sr = 48000; n = sr
t = np.arange(n) / sr
thd = {}
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
for lvl in (-18, -6, 0):
    a = 10 ** (lvl / 20)
    sig = a * np.sin(2 * np.pi * 100 * t)
    rows = {"v1": [], "v2": [], "v1_rms": [], "v2_rms": [], "v2peak_rms": []}
    for dv in range(0, 101, 10):
        for ver in ("v1", "v2"):
            if ver == "v1":
                y, _ = run_v1(sig, sig.copy(), const(n, 0), sr, drive=dv, click=0)
            else:
                y, _ = run_v2(sig, sig.copy(), const(n, 0), const(n, 0), sr, drive=dv, click=0)
            seg = y[sr // 2:]
            Y = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
            fb = len(seg) / sr
            h = [Y[int(round(k * 100 * fb))] for k in range(1, 11)]
            rows[ver].append(100 * math.sqrt(sum(v * v for v in h[1:])) / h[0])
            rows[ver + "_rms"].append(20 * math.log10(np.sqrt(np.mean(seg ** 2)) / (a / math.sqrt(2))))
        y, _ = run_v2(sig, sig.copy(), const(n, 0), const(n, 0), sr, drive=dv, click=0, comp=0)
        seg = y[sr // 2:]
        rows["v2peak_rms"].append(20 * math.log10(np.sqrt(np.mean(seg ** 2)) / (a / math.sqrt(2))))
    thd[lvl] = rows
    ax[0].plot(range(0, 101, 10), rows["v1"], ":", marker=".", label=f"v1 {lvl} dBFS")
    ax[0].plot(range(0, 101, 10), rows["v2"], "-", marker=".", label=f"v2 {lvl} dBFS")
    ax[1].plot(range(0, 101, 10), rows["v1_rms"], ":", marker=".", label=f"v1 {lvl} dBFS")
    ax[1].plot(range(0, 101, 10), rows["v2_rms"], "-", marker=".", label=f"v2 Unity {lvl} dBFS")
    ax[1].plot(range(0, 101, 10), rows["v2peak_rms"], "--", marker="x", ms=3, label=f"v2 Peak {lvl} dBFS")
ax[0].set(xlabel="Drive %", ylabel="THD %", title="THD, 100 Hz sine, filter FLAT"); ax[0].legend(fontsize=7)
ax[1].set(xlabel="Drive %", ylabel="dB", title="Output level change vs input (RMS)"); ax[1].legend(fontsize=7)
fig.tight_layout(); fig.savefig(f"{IMG}/drive_thd_level.png"); plt.close(fig)
R["drive_thd_level"] = {str(k): {kk: [round(v, 2) for v in vv] for kk, vv in rows.items()} for k, rows in thd.items()}

# ================================================================ 3. switching transient
print("3. switching transient")
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
ck = {}
for sr in RATES:
    n = int(sr * 0.05)
    z = np.zeros(n)
    kn = const(n, 3); kn[int(sr * 0.01):] = 6
    rows = {}
    for ver in ("v1", "v2"):
        acc = []
        spec = 0
        for sd in range(20):
            if ver == "v1":
                y, _ = run_v1(z, z, kn, sr, click=100, seed=sd)
            else:
                y, _ = run_v2(z, z, kn, kn, sr, click=100, seed=sd)
            seg = y[int(sr * 0.01):int(sr * 0.03)]
            acc.append(np.sqrt(np.mean(seg ** 2)))
            if sr == 48000 or sr == 96000:
                fr = np.fft.rfftfreq(1 << 14, 1 / sr)
                spec = spec + np.abs(np.fft.rfft(seg, 1 << 14)) ** 2 / (sr * len(seg) / 2)   # PSD per Hz
        rows[ver] = float(20 * np.log10(np.mean(acc)))
        # share of audible (<20 kHz) transient energy in 16-20 kHz: should not change with rate
        fr2 = np.fft.rfftfreq(len(seg), 1 / sr)
        P = np.abs(np.fft.rfft(seg)) ** 2
        rows[ver + "_pct_16k_20k"] = float(100 * P[(fr2 > 16000) & (fr2 < 20000)].sum() / P[fr2 < 20000].sum())
        if sr in (48000, 96000):
            ax[1].semilogx(fr[1:], 10 * np.log10(spec[1:] / 20 + 1e-20), ":" if ver == "v1" else "-",
                           label=f"{ver} {sr/1000:g} kHz")
        if sr == 48000 and ver == "v2":
            ax[0].plot(np.arange(len(seg)) / sr * 1000, seg, lw=.7)
    ck[sr] = rows
ax[0].set(xlabel="ms after switch", title="v2 switch transient, Click 100 %, 48 kHz (one seed)")
ax[1].set(xlim=(50, 48000), xlabel="Hz", ylabel="dB re 1/Hz", title="Transient power spectral density (20-seed mean)")
ax[1].legend(fontsize=7)
fig.tight_layout(); fig.savefig(f"{IMG}/click.png"); plt.close(fig)
R["click_by_rate"] = {str(k): {kk: round(vv, 2) for kk, vv in v.items()} for k, v in ck.items()}

# ================================================================ 4. stability / robustness
print("4. stability")
rob = {}
rng = np.random.default_rng(0)
for sr in RATES:
    n = sr * 3
    nz = rng.uniform(-1, 1, n)
    kn = np.repeat(rng.integers(0, 12, n // int(sr * .01) + 1), int(sr * .01))[:n].astype(float)
    worst = {}
    for name, kw in {
        "Q8_18dB_drive100_peakcal": dict(reso=8, slope=1, drive=100, comp=0),
        "Q8_12dB_glide50": dict(reso=8, slope=0, glide=50),
        "Q8_dual": dict(reso=8, stereo=1),
        "Q0.5_out+12": dict(reso=.5, outdb=12),
    }.items():
        y1, y2 = run_v2(nz, -nz, kn, kn[::-1].copy(), sr, click=100, settle=False, **kw)
        worst[name] = dict(finite=bool(np.all(np.isfinite(y1)) and np.all(np.isfinite(y2))),
                           peak=float(max(abs(y1).max(), abs(y2).max())))
    # NaN / inf injection then recovery
    x = nz.copy(); x[1000:1010] = np.nan; x[2000] = np.inf
    y1, _ = run_v2(x, x, kn, kn, sr, reso=8)
    tail = y1[3000:]
    worst["nan_inf_injection"] = dict(finite=bool(np.all(np.isfinite(y1))),
                                      recovers=bool(np.std(tail) > 0.01))
    # denormals: impulse then 5 s silence must decay to exact zero
    x = np.zeros(sr * 5); x[0] = 1.0
    y1, _ = run_v2(x, x, const(len(x), 1), const(len(x), 1), sr, reso=8, click=0)
    tl = y1[-sr:]
    worst["silence_tail_below_-400dB"] = bool(np.max(np.abs(tl)) < 1e-20)
    worst["subnormals_in_output"] = int(np.sum((tl != 0) & (np.abs(tl) < np.finfo(float).tiny)))
    rob[sr] = worst
R["robustness"] = {str(k): v for k, v in rob.items()}

# ================================================================ 5. switching level jumps
print("5. switching jumps")
jumps = {}
for sr in RATES:
    n = int(sr * 0.2)
    t = np.arange(n) / sr
    s = 0.5 * np.sin(2 * np.pi * 12000 * t)       # in the passband of steps 1..9
    kn = const(n, 2); kn[n // 2:] = 7
    rows = {}
    for ver in ("v1", "v2"):
        if ver == "v1":
            y, _ = run_v1(s, s, kn, sr, click=0, drive=0)
        else:
            y, _ = run_v2(s, s, kn, kn, sr, click=0, drive=0)
        env = np.abs(signal.hilbert(y))
        a = env[int(n * .3):int(n * .45)].mean(); b = env[int(n * .7):int(n * .9)].mean()
        rows[ver] = round(float(20 * np.log10(b / a)), 3)
    # largest sample-to-sample step on a 100 Hz sine during FLAT->1k switch
    s2 = 0.5 * np.sin(2 * np.pi * 100 * t)
    k2 = const(n, 0); k2[n // 2:] = 6
    y, _ = run_v2(s2, s2, k2, k2, sr, click=0, drive=0)
    d = np.abs(np.diff(y))
    rows["v2_max_diff_switch_vs_steady"] = round(float(d[n // 2 - 5:n // 2 + int(sr * .02)].max() / d[:n // 2 - 5].max()), 3)
    y, _ = run_v1(s2, s2, k2, sr, click=0, drive=0)
    d = np.abs(np.diff(y))
    rows["v1_max_diff_switch_vs_steady"] = round(float(d[n // 2 - 5:n // 2 + int(sr * .02)].max() / d[:n // 2 - 5].max()), 3)
    y, _ = run_v2(s2, s2, k2, k2, sr, click=0, drive=0, glide=50)
    d = np.abs(np.diff(y))
    rows["v2_glide50_max_diff_switch_vs_steady"] = round(float(d[n // 2 - 5:n // 2 + int(sr * .08)].max() / d[:n // 2 - 5].max()), 3)
    jumps[sr] = rows
R["switch_level_and_discontinuity"] = {str(k): v for k, v in jumps.items()}

# ================================================================ 6. stereo
print("6. stereo")
sr = 48000; n = sr
a = rng.uniform(-.5, .5, n); b = rng.uniform(-.5, .5, n)
y1, y2 = run_v2(a, a.copy(), const(n, 6), const(n, 1), sr, stereo=0)
lk = bool(np.array_equal(y1, y2))
y1, y2 = run_v2(a, b, const(n, 6), const(n, 1), sr, stereo=0)
y1s, _ = run_v2(a, a.copy(), const(n, 6), const(n, 1), sr, stereo=0)
y2s, _ = run_v2(b, b.copy(), const(n, 6), const(n, 1), sr, stereo=0)
lk_same_path = bool(np.allclose(y1, y1s) and np.allclose(y2, y2s))
y1, y2 = run_v2(a, b, const(n, 6), const(n, 1), sr, stereo=2)
mono = bool(np.array_equal(y1, y2))
h1 = ir_v2(sr, 6)
x = np.zeros(1 << 15); x[0] = 1e-3
yl, yr = run_v2(x, x, const(len(x), 6), const(len(x), 1), sr, stereo=1, click=0)
_, mL, _ = resp(yl / 1e-3, sr); f, mR, _ = resp(yr / 1e-3, sr)
dual_fc = (float(f[np.argmin(abs(mL - (-3)) + (f < 100) * 1e9)]), float(f[np.argmin(abs(mR - (-3)) + (f < 10) * 1e9)]))
R["stereo"] = dict(linked_identical_LR=lk, linked_each_side_same_as_mono_path=lk_same_path,
                   mono_mode_L_equals_R=mono, dual_minus3dB_points_hz=dual_fc)

# ================================================================ 7. parameter smoothing
print("7. smoothing")
sm = {}
for sr in RATES:
    n = int(sr * .3)
    x = 0.5 * np.sin(2 * np.pi * 200 * np.arange(n) / sr)
    # v2 smoothers start from zero with settle=False: measure 10-90 % rise of output gain
    y, _ = run_v2(x, x, const(n, 0), const(n, 0), sr, settle=False, click=0, drive=0)
    env = np.abs(signal.hilbert(y))
    i10 = np.argmax(env > .05); i90 = np.argmax(env > .45)
    sm[sr] = round((i90 - i10) / sr * 1000, 2)
R["output_smoother_10_90_ms"] = {str(k): v for k, v in sm.items()}

# ================================================================ 8. latency + CPU proxy
print("8. latency/cpu")
h = ir_v2(48000, 0, drive=0)
R["latency_samples_flat"] = int(np.argmax(np.abs(h)))
h = ir_v2(48000, 6, drive=0)
f, m, H = resp(h, 48000)
gd = -np.gradient(np.unwrap(np.angle(H)), 2 * np.pi * f[1] - 2 * np.pi * f[0])
R["group_delay_ms_step1k_at_10k"] = round(float(gd[np.argmin(abs(f - 10000))] * 1000), 4)
cpu = {}
for sr in RATES:
    n = sr * 10
    x = rng.uniform(-.5, .5, n)
    kn = const(n, 6)
    run_v2(x[:100], x[:100], kn[:100], kn[:100], sr)   # warm JIT
    t0 = time.perf_counter(); run_v2(x, x, kn, kn, sr); dt = time.perf_counter() - t0
    cpu[sr] = dict(ns_per_stereo_sample=round(dt / n * 1e9, 1), pct_one_core=round(dt / 10 * 100, 2))
R["cpu_proxy_numba"] = {str(k): v for k, v in cpu.items()}

json.dump(R, open(os.path.join(OUT, "results.json"), "w"), indent=1)
print(json.dumps(R, indent=1))
