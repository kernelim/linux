#!/usr/bin/python3
#
# This script parses a git log from stdin, which should be given with:
# $ git log [<options>] -z --format="- %s (%an)%n%b" [<range>] [[--] <path>...] | ...
# And then outputs to stdout a trimmed changelog for use with rpm packaging
#
# Author: Herton R. Krzesinski <herton@redhat.com>
# Copyright (C) 2021 Red Hat, Inc.
#
# This software may be freely redistributed under the terms of the GNU
# General Public License (GPL).

"""Parses a git log from stdin, and output a log entry for an rpm."""

import re
import sys

def find_bz_in_line(line, prefix):
    """Return bug number from properly formated Bugzilla: line."""
    # BZs must begin with '{prefix}: ' and contain a complete BZ URL or id
    _bugs = set()
    if not line.startswith(f"{prefix}: "):
        return _bugs
    bznum_re = re.compile(r'(?P<bug_ids> \d{4,8})|'
        r'( http(s)?://bugzilla\.redhat\.com/(show_bug\.cgi\?id=)?(?P<url_bugs>\d{4,8}))')
    for match in bznum_re.finditer(line[len(f"{prefix}:"):]):
        for group in [ 'bug_ids', 'url_bugs' ]:
            if match.group(group):
                bid = match.group(group).strip()
                _bugs.add(bid)
    return _bugs

def find_cve_in_line(line):
    """Return cve number from properly formated CVE: line."""
    # CVEs must begin with 'CVE: '
    cve_set = set()
    if not line.startswith("CVE: "):
        return cve_set
    _cves = line[len("CVE: "):].split()
    pattern = "(?P<cve>CVE-[0-9]+-[0-9]+)"
    cve_re = re.compile(pattern)
    for cve_item in _cves:
        cve = cve_re.match(cve_item)
        if cve:
            cve_set.add(cve.group('cve'))
    return cve_set


def parse_commit(commit):
    """Extract metadata from a commit log message."""
    lines = commit.split('\n')

    # Escape '%' as it will be used inside the rpm spec changelog
    log_entry = lines[0].replace("%","%%")

    cve_set = set()
    bug_set = set()
    zbug_set = set()
    for line in lines[1:]:
        # Metadata in git notes has priority over commit log
        # If we found any BZ/ZBZ/CVE in git notes, we ignore commit log
        if line == "^^^NOTES-END^^^":
            if bug_set or zbug_set or cve_set:
                break

        # Process Bugzilla and ZStream Bugzilla entries
        bug_set.update(find_bz_in_line(line, 'Bugzilla'))
        zbug_set.update(find_bz_in_line(line, 'Z-Bugzilla'))

        # Grab CVE tags if they are present
        cve_set.update(find_cve_in_line(line))

    return (log_entry, sorted(cve_set), sorted(bug_set), sorted(zbug_set))


if __name__ == "__main__":
    all_bzs = []
    all_zbzs = []
    commits = sys.stdin.read().split('\0')
    for c in commits:
        if not c:
            continue
        log_item, cves, bugs, zbugs = parse_commit(c)
        entry = f"{log_item}"
        if bugs or zbugs:
            entry += " ["
            if zbugs:
                entry += " ".join(zbugs)
                all_zbzs.extend(zbugs)
            if bugs and zbugs:
                entry += " "
            if bugs:
                entry += " ".join(bugs)
                all_bzs.extend(bugs)
            entry += "]"
        if cves:
            entry += " {" + " ".join(cves) + "}"
        print(entry)

    resolved_bzs = []
    for bzid in (all_zbzs if all_zbzs else all_bzs):
        if not bzid in resolved_bzs:
            resolved_bzs.append(bzid)
    print("Resolves: ", end="")
    for i, bzid in enumerate(resolved_bzs):
        if i:
            print(", ", end="")
        print(f"rhbz#{bzid}", end="")
    print("\n")

