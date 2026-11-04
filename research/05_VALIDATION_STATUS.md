# Native gen~ and Ableton Live validation (brief parts 5 and 6)

**Environment:** a Linux cloud VM with no Max/MSP and no Ableton Live. Nothing below was run natively. **No integration result is claimed.**

## Status per item

| Item | V2.1 release | V2.2 Motion candidate | Notes |
|---|---|---|---|
| Native gen~ compilation | **BLOCKED** | **BLOCKED** | Highest risk: multiple-return assignment inside `if`, and 59 (V2.1) or 61 (candidate) History declarations. |
| Max device loading | **BLOCKED** | **BLOCKED** | The .amxd chunk layout parses with Ableton's `maxdiff/amxd_textconv.py`. That checks structure only. |
| Signal routing (plugin~ → gen~ → plugout~) | **BLOCKED** | **BLOCKED** | Wiring verified in the patcher JSON by tests. |
| Mono / stereo operation | **BLOCKED** | **BLOCKED** | [sim] PASS |
| Stereo Link, Dual and Mono | **BLOCKED** | **BLOCKED** | [sim] PASS, including channel isolation and image integrity |
| Parameter mappings | **BLOCKED** | **BLOCKED** | [sim] UI ↔ Param coverage test PASS |
| Automation | **BLOCKED** | **BLOCKED** | |
| Preset save and recall | **BLOCKED** | **BLOCKED** | Candidate adds the `Motion` parameter, default 0. Older presets without it load at 0, which equals V2.1 (to be verified). |
| Project save / reopen | **BLOCKED** | **BLOCKED** | |
| Sample-rate changes | **BLOCKED** | **BLOCKED** | [sim] PASS (reset and dry ramp) |
| Device bypass | **BLOCKED** | **BLOCKED** | Relies on the middle outlet of `live.thisdevice` reporting on/off; unverified. |
| Multiple instances | **BLOCKED** | **BLOCKED** | Proxy: 16 instances measured 33 % (V2.1) and 45 % (all experiments) of one core at 44.1 kHz, single-thread, on this VM. |
| Latency compensation by Live | **BLOCKED** | **BLOCKED** | Max for Live supports a fixed *Defined Latency* patcher attribute. Whether Live compensates it for this device is test L15. |
| GSX ↔ native gen~ differences | **BLOCKED** | **BLOCKED** | Needs native output to compare. The capture kit (`validation/`) does it automatically once renders exist. |

## Known or suspected GSX ↔ gen~ differences (to check first)
1. **Multiple-return assignment inside `if/else`** to variables declared outside the block. It is documented for GenExpr in general, but whether it is allowed inside a block is not documented. If gen~ rejects it, the fallback is to compute both branches and select with `?:`. That costs CPU at ≥ 60 kHz, where the oversampled branch would also run.
2. **History read semantics.** The source never reads a History after writing it in the same frame (enforced by the GSX lint), so this difference cannot affect the shipped code.
3. **`noise()`** follows a different sequence. Only the Click transient uses it, and the capture kit compares that by level, not sample by sample.
4. **Float precision.** gen~ is believed to run in 64-bit. If it does not, expect about −140 dBFS deviations, well inside the −80 dBFS capture tolerance.
5. **`selector` with an out-of-range index, and `log`/`exp` edge values.** The inputs are clamped before these calls, so no edge values reach them.

## Procedure (when Max and Live are available)
1. Open `device/Tubby Filter.amxd` (release) and `experiments/candidate/device/Tubby Filter.amxd` (candidate) in Live. Check the Max console for gen~ compile errors (L1).
2. Run the capture kit for both: `python3 validation/make_signals.py 44100 48000 96000`, render per `validation/LIVE_VALIDATION.md`, then `compare_capture.py`.
   - For the candidate, the existing cases apply with Motion 0. That checks Motion 0 = V2.1 *natively*.
   - Add a Motion case by rendering the C_motion loop automation, and compare against `experiments/renders/C_motion.wav` *before level matching*. That means regenerating it with `match_gain = 0`.
3. Complete L2–L15. Run L13 (CPU Reporter) with 1, 8 and 16 instances at 44.1, 48 and 96 kHz for V2.1 and the candidate.
4. Run the blind ABX listening test on `experiments/renders/` and record it below.

## Listening test record (empty: not performed)

| Comparison | Listener | Preferred | Confidence | Notes |
|---|---|---|---|---|
| A vs C (Motion) | | | | |
| A vs B (Core) | | | | |
| A vs D2 (Kick) | | | | |
| A vs E (Core + Motion) | | | | |
