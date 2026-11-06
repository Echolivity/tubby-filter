"""V2.1 measurement report (SIMULATED: GSX execution of the shipped .genexpr sources).

Compares legacy/v2 (V2) with src/ (V2.1) on every point in the V2.1 brief.
Writes reports/measurements_v21.json and reports/img/*.png.
Nothing here is a gen~ or Ableton Live measurement.
"""
import json, math, os, sys, time
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))
from gsx import compile_genexpr
from metrics import *
from baseline_v2 import discrete_switch_tests, fr_dev, alias_table

IMG = os.path.join(ROOT, "reports", "img")
os.makedirs(IMG, exist_ok=True)
plt.rcParams.update({"figure.dpi": 110, "font.size": 9, "axes.grid": True, "grid.alpha": .3})
RATES5 = [44100, 48000, 88200, 96000, 176400, 192000]

V2 = compile_genexpr(open(os.path.join(ROOT, "legacy/v2/tubby_filter.genexpr")).read(), check_order=False)
V21 = compile_genexpr(open(os.path.join(ROOT, "src/tubby_filter.genexpr")).read())
R = {"_note": "SIMULATED: shipped .genexpr sources executed by tools/gsx.py. "
              "Not gen~ and not Ableton Live measurements."}
t_all = time.time()


def log(s):
    print(f"[{time.time() - t_all:6.1f}s] {s}", flush=True)


# ------------------------------------------------------------ A. discrete transitions
log("A. discrete transitions")
R["transitions_48k"] = {"V2": discrete_switch_tests(V2, 48000), "V2.1": discrete_switch_tests(V21, 48000)}
for sr in (44100, 96000):
    R[f"transitions_{sr // 1000}k_V2.1"] = discrete_switch_tests(V21, sr)

# rapid toggling: every 25 ms for 1 s, worst HF artefact
def rapid(prog, sr, p, vals, extra):
    n = 2 * sr
    t = np.arange(n) / sr
    x = 0.25 * np.sin(2 * np.pi * 100 * t); xr = 0.25 * np.sin(2 * np.pi * 100 * t + 1.3)
    seq = np.zeros(n)
    blk = int(0.025 * sr)
    for j in range(n // blk):
        seq[j * blk:(j + 1) * blk] = vals[j % len(vals)]
    seq[:sr // 2] = vals[0]
    v = dict(click=0, reso=1.4); v.update(extra); v[p] = seq
    y1, y2 = prog.run(x, xr, sr, v)
    sos = signal.butter(4, 3000, "hp", fs=sr, output="sos")
    # per channel (joining L and R before filtering would create a fake step)
    pk = max(np.max(np.abs(signal.sosfilt(sos, y)[sr // 2 + 100:])) for y in (y1, y2))
    return round(float(db(pk)), 1)

RAP = {"stereo 0/1/2 cycling": ("stereo", [0, 1, 2], dict(knob=6, knobr=1)),
       "comp toggling (drive 60)": ("comp", [1, 0], dict(drive=60)),
       "drive-only toggling": ("drvonly", [0, 1], dict(knob=6, drive=40)),
       "slope toggling": ("slope", [0, 1], dict(knob=6))}
R["rapid_toggle_48k"] = {k: {"V2": rapid(V2, 48000, *a), "V2.1": rapid(V21, 48000, *a)} for k, a in RAP.items()}

fig, ax = plt.subplots(figsize=(10, 4))
names = list(R["transitions_48k"]["V2"].keys())
xs = np.arange(len(names))
ax.bar(xs - .2, [R["transitions_48k"]["V2"][k]["artifact_dbfs"] for k in names], .4, label="V2")
ax.bar(xs + .2, [R["transitions_48k"]["V2.1"][k]["artifact_dbfs"] for k in names], .4, label="V2.1")
ax.axhline(-70, color="k", ls="--", lw=.8, label="acceptance (−70 dBFS)")
ax.set_xticks(xs, names, rotation=30, ha="right", fontsize=7)
ax.set(ylabel="dBFS (content >3 kHz, 30 ms after switch)", ylim=(-160, 0),
       title="Discrete-control switching artefacts, 100 Hz sine at −12 dBFS, 48 kHz (GSX)")
ax.legend(fontsize=7)
fig.tight_layout(); fig.savefig(f"{IMG}/transitions.png"); plt.close(fig)

# ------------------------------------------------------------ B. click / glide
log("B. click/glide")
def click_energy(prog, sr, glide, trigger):
    n = sr
    z = np.zeros(n)
    v = dict(click=100, glide=glide, knob=3, knobr=3)
    if trigger == "step":
        kn = np.full(n, 3.0); kn[n // 2:] = 6; v["knob"] = kn
    elif trigger == "stereo":
        st = np.zeros(n); st[n // 2:] = 1; v["stereo"] = st; v["knobr"] = 8
    elif trigger == "srchange":
        pass
    elif trigger == "load":
        pass
    if trigger == "srchange":
        srs = np.full(n, float(sr)); srs[n // 2:] = 96000 if sr != 96000 else 48000
        y1, y2 = prog.run(z, z, srs, v)
    else:
        y1, y2 = prog.run(z, z, sr, v)
    seg = slice(0, int(0.3 * sr)) if trigger == "load" else slice(n // 2, n // 2 + int(0.03 * sr))
    return round(float(db(np.sqrt(np.mean(np.concatenate([y1[seg], y2[seg]]) ** 2)))), 1)

CG = {}
for g in (0, 1, 50, 300, 2000):
    CG[f"step move, glide {g} ms"] = {"V2": click_energy(V2, 48000, g, "step"), "V2.1": click_energy(V21, 48000, g, "step")}
CG["stereo Link->Dual (knobr differs)"] = {"V2": click_energy(V2, 48000, 0, "stereo"), "V2.1": click_energy(V21, 48000, 0, "stereo")}
CG["device load with saved step 3"] = {"V2": click_energy(V2, 48000, 0, "load"), "V2.1": click_energy(V21, 48000, 0, "load")}
CG["sample-rate change 48k->96k"] = {"V2": click_energy(V2, 48000, 0, "srchange"), "V2.1": click_energy(V21, 48000, 0, "srchange")}
R["click_glide_rms_dbfs_48k_silence_in"] = CG

# rapid stepping must not stack: step every 2 ms for 200 ms
n = 48000; z = np.zeros(n)
kn = np.full(n, 1.0)
for j in range(100):
    kn[24000 + j * 96: 24000 + (j + 1) * 96] = 1 + (j % 10)
y1, _ = V21.run(z, z, 48000, dict(click=100, knob=kn))
single, _ = V21.run(z, z, 48000, dict(click=100, knob=np.where(np.arange(n) >= 24000, 5.0, 1.0)))
R["click_rapid_stepping_peak_dbfs"] = dict(rapid_2ms_steps=round(float(db(np.abs(y1).max())), 1),
                                            single_step=round(float(db(np.abs(single).max())), 1))

# ------------------------------------------------------------ C. frequency response accuracy
log("C. frequency response")
R["fr_deviation"] = {"V2": {sr: fr_dev(V2, sr) for sr in RATES5}, "V2.1": {sr: fr_dev(V21, sr) for sr in RATES5}}

fig, ax = plt.subplots(1, 2, figsize=(11, 4))
for j, (ver, ls) in enumerate((("V2", ":"), ("V2.1", "-"))):
    for sr, c in zip(RATES5, plt.cm.plasma(np.linspace(0, .85, len(RATES5)))):
        d = R["fr_deviation"][ver][sr]["worst_by_step"]
        ax[0].plot(list(d.keys()), list(d.values()), ls, marker=".", color=c,
                   label=f"{ver} {sr/1000:g}k" if True else None)
ax[0].set_xticks(range(1, 12), [f"{int(s)}" if s < 1000 else f"{s/1000:g}k" for s in STEPS[1:]], fontsize=7)
ax[0].set(yscale="log", ylabel="worst |dB| vs analog", xlabel="step (Hz)",
          title="Worst deviation per step (all Q × slopes, ≤20 kHz)")
ax[0].legend(fontsize=6, ncol=2)
xs = np.arange(len(RATES5))
ax[1].bar(xs - .2, [max(R["fr_deviation"]["V2"][s]["passband_peak"], R["fr_deviation"]["V2"][s]["skirt"]) for s in RATES5], .4, label="V2")
ax[1].bar(xs + .2, [max(R["fr_deviation"]["V2.1"][s]["passband_peak"], R["fr_deviation"]["V2.1"][s]["skirt"]) for s in RATES5], .4, label="V2.1")
ax[1].set_xticks(xs, [f"{s/1000:g}k" for s in RATES5])
ax[1].set(ylabel="worst |dB|", title="Overall worst deviation by host rate")
ax[1].legend()
fig.tight_layout(); fig.savefig(f"{IMG}/fr_accuracy.png"); plt.close(fig)

# device passband & latency with OS (FLAT, drive 0, mix 100)
def passband(prog, sr):
    n = 1 << 15
    x = np.zeros(n + sr // 4); x[sr // 4] = 1.0
    y, _ = prog.run(x, x, sr, dict(knob=0, drive=0, click=0))
    h = y[sr // 4:]
    H = np.fft.rfft(h); f = np.fft.rfftfreq(n, 1 / sr)
    gd = -np.gradient(np.unwrap(np.angle(H)), 2 * np.pi * f[1])
    sel = f <= 20000
    return dict(ripple_db_to_20k=round(float(np.max(np.abs(db(H[sel])))), 4),
                gain_db_at_20k=round(float(db(H[np.argmin(abs(f - 20000))])), 3),
                group_delay_samples_1k=round(float(gd[np.argmin(abs(f - 1000))] * sr), 3),
                group_delay_samples_10k=round(float(gd[np.argmin(abs(f - 10000))] * sr), 3),
                group_delay_samples_18k=round(float(gd[np.argmin(abs(f - 18000))] * sr), 3),
                impulse_peak_sample=int(np.argmax(np.abs(h))), f=f, H=H, gd=gd)
PB = {sr: passband(V21, sr) for sr in RATES5}
R["passband_flat_drive0_V2.1"] = {sr: {k: v for k, v in d.items() if k not in ("f", "H", "gd")} for sr, d in PB.items()}
fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
for sr in (44100, 48000, 96000):
    d = PB[sr]
    ax[0].semilogx(d["f"][1:], db(d["H"][1:]), label=f"{sr/1000:g}k")
    ax[1].semilogx(d["f"][1:], d["gd"][1:] * 1000, label=f"{sr/1000:g}k")
ax[0].set(xlim=(20, 24000), ylim=(-3, 0.5), title="V2.1 FLAT, Drive 0: magnitude", xlabel="Hz", ylabel="dB")
ax[1].set(xlim=(20, 24000), ylim=(-0.01, 0.6), title="V2.1 FLAT, Drive 0: group delay", xlabel="Hz", ylabel="ms")
for a in ax: a.legend(fontsize=7)
fig.tight_layout(); fig.savefig(f"{IMG}/os_passband.png"); plt.close(fig)

# ------------------------------------------------------------ D. drive: aliasing + character
log("D. aliasing / drive character")
R["aliasing_-6dBFS"] = {"V2": {sr: alias_table(V2, sr) for sr in (44100, 48000, 96000)},
                        "V2.1": {sr: alias_table(V21, sr) for sr in (44100, 48000, 96000)}}

fig, ax = plt.subplots(1, 3, figsize=(13, 3.8), sharey=True)
for a, sr in zip(ax, (44100, 48000, 96000)):
    keys = list(R["aliasing_-6dBFS"]["V2"][sr].keys())
    xs = np.arange(len(keys))
    a.bar(xs - .2, [R["aliasing_-6dBFS"]["V2"][sr][k]["alias_db"] for k in keys], .4, label="V2")
    a.bar(xs + .2, [R["aliasing_-6dBFS"]["V2.1"][sr][k]["alias_db"] for k in keys], .4, label="V2.1")
    a.set_xticks(xs, [k.replace("Hz drive", "k/").replace("000", "") for k in keys], rotation=60, fontsize=6)
    a.set(title=f"{sr/1000:g} kHz host", ylim=(-160, 0))
ax[0].set_ylabel("aliased energy <20 kHz re fundamental (dB)")
ax[0].legend(fontsize=7)
fig.suptitle("Aliasing, −6 dBFS sine, filter FLAT, Unity cal  (labels: tone kHz / Drive %)", fontsize=9)
fig.tight_layout(); fig.savefig(f"{IMG}/aliasing.png"); plt.close(fig)

# drive character: harmonics 2..7 of a 100 Hz tone must match V2 (in-band, no aliasing at 100 Hz)
def harmonics(prog, sr, lvl_db, dv):
    n = 1 << 16
    f0 = bin_freq(100, sr, n)
    t = np.arange(n + sr // 2) / sr
    x = 10 ** (lvl_db / 20) * np.sin(2 * np.pi * f0 * t)
    y, _ = prog.run(x, x, sr, dict(knob=0, drive=dv, click=0))
    seg = y[sr // 2:sr // 2 + n]
    Y = np.abs(np.fft.rfft(seg * signal.windows.blackmanharris(n)))
    df = sr / n
    return [float(db(Y[int(round(k * f0 / df)) - 3:int(round(k * f0 / df)) + 4].max())) for k in range(1, 8)]
CH = {}
worst = 0
for lvl in (-18, -6, 0):
    for dv in (25, 50, 100):
        a = harmonics(V2, 48000, lvl, dv); b = harmonics(V21, 48000, lvl, dv)
        dif = [round(b[i] - a[i], 3) for i in range(7)]
        CH[f"{lvl} dBFS drive {dv}"] = dif
        worst = max(worst, max(abs(d) for d, lv in zip(dif, b) if lv > -120))
R["drive_character_harmonic_diff_db_V21_minus_V2_48k"] = dict(per_case_h1_to_h7=CH, worst_abs_db=round(worst, 3))

# ------------------------------------------------------------ E. numerical stability
log("E. stability")
rng = np.random.default_rng(7)
STAB = {}
for sr in RATES5:
    n = sr
    res = {}
    nz = rng.uniform(-1, 1, n)
    # pathological inputs
    x = nz.copy(); x[1000:1010] = np.nan; x[2000] = np.inf; x[3000] = -np.inf; x[4000:4100] = 1e30
    y1, y2 = V21.run(x, x, sr, dict(knob=6, reso=8, drive=100))
    res["nan_inf_huge_input"] = dict(finite=bool(np.isfinite(y1).all() and np.isfinite(y2).all()),
                                     peak_dbfs=round(float(db(max(abs(y1).max(), abs(y2).max()))), 2),
                                     recovers=bool(np.std(y1[sr // 2:]) > 0.01))
    # denormal tail
    x = np.zeros(4 * sr); x[0] = 1.0
    y1, _ = V21.run(x, x, sr, dict(knob=1, reso=8, click=0))
    tl = y1[-sr:]
    res["silence_tail"] = dict(max_abs=float(np.abs(tl).max()),
                               subnormals=int(np.sum((tl != 0) & (np.abs(tl) < 2.2250738585072014e-308))))
    # extreme parameter corners, randomised per 5 ms
    def rnd(lo, hi, blk):
        return np.repeat(rng.choice([lo, hi], n // blk + 1), blk)[:n]
    corners = dict(knob=rnd(0, 11, 240), knobr=rnd(0, 11, 300), reso=rnd(.5, 8, 200), drive=rnd(0, 100, 260),
                   glide=rnd(0, 2000, 900), click=rnd(0, 100, 400), slope=rnd(0, 1, 330), blend=rnd(0, 100, 270),
                   stereo=rnd(0, 2, 410), comp=rnd(0, 1, 310), drvonly=rnd(0, 1, 520), outdb=rnd(-24, 12, 280))
    y1, y2 = V21.run(nz, -nz, sr, corners)
    res["param_corners_5ms"] = dict(finite=bool(np.isfinite(y1).all() and np.isfinite(y2).all()),
                                    peak_dbfs=round(float(db(max(abs(y1).max(), abs(y2).max()))), 2))
    # per-sample random automation of every parameter
    storm = {k: rng.uniform(lo, hi, n) for k, (lo, hi) in dict(
        knob=(0, 11), knobr=(0, 11), reso=(.5, 8), drive=(0, 100), glide=(0, 2000), click=(0, 100),
        slope=(0, 1), blend=(0, 100), stereo=(0, 2), comp=(0, 1), drvonly=(0, 1), outdb=(-24, 12)).items()}
    y1, y2 = V21.run(nz, nz[::-1].copy(), sr, storm)
    res["per_sample_automation"] = dict(finite=bool(np.isfinite(y1).all() and np.isfinite(y2).all()),
                                        peak_dbfs=round(float(db(max(abs(y1).max(), abs(y2).max()))), 2))
    # out-of-range values (Param clamps)
    y1, _ = V21.run(nz, nz, sr, dict(knob=1e9, reso=-5, drive=1e6, glide=-1, outdb=1e3, stereo=7))
    res["out_of_range_values"] = dict(finite=bool(np.isfinite(y1).all()), peak_dbfs=round(float(db(np.abs(y1).max())), 2))
    # DC: +0.5 DC offset, filter on and FLAT+drive
    dc = np.full(2 * sr, 0.5)
    y1, _ = V21.run(dc, dc, sr, dict(knob=1, click=0))
    y2, _ = V21.run(dc, dc, sr, dict(knob=0, drive=80, click=0))
    res["dc_in_0.5"] = dict(step70_out_after_1s=float(abs(y1[-sr // 2:]).max()),
                            flat_drive80_out_after_1s=float(abs(y2[-sr // 2:]).max()))
    STAB[sr] = res
# sample-rate change + device re-activation mid-stream
n = 3 * 48000
srs = np.concatenate([np.full(48000, 44100.), np.full(48000, 96000.), np.full(48000, 48000.)])
x = 0.5 * np.sin(2 * np.pi * 220 * np.arange(n) / 48000)
act = np.ones(n); act[30000:40000] = 0
y1, _ = V21.run(x, x, srs, dict(knob=6, reso=6, drive=60, click=100, active=act))
y1 = np.where(act > 0.5, y1, x)          # Live passes the input while the device is off
d = np.abs(np.diff(y1))
R["sr_change_and_reactivation"] = dict(finite=bool(np.isfinite(y1).all()),
                                       max_step_at_changes=[round(float(d[i - 2:i + 200].max()), 4) for i in (40000, 48000, 96000)],
                                       max_step_steady=round(float(d[20000:29000].max()), 4))
R["stability"] = STAB

# ------------------------------------------------------------ stereo / calibration / noise
log("stereo, calibration, noise")
sr = 48000; n = sr
a = rng.uniform(-.5, .5, n); z = np.zeros(n)
ST = {}
for mode in (0, 1, 2):
    y1, y2 = V21.run(a, z, sr, dict(stereo=mode, knob=6, knobr=2, click=0))
    s = sr // 2
    ST[["Link", "Dual", "Mono"][mode]] = dict(
        L_only_input_R_out_dbfs=round(float(db(np.sqrt(np.mean(y2[s:] ** 2)) + 1e-300)), 1),
        L_out_dbfs=round(float(db(np.sqrt(np.mean(y1[s:] ** 2)))), 1))
y1, y2 = V21.run(a, a, sr, dict(stereo=0, knob=6, click=30))
ST["Link identical input -> identical output"] = bool(np.array_equal(y1, y2))
y1, y2 = V21.run(a, rng.uniform(-.5, .5, n), sr, dict(stereo=2, knob=6))
ST["Mono L == R (after 10 ms start-up ramp)"] = bool(np.array_equal(y1[600:], y2[600:]))
R["stereo"] = ST

CAL = {}
for sr in (44100, 48000, 96000):
    n = sr
    f0 = 1000
    t = np.arange(n) / sr
    x = 0.01 * np.sin(2 * np.pi * f0 * t)                        # -40 dBFS
    row = {}
    for dv in (0, 50, 100):
        y, _ = V21.run(x, x, sr, dict(knob=0, drive=dv, comp=1, click=0))
        row[f"unity_small_signal_gain_db_drive{dv}"] = round(float(db(np.sqrt(np.mean(y[n // 2:] ** 2)) / (0.01 / math.sqrt(2)))), 4)
    for od in (-24, -6, 0, 12):
        y, _ = V21.run(x, x, sr, dict(knob=0, drive=0, outdb=od, click=0))
        row[f"output_{od}dB_measured"] = round(float(db(np.sqrt(np.mean(y[n // 2:] ** 2)) / (0.01 / math.sqrt(2)))), 4)
    CAL[sr] = row
R["calibration"] = CAL

NF = {}
for sr in (44100, 96000):
    z = np.zeros(2 * sr)
    y1, _ = V21.run(z, z, sr, dict(knob=6, drive=100, reso=8, click=100))
    NF[sr] = dict(silence_in_max_abs_out=float(np.abs(y1).max()))
R["noise_floor"] = NF

# ------------------------------------------------------------ CPU proxy
log("CPU proxy")
CPU = {}
for sr in RATES5:
    n = sr * 4
    x = rng.uniform(-.5, .5, n)
    row = {}
    for name, prog in (("V2", V2), ("V2.1", V21)):
        prog.run(x[:64], x[:64], sr, {})
        best = 1e9
        for _ in range(3):
            t0 = time.perf_counter(); prog.run(x, x, sr, dict(knob=6)); best = min(best, time.perf_counter() - t0)
        row[name] = dict(ns_per_stereo_frame=round(best / n * 1e9, 1), pct_core_one_instance=round(best / 4 * 100, 2))
    t0 = time.perf_counter()
    for _ in range(8):
        V21.run(x, x, sr, dict(knob=6))
    row["V2.1_8_instances_pct_core"] = round((time.perf_counter() - t0) / 4 * 100, 2)
    row["ratio_V2.1_over_V2"] = round(row["V2.1"]["ns_per_stereo_frame"] / row["V2"]["ns_per_stereo_frame"], 2)
    CPU[sr] = row
R["cpu_proxy_gsx_numba"] = CPU

json.dump(R, open(os.path.join(ROOT, "reports", "measurements_v21.json"), "w"), indent=1, default=str)
log("done")
