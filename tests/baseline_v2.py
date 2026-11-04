"""Measure-before-change: V2 behaviour on the points the V2.1 brief raises.
Runs the shipped V2 source (legacy/v2/tubby_filter.genexpr) through GSX.
Writes reports/baseline_v2.json.  These are SIMULATED results (GSX), not gen~."""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
from gsx import compile_genexpr
from metrics import *

ROOT = os.path.join(HERE, "..")


def load(path):
    return compile_genexpr(open(os.path.join(ROOT, path)).read())


def discrete_switch_tests(prog, sr, extra=None):
    """100 Hz sine at -12 dBFS, switch one discrete control at t = 0.5 s."""
    extra = extra or {}
    n = sr
    t = np.arange(n) / sr
    x = 0.25 * np.sin(2 * np.pi * 100 * t)
    xr = 0.25 * np.sin(2 * np.pi * 100 * t + 1.3)          # L != R
    res = {}
    cases = {
        "stereo Link->Mono": ("stereo", 0, 2, dict(knob=6, knobr=1)),
        "stereo Link->Dual": ("stereo", 0, 1, dict(knob=6, knobr=1)),
        "stereo Dual->Link": ("stereo", 1, 0, dict(knob=6, knobr=1)),
        "comp Unity->Peak (drive 60)": ("comp", 1, 0, dict(drive=60, knob=0)),
        "comp Peak->Unity (drive 60)": ("comp", 0, 1, dict(drive=60, knob=0)),
        "mode Filter->Drive": ("drvonly", 0, 1, dict(knob=6, drive=40)),
        "slope 12->18": ("slope", 0, 1, dict(knob=6)),
        "step 0->6, click 0": ("knob", 0, 6, dict(click=0)),
        "step 3->6, click 0": ("knob", 3, 6, dict(click=0)),
    }
    for name, (p, a, b, base) in cases.items():
        vals = dict(click=0.0, reso=1.4)
        vals.update(base); vals.update(extra)
        arr = np.full(n, float(a)); arr[n // 2:] = b
        vals[p] = arr
        y1, y2 = prog.run(x, xr, sr, vals)
        a1, b1 = transition_artifact(y1, sr, 0.5)
        a2, b2 = transition_artifact(y2, sr, 0.5)
        res[name] = dict(artifact_dbfs=round(max(a1, a2), 1), steady_dbfs=round(max(b1, b2), 1))
    return res


def fr_dev(prog, sr, extra=None):
    worst = [0.0, 0.0]
    per_step = {}
    n = 1 << 16 if sr <= 96000 else 1 << 17
    x = np.zeros(n); x[int(0.25 * sr)] = 1e-3      # settle 250 ms first
    for st in range(1, 12):
        for sl in (0, 1):
            for Q in (0.707, 1.4, 8.0):
                vals = dict(knob=st, knobr=st, reso=Q, slope=sl, drive=0, click=0)
                vals.update(extra or {})
                y, _ = prog.run(x, x, sr, vals)
                h = y[int(0.25 * sr):int(0.25 * sr) + (1 << 15 if sr <= 96000 else 1 << 16)] / 1e-3
                H = np.fft.rfft(h); f = np.fft.rfftfreq(len(h), 1 / sr)
                pb, sk = fr_error(f, H, STEPS[st], Q, sl, min(20000, 0.4 * sr))
                worst[0] = max(worst[0], pb); worst[1] = max(worst[1], sk)
                per_step[st] = max(per_step.get(st, 0), pb, sk)
    return dict(passband_peak=round(worst[0], 3), skirt=round(worst[1], 3),
                worst_by_step={int(k): round(v, 3) for k, v in per_step.items()})


def alias_table(prog, sr, extra=None):
    out = {}
    n = 1 << 15
    for f0 in (3000, 7000, 11000, 15000):
        fb = bin_freq(f0, sr, n)
        t = np.arange(n + sr // 2) / sr
        x = 0.5 * np.sin(2 * np.pi * fb * t)              # -6 dBFS
        for dv in (25, 50, 100):
            vals = dict(knob=0, drive=dv, click=0, comp=1)
            vals.update(extra or {})
            y, _ = prog.run(x, x, sr, vals)
            thd, al = harmonic_alias(y[sr // 2:sr // 2 + n], sr, fb)
            out[f"{f0}Hz drive{dv}"] = dict(harm_db=round(thd, 1), alias_db=round(al, 1))
    return out


if __name__ == "__main__":
    prog = load("legacy/v2/tubby_filter.genexpr")
    R = {"_note": "SIMULATED with GSX on the shipped V2 source. Not gen~/Live measurements."}
    R["fr_deviation"] = {sr: fr_dev(prog, sr) for sr in RATES}
    R["aliasing_-6dBFS"] = {sr: alias_table(prog, sr) for sr in (44100, 48000, 96000)}
    R["discrete_switches_48k"] = discrete_switch_tests(prog, 48000)
    os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
    json.dump(R, open(os.path.join(ROOT, "reports", "baseline_v2.json"), "w"), indent=1)
    print(json.dumps(R, indent=1))
