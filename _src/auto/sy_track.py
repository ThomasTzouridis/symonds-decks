# -*- coding: utf-8 -*-
"""Symonds Productions deck tracking + Presentation Log. Runs on the Mac (mac-hub job symonds_track, every 6 h), checkout ~/symonds-decks.
Same model as craze&friends (cf_track.py), without Calendly: Symonds books on Acuity (symondsproductions.as.me), which has no API key here,
so a booking shows up only as a Book click plus whatever Thomas types into the manual columns.
1. Deck events: every deck (template.html, before </body>) posts open / slide / video / book / ping / leave beacons to mac-hub
   (/webhook/sy-deck-track), which appends them to ~/Desktop/AIOS/automations/mac-hub/logs/events.jsonl with the visitor IP. Read
   incrementally (byte offset in _private/sy_track_state.json), aggregated per slug and per session; bots / link scanners and sessions from
   NOT_COUNTED_CC never count. -> Presentation Log columns AE:AM (after the manual block W:AD, which is never touched).
2. Presentation Log (sheet "Symonds Production | Meetings & Tracking"): one row per lead of campaign 664625 "Symonds Production | Dave Symonds"
   plus every connected lead of the Connect campaign 641853 that is not in 664625 yet (feed pending / failed / has a conversation).
   Keyed by LinkedIn id (column E), rows keep their position, the auto block A:V is rewritten every run, W:AD is manual.
   Facts come from HeyReach (statuses, custom fields client_word / companyname / presentation), the flow state
   (~/Desktop/AIOS/automations/mac-hub/state/symonds_presentation_flow_v2.json: deck status per lead) and the connected stamp
   (state/symonds_connected.json, written by the 30 min flow the first time it sees a lead connected: message 1 is due 24 h later, HeyReach's
   1 DAY delay after CHECK_IS_CONNECTION on both sequence paths).
   Column "Check" is the verdict per lead (OK / DECK NOT LIVE / STOPPED / BUILD FAILED / MESSAGE 1 OUT, NO DECK YET / ...); a bad verdict DMs
   Thomas once per lead and verdict. A crash DMs at most once every 20 h. Last run and open rate go to the job log, no Status tab (Thomas 2026-10-17).
  python3 _src/auto/sy_track.py
"""
import os, sys, re, json, time, datetime, traceback, urllib.request, urllib.parse, urllib.error
HERE = os.path.dirname(os.path.abspath(__file__)); SRC = os.path.dirname(HERE); ROOT = os.path.dirname(SRC)
HOME = os.path.expanduser('~')
HUB = os.path.join(HOME, 'Desktop', 'AIOS', 'automations', 'mac-hub')
EVENTS = os.path.join(HUB, 'logs', 'events.jsonl')
FLOW_STATE = os.path.join(HUB, 'state', 'symonds_presentation_flow_v2.json')
CONN_STATE = os.path.join(HUB, 'state', 'symonds_connected.json')
STATE = os.path.join(ROOT, '_private', 'sy_track_state.json')
CRASH = os.path.join(ROOT, '_private', 'sy_track_crash.json')
B = 'https://api.heyreach.io/api/public'
SENDER_NAME = 'Dave Symonds'
MSG = {'list': 1036135, 'campaign': 664625}
CONNECT = {'list': 999923, 'campaign': 641853}
SITE = 'https://www.symondsproductions-cases.co/'
SHEET = '1DqTJU_iCMtxVKq_LRaP5AVKfQfw1dzFK7TR_fJRR5QE'   # "Symonds Production | Meetings & Tracking"
TAB = 'Presentation Log'
AUTO_HDR = ['Lead', 'Company', 'Sender', 'Campaign', 'LinkedIn id', 'Connection status (HeyReach)', 'Connected', 'First seen connected',
            'Message 1 due (accept + 24 h)', 'Message status (HeyReach)', 'Replied (HeyReach)', 'Campaign status (HeyReach)', 'Last action (HeyReach)',
            'Client word', 'Company name (message 2)', 'Deck URL HeyReach sends', 'Deck slug', 'Deck status (flow)', 'Deck set at', 'Live check', 'Check', 'Note or error']
MAN_HDR = ['Reply date', 'Reply summary', 'Interested', 'Meeting booked date', 'Showed up', 'Closed', 'Deal value', 'Notes']
TRACK_HDR = ['Deck opens', 'Deck sessions', 'First opened', 'Last opened', 'Deepest slide', 'Time on deck (s)', 'Videos played', 'Book clicks', 'Opened from']
NA, NM = len(AUTO_HDR), len(MAN_HDR)
NOT_COUNTED_CC = {'SI'}   # we sit in Celje: every session from Slovenia is ours
CONNECTED = re.compile(r'(?i)accept|^connected|already')
INACTIVE = {'Finished', 'Failed', 'Stopped', 'ManuallyStopped', 'Excluded', 'Canceled'}
BAD = ('DECK NOT LIVE', 'STOPPED', 'BUILD FAILED', 'MESSAGE 1 OUT', 'NO CLIENT WORD', 'NO COMPANY NAME', 'NO DECK VERSION', 'Connect-only: feed failed')
DC_ORG = re.compile(r'microsoft|azure|google|amazon|aws|linkedin|cloudflare|akamai|digitalocean|hetzner|ovh|oracle|facebook|meta platforms|proofpoint|mimecast|barracuda', re.I)
from zoneinfo import ZoneInfo
BERLIN = ZoneInfo('Europe/Berlin')
sys.path.insert(0, os.path.join(HOME, 'Desktop', 'AIOS'))


def col(n):
    """1-based column number -> letter(s)."""
    s = ''
    while n: n, r = divmod(n - 1, 26); s = chr(65 + r) + s
    return s


TRACK_COL = col(NA + NM + 1)   # AE


def ts(t): return datetime.datetime.fromtimestamp(t, BERLIN).strftime('%Y-%m-%d %H:%M') if t else ''


def now(): return datetime.datetime.now().isoformat(timespec='seconds')


def say(*a): print(now(), *a, flush=True)


def env(k):
    kv = dict(re.findall(r'^([A-Z0-9_]+)=(.*)$', open(os.path.join(HOME, 'Desktop', 'AIOS', '.env'), encoding='utf-8').read(), re.M))
    return kv.get(k, '').strip().strip('"').strip("'")


def alert(text):
    """DM to Thomas (the mac-hub alert channel is archived, so common.slack_alert goes nowhere)."""
    say('ALERT', text)
    try:
        r = urllib.request.Request('https://slack.com/api/chat.postMessage', json.dumps({'channel': 'U09HBPS205B', 'text': 'Symonds decks: ' + text}).encode(),
                                   {'Content-Type': 'application/json; charset=utf-8', 'Authorization': 'Bearer ' + env('SLACK_USER_TOKEN')})
        urllib.request.urlopen(r, timeout=20).read()
    except Exception as e:
        say('slack failed', e)


def hr(path, body=None, method='POST'):
    for a in range(6):
        try:
            r = urllib.request.Request(B + path, json.dumps(body).encode() if body is not None else None,
                                       {'X-API-KEY': env('HEYREACH_SYMONDS_API_KEY'), 'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}, method=method)
            t = urllib.request.urlopen(r, timeout=90).read().decode()
            return json.loads(t) if t.strip() else {}
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and a < 5: time.sleep(20 * (a + 1)); continue
            raise
        except (urllib.error.URLError, TimeoutError):
            if a < 5: time.sleep(10 * (a + 1)); continue
            raise


def lid_of(url):
    u = urllib.parse.unquote((url or '').strip().lower().split('?')[0].rstrip('/'))
    return u.split('linkedin.com/in/')[-1] if 'linkedin.com/in/' in u else u


def cf_of(lead):
    return {c.get('name'): str(c.get('value')) for c in (lead.get('customFields') or []) if c.get('name') and c.get('value') not in (None, '')}


def list_leads(list_id):
    out, off = {}, 0
    while True:
        items = hr('/list/GetLeadsFromList', {'listId': list_id, 'offset': off, 'limit': 1000}).get('items') or []
        for l in items: out[lid_of(l.get('profileUrl'))] = l
        if len(items) < 1000: return out
        off += 1000


def campaign_leads(cid):
    out, off = {}, 0
    while True:
        items = hr('/campaign/GetLeadsFromCampaign', {'campaignId': cid, 'offset': off, 'limit': 100}).get('items') or []
        for x in items: out[lid_of((x.get('linkedInUserProfile') or {}).get('profileUrl'))] = x
        if len(items) < 100: return out
        off += 100


def sheets_svc():
    from google_auth import get_creds
    from googleapiclient.discovery import build
    return build('sheets', 'v4', credentials=get_creds(), cache_discovery=False).spreadsheets()


def ensure_tab(sv):
    """Presentation Log tab (frozen bold header) if missing, wide enough for the tracking block, header row kept current."""
    meta = sv.get(spreadsheetId=SHEET, fields='sheets.properties').execute()['sheets']
    need = NA + NM + len(TRACK_HDR)
    pl = next((x['properties'] for x in meta if x['properties']['title'] == TAB), None)
    if not pl:
        r = sv.batchUpdate(spreadsheetId=SHEET, body={'requests': [{'addSheet': {'properties': {'title': TAB, 'gridProperties': {'frozenRowCount': 1, 'columnCount': need + 2}}}}]}).execute()
        sid = r['replies'][0]['addSheet']['properties']['sheetId']
        sv.batchUpdate(spreadsheetId=SHEET, body={'requests': [{'repeatCell': {'range': {'sheetId': sid, 'startRowIndex': 0, 'endRowIndex': 1},
            'cell': {'userEnteredFormat': {'textFormat': {'bold': True}, 'backgroundColor': {'red': .9, 'green': .9, 'blue': .9}}},
            'fields': 'userEnteredFormat(textFormat,backgroundColor)'}}]}).execute()
    elif pl['gridProperties']['columnCount'] < need:
        sv.batchUpdate(spreadsheetId=SHEET, body={'requests': [{'appendDimension': {'sheetId': pl['sheetId'], 'dimension': 'COLUMNS', 'length': need - pl['gridProperties']['columnCount']}}]}).execute()
    sv.values().update(spreadsheetId=SHEET, range="'%s'!A1" % TAB, valueInputOption='RAW', body={'values': [AUTO_HDR + MAN_HDR + TRACK_HDR]}).execute()
    return meta


def live_code(slug, cache):
    """200 = the lead's deck is served, else the HTTP code (GitHub Pages 404 fallback) or 0."""
    if slug in cache: return cache[slug]
    try:
        r = urllib.request.urlopen(urllib.request.Request(SITE + slug + '/', headers={'User-Agent': 'Mozilla/5.0', 'Cache-Control': 'no-cache'}), timeout=20)
        cache[slug] = 200 if r.status == 200 and 'Symonds' in r.read().decode('utf-8', 'replace') else r.status
    except urllib.error.HTTPError as e: cache[slug] = e.code
    except Exception: cache[slug] = 0
    return cache[slug]


# ---------- deck events (same rules as craze&friends cf_track.py) ----------
_ZONES = None
def tz_cc(tz):
    global _ZONES
    if _ZONES is None:
        _ZONES = {}
        for pth in ('/usr/share/zoneinfo/zone.tab', '/usr/share/zoneinfo/zone1970.tab'):
            try:
                for line in open(pth, encoding='utf-8'):
                    if line.startswith('#'): continue
                    f = line.rstrip('\n').split('\t')
                    if len(f) >= 3: _ZONES.setdefault(f[2], f[0].split(',')[0])
            except OSError: pass
    return _ZONES.get(tz or '', '')


def geo(ip, cache):
    """'City, CC' via ipinfo.io (free, no token), cached forever; the owner lands in cache['org:' + ip] for is_bot()."""
    if not ip or ip.startswith(('10.', '100.', '127.', '192.168.')): return ''
    if ip in cache and ('org:' + ip) in cache: return cache[ip]
    try:
        d = json.loads(urllib.request.urlopen(urllib.request.Request('https://ipinfo.io/%s/json' % ip, headers={'User-Agent': 'Mozilla/5.0'}), timeout=15).read().decode())
        cache[ip] = ', '.join(x for x in (d.get('city'), d.get('country')) if x) or '?'
        cache['org:' + ip] = d.get('org') or ''
    except Exception as e:
        say('geo lookup failed', ip, e); return cache.get(ip, '')
    return cache[ip]


def is_bot(s):
    """Link scanners (LinkedIn / Microsoft Safe Links, mail security): data center IP, impossible ping clock, zero-width window or headless UA."""
    if DC_ORG.search(s.get('org') or ''): return True
    if s.get('pings', 0) > s.get('secs', 0) // 30 + 1: return True
    if s.get('w') == 0 or 'headless' in (s.get('ua') or '').lower(): return True
    return False


def read_events(st):
    """New sy-deck-track beacons since the stored offset -> st['slugs'][slug]['sids'][sid]."""
    size = os.path.getsize(EVENTS) if os.path.exists(EVENTS) else 0
    if st.get('v') != 1: st.update(v=1, offset=None, slugs={})
    off = st.get('offset')
    if off is None or off > size: off = max(0, size - 2_000_000) if off is None else 0   # first run: only the tail (tracking started 2026-10-17)
    agg = st.setdefault('slugs', {})
    if size:
        with open(EVENTS, 'rb') as f:
            f.seek(off)
            for line in f:
                if not line.endswith(b'\n'): break
                off += len(line)
                if b'sy-deck-track' not in line: continue
                try: e = json.loads(line)
                except ValueError: continue
                if e.get('path') != 'sy-deck-track': continue
                p = e.get('payload') or {}
                if not isinstance(p, dict): continue
                slug, sid, ev, t = (p.get('slug') or '').lower(), p.get('sid') or '', p.get('ev') or '', e.get('ts') or time.time()
                if not slug or slug.startswith('_'): continue
                a = agg.setdefault(slug, {'sids': {}})
                s = a['sids'].setdefault(sid, {'opens': 0, 'first': t, 'last': t, 'secs': 0, 'max': 1, 'videos': [], 'book': 0, 'open_t': t, 'pings': 0})
                s['first'], s['last'] = min(s['first'], t), max(s['last'], t)
                if e.get('ip') and not s.get('ip'): s['ip'] = e['ip']
                if ev == 'open':
                    s['opens'] += 1
                    s['open_t'] = min(s.get('open_t', t), t); s['tz'] = p.get('tz') or ''; s['phone'] = bool(p.get('phone'))
                    s['w'] = p.get('w'); s['ua'] = (p.get('ua') or '')[:160]
                elif ev in ('slide', 'leave', 'ping', 'book'):
                    s['max'] = max(s['max'], int(p.get('max') or 0))
                    if ev in ('leave', 'ping'): s['secs'] = max(s['secs'], int(p.get('secs') or 0))
                    if ev == 'ping': s['pings'] = s.get('pings', 0) + 1
                    if ev == 'book': s['book'] += 1; s['book_t'] = t
                elif ev == 'video' and p.get('v') and p['v'] not in s['videos']: s['videos'].append(str(p['v'])[:60])
    st['offset'] = off
    cache = st.setdefault('geo', {})
    for a in agg.values():
        for s in a['sids'].values():
            if s.get('ip') and ('loc' not in s or 'org' not in s):
                s['loc'] = geo(s['ip'], cache); s['org'] = cache.get('org:' + s['ip'], '')
            s['bot'] = is_bot(s)


def sess_cc(s): return (s.get('loc') or '').rsplit(', ', 1)[-1] if s.get('loc') and ', ' in s['loc'] else tz_cc(s.get('tz'))


def counted(a):
    """Slug totals over the sessions that count (has an IP, not a bot, not from NOT_COUNTED_CC), None if none."""
    ss = [s for s in a['sids'].values() if s.get('ip') and not s.get('bot') and sess_cc(s) not in NOT_COUNTED_CC] if a else []
    if not ss: return None
    return {'opens': sum(s['opens'] for s in ss), 'sessions': len(ss), 'first': min(s['first'] for s in ss), 'last': max(s['last'] for s in ss),
            'max': max(s['max'] for s in ss), 'secs': sum(s['secs'] for s in ss), 'videos': list(dict.fromkeys(v for s in ss for v in s['videos'])),
            'book': sum(s['book'] for s in ss), 'sids': ss}


def where(ss):
    n = {}
    for s in ss:
        if s.get('loc'): n[s['loc']] = n.get(s['loc'], 0) + 1
    return ', '.join('%s (%d)' % (k, v) for k, v in sorted(n.items(), key=lambda x: -x[1]))


# ---------- Presentation Log ----------
def load_json(p, default):
    try: return json.load(open(p, encoding='utf-8'))
    except (OSError, ValueError): return default


def verdict(a, fs):
    """One plain sentence per lead; the prefixes in BAD DM Thomas once."""
    s, note = fs.get('status') or '', (fs.get('note') or '')[:120]
    if not a['in_msg']:
        if s == 'skipped: conversation': return 'Connect-only: has a conversation with Dave, never fed'
        if s == 'feed failed': return 'Connect-only: feed failed, %s' % note
        return 'Connect-only: feed pending (next flow run, every 30 min)'
    if not a['connected']: return 'not connected yet'
    pre = ''
    if not a['client_word']: pre += 'NO CLIENT WORD; '
    if s.startswith('stopped'): return pre + 'STOPPED: %s (%s)' % (s[9:], note)
    if not a['active']: return pre + 'inactive (%s)' % a['camp_status']
    if s == 'no deck version': return pre + 'NO DECK VERSION (%s), the flow stops the lead after message 1' % note
    if s == 'build failed': return pre + 'BUILD FAILED (%s tries): %s' % (fs.get('tries', '?'), note)
    if s == 'fields set':
        if not a['companyname']: pre += 'NO COMPANY NAME; '
        if a['live'] == 200 and a['hr_url']: return pre + 'OK'
        if a['live'] == 200: return pre + 'OK (deck live, campaign field set, list field not readable)'
        return pre + 'DECK NOT LIVE (%s), HeyReach would send a dead link' % a['live']
    if s == 'deck built': return pre + ('BUILT, fields next run' if a['live'] == 200 else 'BUILT, not live yet')
    if a['msg_out']:
        due = ts(a['last_ts'] + 4 * 86400) if a['last_ts'] else '?'
        return pre + 'MESSAGE 1 OUT, NO DECK YET (message 2 due about %s)' % due
    return pre + 'waiting for deck (flow every 30 min)'


def iso_ts(s):
    m = re.match(r'(\d{4})-(\d\d)-(\d\d)[T ](\d\d):(\d\d):(\d\d)', s or '')
    if not m: return 0
    return datetime.datetime(*map(int, m.groups()), tzinfo=datetime.timezone.utc).timestamp()


def leads_now(st):
    """{lid: facts} for every lead of 664625 plus the connected Connect-only leads."""
    conn = load_json(CONN_STATE, {})
    flow = load_json(FLOW_STATE, {})
    src, con_src = list_leads(MSG['list']), list_leads(CONNECT['list'])
    camp, con_camp = campaign_leads(MSG['campaign']), campaign_leads(CONNECT['campaign'])
    first = st.setdefault('first', {})   # own stamp when the tracker sees a lead connected before the flow did
    out = {}
    for cid, leads in ((MSG['campaign'], camp), (CONNECT['campaign'], con_camp)):
        for lid, x in leads.items():
            in_msg = cid == MSG['campaign']
            stt = x.get('leadConnectionStatus') or 'None'
            connected = bool(CONNECTED.search(stt)) or x.get('errorCode') == 'AlreadyAConnection' or lid in conn
            if not in_msg and (not connected or lid in camp): continue
            p = x.get('linkedInUserProfile') or {}
            l = src.get(lid) or con_src.get(lid) or {}
            cf = cf_of(l)
            c = conn.get(lid) or {}
            if connected and not c and lid not in first: first[lid] = {'first_ts': time.time(), 'first_seen': time.strftime('%Y-%m-%d %H:%M')}
            f = c or first.get(lid) or {}
            fs = flow.get(lid) or {}
            link = cf.get('presentation') or ''
            slug = (link or fs.get('link') or '').rstrip('/').split('/')[-1] if (link or fs.get('link')) else ''
            ms = x.get('leadMessageStatus') or 'None'
            out[lid] = {'name': ('%s %s' % (l.get('firstName') or p.get('firstName') or '', l.get('lastName') or p.get('lastName') or '')).strip(),
                        'company': cf.get('Company') or l.get('companyName') or p.get('companyName') or '', 'sender': x.get('linkedInSenderFullName') or SENDER_NAME,
                        'campaign': cid, 'status': stt, 'connected': connected, 'first_seen': f.get('first_seen', ''), 'first_ts': f.get('first_ts'),
                        'msg_status': ms, 'msg_out': ms != 'None', 'replied': 'Yes' if 'repl' in ms.lower() else 'No',
                        'camp_status': x.get('leadCampaignStatus') or '', 'active': (x.get('leadCampaignStatus') or '') not in INACTIVE,
                        'last_action': (x.get('lastActionTime') or '')[:19].replace('T', ' '), 'last_ts': iso_ts(x.get('lastActionTime')),
                        'client_word': cf.get('client_word') or '', 'companyname': cf.get('companyname') or (fs.get('company') if fs.get('status') == 'fields set' else '') or '',
                        'hr_url': link, 'flow_link': fs.get('link') or '', 'slug': slug, 'in_msg': in_msg, 'fs': fs}
    return out


def sync_log(sv, st, al):
    old = sv.values().get(spreadsheetId=SHEET, range="'%s'!E2:E" % TAB).execute().get('values', [])
    order = [r[0] if r else '' for r in old]
    have = set(order)
    for lid in sorted((l for l in al if l not in have), key=lambda l: (not al[l]['connected'], al[l].get('first_ts') or 9e12, al[l]['name'])): order.append(lid)
    live = {}
    rows, track, flagged = [], [], st.setdefault('flagged', [])
    messaged = opened = 0
    for lid in order:
        a = al.get(lid)
        if not a: rows.append([''] * NA); track.append([''] * len(TRACK_HDR)); continue
        a['live'] = live_code(a['slug'], live) if a['slug'] else ''
        fs = a['fs']
        chk = verdict(a, fs)
        due = ts(a['first_ts'] + 86400) if a['connected'] and a['first_ts'] else ''
        rows.append([a['name'], a['company'], a['sender'], a['campaign'], lid, a['status'], 'Yes' if a['connected'] else 'No', a['first_seen'], due,
                     a['msg_status'], a['replied'], a['camp_status'], a['last_action'], a['client_word'], a['companyname'],
                     a['hr_url'] or (a['flow_link'] and a['flow_link'] + ' (campaign field)') or '', a['slug'], fs.get('status', ''), fs.get('at', ''), a['live'], chk, (fs.get('note') or '')[:300]])
        t = counted(st['slugs'].get(a['slug'])) if a['slug'] else None
        track.append([t['opens'], t['sessions'], ts(t['first']), ts(t['last']), t['max'], t['secs'], ', '.join(t['videos']), t['book'], where(t['sids'])] if t else [''] * len(TRACK_HDR))
        if a['in_msg'] and a['msg_out']: messaged += 1; opened += 1 if t and t['opens'] else 0
        if chk.startswith(BAD) or any(b in chk for b in ('NO CLIENT WORD', 'NO COMPANY NAME')):
            kf = lid + '|' + chk[:24]
            if kf not in flagged: flagged.append(kf); alert('control check: %s (%s): %s' % (a['name'], a['company'], chk))
    if rows:
        sv.values().batchUpdate(spreadsheetId=SHEET, body={'valueInputOption': 'RAW', 'data': [
            {'range': "'%s'!A2" % TAB, 'values': rows}, {'range': "'%s'!%s2" % (TAB, TRACK_COL), 'values': track}]}).execute()
    st['open_rate'] = (messaged, opened)
    say('sheet synced:', len(rows), 'lead rows, messaged', messaged, 'opened', opened)
    return rows


def status_line(st, failed):
    """Run summary into the job log only (Thomas 2026-10-17: no Status tab in the sheet)."""
    t = time.time()
    if not failed: st['last_ok'] = t
    m, o = st.get('open_rate', (0, 0))
    say('status: last ok', ts(st.get('last_ok')), '| open rate',
        ('%d of %d messaged leads opened their deck (%.0f%%)' % (o, m, 100.0 * o / m)) if m else 'nobody messaged yet',
        '| this run', 'FAILED: ' + repr(failed)[:150] if failed else 'OK')


def crashed(e):
    say(traceback.format_exc())
    last = load_json(CRASH, {}).get('at', 0)
    if time.time() - last < 20 * 3600: return
    tb = traceback.format_exc().strip().splitlines()
    alert('symonds_track FAILED on the Mac: %s\n%s\nRetried every 6 h, this alert at most once a day. Log: ~/Desktop/AIOS/automations/mac-hub/logs/jobs/symonds_track.log'
          % (repr(e)[:200], (tb[-3] if len(tb) >= 3 else '')[:200]))
    json.dump({'at': time.time(), 'err': repr(e)[:200]}, open(CRASH, 'w', encoding='utf-8'))


def run():
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    st = load_json(STATE, {})
    read_events(st)
    json.dump(st, open(STATE, 'w', encoding='utf-8'))   # events are consumed, save before anything that can fail
    sv = sheets_svc()
    meta = ensure_tab(sv)
    failed = None
    try:
        al = leads_now(st)
        sync_log(sv, st, al)
    except Exception as e:
        failed = e; say('LOG SYNC FAILED:', repr(e))
    status_line(st, failed)
    json.dump(st, open(STATE, 'w', encoding='utf-8'))
    say('tracked decks:', len(st.get('slugs', {})))
    if failed: raise failed


def main():
    try: run()
    except Exception as e:
        crashed(e); raise


if __name__ == '__main__':
    main()
