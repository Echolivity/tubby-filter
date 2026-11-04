# Ableton Live 12 manual QA — Tubby Filter 2.2.0-rc1

**Status: nothing in this document has been run.** Every *Result* field is empty and every status is **NOT TESTED**, to be filled in on the target Windows PC.

**Record:** Live 12 version, Max version (*Preferences → Max for Live → Max version*), Windows version, CPU, audio interface and driver (ASIO), buffer size, sample rate.

**Status values:**
- **PASS / FAIL:** actually executed.
- **BLOCKED:** couldn't be run (say why).
- **NOT TESTED:** not attempted.

## 0. Prepare (about 5 minutes)
1. Build or copy the device. Check `certutil -hashfile "device\Tubby Filter.amxd" SHA256` against `device\build_manifest.json`.
2. Run `py validation\make_signals.py 44100 48000 96000`. This writes `validation\signals\<rate>\` with the input WAVs, the references and `SETTINGS.md`.
3. Create a Live set, *TubbyQA.als*:
   - **Track 1 "DUT":** an audio track with the Tubby Filter 2.2.0-rc1 device.
   - **Track 2 "V2.1":** an audio track with `legacy\v2.1\device\Tubby Filter.amxd`.
   - **Track 3 "DRY":** an audio track with no devices.
   - **Track 4 "CPU":** an audio track with Ableton's *CPU Reporter* device (github.com/Ableton/maxdevtools → cpu-reporter).
4. Put `reports\v22\audio\ref_dry_dub_loop_48k.wav` on tracks 1–3, with Warp off and clip gain 0 dB.
5. Save the set. Keep a copy to reuse.

## Part A — automated capture comparison (compiled gen~ inside Live)
This is the only test that measures the compiled DSP. Do it per rate: 44.1, 48 and 96 kHz.

1. Set *Preferences → Audio → Sample Rate* to the rate under test.
2. For each case in `validation\signals\<rate>\SETTINGS.md`:
   1. Load `<case>_in.wav` on track 1 (DUT) with Warp off, starting at bar 1.
   2. Set the device exactly as listed. **Click must be 0** unless the case says otherwise.
   3. **C14 only:** at 120 BPM, write an automation step for *Tubby Filter* from 150 to 1k at the time listed (1.50 s from the clip start).
   4. *File → Export Audio/Video*: track 1 only, WAV, **32-bit float**, the same rate, **Normalize off, Dither off**, length = the clip.
   5. Save as `renders\<rate>\<case>_live.wav`.
3. Run `py validation\compare_capture.py <rate> renders\<rate>`. Missing renders show as NOT PERFORMED.

| Rate | PASS | FAIL | NOT PERFORMED | Report | Date / tester |
|---|---|---|---|---|---|
| 44.1 kHz | | | 14 | | |
| 48 kHz | | | 14 | | |
| 96 kHz | | | 14 | | |

Cases C01–C12 are V2.1 behaviour with Motion 0, so they must be sample-exact. C13 is Motion 100 at a static cutoff, which must also be sample-exact; that is the "no modulation at rest" proof. C14 is the Motion bloom, compared statistically within ±2 dB.

## Part B — manual checklist

| ID | Area | Procedure | Expected | Result | Status |
|---|---|---|---|---|---|
| L1 | Device loading | Drop the device on a track. *Right-click the title bar → Open in Max*; open *Window → Max Console*. | No red errors; no `gen~` compile error. If gen~ reports a syntax error, record it verbatim: see KI-02. | | NOT TESTED |
| L2 | Loading the V2.1 device | Same for the V2.1 device on track 2. | Loads. If gen~ rejects `f` or `i`, record it (KI-05). | | NOT TESTED |
| G-1 | GUI | Check every control is visible and readable at 100 % and 200 % zoom, and that Motion doesn't overlap Filter R or the footer text. | 13 controls; footer reads "· v2.2". | | NOT TESTED |
| G-2 | GUI | Turn each control and watch the Info View text (hover). | Values and units sensible; Glide and Click texts describe "every step move, at any Glide". | | NOT TESTED |
| F-1 | Cutoff | Play the loop and step Filter through all 12 positions. | FLAT is unfiltered; each step removes more low end; Click sounds on every step (Click 30). | | NOT TESTED |
| F-2 | Resonance | At Filter 500, sweep Reso from 0.5 to 8. | A growing peak; no self-oscillation, even at 8. | | NOT TESTED |
| F-3 | V2.1 equivalence by ear | Mute track 2, set track 1 Motion 0, match settings. Put *Utility* on track 2 with phase invert, unmute, and play both. | Silence (a perfect null). | | NOT TESTED |
| M-1 | Motion: rest | Motion 100, Filter fixed at 1k, play for 30 s. | Sounds identical to Motion 0, with no wobble or modulation. | | NOT TESTED |
| M-2 | Motion: sweep | Glide 300, Motion 0 → 50 → 100; throw Filter between 150 and 5k. | The resonance "sings" during the sweep and relaxes about 0.2 s after it stops; the effect grows with Motion. | | NOT TESTED |
| M-3 | Motion: slow | Glide 2000, Motion 100, slow throws. | Subtle; barely more than Motion 0. | | NOT TESTED |
| M-4 | Motion: hard steps | Glide 0, Click 0, Motion 100; rhythmic steps 3 ↔ 7. | A short resonant bloom on each step, with no build-up over many steps. **KI-01:** listen for a faint tick, then compare `reports\v22\audio\KI01_*` (2/5/10 ms) and record which is preferable. | | NOT TESTED |
| M-5 | Motion: extremes | Reso 8, Motion 100: steps near FLAT/70/100 and near 7.5k/10k, with Drive 100. | Bounded; no runaway; level jumps of a few dB at most (the +6 dBFS knee holds). | | NOT TESTED |
| M-6 | Motion: Dual | Stereo Dual, Filter 1k, Filter R 150, Motion 100; switch Link ↔ Dual repeatedly. | No click and no bloom caused by the mode switch itself. | | NOT TESTED |
| M-7 | Motion: amount change | While gliding, jump Motion 0 → 100. | Level rises as the bloom starts (expected, KI-04), with no click. | | NOT TESTED |
| MIDI-1 | MIDI mapping | *MIDI Map* mode: map Filter, Reso, Motion and Glide to encoders. | Filter steps through all 12 positions; Motion 0–100; mappings survive save and reopen. | | NOT TESTED |
| A-1 | Automation | Draw step automation for Filter, plus ramps for Motion and Reso; play and render. | Steps land on time; the Motion ramp is smooth (no zipper). | | NOT TESTED |
| A-2 | Automation from V2.1 | Copy a V2.1 track's automation of *Tubby Filter* onto the V2.2 device. | Plays identically. | | NOT TESTED |
| P-1 | Preset recall | Set all 13 controls to non-defaults and save as a device preset (.adv); load it on a new track. | All 13 restored. | | NOT TESTED |
| P-2 | V2.1 preset into V2.2 | Save a preset with the V2.1 device, then load it onto the V2.2 device (or replace the device in a V2.1 set). | 12 controls map by name; **Motion = 0**; the sound matches V2.1 (null against track 2). | | NOT TESTED |
| P-3 | Project save and reopen | Save the set, close Live, reopen it. | Every value restored; no click on load; Motion value restored. | | NOT TESTED |
| R-1 | Sample-rate change | Change 44.1 → 96 → 48 kHz while playing. | Audio returns within about 50 ms; no noise burst; no stuck state. | | NOT TESTED |
| R-2 | Transport | Start and stop repeatedly with Reso 8 and Motion 100. | No device-caused clicks; resonant tails ring out naturally. | | NOT TESTED |
| R-3 | Device on/off | Toggle the device activator while playing. | Off = Live bypass. On = a 10 ms crossfade from dry, with no click. | | NOT TESTED |
| PAR-1 | Parallel processing | Track 1 (DUT: FLAT, Drive 0, Mix 100) and track 3 (DRY), same clip; *Utility* phase-invert on track 3; sum on the master. | At 88.2/96 kHz: perfect null. At 44.1/48 kHz: residual rising above about 1 kHz (KI-03). Record the master level. | | NOT TESTED |
| PAR-2 | Internal dry/wet | On the DUT, set FLAT, Drive 0 and Mix 0, 30, 50 and 70; null against the DRY track as in PAR-1. | Same residual at every Mix setting, because the internal dry/wet is phase-aligned ([sim] `test_L02`). | | NOT TESTED |
| L-PDC-1 | Latency compensation | Check that *Options → Delay Compensation* is on. Run PAR-1 at 44.1 kHz and export the master and run `py validation\null_test.py master.wav reports\v22\audio\ref_dry_dub_loop_48k.wav`; record the 125 Hz and 1 kHz bands. | With no latency declared (current): a deep null at 100 Hz, partial at 1 kHz. | | NOT TESTED |
| L-PDC-2 | Declared-latency experiment | In Max, open the device's *Patcher Inspector*, set **Defined Latency = 3**, save as a test copy, and repeat L-PDC-1 with this copy. | If Live compensates: the null at 1 kHz improves (about −40 dB expected). If not: unchanged. Record both. **Do not ship this change from simulation alone.** | | NOT TESTED |
| X-1 | Audio export | Export the loop with automation (Filter, Motion), at 44.1 and 96 kHz. | The file matches the real-time playback; no dropouts. | | NOT TESTED |
| CPU-1 | CPU | CPU Reporter, record after 2 minutes: 1, 8 and 16 DUT instances at 44.1, 48 and 96 kHz, buffer 128. Repeat with V2.1. | Record the average and peak. V2.2 should be within about 10 % of V2.1, with no dropouts. | | NOT TESTED |
| CPU-2 | CPU under Motion | As CPU-1, with Motion 100 and Filter automated every beat. | Same order as CPU-1. | | NOT TESTED |
| LD-1 | Long duration | Loop the set for 60 minutes with Filter automation and Motion 100. | No dropouts, drift, level creep, DC or noise build-up; CPU steady ([sim] `test_S09`: 60 s with no drift). | | NOT TESTED |

### CPU results

| Instances | 44.1 kHz V2.2 avg / peak | 48 kHz | 96 kHz | V2.1 at 48 kHz |
|---|---|---|---|---|
| 1 | | | | |
| 8 | | | | |
| 16 | | | | |

## Part C — listening record (blind, level-matched where indicated)

| Comparison | Files (`reports\v22\audio\`) | Listener | Result |
|---|---|---|---|
| V2.1 vs V2.2 Motion 0 | `ref_v21_*`, `ref_v22_motion0_*` (they null exactly; a sanity check) | | |
| Motion 0 / 50 / 100 | `demo_motion*_levelmatched.wav` | | |
| KI-01 attack choice | `KI01_*attack02ms`, `05ms`, `10ms`, `motion000` | | |
