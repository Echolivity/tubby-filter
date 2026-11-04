# Tubby Filter v2

A stepped dub high-pass filter with console drive, for Ableton Live (Max for Live audio effect).
It is inspired by the switched high-pass on King Tubby's mixing desk. It is a character model built for live performance, not a circuit-accurate clone.

## Install

Drag `device/Tubby Filter.amxd` onto an audio track or return.
If Live refuses the file, open `device/Tubby Filter.maxpat` in Max and choose **File → Save As Device…**. As a last resort, rebuild it by hand from `src/tubby_filter.genexpr` (see *Manual rebuild* below).

## Controls

| Control | What it does |
|---|---|
| **Filter** (big knob) | Stepped high-pass: FLAT · 70 · 100 · 150 · 250 · 500 · 1k · 2k · 3k · 5k · 7.5k · 10k Hz. FLAT takes the filter out. |
| **Filter R** | Right-side cutoff. Only active when Stereo = **Dual**. |
| **Reso** | Resonance (Q 0.5–8). 0.707 gives no peak; 1.4 is the default "desk" bump; 4–8 whistles. |
| **Drive** | Console saturation, 0–+18 dB into the shaper. 0 % is a perfectly clean path. |
| **Output** | Output level, −24 to +12 dB. |
| **Glide** | 0 ms = hard switched, with the switch transient. Above 0, steps sweep over that many ms with no transient. |
| **Click** | Level of the switch transient. Only heard when Glide = 0. |
| **Mix** | Dry/wet. |
| **Slope** | 12 or 18 dB/octave. |
| **Stereo** | **Link**: both sides identical. **Dual**: Filter sets left, Filter R sets right. **Mono**: sums L+R first, which suits mono sources on a stereo track. |
| **Drive Cal** | **Unity**: quiet material keeps its level at any drive setting, and loud peaks get squashed. **Peak**: full-scale stays near full-scale, and quiet material comes up, like pushing a desk. |
| **Mode** | **Filter**: normal. **Drive**: filter bypassed, drive stage only. |

## Playing it

- Map **Filter** to a hardware encoder or knob. Hard switching is the classic move: throw a drum bus or skank up to 1k–3k for a bar, then drop back to FLAT.
- For the "riding the knob" sweep, set Glide to 150–400 ms and turn Reso up to around 3.
- With Drive above 50 % and Drive Cal = Unity, loud hits lose level. That is by design (see the measurements). Use **Output** to make up the gain.
- The Click transient is muted for the first 200 ms after the device loads, so restoring a set never clicks.

## Files

```
device/   Tubby Filter.amxd, Tubby Filter.maxpat      (the device)
src/      tubby_filter.genexpr   gen~ DSP (the single source of truth)
          build_device.py        regenerates device/ from the .genexpr
tests/    model.py               line-by-line Python model of v1 and v2
          measure.py             every measurement in docs/ (python3 measure.py)
docs/     DSP_ARCHITECTURE.md, CHANGES.md, MEASUREMENTS.md, results.json, img/
v1/       the original files, unchanged
```

## Manual rebuild

1. In Live, create a new **Max Audio Effect** and open it in Max.
2. Put `[gen~]` between `[plugin~]` and `[plugout~]`, with left to left and right to right.
3. Inside the gen~, create a `codebox` with two inlets and two outlets, and paste in the contents of `src/tubby_filter.genexpr`.
4. Add a `live.*` control for each parameter. Send its output through `[prepend <name>]` into gen~'s left inlet. The parameter names are `knob knobr reso drive outdb glide click blend slope stereo comp drvonly`.
