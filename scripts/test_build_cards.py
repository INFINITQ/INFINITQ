"""Tests for the pit-wall card generator.

    python -m unittest discover -s scripts -p "test_*.py" -v

They run on synthetic data shaped like GitHub's GraphQL responses, so they
need no network and no token.
"""

from __future__ import annotations

import copy
import json
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_cards as bc  # noqa: E402
import pitwall_svg as svg  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "profile.config.json").read_text(encoding="utf-8"))
TODAY = date(2026, 11, 5)
SVG_NS = "{http://www.w3.org/2000/svg}"


def calendar(start: date, end: date, count) -> dict:
    """A contributionsCollection shaped like GitHub's, with Sunday-first weeks."""
    weeks, day = [], start - timedelta(days=(start.weekday() + 1) % 7)
    while day <= end:
        days = [{"date": d.isoformat(), "contributionCount": count(d)}
                for d in (day + timedelta(days=k) for k in range(7)) if start <= d <= end]
        if days:
            weeks.append({"contributionDays": days})
        day += timedelta(days=7)
    total = sum(d["contributionCount"] for w in weeks for d in w["contributionDays"])
    return {"contributionCalendar": {"totalContributions": total, "weeks": weeks}}


def pattern(d: date) -> int:
    """0-4 contributions a day; exactly one quiet day in every five."""
    return (d.toordinal() * 7) % 5


def repo(name, pushed, language, color, edges, release=None, commits=None):
    return {
        "name": name, "stargazerCount": 1, "pushedAt": pushed,
        "primaryLanguage": {"name": language, "color": color},
        "latestRelease": {"tagName": release} if release else None,
        "defaultBranchRef": {"target": {"history": {"totalCount": commits}}} if commits is not None else None,
        "languages": {"edges": [{"size": size, "node": {"name": n, "color": c}} for n, c, size in edges]},
    }


def fake_data() -> dict:
    nodes = [
        repo("Lathe", "2026-11-04T10:00:00Z", "TypeScript", "#3178c6",
             [("TypeScript", "#3178c6", 9000), ("Rust", "#dea584", 4000)], release="v0.1.0", commits=7),
        repo("web-browser", "2026-03-08T10:00:00Z", "Python", "#3572A5",
             [("Python", "#3572A5", 3000)], commits=0),
        repo("tool", "2025-01-01T10:00:00Z", "PowerShell", "#012456",
             [("PowerShell", "#012456", 100), ("NSIS", None, 50), ("Python", "#3572A5", 900)]),
    ]
    return {"user": {
        "login": "INFINITQ",
        "createdAt": "2024-03-10T08:00:00Z",
        "repositories": {"totalCount": len(nodes), "nodes": nodes},
        "last": calendar(TODAY - timedelta(days=365), TODAY, pattern),
        "y2024": calendar(date(2024, 3, 10), date(2024, 12, 31), pattern),
        "y2025": calendar(date(2025, 1, 1), date(2025, 12, 31), pattern),
        "y2026": calendar(date(2026, 1, 1), TODAY, pattern),
    }}


class StatsTests(unittest.TestCase):
    def test_quiet_today_keeps_the_current_streak(self):
        days = {TODAY - timedelta(days=k): 1 for k in range(1, 5)}
        days[TODAY] = 0
        self.assertEqual(bc.streaks(days, TODAY), (4, 4))

    def test_streak_spans_new_year_and_breaks_on_a_gap(self):
        days = {date(2025, 12, 29) + timedelta(days=k): 1 for k in range(6)}  # 29 Dec - 3 Jan
        days[date(2026, 1, 4)] = 0
        days[date(2026, 1, 5)] = 2
        self.assertEqual(bc.streaks(days, date(2026, 1, 5)), (1, 6))

    def test_overlapping_calendars_are_not_double_counted(self):
        a = calendar(date(2026, 1, 1), date(2026, 1, 10), lambda d: 1)
        b = calendar(date(2026, 1, 5), date(2026, 1, 15), lambda d: 1)
        self.assertEqual(sum(bc.daily_counts([a, b]).values()), 15)

    def test_weekly_series_keeps_the_last_52_sunday_weeks(self):
        series = bc.weekly_series(calendar(TODAY - timedelta(days=500), TODAY, lambda d: 1))
        self.assertEqual(len(series), 52)
        self.assertTrue(all(total <= 7 for _, total in series))
        self.assertEqual(series[-1][0].weekday(), 6)  # Sunday

    def test_weekday_totals_start_on_monday(self):
        monday = date(2026, 11, 2)
        self.assertEqual(bc.weekday_totals({monday: 3, monday + timedelta(days=6): 1}), [3, 0, 0, 0, 0, 0, 1])

    def test_language_blend_credits_repo_count(self):
        langs, count = bc.language_ranking(fake_data()["user"]["repositories"]["nodes"])
        self.assertEqual(count, 5)
        self.assertAlmostEqual(sum(r["share"] for r in langs), 100.0, places=6)
        # TypeScript has the most bytes; Python is in two repos, so it passes Rust
        self.assertEqual([r["name"] for r in langs[:3]], ["TypeScript", "Python", "Rust"])

    def test_language_exclude(self):
        langs, _ = bc.language_ranking(fake_data()["user"]["repositories"]["nodes"], exclude=("TypeScript",))
        self.assertNotIn("TypeScript", [r["name"] for r in langs])

    def test_summary(self):
        st = bc.summarize(fake_data(), CONFIG, TODAY)
        self.assertEqual((st["since"], st["seasons"], st["repos"]), (2024, 3, 3))
        self.assertGreater(st["contrib_all"], st["contrib_12mo"])
        self.assertEqual(st["longest"], 4)
        self.assertEqual(st["best_day"], 4)
        self.assertEqual(len(st["weeks"]), 52)
        self.assertEqual(st["repo_facts"]["Lathe"]["release"], "v0.1.0")
        self.assertEqual(st["repo_facts"]["Lathe"]["pushed"], date(2026, 11, 4))
        self.assertIsNone(st["repo_facts"]["tool"]["commits_30d"])


class SvgTests(unittest.TestCase):
    @staticmethod
    def cards() -> dict[str, str]:
        st = bc.summarize(fake_data(), CONFIG, TODAY)
        return {**bc.static_assets(CONFIG), **bc.live_cards(CONFIG, st)}

    def test_every_card_is_valid_and_self_contained(self):
        cards = self.cards()
        self.assertEqual(len(cards), 3 + 3 + len(CONFIG["projects"]))
        for name, doc in cards.items():
            with self.subTest(name=name):
                bc.validate(name, doc)  # well-formed, small, nothing GitHub would block
                title = ET.fromstring(doc).find(f"{SVG_NS}title")
                self.assertTrue(title is not None and title.text.strip())

    def test_validate_rejects_external_resources(self):
        bad = '<svg xmlns="http://www.w3.org/2000/svg"><image href="https://example.com/x.png"/></svg>'
        with self.assertRaises(ValueError):
            bc.validate("bad.svg", bad)

    def test_text_is_escaped(self):
        self.assertEqual(svg.esc('<a & "b">'), "&lt;a &amp; &quot;b&quot;&gt;")
        ET.fromstring(svg.doc(10, 10, svg.text(0, 0, "R&D <3", 10), title="x & y"))

    def test_fit_shortens_with_an_ellipsis(self):
        s = svg.fit("a fairly long project summary line", 80, 14)
        self.assertTrue(s.endswith("…"))
        self.assertLessEqual(svg.text_width(s, 14), 80)

    def test_discrete_wraps_and_starts_at_zero(self):
        kt, vals = svg.discrete([(-1, 5), (2, 0)], 10)
        self.assertEqual(kt, "0.00000;0.20000;0.90000")
        self.assertEqual(vals, "5;0;5")  # at t=0 the wrapped event from t=9 still holds

    def test_monotone_path_never_overshoots(self):
        path = svg.monotone_path([(0, 100), (10, 0), (20, 100), (30, 100), (40, 50)])
        ys = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", path)][1::2]
        self.assertTrue(all(-0.01 <= y <= 100.01 for y in ys))

    def test_readable_lightens_only_dark_colours(self):
        self.assertEqual(svg.readable("#3178C6"), "#3178C6")
        self.assertNotEqual(svg.readable("#012456"), "#012456")
        self.assertEqual(svg.readable(None), svg.GREY)

    def test_ago(self):
        self.assertEqual(svg.ago(TODAY, TODAY), "today")
        self.assertEqual(svg.ago(TODAY - timedelta(days=1), TODAY), "yesterday")
        self.assertEqual(svg.ago(TODAY - timedelta(days=5), TODAY), "5 days ago")
        self.assertEqual(svg.ago(TODAY - timedelta(days=150), TODAY), "5 months ago")
        self.assertEqual(svg.ago(None, TODAY), "a while ago")


class ConfigTests(unittest.TestCase):
    def test_radio_messages_fit_the_strip(self):
        for msg in CONFIG["radio"]:
            self.assertLessEqual(len(msg), svg.RADIO_MAX_CHARS, msg)

    def test_check_config_rejects_a_long_radio_message(self):
        cfg = copy.deepcopy(CONFIG)
        cfg["radio"] = ["x" * (svg.RADIO_MAX_CHARS + 1)]
        with self.assertRaises(SystemExit):
            bc.check_config(cfg)

    def test_committed_art_matches_the_config(self):
        for name, doc in bc.static_assets(CONFIG).items():
            path = ROOT / "assets" / name
            with self.subTest(name=name):
                self.assertTrue(path.exists(), f"missing {path}: run python scripts/build_cards.py assets")
                self.assertEqual(path.read_text(encoding="utf-8"), doc,
                                 f"assets/{name} is out of date: run python scripts/build_cards.py assets")


if __name__ == "__main__":
    unittest.main()
