import json, struct
code = open("tubby_filter.genexpr").read()

def gbox(i, text, ni, no, x, y, **kw):
    b = {"id": i, "maxclass": "newobj", "text": text, "numinlets": ni, "numoutlets": no,
         "patching_rect": [x, y, 60, 22]}
    if no: b["outlettype"] = [""] * no
    b.update(kw); return {"box": b}

gen = {"fileversion": 1, "appversion": {"major": 8, "minor": 6, "revision": 0, "architecture": "x64", "modernui": 1},
       "classnamespace": "dsp.gen", "rect": [100, 100, 700, 600],
       "boxes": [
           gbox("g-in1", "in 1", 0, 1, 30, 20), gbox("g-in2", "in 2", 0, 1, 400, 20),
           {"box": {"id": "g-code", "maxclass": "codebox", "code": code, "fontface": 0, "fontname": "<Monospaced>",
                    "fontsize": 12, "numinlets": 2, "numoutlets": 2, "outlettype": ["", ""],
                    "patching_rect": [30, 60, 600, 440]}},
           gbox("g-out1", "out 1", 1, 0, 30, 520), gbox("g-out2", "out 2", 1, 0, 400, 520)],
       "lines": [{"patchline": {"source": ["g-in1", 0], "destination": ["g-code", 0]}},
                 {"patchline": {"source": ["g-in2", 0], "destination": ["g-code", 1]}},
                 {"patchline": {"source": ["g-code", 0], "destination": ["g-out1", 0]}},
                 {"patchline": {"source": ["g-code", 1], "destination": ["g-out2", 0]}}]}

boxes, lines = [], []
def link(a, ao, b, bi): lines.append({"patchline": {"source": [a, ao], "destination": [b, bi]}})

boxes.append({"box": {"id": "plugin", "maxclass": "newobj", "text": "plugin~", "numinlets": 2, "numoutlets": 2,
                      "outlettype": ["signal", "signal"], "patching_rect": [30, 260, 60, 22]}})
boxes.append({"box": {"id": "gen", "maxclass": "newobj", "text": "gen~ @title tubby", "numinlets": 2, "numoutlets": 2,
                      "outlettype": ["signal", "signal"], "patching_rect": [30, 320, 200, 22], "patcher": gen}})
boxes.append({"box": {"id": "plugout", "maxclass": "newobj", "text": "plugout~", "numinlets": 2, "numoutlets": 0,
                      "patching_rect": [30, 380, 60, 22]}})
link("plugin", 0, "gen", 0); link("plugin", 1, "gen", 1)
link("gen", 0, "plugout", 0); link("gen", 1, "plugout", 1)

steps = ["FLAT", "70", "100", "150", "250", "500", "1k", "2k", "3k", "5k", "7.5k", "10k"]
x = 30
def ui(i, cls, name, short, ptype, extra, px, pw, ph, msg, outtypes):
    global x
    va = {"parameter_longname": name, "parameter_shortname": short, "parameter_type": ptype,
          "parameter_initial_enable": 1}
    va.update(extra)
    boxes.append({"box": {"id": i, "maxclass": cls, "numinlets": 1, "numoutlets": len(outtypes),
                          "outlettype": outtypes, "parameter_enable": 1, "presentation": 1,
                          "presentation_rect": [px, 8, pw, ph], "patching_rect": [x, 40, pw, ph],
                          "saved_attribute_attributes": {"valueof": va}}})
    boxes.append({"box": {"id": i + "-p", "maxclass": "newobj", "text": "prepend " + msg, "numinlets": 1,
                          "numoutlets": 1, "outlettype": [""], "patching_rect": [x, 200, 90, 22]}})
    link(i, 0, i + "-p", 0); link(i + "-p", 0, "gen", 0)
    x += max(pw, 95) + 10

ui("step", "live.menu", "Tubby Filter", "Filter", 2,
   {"parameter_enum": steps, "parameter_mmax": 11, "parameter_initial": [0]}, 10, 70, 20, "knob", ["", "", "float"])
dial = ["", "float"]
def d(i, name, lo, hi, init, unit, px, msg):
    ui(i, "live.dial", name, name, 0, {"parameter_mmin": lo, "parameter_mmax": hi, "parameter_initial": [init],
                                         "parameter_unitstyle": unit}, px, 44, 48, msg, dial)
d("reso", "Reso", 0.5, 8.0, 1.4, 1, 90, "reso")
d("drive", "Drive", 0.0, 100.0, 20.0, 5, 140, "drive")
d("glide", "Glide", 0.0, 2000.0, 0.0, 2, 190, "glide")
d("click", "Click", 0.0, 100.0, 30.0, 5, 240, "click")
d("blend", "Mix", 0.0, 100.0, 100.0, 5, 290, "blend")
ui("slope", "live.tab", "Slope", "Slope", 2,
   {"parameter_enum": ["12 dB", "18 dB"], "parameter_mmax": 1, "parameter_initial": [1]},
   10, 70, 20, "slope", ["", "", "float"])
boxes[-2]["box"]["presentation_rect"] = [10, 36, 70, 20]

patch = {"patcher": {"fileversion": 1, "appversion": gen["appversion"], "classnamespace": "box",
                     "rect": [100, 100, 900, 480], "openinpresentation": 1, "devicewidth": 345.0,
                     "boxes": boxes, "lines": lines}}
js = json.dumps(patch, indent=1)
open("Tubby Filter.maxpat", "w").write(js)
body = js.encode() + b"\x00"
amxd = b"ampf" + struct.pack("<I", 4) + b"aaaa" + b"meta" + struct.pack("<I", 4) + b"\x00" * 4 + b"ptch" + struct.pack("<I", len(body)) + body
open("Tubby Filter.amxd", "wb").write(amxd)
print("ok", len(boxes), len(lines))
