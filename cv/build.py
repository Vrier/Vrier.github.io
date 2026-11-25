#!/usr/bin/env python3
"""Build the CV page and PDF from cv/cv.yml.

From the repo root:
    python3 cv/build.py            # writes cv/index.html, files/Thomas-Stephen-CV.pdf,
                                   # and the CV parts of index.html (Teaching, Talks list, short CV)
    python3 cv/build.py --no-pdf   # everything except the PDF

Needs PyYAML, and Playwright with a Chromium browser for the PDF.
Set CHROME=/path/to/chrome to print with an installed Chrome instead.
"""
import argparse
import html
import os
import pathlib
import re
import sys
import tempfile

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "cv" / "cv.yml"
OUT_HTML = ROOT / "cv" / "index.html"
HOME = ROOT / "index.html"
OUT_PDF = ROOT / "files" / "Thomas-Stephen-CV.pdf"
PDF_HREF = "../files/Thomas-Stephen-CV.pdf"
SITE = "https://www.tstephen.com"


# ---------------------------------------------------------------- text helpers

def inline(text, root=".."):
    """Escape text, then apply *italic*, **bold**, ~sub~ and [label](url).

    Site links (/files/...) are made relative: root ".." for /cv/, "." for the homepage."""
    s = html.escape(str(text), quote=False)

    def link(m):
        label, url = m.group(1), m.group(2)
        if url.startswith("/"):
            url = root + url
        attrs = ' target="_blank" rel="noopener"' if url.startswith("http") else ""
        return f'<a href="{url.replace(chr(34), "%22")}"{attrs}>{label}</a>'

    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
    s = re.sub(r"~(.+?)~", r"<sub>\1</sub>", s)
    return s


def dates(text):
    return re.sub(r"(\d{4})\s*-\s*(\d{4}|present)", "\\1–\\2", str(text or ""))


def plain(text):
    """Text without markup, for attributes and the page title."""
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", str(text))
    return re.sub(r"[*~]", "", s)


# ---------------------------------------------------------------- blocks

def row(item):
    parts = []
    fields = {"what": item.get("what"), "detail": item.get("detail"),
              "topics": " · ".join(item.get("topics") or []), "where": item.get("where")}
    for key, cls in (("what", "what"), ("detail", "detail"), ("topics", "detail topics"), ("where", "where")):
        if fields[key]:
            parts.append(f'<div class="{cls}">{inline(fields[key])}</div>')
    if item.get("notes"):
        lis = "".join(f"<li>{inline(n)}</li>" for n in item["notes"])
        parts.append(f'<ul class="notes">{lis}</ul>')
    return (f'<div class="row"><div class="when">{html.escape(dates(item.get("when")))}</div>'
            f'<div class="body">{"".join(parts)}</div></div>')


def talks(items):
    out, last = [], None
    for t in items:
        year = str(t.get("when", ""))
        shown = html.escape(year) if year != last else ""
        last = year
        co = f'<span class="co">with {inline(t["with"])}</span>' if t.get("with") else ""
        out.append(
            f'<div class="talk"><div class="yr">{shown}</div>'
            f'<div class="tt"><span class="ev">{inline(t["event"])}'
            f'<span class="at">{" · " + inline(t["where"]) if t.get("where") else ""}</span></span>'
            f'<em>{inline(t["title"])}</em>{co}</div>'
            f'<div class="vn">{inline(t.get("where", ""))}</div></div>')
    return '<div class="talks">' + "".join(out) + "</div>"


def on_cv(items):
    """Items for the CV page and PDF: an item marked `cv: false` shows on the homepage only."""
    return [i for i in items if i.get("cv", True) is not False]


def block(node, level=0):
    out = []
    if node.get("items"):
        if node.get("layout") == "talks":
            out.append(talks(on_cv(node["items"])))
        elif node.get("layout") == "inline":
            lis = "".join(f'<li>{inline(i["what"])}' + (f' <span class="detail">{inline(i["detail"])}</span>' if i.get("detail") else "") + "</li>"
                          for i in node["items"])
            out.append(f'<div class="rows"><div class="row"><div class="when"></div><div class="body"><ul class="inline-list">{lis}</ul></div></div></div>')
        else:
            out.append('<div class="rows">' + "".join(row(i) for i in node["items"]) + "</div>")
    for g in node.get("groups", []):
        tag = "h3" if level == 0 else "h4"
        out.append(f'<div class="group lvl{level}"><{tag}>{inline(g["title"])}</{tag}>{block(g, level + 1)}</div>')
    return "".join(out)


# ---------------------------------------------------------------- page

CSS = """
:root{--paper:oklch(0.986 0.004 95);--paper-2:oklch(0.968 0.006 88);--ink:oklch(0.245 0.012 260);
--ink-soft:oklch(0.44 0.012 260);--ink-faint:oklch(0.54 0.01 260);--rule:oklch(0.885 0.008 260);
--rule-strong:oklch(0.8 0.01 260);--accent:oklch(0.55 0.15 33);--accent-deep:oklch(0.46 0.14 33);
--accent-soft:oklch(0.95 0.03 45);--sans:"Space Grotesk",system-ui,sans-serif;--serif:"Newsreader",Georgia,serif;
--mono:"JetBrains Mono",ui-monospace,monospace;--maxw:1180px;--gutter:clamp(20px,5vw,64px)}
*{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:84px}
.skip{position:absolute;left:12px;top:-64px;z-index:300;background:var(--ink);color:var(--paper);padding:10px 14px;border-radius:6px;font-family:var(--mono);font-size:.8rem;letter-spacing:.04em;text-decoration:none}
.skip:focus{top:12px}
@media print{.skip{display:none}}
a:focus-visible,button:focus-visible{outline:2px solid var(--accent-deep);outline-offset:3px}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*::before,*::after{transition:none!important;animation:none!important}}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--serif);
font-size:clamp(1.02rem,0.5vw + 0.95rem,1.16rem);line-height:1.62;-webkit-font-smoothing:antialiased;font-synthesis:none}
a{color:inherit}
::selection{background:var(--accent-soft)}
.wrap{max-width:var(--maxw);margin:0 auto;padding-inline:var(--gutter)}
header.site{position:sticky;top:0;z-index:50;background:color-mix(in oklab,var(--paper) 88%,transparent);
backdrop-filter:blur(10px);border-bottom:1px solid var(--rule)}
.bar{display:flex;align-items:center;justify-content:space-between;gap:8px 18px;min-height:64px;flex-wrap:wrap}
.brand{display:flex;align-items:baseline;gap:12px;text-decoration:none}
.brand b{font-family:var(--sans);font-weight:600;font-size:1.02rem;letter-spacing:-0.01em}
.brand .tag{font-family:var(--mono);font-size:0.76rem;letter-spacing:0.08em;text-transform:uppercase;color:var(--ink-faint)}
nav.secnav{display:flex;gap:2px;align-items:center}
nav.secnav a{font-family:var(--mono);font-size:0.78rem;letter-spacing:0.04em;text-transform:uppercase;text-decoration:none;
color:var(--ink-soft);padding:8px 10px;border-radius:6px;position:relative;white-space:nowrap;transition:color .18s,background .18s}
nav.secnav a:hover{color:var(--ink);background:var(--paper-2)}
nav.secnav a.active{color:var(--accent-deep)}
nav.secnav a.active::before{content:"";position:absolute;left:10px;right:10px;bottom:3px;height:1.5px;background:var(--accent)}
.btn{font-family:var(--mono);font-size:0.8rem;letter-spacing:0.04em;text-transform:uppercase;text-decoration:none;
background:var(--ink);color:var(--paper);padding:13px 20px;border-radius:7px;display:inline-flex;gap:10px;align-items:center;
transition:.18s;white-space:nowrap}
.btn:hover{background:var(--accent-deep)}
.intro{padding-block:clamp(44px,7vw,84px) clamp(28px,4vw,44px)}
h1.name{font-family:var(--sans);font-weight:600;letter-spacing:-0.03em;line-height:1;font-size:clamp(2.4rem,6vw,4rem);margin:0 0 18px}
.pos{font-family:var(--mono);font-size:0.8rem;letter-spacing:0.06em;text-transform:uppercase;color:var(--accent-deep);
margin:0 0 22px;max-width:72ch;line-height:1.6}
ul.contact{list-style:none;margin:0 0 28px;padding:0;display:flex;flex-wrap:wrap;gap:10px}
ul.contact a{font-family:var(--mono);font-size:0.8rem;letter-spacing:0.03em;color:var(--ink-soft);border:1px solid var(--rule-strong);
border-radius:999px;padding:6px 14px;text-decoration:none;display:inline-flex;transition:.18s}
ul.contact a:hover{border-color:var(--accent);color:var(--accent-deep);background:var(--accent-soft)}
.actions{display:flex;flex-wrap:wrap;align-items:center;gap:18px}
.upd{font-family:var(--mono);font-size:0.78rem;letter-spacing:0.04em;text-transform:uppercase;color:var(--ink-faint)}
main section{padding-block:clamp(40px,6vw,72px);border-top:1px solid var(--rule)}
.sec-head{display:flex;align-items:baseline;gap:18px;margin-bottom:30px}
.sec-num{font-family:var(--mono);font-size:0.8rem;color:var(--accent-deep);font-weight:600;letter-spacing:0.04em}
.sec-title{font-family:var(--sans);font-weight:600;font-size:clamp(1.5rem,2.6vw,2.05rem);letter-spacing:-0.02em;margin:0}
.group{margin-top:34px}
.group:first-child{margin-top:0}
.group h3{font-family:var(--sans);font-weight:600;font-size:1.14rem;letter-spacing:-0.01em;margin:0 0 12px}
.group.lvl1{margin-top:22px}
.group h4{font-family:var(--mono);font-weight:500;font-size:0.8rem;letter-spacing:0.06em;text-transform:uppercase;
color:var(--ink-soft);margin:0 0 8px}
.rows,.talks{display:flex;flex-direction:column}
.row{display:grid;grid-template-columns:130px 1fr;gap:22px;padding:13px 0;border-top:1px solid var(--rule)}
.row:first-child,.talk:first-child{border-top:1px solid var(--rule-strong)}
.row .when,.talk .yr{font-family:var(--mono);font-size:0.84rem;color:var(--accent-deep);font-weight:500;padding-top:2px}
.row .what{font-family:var(--sans);font-weight:500;font-size:1.02rem;letter-spacing:-0.01em;line-height:1.4}
.row .detail{color:var(--ink-soft);line-height:1.5;margin-top:2px}
.row .where{font-family:var(--mono);font-size:0.8rem;color:var(--ink-soft);margin-top:4px}
.row ul.notes{margin:6px 0 0;padding-left:1.1em;color:var(--ink-soft)}
.row ul.notes li{margin:2px 0}
.inline-list{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;font-family:var(--sans);font-weight:500;font-size:1.02rem;letter-spacing:-0.01em;line-height:1.5}
.inline-list li+li::before{content:"·";margin:0 12px;color:var(--ink-faint);font-weight:400}
.inline-list .detail{font-family:var(--serif);font-weight:400;color:var(--ink-soft)}
.body a,.tt a{text-decoration-color:var(--rule-strong);text-underline-offset:3px}
.body a:hover,.tt a:hover{color:var(--accent-deep);text-decoration-color:var(--accent)}
.talk{display:grid;grid-template-columns:130px 1fr 0.6fr;gap:22px;align-items:baseline;padding:16px 0;border-top:1px solid var(--rule)}
.talk .tt{font-family:var(--serif);font-style:italic;font-size:1.06rem;line-height:1.4}
.talk .tt .ev{display:block;font-style:normal;font-family:var(--sans);font-size:0.86rem;font-weight:500;letter-spacing:-0.01em;
color:var(--ink);margin-bottom:3px}
.talk .tt .co{font-style:normal;font-family:var(--mono);font-size:0.78rem;color:var(--ink-faint);display:block;margin-top:4px}
.talk .vn{font-family:var(--mono);font-size:0.8rem;color:var(--ink-soft);text-align:right}
.talk .at{display:none}
footer{border-top:1px solid var(--rule);padding-block:34px}
.foot{display:flex;flex-wrap:wrap;gap:14px;justify-content:space-between;align-items:center;font-family:var(--mono);
font-size:0.76rem;letter-spacing:0.04em;color:var(--ink-faint);text-transform:uppercase}
@media screen and (max-width:900px){
  nav.secnav{order:3;width:100%;overflow-x:auto;padding-bottom:8px;margin-top:-4px;scrollbar-width:none}
  nav.secnav::-webkit-scrollbar{display:none}
  html{scroll-padding-top:120px}
  .talk{grid-template-columns:90px 1fr}
  .talk .vn{grid-column:2;text-align:left;margin-top:2px}
  .row{grid-template-columns:90px 1fr}
}
@media screen and (max-width:620px){
  .row,.talk{grid-template-columns:1fr;gap:3px}
  .talk .vn{grid-column:1}
  .row .when:empty,.talk .yr:empty{display:none}
  .inline-list{flex-direction:column;gap:6px}
  .inline-list li+li::before{display:none}
}
@media print{
  :root{--paper:#fff}
  body{font-size:9.6pt;line-height:1.28;background:#fff}
  header.site,footer,.actions{display:none!important}
  .wrap{max-width:none;padding:0}
  .intro{padding:0 0 9pt}
  h1.name{font-size:21pt;margin:0 0 5pt}
  .pos{font-size:7.6pt;margin:0 0 5pt;letter-spacing:0.05em}
  ul.contact{gap:0;margin:0}
  ul.contact a{border:0;padding:0;font-size:8.2pt;color:var(--ink-soft)}
  ul.contact li+li::before{content:"·";margin:0 7pt;color:var(--ink-faint);font-family:var(--mono)}
  main section{padding:7pt 0 2pt;border-top:0.75pt solid var(--rule-strong)}
  .sec-head{margin-bottom:5pt;gap:8pt;break-after:avoid}
  .sec-num{font-size:7.6pt}
  .sec-title{font-size:12.5pt}
  .group{margin-top:6pt}
  .group.lvl1{margin-top:6pt}
  .group h3{font-size:10pt;margin:0 0 3pt;break-after:avoid}
  .group h4{font-size:7.2pt;margin:0 0 2pt;break-after:avoid}
  .row,.talk{grid-template-columns:20mm 1fr;gap:8pt;padding:1.9pt 0;border-top:0.5pt solid var(--rule);break-inside:avoid}
  .row:first-child,.talk:first-child{border-top:0.5pt solid var(--rule-strong)}
  .talk .vn{display:none}
  .talk .at{display:inline;font-family:var(--serif);font-weight:400;color:var(--ink-soft)}
  .row .when,.talk .yr{font-size:7.8pt;padding-top:1pt}
  .row .what{font-size:9.6pt}
  .row .detail{font-size:9.2pt;margin-top:0}
  .row .what,.row .detail{display:inline}
  .inline-list{font-size:9.6pt}
  .inline-list li+li::before{margin:0 7pt}
  .row .what+.detail::before{content:"  ·  ";white-space:pre;color:var(--ink-faint)}
  .row .detail.topics::before{content:": "}
  .row .where{font-size:7.8pt;margin-top:1pt}
  .row ul.notes{margin-top:1pt}
  .row ul.notes li{margin:0}
  .talk .tt{font-size:9.6pt;line-height:1.3}
  .talk .tt .ev{font-size:8.4pt;margin-bottom:0}
  .talk .tt .co{font-size:7.4pt;display:inline;margin:0 0 0 5pt}
  .talk .tt .co::before{content:"· "}
  a{text-decoration:none}
}
"""

SCRIPT = """
(function(){
  if(!('IntersectionObserver' in window))return;
  var links={};
  document.querySelectorAll('nav.secnav a').forEach(function(a){links[a.getAttribute('href').slice(1)]=a;});
  var obs=new IntersectionObserver(function(entries){
    entries.forEach(function(e){
      if(!e.isIntersecting)return;
      Object.keys(links).forEach(function(k){links[k].classList.remove('active');});
      if(links[e.target.id])links[e.target.id].classList.add('active');
    });
  },{rootMargin:'-40% 0px -55% 0px'});
  document.querySelectorAll('main section[id]').forEach(function(s){obs.observe(s);});
})();
"""

# Fonts are served from the site itself (fonts/, see fonts/fonts.css); nothing loads from Google.
FONT_LINKS = """<link rel="preload" href="../fonts/newsreader-latin-opsz-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="../fonts/space-grotesk-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="../fonts/fonts.css">"""


def page(cv):
    c = cv["contact"]
    phone_href = "tel:" + re.sub(r"[^\d+]", "", c["phone"])
    contact = (f'<li><a href="{phone_href}">{html.escape(c["phone"])}</a></li>'
               f'<li><a href="mailto:{c["email"]}">{html.escape(c["email"])}</a></li>'
               f'<li><a href="https://{c["website"]}">{html.escape(c["website"])}</a></li>')
    if c.get("orcid"):
        contact += f'<li><a href="https://orcid.org/{c["orcid"]}">ORCID {html.escape(c["orcid"])}</a></li>'
    nav = "".join(f'<a href="#{s["id"]}">{html.escape(s.get("nav", plain(s["title"])))}</a>' for s in cv["sections"])
    sections = "".join(
        f'<section id="{s["id"]}"><div class="wrap"><div class="sec-head"><span class="sec-num">{n:02d}</span>'
        f'<h2 class="sec-title">{inline(s["title"])}</h2></div>{block(s)}</div></section>'
        for n, s in enumerate(cv["sections"], 1))
    name = plain(cv["name"])
    updated = html.escape(cv["updated"])
    year = re.search(r"\d{4}", cv["updated"]).group(0)
    return f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Thomas Stephen: Curriculum Vitae</title>
<meta name="description" content="Curriculum vitae of {html.escape(name)}: education, employment, teaching, organisation and presentations.">
<link rel="canonical" href="{SITE}/cv/">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Thomas Stephen">
<meta property="og:title" content="Thomas Stephen: Curriculum Vitae">
<meta property="og:description" content="Curriculum vitae of {html.escape(name)}: education, employment, teaching, organisation and presentations.">
<meta property="og:url" content="{SITE}/cv/">
<meta property="og:image" content="{SITE}/images/preview.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Thomas Stephen, Fellow in Linguistics, Trinity College Dublin">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="image/png" href="../images/favicon.png">
{FONT_LINKS}
<style>{CSS}</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<!-- Generated by cv/build.py from cv/cv.yml. Edit cv.yml and rebuild; do not edit this file. -->
<header class="site">
  <div class="wrap bar">
    <a class="brand" href="../"><b>Thomas Stephen</b><span class="tag">Curriculum Vitae</span></a>
    <nav class="secnav" aria-label="Sections">{nav}</nav>
  </div>
</header>
<main id="main">
  <div class="wrap intro">
    <h1 class="name">{inline(cv["name"])}</h1>
    <p class="pos">{inline(cv["position"])}</p>
    <ul class="contact">{contact}</ul>
    <div class="actions">
      <a class="btn" href="{PDF_HREF}" download>Download PDF <span class="ar">↓</span></a>
      <span class="upd">Updated {updated}</span>
    </div>
  </div>
  {sections}
</main>
<footer>
  <div class="wrap foot">
    <span>© {year} Thomas Stephen</span>
    <span>Curriculum Vitae · Updated {updated}</span>
  </div>
</footer>
<script>{SCRIPT}</script>
</body>
</html>
"""


# ---------------------------------------------------------------- homepage parts

def kw_attr(kws):
    """data-kw for the keyword highlighting in About (empty: fades for every keyword)."""
    return f' data-kw="{html.escape(" ".join(kws or []))}"'


def check_keywords(cv, page_html):
    """Every kw slug in cv.yml must be one of the keyword buttons in index.html."""
    known = set(re.findall(r'class="key"[^>]*data-kw="([a-z-]+)"', page_html))
    used = set()

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "kw":
                    used.update(v or [])
                elif k == "topic_kw":
                    for kws in v.values():
                        used.update(kws or [])
                else:
                    walk(v)
        elif isinstance(node, list):
            for x in node:
                walk(x)
    walk(cv)
    unknown = sorted(used - known)
    if unknown:
        sys.exit(f"cv.yml uses keyword tags with no button in index.html: {', '.join(unknown)}")


def home_talks(items):
    """The homepage Talks list, in its own markup (a year on every row)."""
    rows = []
    for t in items:
        co = f'<span class="co">with {inline(t["with"], ".")}</span>' if t.get("with") else ""
        rows.append(f'        <div class="talk"{kw_attr(t.get("kw"))}><div class="yr">{html.escape(str(t.get("when", "")))}</div>'
                    f'<div class="tt"><span class="ev">{inline(t["event"], ".")}</span>'
                    f'<em>{inline(t["title"], ".")}</em>{co}</div>'
                    f'<div class="vn">{inline(t.get("where", ""), ".")}</div></div>')
    return "\n".join(rows) + "\n"


def home_rows(items):
    out = []
    for i in items:
        body = f'<div class="what">{inline(i["what"], ".")}</div>'
        if i.get("detail"):
            body += f'<div class="where">{inline(i["detail"], ".")}</div>'
        if i.get("where"):
            body += f'<div class="where">{inline(i["where"], ".")}</div>'
        if i.get("notes"):
            body += '<ul class="notes">' + "".join(f"<li>{inline(n, '.')}</li>" for n in i["notes"]) + "</ul>"
        out.append(f'          <div class="cvs-row"><div class="when">{html.escape(dates(i.get("when")))}</div><div>{body}</div></div>')
    return out


def home_summary(cv):
    """The short CV in section 07: columns of sections, as listed under homepage: in cv.yml."""
    by_id = {s["id"]: s for s in cv["sections"]}
    cols = []
    for col in cv["homepage"]["summary_columns"]:
        parts = []
        for entry in col:
            if isinstance(entry, dict):  # one group of a section, optionally retitled
                group = next(g for g in by_id[entry["section"]]["groups"] if g["title"] == entry["group"])
                blocks = [(entry.get("title", group["title"]), group)]
            else:
                sec = by_id[entry]
                blocks = [(sec["title"], sec)] if sec.get("items") else [(g["title"], g) for g in sec.get("groups", [])]
            for title, node in blocks:
                parts.append(f"          <h3>{inline(title, '.')}</h3>")
                if node.get("layout") == "inline":
                    lis = "".join(f"<li>{inline(i['what'], '.')}</li>" for i in node["items"])
                    parts.append(f'          <ul class="cvs-list">{lis}</ul>')
                else:
                    parts.extend(home_rows(node["items"]))
        cols.append('        <div>\n' + "\n".join(parts) + '\n        </div>')
    return '      <div class="cvs">\n' + "\n".join(cols) + '\n      </div>\n'


LINK_ICON = ('<svg class="lk" viewBox="0 0 24 24" width="15" height="15" aria-hidden="true">'
             '<path d="M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1"/>'
             '<path d="M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/></svg>')


def find_group(node, title):
    """The group with this title anywhere under node (a section or group)."""
    for g in node.get("groups", []):
        if g.get("title") == title:
            return g
        hit = find_group(g, title)
        if hit:
            return hit
    return None


def count_theses(cv):
    """Replace {theses:AT} in the teaching section with the number of named theses at AT."""
    teaching = next(s for s in cv["sections"] if s["id"] == "teaching")

    def walk(node):
        for g in node.get("groups", []):
            for item in g.get("items", []):
                for at in re.findall(r"\{theses:([^}]+)\}", str(item.get("what", ""))):
                    n = sum(1 for t in g.get("theses", []) if t.get("at") == at)
                    item["what"] = item["what"].replace("{theses:%s}" % at, str(n))
            walk(g)
    walk(teaching)


def home_teaching(cv):
    """Section 03: institutions, summer-school cards and supervision, as mapped under homepage: teaching."""
    conf = cv["homepage"]["teaching"]
    teaching = next(s for s in cv["sections"] if s["id"] == "teaching")
    out = []
    for inst in conf["institutions"]:
        cols = []
        for col in inst["columns"]:
            if col.get("topics"):
                item = next(i for i in find_group(teaching, inst["name"])["items"] if i["what"] == col["topics"])
                entries = [(n, item.get("topic_kw", {}).get(n)) for n in item["topics"]]
            else:
                entries = [(i["what"], i.get("kw")) for src in col["from"] for i in find_group(teaching, src)["items"]
                           if not i.get("topics") and col["level"].lower() in str(i.get("detail", "")).lower()]
            lis = "".join(f"<li{kw_attr(k)}>{inline(n, '.')}</li>" for n, k in entries)
            cols.append(f'          <div class="level"><h4>{html.escape(col["title"])}</h4><ul>{lis}</ul></div>')
        out.append('      <div class="teach-inst">\n'
                   f'        <div class="inst"><h3>{html.escape(inst["name"])}</h3><span>{html.escape(inst["role"])}</span></div>\n'
                   '        <div class="levels">\n' + "\n".join(cols) + '\n        </div>\n      </div>\n')
    for item in find_group(teaching, conf["features"])["items"]:
        m = re.match(r"\[([^\]]+)\]\(([^)\s]+)\)(?:,\s*with\s+(.+))?$", item["what"])
        if m:
            title = (f'<a class="feat-link" href="{m.group(2)}" target="_blank" rel="noopener">'
                     f'{inline(m.group(1), ".")} {LINK_ICON}</a>')
            co = m.group(3)
        else:
            title, co = inline(item["what"], "."), None
        meta = [inline(item["detail"], ".")] if item.get("detail") else []
        meta.append(html.escape(" ".join(x for x in (item.get("where"), str(item.get("when", ""))) if x)))
        if co:
            meta.append("with " + inline(co, "."))
        out.append(f'      <div class="feature"{kw_attr(item.get("kw"))}>\n'
                   f'        <span class="ftag">Summer school · {html.escape(item["tag"])}</span>\n'
                   f'        <h3>{title}</h3>\n'
                   f'        <div class="meta">{" · ".join(meta)}</div>\n'
                   f'        <p>{inline(item["blurb"], ".")}</p>\n'
                   '      </div>\n')
    sup = find_group(teaching, conf["supervision"])
    rows = [f'        <div class="row"{kw_attr(t.get("kw"))}><div><span class="who">{html.escape(t["who"])}:</span> '
            f'<span class="ti">{inline(t["title"], ".")}</span></div>'
            f'<span class="deg">{html.escape(t["degree"])} · {html.escape(t["at"])} · {html.escape(str(t["year"]))}</span></div>'
            for t in sup["theses"]]
    out.append('      <div class="sup">\n        <h3>Supervision</h3>\n' + "\n".join(rows) + '\n      </div>\n')
    return "".join(out)


def fill(page_html, name, content):
    """Replace what sits between the <!-- cv:NAME start ... --> and <!-- cv:NAME end --> markers."""
    pat = re.compile(r"(<!-- cv:%s start[^>]*-->\n)(.*?)(<!-- cv:%s end -->)" % (name, name), re.S)
    if not pat.search(page_html):
        sys.exit(f"index.html has no cv:{name} markers; see cv/build.py")
    return pat.sub(lambda m: m.group(1) + content + m.group(3), page_html, count=1)


def update_homepage(cv):
    by_id = {s["id"]: s for s in cv["sections"]}
    page_html = HOME.read_text(encoding="utf-8")
    check_keywords(cv, page_html)
    page_html = fill(page_html, "teaching", home_teaching(cv))
    page_html = fill(page_html, "talks", home_talks(by_id[cv["homepage"]["talks"]]["items"]))
    page_html = fill(page_html, "summary", home_summary(cv))
    HOME.write_text(page_html, encoding="utf-8")


# ---------------------------------------------------------------- pdf

def print_pdf(page_html, cv):
    from playwright.sync_api import sync_playwright
    # Relative links resolve against the live site inside the PDF.
    printable = page_html.replace("<head>", f'<head>\n<base href="{SITE}/cv/">', 1)
    footer = ('<div style="width:100%;padding:0 15mm;display:flex;justify-content:space-between;'
              'font-family:monospace;font-size:7px;letter-spacing:0.05em;text-transform:uppercase;color:#8a8f98">'
              f'<span>{html.escape(plain(cv["name"]))} · Curriculum Vitae · {html.escape(cv["updated"])}</span>'
              '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>')
    with tempfile.TemporaryDirectory() as tmp:
        src = pathlib.Path(tmp) / "cv.html"
        src.write_text(printable, encoding="utf-8")
        with sync_playwright() as p:
            chrome = os.environ.get("CHROME")
            browser = p.chromium.launch(executable_path=chrome) if chrome else p.chromium.launch()
            pg = browser.new_page()
            # The page's links point at the live site; serve its fonts from this repo, so the
            # PDF never depends on what is deployed.
            types = {".css": "text/css", ".woff2": "font/woff2"}

            def local(route):
                path = ROOT / route.request.url[len(SITE) + 1:].split("?")[0]
                if path.is_file():
                    route.fulfill(body=path.read_bytes(), headers={
                        "Content-Type": types.get(path.suffix, "application/octet-stream"),
                        "Access-Control-Allow-Origin": "*"})
                else:
                    route.abort()
            pg.route(SITE + "/fonts/**", local)
            pg.goto(src.as_uri(), wait_until="networkidle")
            pg.evaluate("document.fonts.ready")
            pg.pdf(path=str(OUT_PDF), format="A4", print_background=True,
                   display_header_footer=True, header_template="<span></span>", footer_template=footer,
                   margin={"top": "12mm", "bottom": "15mm", "left": "15mm", "right": "15mm"})
            browser.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--no-pdf", action="store_true", help="write the page only")
    args = ap.parse_args()
    cv = yaml.safe_load(SRC.read_text(encoding="utf-8"))
    count_theses(cv)
    out = page(cv)
    OUT_HTML.write_text(out, encoding="utf-8")
    print(f"wrote {OUT_HTML.relative_to(ROOT)}")
    update_homepage(cv)
    print(f"updated {HOME.relative_to(ROOT)} (Teaching, Talks list, short CV)")
    if not args.no_pdf:
        print_pdf(out, cv)
        print(f"wrote {OUT_PDF.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
