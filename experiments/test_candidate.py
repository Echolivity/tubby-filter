"""Tests for the V2.2 Motion candidate (EXPERIMENTAL, not the release).  pytest -q experiments
Level: [sim] — GSX execution of experiments/candidate/*.genexpr; not gen~, not Live."""
import json, os, subprocess, sys, tempfile
import numpy as np
import pytest
from scipy import signal
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path[:0] = [os.path.join(ROOT, "tools"), HERE, os.path.join(ROOT, "tests")]
from gsx import compile_genexpr
import exp_model as X
from metrics import transition_artifact, db

CAND = os.path.join(HERE, "candidate", "tubby_filter_v22_candidate.genexpr")
RNG = np.random.default_rng(77)


@pytest.fixture(scope="module")
def cand():
    return compile_genexpr(open(CAND).read())


@pytest.fixture(scope="module")
def v21():
    return compile_genexpr(open(os.path.join(ROOT, "src", "tubby_filter.genexpr")).read())


def _auto(n):
    def rnd(lo, hi, blk):
        return np.repeat(RNG.uniform(lo, hi, n // blk + 1), blk)[:n]
    return dict(knob=rnd(0, 11, 700), knobr=rnd(0, 11, 900), reso=rnd(.5, 8, 500), drive=rnd(0, 100, 650),
                glide=rnd(0, 300, 1500), click=rnd(0, 100, 2000), slope=rnd(0, 1, 800), blend=rnd(0, 100, 1100),
                stereo=rnd(0, 2, 1300), comp=rnd(0, 1, 1200), outdb=rnd(-24, 12, 1000))


@pytest.mark.parametrize("sr", [44100, 48000, 88200, 96000])
def test_motion_zero_is_v21_bit_exact(cand, v21, sr):
    n = sr // 2
    a = RNG.uniform(-1, 1, n); b = RNG.uniform(-1, 1, n)
    au = _auto(n)
    c = cand.run(a, b, sr, dict(au, motion=0)); r = v21.run(a, b, sr, au)
    assert np.array_equal(c[0], r[0]) and np.array_equal(c[1], r[1])


@pytest.mark.parametrize("sr", [44100, 96000])
@pytest.mark.parametrize("pct", [35, 100])
def test_candidate_matches_research_model(cand, sr, pct):
    n = sr // 2
    a = RNG.uniform(-1, 1, n); b = RNG.uniform(-1, 1, n)
    au = _auto(n)
    c = cand.run(a, b, sr, dict(au, motion=pct))
    x = X.run(a, b, sr, exp=dict(motion=pct * 0.01), **au)
    assert np.array_equal(c[0], x[0]) and np.array_equal(c[1], x[1])


def _ring(prog, motion, t_imp, sr=48000):
    k = np.full(3 * sr, 3.0); k[sr:] = 9
    x = np.zeros(3 * sr); x[int(t_imp * sr)] = 0.5
    y, _ = prog.run(x, x, sr, dict(knob=k, glide=300, reso=1.4, motion=motion, click=0, drive=0))
    seg = y[int(t_imp * sr) + 48:int(t_imp * sr) + 9600]
    return float(db(np.sqrt(np.sum(seg ** 2))))


def test_motion_blooms_only_while_moving(cand):
    assert _ring(cand, 100, 1.1) - _ring(cand, 0, 1.1) > 3.0       # mid-sweep: louder ring
    assert abs(_ring(cand, 100, 0.9) - _ring(cand, 0, 0.9)) < 0.01  # before the move: identical
    assert abs(_ring(cand, 100, 2.5) - _ring(cand, 0, 2.5)) < 0.05  # 1.5 s after: settled


def test_motion_leaves_no_trace_after_settling(cand):
    """Motion changes damping only while the cutoff moves; the cutoff itself is computed
    from the same glide state as V2.1 (by construction). Once settled, output matches V2.1."""
    sr = 48000
    k = np.full(3 * sr, 3.0); k[sr // 2:] = 9
    x = 0.1 * np.sin(2 * np.pi * 2000 * np.arange(3 * sr) / sr)
    y0, _ = cand.run(x, x, sr, dict(knob=k, glide=50, reso=1.4, motion=0, click=0, drive=0))
    y1, _ = cand.run(x, x, sr, dict(knob=k, glide=50, reso=1.4, motion=100, click=0, drive=0))
    # The one-pole glide approaches its target exponentially, so the cutoff speed (and with
    # it Motion's effect) decays exponentially (~40 dB per 0.5 s here) rather than stopping.
    # Criterion: below -100 dBFS from 2 s after the move.
    assert np.abs(y0[-sr // 2:] - y1[-sr // 2:]).max() < 1e-5
    assert np.abs(y0[sr // 2:sr // 2 + 4800] - y1[sr // 2:sr // 2 + 4800]).max() > 1e-3   # but differs while moving


@pytest.mark.parametrize("sr", [44100, 96000])
def test_motion_stable_at_extremes(cand, sr):
    nz = np.clip(RNG.standard_normal(sr) * 0.7, -4, 4)
    y1, y2 = cand.run(nz, -nz, sr, dict(motion=100, reso=8, drive=100, comp=0, outdb=12,
                                         knob=RNG.integers(0, 12, sr).astype(float), glide=0))
    assert np.isfinite(y1).all() and np.isfinite(y2).all() and np.abs(y1).max() <= 2.512
    x = np.zeros(2 * sr); x[100] = 0.5
    k = np.full(2 * sr, 2.0); k[50:] = 11
    y, _ = cand.run(x, x, sr, dict(motion=100, reso=8, knob=k, glide=0, click=0, drive=0))
    assert np.abs(y[sr:]).max() < 1e-6                            # still rings down: no self-oscillation


SWITCHES = {"stereo Link->Dual": ("stereo", 0, 1, dict(knob=6, knobr=1)),
            "stereo Dual->Link": ("stereo", 1, 0, dict(knob=6, knobr=1)),
            "stereo Link->Mono": ("stereo", 0, 2, dict(knob=6, knobr=1)),
            "comp Unity->Peak": ("comp", 1, 0, dict(drive=60)),
            "mode Filter->Drive": ("drvonly", 0, 1, dict(knob=6, drive=40)),
            "slope 12->18": ("slope", 0, 1, dict(knob=6))}


@pytest.mark.parametrize("name", list(SWITCHES))
def test_motion_keeps_discrete_switches_click_free(cand, name):
    sr = 48000; p, a, b, base = SWITCHES[name]
    t = np.arange(sr) / sr
    x = 0.25 * np.sin(2 * np.pi * 100 * t); xr = 0.25 * np.sin(2 * np.pi * 100 * t + 1.3)
    v = dict(click=30, reso=1.4, motion=100); v.update(base)
    arr = np.full(sr, float(a)); arr[sr // 2:] = b; v[p] = arr
    y1, y2 = cand.run(x, xr, sr, v)
    assert max(transition_artifact(y1, sr, 0.5)[0], transition_artifact(y2, sr, 0.5)[0]) < -70


def test_candidate_build_reproducible_and_release_untouched():
    rel = open(os.path.join(ROOT, "device", "Tubby Filter.amxd"), "rb").read()
    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
        outs = []
        for d in (d1, d2):
            subprocess.run([sys.executable, os.path.join(ROOT, "src", "build_device.py"), d, "--candidate", CAND],
                           check=True, capture_output=True)
            outs.append(open(os.path.join(d, "Tubby Filter.amxd"), "rb").read())
        subprocess.run([sys.executable, os.path.join(ROOT, "src", "build_device.py"), d1], check=True, capture_output=True)
        assert open(os.path.join(d1, "Tubby Filter.amxd"), "rb").read() == rel      # release build unchanged
    assert outs[0] == outs[1]
    assert outs[0] == open(os.path.join(HERE, "candidate", "device", "Tubby Filter.amxd"), "rb").read()
    assert open(CAND).read().encode() in outs[0] or json.dumps(open(CAND).read())[1:-1].encode() in outs[0]
