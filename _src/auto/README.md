# Symonds Productions: deck tracking and Presentation Log

Everything runs on the MacBook (mac-hub, `~/Desktop/AIOS/automations/mac-hub`), checkout `~/symonds-decks`.

| What | Where | When |
|---|---|---|
| Decks + HeyReach fields (`presentation`, `companyname`), feeder from the Connect campaign, 24 h stamp | `jobs/symonds_presentation_flow.py` + `symonds_presentation.py` | every 30 min |
| Deck opens, slides, time, videos, Book clicks + Presentation Log + Status tab | `_src/auto/sy_track.py` (wrapper `jobs/symonds_track.py`) | every 6 h |

## Tracking pathway

1. Every deck carries the script at the end of `_src/template.html` (and of every `*/index.html`). It posts `open`, `slide` (deepest slide),
   `video`, `book` (click on the `as.me` button), `ping` (every 30 s with seconds visible) and `leave` to
   `https://macbook-air-von-thomas.tail94ea31.ts.net/webhook/sy-deck-track`.
   Not tracked: bots (navigator.webdriver) and our own browsers (open any deck once with `?syint=1`, undo with `?syint=0`).
2. mac-hub (`hub.py`) appends every beacon with the visitor IP to `logs/events.jsonl`.
3. `sy_track.py` reads the new lines (byte offset in `_private/sy_track_state.json`), aggregates per deck slug and per session, geolocates the IP
   (ipinfo.io, cached) and drops bots (data center IPs, impossible ping clocks, headless UAs) and every session from Slovenia (us).
4. Presentation Log tab of the sheet "Symonds Production | Meetings & Tracking" (`1DqTJU_iCMtxVKq_LRaP5AVKfQfw1dzFK7TR_fJRR5QE`):
   one row per lead of campaign 664625 plus every connected Connect-campaign lead not fed yet, keyed by LinkedIn id (column E).
   A:V auto (HeyReach statuses, client word, company name, deck URL, deck status, live check, verdict), W:AD manual (never touched),
   AE:AM tracking (opens, sessions, first/last opened, deepest slide, seconds, videos, Book clicks, opened from).
5. Bad verdicts (DECK NOT LIVE, STOPPED, BUILD FAILED, MESSAGE 1 OUT NO DECK YET, NO CLIENT WORD, NO COMPANY NAME, feed failed) DM Thomas once
   per lead and verdict. A crash DMs at most once every 20 h. Status tab: last run, open rate, cadence.

## The 24 h rule

HeyReach's sequence of 664625 has a `1 DAY` delay between the connection check (or the accepted request) and message 1 on both paths, so no lead
ever gets message 1 earlier than 24 h after connecting. The flow records the first time it sees a lead connected (`state/symonds_connected.json`,
30 min resolution) and the log shows "First seen connected" and "Message 1 due (accept + 24 h)". HeyReach then sends inside its sending window,
so the real gap is 24 h plus the wait for the next window, never less.

## Booking

Symonds books on Acuity (`symondsproductions.as.me/strategy-session`); there is no API credential, so only Book clicks are tracked.
Bookings go into the manual columns by hand.

## Manual

```
ssh thomastzouridis@100.93.68.58
cd ~/Desktop/AIOS/automations/mac-hub
python3 -m jobs.symonds_presentation_flow --dry     # who would be fed / built
python3 -m jobs.symonds_track                       # one tracking run now
tail -f logs/jobs/symonds_track.log
```
