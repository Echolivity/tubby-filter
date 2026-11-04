"""Builds 'Tubby Filter.maxpat' and 'Tubby Filter.amxd' from tubby_filter.genexpr.

python3 build_device.py [outdir]   (default ../device/)
The .amxd is the same patcher wrapped in Live's device container:
  "ampf" <u32 LE 4> "aaaa"  |  "meta" <u32 LE 4> 00000000  |  "ptch" <u32 LE n> <patcher JSON> NUL
(chunk layout as read by Ableton's maxdevtools/maxdiff/amxd_textconv.py).
The build is deterministic: same source -> byte-identical outputs. A
build_manifest.json with SHA-256 hashes is written next to the outputs.
"""
import hashlib, json, os, struct, sys

VERSION = "2.1.0"

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "device")
os.makedirs(OUT, exist_ok=True)
code = open(os.path.join(HERE, "tubby_filter.genexpr")).read()
APP = {"major": 8, "minor": 6, "revision": 0, "architecture": "x64", "modernui": 1}

# ---------------------------------------------------------------- gen~ subpatch
def gb(i, text, ni, no, x, y):
    b = {"id": i, "maxclass": "newobj", "text": text, "numinlets": ni, "numoutlets": no,
         "patching_rect": [x, y, 60, 22]}
    if no:
        b["outlettype"] = [""] * no
    return {"box": b}

gen = {"fileversion": 1, "appversion": APP, "classnamespace": "dsp.gen", "rect": [80, 80, 760, 700],
       "boxes": [gb("g-in1", "in 1", 0, 1, 20, 14), gb("g-in2", "in 2", 0, 1, 640, 14),
                 {"box": {"id": "g-code", "maxclass": "codebox", "code": code, "fontface": 0,
                          "fontname": "<Monospaced>", "fontsize": 11, "numinlets": 2, "numoutlets": 2,
                          "outlettype": ["", ""], "patching_rect": [20, 48, 680, 580]}},
                 gb("g-out1", "out 1", 1, 0, 20, 645), gb("g-out2", "out 2", 1, 0, 640, 645)],
       "lines": [{"patchline": {"source": ["g-in1", 0], "destination": ["g-code", 0]}},
                 {"patchline": {"source": ["g-in2", 0], "destination": ["g-code", 1]}},
                 {"patchline": {"source": ["g-code", 0], "destination": ["g-out1", 0]}},
                 {"patchline": {"source": ["g-code", 1], "destination": ["g-out2", 0]}}]}

# ---------------------------------------------------------------- main patcher
boxes, lines = [], []
def link(a, ao, b, bi):
    lines.append({"patchline": {"source": [a, ao], "destination": [b, bi]}})

def obj(i, text, ni, no, x, y, w=80, outs=None, **kw):
    b = {"id": i, "maxclass": "newobj", "text": text, "numinlets": ni, "numoutlets": no,
         "patching_rect": [x, y, w, 22]}
    if no:
        b["outlettype"] = outs or [""] * no
    b.update(kw)
    boxes.append({"box": b})

# vintage desk colours (RGBA 0..1)
PANEL = [0.16, 0.20, 0.17, 1.0]     # dark console green
CREAM = [0.93, 0.89, 0.78, 1.0]
AMBER = [0.96, 0.63, 0.20, 1.0]

boxes.append({"box": {"id": "panel", "maxclass": "panel", "numinlets": 1, "numoutlets": 0,
                      "background": 1, "bgcolor": PANEL, "rounded": 0, "presentation": 1,
                      "presentation_rect": [0, 0, 424, 169], "patching_rect": [700, 10, 60, 40]}})

def comment(i, text, px, py, w=80, size=9.0, color=CREAM, bold=0):
    boxes.append({"box": {"id": i, "maxclass": "live.comment", "text": text, "numinlets": 1,
                          "numoutlets": 0, "fontsize": size, "textcolor": color, "fontface": bold,
                          "presentation": 1, "presentation_rect": [px, py, w, 14],
                          "patching_rect": [700, 60 + len(boxes) * 2, w, 18]}})

comment("title", "TUBBY FILTER", 8, 4, 120, 10.5, AMBER, 1)
comment("sub", "stepped hi-pass · console drive · v2.1", 8, 152, 220, 8.0)

obj("plugin", "plugin~", 2, 2, 30, 330, 60, ["signal", "signal"])
boxes.append({"box": {"id": "gen", "maxclass": "newobj", "text": "gen~ @title tubby_v2_1", "numinlets": 2,
                      "numoutlets": 2, "outlettype": ["signal", "signal"], "patching_rect": [30, 380, 220, 22],
                      "patcher": gen}})
obj("plugout", "plugout~", 2, 0, 30, 430, 60)
link("plugin", 0, "gen", 0); link("plugin", 1, "gen", 1)
link("gen", 0, "plugout", 0); link("gen", 1, "plugout", 1)

# load-time push: every control re-sends its value into gen~ when the device opens
obj("thisdev", "live.thisdevice", 1, 3, 30, 10, 100, ["bang", "int", "int"])
# device on/off state (middle outlet) -> gen~ 'active': DSP state is reset when
# the device is switched back on, so stale filter state cannot click
obj("active-p", "prepend active", 1, 1, 150, 40, 100)
link("thisdev", 1, "active-p", 0); link("active-p", 0, "gen", 0)
UI = []
x = [30]

STEPS = ["FLAT", "70", "100", "150", "250", "500", "1k", "2k", "3k", "5k", "7.5k", "10k"]

def control(i, cls, longname, short, msg, va, prect, outs, info, extra=None):
    va = dict(va)
    va.update({"parameter_longname": longname, "parameter_shortname": short,
               "parameter_initial_enable": 1, "parameter_annotation_name": longname,
               "parameter_info": info})
    b = {"id": i, "maxclass": cls, "numinlets": 1, "numoutlets": len(outs), "outlettype": outs,
         "parameter_enable": 1, "presentation": 1, "presentation_rect": prect,
         "patching_rect": [x[0], 60, prect[2], prect[3]],
         "saved_attribute_attributes": {"valueof": va}}
    if extra:
        b.update(extra)
    boxes.append({"box": b})
    obj(i + "-p", "prepend " + msg, 1, 1, x[0], 290, 100)
    link(i, 0, i + "-p", 0); link(i + "-p", 0, "gen", 0)
    link("thisdev", 0, i, 0)
    x[0] += max(prect[2], 100) + 12

DIALCOL = {"activedialcolor": AMBER, "textcolor": CREAM, "dialcolor": [0.08, 0.1, 0.09, 1.0]}

# big stepped selector (same longname/enum as v1's menu => automation & sets still map)
control("step", "live.dial", "Tubby Filter", "Filter", "knob",
        {"parameter_type": 2, "parameter_enum": STEPS, "parameter_mmax": 11, "parameter_initial": [0]},
        [10, 24, 96, 118], ["", "float"],
        "Stepped high-pass cutoff. FLAT = filter out. Linked/Mono: both sides; Dual: left side.", DIALCOL)
control("stepr", "live.dial", "Filter R", "Filter R", "knobr",
        {"parameter_type": 2, "parameter_enum": STEPS, "parameter_mmax": 11, "parameter_initial": [0]},
        [110, 44, 52, 62], ["", "float"], "Right-side cutoff. Active only in Dual stereo mode.", DIALCOL)

def dial(i, name, lo, hi, init, unit, px, py, msg, info, exp=0.0):
    va = {"parameter_type": 0, "parameter_mmin": lo, "parameter_mmax": hi, "parameter_initial": [init],
          "parameter_unitstyle": unit}
    if exp:
        va["parameter_exponent"] = exp
    control(i, "live.dial", name, name, msg, va, [px, py, 48, 50], ["", "float"], info, DIALCOL)

dial("reso", "Reso", 0.5, 8.0, 1.4, 1, 170, 6, "reso", "Resonance (Q) at the cutoff. 0.707 = no peak.", 2.0)
dial("drive", "Drive", 0.0, 100.0, 20.0, 5, 222, 6, "drive", "Console drive, 0..+18 dB into the saturator.")
dial("outlvl", "Output", -24.0, 12.0, 0.0, 4, 274, 6, "outdb", "Output level in dB.")
dial("glide", "Glide", 0.0, 2000.0, 0.0, 2, 170, 72, "glide",
     "0 = hard switched (with switch transient). Above 0: steps glide over this many ms, no transient.", 3.0)
dial("click", "Click", 0.0, 100.0, 30.0, 5, 222, 72, "click", "Switch transient level (hard-switch mode only).")
dial("blend", "Mix", 0.0, 100.0, 100.0, 5, 274, 72, "blend", "Dry/wet.")

TABCOL = {"activebgoncolor": AMBER, "textcolor": CREAM, "activetextoncolor": [0.1, 0.1, 0.1, 1],
          "bgcolor": [0.08, 0.1, 0.09, 1.0], "fontsize": 8.5}
def tab(i, name, items, init, py, msg, info):
    comment(i + "-lbl", name.upper(), 332, py, 84, 8.0)
    control(i, "live.tab", name, name, msg,
            {"parameter_type": 2, "parameter_enum": items, "parameter_mmax": len(items) - 1,
             "parameter_initial": [init]},
            [332, py + 12, 84, 16], ["", "", "float"], info, TABCOL)

tab("slope", "Slope", ["12dB", "18dB"], 1, 2, "slope", "12 or 18 dB/octave.")
tab("stereo", "Stereo", ["Link", "Dual", "Mono"], 0, 36, "stereo",
    "Link: one setting, identical L/R. Dual: Filter R sets the right side. Mono: sums L+R first.")
tab("comp", "Drive Cal", ["Peak", "Unity"], 1, 70, "comp",
    "Unity: quiet signals keep their level at any drive. Peak: full-scale stays full-scale, quiet material comes up.")
tab("mode", "Mode", ["Filter", "Drive"], 0, 104, "drvonly", "Drive = filter bypassed, drive stage only.")

patch = {"patcher": {"fileversion": 1, "appversion": APP, "classnamespace": "box",
                     "rect": [60, 60, 1200, 520], "openinpresentation": 1, "devicewidth": 424.0,
                     "description": f"Tubby Filter {VERSION} — stepped dub high-pass with console drive",
                     "boxes": boxes, "lines": lines}}
js = json.dumps(patch, indent=1)
open(os.path.join(OUT, "Tubby Filter.maxpat"), "w").write(js)
body = js.encode() + b"\x00"
amxd = (b"ampf" + struct.pack("<I", 4) + b"aaaa" + b"meta" + struct.pack("<I", 4) + b"\x00" * 4 +
        b"ptch" + struct.pack("<I", len(body)) + body)
open(os.path.join(OUT, "Tubby Filter.amxd"), "wb").write(amxd)

def sha(b):
    return hashlib.sha256(b).hexdigest()
manifest = {"version": VERSION,
            "src/tubby_filter.genexpr": sha(code.encode()),
            "device/Tubby Filter.maxpat": sha(js.encode()),
            "device/Tubby Filter.amxd": sha(amxd)}
open(os.path.join(OUT, "build_manifest.json"), "w").write(json.dumps(manifest, indent=1) + "\n")
print(f"built {VERSION}: {len(boxes)} boxes, {len(lines)} lines, {len(amxd)} bytes, amxd sha256 {sha(amxd)[:16]}")
