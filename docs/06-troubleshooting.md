# 6. Troubleshooting
Work from the symptom. Find your row, run the check, change one thing, write down what happened.

Most of these are not hardware. They are a setting copied from another printer, a file sliced for
another firmware, or two changes made at once.

## Before you change anything
| Do this | Why |
|---|---|
| Read the state: `curl -s http://<PRINTER_IP>:7125/printer/info` | `state` and `state_message` usually name the problem and the line |
| Read the console, not just the web page: `curl -s "http://<PRINTER_IP>:7125/server/gcode_store?count=100"` | Errors from a running print appear here and nowhere else |
| Change one thing | Two changes and one result tells you nothing |
| Know your restarts | `RESTART` reloads the config, `FIRMWARE_RESTART` also resets the board, power-cycling both is the last resort |

## Find your symptom
| Symptom | Entry |
|---|---|
| Nothing on the network, web UI will not load | [1](#1-the-printer-is-not-on-the-network) |
| Klipper says ERROR and will not home | [2](#2-klipper-will-not-start-after-a-config-change) |
| `Unknown command: "G2"` | [3](#3-unknown-command-g2) |
| `Unknown command: "M201"` / `M203` / `M205` / `T0` | [4](#4-unknown-command-m201-m203-m205-t0) |
| `Move out of range` | [5](#5-move-out-of-range) |
| First layer will not stick | [6](#6-the-first-layer-will-not-stick) |
| Corners bulge on square parts | [7](#7-corner-bulges-and-it-is-not-pressure-advance) |
| Strings, hairs, ooze between parts | [8](#8-strings-between-parts) |
| A blob wherever the print paused | [9](#9-a-blob-wherever-the-print-waited) |
| Thin single-wall test collapses | [10](#10-a-thin-single-wall-test-collapses) |
| Layer shifts | [11](#11-layer-shifts) |
| Overhangs droop or curl | [12](#12-overhangs-droop-or-curl-up) |
| Under-extrusion after changing rotation_distance | [13](#13-under-extrusion-after-a-rotation_distance-change) |

## 1. The printer is not on the network
**You see:** the web UI will not load, `ping` gets no answer, the agent cannot reach port 7125.

| Likely cause | Check, then fix |
|---|---|
| Wrong address | Look for the Pi's hostname in the router's DHCP client list, and try `ping <PI_HOSTNAME>.local`. Then set a **DHCP reservation**, because ours moved three times in a month |
| The Pi is not booted | Steady red LED means power, flickering green means SD card activity. No green after 60 s: re-seat the card, check the supply is 5 V / 2.5 A or better |
| Wi-Fi dropped | Plug in Ethernet. If it appears, the fault is Wi-Fi: move the Pi, or keep Ethernet. Losing the host mid-print scraps the print |
| Web UI loads, port 7125 does not | Moonraker is down and Klipper may be fine. Over SSH: `sudo systemctl status moonraker`, then `sudo systemctl restart moonraker` |

## 2. Klipper will not start after a config change
**You see:** `Klipper reports: ERROR`, the printer will not home, nothing moves.

```bash
curl -s http://<PRINTER_IP>:7125/printer/info                       # state + state_message
curl -s http://<PRINTER_IP>:7125/server/files/logs/klippy.log | tail -40 # the real error
```

`state_message` names the file and line. That is almost always the answer.

| Likely cause | Check, then fix |
|---|---|
| Indentation or a tab | Options sit indented under their `[section]` header. Use spaces |
| Duplicate section | `grep -n "^\[" printer.cfg` and look for two of the same name |
| Unknown option | Klipper rejects options it does not know. The log gives the exact name |
| `[include]` of a missing file | `[include macros.cfg]` needs that file in the same folder, exact case |
| Config saved while printing | Look at the end of `printer.cfg` for a `#*# <---- SAVE_CONFIG` block. Restore the backup and redo it |

Then `curl -s -X POST http://<PRINTER_IP>:7125/printer/restart`. Note that `shutdown` is not `error`:
shutdown is a runtime fault (lost MCU, heater error) and usually clears with `FIRMWARE_RESTART`.

## 3. `Unknown command: "G2"`
**You see:** the console shows `Unknown command:"G2"`, or `G3`, and the print keeps going.

Klipper understands arcs only if `[gcode_arcs]` is in `printer.cfg`. It is not on this machine. The
move is **skipped**, not stopped, so the print finishes with a straight chord or a gap where the arc
belonged. That is why it is easy to miss.

Check with `grep -c "^G2\|^G3" yourfile.gcode`, and `curl -s "http://<PRINTER_IP>:7125/printer/gcode/help" | grep -i arc` to see whether arc support is loaded at all.

Fix, in order of preference:

1. Turn arc fitting off in the slicer (Orca and PrusaSlicer both have it) and slice again.
2. Keep hand-written test files straight-line only.
3. Add `[gcode_arcs]` with `resolution: 0.1` and restart. Klipper supports it, but then your files only
   run on machines that also enable it. This guide keeps arcs off so every file behaves the same way.

## 4. `Unknown command: "M201"`, `M203`, `M205`, `T0`
**What it means:** those are Marlin commands. Klipper has no M201/M203/M205 (max acceleration, max
feedrate, jerk) and no `T0` (tools are selected with `ACTIVATE_EXTRUDER`). Its limits live in
`printer.cfg`. They come from an old pre-sliced file or a Marlin-flavoured slicer profile. Find them
with `grep -n "M20[0-9]\|^T0" yourfile.gcode`.

Fix: slice with a Klipper flavour (Orca: printer settings, `G-code flavour: Klipper`). For a file you
did not slice, strip the lines and read the start block by eye:

```bash
grep -v -E "^(M20[0-9]|T0)([^0-9]|$)" in.gcode > out.gcode
```

`M204` is different, because Klipper does accept it. See entry 7.

## 5. `Move out of range`
**You see:** `Move out of range: 226.000 100.000 0.200 [0.000]`. The numbers are X, Y, Z, E.

| Likely cause | Check, then fix |
|---|---|
| Slicer bed larger than the printer | Set the slicer bed to 225 x 225. A 225 mm part plus a 2 mm skirt is already out of range |
| Part placed off-centre | Re-centre it. Stay a few mm inside the nominal volume |
| Prime line or skirt across the edge | Read the first 30 lines of the file. Fix the start macro, not the model |
| Z below the minimum | Homing is wrong, or the file contains a negative Z move |
| Different origin | Klipper's 0,0 is a corner; some profiles use a centred origin. Match them |

Confirm the real limits in `[stepper_x]` / `[stepper_y]`, or query `/printer/objects/query?configfile=settings`.

## 6. The first layer will not stick
| Likely cause | Check, then fix |
|---|---|
| Nozzle too high | Slide a sheet of paper under the nozzle at the centre. Light drag is about right. Adjust in 0.05 mm steps |
| Bed is dirty | Warm water and dish soap, dry, then isopropyl alcohol. A fingerprint is enough to break adhesion |
| Bed too cold | 60 C for PLA, and give it 3 minutes: the surface lags the sensor |
| First layer too fast | 20 mm/s, 0.2 mm high, fan off for layer 1 |
| Not enough squish | A first layer that is round on top is too high. One that looks transparent is too low |

*This machine:* there is no bed probe, so the gap is set mechanically by `position_endstop` in
`[stepper_z]`. Change it 0.05 mm at a time and `RESTART`. `SET_GCODE_OFFSET Z=-0.05 MOVE=1` works
live but is lost on restart, so bake the final number into the config.

## 7. Corner bulges (and it is not pressure advance)
**You see:** all four outside corners of a cube stick out; the flat walls between them are clean.
Measured: 20.0 mm across a wall, 20.5 mm across a corner.

**Cause here: acceleration.** At low acceleration the head slows to nearly zero in each corner and
plastic keeps oozing during the dwell. At high acceleration it crosses the corner too fast to leave a
lump.

| Check | What it told us |
|---|---|
| `curl -s "http://<PRINTER_IP>:7125/printer/objects/query?toolhead=max_accel,max_velocity"` | The limit in force right now. If it reads 1500, something lowered it |
| `grep -n "M204" yourfile.gcode` | Klipper accepts `M204 S1500` and `M204 P1500 T1500`, and that changes the limit **for the rest of the print**. `M204 P1500` on its own is refused, which is why the effect can look random |
| A cube with acceleration bands 500/1500/3000/5000/7000 | 5000 and 7000 were visibly better. This reversed our own guess |
| A pressure-advance cube from 0.20 to 0.92 | No visible change at the operating acceleration. Raising PA goes the wrong way |
| A single wall measured with calipers | 0.40 mm against 0.45 nominal, so it was not over-extrusion either |

Fix, in order:

1. Remove `M204` from the file, or slice in Klipper flavour so the machine's own `max_accel` applies.
2. Set `max_accel: 7000` in `[printer]`. This machine ran 5000-7000 cleanly.
3. Still bulging in **every** band, including 7000? Stop blaming motion: check belt tension, pulley set
   screws and the frame. A loose pulley looks exactly like a corner bulge.

Undo an `M204` without a restart:

```bash
curl -s -X POST "http://<PRINTER_IP>:7125/printer/gcode/script" -H "Content-Type: application/json" -d '{"script":"SET_VELOCITY_LIMIT ACCEL=7000"}'
```

Do not reach for pressure advance first: on a 700 mm Bowden it is a weak lever, and across 0.20-0.92 we
could not see a difference at 3000 or 7000 mm/s².

## 8. Strings between parts
| Likely cause | Check, then fix |
|---|---|
| Retraction is not what you think | Read the slicer. This machine wants 5.0 mm at 45 mm/s; a leftover profile says 4.5 at 35 |
| Wet filament | 2.85 mm PLA takes up water fast. Listen for a crackle or pop, look for steam, and ask whether a spool that used to be clean now strings. Dry at 45-50 C for 4-6 h and re-test before changing a setting |
| Travel moves that do not retract | Some skirt and brim moves run unretracted. Our own test file leaked between two parts from its brim loops and looked like part stringing |
| No z-hop or wipe | z-hop 0.4 mm, wipe 70 %, travel 150 mm/s or more |
| Too hot | Not the lever here: 195-220 C made no visible difference on this machine |

The test that settled retraction: two hollow cylinders 40 mm apart, banded 5.0/5.5/6.0/6.5/7.0 mm. No
stringing at any band, so 5.0 mm is already enough. Less is better: faster prints, fewer clogs.

## 9. A blob wherever the print waited
**You see:** a lump at one height, on every print that paused, changed temperature or changed filament
there. The nozzle sits still and hot against the part while the machine waits, and a pressurised
Bowden keeps feeding plastic for seconds.

Every wait must be wrapped in four steps:

```gcode
M83                  ; relative extrusion (add this if the file uses M82)
G91                  ; relative moves
G1 E-5 F2700         ; retract 5 mm
G1 Z2 F600           ; lift 2 mm
G90                  ; absolute again
G1 X10 Y220 F6000    ; park, off the part
; ... wait, change temperature, pause ...
G1 X.. Y.. F6000     ; return
G91
G1 E5 F2700          ; prime
G90
```

`M109` (wait for temperature), `M190` and `PAUSE` all count as waits.

*This machine:* With only `[pause_resume]` in `printer.cfg`, `PAUSE` retracts nothing. The 1 mm you may have seen comes from Mainsail's or Fluidd's client macro in
the config. On a 700 mm Bowden that is not enough. Define it, or use your own pause macro.

To prove it, print a cube that changes temperature between bands, once without retract-and-park and
once with it. The first grows a blob at every boundary; the second does not.

## 10. A thin single-wall test collapses
**You see:** the wall leans, sags or smears, usually above the first few layers. The next layer is laid
before the one below has cooled: a 20 mm single wall at 40 mm/s is about 2 s per layer, and PLA needs
roughly 4 s at these temperatures.

Check: layer time is wall length divided by speed. A 20 mm square is 80 mm of wall, so 2 s at 40 mm/s.
A 30 mm square is 3 s. Two walls double both.

Fix, cheapest first: slow to 20 mm/s; make the test a 30 or 40 mm square; print two copies at once so
each layer has two walls to cool; or set a minimum layer time in the slicer.

*This machine:* a 20 mm column at about 2 s per layer failed twice; a 30 mm column at about 6 s per
layer held. If a test looks melted rather than printed, check layer time before touching a setting.

## 11. Layer shifts
| Likely cause | Check, then fix |
|---|---|
| Acceleration too high for the mechanics | A shift that starts exactly where an acceleration band starts is the machine stating its limit. Drop `max_accel` to 5000 and re-run the same file |
| Loose pulley set screw | Mark shaft and pulley with a pen, print, look for a slip. Tighten onto the flat, not the round |
| Belt too loose | Pluck it. A low dead thunk is too loose. Both belts the same |
| Driver current too low | A click, or a shift in one direction only. Check the driver's Vref with a meter and its datasheet |
| Cable snag or nozzle strike | Look before clearing the bed. A shift with a witness mark on the part is mechanical |

*This machine:* 7000 mm/s² at 80 steps/mm on an ATmega2560 board is at the top of this hardware. It ran
clean for us, but 5000 is the safe number for tall parts.

## 12. Overhangs droop or curl up
| Likely cause | Check, then fix |
|---|---|
| Not enough cooling | One radial fan, 100 % from layer 2. Check it spins and the duct is not blocked or sagging |
| Angle past the machine's limit | Print a known overhang test and find the angle where the underside stops being clean. Keep real models inside it |
| Too hot, or too fast on overhangs | 215-220 C and 20-30 mm/s on overhang perimeters |
| Curl dragged by the nozzle | Curled edges get hit and torn. z-hop 0.4 mm, and a little more cooling |

*This machine:* measured on the standard Printables model at 220 C, one fan at 100 percent: clean
to about **55 degrees from vertical**, rough from roughly 40 onward on the worst arm, tips at 50-60
out of range. Use **45 degrees as the design limit**. That number assumes dry filament and a
normal slice; wet PLA foams in the nozzle and pulls the ceiling down noticeably, so check the
filament before you blame the fan.

## 13. Under-extrusion after a rotation_distance change
`rotation_distance` is how far filament moves per full turn of the extruder motor
(<https://www.klipper3d.org/Rotation_Distance.html>). A **bigger** number means less plastic for each
mm requested, so a too-large value under-extrudes.

Check, in this order:

1. **Direction.** Did the number go up or down? Up means less plastic.
2. **100 mm extrude-and-measure.** Mark the filament 120 mm above the inlet, ask for 100 mm, measure
   what is left. Hot and slow. One manual extrude longer than `max_extrude_only_distance` (default
   50 mm) is refused with "Extrude only move too long", so use 20 mm steps or raise the limit.
3. **Flow ratio in the slicer.** It should be 1.0. Any other number is hiding a defect.
4. **A single wall, measured.** Below about 0.43 mm against 0.45 nominal is thin.

Fix: `new = old x (requested / actual)`. Asked for 100 mm and got 94 mm: `new = old x 100/94`. Change
one number, restart, measure again.

*This machine:* the **extruder** rotation_distance of 8.6227662 is measured and deployed. The earlier 9.133264 was 5.9 % too large and made
every print under-extruded; a flow ratio of 1.176 was set to hide it. Do not carry 1.176 forward.
