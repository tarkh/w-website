# W website

The website of [W Linux](https://github.com/tarkh/w): a landing page, the
download page, the changelog, and the W documentation, published with GitHub
Pages.

The documentation itself is not in this repository. It lives in the W
repository next to the system it describes, and W's own generator
(`devtools/usr/local/bin/w-docs-site`) renders it — for this site and for the
offline copy every W machine carries. `build.py` loads that generator as a
library and adds what only the web has. Fonts, images and the landing page live
here so that they never enter the history every W installation clones.

## Building

```sh
git clone https://github.com/tarkh/w w-linux        # next to this repository
./build.py                                          # → out/
python3 -m http.server -d out                       # preview at http://localhost:8000
```

`W_SRC=<path>` points the build at another W checkout. It needs Python 3.12+ and
`markdown-it-py`. The build fails on any relative link or `#anchor` that does not
resolve, and the site uses relative links only — it works under any domain or
sub-path, and from disk.

## Layout

| | |
|---|---|
| `build.py` | the build: landing, download, changelog, contributing, security, 404, `llms.txt` |
| `templates/home.html` | the landing page |
| `i18n/web.json` | every string of the pages above, per language |
| `assets/web.css`, `assets/web.js` | light scheme, fonts, landing and download styles; language memory and the download card |
| `fonts/` | Inter and JetBrains Mono, subset to Latin and Cyrillic |
| `shots/` | screenshots for the landing page's strip (shown once there are any) |

The download card asks the GitHub API for the current `edge` image in the
reader's browser: the image is rebuilt every night under a dated name, and the
site is not.

## Publishing

`.github/workflows/site.yml` builds against `tarkh/w@main` — the last W release —
and deploys to Pages on a push to `main` here, and on `workflow_dispatch`, which
W's release script starts after every release.

## License

The code and text are GPL-3.0-or-later (`LICENSE`), like W. The fonts are under
the SIL Open Font License 1.1: Inter by Rasmus Andersson
(`fonts/OFL-Inter.txt`), JetBrains Mono by JetBrains
(`fonts/OFL-JetBrainsMono.txt`); the files here are subsets of the upstream
releases (Inter 4.1, JetBrains Mono 2.304).
