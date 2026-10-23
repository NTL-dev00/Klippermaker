# 1. Get started: hardware, Pi, Klipper

From a stock Ultimaker 2 Extended+ and a bare Raspberry Pi to a printer that answers in a
web browser: a Pi running Klipper, Moonraker and Fluidd, a fixed IP address, and the
printer's USB device name written down. Flashing the printer's own board is **not** here —
that is [docs/02-config.md](02-config.md).

## How the pieces fit

```
browser (Fluidd)  ->  Moonraker  ->  Klipper  ->  USB  ->  printer board
   your laptop         on the Pi     on the Pi             (ATmega2560)
```

| Name | What it is, in one line |
|---|---|
| Klipper | The firmware. The hard real-time work runs on the printer board; the thinking runs on the Pi. |
| Moonraker | The API on the Pi that the web page talks to. It also starts and stops Klipper. |
| Fluidd | The web page you open in a browser. Nothing is installed on your laptop. |

Klipper is split in two: a small binary on the printer board, a Python program on the Pi.
That is why a Pi is needed, and why the printer must stay on USB while printing.

## What you need

| Part | Get this | Why it matters |
|---|---|---|
| Raspberry Pi | Pi 3B+, Pi 4, Pi Zero 2 W | Klipper's recommended minimum is a Pi 3, Pi 4, Pi 5 or Zero 2 W. Pi 1/2/Zero 1 are too slow and cause print stalls ([Klipper FAQ](https://www.klipper3d.org/FAQ.html#can-i-run-klipper-on-something-other-than-a-raspberry-pi-3)). |
| microSD card | 8 GB or larger, class A1/A2 | A slow or worn card is a common cause of mid-print hangs. |
| Power supply | Official Pi supply, 5 V 3 A (Pi 4: USB-C, Zero 2 W: micro-USB) | Under-voltage makes the Pi reboot mid-print. This is the first thing Klipper's FAQ blames ([FAQ](https://www.klipper3d.org/FAQ.html#my-raspberry-pi-keeps-rebooting-during-prints)). |
| USB cable | USB-A to USB-B, short and thick | The UM2E+ board has a USB-B socket. A charge-only cable will never show up as a device. |
| Printer | Ultimaker 2 Extended+, stock | 225 x 225 x 305 mm, 0.4 mm nozzle, 2.85 mm filament. |
| Network | Wi-Fi or Ethernet, 2.4 GHz Wi-Fi is safest | The Pi and your laptop must be on the same network. |

Two facts about this printer you will meet again: it uses **2.85 mm filament**, not 1.75 mm,
and this guide's config leaves `[gcode_arcs]` out, so `G2`/`G3` are skipped. That is a choice,
not a limit of the board — see [docs/02-config.md](02-config.md).

## Step 1 — Flash the Pi

Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/). It writes the card and
lets you set up Wi-Fi and SSH before the first boot, so you never need a monitor.

1. Install and open Imager.
2. **Choose device** — your Pi model.
3. **Choose OS** → `Raspberry Pi OS (other)` → `Raspberry Pi OS Lite (64-bit)`.
   Lite means no desktop. Klipper does not need one, and a desktop can interfere with
   USB access ([Klipper install docs](https://www.klipper3d.org/Installation.html)).
4. **Choose storage** — your microSD card. Double-check you picked the card and not a
   USB stick with your files on it.
5. When Imager offers OS customization, choose **Edit Settings** (older versions: the gear
   icon or `Ctrl+Shift+X`). Set hostname `<PI_HOSTNAME>`, username `<YOUR_USER>` and a
   password, your Wi-Fi SSID/password and country, locale/timezone, and on the Services
   tab enable **SSH**.
6. Write, wait for "Write successful", then eject.

**You should see** a progress bar, then a success message. **If you don't:** a card that
fails to write twice is usually fake or dying — try another. If the settings dialog never
appeared, your Imager is old; update it or edit settings later with `sudo raspi-config`.

## Step 2 — First boot and SSH

Put the card in the Pi, connect Ethernet if you have it, power up, and wait 60–90 seconds.
First boot resizes the filesystem and reboots once. Then, from your laptop:

```
ping <PI_HOSTNAME>.local
ssh <YOUR_USER>@<PI_HOSTNAME>.local
```

**You should see** ping replies, then a password prompt and a shell. **If you don't:**

- No ping: wait another minute, then recheck the Wi-Fi details. The Pi 3 and Zero 2 W only
  see 2.4 GHz networks.
- `Could not resolve hostname`: mDNS is blocked here. Get the Pi's IP from your router and
  use `ssh <YOUR_USER>@<PRINTER_IP>`.
- `Connection refused`: SSH is off. Remount the card's boot partition and create an empty
  file named `ssh` in it.

## Step 3 — Update the Pi

Do this before installing anything; Klipper expects a current system.

```
sudo apt update
sudo apt full-upgrade -y
sudo reboot
```

Reconnect with SSH after the reboot. **You should see** upgrades applying and the
connection dropping. Then install git, which the next step needs:

```
sudo apt-get install git -y
```

## Step 4 — Give the Pi a fixed address

**Why.** Three things hard-code the Pi's address: your bookmark, your slicer's upload
target, and Moonraker's trusted-clients list. If the router hands out a new address after a
power cut, the printer "disappears". Fix it once.

**Option A — DHCP reservation (recommended).** In your router's admin page, find the Pi in
the client list and reserve its address. Nothing to configure on the Pi, nothing to break
on the next OS update.

**Option B — static address on the Pi.** Raspberry Pi OS uses NetworkManager. Get the
connection name with `nmcli con show`, then set your own free address and your gateway:

```
sudo nmcli con mod "<CONNECTION_NAME>" \
  ipv4.addresses <PRINTER_IP>/24 \
  ipv4.gateway <GATEWAY_IP> \
  ipv4.dns "1.1.1.1" \
  ipv4.method manual
sudo nmcli con up "<CONNECTION_NAME>"
```

Pick an address **outside** your router's DHCP pool, or the router may hand the same
address to another device.

**You should see:** `hostname -I` reports the address you chose, and it is still the same
after `sudo reboot`.

**If you don't:** you are back to no network. Connect a monitor and keyboard, log in, and
run `sudo nmcli con mod "<CONNECTION_NAME>" ipv4.method auto` to undo it, then use Option A.

## Step 5 — Install Klipper, Moonraker and Fluidd

KIAUH is a menu-driven installer for all three, and is what Klipper's own docs point at
([Installation](https://www.klipper3d.org/Installation.html)).

```
cd ~
git clone https://github.com/dw-0/kiauh.git
./kiauh/kiauh.sh
```

In the menu:

1. `Install`
2. `Klipper` — accept the default instance name `printer`, confirm
3. `Moonraker` — same instance
4. `Fluidd`
5. `B` to go back, then `Q` to quit

That order matters: Moonraker needs Klipper, Fluidd needs Moonraker. Menu numbers move
between KIAUH versions (v6 is a Python rewrite), so follow the **names**. The sudo password
prompt is expected.

**Mainsail instead?** It is the same kind of web page and works identically. Pick `Mainsail` in
step 4 instead of `Fluidd`; everything else in this guide is unchanged. (The machine this guide was
written on runs Mainsail.)

**You should see** several minutes of compiling and pip installs, then the menu with no red
error text. Check the services:

```
systemctl status klipper --no-pager
systemctl status moonraker --no-pager
```

Both should say `active (running)`. **If you don't:**

- `klipper` failed and the log mentions a missing `printer.cfg`: expected, there is no config
  yet. Ignore it.
- `moonraker` failed: read `~/printer_data/logs/moonraker.log`. The usual cause is a port
  already in use — usually a second web UI installed on port 80.
- `Failed to connect to the bus` or permission errors: you skipped the reboot in Step 3.

Config files live in `~/printer_data/config/`. That directory is what you will back up
and what the next chapter fills in.

## Step 6 — Find the printer's USB name

Connect the USB cable between the Pi and the printer, and power the printer on. The board
needs power to appear.

```
ls /dev/serial/by-id/*
```

**You should see** one line, something like:

```
/dev/serial/by-id/usb-<VENDOR>_<PRODUCT>_<SERIAL>-if00
```

Copy it exactly. Yours is unique — the vendor and serial parts differ from every example
online, including this one.

**Use this path, not `/dev/ttyACM0` or `/dev/ttyUSB0`.** The kernel numbers those in the
order devices appear, so unplugging the printer, rebooting the Pi or adding another USB
device can move the number to something else. The `by-id` name comes from the board's own
serial number and never moves
([Klipper FAQ](https://www.klipper3d.org/FAQ.html#wheres-my-serial-port)).

The name **can change after you flash the board**, so run this again afterwards.

**If you see nothing:**

- `dmesg | tail -20` right after plugging in. No new lines means the Pi never saw a device:
  suspect the cable (charge-only cables are common) or the printer's power.
- Lines appear but no `/dev/serial/by-id/` entry: the board enumerated without a serial
  number. Try `ls /dev/serial/by-path/*` instead, and use that path in the config.
- Random "Lost communication with MCU" errors later: a different problem, a bad cable or a
  weak Pi supply. Check it before you blame the config.

> **Before `printer.cfg` will work, the printer board itself must run Klipper.** If you have not
> done that yet, do [chapter 8](08-flash-firmware.md) now — the board still has Ultimaker's
> firmware, and the Pi cannot talk to it.

## Step 7 — First contact in Fluidd

Open a browser on your laptop:

```
http://<PRINTER_IP>
```

Port 80 is the KIAUH default for Fluidd, so no port number is needed. **You should see** the
Fluidd interface with a red banner:

```
Klipper reports: error
Unable to open config file /home/<YOUR_USER>/printer_data/config/printer.cfg
```

**That is normal and expected.** Klipper is installed and running; it just has no printer
definition yet. Nothing is broken. Do not reinstall anything.

To confirm the three layers are individually alive:

| Check | Command or URL | Healthy answer |
|---|---|---|
| Moonraker | `http://<PRINTER_IP>/server/info` | a page of JSON |
| Klipper service | `systemctl status klipper` | `active (running)` |
| Config folder | `ls ~/printer_data/config/` | the folder exists, `printer.cfg` may be absent |

Leave the banner alone. [docs/02-config.md](02-config.md) writes the config that clears it.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ping <PI_HOSTNAME>.local` gets no reply | Pi never joined Wi-Fi; 5 GHz-only network; wrong country code | Re-flash the card with the Wi-Fi details checked twice, or plug in Ethernet and retry |
| SSH says `Permission denied` | Wrong username, or the password was mistyped during setup | Log in on a monitor, or re-flash; there is no default password on current images |
| `ls /dev/serial/by-id/*` says "No such file or directory" | Cable is charge-only, printer is off, or the board is not enumerating | Try a known-good data cable, power the printer on, watch `dmesg` while plugging in |
| Fluidd gives `404 Not Found` | Fluidd is not installed, or you are on the wrong port or the wrong device | Run `systemctl status nginx`, reinstall Fluidd from KIAUH, confirm the address with `hostname -I` |
| Fluidd loads but says "Klipper not connected" | Klipper crashed on a config error, or Moonraker cannot reach it | Read the banner text, then `~/printer_data/logs/klippy.log` |
| Worked yesterday, gone today | The router gave the Pi a new address | Set the DHCP reservation from Step 4 |

## What you have now

Klipper, Moonraker and Fluidd running on a Pi at a fixed address, and your printer's stable
USB path written down.

Next: [docs/02-config.md](02-config.md)
