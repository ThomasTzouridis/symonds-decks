"""Build one Dave Symonds Productions deck per spec: py build.py specs/<slug>.json -> ../<slug>/index.html"""
import json, sys, os, html
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
LOGOS = ''.join(f'<img src="../assets/logos/{n}" alt="">' for n in ["bedrock.png","rocket.png","lovesac.png","qualigence.svg","talenti.png","tedxdetroit.png","redico.png","related.png","ddl.png","americanhouse.png"])
for path in sys.argv[1:]:
    sp = json.load(open(path, encoding='utf-8'))
    e = html.escape
    co = e(sp['company'])
    prep = f"{e(sp['first_name'])} · {co}" if sp.get('first_name') else co
    lines = ''.join(f'<p>{l}</p>' for l in sp['why_lines'][:-1]) + f'<p class="turn">{sp["why_lines"][-1]}</p>'
    mark = f'<span class="co">{co}</span>'
    if sp.get('logo'):
        img = f'<img class="ll" src="../assets/leadlogos/{sp["logo"]}" alt="{co}">'
        mark = f'<span class="llb">{img}</span>' if sp.get('logo_badge') else img
    out = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
    for k, v in {'COMPANY': co, 'PREPARED': prep, 'CO_MARK': mark, 'WHY_HEAD': sp['why_head'], 'WHY_LINES': lines, 'WHY_IMG': sp.get('why_img', 'shoot_office.jpg'), 'WHY_CAP': e(sp.get('why_cap', 'A client interview, filmed on one content day')), 'LOGOS': LOGOS, 'ORG_1': sp['org_1'], 'ADS_1': sp['ads_1']}.items():
        out = out.replace('{{' + k + '}}', v)
    d = os.path.join(ROOT, sp['slug']); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(out)
    print('built', sp['slug'])
