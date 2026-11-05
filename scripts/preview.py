#!/usr/bin/env python3
"""Preview README.md the way GitHub renders it, before you push.

    python scripts/build_cards.py all
    python scripts/preview.py
    python -m http.server 8765        # then open http://localhost:8765/.preview/

README.md goes through GitHub's own Markdown API (via the gh CLI), so the
preview gets the same HTML clean-up as your profile page. Images from the
`output` branch point at the local dist/ folder instead, and the profile-view
counter is swapped for a static badge so previews don't count as visits.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_cards import ROOT, _windows_gh  # noqa: E402

REPO = "INFINITQ/INFINITQ"
CSS = "https://cdn.jsdelivr.net/npm/github-markdown-css@5/github-markdown.min.css"
PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Profile preview</title>
<base href="/">
<link rel="stylesheet" href="{css}">
<style>
  body {{ margin: 0; background: #ffffff; }}
  @media (prefers-color-scheme: dark) {{ body {{ background: #0d1117; }} }}
  /* github.com shows a profile README 831 px wide at desktop sizes */
  .markdown-body {{ box-sizing: border-box; max-width: 879px; margin: 0 auto; padding: 32px 24px; }}
</style></head>
<body><article class="markdown-body">
{body}
</article>
<script>
// github.com swaps <picture> images to match the theme with its own script (the
// <img> sits inside a link, so the browser can't); this stands in for it.
const dark = matchMedia('(prefers-color-scheme: dark)');
function theme() {{
  for (const pic of document.querySelectorAll('picture')) {{
    const img = pic.querySelector('img'), src = pic.querySelector('source[media*=dark]');
    if (!img) continue;
    img.dataset.light ??= img.getAttribute('src');
    img.src = dark.matches && src ? src.getAttribute('srcset') : img.dataset.light;
  }}
}}
theme(); dark.addEventListener('change', theme);
</script></body></html>
"""
VIEWS_STUB = "https://img.shields.io/badge/profile_views-preview-59636e?style=flat-square"


def render(markdown: str) -> str:
    gh = shutil.which("gh") or _windows_gh()
    if not gh:
        raise SystemExit("preview.py needs the gh CLI: it calls GitHub's Markdown API.")
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
        # "markdown" is how GitHub renders README files; "gfm" is comment-style, where
        # every newline becomes a line break.
        json.dump({"text": markdown, "mode": "markdown"}, fh)
        body = Path(fh.name)
    try:
        run = subprocess.run([gh, "api", "markdown", "--input", str(body)],
                             capture_output=True, text=True, encoding="utf-8")
    finally:
        body.unlink(missing_ok=True)
    if run.returncode != 0:
        raise SystemExit(f"GitHub's Markdown API failed: {run.stderr.strip()}")
    return run.stdout


def _uncamo(tag: str) -> str:
    """GitHub proxies outside images through camo; point back at the original."""
    original = re.search(r'data-canonical-src="([^"]+)"', tag)
    if not original:
        return tag
    return re.sub(r'(?<![-\w])src="[^"]*"', lambda _: f'src="{original.group(1)}"', tag, count=1)


def localize(html: str) -> str:
    html = re.sub(r"<img\b[^>]*>", lambda m: _uncamo(m.group(0)), html)
    html = html.replace(f"https://raw.githubusercontent.com/{REPO}/output/", "/dist/")
    # files in this repo, resolved against GitHub's copy: use the local ones
    html = re.sub(rf"https://(?:github\.com/{REPO}/(?:raw|blob)|raw\.githubusercontent\.com/{REPO})/[^/\"']+/",
                  "/", html)
    return re.sub(r'src="https://komarev\.com/ghpvc/[^"]*"', f'src="{VIEWS_STUB}"', html)


def main() -> None:
    html = localize(render((ROOT / "README.md").read_text(encoding="utf-8")))
    out = ROOT / ".preview"
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(PAGE.format(css=CSS, body=html), encoding="utf-8")
    print(f"wrote {out / 'index.html'}; serve the repo folder and open /.preview/")


if __name__ == "__main__":
    main()
