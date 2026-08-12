#!/usr/bin/env python3
"""BUILD TIME. Scrub machine-identifying strings out of archived run records.

WHY, AND WHY ONLY THIS MUCH
---------------------------
The run records ship with the submission, because REPORT.md points a reader at them and a
provenance claim nobody can check is the weakest kind. Shipping them means publishing
whatever the tools happened to write down, which includes the absolute paths of a developer
machine.

The line this draws matters. Two categories look similar and are not:

  REMOVED   Paths, hostnames, addresses, provider names. These identify a machine and its
            owner. None of them is load bearing for any measurement in this project.

  KEPT      cpu_model, ram_gb, host_cpu_count, steal readings, thread counts. These
            describe the measurement conditions and several are load bearing: the
            oversubscription finding is precisely that llama-bench reported 12 threads
            inside a container capped at 4 CPUs, which cannot be stated without
            host_cpu_count. Scrubbing them would publish a cleaner archive that proves
            less.

RUN IT BEFORE THE FIRST COMMIT THAT INCLUDES runs/. Git history is not scrubbable after
the fact, and `runs/` has never been committed, so there is exactly one clean moment.

Usage:
    python3 scripts/scrub_runs.py            # report only, exits 1 if anything is found
    python3 scripts/scrub_runs.py --apply    # rewrite, printing every change
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RUNS = REPO / "runs"

SCRUBBABLE = ("*.json", "*.log", "*.stderr", "*.txt")

# Rewritten automatically: the repo's own absolute path becomes a repo-relative one, which
# loses nothing. A reader gets a more useful record, not a redacted one.
REPO_PREFIX = str(REPO).rstrip("/") + "/"

# Reported, never auto-rewritten. Each needs a human decision about what the replacement
# should say, and a wrong automatic substitution in an archived record is worse than a
# flagged one.
FLAG_ONLY = {
    "home directory path": re.compile(r"/(?:home|Users)/[A-Za-z0-9._-]+"),
    "hostname or FQDN": re.compile(
        r"\b[a-z0-9][a-z0-9-]*\.(?:[a-z0-9-]+\.)+(?:net|com|org|io|cloud|host)\b", re.I),
    "IP address": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "hosting provider": re.compile(
        r"\b(?:contabo|vultr|hetzner|linode|digitalocean|ovh|scaleway|akamai)\b", re.I),
}

# Named so the decision to keep them is visible rather than implicit.
DELIBERATELY_KEPT = (
    "cpu_model", "ram_gb", "host_cpu_count", "steal_pct", "runnable_before",
    "thread counts, container constraints, and every measured value",
)

# Loopback and unspecified addresses are configuration, not location.
IP_ALLOWED = {"0.0.0.0", "127.0.0.1", "255.255.255.255"}


def targets() -> list[Path]:
    return sorted(p for pattern in SCRUBBABLE for p in RUNS.rglob(pattern) if p.is_file())


def findings(text: str) -> list[tuple[str, str]]:
    out = []
    for label, pattern in FLAG_ONLY.items():
        for match in set(pattern.findall(text)):
            if label == "IP address" and match in IP_ALLOWED:
                continue
            out.append((label, match))
    return sorted(set(out))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="rewrite repo-absolute paths; other findings stay flagged")
    args = ap.parse_args()

    if not RUNS.exists():
        print("no runs/ directory")
        return 0

    rewritten, flagged = [], []
    for path in targets():
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        new = text.replace(REPO_PREFIX, "")
        if new != text:
            count = text.count(REPO_PREFIX)
            rewritten.append((path, count))
            if args.apply:
                path.write_text(new, encoding="utf-8")

        for label, value in findings(new):
            flagged.append((path, label, value))

    rel = lambda p: p.relative_to(REPO)
    verb = "rewrote" if args.apply else "would rewrite"
    print(f"{verb} repo-absolute paths in {len(rewritten)} file(s):")
    for path, count in rewritten:
        print(f"  {rel(path)}  ({count})")
    if not rewritten:
        print("  (none)")

    print("\nflagged, needs a human decision:")
    for path, label, value in flagged:
        print(f"  {rel(path)}: {label} -> {value!r}")
    if not flagged:
        print("  (none)")

    print("\ndeliberately kept, because the measurements depend on them:")
    for field in DELIBERATELY_KEPT:
        print(f"  {field}")

    if flagged:
        print("\nResolve the flagged items by hand before committing runs/.")
        return 1
    if rewritten and not args.apply:
        print("\nRe-run with --apply, review the diff, then commit.")
        return 1
    print("\nClean." if args.apply or not rewritten else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
