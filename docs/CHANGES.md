# Changes from v1 to v2

Every change below was measured with `tests/measure.py`, using line-by-line models of the v1 and v2 code at 44.1, 48, 88.2 and 96 kHz.

## Fixed (measured problems in v1)

| v1 problem | Measured in v1 | v2 |
|---|---|---|
| The drive stage `tanh(g·x)/√g` added gain: small-signal gain was √g, so at the default 20 % Drive everything got louder | +2.04 dB at the default, +6.0 dB at 100 % | Calibrated shaper: 0.00 dB small-signal in Unity mode |
| Drive 0 % was not clean: tanh still saturated a 0 dBFS sine | 6.7 % THD, −1.8 dB | Drive 0 is bit-exact clean: 0.00 % THD, 0.00 dB |
| The click was white noise, so its spectrum depended on the sample rate | 17–24 % of audible click energy in 16–20 kHz, and most of the energy above 22 kHz at 88.2/96k | Band-limited, rate-normalised: 6.7–8.4 % in 16–20 kHz at every rate |
| The frequency step took exactly 1 sample, so its sharpness depended on the sample rate | — | 0.5 ms log-domain floor, same at every rate |
| The click fired when a saved set loaded | — | Muted for the first 200 ms |
| No denormal or NaN protection | — | `fixdenorm`/`fixnan` on every state and output (tested) |
| Reso, Drive, Mix and Slope jumped instantly (zipper noise, slope clicks) | — | 10–20 ms one-pole smoothing |
| Controls might not reach gen~ when a set loads | — | `live.thisdevice` pushes all values at load |
| Glide had no effect on the FLAT↔filter crossfade, so a glide from FLAT still snapped in 4 ms | — | Crossfade follows `max(4 ms, Glide)` |

## Added
- **Stereo modes**: Link (default, v1 behaviour), Dual (independent right cutoff), Mono.
- **Drive Cal**: Unity / Peak calibration.
- **Mode**: Drive-only (filter bypassed).
- **Output** level control.
- **Contact-bounce transient**: three bursts instead of a single noise burst. Click is now off when Glide > 0, so gliding is click-free as the brief asks.
- **Safety knee** above +6 dBFS, with a +8 dBFS ceiling.
- **New panel**: big stepped Filter dial, all controls on one face, no menus.

## Kept on purpose
- The TPT state-variable filter, the cutoff steps, both slopes and the Q range. Measured: the filter itself is identical in v1 and v2, so the response curves overlay exactly once drive gain is equal.
- The original parameter names and ranges, for automation and saved-set compatibility.

## Behaviour changes to be aware of
- **Drive now sounds different at the same setting.** v1's drive range topped out at about +12 dB of pre-gain and also raised the overall level. v2 goes to +18 dB with no level rise in Unity mode. Old sets at 20 % will be about 2 dB quieter, which is the v1 gain error being removed.
- **Click is ignored when Glide > 0.** v1 clicked even while gliding.
- **Peak calibration raises low-level material at high drive** (by +16 dB at −18 dBFS with 100 % Drive). It is opt-in and labelled.

## Not done, and why
- **Oversampling the drive**: in M4L this needs `poly~ @resampling`, which adds latency and uses fixed resampling filters. The aliasing trade is documented instead.
- **Correcting the top-step warping at 44.1/48k**: compensating Q does not help (tested), and fixing it properly would need oversampling.
- **Component-tolerance detune per step**: considered, then rejected because it would make the steps less predictable live.
