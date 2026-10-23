# 7. What we measured

This page is the evidence behind every number in `03-tuning.md`. It is not a tutorial. If you want to know
why a value is what it is, or whether we actually tested it, this is where to look.

Read it two ways: trust the conclusions, and be sceptical of the method. Most of what is below is a human
looking at a printed part, not an instrument. Where we used calipers we say so.

## How we read results

| Method | Used for | How good it is |
|---|---|---|
| Eye, at arm's length and under a light | Corners, stringing, surface, band differences | Good for "clearly better", blind to "slightly better" |
| Fingernail across a corner | Bulge or pinch | Crude but repeatable |
| Calipers, 0.01 mm | Wall thickness, outer dimensions | The only real measurement on this page |
| Ruler against the part | Which band is which | Fine, bands are 2-4 mm apart |

What we did not do: photograph every part at a fixed angle, measure bulge height, or scan surfaces. So
"clean" below means "no visible defect at arm's length", not "within 0.05 mm". Treat the differences
marked *clear* as real and the ones marked *none* as "we could not see it".

Every print used the same filament, 0.2 mm layers, 0.45 mm line width, 220 °C nozzle and 60 °C bed unless
the test varied that. Ten tests on 2026-10-22, six of them timed, all with **zero rejected commands**.

## Every test we ran

| # | Test | What varied | What we measured | Result |
|---|---|---|---|---|
| 1 | Retraction tower, 4 columns | Retraction 0-8 mm, 9 bands | Stringing between columns | Clean from ~6 mm up. Coarse read, later superseded |
| 2 | Retraction pair, 2 cylinders | Retraction 5.0-7.0 mm, 5 bands | The 40 mm dry gap | No stringing at any band, including 5.0 |
| 3 | PA cube at 3000 mm/s² | Pressure advance 0.00-0.80 | Corners and wall after the corner | Clean 0.30-0.40, bulge below, pinch above |
| 4 | Flow cube, 2 tubes | Nothing - one setting | Wall thickness with calipers | 0.40 mm against 0.45 nominal |
| 5 | Accel cube | Acceleration 500-7000 mm/s² | Corners and wall straightness | **5000-7000 clearly better** |
| 6 | Temperature cube | Nozzle 220→195 °C in 5° steps | Surface, corners, band differences | Almost no difference |
| 7 | PA cube at 7000 mm/s² | Pressure advance 0.20-0.92 | Corners and wall after the corner | No visible difference anywhere |
| 8 | Overhang finder v2, hand-built | Overhang angle, 4 arms | Where droop starts | **Failed - test design** |
| 9 | Overhang finder v3, hand-built | Overhang angle, 3 arms | Where droop starts | **Failed - test design**, cancelled |
| 10 | Overhang test, standard model (tomi3d) | Nothing - read the angles | Angle where the underside goes bad | Clean to ~55 deg from vertical; design at 45 |

Print times and filament: test 2 10.3 min / 0.08 m, test 3 13.2 min / 0.53 m, test 4 13.8 min /
0.22 m, test 5 18.4 min / 0.52 m, test 6 12.9 min / 0.32 m, test 7 11.8 min / 0.52 m.

## Band maps

Reading these: the top row is the value in that band, the bottom row is what we saw.

**Pressure advance, 0.00 to 0.80, at 3000 mm/s² (test 3)**

| Band | 0.00 | 0.10 | 0.20 | 0.30 | 0.40 | 0.50 | 0.60 | 0.70 | 0.80 |
|---|---|---|---|---|---|---|---|---|---|
| Corner | bulge | bulge | bulge | clean | clean | pinch | pinch | pinch | pinch |
| Wall start | blobby | blobby | blobby | even | even | thin | thin | gapped | gapped |

That gives a clean window of roughly 0.28 to 0.44. We adopted 0.28, at the low end of it.

**Pressure advance, 0.20 to 0.92, at 7000 mm/s² (test 7)**

| Band | 0.20 | 0.28 | 0.36 | 0.44 | 0.52 | 0.60 | 0.68 | 0.76 | 0.84 | 0.92 |
|---|---|---|---|---|---|---|---|---|---|---|
| Corner | same | same | same | same | same | same | same | same | same | same |

The operator read was "all pretty much the same". This is a null result and we report it as one: on
this machine, at the acceleration we print at, pressure advance does not visibly change the part.

**Acceleration, 500 to 7000 mm/s² (test 5)**

| Band | 500 | 1500 | 3000 | 5000 | 7000 |
|---|---|---|---|---|---|
| Corner | bulge | bulge | slight | clean | clean |
| Side width | - | - | - | 20.2 mm | 20.2 mm |

Bands are 4 mm tall, bottom to top, constant 60 mm/s and constant pressure advance. The part got
**better** as acceleration went up, which is the opposite of what we expected.

**Nozzle temperature, 220 down to 195 °C (test 6)**

| Band | 220 | 215 | 210 | 205 | 200 | 195 |
|---|---|---|---|---|---|---|
| Surface | - | - | - | - | - | - |
| Corners | - | - | - | - | - | - |

Every cell is a dash because there was nothing to write. "Almost no difference" was the read. This
test also produced five blobs, one at each band boundary, because that version of the file parked the
nozzle at the part edge during the temperature wait. The blobs are a bug in the test file, not a
finding about temperature. The generator in `tools/` parks off the part before every wait.

**Retraction length, 5.0 to 7.0 mm (test 2)**

| Band | 5.0 | 5.5 | 6.0 | 6.5 | 7.0 |
|---|---|---|---|---|---|
| 40 mm gap | no string | no string | no string | no string | no string |

Because the lowest band was already clean, this test did not find a minimum - it found a ceiling on
how much retraction you need. The true minimum is below 5.0 mm. Starting the sweep higher than the
answer is the mistake described in `03-tuning.md`.

**Retraction tower, 0-8 mm (test 1)**

Nine bands on a four-column tower. The read was "clean from 65-70 percent of the height upward",
which put the first clean band at 6.0 mm. Test 2 then showed 5.0 mm is clean, so test 1 was reading
the geometry, not the printer: four columns means three dry gaps per layer plus a raft, three times
the travel, and a coarse height judgement. Test 2 matches the standard two-cylinder model and is the
better signal. **We kept 5.0 mm.**

Two tests disagreeing is normal. Trust the one whose geometry matches a real part.

## The logic chain that found the real cause

This is the useful part of the page, because it is how tuning actually goes: not one clean experiment,
but a series of eliminations.

1. **Corner bulges appeared on many prints.** First guess: pressure advance too low.
2. **Test 3 ran at 80 mm/s.** Clean corners at 0.30 and 0.40. So pressure advance was already fine.
3. **Test 4 ran at 40 mm/s and still bulged.** The need for pressure advance *rises* with speed, so at
   half the speed 0.28 should have been too high (pinched), not too low (bulged). It bulged anyway, which
   rules out pressure advance as the cause at any speed.
4. **Test 4 also measured the wall: 0.40 mm against 0.45 nominal.** Not thick, so not over-extrusion, and
   that rules out flow. Had it measured 0.50 mm, this page would end differently.
5. **Test 6 swept temperature 220→195.** No change. That rules out the melt being too hot or too cold.
6. **Test 5 swept acceleration.** 5000-7000 mm/s² was clearly better. That leaves acceleration as the
   only variable that moves the result.
7. **Test 7 swept pressure advance again, this time at 7000 mm/s².** No effect. Confirms step 3 at the
   acceleration we actually print at.

The mechanism that fits: at low acceleration the head dwells near zero speed at each corner, and the
nozzle keeps oozing into that dwell. Numbers are in `03-tuning.md` section 6: 220 ms of slow movement
per corner at 500 mm/s², 16 ms at 7000.

Then the confirmation from history: every old print on this machine was sliced with `M204 P1500 R1500 T1500` in the start G-code.
Klipper reads that as 1500 mm/s², so all of them ran in the bad regime. Every one of them ran in the bad regime.
The defect was not a mystery, it was a slicer line.

## The overhang tests that failed

Two hand-built overhang tests failed in a row. Both failures were the test's fault, and the details are
worth keeping because they are easy to repeat.

| Version | Design | What went wrong |
|---|---|---|
| v2 | 30 mm column, four arms at 30/45/60/75 degrees from horizontal, each arm starting with a flat 5 mm bridge | A flat 5 mm bridge is an extreme overhang at *any* angle. Every arm collapsed on its first layer, so the angle comparison never happened |
| v3 | Arms flush with the column edge, growing per layer, 30/20/10 degrees from vertical, 24.8 mm tall | Each arm was a single 0.45 mm bead carrying a 10 mm shelf, with no brim, and the path retraced the column wall. Too fragile; the nozzle dragged the curled edge and it turned into spaghetti. Cancelled at 17.8 mm of 24.8 |

Nothing in those two prints says anything about the printer - they are here so nobody reads "overhang
tests failed" as "this machine has bad overhangs".

The fix was to stop hand-building geometry and use a model that thousands of people have printed:
"Overhang Test" by tomi3d on Printables, <https://www.printables.com/model/126029-overhang-test>
(CC BY-NC 4.0, attribution required), sliced normally in PrusaSlicer 2.8.1 with the Klipper profile. That
is the right way to measure an overhang ceiling, and the route we recommend in `03-tuning.md`.

**The number:** clean to about **55 degrees from vertical**, rough from roughly 40 on the arm that
faced the fan worst, tips at 50-60 clearly out of range. **45 degrees is the design limit.**

Confidence: medium. This is one visual read of one print, not a measured angle, and the print was
cancelled at 86 percent while the top section was failing - the arms that matter had already been
laid down, but the failure itself was still in progress. Wet filament was present (months open to
air) and would pull the ceiling down, so treat 55 as a fair-weather number and 45 as the one to
design with.

## What this evidence does not prove

- **No retraction minimum.** The sweep started too high, so 5.0 mm is sufficient, not minimal.
- **The overhang number is a visual read**, not a measured angle, and it was taken with slightly wet
  filament. 55 is the observed ceiling; 45 is the design limit.
- **Retraction speed was not swept at all.** 45 mm/s worked and stayed. One data point is not a sweep.
- **Max volumetric flow is not measured.** We run at about 5.4 mm³/s and never reached a limit.
- **One filament, one day.** PLA at 220 °C. PETG or a different brand may want different retraction and
  a different temperature. Pressure advance is unlikely to start mattering, but check.
- **Eye, not instrument.** The acceleration result is a clear visual difference, not a measured one.
- **No input shaper, no bed mesh.** Neither was enabled during any of this, so nothing here says
  anything about ringing or first-layer flatness.

## The numbers that came out of it

| Setting | Value | Confidence |
|---|---|---|
| Retraction length | 5.0 mm | High - no stringing at any band tested |
| Retraction speed | 45 mm/s | Low - never swept, worked first time |
| Pressure advance | 0.28 | Medium - clean zone 0.28-0.44 at 3000, no effect at 7000 |
| Flow | 1.0 | Medium - one caliper reading, at the top rim, 0.40 mm |
| Nozzle temperature | 220 °C | High for "195-220 makes no difference", low for "220 is best" |
| Acceleration | 7000 mm/s² | High - the clearest result on the page |
| Max volumetric flow | not measured | None - open |

**The bulges were low acceleration, caused by one slicer line. Pressure advance was never the problem.**
