#!/usr/bin/env python3
"""Build the pit-wall cards for the INFINITQ profile README.

    python scripts/build_cards.py            # live cards from GitHub data -> dist/
    python scripts/build_cards.py assets     # static art -> assets/ (no network)
    python scripts/build_cards.py all        # both

GitHub data comes from the GraphQL API. With GITHUB_TOKEN set (as in the
Action) the script calls the API itself; without it, it goes through the gh
CLI, so a local run reuses your gh login and this script never sees a token.
Only public repositories count, and every contribution number comes from the
public contribution calendar, so local and CI runs draw the same cards.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pitwall_svg as svg  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
API = "https://api.github.com/graphql"
CALENDAR = "contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }"
# GitHub shows README images in a sandbox: none of these would work there.
FORBIDDEN = ("<script", "<image", "<foreignobject", "@import", "url(http", 'href="http', "javascript:")
MAX_BYTES = 100_000


# ------------------------------------------------------------------ GitHub

def graphql(query: str) -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        payload = _post(query, token)
    else:
        gh = shutil.which("gh") or _windows_gh()
        if not gh:
            raise SystemExit("No GitHub access: set GITHUB_TOKEN, or install and log in to the gh CLI.")
        run = subprocess.run([gh, "api", "graphql", "-f", f"query={query}"],
                             capture_output=True, text=True, encoding="utf-8")
        if run.returncode != 0:
            raise SystemExit(f"gh api graphql failed: {run.stderr.strip() or run.stdout.strip()}")
        payload = json.loads(run.stdout)
    if payload.get("errors"):
        raise SystemExit(f"GitHub GraphQL errors: {payload['errors']}")
    return payload["data"]


def _post(query: str, token: str, attempts: int = 3) -> dict:
    body = json.dumps({"query": query}).encode()
    for attempt in range(attempts):
        req = urllib.request.Request(API, data=body, headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "infinitq-pit-wall",
        })
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as err:
            if err.code < 500 or attempt == attempts - 1:
                raise
        except urllib.error.URLError:
            if attempt == attempts - 1:
                raise
        time.sleep(2 * (attempt + 1))
    raise RuntimeError("unreachable")


def _windows_gh() -> str | None:
    path = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "GitHub CLI" / "gh.exe"
    return str(path) if path.exists() else None


def parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch(login: str, now: datetime) -> dict:
    """Everything the cards need, in two GraphQL requests."""
    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}", login):
        raise SystemExit(f"Not a GitHub login: {login!r}")
    created = parse_dt(graphql(f'{{ user(login: "{login}") {{ createdAt }} }}')["user"]["createdAt"])
    years = []
    for y in range(created.year, now.year + 1):
        start = max(datetime(y, 1, 1, tzinfo=timezone.utc), created)
        end = min(datetime(y, 12, 31, 23, 59, 59, tzinfo=timezone.utc), now)
        years.append(f'y{y}: contributionsCollection(from: "{iso(start)}", to: "{iso(end)}") {{ {CALENDAR} }}')
    since = iso(now - timedelta(days=30))
    query = f"""{{
      user(login: "{login}") {{
        login createdAt
        repositories(first: 100, privacy: PUBLIC, ownerAffiliations: OWNER, isFork: false,
                     orderBy: {{field: PUSHED_AT, direction: DESC}}) {{
          totalCount
          nodes {{
            name stargazerCount pushedAt
            primaryLanguage {{ name color }}
            latestRelease {{ tagName }}
            defaultBranchRef {{ target {{ ... on Commit {{ history(since: "{since}") {{ totalCount }} }} }} }}
            languages(first: 12, orderBy: {{field: SIZE, direction: DESC}}) {{
              edges {{ size node {{ name color }} }}
            }}
          }}
        }}
        last: contributionsCollection {{ {CALENDAR} }}
        {" ".join(years)}
      }}
    }}"""
    data = graphql(query)
    data["fetchedAt"] = iso(now)
    return data


# ------------------------------------------------------------------ stats

def daily_counts(collections) -> dict[date, int]:
    days: dict[date, int] = {}
    for col in collections:
        for week in col["contributionCalendar"]["weeks"]:
            for d in week["contributionDays"]:
                day = date.fromisoformat(d["date"])
                days[day] = max(days.get(day, 0), d["contributionCount"])
    return days


def streaks(days: dict[date, int], today: date) -> tuple[int, int]:
    """(current, longest) runs of days with contributions.

    A quiet `today` doesn't break the current streak: the day isn't over yet.
    """
    longest = run = 0
    prev = None
    for d in sorted(d for d, c in days.items() if c > 0):
        run = run + 1 if prev is not None and (d - prev).days == 1 else 1
        longest = max(longest, run)
        prev = d
    day = today if days.get(today, 0) > 0 else today - timedelta(days=1)
    current = 0
    while days.get(day, 0) > 0:
        current += 1
        day -= timedelta(days=1)
    return current, longest


def weekly_series(collection, weeks: int = 52) -> list[tuple[date, int]]:
    out = []
    for week in collection["contributionCalendar"]["weeks"]:
        days = week["contributionDays"]
        if days:
            out.append((date.fromisoformat(days[0]["date"]), sum(d["contributionCount"] for d in days)))
    return out[-weeks:]


def weekday_totals(days: dict[date, int]) -> list[int]:
    """Contributions per weekday, Monday first."""
    totals = [0] * 7
    for d, c in days.items():
        totals[d.weekday()] += c
    return totals


def language_ranking(repos, exclude=()) -> tuple[list[dict], int]:
    """Languages ranked by sqrt(bytes x repos using it), as percentages.

    Raw byte counts would bury a language used across many small repos under
    one big app; the blend credits both. Shares over the full list sum to 100.
    """
    size, count, color = Counter(), Counter(), {}
    for repo in repos:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            if name in exclude:
                continue
            size[name] += edge["size"]
            count[name] += 1
            color[name] = edge["node"]["color"] or svg.GREY
    score = {n: math.sqrt(size[n] * count[n]) for n in size}
    total = sum(score.values()) or 1.0
    ranked = sorted(score, key=lambda n: (-score[n], n))
    return [{"name": n, "color": color[n], "share": 100 * score[n] / total} for n in ranked], len(ranked)


def repo_facts(node: dict) -> dict:
    target = (node.get("defaultBranchRef") or {}).get("target") or {}
    lang = node.get("primaryLanguage") or {}
    return {
        "stars": node.get("stargazerCount", 0),
        "pushed": parse_dt(node["pushedAt"]).date() if node.get("pushedAt") else None,
        "language": lang.get("name"),
        "language_color": lang.get("color"),
        "release": (node.get("latestRelease") or {}).get("tagName"),
        "commits_30d": (target.get("history") or {}).get("totalCount"),
    }


def summarize(data: dict, cfg: dict, today: date) -> dict:
    user = data["user"]
    created = parse_dt(user["createdAt"])
    years = [user[k] for k in sorted(user) if re.fullmatch(r"y\d{4}", k)]
    last = daily_counts([user["last"]])
    every = daily_counts(years + [user["last"]])
    current, longest = streaks(every, max(last) if last else today)
    repos = user["repositories"]["nodes"]
    languages, language_count = language_ranking(repos, cfg.get("language_exclude", ()))
    return {
        "since": created.year,
        "seasons": today.year - created.year + 1,
        "contrib_12mo": sum(last.values()),
        "contrib_all": sum(every.values()),
        "active_days": sum(1 for c in last.values() if c > 0),
        "repos": user["repositories"]["totalCount"],
        "current": current,
        "longest": longest,
        "best_day": max(every.values(), default=0),
        "weeks": weekly_series(user["last"]),
        "weekdays": weekday_totals(last),
        "languages": languages,
        "language_count": language_count,
        "repo_facts": {node["name"]: repo_facts(node) for node in repos},
        "updated": today,
    }


# ------------------------------------------------------------------ output

def check_config(cfg: dict) -> None:
    for msg in cfg["radio"]:
        if len(msg) > svg.RADIO_MAX_CHARS:
            raise SystemExit(f"Team radio message is {len(msg)} characters; the strip fits "
                             f"{svg.RADIO_MAX_CHARS}: {msg!r}")
    for p in cfg["projects"]:
        if len(p["sectors"]) != 3:
            raise SystemExit(f"Project {p['id']!r} needs exactly 3 sectors")


def static_assets(cfg: dict) -> dict[str, str]:
    return {
        "header.svg": svg.header(cfg),
        "ml-season.svg": svg.ml_season(cfg),
        "finish.svg": svg.finish(cfg),
    }


def live_cards(cfg: dict, stats: dict) -> dict[str, str]:
    cards = {
        "driver-card.svg": svg.driver_card(cfg, stats),
        "telemetry.svg": svg.telemetry(stats),
        "pit-wall.svg": svg.pit_wall(stats),
    }
    for p in cfg["projects"]:
        cards[f"project-{p['id']}.svg"] = svg.project_card(
            p, stats["repo_facts"].get(p["repo"]), stats["updated"], cfg["login"])
    return cards


def validate(name: str, doc: str) -> None:
    ET.fromstring(doc)
    if len(doc.encode("utf-8")) > MAX_BYTES:
        raise ValueError(f"{name} is over {MAX_BYTES // 1000} KB")
    lowered = doc.lower()
    for bad in FORBIDDEN:
        if bad in lowered:
            raise ValueError(f"{name} contains {bad!r}, which GitHub would block")
    urls = set(re.findall(r"https?://[^\s\"'<>)]+", doc)) - {"http://www.w3.org/2000/svg"}
    if urls:
        raise ValueError(f"{name} links to {sorted(urls)}; README images must be self-contained")


def write_all(out_dir: Path, files: dict[str, str]) -> None:
    """Check every file first, then write them all, so a bad run writes nothing."""
    for name, doc in files.items():
        validate(name, doc)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, doc in files.items():
        tmp = out_dir / f".{name}.tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(doc)
        os.replace(tmp, out_dir / name)
    print(f"wrote {len(files)} files to {out_dir}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Build the pit-wall cards for the INFINITQ profile README.")
    ap.add_argument("what", nargs="?", choices=("live", "assets", "all"), default="live",
                    help="live cards (needs GitHub data), static art, or both (default: live)")
    ap.add_argument("--config", default=str(ROOT / "profile.config.json"))
    ap.add_argument("--out", default=str(ROOT / "dist"), help="folder for the live cards")
    ap.add_argument("--assets-dir", default=str(ROOT / "assets"), help="folder for the static art")
    ap.add_argument("--data", help="read saved GitHub data from this JSON file instead of the API")
    ap.add_argument("--save-data", help="also save the fetched GitHub data to this JSON file")
    ap.add_argument("--today", help="treat this date (YYYY-MM-DD) as today, for repeatable output")
    args = ap.parse_args(argv)

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    check_config(cfg)
    if args.what in ("assets", "all"):
        write_all(Path(args.assets_dir), static_assets(cfg))
    if args.what in ("live", "all"):
        now = datetime.now(timezone.utc)
        today = date.fromisoformat(args.today) if args.today else now.date()
        if args.data:
            data = json.loads(Path(args.data).read_text(encoding="utf-8"))
        else:
            data = fetch(cfg["login"], now)
            if args.save_data:
                Path(args.save_data).parent.mkdir(parents=True, exist_ok=True)
                Path(args.save_data).write_text(json.dumps(data, indent=1), encoding="utf-8")
        write_all(Path(args.out), live_cards(cfg, summarize(data, cfg, today)))


if __name__ == "__main__":
    main()
