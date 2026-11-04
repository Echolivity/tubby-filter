"""V2.2 research experiments.  python3 experiments/run_experiments.py

All results are [ref-model]: measured on experiments/exp_model.py (the V2.1
reference model + switchable experiments). Nothing here ran in gen~ or Live,
and nothing here was listened to by the author — listening material is rendered
to experiments/renders/ for a human to judge.
Writes experiments/results.json and experiments/img/*.png.
"""
import json, math, os, sys, time
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import signal
from scipy.io import wavfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "tests"))
import exp_model as X
from metrics import db, harmonic_alias, bin_freq, analog_hp, STEPS

IMG = os.path.join(HERE, "img"); os.makedirs(IMG, exist_ok=True)
REN = os.path.join(HERE, "renders"); os.makedirs(REN, exist_ok=True)
plt.rcParams.update({"figure.dpi": 110, "font.size": 9, "axes.grid": True, "grid.alpha": .3})
RATES = [44100, 48000, 88200, 96000]
R = {"_label": "[ref-model] experiments/exp_model.py; not gen~, not Live, not listened to"}
T0 = time.time()


def log(s):
    print(f"[{time.time() - T0:6.1f}s] {s}", flush=True)


def run(x, sr, exp=None, **p):
    p.setdefault("click", 0)
    return X.run(x, x, sr, exp=exp, **p)[0]


def ir(sr, n=1 << 15, exp=None, amp=1e-3, **p):
    pre = sr // 4
    x = np.zeros(n + pre); x[pre] = amp
    return run(x, sr, exp, **p)[pre:] / amp


def sine(sr, f, lvl_db, dur):
    return 10 ** (lvl_db / 20) * np.sin(2 * np.pi * f * np.arange(int(dur * sr)) / sr)


def thd_at(sr, f, lvl, exp, **p):
    n = 1 << 15
    fb = bin_freq(f, sr, n)
    x = sine(sr, fb, lvl, n / sr + 0.5)
    y = run(x, sr, exp, **p)[-n:]
    return harmonic_alias(y, sr, fb)


# ======================================================================= P: phase
log("P. phase response")
sr = 48000
fig, ax = plt.subplots(1, 3, figsize=(14, 4))
PH = {}
for st, c in ((2, "C0"), (6, "C1"), (9, "C2")):
    for Q, ls in ((0.707, "--"), (1.4, "-"), (8.0, ":")):
        for sl in (0, 1):
            h = ir(sr, knob=st, reso=Q, slope=sl, drive=0)
            H = np.fft.rfft(h); f = np.fft.rfftfreq(len(h), 1 / sr)
            ph = np.unwrap(np.angle(H))
            gd = -np.gradient(ph, 2 * np.pi * f[1]) * 1000
            fc = STEPS[st]
            i_fc = np.argmin(abs(f - fc))
            PH[f"step{int(fc)} Q{Q} {'18' if sl else '12'}dB"] = dict(
                phase_deg_at_fc=round(float(np.degrees(ph[i_fc])), 1),
                phase_deg_at_fc_x4=round(float(np.degrees(ph[np.argmin(abs(f - 4 * fc))])), 1),
                group_delay_ms_at_fc=round(float(gd[i_fc]), 3),
                group_delay_ms_peak=round(float(gd[(f > fc / 4) & (f < 20000)].max()), 3))
            if sl == 1:
                ax[0].semilogx(f[1:], np.degrees(ph[1:]), ls, color=c, lw=1)
                ax[1].semilogx(f[1:], gd[1:], ls, color=c, lw=1)
ax[0].set(xlim=(20, 20000), title="Phase (18 dB), steps 100/1k/5k; -- Q0.707, - Q1.4, : Q8", ylabel="deg")
ax[1].set(xlim=(20, 20000), ylim=(-0.5, 12), title="Group delay (18 dB)", ylabel="ms")
# Mix 50 %: dry + HP sum
MX = {}
for st in (2, 6, 9):
    for Q in (0.707, 1.4, 8.0):
        h = ir(sr, knob=st, reso=Q, slope=1, drive=0, blend=50)
        H = np.fft.rfft(h); f = np.fft.rfftfreq(len(h), 1 / sr)
        m = db(H); sel = (f > 10) & (f < 20000)
        i = np.argmin(np.where(sel, m, 99))
        MX[f"step{int(STEPS[st])} Q{Q}"] = dict(dip_db=round(float(m[i]), 1), dip_hz=round(float(f[i]), 1),
                                                 dip_over_fc=round(float(f[i] / STEPS[st]), 3))
        if Q == 1.4:
            ax[2].semilogx(f[1:], m[1:], label=f"step {int(STEPS[st])}")
ax[2].set(xlim=(20, 20000), ylim=(-30, 6), title="Mix 50 %, Q 1.4, 18 dB: dry+HP sum", ylabel="dB")
ax[2].legend(fontsize=7)
fig.tight_layout(); fig.savefig(f"{IMG}/phase.png"); plt.close(fig)
R["phase_48k"] = PH
R["mix50_dip_48k"] = MX

# ======================================================================= X5: Butterworth / Altec mapping
log("X5. 3rd-order Butterworth mapping")
BW = {}
for sr in RATES:
    worst = 0
    for st in (1, 4, 6, 8):
        h = ir(sr, knob=st, reso=1.0, slope=1, drive=0)
        H = np.fft.rfft(h); f = np.fft.rfftfreq(len(h), 1 / sr)
        fc = STEPS[st]
        s = 1j * f / fc
        B3 = s ** 3 / ((s + 1) * (s * s + s + 1))     # 3rd-order Butterworth HP
        sel = (f > fc / 8) & (f < 18000) & (db(B3) > -40)
        worst = max(worst, float(np.max(np.abs(db(H[sel]) - db(B3[sel])))))
    BW[sr] = round(worst, 4)
R["X5_reso1_18dB_vs_butterworth3_max_db"] = BW

# ======================================================================= X1: nonlinear inductance
log("X1. nonlinear inductance")
sr = 48000
X1 = {"thd_vs_f_over_fc": {}, "thd_vs_level_at_fc": {}, "gain_at_fc_vs_level": {}}
ratios = [0.25, 0.5, 1.0, 2.0, 4.0]
fc = 500.0
cfgs = {"V2.1 drive 40": (dict(), dict(drive=40)),
        "core 1 (inductance)": (dict(core=1, cmode=0), dict(drive=0)),
        "core 1 (loss)": (dict(core=1, cmode=1), dict(drive=0)),
        "core 1 (both)": (dict(core=1, cmode=2), dict(drive=0))}
fig, ax = plt.subplots(1, 3, figsize=(14, 4))
X1["harmonic_level_dbfs_vs_f_over_fc"] = {}
for name, (ex, p) in cfgs.items():
    row = []; absrow = []
    for r_ in ratios:
        hh, _ = thd_at(sr, fc * r_, -6, ex, knob=5, reso=1.4, slope=1, **p)
        row.append(round(hh, 1))
        nn = 1 << 15; fb = bin_freq(fc * r_, sr, nn)
        yy = run(sine(sr, fb, -6, nn / sr + 0.5), sr, ex, knob=5, reso=1.4, slope=1, **p)[-nn:]
        Y = np.abs(np.fft.rfft(yy * signal.windows.blackmanharris(nn))) / (np.sum(signal.windows.blackmanharris(nn)) / 2)
        df_ = sr / nn
        hs = [Y[int(round(kk * fb / df_)) - 4:int(round(kk * fb / df_)) + 5].max() for kk in range(2, 20) if kk * fb < 20000]
        absrow.append(round(float(db(np.sqrt(np.sum(np.square(hs))))), 1))
    X1["thd_vs_f_over_fc"][name] = row
    X1["harmonic_level_dbfs_vs_f_over_fc"][name] = absrow
    ax[0].semilogx(ratios, row, "o-", label=name)
    lv = []
    for L in (-30, -18, -12, -6, 0):
        hh, _ = thd_at(sr, fc, L, ex, knob=5, reso=1.4, slope=1, **p)
        lv.append(round(hh, 1))
    X1["thd_vs_level_at_fc"][name] = lv
    ax[1].plot((-30, -18, -12, -6, 0), lv, "o-", label=name)
    gl = []
    for L in (-30, -18, -12, -6, 0):
        x = sine(sr, fc, L, 1.0)
        y = run(x, sr, ex, knob=5, reso=1.4, slope=1, **p)
        gl.append(round(float(db(np.sqrt(np.mean(y[sr // 2:] ** 2)) / (10 ** (L / 20) / math.sqrt(2)))), 2))
    X1["gain_at_fc_vs_level"][name] = gl
    ax[2].plot((-30, -18, -12, -6, 0), gl, "o-", label=name)
ax[0].set(xlabel="tone frequency / cutoff (cutoff 500 Hz)", ylabel="harmonics re fundamental (dB)",
          title="Where the distortion happens (−6 dBFS, Q 1.4)")
ax[1].set(xlabel="input level at cutoff (dBFS)", ylabel="harmonics (dB)", title="Level dependence at cutoff")
ax[2].set(xlabel="input level (dBFS)", ylabel="gain at cutoff (dB)", title="Dynamic response at cutoff")
for a in ax: a.legend(fontsize=6)
fig.tight_layout(); fig.savefig(f"{IMG}/x1_inductance.png"); plt.close(fig)
# aliasing at 44.1 and 96 with core
AL = {}
for sr in (44100, 96000):
    for ex, nm in ((dict(), "V2.1"), (dict(core=1, cmode=2), "core1")):
        h, a = thd_at(sr, 6000, -6, ex, knob=9, reso=4, slope=0, drive=0)
        AL[f"{sr} {nm}"] = dict(harm_db=round(h, 1), alias_db=round(a, 1))
X1["aliasing_6k_tone_on_5k_step_q4"] = AL
# resonance stability: Q 8, loud noise, core 1 both
rng = np.random.default_rng(3)
STB = {}
for sr in RATES:
    nz = np.clip(rng.standard_normal(sr) * 0.7, -4, 4)
    y = run(nz, sr, dict(core=1, cmode=2), knob=6, reso=8, drive=100, comp=0, outdb=12)
    kn = np.repeat(rng.integers(0, 12, sr // 200 + 1), 200)[:sr].astype(float)
    y2 = run(nz, sr, dict(core=1, cmode=0), knob=kn, reso=8, drive=100)
    STB[sr] = dict(finite=bool(np.isfinite(y).all() and np.isfinite(y2).all()),
                   peak_dbfs=round(float(db(max(abs(y).max(), abs(y2).max()))), 2))
X1["stability_q8_drive100_core1"] = STB
R["X1_inductance"] = X1

# ======================================================================= X2: movement
log("X2. movement-dependent behaviour")
sr = 48000
pink = signal.lfilter([0.049922035, -0.095993537, 0.050612699, -0.004408786],
                      [1, -2.494956002, 2.017265875, -0.522189400], rng.standard_normal(4 * sr))
pink = 0.25 * pink / np.std(pink)
X2 = {}
# (a) sweep: glide 300 ms from 150 Hz (3) to 5 kHz (9) and back; compare peakiness
n = len(pink)
kn = np.full(n, 3.0); kn[sr:2 * sr] = 9; kn[2 * sr:3 * sr] = 3; kn[3 * sr:] = 3
nper = 2048
res = {}
fig, ax = plt.subplots(1, 3, figsize=(14, 4))
for nm, ex in (("V2.1", dict()), ("motion 0.5", dict(motion=0.5)), ("motion 1", dict(motion=1))):
    y = run(pink, sr, ex, knob=kn, glide=300, reso=1.4, slope=1, drive=0)
    f, tt, S = signal.stft(y, sr, nperseg=nper)
    _, _, Sx = signal.stft(pink, sr, nperseg=nper)
    G = 20 * np.log10(np.abs(S) + 1e-12) - 20 * np.log10(np.abs(Sx) + 1e-12)
    peak = G.max(axis=0)
    res[nm] = dict(peak_gain_db_static=round(float(np.median(peak[(tt > 0.5) & (tt < 0.95)])), 2),
                   peak_gain_db_moving=round(float(np.max(peak[(tt > 1.0) & (tt < 1.5)])), 2),
                   peak_gain_db_settled=round(float(np.median(peak[(tt > 1.7) & (tt < 1.95)])), 2))
    ax[0].plot(tt, peak, label=nm)
ax[0].set(xlabel="s", ylabel="max gain over frequency (dB)", title="Resonant gain during a 300 ms glide\n150 Hz→5 kHz at 1 s, back at 2 s")
ax[0].legend(fontsize=7)
X2["sweep_peak_gain_STFT_unreliable"] = res
# deterministic: single impulse fired while static / mid-sweep / settled; ring energy and -40 dB decay
def ring(ex, t_imp, kseq, glide):
    nn = len(kseq)
    x = np.zeros(nn); x[int(t_imp * sr)] = 0.5
    y = run(x, sr, ex, knob=kseq, glide=glide, reso=1.4, slope=1, drive=0)
    seg = y[int(t_imp * sr):int(t_imp * sr) + int(0.2 * sr)]
    e = np.cumsum(seg[::-1] ** 2)[::-1]
    e = e / max(e[0], 1e-30)
    t40 = int(np.argmax(e < 1e-4)) / sr * 1000
    return {"ring_energy_db": round(float(db(np.sqrt(np.sum(seg[int(0.001 * sr):] ** 2)))), 2),
            "decay_to_-40dB_ms": round(t40, 2)}
ksw = np.full(3 * sr, 3.0); ksw[sr:] = 9
RG = {}
for nm, ex in (("V2.1", dict()), ("motion 0.5", dict(motion=0.5)), ("motion 1", dict(motion=1))):
    RG[nm] = {"static (150 Hz)": ring(ex, 0.9, ksw, 300), "mid-sweep (+100 ms)": ring(ex, 1.1, ksw, 300),
              "late sweep (+400 ms)": ring(ex, 1.4, ksw, 300), "settled (+1.5 s)": ring(ex, 2.5, ksw, 300)}
X2["impulse_ring_during_glide_150_to_5k"] = RG
# position unchanged: the cutoff trajectory (log) is identical with motion on; check via the -3 dB frequency
# of a quiet impulse probe at fixed time points is approximated by checking lf state equality:
# motion only scales k -> verify the low-Q (0.5) response-at-fc tracking with motion: identical g sequence by construction
# (b) step: ping after a hard switch with noise input (energy near new fc, 0-80 ms)
pg = {}
for nm, ex in (("V2.1", dict()), ("motion 1", dict(motion=1))):
    kn2 = np.full(n, 3.0); kn2[2 * sr:] = 6
    y = run(pink, sr, ex, knob=kn2, glide=0, reso=1.4, slope=1, drive=0)
    sos = signal.butter(2, [700, 1400], "bp", fs=sr, output="sos")
    b_ = signal.sosfilt(sos, y)
    after = np.sqrt(np.mean(b_[2 * sr:2 * sr + int(0.08 * sr)] ** 2))
    late = np.sqrt(np.mean(b_[3 * sr:3 * sr + int(0.3 * sr)] ** 2))
    pg[nm] = dict(band_rms_0_80ms_db=round(float(db(after)), 2), band_rms_settled_db=round(float(db(late)), 2),
                  bloom_db=round(float(db(after / late)), 2))
X2["step_bloom_1k_band"] = pg
# (c) rate dependence vs path dependence
def final_gain_at(f_probe, kn_seq, ex, glide):
    nn = len(kn_seq)
    x = sine(sr, f_probe, -30, nn / sr)
    y = run(x, sr, ex, knob=kn_seq, glide=glide, reso=1.4, slope=1, drive=0)
    return float(db(np.sqrt(np.mean(y[-sr // 4:] ** 2)) / (10 ** (-30 / 20) / math.sqrt(2))))
up = np.full(2 * sr, 4.0); up[sr // 2:] = 6        # 150 -> 1k (arrive from below)
dn = np.full(2 * sr, 9.0); dn[sr // 2:] = 6        # 5k -> 1k (arrive from above)
PD = {}
for nm, ex in (("V2.1", dict()), ("motion 1", dict(motion=1)), ("hysteresis 0.25 oct", dict(hyst=0.25))):
    PD[nm] = dict(arrive_from_below_db=round(final_gain_at(1000, up, ex, 50), 3),
                  arrive_from_above_db=round(final_gain_at(1000, dn, ex, 50), 3),
                  arrive_from_below_fast_db=round(final_gain_at(1000, up, ex, 0), 3),
                  arrive_from_below_slow_db=round(final_gain_at(1000, up, ex, 400), 3))
X2["rate_vs_path_dependence_gain_at_1k_after_settling"] = PD
# (d) direction weighting
DW = {}
for md in (0.0, 0.5, 1.0):
    y = run(pink, sr, dict(motion=1, mdir=md), knob=kn, glide=300, reso=1.4, slope=1, drive=0)
    f, tt, S = signal.stft(y, sr, nperseg=nper)
    _, _, Sx = signal.stft(pink, sr, nperseg=nper)
    peak = (20 * np.log10(np.abs(S) + 1e-12) - 20 * np.log10(np.abs(Sx) + 1e-12)).max(axis=0)
    DW[f"mdir {md}"] = dict(rising_peak_db=round(float(peak[(tt > 1.0) & (tt < 1.5)].max()), 2),
                            falling_peak_db=round(float(peak[(tt > 2.0) & (tt < 2.5)].max()), 2))
X2["direction_weighting"] = DW
# (e) stability: motion 1 + Q 8 + per-sample random cutoff
STM = {}
for sr_ in RATES:
    nz = np.clip(rng.standard_normal(sr_) * 0.7, -4, 4)
    y = run(nz, sr_, dict(motion=1, mdir=1), knob=rng.uniform(0, 11, sr_), reso=8, drive=100, glide=0)
    y2 = run(nz, sr_, dict(motion=1, core=1, cmode=2), knob=np.repeat(rng.integers(0, 12, sr_ // 100 + 1), 100)[:sr_].astype(float), reso=8, glide=20)
    STM[sr_] = dict(finite=bool(np.isfinite(y).all() and np.isfinite(y2).all()),
                    peak_dbfs=round(float(db(max(abs(y).max(), abs(y2).max()))), 2))
X2["stability_q8_random_cutoff"] = STM
# plot bloom spectrogram comparison
for a_, (nm, ex) in zip(ax[1:], (("V2.1", dict()), ("motion 1", dict(motion=1)))):
    y = run(pink, sr, ex, knob=kn, glide=300, reso=1.4, slope=1, drive=0)
    f, tt, S = signal.stft(y, sr, nperseg=1024)
    _, _, Sx = signal.stft(pink, sr, nperseg=1024)
    G = 20 * np.log10(np.abs(S) + 1e-12) - 20 * np.log10(np.abs(Sx) + 1e-12)
    a_.pcolormesh(tt, f, G, vmin=-30, vmax=15, shading="auto", cmap="magma")
    a_.set(yscale="log", ylim=(50, 16000), title=f"{nm}: filter gain over time (dB)", xlabel="s")
fig.tight_layout(); fig.savefig(f"{IMG}/x2_motion.png"); plt.close(fig)
R["X2_movement"] = X2

# ======================================================================= X3: contact transient
log("X3. signal-dependent switching")
sr = 48000
X3 = {}
def switch_energy(x, ex, click):
    n_ = len(x)
    k_ = np.full(n_, 3.0); k_[n_ // 2:] = 6
    y = run(x, sr, ex, knob=k_, click=click, glide=0, reso=1.4, slope=1, drive=0)
    yb = run(x, sr, dict(), knob=k_, click=0, glide=0, reso=1.4, slope=1, drive=0)
    w = slice(n_ // 2, n_ // 2 + int(0.005 * sr))
    return float(db(np.sqrt(np.mean((y[w] - yb[w]) ** 2))))     # transient added on top of V2.1 click-0
sigs = {"silence": np.zeros(sr), "60 Hz -6 dBFS": sine(sr, 60, -6, 1), "100 Hz -6 dBFS": sine(sr, 100, -6, 1), "100 Hz -24 dBFS": sine(sr, 100, -24, 1),
        "3 kHz -6 dBFS": sine(sr, 3000, -6, 1), "pink -12 dBFS": pink[:sr] * 10 ** (-12 / 20) / 0.25}
for nm, x in sigs.items():
    X3[nm] = dict(v21_click100_db=round(switch_energy(x, dict(), 100), 1),
                  gate_contact1_db=round(switch_energy(x, dict(contact=1, ctype=0), 0), 1),
                  kick_contact1_db=round(switch_energy(x, dict(contact=1, ctype=1), 0), 1))
R["X3_contact_transient_rms_5ms"] = X3

# ======================================================================= X4: vari-notch
log("X4. vari-notch")
sr = 48000
NT = {}
fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
for st in (2, 5, 8, 10):
    h = ir(sr, exp=dict(notch=1), knob=st, reso=1.4, drive=0)
    H = np.fft.rfft(h); f = np.fft.rfftfreq(len(h), 1 / sr)
    m = db(H)
    NT[int(STEPS[st])] = dict(depth_db=round(float(m[np.argmin(abs(f - STEPS[st]))]), 1),
                              phase_deg_below=round(float(np.degrees(np.angle(H[np.argmin(abs(f - STEPS[st] * 0.8))]))), 1),
                              phase_deg_above=round(float(np.degrees(np.angle(H[np.argmin(abs(f - STEPS[st] * 1.25))]))), 1))
    ax[0].semilogx(f[1:], m[1:], label=f"{int(STEPS[st])} Hz")
    ax[1].semilogx(f[1:], np.degrees(np.angle(H[1:])))
ax[0].set(xlim=(20, 20000), ylim=(-40, 3), title="X4 vari-notch magnitude (depth grows with step)")
ax[1].set(xlim=(20, 20000), title="X4 vari-notch phase (deg)")
ax[0].legend(fontsize=7)
fig.tight_layout(); fig.savefig(f"{IMG}/x4_notch.png"); plt.close(fig)
R["X4_notch"] = NT

# ======================================================================= X7: latency and parallel processing
log("X7. latency / parallel")
LT = {}
for sr in RATES:
    for latc in (0, 1):
        h = ir(sr, exp=dict(latc=latc), knob=0, drive=0, amp=1.0)
        H = np.fft.rfft(h); f = np.fft.rfftfreq(len(h), 1 / sr)
        gd = -np.gradient(np.unwrap(np.angle(H)), 2 * np.pi * f[1]) * sr
        # parallel sum with an uncompensated dry copy, and with a host compensating 3 samples
        res = {}
        for comp_s in (0, 3):
            d = np.zeros_like(h); d[comp_s] = 1.0
            S = np.fft.rfft(h - d)                  # null test: processed minus (delayed) dry
            sel = (f > 20) & (f < 20000)
            res[f"null_residual_db_max_reported{comp_s}"] = round(float(db(np.abs(S[sel])).max()), 1)
            for fq in (100, 1000, 5000, 10000, 15000):
                res[f"null_db_{fq}Hz_reported{comp_s}"] = round(float(db(np.abs(S[np.argmin(abs(f - fq))]))), 1)
        LT[f"{sr} latc{latc}"] = dict(gd_samples_1k=round(float(gd[np.argmin(abs(f - 1000))]), 2),
                                      gd_samples_10k=round(float(gd[np.argmin(abs(f - 10000))]), 2), **res)
R["X7_latency_parallel"] = LT

# ======================================================================= CPU
log("CPU benchmark")
CPU = {"hardware": "Intel Xeon @ 2.10 GHz, 2 vCPU (cloud VM), single-threaded; numba-compiled reference model. "
                   "Relative cost only — not gen~/Live CPU."}
scen = {"normal": dict(knob=6, drive=20, reso=1.4),
        "max drive": dict(knob=6, drive=100, reso=8, comp=0),
        "intensive modulation": None}
variants = {"V2.1": dict(), "X1 core": dict(core=1, cmode=2), "X2 motion": dict(motion=1),
            "X3 contact": dict(contact=1), "X1+X2+X3": dict(core=1, cmode=2, motion=1, contact=1)}
for sr in (44100, 48000, 96000):
    dur = 2
    n = sr * dur
    x = rng.uniform(-.5, .5, n)
    mod = dict(knob=np.repeat(rng.integers(0, 12, n // 64 + 1), 64)[:n].astype(float),
               drive=rng.uniform(0, 100, n), reso=rng.uniform(.5, 8, n), glide=10)
    X.run(x[:256], x[:256], sr, exp=dict(core=1), knob=1)
    for sc, p in scen.items():
        p = mod if p is None else p
        for vn, ex in variants.items():
            best = 1e9
            for _ in range(2):
                t0 = time.perf_counter(); X.run(x, x, sr, exp=ex, **p); best = min(best, time.perf_counter() - t0)
            one = best / dur * 100
            CPU[f"{sr} {sc} {vn}"] = dict(ns_per_frame=round(best / n * 1e9, 1), pct_core_1=round(one, 2),
                                          pct_core_8=round(8 * one, 1), pct_core_16=round(16 * one, 1))
R["cpu"] = CPU

# ======================================================================= listening renders
log("renders")
def dub_loop(sr, bars=4, bpm=76):
    beat = 60 / bpm; n = int(bars * 4 * beat * sr); t = np.arange(n) / sr
    out = np.zeros(n); r = np.random.default_rng(11)
    def hit(start, wave):
        i = int(start * sr); m = min(len(wave), n - i); out[i:i + m] += wave[:m]
    for b in range(bars * 4):
        tb = b * beat
        if b % 2 == 0:                                                  # kick on 1 and 3 (one drop feel)
            k = np.arange(int(0.35 * sr)) / sr
            hit(tb, 0.9 * np.sin(2 * np.pi * (45 + 80 * np.exp(-k * 30)) * k) * np.exp(-k * 7))
        if b % 4 == 2:                                                  # rim/snare on 3
            k = np.arange(int(0.2 * sr)) / sr
            hit(tb, 0.35 * (r.standard_normal(len(k)) * np.exp(-k * 25) + np.sin(2 * np.pi * 330 * k) * np.exp(-k * 30)))
        for s in range(4):                                              # 16th hats
            k = np.arange(int(0.05 * sr)) / sr
            hh = signal.lfilter([1, -1], [1, -0.6], r.standard_normal(len(k))) * np.exp(-k * 90)
            hit(tb + s * beat / 4, (0.12 if s % 2 else 0.2) * hh)
        k = np.arange(int(0.18 * sr)) / sr                              # skank on the off-beat
        chord = sum(np.sign(np.sin(2 * np.pi * fr * k)) for fr in (293.7, 349.2, 440.0)) / 3
        hit(tb + beat / 2, 0.18 * signal.lfilter([0.2], [1, -0.8], chord) * np.exp(-k * 18))
    notes = [55, 55, 65.4, 73.4, 55, 49, 55, 73.4]                    # bassline
    for j in range(bars * 8):
        k = np.arange(int(beat / 2 * sr)) / sr
        fr = notes[j % 8]
        hit(j * beat / 2, 0.45 * (np.sin(2 * np.pi * fr * k) + 0.3 * np.sin(4 * np.pi * fr * k)) * np.minimum(1, k * 60) * np.exp(-k * 2))
    return out / np.max(np.abs(out)) * 0.7
sr = 44100
loop = dub_loop(sr)
n = len(loop); beat = 60 / 76
autom = np.zeros(n)                                     # bar 1 FLAT, bar 2 rhythmic steps, bars 3-4 gliding sweep
seq = [0] * 4 + [5, 7, 5, 9] + [3, 9, 3, 9] + [9, 9, 2, 0]
for b, v in enumerate(seq):
    autom[int(b * beat * sr):int((b + 1) * beat * sr)] = v
glide = np.where(np.arange(n) < int(8 * beat * sr), 0.0, 250.0)
renders = {"A_v21": dict(), "B_core": dict(core=0.7, cmode=2), "C_motion": dict(motion=0.7),
           "D_contact_gate": dict(contact=0.8, ctype=0), "D2_contact_kick": dict(contact=0.8, ctype=1),
           "E_core_motion": dict(core=0.7, cmode=2, motion=0.7)}
ref = None
LV = {}
for nm, ex in renders.items():
    y1, y2 = X.run(loop, loop, sr, exp=ex, knob=autom, glide=glide, reso=2.5, drive=25, click=0)
    rms = np.sqrt(np.mean(y1 ** 2))
    ref = ref or rms
    g = ref / rms                                        # level-match to A_v21 (RMS)
    LV[nm] = dict(rms_dbfs_before_match=round(float(db(rms)), 2), match_gain_db=round(float(db(g)), 2))
    out = np.stack([y1 * g, y2 * g], 1)
    wavfile.write(os.path.join(REN, f"{nm}.wav"), sr, (np.clip(out, -1, 1) * 32767).astype(np.int16))
R["renders_level_match"] = LV

json.dump(R, open(os.path.join(HERE, "results.json"), "w"), indent=1, default=str)
log("done")
