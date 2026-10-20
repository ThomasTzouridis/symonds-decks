# Symonds Productions: deck tracking and Presentation Log

Everything runs on the MacBook (mac-hub, `~/Desktop/AIOS/automations/mac-hub`), checkout `~/symonds-decks`.

| What | Where | When |
|---|---|---|
| Decks + HeyReach fields (`presentation`, `companyname`), feeder from the Connect campaign, 24 h stamp | `jobs/symonds_presentation_flow.py` + `symonds_presentation.py` | every 30 min |
| Deck opens, slides, time, videos, Book clicks + Presentation Log | `_src/auto/sy_track.py` (wrapper `jobs/symonds_track.py`) | every 6 h |

## Tracking pathway

1. Every deck carries the script at the end of `_src/template.html` (and of every `*/index.html`). It posts `open`, `slide` (deepest slide),
   `video`, `book` (click on the Calendly button), `ping` (every 30 s with seconds visible) and `leave` to
   `https://macbook-air-von-thomas.tail94ea31.ts.net/webhook/sy-deck-track`.
   Not tracked: bots (navigator.webdriver) and our own browsers (open any deck once with `?syint=1`, undo with `?syint=0`).
2. mac-hub (`hub.py`) appends every beacon with the visitor IP to `logs/events.jsonl`.
3. `sy_track.py` reads the new lines (byte offset in `_private/sy_track_state.json`), aggregates per deck slug and per session, geolocates the IP
   (ipinfo.io, cached) and drops bots (data center IPs, impossible ping clocks, headless UAs) and every session from Slovenia (us).
4. Presentation Log tab of the sheet "Symonds Production | Meetings & Tracking" (`1DqTJU_iCMtxVKq_LRaP5AVKfQfw1dzFK7TR_fJRR5QE`):
   one row per lead of campaign 664625 plus every connected Connect-campaign lead not fed yet, keyed by LinkedIn id (column E).
   A:V auto (HeyReach statuses, client word, company name, deck URL, deck status, live check, verdict), W:AD manual (never touched),
   AE:AN tracking (opens, sessions, first/last opened, deepest slide, seconds, videos, Book clicks, opened from, AN Meeting booked (Calendly) = start of the lead's active booking).
5. Bad verdicts (DECK NOT LIVE, STOPPED, BUILD FAILED, MESSAGE 1 OUT NO DECK YET, NO CLIENT WORD, NO COMPANY NAME, feed failed) DM Thomas once
   per lead and verdict. A crash DMs at most once every 20 h. Last run and open rate are in the job log only, no Status tab in the sheet.
6. Meetings tab (Thomas 2026-10-17, the craze&friends model): a meeting is a Calendly booking (section Booking), a HeyReach tag containing "meeting" on the lead (tag it in the
   HeyReach inbox) or a date typed into Presentation Log column Z "Meeting booked date". sy_track then writes one row per lead (A lead name,
   B email, C website, D LinkedIn, E company LinkedIn, F phone via Prospeo, G date, H link to the chat doc `Chat Symonds Productions <lead>` in Drive "/Other/Chats" (messenger layout, `mac-hub/chat_doc.py` via `chat_docs`, SOP Meeting Chat Doc, `Desktop\SOPs\KPIs\Meeting Chat Doc.md`, `no thread found` when there is none), I outcome and J $ manual, K lead id,
   L source, M matched by), stops the lead in its campaign, tags it "Meeting booked", posts once to Slack #meeting-booked-notifier and
   refreshes the Performance tab right away.
7. Performance + Copy tabs: engine `mac-hub/hr_perf.py`, config `mac-hub/jobs/symonds_perf.py` (daily 04:00 on the Mac). Sections
   "All Campaigns" and "Messaging campaign" (664625 only), rows Dave Symonds + Total: B connection back rate, C presentation open rate per
   messaged lead (from sy_track), D reply rate, E interested reply rate, F meeting rate, all per messaged lead, all-time since 2026-01-01.
   The Copy tab has one row for Dave's deck chain (C:F same rates, G show up rate manual).

## The 24 h rule

HeyReach's sequence of 664625 has a `1 DAY` delay between the connection check (or the accepted request) and message 1 on both paths, so no lead
ever gets message 1 earlier than 24 h after connecting. The flow records the first time it sees a lead connected (`state/symonds_connected.json`,
30 min resolution) and the log shows "First seen connected" and "Message 1 due (accept + 24 h)". HeyReach then sends inside its sending window,
so the real gap is 24 h plus the wait for the next window, never less.

## Booking

Since 2026-10-20 every deck books on Calendly: https://calendly.com/davesymondsproductions/strategy-session (event "Strategy Session",
Dave's account, user 4c755217-19d8-4c7b-8b4a-e56ba243d530). PAT `CALENDLY_SYMONDS_PAT` in AIOS .env on PC and Mac (no users:read scope,
so the user URI is fixed in sy_track.py). The deck script tags every Book button with `utm_source=sy-deck`, `utm_campaign=<slug>`,
`utm_content=<session id>` (`internal` for a browser flagged `?syint=1`), Calendly stores it on the invitee.

Every sy_track run (6 h) pulls every invitee (active, canceled, rescheduled; a reschedule keeps its row) and matches it to a lead, first hit
wins, the sentence lands in Meetings M: internal (actiscale / symonds email, team name, deck tag internal) -> deck tag (booker is the lead,
else "booked by another person" for that lead) -> email = lead email -> work email domain = lead website -> booker named in a HeyReach chat
-> name match -> a lead's deck opened or Book clicked within 2 h before the booking (best guess, CHECK) -> no match (CHECK).
A matched active booking: Meetings row (L "Calendly booking", G start Berlin time, B the booker email when the lead booked, F the Calendly
phone), stop in campaign, tag "Meeting booked", Slack #meeting-booked-notifier, Performance refresh, Presentation Log AN. A canceled booking
keeps its row with " (canceled)" and triggers nothing. No match: row keyed `cal:<invitee uri>`, "<name> (no lead match)", CHECK, one DM to
Thomas; tag the right lead "Meeting booked" in HeyReach and that lead gets its own row on the next run. The old Acuity link
(symondsproductions.as.me) is gone from every deck.

## Manual

```
ssh thomastzouridis@100.93.68.58
cd ~/Desktop/AIOS/automations/mac-hub
python3 -m jobs.symonds_presentation_flow --dry     # who would be fed / built
python3 -m jobs.symonds_track                       # one tracking run now
tail -f logs/jobs/symonds_track.log
```
