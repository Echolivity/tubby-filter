"""Automated regression tests for Tubby Filter V2.1.   Run:  python3 -m pytest -q tests

What these tests can prove:   the shipped .genexpr source (executed by tools/gsx.py)
matches the independent reference model, keeps V2's sound where intended, and
meets the V2.1 acceptance thresholds; the device files are reproducibly built
and structurally valid.
What they cannot prove:       anything about Cycling '74's gen~ compiler or Ableton
Live. Those are covered by validation/ (manual / capture-based).
"""
import hashlib, json, math, os, struct, subprocess, sys, tempfile
import numpy as np
import pytest
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from gsx import compile_genexpr, SemanticsError
import model_v21 as M
from metrics import transition_artifact, fr_error, STEPS, db

# Target under test. Default: the V2.2 release candidate (Motion at its default 0,
# so every V2.1 behaviour assertion below must still hold). TUBBY_TARGET=v2.1 runs
# the identical suite against the frozen V2.1 baseline in legacy/v2.1.
TARGET = os.environ.get("TUBBY_TARGET", "v2.2")
assert TARGET in ("v2.1", "v2.2"), TARGET
if TARGET == "v2.1":
    SRC = os.path.join(ROOT, "legacy", "v2.1", "tubby_filter.genexpr")
    DEV = os.path.join(ROOT, "legacy", "v2.1", "device")
    BUILD_FLAGS = ["--v21"]
else:
    SRC = os.path.join(ROOT, "src", "tubby_filter.genexpr")
    DEV = os.path.join(ROOT, "device")
    BUILD_FLAGS = []
V2SRC = os.path.join(ROOT, "legacy", "v2", "tubby_filter.genexpr")


@pytest.fixture(scope="session")
def v21():
    return compile_genexpr(open(SRC).read())


@pytest.fixture(scope="session")
def v2():
    # V2 with its known init-constant discrepancy corrected, so only intended changes remain
    s = open(V2SRC).read().replace("History lfL(2.9957), lfR(2.9957)",
                                   "History lfL(2.995732273553991), lfR(2.995732273553991)")
    return compile_genexpr(s)


RNG = np.random.default_rng(1234)


# ---------------------------------------------------------------- source / semantics
def test_v2_source_untouched():
    h = hashlib.sha256(open(V2SRC, "rb").read()).hexdigest()
    pinned = open(os.path.join(ROOT, "legacy", "v2", "SHA256")).read().split()[0]
    assert h == pinned


def test_history_lint_rejects_read_after_write():
    bad = "History h(0);\nh = in1;\nout1 = h;\nout2 = 0;\n"
    with pytest.raises(SemanticsError):
        compile_genexpr(bad)


def test_v21_source_passes_lint(v21):
    assert set(v21.params) >= {"knob", "reso", "drive", "glide", "click", "slope", "blend",
                               "knobr", "stereo", "comp", "drvonly", "outdb", "active"}


# ---------------------------------------------------------------- model vs shipped source
@pytest.mark.parametrize("sr", [44100, 96000])
def test_model_matches_source_bit_exact(v21, sr):
    n = sr // 4
    a = RNG.uniform(-1, 1, n); b = RNG.uniform(-1, 1, n)
    def rnd(lo, hi, blk):
        return np.repeat(RNG.uniform(lo, hi, n // blk + 1), blk)[:n]
    auto = dict(knob=rnd(0, 11, 700), knobr=rnd(0, 11, 900), reso=rnd(.5, 8, 500), drive=rnd(0, 100, 650),
                glide=rnd(0, 300, 1500), click=rnd(0, 100, 2000), slope=rnd(0, 1, 800), blend=rnd(0, 100, 1100),
                stereo=rnd(0, 2, 1300), comp=rnd(0, 1, 1200), drvonly=rnd(0, 1, 2500), outdb=rnd(-24, 12, 1000))
    m1, m2 = M.run(a, b, sr, **auto)
    g1, g2 = v21.run(a, b, sr, auto)
    assert np.array_equal(m1, g1) and np.array_equal(m2, g2)


# ---------------------------------------------------------------- V2 sound preserved
@pytest.mark.parametrize("sr", [88200, 96000, 192000])
@pytest.mark.parametrize("kw", [dict(knob=6), dict(knob=3, reso=6, drive=80, comp=0, slope=0),
                                dict(knob=9, knobr=2, stereo=1, blend=60, outdb=-6)])
def test_v21_equals_v2_without_oversampling(v2, v21, sr, kw):
    """Start-up differs by design (V2 faded output gain in from 0); compare after 1.5 s."""
    n = 2 * sr
    a = RNG.uniform(-.7, .7, n); b = RNG.uniform(-.7, .7, n)
    kw = dict(kw, click=0)
    x1, x2 = v2.run(a, b, sr, kw); y1, y2 = v21.run(a, b, sr, kw)
    s = 3 * sr // 2
    assert max(abs(x1[s:] - y1[s:]).max(), abs(x2[s:] - y2[s:]).max()) < 1e-12


@pytest.mark.parametrize("sr", [44100, 48000])
def test_v21_linear_response_matches_v2_in_band(v2, v21, sr):
    """Oversampling must not change steps where V2 was already accurate (<= 1 kHz).
    Higher steps change on purpose: V2.1 removes their 44.1/48k warping error."""
    n = 1 << 15
    x = np.zeros(n + sr // 4); x[sr // 4] = 1e-3
    for st in (1, 3, 6):
        kw = dict(knob=st, drive=0, click=0)
        h2 = v2.run(x, x, sr, kw)[0][sr // 4:] / 1e-3
        h21 = v21.run(x, x, sr, kw)[0][sr // 4:] / 1e-3
        f = np.fft.rfftfreq(n, 1 / sr)
        sel = (f > STEPS[st]) & (f < 16000)
        diff = np.abs(db(np.fft.rfft(h21))[sel] - db(np.fft.rfft(h2))[sel])
        assert diff.max() < 0.05, (st, diff.max())


# ---------------------------------------------------------------- A: discrete transitions
SWITCHES = {
    "stereo Link->Mono": ("stereo", 0, 2, dict(knob=6, knobr=1)),
    "stereo Link->Dual": ("stereo", 0, 1, dict(knob=6, knobr=1)),
    "stereo Dual->Link": ("stereo", 1, 0, dict(knob=6, knobr=1)),
    "stereo Mono->Dual": ("stereo", 2, 1, dict(knob=6, knobr=1)),
    "comp Unity->Peak": ("comp", 1, 0, dict(drive=60)),
    "comp Peak->Unity": ("comp", 0, 1, dict(drive=60)),
    "mode Filter->Drive": ("drvonly", 0, 1, dict(knob=6, drive=40)),
    "mode Drive->Filter": ("drvonly", 1, 0, dict(knob=6, drive=40)),
    "slope 12->18": ("slope", 0, 1, dict(knob=6)),
}


@pytest.mark.parametrize("sr", [44100, 48000, 96000, 192000])
@pytest.mark.parametrize("name", list(SWITCHES))
def test_discrete_switch_is_click_free(v21, sr, name):
    p, a, b, base = SWITCHES[name]
    n = sr
    t = np.arange(n) / sr
    x = 0.25 * np.sin(2 * np.pi * 100 * t); xr = 0.25 * np.sin(2 * np.pi * 100 * t + 1.3)
    v = dict(click=30, reso=1.4); v.update(base)
    arr = np.full(n, float(a)); arr[n // 2:] = b; v[p] = arr
    y1, y2 = v21.run(x, xr, sr, v)
    art = max(transition_artifact(y1, sr, 0.5)[0], transition_artifact(y2, sr, 0.5)[0])
    assert art < -70, art


# ---------------------------------------------------------------- B: click / glide
def _click_rms(prog, sr, **v):
    n = sr
    z = np.zeros(n)
    y1, y2 = prog.run(z, z, sr, v)
    seg = slice(n // 2, n // 2 + int(0.03 * sr))
    return float(db(np.sqrt(np.mean(np.concatenate([y1[seg], y2[seg]]) ** 2))))


@pytest.mark.parametrize("sr", [44100, 96000])
def test_click_fires_identically_at_any_glide(v21, sr):
    kn = np.full(sr, 3.0); kn[sr // 2:] = 6
    levels = [_click_rms(v21, sr, click=100, glide=g, knob=kn) for g in (0, 1, 50, 300, 2000)]
    assert levels[0] > -40
    assert max(levels) - min(levels) < 0.01


def test_click_zero_is_silent(v21):
    kn = np.full(48000, 3.0); kn[24000:] = 6
    assert _click_rms(v21, 48000, click=0, knob=kn) <= -300


@pytest.mark.parametrize("from_mode,to_mode", [(0, 1), (1, 0), (0, 2), (2, 1)])
def test_stereo_mode_change_never_clicks(v21, from_mode, to_mode):
    st = np.full(48000, float(from_mode)); st[24000:] = to_mode
    assert _click_rms(v21, 48000, click=100, knob=3, knobr=8, stereo=st) <= -300


def test_dual_right_knob_clicks_only_right(v21):
    sr = 48000; n = sr; z = np.zeros(n)
    kr = np.full(n, 2.0); kr[n // 2:] = 7
    y1, y2 = v21.run(z, z, sr, dict(click=100, stereo=1, knob=5, knobr=kr))
    assert np.abs(y1).max() == 0 and np.abs(y2).max() > 0.01
    y1, y2 = v21.run(z, z, sr, dict(click=100, stereo=0, knob=5, knobr=kr))   # inactive in Link
    assert np.abs(y1).max() == 0 and np.abs(y2).max() == 0


def test_no_click_on_load_or_samplerate_change(v21):
    sr = 48000; n = sr; z = np.zeros(n)
    y1, _ = v21.run(z, z, sr, dict(click=100, knob=7))                         # restored step
    assert np.abs(y1).max() == 0
    srs = np.full(n, 48000.0); srs[n // 2:] = 96000
    y1, _ = v21.run(z, z, srs, dict(click=100, knob=7))
    assert np.abs(y1).max() == 0


def test_rapid_stepping_does_not_stack(v21):
    sr = 48000; n = sr; z = np.zeros(n)
    kn = np.full(n, 1.0)
    for j in range(100):
        kn[24000 + j * 96:24000 + (j + 1) * 96] = 1 + (j % 10)
    y_r, _ = v21.run(z, z, sr, dict(click=100, knob=kn))
    y_1, _ = v21.run(z, z, sr, dict(click=100, knob=np.where(np.arange(n) >= 24000, 5.0, 1.0)))
    assert np.abs(y_r).max() <= 1.6 * np.abs(y_1).max()


# ---------------------------------------------------------------- C: frequency response
@pytest.mark.parametrize("sr", [44100, 48000, 88200, 96000, 176400, 192000])
def test_frequency_response_within_1_1_db_of_analog(v21, sr):
    n = 1 << 15 if sr <= 96000 else 1 << 16
    x = np.zeros(n + sr // 4); x[sr // 4] = 1e-3
    worst = 0
    for st in (1, 6, 9, 10, 11):
        for sl in (0, 1):
            for Q in (0.707, 8.0):
                y, _ = v21.run(x, x, sr, dict(knob=st, reso=Q, slope=sl, drive=0, click=0))
                h = y[sr // 4:] / 1e-3
                f = np.fft.rfftfreq(len(h), 1 / sr)
                worst = max(worst, *fr_error(f, np.fft.rfft(h), STEPS[st], Q, sl, min(20000, 0.4 * sr)))
    assert worst < 1.1, worst


@pytest.mark.parametrize("sr", [44100, 48000])
def test_oversampling_passband_flat_to_20k(v21, sr):
    n = 1 << 15
    x = np.zeros(n + sr // 4); x[sr // 4] = 1.0
    y, _ = v21.run(x, x, sr, dict(knob=0, drive=0, click=0))
    H = np.fft.rfft(y[sr // 4:]); f = np.fft.rfftfreq(n, 1 / sr)
    assert np.max(np.abs(db(H[f <= 20000]))) < 0.01


# ---------------------------------------------------------------- D: aliasing
def test_oversampling_reduces_aliasing_at_44k(v2, v21):
    from metrics import harmonic_alias, bin_freq
    sr = 44100; n = 1 << 15
    for f0, dv, min_gain in ((7000, 50, 15), (11000, 50, 15), (3000, 100, 15)):
        fb = bin_freq(f0, sr, n)
        x = 0.5 * np.sin(2 * np.pi * fb * np.arange(n + sr // 2) / sr)
        a2 = harmonic_alias(v2.run(x, x, sr, dict(knob=0, drive=dv, click=0))[0][sr // 2:sr // 2 + n], sr, fb)[1]
        a21 = harmonic_alias(v21.run(x, x, sr, dict(knob=0, drive=dv, click=0))[0][sr // 2:sr // 2 + n], sr, fb)[1]
        assert a2 - a21 > min_gain, (f0, dv, a2, a21)


# ---------------------------------------------------------------- E: stability
@pytest.mark.parametrize("sr", [44100, 96000, 192000])
def test_pathological_input_stays_finite_and_recovers(v21, sr):
    x = RNG.uniform(-1, 1, sr)
    x[1000:1010] = np.nan; x[2000] = np.inf; x[3000] = -np.inf; x[4000:4100] = 1e30
    y1, y2 = v21.run(x, x, sr, dict(knob=6, reso=8, drive=100))
    assert np.isfinite(y1).all() and np.isfinite(y2).all()
    assert np.abs(y1).max() <= 2.512
    assert np.std(y1[sr // 2:]) > 0.01


@pytest.mark.parametrize("sr", [44100, 96000])
def test_silence_tail_has_no_subnormals(v21, sr):
    x = np.zeros(4 * sr); x[0] = 1.0
    y, _ = v21.run(x, x, sr, dict(knob=1, reso=8, click=0))
    tl = y[-sr:]
    assert np.sum((tl != 0) & (np.abs(tl) < 2.2250738585072014e-308)) == 0
    assert np.abs(tl).max() < 1e-20


@pytest.mark.parametrize("sr", [44100, 192000])
def test_per_sample_automation_storm(v21, sr):
    n = sr // 2
    x = RNG.uniform(-1, 1, n)
    storm = {k: RNG.uniform(lo, hi, n) for k, (lo, hi) in dict(
        knob=(0, 11), knobr=(0, 11), reso=(.5, 8), drive=(0, 100), glide=(0, 2000), click=(0, 100),
        slope=(0, 1), blend=(0, 100), stereo=(0, 2), comp=(0, 1), drvonly=(0, 1), outdb=(-24, 12)).items()}
    y1, y2 = v21.run(x, -x, sr, storm)
    assert np.isfinite(y1).all() and np.isfinite(y2).all() and np.abs(y1).max() <= 2.512


def test_out_of_range_parameters_are_clamped(v21):
    x = RNG.uniform(-1, 1, 48000)
    y, _ = v21.run(x, x, 48000, dict(knob=1e9, reso=-5, drive=1e6, glide=-1, outdb=1e3, stereo=7))
    assert np.isfinite(y).all() and np.abs(y).max() <= 2.512


def test_dc_is_removed_by_filter_and_drive_path_settles(v21):
    sr = 48000; dc = np.full(2 * sr, 0.5)
    y1, _ = v21.run(dc, dc, sr, dict(knob=1, click=0))
    assert np.abs(y1[-sr // 2:]).max() < 1e-6


def test_samplerate_change_and_reactivation_are_smooth(v21):
    n = 3 * 48000
    srs = np.concatenate([np.full(48000, 44100.), np.full(48000, 96000.), np.full(48000, 48000.)])
    x = 0.5 * np.sin(2 * np.pi * 220 * np.arange(n) / 48000)
    act = np.ones(n); act[30000:40000] = 0
    y, _ = v21.run(x, x, srs, dict(knob=6, reso=6, drive=60, click=100, active=act))
    assert np.isfinite(y).all()
    y = np.where(act > 0.5, y, x)            # model Live's bypass: input passes while off
    d = np.abs(np.diff(y))
    steady = max(d[20000:29000].max(), np.abs(np.diff(x)).max())
    # re-activation: no sample step larger than normal signal motion
    assert d[40000 - 2:40000 + 800].max() <= 1.05 * steady
    # rate changes restart Live's audio engine, so the stream is interrupted anyway;
    # require only a bounded hand-over (<= 2x normal motion) and recovery
    for i in (48000, 96000):
        assert d[i - 2:i + 800].max() <= 2.0 * steady, (i, d[i - 2:i + 800].max(), steady)


# ---------------------------------------------------------------- stereo / calibration
def test_link_bit_identical_and_mono(v21):
    a = RNG.uniform(-.5, .5, 48000)
    y1, y2 = v21.run(a, a, 48000, dict(stereo=0, knob=6))
    assert np.array_equal(y1, y2)
    y1, y2 = v21.run(a, RNG.uniform(-.5, .5, 48000), 48000, dict(stereo=2, knob=6))
    s = int(0.012 * 48000)                   # after the 10 ms post-load dry->processed ramp
    assert np.array_equal(y1[s:], y2[s:])


@pytest.mark.parametrize("mode", [0, 1])
def test_no_crosstalk_in_link_and_dual(v21, mode):
    a = RNG.uniform(-.5, .5, 48000); z = np.zeros(48000)
    _, y2 = v21.run(a, z, 48000, dict(stereo=mode, knob=6, knobr=2, click=0))
    assert np.abs(y2).max() == 0


@pytest.mark.parametrize("sr", [44100, 96000])
def test_unity_drive_and_output_calibration(v21, sr):
    t = np.arange(sr) / sr
    x = 0.01 * np.sin(2 * np.pi * 1000 * t)
    ref = 0.01 / math.sqrt(2)
    for dv in (0, 50, 100):
        y, _ = v21.run(x, x, sr, dict(knob=0, drive=dv, comp=1, click=0))
        assert abs(db(np.sqrt(np.mean(y[sr // 2:] ** 2)) / ref)) < 0.02
    for od in (-24, -6, 12):
        y, _ = v21.run(x, x, sr, dict(knob=0, drive=0, outdb=od, click=0))
        assert abs(db(np.sqrt(np.mean(y[sr // 2:] ** 2)) / ref) - od) < 0.01


# ---------------------------------------------------------------- build / device files
def _build(outdir):
    subprocess.run([sys.executable, os.path.join(ROOT, "src", "build_device.py"), outdir] + BUILD_FLAGS,
                   check=True, capture_output=True)
    return open(os.path.join(outdir, "Tubby Filter.amxd"), "rb").read()


def test_build_is_reproducible_and_matches_shipped_device():
    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
        a, b = _build(d1), _build(d2)
    assert a == b
    assert a == open(os.path.join(DEV, "Tubby Filter.amxd"), "rb").read()


def _chunks(data):
    out, pos = {}, 0
    while pos + 8 <= len(data):
        tag = data[pos:pos + 4].decode("ascii")
        size = int.from_bytes(data[pos + 4:pos + 8], "little")
        out[tag] = data[pos + 8:pos + 8 + size]
        pos += 8 + size
    assert pos == len(data)
    return out


def test_amxd_container_and_embedded_source():
    data = open(os.path.join(DEV, "Tubby Filter.amxd"), "rb").read()
    ch = _chunks(data)
    assert ch["ampf"] == b"aaaa"                       # audio effect
    assert ch["ptch"][-1:] == b"\0"
    patch = json.loads(ch["ptch"][:-1].decode("utf-8"))["patcher"]
    gen = [b["box"] for b in patch["boxes"] if b["box"].get("text", "").startswith("gen~")][0]
    code = [b["box"]["code"] for b in gen["patcher"]["boxes"] if b["box"]["maxclass"] == "codebox"][0]
    assert code == open(SRC).read()


def test_ui_parameters_cover_dsp_and_keep_v2_names():
    patch = json.load(open(os.path.join(DEV, "Tubby Filter.maxpat")))["patcher"]
    msgs = {b["box"]["text"].split()[1] for b in patch["boxes"] if b["box"].get("text", "").startswith("prepend ")}
    params = set(compile_genexpr(open(SRC).read()).params)
    assert msgs == params
    longnames = {b["box"]["saved_attribute_attributes"]["valueof"]["parameter_longname"]
                 for b in patch["boxes"] if "saved_attribute_attributes" in b["box"]}
    assert {"Tubby Filter", "Reso", "Drive", "Glide", "Click", "Mix", "Slope"} <= longnames
    assert {"Filter R", "Output", "Stereo", "Drive Cal", "Mode"} <= longnames      # V2 additions kept


# ---------------------------------------------------------------- Live capture kit self-test
def test_capture_tool_passes_reference_and_catches_faults(tmp_path):
    """Checks the comparison TOOL (not Live): a perfect render passes, faulty renders fail."""
    import shutil
    sys.path.insert(0, os.path.join(ROOT, "validation"))
    import make_signals, compare_capture
    from scipy.io import wavfile
    make_signals.main([48000])
    sd = os.path.join(ROOT, "validation", "signals", "48000")
    good, bad = tmp_path / "good", tmp_path / "bad"
    good.mkdir(); bad.mkdir()
    for f in os.listdir(sd):
        if f.endswith("_ref.wav"):
            nm = f[:-8]
            sr, r = wavfile.read(os.path.join(sd, f))
            wavfile.write(good / f"{nm}_live.wav", sr, r)
            wavfile.write(bad / f"{nm}_live.wav", sr, (r * 10 ** (0.2 / 20)).astype(np.float32))
    compare_capture.main(48000, str(good))
    compare_capture.main(48000, str(bad))
    g = json.load(open(good / "capture_report.json"))["cases"]
    b = json.load(open(bad / "capture_report.json"))["cases"]
    assert all(v["status"] == "PASS" for v in g.values())
    # C10/C12 are level-independent by nature; C14 compares a bloom RATIO (Motion vs Motion 0),
    # which is gain-invariant by design. Every other case must catch a 0.2 dB gain error.
    gain_sensitive = [k for k in b if k not in ("C10_leftonly_link_sep", "C12_silence_noise_floor",
                                                "C14_motion100_step_bloom")]
    assert all(b[k]["status"] == "FAIL" for k in gain_sensitive)
    # C14 must catch a device whose Motion does nothing (render equals the Motion-0 reference)
    c14 = "C14_motion100_step_bloom"
    if c14 in g:
        bad2 = tmp_path / "nomotion"; bad2.mkdir()
        sr, r0 = wavfile.read(os.path.join(sd, f"{c14}_ref_motion0.wav"))
        wavfile.write(bad2 / f"{c14}_live.wav", sr, r0)
        compare_capture.main(48000, str(bad2))
        assert json.load(open(bad2 / "capture_report.json"))["cases"][c14]["status"] == "FAIL"


# ================================================================ V2.2 research additions (part 7)
@pytest.mark.parametrize("sr", [44100, 96000])
@pytest.mark.parametrize("slope", [0, 1])
def test_no_self_oscillation_at_maximum_resonance(v21, sr, slope):
    """Q is capped at 8: every step must ring down (passive-filter behaviour, by design)."""
    n = 2 * sr
    x = np.zeros(n); x[sr // 4] = 0.5
    for st in (1, 6, 11):
        y, _ = v21.run(x, x, sr, dict(knob=st, reso=8, slope=slope, drive=0, click=0))
        assert np.abs(y[sr // 4 + sr:]).max() < 1e-6, st          # < -120 dBFS one second later


@pytest.mark.parametrize("sr", [44100, 96000])
def test_maximum_drive_bounded_and_dc_free(v21, sr):
    t = np.arange(2 * sr) / sr
    sq = np.sign(np.sin(2 * np.pi * 50 * t))                       # full-scale square
    y, _ = v21.run(sq, sq, sr, dict(knob=0, drive=100, comp=0, reso=8, outdb=12, click=0))
    assert np.isfinite(y).all() and np.abs(y).max() <= 2.512
    assert abs(np.mean(y[sr:])) < 1e-3                             # DC blocker active


@pytest.mark.parametrize("sr", [44100, 96000])
def test_rapid_cutoff_modulation_continuity(v21, sr):
    n = sr
    t = np.arange(n) / sr
    x = 0.5 * np.sin(2 * np.pi * 220 * t)
    kn = RNG.integers(0, 12, n).astype(float)                     # new step every sample
    y, _ = v21.run(x, x, sr, dict(knob=kn, reso=8, click=0, glide=0))
    assert np.isfinite(y).all() and np.abs(y).max() <= 2.512
    y, _ = v21.run(x, x, sr, dict(knob=kn, reso=1.4, click=0, glide=20))   # with glide: no steps
    d = np.abs(np.diff(y[sr // 2:]))
    assert d.max() <= 1.5 * np.abs(np.diff(x)).max()


def test_link_channels_are_independent(v21):
    """Link: each side's output depends only on that side's input (stereo image integrity)."""
    a = RNG.uniform(-.5, .5, 48000); b = RNG.uniform(-.5, .5, 48000)
    yl, yr = v21.run(a, b, 48000, dict(stereo=0, knob=6, drive=60, reso=4))
    yl_ref, _ = v21.run(a, a, 48000, dict(stereo=0, knob=6, drive=60, reso=4))
    _, yr_ref = v21.run(b, b, 48000, dict(stereo=0, knob=6, drive=60, reso=4))
    assert np.array_equal(yl, yl_ref) and np.array_equal(yr, yr_ref)


@pytest.mark.parametrize("sr", [88200, 96000])
def test_flat_clean_is_bit_transparent_at_native_rates(v21, sr):
    """Transport start / abrupt signal after silence: FLAT + Drive 0 adds nothing."""
    x = np.concatenate([np.zeros(sr // 2), RNG.uniform(-1, 1, sr)])
    y1, y2 = v21.run(x, x, sr, dict(knob=0, drive=0, click=30))
    s = int(0.02 * sr)
    assert np.array_equal(y1[s:], x[s:]) and np.array_equal(y2[s:], x[s:])
