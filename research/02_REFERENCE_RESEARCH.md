# Reference research

**Access notes.** The three URLs in the brief couldn't be fetched directly from this environment, so the same material was reached through search results:
- AudioThing: its official user guide (PDF), plus press coverage.
- KTBK-1B: dealer pages (Turnlab, KMR Audio, Soundgas) that reproduce the manufacturer's specifications.
- Bass Culture: the article itself, but only the free introduction; the rest is paywalled.

**Measurement status.** Neither the AudioThing plug-in nor the KTBK-1B hardware was available here, so **no measurement of either reference was possible (BLOCKED).** Everything below is what their documentation states. It is not an observed behaviour.

## A. AudioThing Dub Filter

Sources: [user guide v1.0 (PDF)](https://www.audiothing.net/docs/AudioThing_DubFilter.pdf), [Synth Anatomy](https://synthanatomy.com/2024/04/audiothing-dub-filter-a-king-tubb-big-knob-high-pass-filter-emulation-for-mac-win-and-ios.html), [rekkerd.org](https://rekkerd.org/audiothing-launches-dub-filter-vintage-high-pass-filter-plugin/).

| Control | Documented behaviour | Tubby Filter equivalent |
|---|---|---|
| Cutoff | Stepped, about 70 Hz–7.5 kHz, 11 positions including off | **Filter** (FLAT + 70 Hz–10 kHz) |
| Impedance | Resonance of the high-pass | **Reso** |
| Extra HP | Off gives 12 dB/oct, on gives 18 dB/oct | **Slope** |
| Mode | Two sets of cutoff frequencies | none |
| **Magnetism** | Controls the non-linear model of the inductance; shapes the slope and intensity of the harmonics | none (see X1) |
| **Character** | Controls how non-linear the filter is, and so how many harmonics it adds | none (see X1) |
| **Dynamics** | Controls how smoothly the frequency changes in the non-linear inductance model; at extremes it can sound like an envelope filter | none (X1 inductance variant is the closest; see below) |
| **Artefacts** | Volume of the clicks and noises when the filter is turned | **Click** |
| Soft Clip | Output soft clipping | Safety knee (not user-facing) |
| LFO, envelope follower | Modulate the cutoff | none |

**Interpretation, labelled as inference.** The guide says "Dynamics" sets how smoothly the *inductance model* changes frequency, and that at extremes it acts like an envelope filter. The most plausible reading is a signal-dependent cutoff: an inductance that varies with current makes the cutoff follow the signal level. That is what experiment **X1, inductance variant** implements. It could not be compared with the plug-in. Magnetism and Character appear to set the shape and amount of the same non-linearity.

**Not adopted on principle.** LFO and envelope-follower modulation would turn Tubby into a modulation effect, and Live already provides LFO and envelope modulation through its own devices and Modulators. Soft Clip duplicates what Live already offers.

## B. Audio Merge KTBK-1B (Altec 9069B replica)

Sources: [Turnlab](https://www.turnlab.be/audio-merge-ktbk-1b-altec-9069b-filter.html), [KMR Audio](https://kmraudio.com/products/audio-merge-ktbk-1b-king-tubby-s-big-knob), [Soundgas](https://soundgas.com/products/audio-merge-king-tubbys-big-knob-ktbk).

| Characteristic | Documented | Relevance to Tubby (measured where noted) |
|---|---|---|
| Topology | Passive LC, 3rd-order high-pass; the original Altec used a toroidal-inductor T-network | Tubby's Slope 18 = 2-pole + 1-pole. **Measured [ref-model]:** Reso 1.0 + 18 dB matches an ideal 3rd-order Butterworth high-pass within 0.08–0.10 dB at 44.1–96 kHz (X5). Assuming the 600 mode is close to Butterworth (a passive doubly-terminated LC ladder normally is), **the original response already exists in Tubby at Reso 1.0.** This is a hypothesis; the actual 9069B curve has not been measured. |
| Cutoffs | 70, 100, 150, 250, 500, 1k, 2k, 3k, 5k, 7.5k | Identical to Tubby's steps 1–10. Tubby adds 10 kHz and FLAT. |
| Multi-tap inductor, stepped rotary switch | The cutoff changes by switching inductor taps | Motivates X3b, the inductive kick when a tap is switched. |
| Mode "600" | Original response, **6 dB insertion loss** | Not emulated. A level drop doesn't serve a plug-in that already has Output. |
| Mode BELL | Resonant peak above the cutoff, 0 dB insertion loss; sweeping it blended with dry gives phasing | Already present: Reso > 1 gives the bell. **Measured:** at Mix 50 % the dry + high-pass sum has a −9 to −14.5 dB dip at 0.78–0.87 × cutoff (phase cancellation). This is the phasing effect described, and it moves with the step. |
| Mode NOTCH ("vari-notch") | Attenuation increases with frequency | **X4** prototype: SVF notch whose depth grows with the step (−8 dB at 100 Hz, −20 dB at 3 kHz). |
| Damping | One control, 6 levels, Bell and Notch only | Tubby's continuous Reso covers this. |
| THD | **< 0.01 % at 1 kHz, +17 dBu**; maximum input +38 dBu | **Key finding:** at normal levels the hardware is essentially linear. Inductor saturation in the real unit only appears far above line level. Any "magnetic" distortion in software is a creative character choice, not a replica of what this hardware measurably does. |
| Switching | Passive band switching can click, especially with low-frequency material | V2.1's Click is signal-independent noise. **X3b (inductive kick)** reproduces the low-frequency dependence: measured louder for 60–100 Hz content than for 3 kHz, and silent on silence. |
| Usage | Before an echo or reverb send, or in parallel for phasing | Documentation and routing guidance, not DSP. |

## C. Bass Culture — "The Heart of Dub: Filter Sweeps & Movement"

Source: [Bass Culture (Dubmatix)](https://bassculture.substack.com/p/the-heart-of-dub-filter-sweeps-and). Only the free introduction is readable; the tutorials are paywalled.

What the readable part says:
- The hi-hat is a typical filtered element, as on *King Tubby Meets Rockers Uptown*.
- A hands-on filter gives more room for spontaneity; the article suggests a rotary knob on a MIDI controller.
- Knob moves can be written as automation, so the gesture becomes part of the track.

The article doesn't cover sweep speeds, timing, or delay and reverb interaction in the readable part. KTBK's own guidance supplies the routing point: place the filter before the echo or reverb send.

**Implications for Tubby** (musical reasoning, not measurement):
1. **The gesture is the instrument.** How the knob moves (speed, direction, a quick throw versus a slow ride) is the expressive content, and V2.1 only responds to *where* the knob is. That is the case for X2, movement-dependent behaviour.
2. **Responsiveness matters more than precision.** The Filter step dial must map cleanly to MIDI encoders; the V2 enum dial already does.
3. **Filter before delay.** The character of the filter's movement gets multiplied by the echoes, so transient and resonance behaviour during movement matters more than static curves. This is a documentation point.

## Summary: what the references justify

| Idea | Supported by | Verdict input |
|---|---|---|
| Signal-dependent inductance (level-dependent cutoff, harmonics near the cutoff) | AudioThing Magnetism, Character, Dynamics (documented intent) | Creative, not authentic (the KTBK is linear at line level). Worth testing → X1 |
| Behaviour that depends on movement | Bass Culture (gesture), AudioThing Dynamics (smooth frequency change) | The central research question → X2 |
| Switching transient that depends on the signal, louder with bass | KTBK (clicks especially with low-frequency material) | → X3b |
| 3rd-order passive response | KTBK, Altec | Already available at Reso 1.0 + 18 dB (X5). Needs no new mode. |
| Bell | KTBK | Already Reso > 1 |
| Vari-notch | KTBK | → X4 |
| Insertion loss, 600 Ω impedance behaviour | KTBK | Not useful in software |
| LFO, envelope follower, soft clip | AudioThing | Out of scope; Live provides them |
