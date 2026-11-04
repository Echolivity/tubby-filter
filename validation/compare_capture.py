"""Compare audio rendered by the real device in Ableton Live with the reference.

python3 validation/compare_capture.py <rate> <renders_dir>

<renders_dir> holds Live exports named <case>_live.wav (32-bit float, no
normalise, no dither — see LIVE_VALIDATION.md). Missing renders are reported as
NOT PERFORMED, never as passed. Writes <renders_dir>/capture_report.json and .md.

This is the only part of the test suite that measures the compiled gen~ code
running inside Live. Its results are labelled MEASURED (LIVE).
"""
import json, math, os, sys
import numpy as np
from scipy import signal
from scipy.io import wavfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tests")); sys.path.insert(0, HERE)
from metrics import db, harmonic_alias, bin_freq
from cases import CASES, PRE

TOL = dict(sample_exact_err_dbfs=-80.0,   # peak |live - ref| after alignment
           latency_samples=0,              # device must not delay audio vs reference
           fr_db=0.1, level_db=0.05, thd_db=0.5, separation_db=-120.0, noise_floor_dbfs=-120.0)


def load(path):
    sr, x = wavfile.read(path)
    x = x.astype(np.float64)
    if x.dtype.kind == "i":
        x /= np.iinfo(x.dtype).max
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    return sr, x


def align(live, ref, maxlag=4096):
    """Lag (samples) of live relative to ref, by cross-correlation of the left channel."""
    n = min(len(live), len(ref))
    c = signal.correlate(live[:n, 0], ref[:n, 0], mode="full", method="fft")
    mid = n - 1
    seg = c[mid - maxlag:mid + maxlag + 1]
    return int(np.argmax(np.abs(seg)) - maxlag)


def check_case(name, case, sr, live, ref, inp):
    out = {}
    lag = align(live, ref)
    out["lag_samples"] = lag
    if lag > 0:
        live = live[lag:]
    elif lag < 0:
        live = np.concatenate([np.zeros((-lag, 2)), live])
    n = min(len(live), len(ref)); live, ref = live[:n], ref[:n]
    s = int(PRE * sr)
    res = {}
    for chk in case["checks"]:
        if chk == "sample_exact":
            e = float(db(np.abs(live[s:] - ref[s:]).max()))
            res[chk] = dict(value=round(e, 1), limit=TOL["sample_exact_err_dbfs"], ok=e <= TOL["sample_exact_err_dbfs"])
        elif chk == "latency":
            res[chk] = dict(value=lag, limit=TOL["latency_samples"], ok=lag == TOL["latency_samples"])
        elif chk in ("impulse", "step_response"):
            e = float(db(np.abs(live[s:s + sr // 2] - ref[s:s + sr // 2]).max()))
            res[chk] = dict(value=round(e, 1), limit=TOL["sample_exact_err_dbfs"], ok=e <= TOL["sample_exact_err_dbfs"])
        elif chk == "freq_response":
            nf = 1 << 16
            L = np.fft.rfft(live[s:, 0], nf); Rf = np.fft.rfft(ref[s:, 0], nf); f = np.fft.rfftfreq(nf, 1 / sr)
            band = (f > 30) & (f < 18000) & (db(Rf) > db(Rf).max() - 40)
            e = float(np.max(np.abs(db(L[band]) - db(Rf[band]))))
            res[chk] = dict(value=round(e, 3), limit=TOL["fr_db"], ok=e <= TOL["fr_db"])
        elif chk == "level":
            lv = float(db(np.sqrt(np.mean(live[s + sr // 2:, 0] ** 2)) / np.sqrt(np.mean(ref[s + sr // 2:, 0] ** 2))))
            res[chk] = dict(value=round(lv, 3), limit=TOL["level_db"], ok=abs(lv) <= TOL["level_db"])
        elif chk in ("thd", "thd_alias"):
            nn = 1 << 15
            f0 = 100 if "sine100" in case["signal"] else 7000
            fb = f0  # signals are generated at exact frequency; use nearest-bin windowed estimate
            hl, al = harmonic_alias(live[s + sr // 4:s + sr // 4 + nn, 0], sr, bin_freq(fb, sr, nn))
            hr, ar = harmonic_alias(ref[s + sr // 4:s + sr // 4 + nn, 0], sr, bin_freq(fb, sr, nn))
            ok = abs(hl - hr) <= TOL["thd_db"] and (chk == "thd" or al <= ar + 3)
            res[chk] = dict(value=dict(harm_live=round(hl, 2), harm_ref=round(hr, 2),
                                       alias_live=round(al, 1), alias_ref=round(ar, 1)), ok=bool(ok))
        elif chk == "separation":
            sep = float(db(np.sqrt(np.mean(live[s:, 1] ** 2)) + 1e-300))
            res[chk] = dict(value=round(sep, 1), limit=TOL["separation_db"], ok=sep <= TOL["separation_db"])
        elif chk == "noise_floor":
            nfv = float(db(np.abs(live).max()))
            res[chk] = dict(value=round(nfv, 1), limit=TOL["noise_floor_dbfs"], ok=nfv <= TOL["noise_floor_dbfs"])
    # every case: the device must not add delay relative to the reference
    if "latency" not in res and "noise_floor" not in case["checks"] and "separation" not in case["checks"]:
        res["latency"] = dict(value=lag, limit=TOL["latency_samples"], ok=lag == TOL["latency_samples"])
    out["checks"] = res
    out["status"] = "PASS" if all(v["ok"] for v in res.values()) else "FAIL"
    return out


def main(sr, rdir):
    sdir = os.path.join(HERE, "signals", str(sr))
    report = {"_label": "MEASURED (LIVE): compiled device rendered by Ableton Live", "rate": sr, "cases": {}}
    for name, case in CASES.items():
        lp = os.path.join(rdir, f"{name}_live.wav")
        if not os.path.exists(lp):
            report["cases"][name] = {"status": "NOT PERFORMED", "reason": "no render found"}
            continue
        srl, live = load(lp)
        if srl != sr:
            report["cases"][name] = {"status": "FAIL", "reason": f"render is {srl} Hz, expected {sr}"}
            continue
        _, ref = load(os.path.join(sdir, f"{name}_ref.wav"))
        _, inp = load(os.path.join(sdir, f"{name}_in.wav"))
        report["cases"][name] = check_case(name, case, sr, live, ref, inp)
    json.dump(report, open(os.path.join(rdir, "capture_report.json"), "w"), indent=1, default=float)
    lines = [f"# Live capture report — {sr} Hz", "", "| Case | Status | Details |", "|---|---|---|"]
    for k, v in report["cases"].items():
        det = v.get("reason") or "; ".join(f"{c}: {d['value']}" for c, d in v.get("checks", {}).items())
        lines.append(f"| {k} | {v['status']} | {det} |")
    open(os.path.join(rdir, "capture_report.md"), "w").write("\n".join(lines) + "\n")
    counts = {}
    for v in report["cases"].values():
        counts[v["status"]] = counts.get(v["status"], 0) + 1
    print(counts)


if __name__ == "__main__":
    main(int(sys.argv[1]), sys.argv[2])
