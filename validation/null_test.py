"""Measure a parallel null test exported from Live (QA items PAR-1, PAR-2, L-PDC-1/2, F-3).

    py validation/null_test.py <null_export.wav> <reference.wav>

<null_export.wav>: the master bus exported while DUT and a phase-inverted copy play together.
<reference.wav>:  the clip that was played (e.g. reports/v22/audio/ref_dry_dub_loop_48k.wav).
Prints the residual per octave band relative to the reference, in dB (more negative = better null).
"""
import sys
import numpy as np
from scipy import signal
from scipy.io import wavfile


def load(p):
    sr, x = wavfile.read(p)
    x = x.astype(np.float64)
    if np.issubdtype(x.dtype, np.integer):
        x /= np.iinfo(x.dtype).max
    return sr, (x if x.ndim == 1 else x[:, 0])


def main(null_path, ref_path):
    srn, nl = load(null_path); srr, ref = load(ref_path)
    if srn != srr:
        sys.exit(f"sample rates differ: {srn} vs {srr}")
    n = min(len(nl), len(ref)); nl, ref = nl[:n], ref[:n]
    print(f"broadband residual: {20 * np.log10(np.sqrt(np.mean(nl ** 2)) / np.sqrt(np.mean(ref ** 2)) + 1e-300):7.1f} dB")
    for lo in (63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000):
        hi = min(lo * 2, srn / 2 * 0.95)
        if lo >= hi:
            break
        sos = signal.butter(4, [lo, hi], "bp", fs=srn, output="sos")
        a = signal.sosfilt(sos, nl); b = signal.sosfilt(sos, ref)
        r = 20 * np.log10(np.sqrt(np.mean(a ** 2)) / max(np.sqrt(np.mean(b ** 2)), 1e-20) + 1e-300)
        print(f"{lo:6d}-{int(hi):5d} Hz: {r:7.1f} dB")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
