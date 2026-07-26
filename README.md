<h1>Daniel Cuesta</h1>

<p>
  I build small, local-first tools that solve a problem I actually have — then keep
  using them. Most run on <code>localhost</code>, keep their data in plain files you own,
  and install with a single <code>git clone</code>.
</p>

<p>
  <a href="https://danielcuesta007.com">danielcuesta007.com</a>
</p>

---

## Cadence

<table>
<tr>
<td width="120" valign="top"><img src="https://raw.githubusercontent.com/danieljcuesta007/danieljcuesta007/main/icons/cadence.png" width="100" alt="Cadence icon"></td>
<td valign="top">

**Dictation for macOS that runs entirely on your machine.** Rust core, Swift interface,
Whisper for transcription — no audio leaves the device.

Bilingual auto-detection between English and Spanish, a personal dictionary that fixes
the names it keeps getting wrong, and a dashboard that measures time saved rather than
words typed. Measured at 1.78% word error rate against a hand-built evaluation corpus.

Architected local-first and **cloud-optional**: the on-device path is the reliability
floor, and a Pro tier (OAuth accounts, zero-retention cloud inference, end-to-end
encrypted settings sync) layers higher-accuracy models on top for users who opt in —
degrading silently back to local whenever the network does. Every utterance shows you
which path it actually took.

`Rust` · `Swift` · `Whisper` · `Metal` · `SQLCipher`

**[Source available →](https://github.com/danieljcuesta007/cadence)**

</td>
</tr>
</table>

---

## Local dashboards

Each is one Python file and one HTML file, served on localhost from the standard library
alone — clone it and it runs, on any Mac, at any Python 3.8 or later.

<table>
<tr>
<td width="120" valign="top"><img src="https://raw.githubusercontent.com/danieljcuesta007/danieljcuesta007/main/icons/social-dashboard.png" width="100" alt="Social Dashboard icon"></td>
<td valign="top">

### Social Dashboard

Audience growth across LinkedIn, Instagram, YouTube and an email newsletter.

The interesting part is the newsletter chart: a subscriber list that moved between three
providers stays a **single continuous series**, colour-coded by era with markers at each
migration — instead of the three disconnected charts each platform shows you, all
starting at zero on the day you arrived.

YouTube syncs through the Data API on a daily schedule. The rest are entered by hand,
deliberately — five seconds of typing earns the same trend while staying inside every
platform's terms of service.

`Python` · `SVG` · `YouTube Data API`

</td>
</tr>

<tr>
<td width="120" valign="top"><img src="https://raw.githubusercontent.com/danieljcuesta007/danieljcuesta007/main/icons/investing.png" width="100" alt="Investing icon"></td>
<td valign="top">

### Investing Dashboard

Portfolio and watchlist with live quotes, importing straight from a Fidelity positions CSV.

Quotes fall back across two providers, so one endpoint changing its shape doesn't take the
dashboard down. Money-market funds like `SPAXX` aren't quoted by market feeds at all, so
they're priced at NAV — otherwise your cash silently vanishes from the total.

Holdings live in a JSON file next to the server, not in browser storage, so they survive a
browser reset and move with the folder.

`Python` · `Atomic writes` · `Multi-source failover`

</td>
</tr>

<tr>
<td width="120" valign="top"><img src="https://raw.githubusercontent.com/danieljcuesta007/danieljcuesta007/main/icons/msgtriage.png" width="100" alt="MsgTriage icon"></td>
<td valign="top">

### Message Triage

An oldest-unread-first jump list for macOS Messages.

Apple gives you no folders and no way to sort unread conversations oldest to newest, so a
message from three weeks ago sits below one from this morning forever. This reads the
Messages database directly, sorts by genuine age, and opens the real thread when you click.

Strictly read-only against the Messages database — it observes and sorts, and leaves
every conversation exactly as it found it.

`Python` · `SQLite` · `AppleScript`

</td>
</tr>
</table>

---

## Icon toolkit

<table>
<tr>
<td width="120" valign="top"><img src="https://raw.githubusercontent.com/danieljcuesta007/danieljcuesta007/main/icons/travel-map.png" width="100" alt="Icon toolkit"></td>
<td valign="top">

Generating macOS `.icns` app icons on a machine with no imaging libraries installed —
no Pillow, no ImageMagick, no admin rights.

The pipeline is SVG, rendered through headless Chrome, downsampled with `sips`, packed by
`iconutil`. Icons are drawn on Apple's own grid: an 824×824 body on a 1024 canvas, shaped
as a true superellipse rather than a rounded rectangle, which is the difference between an
icon that sits correctly beside system icons and one that looks subtly wrong.

`Python` · `SVG` · `Headless Chrome`

</td>
</tr>
</table>

---

<sub><b>Cadence is open source</b> — read it, build it, run it:
<a href="https://github.com/danieljcuesta007/cadence">github.com/danieljcuesta007/cadence</a>.
The dashboards run on my own machine daily; source available on request.</sub>
