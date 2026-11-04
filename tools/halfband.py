"""Polyphase IIR half-band design (two allpass branches), after the elliptic
design method used by Laurent de Soras' HIIR library (WTFPL).

H(z) = 0.5 * (A0(z^2) + z^-1 * A1(z^2)), each Ai a cascade of
first-order-in-z^2 allpass sections  (a + z^-2) / (1 + a z^-2).
Coefficients alternate: even index -> branch 0, odd index -> branch 1.
"""
import math
import numpy as np


def _transition_param(transition):
    k = math.tan((1 - transition * 2) * math.pi / 4) ** 2
    kksqrt = (1 - k * k) ** 0.25
    e = 0.5 * (1 - kksqrt) / (1 + kksqrt)
    e2 = e * e; e4 = e2 * e2
    q = e * (1 + e4 * (2 + e4 * (15 + 150 * e4)))
    return k, q


def _acc_num(q, order, c):
    res, i, j = 0.0, 0, 1
    while True:
        nxt = q ** (i * (i + 1)) * math.sin((i * 2 + 1) * c * math.pi / order) * j
        res += nxt; j = -j; i += 1
        if abs(nxt) < 1e-100:
            return res


def _acc_den(q, order, c):
    res, i, j = 0.0, 1, -1
    while True:
        nxt = q ** (i * i) * math.cos(i * 2 * c * math.pi / order) * j
        res += nxt; j = -j; i += 1
        if abs(nxt) < 1e-100:
            return res


def design(nbr_coefs, transition):
    """transition: normalised to the *oversampled* rate (0 < t < 0.5)."""
    k, q = _transition_param(transition)
    order = nbr_coefs * 2 + 1
    out = []
    for idx in range(nbr_coefs):
        c = idx + 1
        num = _acc_num(q, order, c) * q ** 0.25
        den = _acc_den(q, order, c) + 0.5
        ww = num / den
        wwsq = ww * ww
        x = math.sqrt((1 - wwsq * k) * (1 - wwsq / k)) / (1 + wwsq)
        out.append((1 - x) / (1 + x))
    return out


def response(coefs, f):
    """Magnitude of the half-band low-pass at normalised freq f (cycles/sample, oversampled rate)."""
    z = np.exp(1j * 2 * np.pi * np.asarray(f))
    z2 = z ** -2
    a0 = np.ones_like(z); a1 = np.ones_like(z)
    for i, a in enumerate(coefs):
        sec = (a + z2) / (1 + a * z2)
        if i % 2 == 0:
            a0 = a0 * sec
        else:
            a1 = a1 * sec
    return 0.5 * (a0 + a1 / z)


if __name__ == "__main__":
    for nc, tr in ((6, 0.05), (8, 0.04), (8, 0.05), (10, 0.03), (12, 0.02)):
        c = design(nc, tr)
        f = np.linspace(0, 0.5, 20001)
        H = np.abs(response(c, f))
        stop = 20 * np.log10(H[f >= 0.25 + tr].max())
        print(nc, tr, f"stopband {stop:.1f} dB, passband edge {(0.25 - tr):.3f}",
              f"ripple {20*np.log10(H[f <= 0.25 - tr]).min():.5f} dB")
