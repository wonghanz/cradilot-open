"""Pre-publicity gates for the sanitized snapshot.

Not a substitute for the test suite: these are the things that only matter once —
a name that should not appear, an address that belongs to one machine, a runtime
file full of customer data that must never reach a remote.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FORBIDDEN: list[tuple[str, re.Pattern[str], tuple[str, ...]]] = [
    # the identity this was built under. README.md is exempt: naming the contest that
    # funded the original build is the point, and it is one deliberate sentence.
    ("previous vendor", re.compile(r"exabytes|iot services|cradle data/cip", re.I),
     ("README.md",)),
    # one machine's address, useless to everyone else. The SSRF tests cite private
    # ranges on purpose — those are the values the blocklist must reject.
    ("lab server IP", re.compile(r"192\.168\.\d+\.\d+"), ("web_scraper.py",
     "test_web_scraper.py")),
    ("loopback in docs", re.compile(r"localhost|127\.0\.0\.1"),
     ("test_web_scraper.py", "test_pain_roadmap_evidence_bound.py")),
    # personal or account identifiers. README.md and LICENSE are exempt: a CI badge and
    # a copyright line have to name the owner, and that is attribution, not exposure.
    ("personal handle", re.compile(r"wonghanz|@qq\.com|Hanz", re.I),
     ("test_ui_integrity.py", "LICENSE", "README.md")),
    # runtime state: sales_leads.jsonl holds customer contact details
    ("committed runtime file", re.compile(r"^data/(cradilot_wiki\.db|sales_leads\.jsonl)$"), ()),
]

# These files quote the patterns they are enforcing, so they must not match themselves.
SELF_REFERENTIAL = {"check_release_gates.py", "check_no_secrets.py", "ci.yml",
                    "dev_audit.py"}

TEXT_SUFFIXES = {".py", ".md", ".json", ".html", ".js", ".css", ".txt", ".yaml",
                 ".yml", ".toml", ".typ", ".env", "", ".example", ".ini", ".cfg"}


def tracked_or_untracked_files() -> list[Path]:
    out = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        parts = set(path.relative_to(ROOT).parts)
        if {".git", "__pycache__", ".pytest_cache", "node_modules", ".venv"} & parts:
            continue
        out.append(path)
    return out


def check() -> int:
    failures = []
    for path in tracked_or_untracked_files():
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        base = rel.split("/")[-1]
        if base in SELF_REFERENTIAL:
            continue
        if path.suffix not in TEXT_SUFFIXES and ".env.example" not in rel:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for label, pattern, exempt in FORBIDDEN:
            if rel.split("/")[-1] in exempt or rel in exempt:
                continue
            if label == "committed runtime file":
                if pattern.match(rel):
                    failures.append(f"{label}: {rel}")
                continue
            for n, line in enumerate(lines, 1):
                if pattern.search(line):
                    failures.append(f"{label}: {rel}:{n}: {line.strip()[:70]}")
                    break

    # gitignore must actually cover the runtime state, or the next demo leaks customers
    ignored = subprocess.run(["git", "check-ignore", "-q", "data/sales_leads.jsonl"],
                             cwd=ROOT, capture_output=True).returncode == 0
    if not ignored:
        failures.append("gitignore gap: data/sales_leads.jsonl is not ignored")

    if failures:
        print(f"FAIL ({len(failures)}):")
        for f in failures[:25]:
            print("  " + f)
        return 1
    print("PASS: no vendor identity, no machine-specific address, no personal handle, "
          "no runtime customer data.")
    return 0


if __name__ == "__main__":
    sys.exit(check())
