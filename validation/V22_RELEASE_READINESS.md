# Tubby Filter 2.2.0-rc1 — release-readiness assessment

## Decision: **D. BLOCKED**

The native environment needed for critical validation is unavailable, so that validation remains incomplete. Every automated check that *can* run here has run, and all of them pass except one deliberately unrelaxed criterion (KI-01). **Native gen~ compilation, which decides whether the device works at all, has not been performed,** and neither has anything in Ableton Live.

### Why not the other options
- **A. Release Candidate** requires "all critical automated **and native** tests passed". No native test has been run.
- **B. Conditional RC** presumes the core implementation is shown to be sound. That holds in simulation only. Whether gen~ accepts the source (KI-02: 14 multiple-return assignments inside `if/else` blocks) is unknown, and a compile failure would be a total failure, not a "non-critical issue".
- **C. Not Ready** would need a demonstrated technical, DSP, regression or stability defect. None remains in the evidence:
  - regression is bit-identical;
  - stability tests pass;
  - KI-01 is a measured, bounded trade-off awaiting a listening decision, not a fault.

### Path out of BLOCKED

| Step | Outcome needed | Result |
|---|---|---|
| 1 | QA **L1**: the device loads and gen~ compiles with no console errors | → if it fails: fix per KI-02 contingency, re-run all tests |
| 2 | QA **Part A** at 44.1 / 48 / 96 kHz: C01–C14 PASS (proves the native output equals the reference, including Motion 0 = V2.1 and a static cutoff = Motion 0) | → **B** |
| 3 | Decide KI-01 by listening (QA M-4, Part C). If the attack changes: one constant edit, rebuild, re-run every test | |
| 4 | QA Part B items: G, F, M, MIDI, A, P, R, PAR, L-PDC, X, CPU, LD | → **A** |

## Evidence summary
Full lists: `V22_TEST_RESULTS.md` (generated from JUnit), `V22_COMPARISON_REPORT.md`, `V22_MOTION_VALIDATION.md` and `V22_LATENCY_PHASE.md`.

| Area | Level | Result |
|---|---|---|
| Environment | recorded | Ubuntu 24.04.5 VM, 2 vCPU Xeon 2.1 GHz, 7.8 GB RAM; Python 3.13.18, numpy 2.5.3, scipy 1.18.1, numba 0.68.1, pytest 9.1.1; gcc 13.3, clang 18.1, Node 22.23; ffmpeg present; **no audio device; no Max; no Ableton Live; no gen~** |
| V2.1 preserved | executed | `legacy/v2.1` SHA-256-pinned; `--v21` rebuilds the V2.1 .amxd byte-for-byte; the V2.1 regression suite passes on V2.1: **101/101** |
| V2.1 regression (Motion 0) | [sim] executed | **Bit-identical:** 35/35 report cases (7 signals × 5 rates); R01–R11 in the suite; the audio null peak is 0.0 |
| Motion behaviour | [sim] executed | All 10 scenarios measured. Trajectory bit-identical; no effect at rest (bit-identical); bloom +0.3 to +6.5 dB rising with speed; decay −21.5 dB at 0.3 s; no accumulation; no self-oscillation |
| Defects fixed | executed | FX-01 (bloom release ignored spec), FX-02 (gen name collisions), FX-03 (wrong help texts), FX-04 (labels and versions) |
| Automated suite | [sim] executed | **231 PASS, 2 FAIL** (strict xfail KI-01 at 44.1 and 96 kHz), 0 NOT TESTED |
| Frequency response, stability, latency | [sim] executed | Unchanged from V2.1. No NaN, Inf, DC, runaway, drift or subnormals in any test (60 s long-run included) |
| gen~ compatibility | static audit (inspection, **not** compilation) | No issues against the official operator lists (the 14 multiple-return-in-block assignments remain a compile risk) |
| Native gen~ compilation | — | **BLOCKED** |
| Ableton Live 12: all items | — | **BLOCKED** (procedure: `ABLETON_LIVE_12_QA.md`) |
| PDC / latency declaration | [sim] analysed | Not justified across the band or across rates; not implemented; Live test L-PDC-2 decides |
| Listening | — | **NOT TESTED** (no audio device). Renders provided |
| Real CPU | — | **BLOCKED.** Proxy: 0–15 % over V2.1 (research benchmark, noisy VM) |
| Ableton `.als` test project | — | **NOT TESTED / not produced.** It can't be checked without Live; QA §0 builds one in about 5 minutes |
