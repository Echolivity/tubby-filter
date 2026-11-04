> **Superseded for 2.2:** this is the V2.1 document, kept for reference. For 2.2.0-rc1 use `validation/ABLETON_LIVE_12_QA.md` and `validation/V22_RELEASE_READINESS.md`.

# Ableton Live validation — Tubby Filter 2.1.0

**Status: NOT PERFORMED.** No test in this document has been run. The development environment has no Max or Ableton Live. Every result field below is blank on purpose and must be filled in by someone running the real device. Until then, V2.1 is **not certified for release** (see `docs/RELEASE_CHECKLIST.md`).

Record for each run: Live version, Max version, OS, CPU, audio interface, buffer size.

## Part 1 — Automated capture comparison (gen~ inside Live vs reference)

This is the only test that measures the compiled gen~ code. It needs about 30 minutes per sample rate.

1. `python3 validation/make_signals.py 44100 48000 96000` writes the input WAVs, the reference outputs and a `SETTINGS.md` per rate into `validation/signals/<rate>/`.
2. In Live, set **Preferences → Audio → Sample Rate** to the rate under test. Create an audio track, drop `device/Tubby Filter.amxd` on it, and add nothing else.
3. For each case in `SETTINGS.md`:
   1. Put `<case>_in.wav` on the track at bar 1. Turn **Warp off** and keep the clip gain at 0 dB.
   2. Set the device controls exactly as listed. **Click must be 0** unless the case says otherwise.
   3. Choose **File → Export Audio/Video** with: rendered track = this track, length = the clip, **WAV, 32-bit float**, same sample rate, **Normalize off**, **Dither off**, Convert to Mono off.
   4. Save the file as `<case>_live.wav` in a folder, for example `renders/48000/`.
4. Run `python3 validation/compare_capture.py 48000 renders/48000`. It writes `capture_report.md` and `capture_report.json` to that folder. Cases without a render are reported as NOT PERFORMED.

The comparison checks are: sample-exact match with the reference (≤ −80 dBFS peak error), latency (must be 0 samples), frequency response (≤ 0.1 dB), step and impulse response, THD and aliasing, level calibration (≤ 0.05 dB), stereo separation (≤ −120 dB) and the noise floor.

| Rate | Cases PASS | FAIL | NOT PERFORMED | Report file | Tester / date |
|---|---|---|---|---|---|
| 44.1 kHz | | | 12 | | |
| 48 kHz | | | 12 | | |
| 96 kHz | | | 12 | | |

## Part 2 — Integration checks (manual)

| # | Test | Procedure | Pass criterion | Result |
|---|---|---|---|---|
| L1 | Device loads | Drop the .amxd on an audio track. Open the Max window (right-click the device title → Open in Max, then Window → Max Console). | No red errors, no "gen~: compile error". | NOT PERFORMED |
| L2 | Routing | Play stereo material. Check that Filter FLAT with Drive 0 sounds identical to the device switched off. | No level change; both channels present. | NOT PERFORMED |
| L3 | Mono source | Put a mono clip on the track. Try Link and Mono. | Centred; same level in both modes. | NOT PERFORMED |
| L4 | Stereo modes | Use Dual with Filter 1k and Filter R 70. Then switch Link → Dual → Mono while playing. | Left side thinner than right in Dual; mode switches make no click. | NOT PERFORMED |
| L5 | Automation | Draw step automation for Filter, plus Drive and Reso ramps. Play and render. | Steps land on the grid; no zipper noise on ramps. | NOT PERFORMED |
| L6 | Parameter recall | Set every control to a non-default value, save the set, close Live, reopen it. | All 12 controls restored, sound identical, no click on load. | NOT PERFORMED |
| L7 | Preset | Save a device preset (.adv), load it on a new track. | All controls restored. | NOT PERFORMED |
| L8 | V2 set compatibility | Open a set saved with V2 and replace the device with V2.1 (or open with V2.1 in place). | Controls map by name: Tubby Filter, Reso, Drive, Glide, Click, Mix, Slope, Filter R, Output, Stereo, Drive Cal, Mode. | NOT PERFORMED |
| L9 | Sample-rate change | While playing, change the rate 44.1 → 96 → 48 kHz. | No runaway noise or stuck silence; sound returns within 50 ms. | NOT PERFORMED |
| L10 | Transport | Start and stop the transport repeatedly. Stop with the filter resonating (Q 8). | No clicks caused by the device. The tail rings out naturally, because the device doesn't follow the transport. | NOT PERFORMED |
| L11 | Device on/off | Toggle the device's activator while playing (Filter 1k, Drive 60). | Turning it off is Live's own bypass. Turning it on crossfades from dry over 10 ms with no click. Confirm `live.thisdevice` sends 0/1 (Max console: add `[print]` to its middle outlet). | NOT PERFORMED |
| L12 | Click / Glide | Set Click 100 and step Filter at Glide 0, then at Glide 500. | Click is heard in both, at the same level; the filter glides at 500. | NOT PERFORMED |
| L13 | CPU, sustained | Use Ableton's **CPU Reporter** device (github.com/Ableton/maxdevtools, `cpu-reporter`). Run 1, 8 and 16 instances on looping material for 5 minutes at 48 and 96 kHz, buffer 128. | Record the average and peak. There is no fixed limit; compare with V2 on the same machine. | NOT PERFORMED |
| L14 | Load time | Use Ableton's **Load Time Tester** (same repository). | Record the time; compare with V2. | NOT PERFORMED |
| L15 | Latency reporting | Put the device on one of two duplicated tracks. Use FLAT with Drive 0 at 44.1 kHz and sum them with one polarity inverted. | Expected: a very small residual above 10 kHz, because the oversampler group delay is not reported to Live (see Known limitations). Record the residual level. | NOT PERFORMED |

### CPU results (to fill in)

| Instances | 48 kHz avg / peak | 96 kHz avg / peak | V2 at 48 kHz avg / peak |
|---|---|---|---|
| 1 | | | |
| 8 | | | |
| 16 | | | |
