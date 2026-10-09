#!/usr/bin/env python3
# build.py — the W website: the documentation of W plus the pages only the web
# has (landing, download, changelog, contributing, security, 404, llms.txt).
#
# The docs are not here. They live in the W repository (w-linux, public as
# tarkh/w) next to the system they describe, and its generator — w-docs-site —
# renders them for the offline Help window too. This script loads that generator
# as a library and builds on it: Site("web", chrome) renders the docs with this
# site's top navigation and footer, .md() renders W's root documents with the
# same link rules, .page() lays every page out in the same template, .verify()
# fails the build on any relative link or #anchor that does not resolve. The site
# is relative links only — it works under any domain or sub-path, and from disk.
#
# What lives here instead is what every W machine should not have to clone:
# images, fonts, the landing page.
#
#   W_SRC=<w-linux checkout> ./build.py [OUT]     default: ../w-linux, out/
#
# CI builds against tarkh/w@main — the last release, i.e. the docs users have.
import html
import importlib.machinery
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from string import Template

HERE = Path(__file__).resolve().parent
W_SRC = Path(os.environ.get("W_SRC") or HERE.parent / "w-linux").resolve()


def load_generator():
    path = W_SRC / "devtools/usr/local/bin/w-docs-site"
    if not path.is_file():
        sys.exit(f"build.py: no w-docs-site under {W_SRC} — set W_SRC to a w-linux checkout")
    loader = importlib.machinery.SourceFileLoader("w_docs_site", str(path))
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(mod)
    return mod


wds = load_generator()
LANGS, REPO_URL = wds.LANGS, wds.REPO_URL
RAW_URL = REPO_URL.replace("https://github.com/", "https://raw.githubusercontent.com/") + "/main"
GH_REPO = REPO_URL.removeprefix("https://github.com/")
VERSION = wds.OS_RELEASE["IMAGE_VERSION"]
STR = json.loads((HERE / "i18n/web.json").read_text())
OWN = ["index.html", "download.html", "changelog.html", "contributing.html", "security.html"]
HIGHLIGHTS = [  # tile → docs page and, where that language's page has it, a section
    ("reversible", "guide/updates.md", "if-an-update-goes-wrong"),
    ("theme", "guide/theming.md", ""),
    ("desktop", "guide/desktop.md", ""),
    ("security", "guide/security.md", ""),
    ("ai", "guide/ai.md", ""),
    ("packs", "guide/packs.md", ""),
]


def t(key, lang):
    return wds.t(key, lang, STR)


def links(lang):
    """W's root documents that are pages of this site."""
    out = {"README.md": ("index.html", "en"), "CHANGELOG.md": ("changelog.html", lang)}
    for name in ("CONTRIBUTING", "SECURITY"):
        out[f"{name}.md"] = (f"{name.lower()}.html", "en")
        out.update({f"docs/{lg}/{name}.md": (f"{name.lower()}.html", lg) for lg in LANGS[1:]})
    out.update({f"docs/{lg}/README.md": ("index.html", lg) for lg in LANGS[1:]})
    return out


# ── Chrome: what the web adds around every page ───────────────────────────────
def chrome(lang, root, url):
    def a(u, label, cur):
        return f'<a href="{root}/{lang}/{u}"{" aria-current=\"page\"" if cur else ""}>{html.escape(label)}</a>'

    nav = (f'<nav class="primary">{a("docs.html", t("nav.docs", lang), url not in OWN)}'
           f'{a("download.html", t("nav.download", lang), url == "download.html")}'
           f'{a("changelog.html", t("nav.changelog", lang), url == "changelog.html")}'
           f'<a class="ext" href="{REPO_URL}">{t("nav.github", lang)}</a></nav>')
    return {"head": f'\n<link rel="stylesheet" href="{root}/assets/web.css">'
                    f'\n<script src="{root}/assets/web.js" defer></script>',
            "topnav": nav, "foot": footer(lang, root, url)}


def footer(lang, root, url):
    def a(u, label):
        return f'<a href="{root}/{lang}/{u}">{html.escape(label)}</a>'

    switch = "".join(f"<b>{lg}</b>" if lg == lang else
                     f'<a href="{root}/{lg}/{url}" hreflang="{lg}">{lg}</a>' for lg in LANGS)
    return (f'\n<footer class="site"><div class="row">'
            f'<img src="{root}/assets/logo.svg" alt="" width="22" height="22">'
            f'<nav><a class="ext" href="{REPO_URL}">GitHub</a>{a("changelog.html", t("nav.changelog", lang))}'
            f'{a("security.html", t("foot.security", lang))}{a("contributing.html", t("foot.contributing", lang))}</nav>'
            f'<span class="ver">{t("foot.release", lang)} v{VERSION}</span>'
            f'<span class="langs">{switch}</span></div>'
            f'<p>{html.escape(t("foot.license", lang))}</p></footer>')


def webp_size(path):
    """Width and height from a WebP header, so the strip lays out before the images load."""
    b = path.read_bytes()[:30]
    if b[12:16] == b"VP8 ":
        return int.from_bytes(b[26:28], "little") & 0x3FFF, int.from_bytes(b[28:30], "little") & 0x3FFF
    if b[12:16] == b"VP8X":
        return 1 + int.from_bytes(b[24:27], "little"), 1 + int.from_bytes(b[27:30], "little")
    n = int.from_bytes(b[21:25], "little")  # VP8L
    return 1 + (n & 0x3FFF), 1 + (n >> 14 & 0x3FFF)


# ── Pages ─────────────────────────────────────────────────────────────────────
def home(site, lang):
    def anchor(key, sec):
        url = site.pages[(key, lang)].url
        return f"{url}#{sec}" if sec and f' id="{sec}"' in site.files[f"{lang}/{url}"].decode() else url

    tiles = "".join(
        f'<a class="tile" href="{anchor(key, sec)}"><h3>{html.escape(t(f"hl.{k}.title", lang))}</h3>'
        f'<p>{html.escape(t(f"hl.{k}.text", lang))}</p><span class="more">{t("home.more", lang)} →</span></a>'
        for k, key, sec in HIGHLIGHTS)
    steps = "".join(f'<li><h3>{t(f"how.{k}.title", lang)}</h3><p>{t(f"how.{k}.text", lang)}</p>{extra}</li>'
                    for k, extra in (("iso", ""), ("install", ""),
                                     ("update", '<pre><code><span class="w">w-sync</span> update</code></pre>')))
    figs = ""  # shots/NN-key.webp for every language, shots/<lang>/ where the UI in it is localised
    for p in sorted((p for d in ("shots", f"shots/{lang}") for p in (HERE / d).glob("*.webp")), key=lambda p: p.name):
        src, cap, (w, h) = p.relative_to(HERE).as_posix(), html.escape(t(f"shot.{p.stem[3:]}", lang)), webp_size(p)
        figs += (f'<figure><a href="../{src}"><img src="../{src}" width="{w}" height="{h}" alt="{cap}" loading="lazy">'
                 f'</a><figcaption>{cap}</figcaption></figure>')
    def btn(cls, key, path):
        return (f'<button class="{cls}" type="button" aria-label="{t(key, lang)}"><svg viewBox="0 0 24 24" aria-hidden="true">'
                f'<path d="{path}"/></svg></button>')

    box = (f'<dialog class="lightbox"><figure><img alt=""><figcaption></figcaption></figure>'
           + btn("prev", "shots.prev", "M15 5l-7 7 7 7") + btn("next", "shots.next", "M9 5l7 7-7 7")
           + btn("close", "shots.close", "M6 6l12 12M18 6L6 18") + "</dialog>")
    strip = figs and f'<section class="shots"><h2>{t("shots.title", lang)}</h2><div class="grid">{figs}</div>{box}</section>'
    switch = "".join(f"<b>{lg}</b>" if lg == lang else f'<a href="../{lg}/index.html" hreflang="{lg}">{lg}</a>'
                     for lg in LANGS)
    tpl = Template((HERE / "templates/home.html").read_text())
    ch = chrome(lang, "..", "index.html")
    site.files[f"{lang}/index.html"] = tpl.substitute(
        lang=lang, title=html.escape(t("home.title", lang)), h1=html.escape(t("home.h1", lang)),
        lead=html.escape(t("home.lead", lang)), download=t("home.download", lang), docs=t("home.docs", lang),
        banner=html.escape(t("home.banner", lang), quote=True), highlights=t("home.highlights", lang),
        tiles=tiles, how=t("how.title", lang), steps=steps, shots=strip, langs=switch,
        site_name=wds.t("site.name", lang),
        topnav=ch["topnav"], foot=ch["foot"]).encode()


def readme_section(lang, heading):
    src = "README.md" if lang == "en" else f"docs/{lang}/README.md"
    m = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", (W_SRC / src).read_text(), re.MULTILINE | re.DOTALL)
    if not m:
        sys.exit(f"build.py: {src} has no section '## {heading}' (i18n/web.json dl.readme)")
    return src, f"## {heading}\n" + re.sub(r"\n-{3,}\s*\Z", "\n", m.group(1).rstrip() + "\n")


def download(site, lang):
    req, inst, build = t("dl.readme", lang).split("|")
    own = "README.md"   # web.json's links are written from the repository root
    parts = [(own, t("dl.intro.md", lang)), readme_section(lang, req),
             (own, f'## {t("dl.modes.title", lang)}\n\n{t("dl.modes.md", lang)}'),
             readme_section(lang, inst),
             (own, f'## {t("dl.verify.title", lang)}\n\n{t("dl.verify.md", lang)}'),
             readme_section(lang, build)]
    body, toc = "", []
    for src, text in parts:
        b, c = site.md(text, src, lang, "download.html", links(lang))
        body, toc = body + b, toc + c
    page = f"{REPO_URL}/releases/tag/edge"
    rows = "".join(f'<dt>{t(f"dl.{k}", lang)}</dt><dd data-k="{k}"></dd>' for k in ("release", "built", "size"))
    card = (f'<div class="iso" data-repo="{GH_REPO}" data-tag="edge">'
            f'<p class="iso-name" data-k="name">W · {t("dl.loading", lang)}</p><dl>{rows}</dl>'
            f'<code class="iso-sha" data-k="sha"></code>'
            f'<p class="cta"><a class="button primary iso-get" href="{page}">{t("dl.button", lang)}</a>'
            f'<a class="button" href="{page}">{t("dl.page", lang)}</a></p></div>\n')
    site.page(lang, "download.html", t("dl.title", lang), card + body, summary=t("dl.summary", lang), toc=toc)


def root_doc(site, lang, name):
    """CONTRIBUTING / SECURITY: W's root document, its translation in docs/<lang>/."""
    src = name if lang == "en" else f"docs/{lang}/{name}"
    translated = (W_SRC / src).is_file()
    src = src if translated else name
    h1, body = re.match(r"# ([^\n]+)\n+(.*)", (W_SRC / src).read_text(), re.DOTALL).groups()
    body = re.sub(r"\A(\*\*English\*\*|\[English\]).*?\n\n", "", body, flags=re.DOTALL)
    url = name.lower().replace(".md", ".html")
    b, toc = site.md(body, src, lang, url, links(lang))
    site.page(lang, url, h1, b, toc=toc, edit=src, notice=notice(lang, translated))


def changelog(site, lang):
    # Everything above the first release is a note to whoever cuts the release.
    text = (W_SRC / "CHANGELOG.md").read_text()
    b, toc = site.md(text[text.index("\n## ") + 1:], "CHANGELOG.md", lang, "changelog.html", links(lang))
    site.page(lang, "changelog.html", t("nav.changelog", lang), b, toc=toc, notice=notice(lang, lang == "en"))


def notice(lang, translated):
    return "" if translated else f'<p class="notice">{wds.t("ui.untranslated", lang)}</p>\n'


def not_found(site):
    """Pages serves /404.html for a miss at ANY depth, so relative links cannot
    work in it: it carries its style and logo inline and finds the site root at
    run time (a *.github.io project site lives under /<repo>/, a domain at /)."""
    texts = {k: {lg: t(k, lg) for lg in LANGS} for k in ("404.title", "404.text", "404.home")}
    logo = re.sub(r"<\?xml.*?\?>\s*", "", site.files["assets/logo.svg"].decode(), flags=re.DOTALL)
    site.files["404.html"] = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>404 · W Linux</title>
<style>
:root{{color-scheme:dark;--bg:#09000e;--fg:#a197a4;--hi:#e8e2ea;--ac:#a170ab}}
@media (prefers-color-scheme:light){{:root{{color-scheme:light;--bg:#fbf8fc;--fg:#4a3f50;--hi:#1a1220;--ac:#7a3f87}}}}
body{{margin:0;min-height:100vh;display:grid;place-items:center;background:var(--bg);color:var(--fg);
font:16px/1.6 Inter,system-ui,sans-serif;text-align:center}}
svg{{width:72px;height:72px}}h1{{color:var(--hi);font-size:28px;margin:24px 0 8px}}a{{color:var(--ac)}}
</style></head>
<body><main>{logo}
<h1 id="t">{texts["404.title"]["en"]}</h1><p id="x">{texts["404.text"]["en"]}</p>
<p><a id="h" href="index.html">{texts["404.home"]["en"]}</a></p></main>
<script>
var T={json.dumps(texts, ensure_ascii=False)},L={json.dumps(LANGS)},s=null;
try{{s=localStorage.getItem("w-lang")}}catch(e){{}}
var p=location.pathname.split("/"),r=/\\.github\\.io$/.test(location.hostname)&&p[1]?"/"+p[1]+"/":"/";
var n=[s].concat(navigator.languages||[navigator.language]).map(function(x){{return(x||"").slice(0,2)}})
.filter(function(x){{return L.indexOf(x)>=0}})[0]||"en";
document.documentElement.lang=n;
document.getElementById("t").textContent=T["404.title"][n];
document.getElementById("x").textContent=T["404.text"][n];
var h=document.getElementById("h");h.textContent=T["404.home"][n];h.href=r+n+"/index.html";
</script></body></html>
""".encode()


def root_index(site):
    alt = "".join(f'<link rel="alternate" hreflang="{lg}" href="{lg}/index.html">\n' for lg in LANGS)
    site.files["index.html"] = (
        '<!doctype html><html><head><meta charset="utf-8"><title>W Linux</title>\n'
        '<meta http-equiv="refresh" content="1; url=en/index.html">\n' + alt +
        f'<script>var l={json.dumps(LANGS)},s=null;try{{s=localStorage.getItem("w-lang")}}catch(e){{}}'
        'var n=[s].concat(navigator.languages||[navigator.language]).map(function(x){return(x||"").slice(0,2)})'
        '.filter(function(x){return l.indexOf(x)>=0})[0]||"en";location.replace(n+"/index.html")</script>\n'
        '</head><body>' + " · ".join(f'<a href="{lg}/index.html">{lg}</a>' for lg in LANGS) +
        '</body></html>\n').encode()


def llms(site):
    """llmstxt.org: the site's map for language models, pointing at the Markdown
    sources themselves (absolute GitHub URLs — the site's own stay relative)."""
    out = [f"# W Linux\n\n> {t('llms.summary', 'en')}\n"]
    pages = [p for (k, lg), p in site.pages.items() if lg == "en"]
    for cat in wds.CATS:
        items = sorted((p for p in pages if p.cat == cat), key=lambda p: (p.order, p.title))
        if items:
            out.append(f"## {wds.t(f'nav.cat.{cat}', 'en')}\n")
            out += [f"- [{p.title}]({RAW_URL}/{p.src.relative_to(W_SRC).as_posix()})"
                    + (f": {p.summary}" if p.summary else "") for p in items]
            out.append("")
    out.append("## Project\n")
    out += [f"- [{n}]({RAW_URL}/{n})" for n in ("README.md", "CHANGELOG.md", "SECURITY.md", "CONTRIBUTING.md")]
    site.files["llms.txt"] = ("\n".join(out) + "\n").encode()


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else HERE / "out").resolve()
    site = wds.Site("web", chrome)
    for d in ("assets", "fonts", "shots"):
        for f in sorted((HERE / d).rglob("*")):
            if f.is_file() and not f.name.startswith("."):
                site.files[f.relative_to(HERE).as_posix()] = f.read_bytes()
    site.files["assets/banner.webp"] = (W_SRC / "banner.webp").read_bytes()
    for lang in LANGS:
        home(site, lang)
        download(site, lang)
        changelog(site, lang)
        for name in ("CONTRIBUTING.md", "SECURITY.md"):
            root_doc(site, lang, name)
    root_index(site)
    not_found(site)
    llms(site)
    if bad := site.verify():
        print("\n".join(f"  {b}" for b in bad), file=sys.stderr)
        sys.exit("build.py: dangling links — nothing written")
    wds.write(site.files, out)
    print(f"build.py: {sum(f.endswith('.html') for f in site.files)} pages from {W_SRC} → {out}")


if __name__ == "__main__":
    main()
