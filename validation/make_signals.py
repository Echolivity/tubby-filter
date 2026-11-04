"""Write the capture-kit input WAVs and the expected (reference) outputs.

python3 validation/make_signals.py [rate ...]      default: 44100 48000 96000

Writes validation/signals/<rate>/<case>_in.wav     (32-bit float stereo, play these in Live)
       validation/signals/<rate>/<case>_ref.wav    (reference output of the shipped source, via GSX)
       validation/signals/<rate>/SETTINGS.md       (what to set on the device for each case)
"""
import os, sys
import numpy as np
from scipy.io import wavfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "tools")); sys.path.insert(0, HERE)
from gsx import compile_genexpr
from cases import CASES, SIGNALS, gen_params, PRE


def main(rates):
    prog = compile_genexpr(open(os.path.join(ROOT, "src", "tubby_filter.genexpr")).read())
    for sr in rates:
        d = os.path.join(HERE, "signals", str(sr)); os.makedirs(d, exist_ok=True)
        lines = [f"# Device settings per case — {sr} Hz project\n",
                 "Set every listed control; anything not listed stays at the device default "
                 "(Filter FLAT, Reso 1.4, Drive 20, Output 0, Glide 0, **Click 0**, Mix 100, 18dB, Link, Unity, Filter).\n"]
        for name, c in CASES.items():
            a, b = SIGNALS[c["signal"]](sr)
            # the device sees 32-bit float audio: quantise before computing the reference
            a = a.astype(np.float32).astype(np.float64); b = b.astype(np.float32).astype(np.float64)
            p, ui = gen_params(c["ui"], c.get("automation"), sr, len(a))
            y1, y2 = prog.run(a, b, sr, p)
            wavfile.write(os.path.join(d, f"{name}_in.wav"), sr, np.stack([a, b], 1).astype(np.float32))
            wavfile.write(os.path.join(d, f"{name}_ref.wav"), sr, np.stack([y1, y2], 1).astype(np.float32))
            auto = ""
            for k, pts in (c.get("automation") or {}).items():
                auto += "; **automate** " + ", ".join(f"{k} -> {v} at {PRE + t:.2f} s from clip start" for t, v in pts)
            lines.append(f"- **{name}**: " + ", ".join(f"{k} = {v}" for k, v in c["ui"].items()) +
                         ("" if "Click" in c["ui"] else ", Click = 0") + auto)
            if c.get("automation"):
                # also keep the Motion-0 reference for the statistical bloom comparison
                p0 = dict(p); p0["motion"] = 0.0
                z1, _ = prog.run(a, b, sr, p0)
                wavfile.write(os.path.join(d, f"{name}_ref_motion0.wav"), sr, np.stack([z1, z1], 1).astype(np.float32))
        open(os.path.join(d, "SETTINGS.md"), "w").write("\n".join(lines) + "\n")
        print(f"{sr}: {len(CASES)} cases -> {d}")


if __name__ == "__main__":
    main([int(r) for r in sys.argv[1:]] or [44100, 48000, 96000])
