#!/usr/bin/env python3
"""Generate Klipper calibration G-code for an Ultimaker 2 Extended+ style printer.

WHAT THIS IS
------------
A small, dependency-free generator for the calibration prints in docs/03-tuning.md.
It writes plain 2.85 mm Bowden, Klipper-flavoured G-code: no slicer needed, no
third-party packages, no network.

Why not just slice the tests? Because the tests are bands, and a slicer gives you
one setting per print. Hand-writing them means one print sweeps a whole range.


SUBCOMMANDS
-----------
    retract-pair   two cylinders 40 mm apart - retraction length per band
    flow-cube      two single-wall tubes      - measure the wall with calipers
    accel-cube     one cube                   - acceleration per band
    temp-cube      one cube                   - nozzle temperature per band
    pa-cube        one cube                   - pressure advance per band

Run `python3 make_test_gcode.py <subcommand> --help` for that test's options.


DESIGN RULES
------------
Every rule below exists because breaking it cost us a print. They are not style
preferences.

* No G2/G3 arcs, ever. Arc support is off in this config, so an arc is skipped with
  `Unknown command: "G2"` and leaves a gap. Circles here are 48 straight segments.
* Relative extrusion (`M83`) for the whole file. A stray absolute E reset causes
  a huge retraction or a blob, and relative moves are easy to read in a console.
* Retract on every travel longer than 2 mm, brim travel included. A test that
  skips retraction on the brim produces "strings" that come from the brim, not
  the part, and you spend an hour reading them.
* Retract and park off the part before any wait (`M109`). A nozzle that waits at
  the part edge leaves a blob there - one per band change. Our first temperature
  cube had five of them.
* Set acceleration with `SET_VELOCITY_LIMIT`, never `M204`. Klipper obeys
  `M204 P...T...` (it takes the lower of the two), which is how a slicer silently
  pins a machine to 1500 mm/s2 and ruins every corner.
* Keep the layer time up. A single 0.45 mm wall collapses if a layer takes less
  than about 4 seconds, which is why the flow test uses two tubes, not one.
* Do not disable the motors at the end of a calibration file: the head stays where it
  is and you can inspect the part before clearing the bed.


GEOMETRY NOTES
--------------
Cubes are hollow boxes with two perimeters and no infill. That is enough to read
corners, seams and wall quality, and it uses a third of the plastic of a solid
cube. The seam sits at the middle of the front wall on every layer so the bands
line up and can be compared side by side.


USAGE
-----
    python3 make_test_gcode.py --help
    python3 make_test_gcode.py pa-cube --start 0.00 --stop 0.80 --step 0.10
    python3 make_test_gcode.py accel-cube --accels 500,1500,3000,5000,7000
    python3 make_test_gcode.py temp-cube --temps 220,215,210,205,200,195
    python3 make_test_gcode.py flow-cube --wall 0.45 --speed 40
    python3 make_test_gcode.py retract-pair --bands 5.0,5.5,6.0,6.5,7.0

Output goes to `--out`, or to `<subcommand>.gcode` in the current directory.
An existing file is not overwritten unless you pass `--force`.

Requires Python 3.7+. Written for Klipper on an ATmega2560 board.
"""

import argparse
import math
import os
import sys

# --- Machine constants -------------------------------------------------------
# Ultimaker 2 Extended+ build volume. Change these for another printer.
BED_X = 225.0
BED_Y = 225.0
BED_Z = 305.0

FILAMENT_D = 2.85          # mm. This is 2.85, not 1.75. It changes every E value.

TRAVEL_F = 6000            # mm/min, dry travel
Z_F = 600                  # mm/min, Z moves
FIRST_LAYER_F = 1200       # mm/min, first layer and brim
CIRCLE_SEGMENTS = 48       # straight segments per full circle (no arcs)
RETRACT_TRAVEL_MIN = 2.0   # mm. Shorter hops do not need a retraction.

# Prime line at the front of the bed. Y=20 keeps it clear of the bed clips on a
# UM2, which sit near Y=5 and get hit by a prime line drawn too far forward.
PRIME_Y = 20.0
PRIME_Z = 0.3
PRIME_X0 = 15.0
PRIME_X1 = 165.0

# Where the nozzle waits while the hot end changes temperature: front left,
# away from anything that has been printed.
PARK_X = 15.0
PARK_Y = 30.0


class Gcode:
    """A small G-code writer that tracks the nozzle position.

    Every move goes through this class, because the generator needs the position
    to compute extrusion per move and to know when a travel needs a retraction.
    """

    def __init__(self, line_width, layer_height, nozzle, bed,
                 retract=5.0, retract_speed=45.0):
        self.lines = []
        self.width = line_width
        self.layer_height = layer_height
        self.nozzle = nozzle
        self.bed = bed
        self.retract_len = retract
        self.retract_f = retract_speed * 60.0
        self.x = 0.0
        self.y = 0.0
        self.z = 5.0
        self.retracted = False
        self.total_e = 0.0

    # -- basic output ------------------------------------------------------
    def raw(self, line):
        self.lines.append(line)

    def comment(self, text):
        for part in str(text).splitlines() or [""]:
            self.lines.append(("; " + part) if part else ";")

    def e_per_mm(self):
        """Filament used, in mm, per mm of travel for a full-width bead."""
        area = math.pi * (FILAMENT_D / 2.0) ** 2
        return (self.width * self.layer_height) / area

    # -- moves -------------------------------------------------------------
    def move(self, x=None, y=None, z=None, f=TRAVEL_F):
        parts = ["G1"]
        if x is not None:
            parts.append("X%.3f" % x)
            self.x = x
        if y is not None:
            parts.append("Y%.3f" % y)
            self.y = y
        if z is not None:
            parts.append("Z%.3f" % z)
            self.z = z
        parts.append("F%d" % int(round(f)))
        self.lines.append(" ".join(parts))

    def extrude_to(self, x, y, f):
        """Straight move with extrusion. Relative E, always positive."""
        dist = math.hypot(x - self.x, y - self.y)
        e = dist * self.e_per_mm()
        self.total_e += e
        self.lines.append("G1 X%.3f Y%.3f E%.5f F%d" % (x, y, e, int(round(f))))
        self.x = x
        self.y = y

    def retract(self):
        if self.retracted:
            return
        self.lines.append("G1 E-%.4f F%d" % (self.retract_len, int(self.retract_f)))
        self.retracted = True

    def unretract(self):
        if not self.retracted:
            return
        self.lines.append("G1 E%.4f F%d" % (self.retract_len, int(self.retract_f)))
        self.retracted = False

    def travel(self, x, y, f=TRAVEL_F):
        """Dry move. Retracts first if the move is long enough to string.

        Short hops (a wall width or two, e.g. from the outer wall to the inner
        one) cannot draw a string, and retracting on them adds hundreds of
        pointless retractions to a thin-wall print.
        """
        dist = math.hypot(x - self.x, y - self.y)
        if dist < 0.01:
            return
        if dist <= RETRACT_TRAVEL_MIN:
            self.move(x=x, y=y, f=f)
            return
        self.retract()
        self.move(x=x, y=y, f=f)
        self.unretract()

    # -- machine settings --------------------------------------------------
    def set_accel(self, accel):
        self.lines.append("SET_VELOCITY_LIMIT ACCEL=%d ACCEL_TO_DECEL=%d"
                          % (accel, accel))

    def set_pa(self, value):
        self.lines.append("SET_PRESSURE_ADVANCE ADVANCE=%.3f" % value)

    def wait_for_temp(self, temp):
        """Retract, lift, park off the part, wait for the new temperature.

        The nozzle must not wait over the part: that leaves a blob at the part
        edge, one per band change. Pair this with `return_to`.
        """
        self.retract()
        self.move(z=min(self.z + 5.0, BED_Z - 1.0), f=Z_F)
        self.move(x=PARK_X, y=PARK_Y, f=TRAVEL_F)
        self.lines.append("M109 S%d" % int(temp))
        # The melt has time to ooze while waiting; wipe along the park edge.
        self.move(x=PARK_X + 30.0, y=PARK_Y, f=TRAVEL_F)
        self.nozzle = temp

    def return_to(self, x, y, z, f=TRAVEL_F):
        """Go back to the part after a wait, then restore the nozzle height."""
        self.move(x=x, y=y, f=f)
        self.move(z=z, f=Z_F)
        self.unretract()
        # Extra prime for what oozed away while the nozzle sat at the park point.
        self.lines.append("G1 E0.20000 F%d" % int(self.retract_f))
        self.total_e += 0.2

    # -- file structure ----------------------------------------------------
    def header(self, title, notes):
        self.comment(title)
        for line in notes:
            self.comment(line)
        self.comment("")
        self.comment("Generated by tools/make_test_gcode.py")
        self.comment("Klipper, 2.85 mm filament, relative E, no G2/G3 arcs.")
        self.raw("")
        self.raw("M140 S%d" % int(self.bed))
        self.raw("M104 S%d" % int(self.nozzle))
        self.raw("G28 Z")
        self.raw("G1 Z50 F1200")
        self.raw("G28 X Y")
        self.raw("M190 S%d" % int(self.bed))
        self.raw("M109 S%d" % int(self.nozzle))
        self.raw("G90")
        self.raw("M83")
        self.raw("M107")
        self.raw("")
        self.prime_line()

    def prime_line(self):
        """One fat bead at the front of the bed, then wipe and lift."""
        self.comment("prime line")
        keep = (self.width, self.layer_height)
        self.width, self.layer_height = 0.5, 0.3
        self.move(z=PRIME_Z + 0.2, f=Z_F)
        self.move(x=PRIME_X0, y=PRIME_Y, f=TRAVEL_F)
        self.move(z=PRIME_Z, f=Z_F)
        self.extrude_to(PRIME_X1, PRIME_Y, FIRST_LAYER_F)
        self.width, self.layer_height = keep
        self.retract()
        self.move(z=PRIME_Z + 2.0, f=Z_F)

    def footer(self, part_z):
        self.done_z = part_z
        self.comment("end")
        self.retract()
        self.move(z=min(part_z + 10.0, BED_Z - 1.0), f=Z_F)
        self.raw("M104 S0")
        self.raw("M140 S0")
        self.raw("M107")
        self.move(x=10.0, y=200.0, f=TRAVEL_F)
        self.comment("motors stay energised: the bed hangs on Z and would drop")

    # -- output ------------------------------------------------------------
    def write(self, path, force=False):
        if os.path.exists(path) and not force:
            sys.exit("%s exists. Use --force to overwrite." % path)
        text = "\n".join(self.lines) + "\n"
        with open(path, "w", newline="\n") as fh:
            fh.write(text)
        return len(text)


# --- shared geometry ---------------------------------------------------------

def check_bed(x0, y0, x1, y1):
    """Fail loudly now instead of moving out of range mid-print."""
    if x0 < 1.0 or y0 < 1.0 or x1 > BED_X - 1.0 or y1 > BED_Y - 1.0:
        sys.exit("Geometry (%.1f,%.1f)-(%.1f,%.1f) does not fit the %.0fx%.0f mm "
                 "bed. Reduce --size or --gap, or move --center-x/--center-y."
                 % (x0, y0, x1, y1, BED_X, BED_Y))


def polyline(g, points, f, link=False):
    """Extrude through a list of points. `link` also extrudes the entry move."""
    if link:
        g.extrude_to(points[0][0], points[0][1], f)
    for (x, y) in points[1:]:
        g.extrude_to(x, y, f)


def rect_points(x0, y0, x1, y1, seam_x):
    """Closed rectangle, starting and ending on the front edge at seam_x."""
    return [(seam_x, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0), (seam_x, y0)]


def circle_points(cx, cy, radius, start_angle=math.pi / 2.0):
    """A circle as straight segments. No arcs: this printer rejects G2/G3."""
    pts = []
    for i in range(CIRCLE_SEGMENTS + 1):
        a = start_angle - 2.0 * math.pi * i / CIRCLE_SEGMENTS
        pts.append((cx + radius * math.cos(a), cy + radius * math.sin(a)))
    return pts


def cube_layers(g, cx, cy, size, layers, start_layer, f,
                two_walls=True, brim=0):
    """Print `layers` layers of a hollow box, seam on the mid-front wall."""
    w = g.width
    h = g.layer_height
    inset = w / 2.0
    inset2 = inset + w
    x0, y0 = cx - size / 2.0, cy - size / 2.0
    x1, y1 = cx + size / 2.0, cy + size / 2.0

    for i in range(layers):
        n = start_layer + i
        g.comment("layer %d" % n)
        g.move(z=h + n * h, f=Z_F)

        if brim and n == 0:
            # Brim loops outside the part. Each loop retracts on entry so its
            # travel cannot be mistaken for stringing from the part.
            for k in range(brim, 0, -1):
                pts = rect_points(x0 - k * w, y0 - k * w,
                                  x1 + k * w, y1 + k * w, cx)
                g.travel(pts[0][0], pts[0][1])
                polyline(g, pts, f)
            g.retract()

        outer = rect_points(x0 + inset, y0 + inset, x1 - inset, y1 - inset, cx)
        g.travel(outer[0][0], outer[0][1])
        polyline(g, outer, f)

        if two_walls and (size - 2 * inset2) > w:
            inner = rect_points(x0 + inset2, y0 + inset2,
                                x1 - inset2, y1 - inset2, cx)
            polyline(g, inner, f, link=True)


def band_values(explicit, low=None, high=None, step=None):
    """Either an explicit comma list, or start/stop/step."""
    if explicit:
        values = [v.strip() for v in explicit.split(",") if v.strip()]
        if len(values) < 2:
            sys.exit("Need at least two values, got %r" % explicit)
        return values
    if step in (None, 0):
        sys.exit("--step must not be zero")
    n = int(round((high - low) / step)) + 1
    if n < 2 or n > 20:
        sys.exit("That range gives %d bands; use between 2 and 20." % n)
    return ["%.3f" % (low + i * step) for i in range(n)]


# --- subcommands -------------------------------------------------------------

def cmd_retract_pair(args):
    """Two cylinders 40 mm apart. One retraction length per band."""
    bands = band_values(args.bands, args.first, args.last, args.step)
    radius = args.diameter / 2.0
    total_w = args.diameter * 2.0 + args.gap
    left_cx = args.center_x - total_w / 2.0 + radius
    right_cx = left_cx + args.diameter + args.gap
    check_bed(left_cx - radius, args.center_y - radius,
              right_cx + radius, args.center_y + radius)

    g = Gcode(args.wall, args.layer, args.nozzle, args.bed,
              retract=float(bands[0]), retract_speed=args.retract_speed)
    g.header("RETRACTION LADDER - two cylinders, one dry gap", [
        "Two free-standing cylinders, %.1f mm across, %.1f mm dry gap."
        % (args.diameter, args.gap),
        "Retraction changes every %d layers: %s mm." % (args.layers_per_band,
                                                        " / ".join(bands)),
        "Any plastic in that %.1f mm gap came out of the nozzle. Look there,"
        % args.gap,
        "not at the cylinder walls: no wall is printed across the gap.",
    ])
    g.set_accel(args.accel)
    if args.pa is not None:
        g.set_pa(args.pa)

    layer = 0
    for idx, value in enumerate(bands):
        g.retract_len = float(value)
        g.comment("")
        g.comment("=== BAND %d: retraction %.1f mm at %.0f mm/s ==="
                  % (idx + 1, g.retract_len, args.retract_speed))
        for _ in range(args.layers_per_band):
            g.comment("layer %d" % layer)
            g.move(z=args.layer + layer * args.layer, f=Z_F)
            for cx in (left_cx, right_cx):
                pts = circle_points(cx, args.center_y, radius - args.wall / 2.0)
                g.travel(pts[0][0], pts[0][1])
                polyline(g, pts, args.speed * 60.0)
            layer += 1

    g.footer(g.z)
    return g, "retract-pair"


def cmd_cube(args, kind):
    """One hollow cube. Which parameter changes per band depends on `kind`."""
    speed_f = args.speed * 60.0
    size = args.size
    x0, y0 = args.center_x - size / 2.0, args.center_y - size / 2.0
    x1, y1 = args.center_x + size / 2.0, args.center_y + size / 2.0
    check_bed(x0 - 2 * args.wall, y0 - 2 * args.wall,
              x1 + 2 * args.wall, y1 + 2 * args.wall)

    if kind == "pa":
        values = band_values(None, args.start, args.stop, args.step)
    elif kind == "accel":
        values = band_values(args.accels)
    else:
        values = band_values(args.temps)

    total_h = len(values) * args.layers_per_band * args.layer
    if args.layer + total_h > BED_Z - 2.0:
        sys.exit("Part would be %.1f mm tall, too tall for this machine." % total_h)

    titles = {
        "pa": "PA CUBE - pressure advance per band",
        "accel": "ACCEL CUBE - acceleration per band",
        "temp": "TEMPERATURE CUBE - nozzle temperature per band",
    }
    notes = {
        "pa": ["Pressure advance changes every %d layers: %s."
               % (args.layers_per_band, " / ".join(values)),
               "Read the corners: bulged = too low, pinched inward = too high.",
               "Print at the acceleration you intend to run."],
        "accel": ["Constant %.0f mm/s and constant pressure advance in every band."
                  % args.speed,
                  "Acceleration changes every %d layers, bottom to top: %s."
                  % (args.layers_per_band, " / ".join(values)),
                  "Bulged low down and clean up top = dwell ooze: raise accel."],
        "temp": ["Temperature changes every %d layers, bottom to top: %s C."
                 % (args.layers_per_band, " / ".join(values)),
                 "The nozzle retracts and parks off the part before every wait,",
                 "so a blob at a band boundary is not a park blob."],
    }
    g = Gcode(args.wall, args.layer, args.nozzle, args.bed,
              retract=args.retract, retract_speed=args.retract_speed)
    g.header(titles[kind], notes[kind])

    for idx, value in enumerate(values):
        start_layer = idx * args.layers_per_band
        g.comment("")
        g.comment("=== BAND %d ===" % (idx + 1))
        if kind == "pa":
            g.set_accel(args.accel)
            g.set_pa(float(value))
            g.comment("pressure advance %s" % value)
        elif kind == "accel":
            g.set_accel(int(float(value)))
            if args.pa is not None:
                g.set_pa(args.pa)
            g.comment("acceleration %s mm/s2" % value)
        else:
            g.set_accel(args.accel)
            if args.pa is not None:
                g.set_pa(args.pa)
            g.comment("nozzle %s C" % value)
            g.wait_for_temp(float(value))
            g.return_to(args.center_x, y0 + args.wall / 2.0,
                        args.layer + start_layer * args.layer, speed_f)

        cube_layers(g, args.center_x, args.center_y, size, args.layers_per_band,
                    start_layer, speed_f,
                    two_walls=not args.one_wall, brim=args.brim)

    g.footer(g.z)
    return g, {"pa": "pa-cube", "accel": "accel-cube", "temp": "temp-cube"}[kind]


def cmd_flow_cube(args):
    """Two single-wall tubes. Measure the wall; do not judge it by eye."""
    speed_f = args.speed * 60.0
    size = args.size
    total_w = size * 2.0 + args.gap
    if total_w > BED_X - 20.0:
        sys.exit("Two %.0f mm tubes with a %.0f mm gap do not fit the bed."
                 % (size, args.gap))
    left_x0 = args.center_x - total_w / 2.0
    right_x0 = left_x0 + size + args.gap
    y0 = args.center_y - size / 2.0
    y1 = args.center_y + size / 2.0
    check_bed(left_x0 - 3 * args.wall, y0 - 3 * args.wall,
              right_x0 + size + 3 * args.wall, y1 + 3 * args.wall)

    g = Gcode(args.wall, args.layer, args.nozzle, args.bed,
              retract=args.retract, retract_speed=args.retract_speed)
    g.header("FLOW CUBE - two single walls, measure with calipers", [
        "Two %.1f mm open tubes, one %.2f mm wall each, %.1f mm apart."
        % (size, args.wall, args.gap),
        "Target wall thickness is the line width: %.2f mm." % args.wall,
        "Measure at mid-height, four places per tube. Ignore the top rim:",
        "the last bead has no layer pressing on it and always reads thin.",
        "Two tubes, not one: a single tube is about 2 s per layer, and thin",
        "walls collapse below roughly 4 s per layer.",
        "Every travel longer than 2 mm retracts, brim travel included.",
    ])
    g.set_accel(args.accel)
    if args.pa is not None:
        g.set_pa(args.pa)

    layers = int(round(size / args.layer))
    for i in range(layers):
        g.comment("layer %d" % i)
        g.move(z=args.layer + i * args.layer, f=Z_F)
        feed = FIRST_LAYER_F if i == 0 else speed_f
        for x0 in (left_x0, right_x0):
            if i == 0 and args.brim:
                for k in range(args.brim, 0, -1):
                    pts = rect_points(x0 - k * args.wall, y0 - k * args.wall,
                                      x0 + size + k * args.wall,
                                      y1 + k * args.wall, x0 + size / 2.0)
                    g.travel(pts[0][0], pts[0][1])
                    polyline(g, pts, feed)
                g.retract()
            inset = args.wall / 2.0
            pts = rect_points(x0 + inset, y0 + inset, x0 + size - inset,
                              y1 - inset, x0 + size / 2.0)
            g.travel(pts[0][0], pts[0][1])
            polyline(g, pts, feed)

    g.footer(g.z)
    return g, "flow-cube"


# --- argument parsing --------------------------------------------------------

def add_common(sp, wall=0.45, layer=0.2, speed=60.0):
    sp.add_argument("--wall", type=float, default=wall,
                    help="line width, mm (default %(default)s)")
    sp.add_argument("--layer", type=float, default=layer,
                    help="layer height, mm (default %(default)s)")
    sp.add_argument("--speed", type=float, default=speed,
                    help="print speed, mm/s (default %(default)s)")
    sp.add_argument("--center-x", type=float, default=112.5,
                    help="part centre X, mm (default %(default)s)")
    sp.add_argument("--center-y", type=float, default=112.5,
                    help="part centre Y, mm (default %(default)s)")
    sp.add_argument("--nozzle", type=int, default=220,
                    help="nozzle temperature, C (default %(default)s)")
    sp.add_argument("--bed", type=int, default=60,
                    help="bed temperature, C (default %(default)s)")
    sp.add_argument("--retract", type=float, default=5.0,
                    help="retraction length, mm (default %(default)s)")
    sp.add_argument("--retract-speed", type=float, default=45.0,
                    help="retraction speed, mm/s (default %(default)s)")
    sp.add_argument("--pa", type=float, default=None,
                    help="pressure advance to hold (default: leave as configured)")
    sp.add_argument("--accel", type=int, default=3000,
                    help="acceleration, mm/s2 (default %(default)s)")
    sp.add_argument("--brim", type=int, default=2,
                    help="brim loops on layer 1 (default %(default)s)")
    sp.add_argument("--out", default=None,
                    help="output file (default: <subcommand>.gcode)")
    sp.add_argument("--force", action="store_true",
                    help="overwrite an existing output file")


def build_parser():
    p = argparse.ArgumentParser(
        prog="make_test_gcode.py",
        description="Generate Klipper calibration G-code. 2.85 mm Bowden, "
                    "relative extrusion, no arcs.",
        epilog="How to read each test: docs/03-tuning.md",
    )
    sub = p.add_subparsers(dest="command", metavar="<subcommand>")
    sub.required = True

    sp = sub.add_parser("retract-pair",
                        help="two cylinders, retraction length per band")
    add_common(sp, speed=45.0)
    sp.add_argument("--diameter", type=float, default=10.0,
                    help="cylinder diameter, mm (default %(default)s)")
    sp.add_argument("--gap", type=float, default=40.0,
                    help="dry gap between the cylinders, mm (default %(default)s)")
    sp.add_argument("--bands", default=None,
                    help="retraction lengths, comma separated, mm "
                         "(default: 5.0 to 7.0 in 0.5 steps)")
    sp.add_argument("--first", type=float, default=5.0,
                    help="with --last/--step: first retraction length")
    sp.add_argument("--last", type=float, default=7.0,
                    help="with --first/--step: last retraction length")
    sp.add_argument("--step", type=float, default=0.5,
                    help="with --first/--last: step size (default %(default)s)")
    sp.add_argument("--layers-per-band", type=int, default=10,
                    help="layers per band (default %(default)s)")
    sp.set_defaults(func=cmd_retract_pair)

    sp = sub.add_parser("pa-cube", help="one cube, pressure advance per band")
    add_common(sp, speed=80.0)
    sp.add_argument("--start", type=float, default=0.0,
                    help="first pressure advance value (default %(default)s)")
    sp.add_argument("--stop", type=float, default=0.8,
                    help="last pressure advance value (default %(default)s)")
    sp.add_argument("--step", type=float, default=0.1,
                    help="pressure advance step (default %(default)s)")
    sp.add_argument("--size", type=float, default=20.0,
                    help="cube size, mm (default %(default)s)")
    sp.add_argument("--layers-per-band", type=int, default=10,
                    help="layers per band (default %(default)s)")
    sp.add_argument("--one-wall", action="store_true",
                    help="single perimeter instead of two")
    sp.set_defaults(func=lambda a: cmd_cube(a, "pa"))

    sp = sub.add_parser("accel-cube", help="one cube, acceleration per band")
    add_common(sp, speed=60.0)
    sp.add_argument("--accels", default="500,1500,3000,5000,7000",
                    help="acceleration values, mm/s2 (default %(default)s)")
    sp.add_argument("--size", type=float, default=20.0,
                    help="cube size, mm (default %(default)s)")
    sp.add_argument("--layers-per-band", type=int, default=20,
                    help="layers per band (default %(default)s)")
    sp.add_argument("--one-wall", action="store_true",
                    help="single perimeter instead of two")
    sp.set_defaults(func=lambda a: cmd_cube(a, "accel"))

    sp = sub.add_parser("temp-cube", help="one cube, nozzle temperature per band")
    add_common(sp, speed=60.0)
    sp.add_argument("--temps", default="220,215,210,205,200,195",
                    help="temperatures, C (default %(default)s)")
    sp.add_argument("--size", type=float, default=20.0,
                    help="cube size, mm (default %(default)s)")
    sp.add_argument("--layers-per-band", type=int, default=10,
                    help="layers per band (default %(default)s)")
    sp.add_argument("--one-wall", action="store_true",
                    help="single perimeter instead of two")
    sp.set_defaults(func=lambda a: cmd_cube(a, "temp"))

    sp = sub.add_parser("flow-cube", help="two single-wall tubes to measure flow")
    add_common(sp, speed=40.0)
    sp.add_argument("--size", type=float, default=20.0,
                    help="tube size, mm (default %(default)s)")
    sp.add_argument("--gap", type=float, default=15.0,
                    help="gap between the tubes, mm (default %(default)s)")
    sp.set_defaults(func=cmd_flow_cube)

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    g, name = args.func(args)
    out = args.out or (name + ".gcode")
    size = g.write(out, force=args.force)
    layers = sum(1 for line in g.lines if line.startswith("; layer"))
    print("%s -> %s" % (name, out))
    print("  %d lines, %.1f kB" % (len(g.lines), size / 1024.0))
    print("  %d layers, %.2f mm tall" % (layers, g.done_z))
    print("  filament: %.0f mm" % g.total_e)


if __name__ == "__main__":
    main()
