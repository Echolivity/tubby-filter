"""Capture cases for validating the compiled device inside Ableton Live.

Each case = one input WAV + one set of device settings. You render the input
through the real device in Live (procedure in validation/LIVE_VALIDATION.md),
then validation/compare_capture.py compares the render with the reference
output of the shipped source and reports PASS / FAIL per metric.

Click is 0 in every sample-exact case: the switch transient uses noise, so it
cannot match sample-for-sample. Case C09 checks its level statistically.
"""
import numpy as np

PRE = 0.5          # s of silence before the test material (lets smoothers settle)


def _t(sr, dur):
    return np.arange(int(dur * sr)) / sr


def sig_impulse(sr):
    x = np.zeros(int((PRE + 1.0) * sr)); x[int(PRE * sr)] = 0.5
    return x, x


def sig_sweep(sr, level=0.1, dur=4.0):
    t = _t(sr, dur); f1, f2 = 20.0, 20000.0
    k = np.log(f2 / f1)
    s = level * np.sin(2 * np.pi * f1 * dur / k * (np.exp(t / dur * k) - 1))
    x = np.concatenate([np.zeros(int(PRE * sr)), s, np.zeros(int(0.5 * sr))])
    return x, x


def sig_sine(sr, f, level_db, dur=2.0):
    x = np.concatenate([np.zeros(int(PRE * sr)), 10 ** (level_db / 20) * np.sin(2 * np.pi * f * _t(sr, dur))])
    return x, x


def sig_step(sr):
    x = np.zeros(int((PRE + 1.5) * sr)); x[int(PRE * sr):] = 0.25
    return x, x


def sig_noise_lr(sr, dur=3.0):
    rng = np.random.default_rng(42)
    a = np.concatenate([np.zeros(int(PRE * sr)), 0.25 * rng.standard_normal(int(dur * sr))])
    b = np.concatenate([np.zeros(int(PRE * sr)), 0.25 * rng.standard_normal(int(dur * sr))])
    return np.clip(a, -1, 1), np.clip(b, -1, 1)


def sig_left_only(sr, dur=3.0):
    rng = np.random.default_rng(7)
    a = np.concatenate([np.zeros(int(PRE * sr)), 0.25 * rng.standard_normal(int(dur * sr))])
    return np.clip(a, -1, 1), np.zeros_like(a)


def sig_pink_motion(sr, dur=4.0):
    from scipy import signal as _s
    rng = np.random.default_rng(14)
    p = _s.lfilter([0.049922035, -0.095993537, 0.050612699, -0.004408786],
                   [1, -2.494956002, 2.017265875, -0.522189400], rng.standard_normal(int(dur * sr)))
    p = p / np.std(p) * 10 ** (-18 / 20)
    a = np.concatenate([np.zeros(int(PRE * sr)), p])
    return a, a.copy()


def sig_silence(sr, dur=3.0):
    z = np.zeros(int(dur * sr)); return z, z


# device settings use the names shown on the device panel; "param" maps to gen~
UI = {"Filter": "knob", "Filter R": "knobr", "Reso": "reso", "Drive": "drive", "Output": "outdb",
      "Glide": "glide", "Click": "click", "Mix": "blend", "Slope": "slope", "Stereo": "stereo",
      "Drive Cal": "comp", "Mode": "drvonly", "Motion": "motion"}
STEP_LABELS = ["FLAT", "70", "100", "150", "250", "500", "1k", "2k", "3k", "5k", "7.5k", "10k"]
ENUMS = {"Slope": ["12dB", "18dB"], "Stereo": ["Link", "Dual", "Mono"], "Drive Cal": ["Peak", "Unity"],
         "Mode": ["Filter", "Drive"], "Filter": STEP_LABELS, "Filter R": STEP_LABELS}
DEFAULT_UI = {"Filter": "FLAT", "Filter R": "FLAT", "Reso": 1.4, "Drive": 20, "Output": 0, "Glide": 0,
              "Click": 0, "Mix": 100, "Slope": "18dB", "Stereo": "Link", "Drive Cal": "Unity", "Mode": "Filter",
              "Motion": 0}

CASES = {
    "C01_impulse_flat_clean": dict(signal="impulse", ui={"Drive": 0},
                                   checks=["sample_exact", "latency", "impulse"]),
    "C02_sweep_2k_q1.4_18dB": dict(signal="sweep", ui={"Filter": "2k", "Drive": 0},
                                   checks=["sample_exact", "freq_response"]),
    "C03_sweep_10k_q8_12dB": dict(signal="sweep", ui={"Filter": "10k", "Reso": 8, "Slope": "12dB", "Drive": 0},
                                  checks=["sample_exact", "freq_response"]),
    "C04_sweep_70_q0.707": dict(signal="sweep", ui={"Filter": "70", "Reso": 0.707, "Drive": 0},
                                checks=["sample_exact", "freq_response"]),
    "C05_step_500": dict(signal="step", ui={"Filter": "500", "Drive": 0},
                         checks=["sample_exact", "step_response"]),
    "C06_sine100_-6_drive60_unity": dict(signal="sine100_-6", ui={"Drive": 60},
                                         checks=["sample_exact", "thd", "level"]),
    "C07_sine7k_-6_drive50": dict(signal="sine7k_-6", ui={"Drive": 50},
                                  checks=["thd_alias", "level"]),
    "C08_sine1k_-40_drive100_unity": dict(signal="sine1k_-40", ui={"Drive": 100},
                                          checks=["level"]),
    "C09_noise_dual_1k_250_peak": dict(signal="noise_lr", ui={"Filter": "1k", "Filter R": "250", "Stereo": "Dual",
                                                               "Drive": 40, "Drive Cal": "Peak", "Mix": 70, "Output": -6},
                                       checks=["sample_exact"]),
    "C10_leftonly_link_sep": dict(signal="left_only", ui={"Filter": "1k"}, checks=["separation"]),
    "C11_leftonly_mono": dict(signal="left_only", ui={"Filter": "1k", "Stereo": "Mono"}, checks=["sample_exact"]),
    "C12_silence_noise_floor": dict(signal="silence", ui={"Filter": "1k", "Reso": 8, "Drive": 100, "Click": 100},
                                    checks=["noise_floor"]),
    # ---- V2.2 Motion
    # C13: Motion at maximum with a STATIC cutoff must be sample-identical to Motion 0 / V2.1
    "C13_motion100_static_cutoff": dict(signal="noise_lr", ui={"Filter": "1k", "Reso": 4, "Motion": 100},
                                        checks=["sample_exact"]),
    # C14: Filter automated 150 -> 1k at exactly 1.0 s after the pre-roll (120 BPM: bar 1 beat 3
    # when the clip starts at bar 1 and the pre-roll is 0.5 s -> place the step at 1.5 s = 1.4.1).
    # M4L parameter automation is block-timed, so this is compared statistically, not sample-exact.
    "C14_motion100_step_bloom": dict(signal="pink_motion", ui={"Filter": "150", "Reso": 1.4, "Motion": 100},
                                     automation={"Filter": [(1.0, "1k")]}, checks=["motion_bloom"]),
}

SIGNALS = {
    "impulse": sig_impulse, "sweep": sig_sweep, "step": sig_step,
    "sine100_-6": lambda sr: sig_sine(sr, 100, -6), "sine7k_-6": lambda sr: sig_sine(sr, 7000, -6),
    "sine1k_-40": lambda sr: sig_sine(sr, 1000, -40), "noise_lr": sig_noise_lr,
    "left_only": sig_left_only, "silence": sig_silence, "pink_motion": sig_pink_motion,
}


def gen_params(ui_overrides, automation=None, sr=None, n=None):
    """Device-panel settings -> gen~ parameter values (the values the device sends).
    automation: {control: [(seconds after the pre-roll, value), ...]} -> per-sample arrays."""
    ui = dict(DEFAULT_UI); ui.update(ui_overrides)
    out = {}
    for k, v in ui.items():
        out[UI[k]] = ENUMS[k].index(v) if k in ENUMS else float(v)
    for k, pts in (automation or {}).items():
        arr = np.full(n, float(out[UI[k]]))
        for t, v in pts:
            arr[int((PRE + t) * sr):] = ENUMS[k].index(v) if k in ENUMS else float(v)
        out[UI[k]] = arr
    return out, ui
