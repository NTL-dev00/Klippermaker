# 5. Using an AI agent to help tune the printer

Nothing on this page is needed to print. Klipper, a slicer and a web browser are enough.

An agent helps with the boring parts: writing test g-code, reading the config, keeping a record of
what you changed and why. That record is the part most people skip, and it is the part that makes
tuning take days instead of weeks.

## What Hermes is

Hermes is an AI agent built by Nous Research. It is not a chat window. It runs on your own computer
and can use tools: run shell commands, read and write files, call web addresses, search the web. You
describe a task in plain English, it plans, runs the commands, reads the output, and reports back.
It also keeps notes between sessions, so it remembers your machine from last week.

Install it on the same laptop you slice on, not on the Raspberry Pi.

**Install and quickstart:** <https://hermes-agent.nousresearch.com/docs>

Linux, macOS, WSL2:

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
hermes setup
```

Windows: use the installer on the Hermes download page, or in PowerShell
`iex (irm https://hermes-agent.nousresearch.com/install.ps1)`.

`hermes setup` asks for a model provider. Any of them works; nothing on this page depends on which.

## How it reaches the printer

Moonraker is a small web server that runs next to Klipper on the Raspberry Pi. Klipper talks to
Moonraker, Moonraker talks HTTP. That is why Mainsail, Fluidd, your browser, a shell script and an
agent can all drive the same printer.

Base address: `http://<PRINTER_IP>:7125`

| To do this | Call |
|---|---|
| See Klipper's state | `GET /printer/info` |
| See whether a print is running | `GET /printer/objects/query?print_stats&virtual_sdcard` |
| See the acceleration limit in force right now | `GET /printer/objects/query?toolhead=max_accel,max_velocity` |
| List files on the printer | `GET /server/files/list?root=gcodes` |
| Read `printer.cfg` off the printer | `GET /server/files/config/printer.cfg` |
| Upload a g-code file | `POST /server/files/upload` |
| Start a file printing | `POST /printer/print/start?filename=<file>` |
| Send one line of g-code | `POST /printer/gcode/script` |
| Read the console history | `GET /server/gcode_store?count=100` |
| Read the Klipper log | `GET /server/files/klippy.log` |

Two things that mislead people:

- `/printer/info` answers `"state": "ready"` **even while printing**. That is Klipper's own state, not
  the print's. Read `print_stats.state` to know what the printer is doing.
- A default Moonraker has no password. Anything on your network can start a print. Keep the printer on
  your own network, and keep the four rules below.

## The four rules that matter

Everything else here is optional. These are not.

| Rule | Why | How you enforce it |
|---|---|---|
| 1. Never change config while printing | A `RESTART` mid-print kills the print, and a half-written config can leave Klipper unable to start | Read-only queries are always fine. Uploads to the `config` root, `RESTART`, `FIRMWARE_RESTART` and `SAVE_CONFIG` wait until `print_stats.state` is `standby` |
| 2. Never let it start a print on its own | A person has to clear the bed: clips, the old part, calipers, a stray hex key. A nozzle through a clip is a dead hotend | It asks, you look, you say go. Say this in your first message of the session |
| 3. Prove the file arrived before printing | A cut-off upload looks like a normal file in the list, and the print fails 40 minutes in | Compare the byte size on the printer with the file on your disk |
| 4. Write every result to a file | A result that only exists in a chat is gone next week, and you will re-run the same test | Keep one `RESULTS.md` beside the test files. One entry per print: what ran, how long, what you saw, what you concluded |

A fifth rule that saves plastic: **one variable per print.** An agent will happily suggest three
changes at once. Refuse.

## The same thing in plain curl

Run these yourself first. Then you know what the agent is doing and can check its work. On Windows,
use `curl.exe` in PowerShell.

**1. Find the address.** Look in your router's DHCP client list, or try the hostname:

```bash
ping <PI_HOSTNAME>.local
curl -s http://<PRINTER_IP>:7125/printer/info
```

You want `"state": "ready"` and a `software_version`. No answer means a wrong address, or Moonraker
is not running. See [troubleshooting](06-troubleshooting.md).

Then set a DHCP reservation in the router: ours moved three times during tuning, and every bookmark
broke with it.

**2. Check that nothing is printing.**

```bash
curl -s "http://<PRINTER_IP>:7125/printer/objects/query?print_stats&virtual_sdcard"
```

`"state": "standby"` and `"is_active": false` is what you want. If it says `printing`, stop here.

**3. Upload the file, without starting it.**

```bash
curl -s -X POST "http://<PRINTER_IP>:7125/server/files/upload" \
     -F "root=gcodes" \
     -F "file=@TEST_ACCEL_CUBE.gcode"
```

The reply contains a `"path"` and a byte `"size"`.

**4. Prove it arrived.**

```bash
ls -l TEST_ACCEL_CUBE.gcode
curl -s "http://<PRINTER_IP>:7125/server/files/metadata?filename=TEST_ACCEL_CUBE.gcode" \
  | grep -o '"size": [0-9]*'
```

The two sizes must match exactly. If they do not, upload again.

**5. Clear the bed, then start it.**

```bash
curl -s -X POST "http://<PRINTER_IP>:7125/printer/print/start?filename=TEST_ACCEL_CUBE.gcode"
```

**6. Watch it without touching it.**

```bash
curl -s "http://<PRINTER_IP>:7125/printer/objects/query?print_stats&extruder&heater_bed"
```

There is also an upload option `-F "print=true"` that starts the print as soon as the upload finishes.
That is exactly what rule 2 forbids, and it is the reason to read a command before letting an agent
run it.

## Tell the agent what the machine is

An agent knows nothing about your printer until you say so. Paste this at the start of a session, or
save it as `printer-notes.md` in the folder you work in:

```text
Ultimaker 2 Extended+, converted to Klipper.
Build volume 225 x 225 x 305 mm. 0.4 mm nozzle. 2.85 mm filament (NOT 1.75).
Long Bowden tube (~700 mm). Single radial part fan.
Controller: ATmega2560 board, 80 steps/mm X/Y. Host: Pi with Klipper + Moonraker.
Printer API: http://<PRINTER_IP>:7125 (Moonraker, no auth).
Tuned values: X/Y rotation_distance 40, Z 16, extruder rotation_distance 8.6227662,
max_velocity 300, max_accel 7000,
square_corner_velocity 5, pressure_advance 0.28, retraction 5.0 mm at 45 mm/s,
nozzle 220 C, bed 60 C, flow 1.0, layer 0.2 mm.
Rules: no [gcode_arcs] here, so G2/G3 fail. No M204 in files, it pins acceleration.
Never change config while printing. Never start a print without asking me.
Verify every upload. Log every result to RESULTS.md.
```

## Three prompts that work

**A calibration test.** State the question, the budget, and how to read the result:

```text
Write a g-code file to find the highest acceleration this printer keeps without a layer shift.
20 mm cube, 2 walls, 30 % infill, constant 60 mm/s, acceleration 2000/3000/5000/7000 in four
equal bands bottom to top. Straight G1 moves only: no G2/G3, no M201/M203/M205/M204. 220 C
nozzle, 60 C bed, bed 225 x 225, start at X100 Y100. Tell me what to look for in each band and
what result means "keep 7000".
```

**A config audit.** Ask for a report, not an edit:

```text
Fetch printer.cfg from http://<PRINTER_IP>:7125/server/files/config/printer.cfg and check it
against the machine facts I gave you. Reply with a table: section, problem, why it matters,
the exact line to change. Do not change anything and do not restart.
```

**A failure diagnosis.** Give it one observation, not your theory:

```text
This 20 mm cube bulges on all four outside corners and the walls between them are clean.
It ran at 40 mm/s with pressure advance 0.28. Give me the three most likely causes in order,
and for each one the cheapest test that rules it in or out. Three maximum.
```

The pattern in all three: one question, a budget, and an output you can check.

## What it is good at, and what it is not

| Good at | Not good at |
|---|---|
| Writing test g-code by hand, including the boring coordinate maths | Seeing the print. A photo gives it a rough idea; your eyes and calipers are the truth |
| Reading `printer.cfg` and `klippy.log` and spotting a contradiction | Hearing a belt, feeling a loose pulley, smelling a hot connector |
| Arithmetic: rotation_distance, flow, layer time, filament use | Knowing whether the bed is clear |
| Remembering the last session and keeping the log straight | Saying "that looks fine": it agrees too easily |
| Suggesting the next single test | Changing hardware, or judging how much risk you want |

Two habits keep it useful:

- **Ask for the evidence.** "Show me the command and its output." If it cannot show both, the claim is
  unverified. It will sometimes be confidently wrong, and the log is what catches it.
- **Make it write the result down.** A tuning session that ends without a `RESULTS.md` entry did not
  happen. The next session starts from that file.
