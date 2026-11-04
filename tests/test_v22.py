"""Tubby Filter 2.2.0-rc1 validation suite.   python3 -m pytest -q tests/test_v22.py

Environment label: [sim] — the shipped .genexpr sources executed by tools/gsx.py
(numba) on Linux. These tests are NOT native gen~ compilation and NOT Ableton Live.
Test IDs match validation/V22_TEST_RESULTS.md.
"""
import json, math, os, re, subprocess, sys, tempfile
import numpy as np
import pytest
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path[:0] = [os.path.join(ROOT, "tools"), HERE]
from gsx import compile_genexpr
import model_v22 as M22
from metrics import db, transition_artifact, fr_error, STEPS

V22SRC = os.path.join(ROOT, "src", "tubby_filter.genexpr")
V21SRC = os.path.join(ROOT, "legacy", "v2.1", "tubby_filter.genexpr")
RATES5 = [44100, 48000, 88200, 96000, 192000]
RNG = np.random.default_rng(2202)


@pytest.fixture(scope="module")
def v22():
    return compile_genexpr(open(V22SRC).read())


@pytest.fixture(scope="module")
def v21():
    return compile_genexpr(open(V21SRC).read())


def pink(sr, dur, lvl_db=-18, seed=1):
    r = np.random.default_rng(seed)
    p = signal.lfilter([0.049922035, -0.095993537, 0.050612699, -0.004408786],
                       [1, -2.494956002, 2.017265875, -0.522189400], r.standard_normal(int(dur * sr)))
    return p / np.std(p) * 10 ** (lvl_db / 20)


def drums(sr, dur, seed=3):
    """Deterministic kick/hat pattern (transients + sustained LF)."""
    r = np.random.default_rng(seed); n = int(dur * sr); out = np.zeros(n)
    for j in range(int(dur * 4)):
        i = int(j * 0.25 * sr); k = np.arange(min(int(0.2 * sr), n - i)) / sr
        out[i:i + len(k)] += 0.6 * np.sin(2 * np.pi * (50 + 90 * np.exp(-k * 35)) * k) * np.exp(-k * 9) if j % 2 == 0 else \
            0.15 * r.standard_normal(len(k)) * np.exp(-k * 80)
    return out


# ======================================================================== R: V2.1 regression (Motion 0)
def _identical(a, b):
    return np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1])


REG_CASES = {
    "R01 static cutoff, noise": lambda sr, n: (dict(knob=6, reso=1.4), RNG.uniform(-.7, .7, n), RNG.uniform(-.7, .7, n)),
    "R02 cutoff sweeps (glide 300, steps)": lambda sr, n: (dict(knob=np.repeat(RNG.integers(0, 12, n // 2000 + 1), 2000)[:n].astype(float), glide=300),
                                                     pink(sr, n / sr), pink(sr, n / sr, seed=2)),
    "R03 resonance automation": lambda sr, n: (dict(knob=7, reso=np.linspace(.5, 8, n)), pink(sr, n / sr), pink(sr, n / sr, seed=4)),
    "R04 impulse": lambda sr, n: (dict(knob=5, reso=4), np.eye(1, n, n // 4)[0] * 0.5, np.eye(1, n, n // 3)[0] * 0.5),
    "R05 step (DC) response": lambda sr, n: (dict(knob=2, reso=8), np.where(np.arange(n) > n // 4, .3, 0.), np.where(np.arange(n) > n // 3, -.3, 0.)),
    "R06 transients (drums), hard steps + click": lambda sr, n: (dict(knob=np.repeat(RNG.integers(0, 12, n // 3000 + 1), 3000)[:n].astype(float), click=80, drive=50),
                                                           drums(sr, n / sr), drums(sr, n / sr, 5)),
    "R07 gain: drive, output, mix, cal": lambda sr, n: (dict(knob=4, drive=90, comp=0, outdb=-7, blend=63), pink(sr, n / sr, -6), pink(sr, n / sr, -6, 9)),
    "R08 all controls automated": None,
}


def _storm(n):
    def rnd(lo, hi, blk):
        return np.repeat(RNG.uniform(lo, hi, n // blk + 1), blk)[:n]
    return dict(knob=rnd(0, 11, 700), knobr=rnd(0, 11, 900), reso=rnd(.5, 8, 500), drive=rnd(0, 100, 650),
                glide=rnd(0, 300, 1500), click=rnd(0, 100, 2000), slope=rnd(0, 1, 800), blend=rnd(0, 100, 1100),
                stereo=rnd(0, 2, 1300), comp=rnd(0, 1, 1200), drvonly=rnd(0, 1, 3000), outdb=rnd(-24, 12, 1000),
                active=np.where(rnd(0, 1, 9000) > 0.9, 0.0, 1.0))


@pytest.mark.parametrize("sr", RATES5)
@pytest.mark.parametrize("case", list(REG_CASES))
def test_R_motion_zero_bit_identical_to_v21(v21, v22, sr, case):
    """R01-R08: V2.2 with Motion at its default (0) is bit-identical to V2.1."""
    n = sr // 2
    if REG_CASES[case] is None:
        p, a, b = _storm(n), RNG.uniform(-1, 1, n), RNG.uniform(-1, 1, n)
    else:
        p, a, b = REG_CASES[case](sr, n)
    assert _identical(v22.run(a, b, sr, p), v21.run(a, b, sr, p))
    assert _identical(v22.run(a, b, sr, dict(p, motion=0)), v21.run(a, b, sr, p))


@pytest.mark.parametrize("sr", [44100, 96000])
def test_R09_sample_rate_change_identical(v21, v22, sr):
    n = sr
    srs = np.full(n, float(sr)); srs[n // 3:] = 48000.0; srs[2 * n // 3:] = 192000.0
    a = pink(sr, 1.0); p = dict(knob=6, reso=6, click=50)
    assert _identical(v22.run(a, a, srs, p), v21.run(a, a, srs, p))


def test_R10_motion_returned_to_zero_converges_to_v21(v21, v22):
    sr = 48000; n = 4 * sr
    a = pink(sr, 4.0); k = np.repeat(RNG.integers(1, 12, n // 2400 + 1), 2400)[:n].astype(float)
    mo = np.zeros(n); mo[:sr] = 100.0
    y22, _ = v22.run(a, a, sr, dict(knob=k, motion=mo, glide=30))
    y21, _ = v21.run(a, a, sr, dict(knob=k, glide=30))
    assert np.abs(y22[3 * sr:] - y21[3 * sr:]).max() < 1e-9         # 2 s after Motion went to 0


def test_R11_model_v22_bit_exact_with_source(v22):
    for sr in (44100, 192000):
        n = sr // 3
        a, b = RNG.uniform(-1, 1, n), RNG.uniform(-1, 1, n)
        p = _storm(n); p["motion"] = np.repeat(RNG.uniform(0, 100, n // 1700 + 1), 1700)[:n]
        assert _identical(v22.run(a, b, sr, p), M22.run(a, b, sr, **p))


# ======================================================================== M: Motion behaviour
SR = 48000


def _ring(prog, motion, t_imp, glide, k0=3, k1=9, reso=1.4):
    n = 3 * SR
    k = np.full(n, float(k0)); k[SR:] = k1
    x = np.zeros(n); x[int(t_imp * SR)] = 0.5
    y, _ = prog.run(x, x, SR, dict(knob=k, glide=glide, reso=reso, motion=motion, click=0, drive=0))
    seg = y[int(t_imp * SR) + 48:int(t_imp * SR) + int(0.2 * SR)]
    return float(db(np.sqrt(np.sum(seg ** 2))))


def _bloom(prog, glide, motion, k0=3, k1=9, reso=1.4, t=1.1):
    return _ring(prog, motion, t, glide, k0, k1, reso) - _ring(prog, 0, t, glide, k0, k1, reso)


def test_M01_slow_sweep_subtle(v22):
    """Glide 2000 ms: Motion is subtle (slow gestures barely bloom)."""
    b = _bloom(v22, 2000, 100, t=1.3)
    assert 0.0 <= b < 1.5, b


def test_M02_medium_sweep_blooms(v22):
    b = _bloom(v22, 300, 100)
    assert 2.0 < b < 8.0, b


def test_M03_fast_sweep_blooms(v22):
    b = _bloom(v22, 50, 100, t=1.02)
    assert 1.0 < b < 8.0, b


def test_M03a_bloom_increases_with_speed(v22):
    """The documented speed mapping (8 oct/s = half effect) makes faster gestures bloom more."""
    b = [_bloom(v22, g, 100, t=1.1 if g >= 300 else 1.05) for g in (2000, 1000, 300, 100)]
    assert b[0] < b[1] < b[2] < b[3], b


def test_M03b_bloom_scales_with_amount(v22):
    b50, b100 = _bloom(v22, 300, 50), _bloom(v22, 300, 100)
    assert 0 < b50 < b100


def _step_env(prog, motion, reso=1.4, k0=3, k1=6):
    n = 4 * SR
    a = pink(SR, 4.0)
    k = np.full(n, float(k0)); k[SR:] = k1
    y, _ = prog.run(a, a, SR, dict(knob=k, reso=reso, motion=motion, click=0, drive=0))
    return a, y


def test_M04_abrupt_jump_bloom_and_release(v22):
    """Hard step: audible but controlled bloom, decaying with the documented ~120 ms release."""
    _, y0 = _step_env(v22, 0); _, y1 = _step_env(v22, 100)
    win = int(0.02 * SR)
    rms = lambda s: np.sqrt(np.convolve(s ** 2, np.ones(win) / win, "same"))
    g = db(rms(y1[SR:SR + SR // 2]) / np.maximum(rms(y0[SR:SR + SR // 2]), 1e-12)).max()
    assert 2.0 < g < 6.0, g
    d = y1 - y0; fr = int(0.05 * SR)
    rel = lambda t: db(np.sqrt(np.mean(d[SR + int(t * SR):SR + int(t * SR) + fr] ** 2)) /
                       np.sqrt(np.mean(y0[SR + int(t * SR):SR + int(t * SR) + fr] ** 2)))
    assert rel(0.4) < -20 and rel(1.0) < -60 and rel(1.5) < -90


def test_M05_repeated_movements_do_not_accumulate(v22):
    n = 4 * SR
    a = pink(SR, 4.0)
    k = np.full(n, 3.0)
    for j in range(int(n / (0.15 * SR))):
        k[int(j * 0.15 * SR):int((j + 1) * 0.15 * SR)] = 3 if j % 2 == 0 else 7
    y0, _ = v22.run(a, a, SR, dict(knob=k, motion=0, click=0, drive=0))
    y1, _ = v22.run(a, a, SR, dict(knob=k, motion=100, click=0, drive=0))
    seg = slice(SR, n)
    assert db(np.sqrt(np.mean(y1[seg] ** 2)) / np.sqrt(np.mean(y0[seg] ** 2))) < 4.0
    assert db(np.abs(y1[seg]).max()) - db(np.abs(y0[seg]).max()) < 6.0
    # last second vs second second: no build-up over time
    assert abs(db(np.sqrt(np.mean(y1[3 * SR:] ** 2)) / np.sqrt(np.mean(y1[SR:2 * SR] ** 2)))) < 1.0


def test_M06_upward_and_downward_symmetric(v22):
    up = _bloom(v22, 300, 100, k0=3, k1=9)
    down = _bloom(v22, 300, 100, k0=9, k1=3)
    assert up > 2 and down > 2 and abs(up - down) < 3.0, (up, down)


@pytest.mark.parametrize("k0,k1", [(0, 1), (1, 2), (1, 0)])
def test_M07_near_minimum_cutoff(v22, k0, k1):
    n = 2 * SR
    a = drums(SR, 2.0)
    k = np.full(n, float(k0)); k[SR // 2:] = k1
    y0, _ = v22.run(a, a, SR, dict(knob=k, reso=8, motion=0, click=0))
    y1, _ = v22.run(a, a, SR, dict(knob=k, reso=8, motion=100, click=0))
    assert np.isfinite(y1).all()
    assert db(np.abs(y1).max()) - db(np.abs(y0).max()) < 6.0


@pytest.mark.parametrize("sr", [44100, 96000, 192000])
def test_M08_near_maximum_cutoff(v22, sr):
    n = 2 * sr
    a = pink(sr, 2.0, -12)
    k = np.full(n, 10.0); k[sr // 2:] = 11; k[sr:] = 10; k[3 * sr // 2:] = 11
    y0, _ = v22.run(a, a, sr, dict(knob=k, reso=8, motion=0, click=0))
    y1, _ = v22.run(a, a, sr, dict(knob=k, reso=8, motion=100, click=0))
    assert np.isfinite(y1).all() and np.abs(y1).max() <= 2.512
    assert db(np.abs(y1).max()) - db(np.abs(y0).max()) < 6.0


@pytest.mark.parametrize("reso", [4, 8])
def test_M09_high_resonance_controlled_no_self_oscillation(v22, reso):
    _, y0 = _step_env(v22, 0, reso=reso); _, y1 = _step_env(v22, 100, reso=reso)
    w = slice(SR, SR + SR // 4)
    assert db(np.abs(y1[w]).max()) - db(np.abs(y0[w]).max()) < 6.0
    # impulse after a step still rings down: no sustained oscillation
    n = 3 * SR; x = np.zeros(n); x[SR + 10] = 0.5
    k = np.full(n, 2.0); k[SR:] = 11
    y, _ = v22.run(x, x, SR, dict(knob=k, reso=reso, motion=100, click=0, drive=0))
    assert np.abs(y[2 * SR:]).max() < 1e-6


@pytest.mark.parametrize("sr", [44100, 192000])
def test_M10_rapid_automation_stable(v22, sr):
    n = sr
    a = np.clip(RNG.standard_normal(n) * 0.7, -4, 4)
    p = dict(knob=RNG.integers(0, 12, n).astype(float), motion=RNG.uniform(0, 100, n),
             reso=RNG.uniform(.5, 8, n), drive=RNG.uniform(0, 100, n), glide=0)
    y1, y2 = v22.run(a, -a, sr, p)
    assert np.isfinite(y1).all() and np.isfinite(y2).all() and np.abs(y1).max() <= 2.512


def test_M11_stationary_cutoff_unaffected_by_motion(v22):
    """No modulation at a stationary cutoff: any Motion value, even automated, is bit-identical to 0."""
    a = pink(SR, 1.0); b = pink(SR, 1.0, seed=7)
    base = v22.run(a, b, SR, dict(knob=6, reso=8, glide=500))
    for m in (100, np.linspace(0, 100, SR), RNG.uniform(0, 100, SR)):
        assert _identical(v22.run(a, b, SR, dict(knob=6, reso=8, glide=500, motion=m)), base)


def _instrument(src):
    """Expose the internal log-cutoff trajectory (nlL) and damping factor (kmL) as outputs."""
    a = "out1 = fixnan(oL);\nout2 = fixnan(oR);"
    assert a in src
    return src.replace(a, "out1 = nlL;\nout2 = kmL;")


def test_M12_cutoff_trajectory_preserved(v22):
    """Motion changes only the damping: the cutoff trajectory is bit-identical to Motion 0."""
    prog = compile_genexpr(_instrument(open(V22SRC).read()))
    n = 2 * SR
    k = np.repeat(RNG.integers(0, 12, n // 3000 + 1), 3000)[:n].astype(float)
    a = pink(SR, 2.0)
    for glide in (0, 40, 400):
        t0, km0 = prog.run(a, a, SR, dict(knob=k, glide=glide, motion=0))
        t1, km1 = prog.run(a, a, SR, dict(knob=k, glide=glide, motion=100))
        assert np.array_equal(t0, t1)
        assert np.all(km0 == 1.0) and km1.min() < 0.5 and km1.max() == 1.0


def _added_hf(y_motion, y_ref, sr, i0, ms=30):
    """Peak (dBFS) of what Motion ADDS above 3 kHz (10th-order high-pass of the difference).
    A 4th-order 3 kHz high-pass of the output is not usable here: the intended bloom at a
    1 kHz cutoff leaks through it (measured: difference energy 500-2000 Hz +4.7 dB, >3 kHz -86 dB)."""
    sos = signal.butter(10, 3000, "hp", fs=sr, output="sos")
    h = signal.sosfilt(sos, y_motion - y_ref)
    return float(db(np.abs(h[i0:i0 + int(ms * 1e-3 * sr)]).max()))


@pytest.mark.xfail(strict=True, reason="KNOWN ISSUE KI-01: with the documented 2 ms attack, Motion 100 adds "
                   "~-54 dBFS above 3 kHz on a hard step (-12 dBFS input). Meeting -70 dBFS needs a 20 ms attack, "
                   "which removes most of the hard-step bloom. Listening decision required (validation/"
                   "V22_KNOWN_ISSUES.md); the criterion is deliberately NOT relaxed.")
@pytest.mark.parametrize("sr", [44100, 96000])
def test_M13_motion_adds_no_switching_artefact(v22, sr):
    """Hard step 150 Hz -> 1 kHz on a 100 Hz sine at -12 dBFS: Motion adds no click (> 3 kHz)."""
    t = np.arange(sr) / sr
    x = 0.25 * np.sin(2 * np.pi * 100 * t)
    k = np.full(sr, 3.0); k[sr // 2:] = 6
    y0 = v22.run(x, x, sr, dict(knob=k, click=0, motion=0))[0]
    y1 = v22.run(x, x, sr, dict(knob=k, click=0, motion=100))[0]
    assert _added_hf(y1, y0, sr, sr // 2) < -70


def test_M13b_motion_step_transient_bounded_and_masked_by_default_click(v22):
    """KI-01 bound: what Motion adds above 3 kHz on a hard step stays >= 38 dB below the signal
    and >= 15 dB below the device's own default Click (30 %) transient on the same step."""
    sr = SR; t = np.arange(sr) / sr
    x = 0.25 * np.sin(2 * np.pi * 100 * t)                            # -12 dBFS
    k = np.full(sr, 3.0); k[sr // 2:] = 6
    y0 = v22.run(x, x, sr, dict(knob=k, click=0, motion=0))[0]
    y1 = v22.run(x, x, sr, dict(knob=k, click=0, motion=100))[0]
    yc = v22.run(x, x, sr, dict(knob=k, click=30, motion=0))[0]
    added = _added_hf(y1, y0, sr, sr // 2)
    click = _added_hf(yc, y0, sr, sr // 2)
    assert added < -12 - 38 and added < click - 15, (added, click)


def test_M15_motion_param_change_is_smooth(v22):
    """Turning Motion 0 -> 100 instantly while the cutoff glides adds no click (> 3 kHz).
    (The output does get louder: the bloom on a tone near the moving resonance, measured
    +9.75 dB after 50 ms; that is documented behaviour, not a discontinuity.)"""
    n = 2 * SR; t = np.arange(n) / SR
    x = 0.3 * np.sin(2 * np.pi * 300 * t)
    k = np.full(n, 3.0); k[SR // 2:] = 9
    i0 = SR // 2 + 2400
    mo = np.zeros(n); mo[i0:] = 100
    y1, _ = v22.run(x, x, SR, dict(knob=k, glide=500, motion=mo, click=0, reso=2))
    y0, _ = v22.run(x, x, SR, dict(knob=k, glide=500, motion=0, click=0, reso=2))
    assert _added_hf(y1, y0, SR, i0) < -70


SWITCHES = {"stereo Link->Dual": ("stereo", 0, 1, dict(knob=6, knobr=1)),
            "stereo Dual->Link": ("stereo", 1, 0, dict(knob=6, knobr=1)),
            "stereo Link->Mono": ("stereo", 0, 2, dict(knob=6, knobr=1)),
            "stereo Mono->Dual": ("stereo", 2, 1, dict(knob=6, knobr=1)),
            "comp Unity->Peak": ("comp", 1, 0, dict(drive=60)),
            "mode Filter->Drive": ("drvonly", 0, 1, dict(knob=6, drive=40)),
            "slope 12->18": ("slope", 0, 1, dict(knob=6))}


@pytest.mark.parametrize("sr", [44100, 96000])
@pytest.mark.parametrize("name", list(SWITCHES))
def test_M14_discrete_switches_click_free_with_motion(v22, sr, name):
    p, a, b, base = SWITCHES[name]
    t = np.arange(sr) / sr
    x = 0.25 * np.sin(2 * np.pi * 100 * t); xr = 0.25 * np.sin(2 * np.pi * 100 * t + 1.3)
    v = dict(click=30, reso=1.4, motion=100); v.update(base)
    arr = np.full(sr, float(a)); arr[sr // 2:] = b; v[p] = arr
    y1, y2 = v22.run(x, xr, sr, v)
    assert max(transition_artifact(y1, sr, 0.5)[0], transition_artifact(y2, sr, 0.5)[0]) < -70


# ======================================================================== S: stability / extremes
@pytest.mark.parametrize("sr", [44100, 96000])
def test_S01_max_resonance_all_steps_ring_down(v22, sr):
    for st in range(1, 12):
        x = np.zeros(2 * sr); x[100] = 1.0
        y, _ = v22.run(x, x, sr, dict(knob=st, reso=8, motion=100, click=0, drive=0))
        assert np.abs(y[sr:]).max() < 1e-6, st


def test_S02_silence_then_sudden_transient(v22):
    x = np.zeros(3 * SR); x[2 * SR] = 1.0; x[2 * SR + 1:2 * SR + 4800] = drums(SR, 0.1)[:4799]
    y, _ = v22.run(x, x, SR, dict(knob=6, reso=8, motion=100, drive=100, comp=0, outdb=12))
    assert np.abs(y[:2 * SR]).max() == 0.0
    assert np.isfinite(y).all() and np.abs(y).max() <= 2.512


@pytest.mark.parametrize("lvl", [0, 12, 24])
def test_S03_high_input_levels(v22, lvl):
    x = pink(SR, 1.0, lvl - 10)
    k = np.repeat(RNG.integers(0, 12, SR // 2000 + 1), 2000)[:SR].astype(float)
    y, _ = v22.run(x, x, SR, dict(knob=k, reso=8, motion=100, drive=100))
    assert np.isfinite(y).all() and np.abs(y).max() <= 2.512


def test_S04_sustained_low_frequency_no_accumulation(v22):
    sr = 48000; n = 10 * sr
    x = 0.9 * np.sin(2 * np.pi * 30 * np.arange(n) / sr)
    k = np.repeat(np.tile([1.0, 2.0], n // (2 * sr) + 1), sr)[:n]          # steps 70/100 every second
    y, _ = v22.run(x, x, sr, dict(knob=k, reso=8, motion=100, drive=80, click=0))
    assert np.isfinite(y).all()
    r = [np.sqrt(np.mean(y[j * sr:(j + 1) * sr] ** 2)) for j in range(2, 10)]
    # steps alternate each second, so compare seconds of the same step: no growth over time
    assert abs(db(r[-2] / r[0])) < 0.1 and abs(db(r[-1] / r[1])) < 0.1
    assert abs(np.mean(y[2 * sr:])) < 1e-3


def test_S05_dc_input(v22):
    dc = np.full(3 * SR, 0.5)
    y, _ = v22.run(dc, dc, SR, dict(knob=1, motion=100, drive=60))
    assert np.abs(y[-SR:]).max() < 1e-6


def test_S06_sudden_state_changes(v22):
    """All discrete controls flip at the same instant, with Motion on."""
    n = 2 * SR; a = pink(SR, 2.0, -12)
    def flip(x0, x1):
        arr = np.full(n, float(x0)); arr[SR:] = x1; return arr
    p = dict(knob=flip(2, 10), knobr=flip(8, 1), stereo=flip(0, 1), comp=flip(1, 0), drvonly=flip(0, 1),
             slope=flip(1, 0), motion=flip(0, 100), reso=flip(1.4, 8), drive=flip(10, 90))
    y1, y2 = v22.run(a, a[::-1].copy(), SR, p)
    assert np.isfinite(y1).all() and np.isfinite(y2).all() and np.abs(y1).max() <= 2.512


def test_S07_nan_inf_input(v22):
    x = pink(SR, 1.0, -12); x[1000:1010] = np.nan; x[2000] = np.inf; x[3000] = -np.inf; x[4000:4100] = 1e30
    k = np.full(SR, 3.0); k[5000:] = 9
    y1, y2 = v22.run(x, x, SR, dict(knob=k, reso=8, motion=100, drive=100))
    assert np.isfinite(y1).all() and np.isfinite(y2).all()
    assert np.std(y1[SR // 2:]) > 0.005


def test_S08_denormals(v22):
    x = np.zeros(4 * SR); x[0] = 1.0
    k = np.full(4 * SR, 2.0); k[100:] = 9
    y, _ = v22.run(x, x, SR, dict(knob=k, reso=8, motion=100, click=0))
    tl = y[-SR:]
    assert np.sum((tl != 0) & (np.abs(tl) < 2.2250738585072014e-308)) == 0 and np.abs(tl).max() < 1e-20


def test_S09_long_duration_periodic_no_drift(v22):
    """60 s at 48 kHz, a 2-s performance pattern repeated 30 times: output must not drift."""
    sr = 48000; per = 2 * sr; reps = 30; n = per * reps
    base = drums(sr, 2.0) + pink(sr, 2.0, -24)
    x = np.tile(base, reps)
    kp = np.full(per, 3.0); kp[per // 4:] = 9; kp[per // 2:] = 6; kp[3 * per // 4:] = 1
    p = dict(knob=np.tile(kp, reps), glide=120, reso=4, motion=100, drive=40, click=40)
    y1, y2 = v22.run(x, x, sr, p)
    assert np.isfinite(y1).all() and np.isfinite(y2).all()
    r = np.array([np.sqrt(np.mean(y1[j * per:(j + 1) * per] ** 2)) for j in range(reps)])
    assert np.max(np.abs(db(r[2:] / r[2]))) < 0.05            # period 3..30 identical in level
    assert abs(np.mean(y1[per:])) < 1e-3


# ======================================================================== L: latency and phase
@pytest.mark.parametrize("sr", RATES5)
def test_L01_latency_unchanged_from_v21(v21, v22, sr):
    x = np.zeros(sr // 2 + 4096); x[sr // 4] = 1.0
    for m in (0, 100):
        y22, _ = v22.run(x, x, sr, dict(knob=0, drive=0, click=0, motion=m))
        y21, _ = v21.run(x, x, sr, dict(knob=0, drive=0, click=0))
        assert np.array_equal(y22, y21)
        assert int(np.argmax(np.abs(y22))) - sr // 4 == (4 if sr < 60000 else 0)


@pytest.mark.parametrize("sr", [44100, 48000, 96000])
def test_L02_internal_dry_wet_phase_aligned(v22, sr):
    """Mix blends dry and wet inside the oversampled domain: FLAT at any Mix is magnitude-flat."""
    n = 1 << 15
    x = np.zeros(n + sr // 4); x[sr // 4] = 1.0
    for bl in (0, 30, 50, 70):
        y, _ = v22.run(x, x, sr, dict(knob=0, drive=0, click=0, blend=bl, motion=100))
        H = np.fft.rfft(y[sr // 4:]); f = np.fft.rfftfreq(n, 1 / sr)
        assert np.max(np.abs(db(H[f <= 20000]))) < 0.01


def test_L03_no_latency_declared_in_device():
    """3-sample latency declaration is NOT implemented (PDC unverified); device declares none."""
    patch = json.load(open(os.path.join(ROOT, "device", "Tubby Filter.maxpat")))["patcher"]
    assert not any("latency" in k.lower() for k in patch)


# ======================================================================== P: parameters / presets
def _params(path):
    patch = json.load(open(path))["patcher"]
    out = {}
    for b in patch["boxes"]:
        bx = b["box"]
        if "saved_attribute_attributes" in bx:
            va = bx["saved_attribute_attributes"]["valueof"]
            msg = [c["box"]["text"] for c in patch["boxes"] if c["box"].get("id") == bx["id"] + "-p"][0]
            out[va["parameter_longname"]] = (bx["maxclass"], msg, {k: v for k, v in va.items()
                                                                   if k not in ("parameter_info",)},
                                             bx["presentation_rect"])
    return out


def test_P01_all_v21_parameters_preserved():
    p21 = _params(os.path.join(ROOT, "legacy", "v2.1", "device", "Tubby Filter.maxpat"))
    p22 = _params(os.path.join(ROOT, "device", "Tubby Filter.maxpat"))
    for name, (cls, msg, va, rect) in p21.items():
        assert name in p22, name
        c2, m2, va2, r2 = p22[name]
        assert (cls, msg, va, rect) == (c2, m2, va2, r2), name      # id, class, range, default, scaling, layout
    assert set(p22) - set(p21) == {"Motion"}
    va = p22["Motion"][2]
    assert va["parameter_initial"] == [0.0] and va["parameter_mmin"] == 0.0 and va["parameter_mmax"] == 100.0


def _gen_params(src):
    return {m.group(1): m.group(2) for m in re.finditer(r"Param\s+(\w+)\(([^)]*)\)", src)}


def test_P02_gen_param_declarations_preserved():
    p21 = _gen_params(open(V21SRC).read()); p22 = _gen_params(open(V22SRC).read())
    for k, v in p21.items():
        assert p22[k] == v, k
    assert set(p22) - set(p21) == {"motion"} and p22["motion"].startswith("0,")


def test_P03_motion_dial_does_not_overlap_controls():
    patch = json.load(open(os.path.join(ROOT, "device", "Tubby Filter.maxpat")))["patcher"]
    rects = {b["box"]["id"]: b["box"]["presentation_rect"] for b in patch["boxes"]
             if "presentation_rect" in b["box"] and b["box"]["maxclass"] in ("live.dial", "live.tab")}
    mx, my, mw, mh = rects.pop("motion")
    for i, (x, y, w, h) in rects.items():
        assert mx + mw <= x or x + w <= mx or my + mh <= y or y + h <= my, i
    assert my + mh <= 169


def test_P04_v21_preset_state_loads_as_v21_sound(v21, v22):
    """A V2.1 preset/set has no 'Motion' value; Live applies the parameter's initial value (0).
    [sim]: V2.2 with every V2.1 parameter set and Motion at its initial value == V2.1."""
    patch = json.load(open(os.path.join(ROOT, "device", "Tubby Filter.maxpat")))["patcher"]
    init = [b["box"]["saved_attribute_attributes"]["valueof"]["parameter_initial"][0] for b in patch["boxes"]
            if b["box"].get("id") == "motion"][0]
    a = pink(SR, 1.0); p = dict(knob=7, reso=5, drive=70, glide=90, click=60, blend=80, outdb=-3)
    assert _identical(v22.run(a, a, SR, dict(p, motion=init)), v21.run(a, a, SR, p))


# ======================================================================== G/B: gen~ static audit and build
def test_G01_static_gen_compat_audit_clean():
    out = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "gen_compat.py"), V22SRC],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stdout


def test_G02_v21_static_issues_documented():
    """V2.1 (frozen) has the 'f'/'i' name collisions fixed in V2.2: recorded, not changed."""
    out = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "gen_compat.py"), V21SRC],
                         capture_output=True, text=True)
    assert out.returncode == 1 and "'f'" in out.stdout and "'i'" in out.stdout


def test_B01_v21_device_reproducible_and_untouched():
    pins = {l.split(maxsplit=1)[1].strip(): l.split(maxsplit=1)[0]
            for l in open(os.path.join(ROOT, "legacy", "v2.1", "SHA256")) if l.strip()}
    import hashlib
    for rel, h in pins.items():
        assert hashlib.sha256(open(os.path.join(ROOT, "legacy", "v2.1", rel), "rb").read()).hexdigest() == h, rel
    with tempfile.TemporaryDirectory() as d:
        subprocess.run([sys.executable, os.path.join(ROOT, "src", "build_device.py"), d, "--v21"], check=True,
                       capture_output=True)
        assert open(os.path.join(d, "Tubby Filter.amxd"), "rb").read() == \
            open(os.path.join(ROOT, "legacy", "v2.1", "device", "Tubby Filter.amxd"), "rb").read()


def test_B02_version_strings_consistent():
    src = open(V22SRC).read()
    man = json.load(open(os.path.join(ROOT, "device", "build_manifest.json")))
    patch = json.load(open(os.path.join(ROOT, "device", "Tubby Filter.maxpat")))["patcher"]
    assert "v2.2.0-rc1" in src and man["version"] == "2.2.0-rc1" and "2.2.0-rc1" in patch["description"]
    texts = [b["box"].get("text", "") for b in patch["boxes"]]
    assert "gen~ @title tubby_v2_2" in texts and any("v2.2" in t for t in texts)


# ======================================================================== T: validation tools
def test_T01_null_tool_reports_known_residuals(tmp_path, capsys):
    """validation/null_test.py reads synthetic nulls of known depth correctly: a copy scaled
    by 0.01 must read -40 dB (+/-0.5) in every band; a perfect null must read below -200 dB."""
    from scipy.io import wavfile
    sys.path.insert(0, os.path.join(ROOT, "validation"))
    import null_test
    sr = 44100; x = pink(sr, 3.0, -12)
    wavfile.write(tmp_path / "ref.wav", sr, x.astype(np.float32))
    wavfile.write(tmp_path / "m40.wav", sr, (0.01 * x).astype(np.float32))
    wavfile.write(tmp_path / "perfect.wav", sr, np.zeros_like(x, dtype=np.float32))
    null_test.main(str(tmp_path / "m40.wav"), str(tmp_path / "ref.wav"))
    lines = capsys.readouterr().out.splitlines()
    vals = [float(l.split(":")[1].split()[0]) for l in lines]
    assert all(abs(v + 40) < 0.5 for v in vals), vals
    null_test.main(str(tmp_path / "perfect.wav"), str(tmp_path / "ref.wav"))
    assert float(capsys.readouterr().out.splitlines()[0].split(":")[1].split()[0]) < -200


def test_T02_capture_case_C13_reference_equals_motion_zero(v22):
    sys.path.insert(0, os.path.join(ROOT, "validation"))
    from cases import CASES, SIGNALS, gen_params
    c = CASES["C13_motion100_static_cutoff"]
    a, b = SIGNALS[c["signal"]](48000)
    p, _ = gen_params(c["ui"])
    assert p["motion"] == 100
    assert _identical(v22.run(a, b, 48000, p), v22.run(a, b, 48000, dict(p, motion=0)))
