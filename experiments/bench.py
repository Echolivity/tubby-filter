"""CPU benchmark (proxy). python3 experiments/bench.py

Single-threaded wall time of numba-compiled implementations on THIS machine.
Medians of 7 runs of 2 s of audio. "8/16 instances" are measured by actually
running 8/16 independent instances back to back (each with its own state),
not by multiplying. Relative cost only: not gen~ CPU, not Live CPU.
"""
import json, os, platform, statistics, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "tests")); sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import exp_model as X
from gsx import compile_genexpr

def cpu_name():
    try:
        for l in open("/proc/cpuinfo"):
            if l.startswith("model name"):
                return l.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor()

GSX = compile_genexpr(open(os.path.join(HERE, "..", "src", "tubby_filter.genexpr")).read())
rng = np.random.default_rng(5)
VAR = {"V2.1": dict(), "X1 core": dict(core=1, cmode=2), "X2 motion": dict(motion=1),
       "X3b kick": dict(contact=1, ctype=1), "X1+X2+X3b": dict(core=1, cmode=2, motion=1, contact=1, ctype=1)}
R = {"hardware": f"{cpu_name()}, {os.cpu_count()} logical CPUs, {platform.system()} {platform.release()}",
     "method": "median of 7 x 2 s runs, single thread; instances run back to back",
     "results": {}}
for sr in (44100, 48000, 96000):
    n = 2 * sr
    x = rng.uniform(-.5, .5, n)
    scen = {"normal": dict(knob=6, drive=20, reso=1.4, click=30),
            "max drive": dict(knob=6, drive=100, reso=8, comp=0, click=30),
            "intensive modulation": dict(knob=np.repeat(rng.integers(0, 12, n // 64 + 1), 64)[:n].astype(float),
                                         drive=rng.uniform(0, 100, n), reso=rng.uniform(.5, 8, n), glide=10, click=30)}
    X.run(x[:256], x[:256], sr, exp=dict(core=1), knob=1)
    GSX.run(x[:256], x[:256], sr, {})
    for sc, p in scen.items():
        for vn, ex in VAR.items():
            ts = []
            for _ in range(7):
                t0 = time.perf_counter(); X.run(x, x, sr, exp=ex, **p); ts.append(time.perf_counter() - t0)
            med = statistics.median(ts)
            row = dict(ns_per_frame=round(med / n * 1e9, 1), pct_core_1=round(med / 2 * 100, 2),
                       spread_pct=round((max(ts) - min(ts)) / med * 100, 1))
            if sc == "normal" and vn in ("V2.1", "X1+X2+X3b"):
                for k in (8, 16):
                    t0 = time.perf_counter()
                    for _ in range(k):
                        X.run(x, x, sr, exp=ex, **p)
                    row[f"pct_core_{k}_measured"] = round((time.perf_counter() - t0) / 2 * 100, 1)
            R["results"][f"{sr} {sc} {vn}"] = row
        ts = []
        for _ in range(7):
            t0 = time.perf_counter(); GSX.run(x, x, sr, p); ts.append(time.perf_counter() - t0)
        R["results"][f"{sr} {sc} V2.1 shipped source (GSX)"] = dict(ns_per_frame=round(statistics.median(ts) / n * 1e9, 1),
                                                                    pct_core_1=round(statistics.median(ts) / 2 * 100, 2))
    print(sr, "done", flush=True)
json.dump(R, open(os.path.join(HERE, "bench.json"), "w"), indent=1)
