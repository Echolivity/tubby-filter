"""Shared measurement helpers (used for V2 baseline, V2.1 reports and Live captures)."""
import math
import numpy as np
from scipy import signal

RATES = [44100, 48000, 88200, 96000, 192000]
STEPS = np.array([20, 70, 100, 150, 250, 500, 1000, 2000, 3000, 5000, 7500, 10000], float)


def db(x):
    return 20 * np.log10(np.maximum(np.abs(x), 1e-15))


def analog_hp(f, fc, Q, slope18):
    s = 1j * np.asarray(f) / fc
    H = s * s / (s * s + s / Q + 1)
    if slope18:
        H = H * s / (s + 1)
    return H


def fr_error(f, H, fc, Q, slope18, f_hi):
    """Max |dB| error vs analog prototype: (passband+peak f>=fc, skirt fc..-20 dB)."""
    sel = (f > max(20, fc / 8)) & (f <= f_hi)
    a = db(analog_hp(f[sel], fc, Q, slope18))
    e = np.abs(db(H[sel]) - a)
    pb = f[sel] >= fc
    sk = (f[sel] < fc) & (a > -20)
    return (float(e[pb].max()) if pb.any() else 0.0, float(e[sk].max()) if sk.any() else 0.0)


def transition_artifact(y, sr, t_switch, win_ms=30, hp_hz=3000):
    """Peak level (dBFS) of content above hp_hz in a window after a switch,
    relative to the same measure in a steady window before it. The test signal
    is a low sine, so HF energy is artefact (click/step)."""
    sos = signal.butter(4, hp_hz, "hp", fs=sr, output="sos")
    h = signal.sosfilt(sos, y)
    i0 = int(t_switch * sr)
    w = int(win_ms * 1e-3 * sr)
    after = np.max(np.abs(h[i0:i0 + w]))
    before = np.max(np.abs(h[i0 - 3 * w:i0 - w]))
    return float(db(after)), float(db(before))


def harmonic_alias(y, sr, f0, nharm=40):
    """Split the spectrum of a steady sine response into fundamental, harmonics
    (k·f0 below Nyquist) and aliasing (everything else). f0 must be bin-centred.
    Returns (thd_db, alias_db) relative to the fundamental."""
    n = len(y)
    w = signal.windows.blackmanharris(n)
    Y = np.abs(np.fft.rfft(y * w)) ** 2
    f = np.fft.rfftfreq(n, 1 / sr)
    df = f[1]
    guard = 6  # bins either side covered by the window main lobe
    used = np.zeros_like(Y, bool)
    used[:guard + 2] = True  # DC
    def band(fr):
        k = int(round(fr / df))
        return slice(max(k - guard, 0), k + guard + 1)
    fund = Y[band(f0)].sum(); used[band(f0)] = True
    harm = 0.0
    for k in range(2, nharm + 1):
        if k * f0 >= sr / 2 - guard * df:
            break
        harm += Y[band(k * f0)].sum(); used[band(k * f0)] = True
    alias = Y[~used].sum()
    return 10 * math.log10(max(harm, 1e-300) / fund), 10 * math.log10(max(alias, 1e-300) / fund)


def bin_freq(f, sr, n):
    return round(f * n / sr) * sr / n
