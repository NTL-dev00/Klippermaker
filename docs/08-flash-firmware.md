# 8. Flash Klipper onto the printer board

Page [01](01-get-started.md) put Klipper on the Pi and never touched the printer, which still
runs Marlin. Until this is done the two halves cannot talk and [02](02-config.md) cannot work,
so read this page in that order: 01, then this, then 02.

> ## Warning: this is the only step that can brick the board
>
> - A write that starts and does not finish leaves the printer unable to boot. It is
>   recoverable (Step 8), but needs a programmer. And never unplug USB, close the terminal
>   or switch the printer off while `avrdude` is writing.
> - Never flash the **ATmega16U2** beside the 2560. It is what puts the printer on USB.
> - Read Step 5 completely before running it.

## Which method, and why

| Method | You need | When |
|---|---|---|
| avrdude over USB | nothing: the Pi and your USB cable | First. This is what Cura itself does |
| USBasp or Arduino-as-ISP | a cheap programmer, six wires | USB upload fails twice, or the board is blank |
| SD card or "signed" file | - | Does not exist for Klipper |

The stock Ultimaker 2 bootloader behaves like an Arduino Mega bootloader: it takes a firmware
file over USB and speaks `stk500v2`, which avrdude calls `wiring`. Cura updates Ultimaker
firmware that way, and it also offers *Upload custom firmware*.

**Evidence level:** this is well documented for the board family, but Ultimaker never promised
third-party firmware, so do not take it on faith. The read-only probe in Step 5a settles it in
ten seconds, without writing anything to the board. If the probe fails, the ISP route in Step 5b
always works.

No SD-card route exists: the open-source replacement bootloader documents an SD upgrade, but
the code is commented out ([UltiBoot](https://github.com/daid/UltiBoot)). SD files print.

## Step 1 — Tools, and a quiet port

```
sudo apt update
sudo apt install -y gcc-avr binutils-avr avr-libc avrdude libncurses-dev
cd ~/klipper
sudo service klipper stop
```

Klipper's own script installs exactly these
([install-debian.sh](https://github.com/Klipper3d/klipper/blob/master/scripts/install-debian.sh)).
Stopping Klipper matters: it holds the serial port, and avrdude needs it free.

**You should see:** `avr-gcc --version` prints a version. **If you don't:** `Unable to locate
package gcc-avr` means stale lists, so `sudo apt update` again; `Unit klipper.service not
found` means another service name, found with `systemctl list-units | grep klipper`.

## Step 2 — `make menuconfig`, the five answers

```
make menuconfig
```

| Question | Answer | Note |
|---|---|---|
| Micro-controller Architecture | **Atmega AVR** | |
| Processor model | **atmega2560** | The board's main chip |
| Processor speed | **16Mhz** | Usually hidden; 16 MHz is the built-in default |
| Communication interface | **UART0** | Usually hidden; also the default |
| Enable extra low-level configuration options | leave **off** | Only those two rows hide behind it |

No **USB** choice exists for this chip, which surprises people: the ATmega2560 has no USB
hardware. The socket belongs to an ATmega16U2 wired to the 2560's first serial port, and
Klipper offers USB only on chips that have it
([AVR Kconfig](https://github.com/Klipper3d/klipper/blob/master/src/avr/Kconfig)). Klipper
therefore runs on UART0 at 250000 baud, which you never have to set.

Press `Q`, then `Y`, then check with
`grep -E "CONFIG_MACH_atmega2560|CONFIG_CLOCK_FREQ|CONFIG_AVR_SERIAL_UART0" .config`.
Expect `=y`, `=16000000`, `=y`. Anything else, go back in — do not build yet.

## Step 3 — Build

```
make
ls -l out/klipper.elf.hex
```

**You should see:** compile lines, then `Creating hex file out/klipper.elf.hex`. **If you
don't:** `avr-gcc: command not found` means Step 1 did not finish; `No rule to make target`
means you are not in `~/klipper`; C errors on a fresh clone mean a dirty tree — `git status`,
then `git checkout .` and rebuild. Keep the `.hex`: every Klipper update on the Pi needs a
rebuild and re-flash, because host and board must match.

## Step 4 — Find the board's USB name

Printer on, USB connected:

```
ls /dev/serial/by-id/*
```

**You should see** one entry, close to
`/dev/serial/by-id/usb-Ultimaker_BV__www.ultimaker.com__Ultimaker_2.0-if00`, maybe ending in
a serial number. Copy it exactly; the doubled underscores are part of it. **If you see
nothing:** cable (charge-only ones never appear), printer power, then port; `dmesg | tail -20`.

## Step 5a — Ask the bootloader whether it is listening (writes nothing)

```bash
sudo service klipper stop
avrdude -c wiring -p atmega2560 -P /dev/serial/by-id/usb-Ultimaker_BV__www.ultimaker.com__Ultimaker_2.0-if00 -n
```

`-n` means no write: avrdude connects, reads the chip identity and stops.

**You should see** `Device signature = 0x1e9801` and `avrdude done.` The bootloader answered,
so the USB route is safe. **If you don't** — `programmer is not responding`, a timeout, or
`stk500v2_ReceiveMessage(): timeout` — the stock bootloader will not accept a third-party
image. Do **not** run `make flash`; go to Step 5b (ISP). Nothing has been written yet, so this
is a free test.

## Step 5 — Flash over USB

```
sudo service klipper stop
make flash FLASH_DEVICE=/dev/serial/by-id/usb-Ultimaker_BV__www.ultimaker.com__Ultimaker_2.0-if00
sudo service klipper start
```

That runs `avrdude -p atmega2560 -c wiring -P "<that path>" -D -U flash:w:out/klipper.elf.hex:i`.
`-c wiring` is the bootloader's protocol. `-D` is the flag that matters: it stops avrdude
erasing the whole chip, so the bootloader in the top 8 KB survives and USB flashing keeps
working. Klipper's Makefile passes it; omit it by hand and you delete your own safety net.

**You should see**, over 10 to 30 seconds, `bytes of flash verified` then `avrdude done.`

**If you don't:**

| Message | Meaning | Do |
|---|---|---|
| `ser_open(): ... Device or resource busy` | Klipper still holds the port | `sudo service klipper stop`, retry |
| `stk500v2_ReceiveMessage(): timeout`, `programmer is not responding` | The bootloader was not listening | Power-cycle, wait for the display, run it again at once. Shorter cable, another port |
| `verification error; content mismatch` | The write did not read back | Once more. If it repeats, use Step 8 — this is the failure reported as "my screen went black" |

Do not retry a failing USB flash more than twice: Step 8 is cheap and certain.

## Step 6 — Point `printer.cfg` at the board

Klipper warns that the serial name can change after flashing. Here it usually does not: the
name belongs to the 16U2, which you did not touch. Check anyway, then make `[mcu]` match:

```
ls /dev/serial/by-id/*
```

```
[mcu]
serial: /dev/serial/by-id/usb-Ultimaker_BV__www.ultimaker.com__Ultimaker_2.0-if00
```

Same name as Step 4 means nothing to change. Never use `/dev/ttyACM0`; it moves.

## Step 7 — Prove it worked

| Check | How | What good looks like |
|---|---|---|
| Config loads | **RESTART** in Fluidd, or `RESTART` | Console ends with `Printer is ready` |
| It runs Klipper, not Marlin | `M115` | Answer contains `FIRMWARE_NAME:Klipper` |
| Right chip, right speed | `grep "MCU 'mcu' config" ~/printer_data/logs/klippy.log \| tail -1` | `MCU=atmega2560 CLOCK_FREQ=16000000`, `SERIAL_BAUD=250000` |
| It moves | `G28`, then `M114` | Bed rises to the top switch and stops, head parks, `M114` reports a position |
| It heats | `M104 S220`, `M190 S60` | Both climb and hold. Cut the power if one runs away |

`FIRMWARE_NAME:Marlin` means the flash did not take: back to Step 5. `CLOCK_FREQ=8000000` is
an 8 MHz build — rebuild.

## Step 8 — The fallback: flashing through the 6-pin header

Use this when USB upload fails twice, or when the board is blank. Run it from `~/klipper`: it
talks to the chip directly. The header is **J1**, a 2x3 block of 2.54 mm pins
([schematic](https://github.com/Ultimaker/Ultimaker2)). Pin 1 is the **square** pad and
carries MISO; match your adapter's labels, or its square pad.

| J1 pin | Signal | Connect to |
|---|---|---|
| 1 | MISO | MISO |
| 2 | +5V | leave off — the printer powers the board |
| 3 | SCK | SCK |
| 4 | MOSI | MOSI |
| 5 | RESET | RST |
| 6 | GND | GND |

Three power rules: never feed the board from programmer and printer supply at once (printer
on, programmer VCC wire off); unplug USB to the Pi; connect the header with the printer off.

```
avrdude -c usbasp -p atmega2560 -D -U flash:w:out/klipper.elf.hex:i
```

With an Arduino Uno running the `ArduinoISP` sketch, use
`avrdude -c stk500v1 -P /dev/ttyACM0 -b 19200 -p atmega2560 -D -U flash:w:out/klipper.elf.hex:i`.

**You should see** the same `bytes of flash verified`. **If you don't:** `target doesn't
answer` is nearly always wiring — check pin 1 and GND, then add `-B 5` to slow the SPI clock.
Before you start, `avrdude -c usbasp -p atmega2560 -U flash:r:stock-backup.hex:i` keeps a
copy of what you replace.

## Step 9 — Getting back to stock

Cura restores Ultimaker's firmware through the same bootloader.

1. Connect the printer to a computer with Cura, printer switched on.
2. **Preferences → Printers → Manage printers**, select it, **Update firmware**, then
   *Automatically upgrade* or *Upload custom firmware*.

Pick the right machine: **Ultimaker 2 Extended** for a stock one, **Ultimaker 2+** if the
Extrusion Upgrade Kit is fitted; the wrong choice turns the feeder the wrong way
(search Ultimaker support for "update printer firmware"; article IDs change). If Cura will not
talk to Klipper, flash the Ultimaker `.hex` through the header in Step 8.

## Troubleshooting

| Symptom | What it means | Fix |
|---|---|---|
| No serial device at all after flashing | The 16U2 stopped enumerating — cable, power or port. Flashing the 2560 cannot remove it | Replug, new cable, another port, watch `dmesg` |
| Device listed, Klipper says `mcu 'mcu': Unable to connect` | The 2560 is not running Klipper: failed flash, or a build for the wrong interface | Re-flash from Step 5, rebuilt for UART0 |
| `MCU Protocol error`, "frequently caused by running an older version of the firmware" | Host and board are on different Klipper versions — normal after updating Klipper on the Pi and not re-flashing | `make`, then `make flash` with Klipper stopped |
| `Timer too close` | The 16 MHz chip or the Pi could not keep up; Klipper's own hint blames an overloaded host | Lower `max_velocity`/`max_accel`, stop other Pi work, check its supply |
| avrdude: `programmer is not responding`, timeouts | Port busy, bootloader not running, or wiring | Stop Klipper, power-cycle, retry, then Step 8 |
| avrdude: `verification error` | The write did not stick | Retry once, then Step 8 |
| `MCU 'mcu' configured for 8Mhz but running at 16Mhz!` | Built for the wrong processor speed | Rebuild at 16 MHz, re-flash |

Next: [02 — the config file](02-config.md), then [03 — tuning](03-tuning.md).

## Sources

- Klipper installation, flashing: <https://www.klipper3d.org/Installation.html>
- AVR options and the `-D` flash rule: <https://github.com/Klipper3d/klipper/tree/master/src/avr>
- Pin map: <https://github.com/Klipper3d/klipper/blob/master/config/generic-ultimaker-ultimainboard-v2.cfg>
- Schematic, J1 and the 16U2: <https://github.com/Ultimaker/Ultimaker2>
- Update via Cura: <https://support.makerbot.com/s/article/1667417418634>
- Bootloader family: <https://github.com/daid/UltiBoot>
- UM2+ walkthrough: <https://www.instructables.com/Ultimaker-2-and-Klipper/>
