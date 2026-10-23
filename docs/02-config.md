# 02 - The config file, explained

Klipper does not have a settings screen. It has one text file, `printer.cfg`,
and it re-reads that file every time it starts. Everything the machine does -
how fast it moves, how hot it gets, how much filament it pushes - is a line in
that file.

This page walks through the config in `config/printer.cfg` block by block, then
shows how to load it safely. Read it once with the file open next to you.

Reference: <https://www.klipper3d.org/Config_Reference.html>

## Where the file lives

On the Pi: `~/printer_data/config/printer.cfg`, with `macros.cfg` next to it.

| Do | Why |
|---|---|
| Back up before editing: copy it to `printer-YYYYMMDD.cfg` | Klipper cannot tell you what it looked like yesterday |
| Edit in Fluidd/Mainsail: Machine, then the config file | The web editor uploads and restarts for you |
| Change one thing per restart | If two things break, you learn nothing |
| Never edit below the `SAVE_CONFIG` marker at the bottom | Klipper writes there itself and will overwrite you |

## [mcu] - the printer board

Tells Klipper how to reach the board over USB.

| Setting | Our value | What it means |
|---|---|---|
| `serial` | `/dev/serial/by-id/usb-Ultimaker_BV__www.ultimaker.com__Ultimaker_2.0-if00` | The board's USB name. It stays the same across reboots; `/dev/ttyACM0` does not |

**Check:** on the Pi, `ls /dev/serial/by-id/` should list one Ultimaker entry.
If Klipper answers `Unable to open serial port`, either the path is wrong or
the board has no Klipper firmware flashed yet.

## [printer] - the motion limits

The numbers that apply to every move the machine makes.

| Setting | Our value | What it means |
|---|---|---|
| `kinematics` | `cartesian` | The head moves in X and Y, the bed moves in Z. Plain, no belt math |
| `max_velocity` | `300` mm/s | The fastest the head may ever be asked to go |
| `max_accel` | `7000` mm/s2 | How hard it may speed up and slow down. **The biggest quality number on this machine** |
| `square_corner_velocity` | `5` mm/s | How much speed it may keep through a 90 degree corner. 5 means almost a full stop, which keeps corners sharp |
| `max_z_velocity` / `max_z_accel` | `25` / `30` | Z is a slow lead screw. Keep it slow |

**Why accel matters more than anything else here:** at 500-1500 mm/s2 the head
crawls through each corner, the nozzle sits nearly still, and plastic oozes
outward. That is what makes corner bulges - not pressure advance. 5000-7000
was visibly cleaner on this printer.

**Check:** in the console, `SET_VELOCITY_LIMIT` prints the limits in use. If
they are not 300 / 7000, something changed them at runtime - usually your
slicer. See the `M204` note at the end of this page.

## [stepper_x] and [stepper_y] - the belts

One block per motor: which pins drive it, how far one turn moves it, and where
it is allowed to travel.

| Setting | Our value | What it means |
|---|---|---|
| `step_pin`, `dir_pin`, `enable_pin` | `PA3`, `!PA1`, `!PA5` (X) | Which board pins move this motor. The `!` means "invert this signal" |
| `microsteps` | `16` | Electronic steps inside one motor step. 16 on both drivers |
| `rotation_distance` | `40` | How far the belt moves per motor turn: 2 mm belt pitch x 20 teeth on the pulley |
| `position_endstop` | `0` (X), `225` (Y) | Where the carriage sits when the endstop clicks. X homes to the left, Y homes to the back - that is why the two numbers differ |
| `position_max` | `225` | The far end of travel in mm. This is the 225 mm build width |
| `homing_speed` | `50` mm/s | How fast it slams into the endstop. Slower is gentler, faster is quicker |

Do **not** work out X/Y `rotation_distance` by printing a test part. Klipper's
own docs say the measure-and-trim method is too inaccurate for those axes; use
the belt-and-pulley arithmetic above
(<https://www.klipper3d.org/Rotation_Distance.html>). Cross-check: 200 full
steps x 16 microsteps / 40 = **80 steps/mm**, which is exactly what the
Ultimaker firmware used.

**Check:** `G28 X Y` then `G1 X225 Y225 F3000`. The head should reach the far
corner and stop without `Move out of range`. If it stops short or grinds, the
endstop position is wrong.

## [stepper_z] - the bed

The bed moves up and down on a lead screw. Nothing else moves in Z.

| Setting | Our value | What it means |
|---|---|---|
| `rotation_distance` | `16` | 200 full steps x 16 microsteps / 200 steps per mm = 16 |
| `position_endstop` | `313.400` | The Z coordinate where the top switch clicks - the top of travel is 313.4 mm above the bed at Z=0. **Measured with paper, machine-specific** |
| `position_max` | `315` | Mechanical limit. Usable print height is 305 mm |
| `homing_positive_dir` | `true` | It homes toward the top switch, not the bottom |
| `homing_speed` | `20` mm/s | Slow, because the bed is heavy |

**Check:** home, then `G1 Z0 F600` and slide a sheet of paper under the nozzle.
You want light drag. Digging in means `position_endstop` is too small; floating
means too large. Adjust by 0.05 mm at a time - it is a fine number.

## [extruder] - the filament drive

The motor that pushes filament down a roughly 700 mm tube to the hotend.

| Setting | Our value | What it means |
|---|---|---|
| `rotation_distance` | `8.6227662` | How far filament moves per motor turn. **Measured on this printer** - see below |
| `nozzle_diameter` | `0.400` | Slicer math depends on this |
| `filament_diameter` | `2.850` | **2.85 mm, not 1.75.** Wrong value here silently ruins every print |
| `max_temp` | `275` | The hotend's limit. Do not raise it |
| `max_extrude_only_distance` | `800` | How far it may push in one stand-alone command. The tube is 700 mm, so loading needs more than that. Note: this also disables the guard that catches a malformed file asking for a huge extrude — put it back to 50 once you are done loading |
| `pressure_advance` | `0.28` | Compensation for how squishy the melt is. A weak lever on a long Bowden - 0.20 to 0.92 all looked the same here |
| `control` | `watermark` | A simple heater mode that needs no tuning. Replaced automatically when you run a PID calibration |

That `rotation_distance` is the single most important number in the file. The first value tried
here was `9.133264` — 5.9 % too large (`9.133264 / 8.6227662 = 1.059`), which made every part
under-extruded. It looked like a flow problem, and flow was pushed to 1.176 to hide it. That
1.176 also carried a second bug: the prints were running 30 °C cold. Fix this number first,
then re-measure flow. Do not carry 1.176 forward.

**The measurement (do this yourself, it takes ten minutes):**

1. Heat the nozzle to 220 C and load filament.
2. Mark the filament 120 mm from where it enters the extruder. Measure that
   distance with calipers as precisely as you can.
3. Send `G91` then `G1 E100 F60`. It will take about 100 seconds. Do not use
   the extruder button in the web UI - it pushes too fast and the reading is
   wrong because of pressure.
4. Measure from the extruder body to the mark again.

```
new_rotation_distance = old_rotation_distance * actually_pushed / 100
```

Round to a whole number for X, Y and Z. For the extruder, keep all the
decimals and run it twice if the first result moved more than ~2 %.

## [heater_bed] - the bed heater

| Setting | Our value | What it means |
|---|---|---|
| `heater_pin` | `PG5` | Which output drives the bed |
| `sensor_type` | `PT100 INA826` | This machine uses a PT100 sensor with an amplifier board, not the usual 100k thermistor. Choosing the wrong type reports wildly wrong temperatures |
| `sensor_pin` | `PK2` | Which input reads it |
| `max_temp` | `100` | The glass bed's limit. Do not raise it |

**Check:** set the bed to 60 C and watch the temperature graph. It should climb
steadily and then hold within a degree or two. Big overshoot means it needs a
PID calibration.

## [fan] and [heater_fan]

Two fans, two blocks, and they are not the same thing.

| Block | Pin | What it does |
|---|---|---|
| `[fan]` | `PH4` | The part-cooling fan. The slicer controls it with `M106`. There is one radial fan on this machine, no second fan |
| `[heater_fan hotend_fan]` | `PJ6` | The hotend heatsink fan. Klipper switches it on by itself whenever the nozzle is above 45 C. If it ever stops, the PTFE liner in the hotend cooks and jams |

**Check:** `M106 S255` should start the part fan and `M106 S0` stop it. Reach
in and feel for air; the web UI number is not proof.

## [probe] and [safe_z_home] - not used here

This machine has **no probe**. Z height comes from the top endstop plus the
paper test, so neither block is active; both sit commented out in the config
so you can see the shape of them.

- `[probe]` would tell Klipper where the bed is automatically, and enable
  `BED_MESH_CALIBRATE` for warped glass.
- `[safe_z_home]` would home Z at a fixed X/Y instead of wherever the head is.
  It matters on printers whose Z endstop is a probe. Here Z homes at the top,
  well clear of the bed, so it is not needed.

Add them only if you fit a probe. Do not add a `[probe]` block with made-up
numbers - a wrong `z_offset` drives the nozzle into the glass.

## [include macros.cfg]

One line, and it pulls in `PRINT_START` and `PRINT_END` from the second file.
Klipper reads both files as one config. If you rename `macros.cfg`, change this
line too, or Klipper stops with a file-not-found error.

If you use Mainsail, add a second line, `[include mainsail.cfg]`, for its
PAUSE / RESUME / CANCEL_PRINT macros. Fluidd has its own equivalent.

## Verify the config

Klipper has no separate "check" button. The check happens when it loads the
file, so the safe order is: load it, read the result, and only then move
anything.

| Step | What you do | What good looks like |
|---|---|---|
| 1. Load | Save the file, press **RESTART** (or `RESTART` in the console) | Console ends with `Printer is ready` |
| 2. Read the state | `curl -s "http://<PRINTER_IP>:7125/printer/info"` | `"state": "ready"`. `"state": "error"` means it refused the file - the message is in `state_message` |
| 3. Home | `G28` | Bed rises to the switch and stops, head parks. No grinding, no `Move out of range` |
| 4. Heat | `M104 S220`, then `M190 S60` | Both reach target and hold. If a heater runs away, cut the power |
| 5. Extrude | `G91` then `G1 E100 F60` | 100 mm of filament goes in and comes out of the nozzle |

**When the config is bad, Klipper does not half-run.** It stops in an error
state with heaters and motors off, and the console shows
`Once the underlying issue is corrected, use the "RESTART" command`. That is
safe. Fix the line, restart, repeat.

### The errors you will actually hit

| Message | What it means | Fix |
|---|---|---|
| `Option 'rotation_distance' in section 'stepper_x' must be specified` | A required line is missing or misspelled | Compare that block against the example config |
| `Unable to parse option 'max_accel' in section 'printer'` | The value is not a plain number - often a unit got pasted in | `7000`, not `7000 mm/s2` |
| `Section 'stepper_x' is not a valid config section` | The section name is misspelled or the block is not a real Klipper section | Check spelling; a section name cannot have a typo |
| `Move out of range: 240.000 10.000 0.300` | A move went past `position_max` | Wrong `position_max`, or the slicer's bed size is bigger than 225 x 225 |
| `Move out of range` on Z only, after homing | `position_endstop` is wrong for your machine | Re-measure it with paper |
| `Must home axis first` | You moved the head before `G28` | Send `G28` |
| `Extrude below minimum temp` | The nozzle is below `min_extrude_temp` (170 C by default) | Heat it first: `M104 S220`, `M109 S220` |
| `Unknown command:"G2"` | The file uses arcs and `[gcode_arcs]` is not in the config | Turn arcs off in the slicer, or use straight segments |
| `Unable to open serial port` | `[mcu] serial` does not point at the board | `ls /dev/serial/by-id/` and copy the real name |
| `Klipper reports: error` with no obvious cause | Usually a YAML-style indent or a tab character pasted in | Klipper wants spaces, and section headers start in column 1 |

`Unknown command` is a **warning**, not a stop. That is exactly why a split
`PRINT_START` line is dangerous: the print carries on at the wrong
temperature and nothing looks broken.

## Numbers you must measure yourself

Everything below came off one specific printer on one specific day. Copying
them is a starting point, not a calibration.

| Value | Where | How |
|---|---|---|
| `rotation_distance` (extruder) | `[extruder]` | The 100 mm extrude-and-measure test above |
| `position_endstop` (Z) | `[stepper_z]` | Home, go to Z=0, paper test, adjust by 0.05 mm |
| `position_endstop` (X, Y) | `[stepper_x/y]` | Where the carriage physically stops when the endstop clicks |
| PID values | `[extruder]`, `[heater_bed]` | `PID_CALIBRATE HEATER=extruder TARGET=220` then `SAVE_CONFIG`. Repeat with `HEATER=heater_bed TARGET=60` |
| Driver current | `[output_pin _stepper_*_current]` | Board-specific. Start with the example config values; raise only if steps skip, lower if drivers get hot |

## What is deliberately missing

| Not in the config | Why |
|---|---|
| `[gcode_arcs]` | Off on this machine. Any `G2`/`G3` becomes `Unknown command:"G2"` |
| `[bed_mesh]` | Needs a probe. No probe fitted |
| `[input_shaper]` | Needs an accelerometer to measure ringing. Nice to have, not needed to print |
| Retraction length and speed | Those live in the slicer, not in Klipper. 5 mm at 45 mm/s on this machine |
| `M201`, `M203`, `M205`, `M204`, `T0` | Old Marlin commands. Klipper rejects or ignores them, and `M204 P1500 T1500` silently pins acceleration to 1500 - the slow regime that causes corner bulges. Use a Klipper-flavoured slicer profile |
