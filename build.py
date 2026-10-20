#!/usr/bin/env python3
"""Build SEO pages for AllStatesWire.

Reads the story data (ART, PH) from index.html and writes:
  news/<slug>/index.html   one static page per dated story (title, description,
                           Open Graph / Twitter tags, NewsArticle JSON-LD)
  sitemap.xml, robots.txt  for Google
  index.html               head meta tags + links from cards to the static pages

Run after adding stories:  python3 build.py
"""
import html, json, os, re, shutil, unicodedata
from datetime import datetime

SITE = "https://allstateswire.com"
ROOT = os.path.dirname(os.path.abspath(__file__))
NAME = "AllStatesWire"
TAGLINE = "The Pulse of All 50 States"
HOME_DESC = "AllStatesWire covers news from all 50 states: politics, courts, business, weather, sports, health and travel across America."

src = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
ART = json.loads(re.search(r"const ART=(\{.*?\});\n", src).group(1))
PH = json.loads(re.search(r"const PH=(\{.*?\});\n", src).group(1))


def slugify(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t.lower()).strip("-")
    return re.sub(r"-+", "-", t)[:80].rstrip("-")


def iso(d):
    return datetime.strptime(d, "%B %d, %Y").strftime("%Y-%m-%d")


def e(t):
    return html.escape(t, quote=True)


# Only real, dated stories get public pages (the undated design samples do not).
stories = [k for k in ART if len(ART[k]) > 5 and ART[k][5]]
SLUG, used = {}, set()
for k in stories:
    s = slugify(ART[k][2]) or k
    while s in used:
        s += "-" + k
    used.add(s)
    SLUG[k] = s

# ---------- shared pieces taken from index.html ----------
style = re.search(r"<style>.*?</style>", src, re.S).group(0)
fonts = re.search(r'<link rel="preconnect".*?display=swap">', src, re.S).group(0)
top = src[src.index('<svg width="0"'):src.index("</nav>", src.index('<nav class="mainnav"')) + 6]
footer = src[src.index("<footer>"):src.index("</footer>") + 9]


def site_links(block):
    block = block.replace('href="#home"', 'href="/"').replace('href="#cat-', 'href="/#cat-')
    block = re.sub(r'href="#story-(\w+)"', lambda m: f'href="/news/{SLUG[m.group(1)]}/"' if m.group(1) in SLUG else 'href="/"', block)
    return block


top_s, footer_s = site_links(top), site_links(footer)
for d in ("news",):
    shutil.rmtree(os.path.join(ROOT, d), ignore_errors=True)


def head(title, desc, url, image, kind, extra=""):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<link rel="icon" type="image/png" href="/favicon.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta property="og:site_name" content="{NAME}">
<meta property="og:type" content="{kind}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{image}">
<meta property="og:locale" content="en_US">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">
<meta name="twitter:image" content="{image}">
{extra}"""


ORG = {"@type": "NewsMediaOrganization", "name": NAME, "url": SITE + "/",
       "logo": {"@type": "ImageObject", "url": SITE + "/logo.png", "width": 600, "height": 120}}

# ---------- story pages ----------
order = sorted(stories, key=lambda k: iso(ART[k][5]), reverse=True)
for k in stories:
    cat, dl, title, dek, body, date = ART[k][:6]
    src_url = ART[k][6] if len(ART[k]) > 6 else ""
    note = ART[k][7] if len(ART[k]) > 7 else ""
    img = PH.get(k, ["", "", "", ""])
    img_url = f"{SITE}/images/{k}.jpg"
    url = f"{SITE}/news/{SLUG[k]}/"
    credit = f"Photo: {img[2]}" + (f" / Wikimedia Commons, {img[3]}" if img[3] else "")
    ld = {"@context": "https://schema.org", "@type": "NewsArticle", "headline": title[:110],
          "description": dek, "image": [img_url], "datePublished": iso(date), "dateModified": iso(date),
          "articleSection": cat, "mainEntityOfPage": url,
          "author": {"@type": "Organization", "name": NAME + " Staff", "url": SITE + "/"},
          "publisher": ORG}
    extra = (f'<meta property="article:published_time" content="{iso(date)}">\n'
             f'<meta property="article:section" content="{e(cat)}">\n'
             f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>\n')
    more = [x for x in order if x != k and ART[x][0] == cat][:3]
    more += [x for x in order if x != k and x not in more][: 3 - len(more)]
    cards = "".join(
        f'<article class="card"><a href="/news/{SLUG[x]}/" class="ph has-img" aria-hidden="true" tabindex="-1">'
        f'<img src="/images/{x}.jpg" alt="" loading="lazy"></a><div class="body">'
        f'<a class="eyebrow" href="/#cat-{ART[x][0].lower()}">{e(ART[x][0])}</a>'
        f'<h3><a href="/news/{SLUG[x]}/">{e(ART[x][2])}</a></h3></div></article>' for x in more)
    paras = "".join(
        f"<p>{f'<span class=\"dl\">{e(dl)} (ASW) —</span> ' if i == 0 else ''}{e(p)}</p>" for i, p in enumerate(body))
    if src_url:
        foot = f'<p class="st-note">Written by {NAME} from public reports. <a href="{e(src_url)}" target="_blank" rel="noopener">Read the original source report ↗</a></p>'
    else:
        foot = f'<p class="st-note">{e(note or "Written by " + NAME + " from public reports.")}</p>'
    page = head(f"{title} | {NAME}", dek, url, img_url, "article", extra) + fonts + "\n" + style + f"""
</head>
<body>
{top_s}
<main class="wrap">
<article class="story">
  <a class="back" href="/">← Back to home</a>
  <header class="st-head"><a class="chip" href="/#cat-{cat.lower()}">{e(cat)}</a><h1>{e(title)}</h1><p class="dek">{e(dek)}</p>
  <div class="st-meta"><strong>{e(dl)} (ASW)</strong> · By {NAME} Staff · <time datetime="{iso(date)}">{e(date)}</time></div></header>
  <figure class="st-fig"><img src="/images/{k}.jpg" alt="{e(img[1])}"><figcaption>{e(img[1])}. {e(credit)}</figcaption></figure>
  <div class="st-body">{paras}{foot}</div>
  <section class="st-more"><div class="sec-head"><h2>More from {NAME}</h2><span class="rule"></span></div><div class="cards">{cards}</div></section>
</article>
</main>
{footer_s}
<script>try{{document.getElementById('today').textContent=new Date().toLocaleDateString('en-US',{{weekday:'long',year:'numeric',month:'long',day:'numeric',timeZone:'America/Chicago'}});}}catch(e){{}}</script>
</body>
</html>
"""
    d = os.path.join(ROOT, "news", SLUG[k])
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(page)

# ---------- home page head + links ----------
home_ld = {"@context": "https://schema.org", "@graph": [
    {"@type": "WebSite", "name": NAME, "url": SITE + "/", "description": HOME_DESC},
    dict(ORG, **{"@context": None})]}
home_ld["@graph"][1].pop("@context")
home_head = f"""<!--seo-start-->
<meta name="description" content="{e(HOME_DESC)}">
<link rel="canonical" href="{SITE}/">
<link rel="icon" type="image/png" href="/favicon.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta property="og:site_name" content="{NAME}">
<meta property="og:type" content="website">
<meta property="og:title" content="{NAME} | {TAGLINE}">
<meta property="og:description" content="{e(HOME_DESC)}">
<meta property="og:url" content="{SITE}/">
<meta property="og:image" content="{SITE}/og-image.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{SITE}/og-image.jpg">
<script type="application/ld+json">{json.dumps(home_ld, ensure_ascii=False)}</script>
<!--seo-end-->"""
out = re.sub(r"\n?<!--seo-start-->.*?<!--seo-end-->", "", src, flags=re.S)
out = re.sub(r"<title>.*?</title>", f"<title>{NAME} | {TAGLINE}</title>\n" + home_head, out, count=1, flags=re.S)
# clicks on story cards go to the real story page
hook = "if(window.SLUG&&SLUG[el.dataset.story]){location.href='/news/'+SLUG[el.dataset.story]+'/';return;}"
if hook not in out:
    out = out.replace("e.preventDefault(); const h='#story-'+el.dataset.story;",
                      "e.preventDefault(); " + hook + " const h='#story-'+el.dataset.story;", 1)
links = f"""<!--slug-start--><script>window.SLUG={json.dumps(SLUG)};
(function(){{var m=/^#story-(\\w+)$/.exec(location.hash);if(m&&SLUG[m[1]]){{location.replace('/news/'+SLUG[m[1]]+'/');return;}}
function fix(){{document.querySelectorAll('a[href^="#story-"]').forEach(function(a){{var k=a.getAttribute('href').slice(7);if(SLUG[k])a.setAttribute('href','/news/'+SLUG[k]+'/');}});}}
fix();new MutationObserver(fix).observe(document.body,{{childList:true,subtree:true}});}})();</script><!--slug-end-->"""
out = re.sub(r"<!--slug-start-->.*?<!--slug-end-->", "", out, flags=re.S)
out = out.rstrip() + "\n" + links + "\n"
open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(out)

# ---------- sitemap + robots ----------
today = datetime.now().strftime("%Y-%m-%d")
urls = [f"  <url><loc>{SITE}/</loc><lastmod>{today}</lastmod><changefreq>hourly</changefreq><priority>1.0</priority></url>"]
for k in order:
    urls.append(f"  <url><loc>{SITE}/news/{SLUG[k]}/</loc><lastmod>{iso(ART[k][5])}</lastmod>"
                f"<image:image><image:loc>{SITE}/images/{k}.jpg</image:loc></image:image></url>")
open(os.path.join(ROOT, "sitemap.xml"), "w").write(
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
    'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n' + "\n".join(urls) + "\n</urlset>\n")
open(os.path.join(ROOT, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n")
print(f"{len(stories)} story pages, sitemap with {len(urls)} URLs")
