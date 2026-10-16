"""Build one Dave Symonds Productions deck per spec: py build.py specs/<slug>.json -> ../<slug>/index.html
Industry text comes from categories.json (spec "category": Construction, High end home services, Law firms, Financial services),
company details from the spec (why_l3, org_1 = Video 01, ads_1 = first ad bullet, film)."""
import json, sys, os, html
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
CATS = json.load(open(os.path.join(HERE, 'categories.json'), encoding='utf-8'))
LOGOS = ''.join(f'<img src="../assets/logos/{n}" alt="">' for n in ["bedrock.png","rocket.png","lovesac.png","qualigence.svg","talenti.png","tedxdetroit.png","redico.png","related.png","ddl.png","americanhouse.png"])
CASES = {"bedrock": ("w_bedrock.jpg", "50% 40%", "Bedrock Detroit · Brand Legend", "18,000", "people in the room", "The video that played Dan Gilbert onto the stage at the Rocket All Company Meeting.", "https://symondsproductions.com/video-marketing/brand-legend"),
         "capitol": ("w_capitolpark.jpg", "50% 50%", "Capitol Park · Real estate ads", "5x+ ROI", "on the ad campaign", "Lifestyle video ads for the residences around Capitol Park, built on the City Modern format.", "https://symondsproductions.com/video-marketing/lifestyle"),
         "citymodern": ("w_citymodern.jpg", "50% 50%", "City Modern · Real estate ads", "95%+", "of the properties filled", "Lifestyle video ads that built demand with an affluent audience for upscale apartments and condos.", "https://symondsproductions.com/video-marketing/lifestyle"),
         "qualigence": ("w_steve.jpg", "60% 40%", "Qualigence · Recruiting agency", "265K+", "views on the CEO reel", "A speaker reel for CEO Steve Lowisz that keeps bringing speaking opportunities and new business to the agency.", "https://symondsproductions.com/video-marketing/promotional-video")}
for path in sys.argv[1:]:
    sp = json.load(open(path, encoding='utf-8'))
    c = dict(CATS[sp['category']]); c.update({k: v for k, v in sp.items() if k in c})
    e = html.escape
    co = e(sp['company'])
    prep = f"{e(sp['first_name'])} · {co}" if sp.get('first_name') else co
    lines = f"<p>{c['why_l1']}</p><p>{c['why_l2']}</p><p class=\"turn\">{sp['why_l3']}</p>"
    mark = f'<span class="co">{co}</span>'
    if sp.get('logo'):
        img = f'<img class="ll" src="../assets/leadlogos/{sp["logo"]}" alt="{co}">'
        mark = f'<span class="llb">{img}</span>' if sp.get('logo_badge') else img
    vids = f'    <div class="m lead"><span class="lab">Video 01 · for {co}</span><h3>{sp["org_1"]}</h3><p>{c["vid_1_p"]}</p></div>\n'
    vids += ''.join(f'    <div class="m"><span class="lab">Video 0{n}</span><h3>{c[f"vid_{n}_h"]}</h3><p>{c[f"vid_{n}_p"]}</p></div>\n' for n in (2, 3, 4))
    cases = ''.join(f'    <a class="case" href="{u}" target="_blank" rel="noopener"><div class="img" style="background-image:url(../assets/img/{i});background-position:{pos}"></div><span class="yr">{lab}</span><div class="res"><b>{n}</b><span>{nl}</span></div><p>{d}</p><span class="go">See the case →</span></a>\n' for i, pos, lab, n, nl, d, u in (CASES[k] for k in c['cases']))
    out = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
    for k, v in {'COMPANY': co, 'PREPARED': prep, 'CO_MARK': mark, 'WHY_HEAD': c['why_head'], 'WHY_LINES': lines,
                 'WHY_IMG': c['why_img'], 'WHY_CAP': e(c['why_cap']), 'LOGOS': LOGOS,
                 'VID_HEAD': c['vid_head'], 'VIDS': vids,
                 'HELP_HEAD': c['help_head'], 'ADS_H3': c['ads_h3'], 'SOC_H3': c['soc_h3'],
                 'ADS_LIS': f"<li class=\"lead\">{sp['ads_1']}</li><li>{c['ads_2']}</li><li>{c['ads_3']}</li><li>{c['ads_4']}</li>",
                 'SOC_LIS': f"<li>{c['soc_1']}</li><li>{c['soc_2']}</li><li>{c['soc_3']}</li><li>{c['soc_4']}</li>",
                 'FILM': sp['film'], 'CASES': cases}.items():
        out = out.replace('{{' + k + '}}', v)
    assert '{{' not in out, path
    d = os.path.join(ROOT, sp['slug']); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(out)
    print('built', sp['slug'], '·', sp['category'])
