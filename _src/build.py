"""Build one Dave Symonds Productions deck per spec: py build.py specs/<slug>.json -> ../<slug>/index.html"""
import json, sys, os, html
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
LOGOS = ''.join(f'<img src="../assets/logos/{n}.png" alt="">' for n in ["bedrock","lovesac","talenti","redico","related","americanhouse"])
for path in sys.argv[1:]:
    sp = json.load(open(path, encoding='utf-8'))
    e = html.escape
    co = e(sp['company'])
    prep = f"{e(sp['first_name'])} · {co}" if sp.get('first_name') else co
    lines = ''.join(f'<p>{l}</p>' for l in sp['saw_lines'][:-1]) + f'<p class="turn">{sp["saw_lines"][-1]}</p>'
    shot = (f'<figure class="shot"><img src="../assets/shots/{sp["shot"]}" alt="{co} website"><figcaption>{e(sp["shot_caption"])}, today</figcaption></figure>' if sp.get('shot') else '<div></div>')
    out = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
    for k, v in {'COMPANY': co, 'PREPARED': prep, 'SAW_LINES': lines, 'SHOT': shot, 'LOGOS': LOGOS, 'ORG_1': sp['org_1'], 'ADS_1': sp['ads_1']}.items():
        out = out.replace('{{' + k + '}}', v)
    d = os.path.join(ROOT, sp['slug']); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(out)
    print('built', sp['slug'])
