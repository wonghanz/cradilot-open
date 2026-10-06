"""Fail if a credential-shaped string is committed.

Two modes:
  python scripts/check_no_secrets.py            scan the working tree
  python scripts/check_no_secrets.py --history  scan every blob in git history too

The point is not to outsmart a determined leaker; it is to make the ordinary mistake
— a real key pasted into a docstring, a .env added "just for a minute" — fail CI
instead of reaching the public remote.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Google API key", re.compile(r"AIza[0-9A-Za-z_-]{20,}")),
    ("OpenAI-style key", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b")),
    ("Anthropic key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{16,}\b")),
    ("GitHub token", re.compile(r"\b(ghp|gho|ghs|github_pat_)[A-Za-z0-9_]{20,}\b")),
    ("GitLab token", re.compile(r"\bglpat-[A-Za-z0-9_-]{16,}\b")),
    ("AWS access key", re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("Private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("SendGrid key", re.compile(r"\bSG\.[A-Za-z0-9_-]{16,}")),
    ("npm token", re.compile(r"\bnpm_[A-Za-z0-9]{30,}\b")),
    ("Hugging Face token", re.compile(r"\bhf_[A-Za-z0-9]{30,}\b")),
    ("URL with embedded credentials",
     re.compile(r"(mongodb|mysql|postgres(ql)?|redis|amqp|mqtt|rediss)(\+[a-z]+)?://"
                r"[^/'\"@\s]+:[^/'\"@\s]+@")),
    ("Assigned secret",
     re.compile(r"(api[_-]?key|apikey|secret[_-]?key|access[_-]?token|client[_-]?secret"
                r"|password|passwd|pwd)\s*[:=]\s*['\"]?[A-Za-z0-9+/_=.@-]{12,}", re.I)),
]

# Placeholders that must not trip the "Assigned secret" rule, and the files that are
# allowed to discuss credentials at all.
ALLOW_VALUES = {"", "your-key-here", "your_api_key_here", "changeme", "example",
                "read-from-env", "none", "null", "secret", "placeholder",
                "xxxxxxxx", "aaaaaaaa"}  # nosec
# A right-hand side that is code rather than a literal is a read, not a leak.
CODE_VALUE_PREFIXES = ("self.", "os.", "config.", "request.", "cls.", "_env", "get(",
                       "environ", "kwargs", "args", "row", "data", "payload")
SKIP_SUFFIXES = {".pyc", ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff",
                 ".woff2", ".ttf", ".db", ".sqlite3", ".zip", ".gz", ".mp4"}
SKIP_NAMES = {".env.example", "check_no_secrets.py"}
# Line-level opt-out, same spelling detect-secrets uses, so the exemption is visible
# in review rather than buried in this file.
OPT_OUT = ("# nosec", "# pragma: allowlist secret")


def _candidate_lines(name: str, text: str) -> list[str]:
    findings = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if any(marker in line for marker in OPT_OUT):
            continue
        for label, pattern in PATTERNS:
            match = pattern.search(line)
            if not match:
                continue
            if label == "Assigned secret":
                value = line.split(":", 1)[-1] if ":" in line else line.split("=", 1)[-1]
                value = value.strip().strip("'\"").lower()
                if value in ALLOW_VALUES or "${" in value or "{{" in value:
                    continue
                if not value.startswith(("'", '"')) and any(
                        value.lstrip().startswith(p) for p in CODE_VALUE_PREFIXES):
                    continue
                if "(" in line.split("=", 1)[-1] and "'" not in line.split("=", 1)[-1]:
                    continue
                if name in SKIP_NAMES:
                    continue
            findings.append(f"{name}:{lineno} [{label}] {line.strip()[:100]}")
            break
    return findings


def scan_worktree() -> list[str]:
    findings: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        parts = set(path.parts)
        if {".git", "__pycache__", ".pytest_cache", "node_modules", ".venv"} & parts:
            continue
        if path.suffix in SKIP_SUFFIXES or path.name in SKIP_NAMES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        findings += _candidate_lines(path.name, text)
    return findings


def scan_history() -> list[str]:
    """Every blob in the object database, including ones no commit points at."""
    listing = subprocess.run(["git", "cat-file", "--batch-all-objects", "--batch-check"],
                             cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if listing.returncode != 0:
        return [f"history scan failed: {listing.stderr.strip()[:200]}"]
    oids = [parts[0] for line in listing.stdout.splitlines()
            if len(parts := line.split()) == 3 and parts[1] == "blob"]
    if not oids:
        return []

    batch = subprocess.run(["git", "cat-file", "--batch"],
                           input="\n".join(oids).encode("utf-8"),
                           cwd=ROOT, capture_output=True)
    text = batch.stdout.decode("utf-8", "replace")
    findings: list[str] = []
    # --batch prefixes each object with "<oid> blob <size>"; split on those headers
    for oid, chunk in zip(oids, re.split(r"^[0-9a-f]{40} blob \d+\n", text, flags=re.M)):
        if not chunk.strip():
            continue
        findings += [f"history {oid[:8]} {f}" for f in _candidate_lines(oid[:8], chunk)]
    return findings


def main(argv: list[str]) -> int:
    findings = scan_worktree()
    scope = "working tree"
    if "--history" in argv:
        scope += " + git history"
        findings += scan_history()
    if findings:
        print(f"FAIL: {len(findings)} credential-shaped hit(s) in the {scope}:")
        for f in findings[:40]:
            print("  " + f)
        return 1
    print(f"OK: no credential-shaped strings in the {scope}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
