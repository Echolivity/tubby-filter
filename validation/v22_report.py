"""Generate the 2.2.0-rc1 measurement data, plots and audio.   python3 validation/v22_report.py

Everything here is [sim]: the shipped .genexpr sources (src/ = V2.2, legacy/v2.1 = V2.1,
experiments/candidate = research candidate) executed by tools/gsx.py on Linux.
No audio was listened to; files in reports/v22/audio are for a human listener.
Outputs: reports/v22/v22_measurements.json, reports/v22/img/*.png, reports/v22/audio/*.wav
"""
import json, math, os, sys, time
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import signal
from scipy.io import wavfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path[:0] = [os.path.join(ROOT, "tools"), os.path.join(ROOT, "tests")]
from gsx import compile_genexpr
from metrics import db, fr_error, STEPS, analog_hp

OUT = os.path.join(ROOT, "reports", "v22"); IMG = os.path.join(OUT, "img"); AUD = os.path.join(OUT, "audio")
for d in (OUT, IMG, AUD):
    os.makedirs(d, exist_ok=True)
plt.rcParams.update({"figure.dpi": 110, "font.size": 9, "axes.grid": True, "grid.alpha": .3})
V22 = compile_genexpr(open(os.path.join(ROOT, "src", "tubby_filter.genexpr")).read())
V21 = compile_genexpr(open(os.path.join(ROOT, "legacy", "v2.1", "tubby_filter.genexpr")).read())
CAND = compile_genexpr(open(os.path.join(ROOT, "experiments", "candidate", "tubby_filter_v22_candidate.genexpr")).read())
RATES = [44100, 48000, 88200, 96000, 192000]
R = {"_environment": "[sim] GSX execution of the shipped .genexpr sources (numba), Ubuntu 24.04, Python 3.13; "
                     "not native gen~, not Ableton Live; no audio was listened to"}
T0 = time.time()
rng = np.random.default_rng(22)


def log(s):
    print(f"[{time.time() - T0:6.1f}s] {s}", flush=True)


def pink(sr, dur, lvl=-18, seed=1):
    r = np.random.default_rng(seed)
    p = signal.lfilter([0.049922035, -0.095993537, 0.050612699, -0.004408786],
                       [1, -2.494956002, 2.017265875, -0.522189400], r.standard_normal(int(dur * sr)))
    return p / np.std(p) * 10 ** (lvl / 20)


def dub_loop(sr, bars=4, bpm=76, seed=11):
    beat = 60 / bpm; n = int(bars * 4 * beat * sr); out = np.zeros(n); r = np.random.default_rng(seed)
    def hit(start, wave):
        i = int(start * sr); m = min(len(wave), n - i)
        if m > 0:
            out[i:i + m] += wave[:m]
    for b in range(bars * 4):
        tb = b * beat
        if b % 2 == 0:
            k = np.arange(int(0.35 * sr)) / sr
            hit(tb, 0.9 * np.sin(2 * np.pi * (45 + 80 * np.exp(-k * 30)) * k) * np.exp(-k * 7))
        if b % 4 == 2:
            k = np.arange(int(0.2 * sr)) / sr
            hit(tb, 0.35 * (r.standard_normal(len(k)) * np.exp(-k * 25) + np.sin(2 * np.pi * 330 * k) * np.exp(-k * 30)))
        for s in range(4):
            k = np.arange(int(0.05 * sr)) / sr
            hh = signal.lfilter([1, -1], [1, -0.6], r.standard_normal(len(k))) * np.exp(-k * 90)
            hit(tb + s * beat / 4, (0.12 if s % 2 else 0.2) * hh)
        k = np.arange(int(0.18 * sr)) / sr
        chord = sum(np.sign(np.sin(2 * np.pi * fr * k)) for fr in (293.7, 349.2, 440.0)) / 3
        hit(tb + beat / 2, 0.18 * signal.lfilter([0.2], [1, -0.8], chord) * np.exp(-k * 18))
    notes = [55, 55, 65.4, 73.4, 55, 49, 55, 73.4]
    for j in range(bars * 8):
        k = np.arange(int(beat / 2 * sr)) / sr; fr = notes[j % 8]
        hit(j * beat / 2, 0.45 * (np.sin(2 * np.pi * fr * k) + 0.3 * np.sin(4 * np.pi * fr * k)) * np.minimum(1, k * 60) * np.exp(-k * 2))
    return out / np.max(np.abs(out)) * 0.7, beat


def wav(name, sr, l, r=None):
    r = l if r is None else r
    wavfile.write(os.path.join(AUD, name), sr, np.stack([l, r], 1).astype(np.float32))


# ===================================================================== 1. V2.1 vs V2.2 (Motion 0)
log("1. regression V2.1 vs V2.2 Motion 0")
REG = {}
def cases(sr, n):
    k = np.repeat(rng.integers(0, 12, n // 2000 + 1), 2000)[:n].astype(float)
    imp = np.zeros(n); imp[n // 4] = 0.5
    stp = np.where(np.arange(n) > n // 4, 0.3, 0.0)
    loop, _ = dub_loop(sr, 1)
    loop = np.resize(loop, n)
    return {"static cutoff (1 kHz, Q 1.4, pink)": (dict(knob=6), pink(sr, n / sr)),
            "cutoff sweeps (random steps, glide 300)": (dict(knob=k, glide=300), pink(sr, n / sr)),
            "resonance sweep 0.5->8": (dict(knob=7, reso=np.linspace(.5, 8, n)), pink(sr, n / sr)),
            "impulse (500 Hz, Q 4)": (dict(knob=5, reso=4), imp),
            "step response (100 Hz, Q 8)": (dict(knob=2, reso=8), stp),
            "transients (dub loop, hard steps, click 80)": (dict(knob=k, click=80, drive=50), loop),
            "gain (drive 90 Peak, out -7, mix 63)": (dict(knob=4, drive=90, comp=0, outdb=-7, blend=63), pink(sr, n / sr, -6))}
for sr in RATES:
    n = sr
    for nm, (p, x) in cases(sr, n).items():
        a1, a2 = V21.run(x, x[::-1].copy(), sr, p)
        b1, b2 = V22.run(x, x[::-1].copy(), sr, p)
        d = np.concatenate([b1 - a1, b2 - a2])
        D = np.abs(np.fft.rfft(b1 - a1))
        REG[f"{sr} | {nm}"] = dict(bit_identical=bool(np.array_equal(a1, b1) and np.array_equal(a2, b2)),
                                   rms_error=float(np.sqrt(np.mean(d ** 2))), peak_error=float(np.abs(d).max()),
                                   residual_dbfs=float(db(np.abs(d).max())),
                                   max_spectral_difference=float(D.max()))
R["regression_v21_vs_v22_motion0"] = REG
R["regression_summary"] = dict(cases=len(REG), bit_identical=sum(v["bit_identical"] for v in REG.values()),
                               max_peak_error=max(v["peak_error"] for v in REG.values()))

# ===================================================================== 2. frequency response (V2.2 == V2.1)
log("2. frequency response")
FR = {}
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
for sr in RATES:
    n = 1 << 15 if sr <= 96000 else 1 << 16
    x = np.zeros(n + sr // 4); x[sr // 4] = 1e-3
    worst = 0; same = True
    for st in range(1, 12):
        for sl in (0, 1):
            for Q in (0.707, 1.4, 8.0):
                pp = dict(knob=st, reso=Q, slope=sl, drive=0, click=0)
                y22 = V22.run(x, x, sr, dict(pp, motion=100))[0][sr // 4:] / 1e-3   # Motion 100, static
                y21 = V21.run(x, x, sr, pp)[0][sr // 4:] / 1e-3
                same &= bool(np.array_equal(y22, y21))
                f = np.fft.rfftfreq(len(y22), 1 / sr); H = np.fft.rfft(y22)
                worst = max(worst, *fr_error(f, H, STEPS[st], Q, sl, min(20000, 0.4 * sr)))
                if sr == 48000 and sl == 1 and Q == 1.4:
                    ax[0].semilogx(f[1:], db(H[1:]), lw=1)
                    ax[1].semilogx(f[1:], np.degrees(np.unwrap(np.angle(H)))[1:], lw=.8)
    FR[sr] = dict(worst_dev_vs_analog_db=round(worst, 3), static_response_identical_to_v21_at_motion100=same)
ax[0].set(xlim=(20, 24000), ylim=(-60, 8), title="V2.2 (= V2.1) magnitude, 18 dB, Q 1.4, 48 kHz", xlabel="Hz", ylabel="dB")
ax[1].set(xlim=(20, 24000), title="phase (deg, unwrapped)", xlabel="Hz")
fig.tight_layout(); fig.savefig(f"{IMG}/frequency_response.png"); plt.close(fig)
R["frequency_response"] = FR

# ===================================================================== 3. Motion
log("3. Motion")
SR = 48000
def ring(prog, motion, t_imp, glide, k0=3, k1=9, reso=1.4):
    n = 3 * SR; k = np.full(n, float(k0)); k[SR:] = k1
    x = np.zeros(n); x[int(t_imp * SR)] = 0.5
    y, _ = prog.run(x, x, SR, dict(knob=k, glide=glide, reso=reso, motion=motion, click=0, drive=0))
    seg = y[int(t_imp * SR) + 48:int(t_imp * SR) + int(0.2 * SR)]
    return float(db(np.sqrt(np.sum(seg ** 2))))
MO = {"speed": {}}
for g, t in ((2000, 1.1), (1000, 1.1), (300, 1.1), (100, 1.05), (50, 1.02), (20, 1.01)):
    MO["speed"][f"glide {g} ms"] = {f"motion {m}": round(ring(V22, m, t, g) - ring(V22, 0, t, g), 2) for m in (25, 50, 100)}
MO["direction"] = {"up 150->5k": round(ring(V22, 100, 1.1, 300) - ring(V22, 0, 1.1, 300), 2),
                   "down 5k->150": round(ring(V22, 100, 1.1, 300, 9, 3) - ring(V22, 0, 1.1, 300, 9, 3), 2)}
MO["near_min"] = {"FLAT->70": round(ring(V22, 100, 1.05, 50, 0, 1, 8) - ring(V22, 0, 1.05, 50, 0, 1, 8), 2),
                  "70->100": round(ring(V22, 100, 1.05, 50, 1, 2, 8) - ring(V22, 0, 1.05, 50, 1, 2, 8), 2)}
MO["near_max"] = {"7.5k->10k": round(ring(V22, 100, 1.02, 50, 10, 11, 8) - ring(V22, 0, 1.02, 50, 10, 11, 8), 2)}
# hard steps on pink: bloom, peak and release, before (candidate) and after (rc1) the fix
n = 4 * SR; pk = pink(SR, 4.0); k = np.full(n, 3.0); k[SR:] = 6
win = int(0.02 * SR)
def rms(s): return np.sqrt(np.convolve(s ** 2, np.ones(win) / win, "same"))
STEP = {}
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
for prog, nm, ls in ((CAND, "research candidate (pre-fix)", ":"), (V22, "2.2.0-rc1", "-")):
    for reso, c in ((1.4, "C0"), (4, "C1"), (8, "C3")):
        y0, _ = prog.run(pk, pk, SR, dict(knob=k, reso=reso, motion=0, click=0, drive=0))
        y1, _ = prog.run(pk, pk, SR, dict(knob=k, reso=reso, motion=100, click=0, drive=0))
        g = db(rms(y1[SR:SR + SR // 2]) / np.maximum(rms(y0[SR:SR + SR // 2]), 1e-12))
        d = y1 - y0; fr = int(0.05 * SR)
        rel = {t: round(float(db(np.sqrt(np.mean(d[SR + int(t * SR):SR + int(t * SR) + fr] ** 2)) /
                                 np.sqrt(np.mean(y0[SR + int(t * SR):SR + int(t * SR) + fr] ** 2)))), 1)
               for t in (0.0, 0.1, 0.2, 0.3, 0.4, 0.6, 1.0, 1.5)}
        STEP[f"{nm} | Reso {reso}"] = dict(peak_gain_db=round(float(db(np.abs(y1[SR:SR + SR // 4]).max()) - db(np.abs(y0[SR:SR + SR // 4]).max())), 2),
                                            rms20ms_max_gain_db=round(float(g.max()), 2),
                                            bloom_residual_db_re_output=rel)
        ts = np.array(list(rel.keys())); ax[0].plot(ts * 1000, list(rel.values()), ls, marker=".", color=c,
                                                     label=f"{nm.split(' (')[0]}, Reso {reso}")
    if prog is V22:
        ax[1].plot(np.arange(SR // 2) / SR * 1000, g, color="C3", label="rc1 Reso 8")
ax[0].axhline(-20, color="k", lw=.5); ax[0].set(xlabel="ms after hard step", ylabel="dB", ylim=(-110, 10),
                                               title="Motion 100: bloom (difference from Motion 0) re output")
ax[0].legend(fontsize=6)
ax[1].set(xlabel="ms after step", ylabel="dB", title="rc1: 20 ms loudness gain vs Motion 0 (Reso 8)")
fig.tight_layout(); fig.savefig(f"{IMG}/motion_step_release.png"); plt.close(fig)
MO["hard_step_pink_-18dBFS"] = STEP
# repeated movements and output gain
k = np.full(n, 3.0)
for j in range(int(n / (0.15 * SR))):
    k[int(j * 0.15 * SR):int((j + 1) * 0.15 * SR)] = 3 if j % 2 == 0 else 7
y0, _ = V22.run(pk, pk, SR, dict(knob=k, motion=0, click=0, drive=0))
y1, _ = V22.run(pk, pk, SR, dict(knob=k, motion=100, click=0, drive=0))
MO["repeated_steps_every_150ms"] = dict(rms_gain_db=round(float(db(np.sqrt(np.mean(y1[SR:] ** 2)) / np.sqrt(np.mean(y0[SR:] ** 2)))), 2),
                                        peak_gain_db=round(float(db(np.abs(y1[SR:]).max()) - db(np.abs(y0[SR:]).max())), 2),
                                        level_last_vs_second_second_db=round(float(db(np.sqrt(np.mean(y1[3 * SR:] ** 2)) / np.sqrt(np.mean(y1[SR:2 * SR] ** 2)))), 2))
# spectrogram of a sweep
k = np.full(n, 3.0); k[SR:] = 9; k[2 * SR:] = 3
fig, ax = plt.subplots(1, 3, figsize=(14, 3.8))
for a_, m in zip(ax, (0, 50, 100)):
    y, _ = V22.run(pk, pk, SR, dict(knob=k, glide=300, reso=1.4, motion=m, click=0, drive=0))
    f, tt, S = signal.stft(y, SR, nperseg=1024); _, _, Sx = signal.stft(pk, SR, nperseg=1024)
    a_.pcolormesh(tt, f, 20 * np.log10(np.abs(S) + 1e-12) - 20 * np.log10(np.abs(Sx) + 1e-12),
                  vmin=-30, vmax=15, shading="auto", cmap="magma")
    a_.set(yscale="log", ylim=(50, 16000), title=f"Motion {m}: filter gain over time (dB)", xlabel="s")
fig.tight_layout(); fig.savefig(f"{IMG}/motion_sweep_spectrogram.png"); plt.close(fig)
R["motion"] = MO

# ===================================================================== 4. stability summary
log("4. stability")
ST = {}
for sr in (44100, 48000, 96000, 192000):
    nz = np.clip(rng.standard_normal(sr) * 0.7, -4, 4)
    storm = dict(knob=rng.integers(0, 12, sr).astype(float), motion=rng.uniform(0, 100, sr), reso=rng.uniform(.5, 8, sr),
                 drive=rng.uniform(0, 100, sr), stereo=rng.uniform(0, 2, sr), comp=rng.uniform(0, 1, sr), glide=0)
    y1, y2 = V22.run(nz, -nz, sr, storm)
    x = nz.copy(); x[100:110] = np.nan; x[300] = np.inf; x[500:520] = 1e30
    z1, _ = V22.run(x, x, sr, dict(knob=6, reso=8, motion=100, drive=100))
    ST[sr] = dict(per_sample_random_all_controls=dict(finite=bool(np.isfinite(y1).all() and np.isfinite(y2).all()),
                                                       peak_dbfs=round(float(db(max(abs(y1).max(), abs(y2).max()))), 2)),
                  nan_inf_huge_input=dict(finite=bool(np.isfinite(z1).all()), peak_dbfs=round(float(db(abs(z1).max())), 2)))
R["stability"] = ST

# ===================================================================== 5. latency and phase
log("5. latency / phase")
from halfband import response as hb_response
c = [0.04063346092419326, 0.1505051290226746, 0.3007570559918741, 0.4607745049614506,
     0.6095243148961883, 0.7385038411188573, 0.8492238103920661, 0.9497427837050002]
LT = {}
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
for sr in RATES:
    nn = 1 << 15
    x = np.zeros(nn + sr // 4); x[sr // 4] = 1.0
    h, _ = V22.run(x, x, sr, dict(knob=0, drive=0, click=0))
    h = h[sr // 4:]
    H = np.fft.rfft(h); f = np.fft.rfftfreq(nn, 1 / sr)
    gd = -np.gradient(np.unwrap(np.angle(H)), 2 * np.pi * f[1]) * sr
    row = dict(impulse_peak_sample=int(np.argmax(np.abs(h))),
               group_delay_samples={str(q): round(float(gd[np.argmin(abs(f - q))]), 3) for q in (20, 100, 1000, 5000, 10000, 15000, 18000)})
    for comp in (0, 1, 2, 3, 4):
        dd = np.zeros_like(h); dd[comp] = 1.0
        S = np.fft.rfft(h - dd)
        row[f"null_vs_dry_delayed_{comp}"] = {str(q): round(float(db(np.abs(S[np.argmin(abs(f - q))]))), 1)
                                               for q in (100, 1000, 3000, 5000, 10000, 15000)}
    LT[sr] = row
    if sr in (44100, 48000, 96000):
        ax[0].semilogx(f[1:], gd[1:], label=f"{sr/1000:g} kHz")
        for comp, ls in ((0, ":"), (3, "-")):
            dd = np.zeros_like(h); dd[comp] = 1.0
            ax[1].semilogx(f[1:], db(np.fft.rfft(h - dd))[1:], ls, label=f"{sr/1000:g}k, dry delayed {comp}")
# analytic DC group delay of up+down half-band chain (in host samples)
w = np.array([1e-6, 2 * np.pi * 1000 / 88200])
LT["analytic"] = "IIR half-band group delay is frequency dependent; no integer latency nulls the full band"
ax[0].set(xlim=(20, 24000), ylim=(-1, 12), xlabel="Hz", ylabel="samples", title="V2.2 group delay, FLAT, Drive 0")
ax[1].set(xlim=(20, 24000), ylim=(-80, 10), xlabel="Hz", ylabel="dB", title="Null test vs dry copy (0 vs 3-sample delay)")
for a_ in ax: a_.legend(fontsize=6)
fig.tight_layout(); fig.savefig(f"{IMG}/latency_phase.png"); plt.close(fig)
# best integer delay per band at 44.1
best = {}
for band in ((20, 500), (500, 2000), (2000, 8000), (8000, 18000)):
    nn = 1 << 15; x = np.zeros(nn + 44100 // 4); x[44100 // 4] = 1.0
    h, _ = V22.run(x, x, 44100, dict(knob=0, drive=0, click=0)); h = h[44100 // 4:]
    f = np.fft.rfftfreq(nn, 1 / 44100); sel = (f >= band[0]) & (f < band[1])
    errs = {}
    for comp in range(0, 13):
        dd = np.zeros_like(h); dd[comp] = 1.0
        errs[comp] = float(np.sqrt(np.mean(np.abs(np.fft.rfft(h - dd))[sel] ** 2)))
    bc = min(errs, key=errs.get)
    best[f"{band[0]}-{band[1]} Hz"] = dict(best_integer_delay=bc, residual_db=round(float(db(errs[bc])), 1))
LT["best_integer_delay_per_band_44k1"] = best
R["latency_phase"] = LT

# ===================================================================== 6. audio
log("6. audio")
AUDIO = {}
sr = 48000
loop, beat = dub_loop(sr, 8)
nL = len(loop)
seq = [0] * 4 + [5, 7, 5, 9] + [3, 9, 3, 9] + [9, 9, 2, 0] + [0] * 4 + [6, 0, 6, 0] + [2, 5, 8, 11] + [11, 6, 3, 0]
autom = np.zeros(nL)
for b, v in enumerate(seq):
    autom[int(b * beat * sr):int((b + 1) * beat * sr)] = v
glide = np.where(np.arange(nL) < int(8 * beat * sr), 0.0, np.where(np.arange(nL) < int(16 * beat * sr), 250.0, 0.0))
base = dict(knob=autom, glide=glide, reso=2.5, drive=25, click=0)
wav("ref_dry_dub_loop_48k.wav", sr, loop)
v21o = V21.run(loop, loop, sr, base); v22o = V22.run(loop, loop, sr, dict(base, motion=0))
wav("ref_v21_dub_loop_48k.wav", sr, *v21o); wav("ref_v22_motion0_dub_loop_48k.wav", sr, *v22o)
wav("null_v22_motion0_minus_v21_48k.wav", sr, v22o[0] - v21o[0], v22o[1] - v21o[1])
AUDIO["null_v22_motion0_minus_v21 peak"] = float(np.abs(v22o[0] - v21o[0]).max())
for m in (50, 100):
    y = V22.run(loop, loop, sr, dict(base, motion=m))
    wav(f"demo_motion{m:03d}_dub_loop_48k.wav", sr, *y)
    g = np.sqrt(np.mean(v21o[0] ** 2)) / np.sqrt(np.mean(y[0] ** 2))
    wav(f"demo_motion{m:03d}_dub_loop_48k_levelmatched.wav", sr, y[0] * g, y[1] * g)
    AUDIO[f"motion {m} level-match gain db"] = round(float(db(g)), 2)
# focused demos: sweeps on pink, hard steps on drums, high resonance
pk = pink(sr, 8.0, -18, seed=5)
k = np.full(len(pk), 3.0)
for j, v in enumerate([3, 9, 3, 9, 6, 1, 10, 3]):
    k[j * sr:(j + 1) * sr] = v
for m in (0, 100):
    wav(f"demo_sweeps_pink_glide300_motion{m:03d}.wav", sr, *V22.run(pk, pk, sr, dict(knob=k, glide=300, reso=1.4, motion=m, click=0)))
    wav(f"demo_hardsteps_loop_reso6_motion{m:03d}.wav", sr,
        *V22.run(loop[:8 * sr], loop[:8 * sr], sr, dict(knob=k, glide=0, reso=6, motion=m, click=30)))
R["audio"] = AUDIO
json.dump(R, open(os.path.join(OUT, "v22_measurements.json"), "w"), indent=1, default=str)
log("done")
