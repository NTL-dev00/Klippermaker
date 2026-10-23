# Changelog

All notable changes to this guide are listed here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] — 2026-10-22

First public version.

### Added

- Getting started: Raspberry Pi setup, Klipper, Moonraker and a web interface
- Flashing Klipper onto the printer's own mainboard, with a read-only bootloader probe and an ISP fallback
- Annotated `printer.cfg` and `macros.cfg` for the Ultimaker 2 Extended+
- Tuning guide in the order that works: retraction, flow, temperature, acceleration, pressure advance
- Measured results for this machine, including the tests that failed and why
- Slicer presets for PrusaSlicer and setup notes for Orca Slicer
- Optional workflow for tuning with the Hermes AI agent
- Troubleshooting page built from real failures
- `tools/make_test_gcode.py` to generate the calibration prints
- `tools/scrub_check.py` to keep personal data out of the repository

### Known gaps

- Input shaping with an accelerometer is not covered
- Maximum volumetric flow was not measured
- The Orca profile is documented as values to enter, not shipped as an importable file
