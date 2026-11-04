# V2.2 research (branch `dev/v2.2-research`) — EXPERIMENTAL

Nothing in this folder or in `experiments/` is part of the V2.1 release, and nothing has been merged into `src/` or `main`.

| Document | Contents |
|---|---|
| [01_V21_BASELINE_AUDIT.md](01_V21_BASELINE_AUDIT.md) | V2.1 tree, authority, simulated vs native execution, reproduced results, slow-test fix |
| [02_REFERENCE_RESEARCH.md](02_REFERENCE_RESEARCH.md) | AudioThing Dub Filter, Audio Merge KTBK-1B, Bass Culture: what each says and what is relevant |
| [03_EXPERIMENTS.md](03_EXPERIMENTS.md) | Phase study; X1 inductance; X2 Motion and hysteresis; X3 switching transients; X4 notch; X5 Altec mapping; X7 latency; CPU; listening renders; the Motion candidate |
| [04_EVALUATION_MATRIX.md](04_EVALUATION_MATRIX.md) | Every proposal scored and classified IMPLEMENT / EXPERIMENT / REJECT |
| [05_VALIDATION_STATUS.md](05_VALIDATION_STATUS.md) | Native gen~ and Live validation: all BLOCKED here; procedure; listening record |
| [06_ROADMAP_V22.md](06_ROADMAP_V22.md) | Proposed V2.2 plan with go/no-go gates |

## Reproduce
```
python3 -m pytest -q tests experiments        # 120 tests (99 release suite + 21 candidate)
python3 experiments/run_experiments.py         # experiments/results.json, img/, renders/
python3 experiments/bench.py                   # experiments/bench.json (CPU proxy)
python3 src/build_device.py experiments/candidate/device --candidate experiments/candidate/tubby_filter_v22_candidate.genexpr
```

**Labels used throughout:**
- **[ref-model]**: the research model (`experiments/exp_model.py`).
- **[sim]**: GenExpr source executed by GSX.
- **BLOCKED**: needs Max or Live, which aren't available here.
- **NOT PERFORMED**: listening.
