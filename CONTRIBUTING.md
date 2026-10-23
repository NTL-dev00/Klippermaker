# Contributing

Thanks for helping. This guide exists because Klipper information for the Ultimaker 2 Extended+ is
thin, so corrections from people who actually run this printer are the most valuable thing you can
send.

## What is useful

- **A correction with evidence.** Say what the guide claims, what your machine did, and how you
  measured it. A photo of a test print or a caliper reading beats an opinion.
- **A missing failure mode.** If you hit an error the troubleshooting page does not cover, add it.
- **A clearer sentence.** If a beginner would stumble on a paragraph, rewrite it.

## What we will not merge

- Untested settings presented as recommendations
- Advice that requires buying new hardware without saying so
- Personal data: IP addresses, usernames, hostnames, serial numbers, Wi-Fi details

## Style

- Plain words. Short sentences. Explain a term the first time you use it.
- One idea per paragraph.
- Steps are numbered; expected results are stated explicitly.
- Prefer a table over three paragraphs.
- No emoji, no marketing language.

## Before you open a pull request

1. Run the privacy check from the repository root:

   ```bash
   python3 tools/scrub_check.py
   ```

   It must print `OK - no private data patterns found`.

2. Re-read your change as if you had never seen Klipper.
3. Say in the pull request **which printer and which firmware version** you tested on.

## Reporting a problem

Open an issue with:

- what you expected
- what happened
- the exact command or G-code
- the relevant part of `klippy.log` (remove any personal data first)

## License

By contributing you agree that your work is released under the MIT license used by this repository.
