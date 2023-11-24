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

def find_ticket_in_line(line, prefix, tkt_re, tkt_groups):
    """Return ticket referenced in the given line"""
    _tkts = set()
    if not line.startswith(f"{prefix}: "):
        return _tkts
    for match in tkt_re.finditer(line[len(f"{prefix}:"):]):
        for group in tkt_groups:
            if match.group(group):
                tid = match.group(group).strip()
                _tkts.add(tid)
    return _tkts

def find_bz_in_line(line, prefix):
    bznum_re = re.compile(r'(?P<bug_ids> \d{4,8})|'
        r'( http(s)?://bugzilla\.redhat\.com/(show_bug\.cgi\?id=)?(?P<url_bugs>\d{4,8}))')
    return find_ticket_in_line(line, prefix, bznum_re, [ 'bug_ids', 'url_bugs' ])

def find_ji_in_line(line, prefix):
    ji_re = re.compile(r' https://issues\.redhat\.com/(?:browse|projects/RHEL/issues)/(?P<jira_id>RHEL-\d{1,8})\s*$')
    return find_ticket_in_line(line, prefix, ji_re, [ 'jira_id' ])

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
    jira_set = set()
    zjira_set = set()
    for line in lines[1:]:
        # Metadata in git notes has priority over commit log
        # If we found any BZ/ZBZ/JIRA/ZJIRA/CVE in git notes,
        # we ignore the commit log
        if line == "^^^NOTES-END^^^":
            if bug_set or zbug_set or jira_set or zjira_set or cve_set:
                break

        # Process Bugzilla and ZStream Bugzilla entries
        bug_set.update(find_bz_in_line(line, 'Bugzilla'))
        zbug_set.update(find_bz_in_line(line, 'Z-Bugzilla'))

        # Grab CVE tags if they are present
        cve_set.update(find_cve_in_line(line))

        # Process Jira issues
        jira_set.update(find_ji_in_line(line, 'JIRA'))
        zjira_set.update(find_ji_in_line(line, 'Z-JIRA'))

    return (log_entry, cve_set, bug_set, zbug_set, jira_set, zjira_set)


if __name__ == "__main__":
    all_bzs = set()
    all_zbzs = set()
    all_jiras = set()
    all_zjiras = set()
    commits = sys.stdin.read().split('\0')
    for c in commits:
        if not c:
            continue
        log_item, cves, bugs, zbugs, jiras, zjiras = parse_commit(c)
        entry = f"{log_item}"
        if bugs or zbugs or jiras or zjiras:
            entry += " ["
            if zbugs:
                entry += " ".join(sorted(zbugs))
                all_zbzs.update(zbugs)
            if zjiras:
                entry += " " if zbugs else ""
                entry += " ".join(sorted(zjiras))
                all_zjiras.update(zjiras)
            if bugs:
                entry += " " if zbugs or zjiras else ""
                entry += " ".join(sorted(bugs))
                all_bzs.update(bugs)
            if jiras:
                entry += " " if zbugs or bugs or zjiras else ""
                entry += " ".join(sorted(jiras))
                all_jiras.update(jiras)
            entry += "]"
        if cves:
            entry += " {" + " ".join(sorted(cves)) + "}"
        print(entry)

    # If we are doing Z-Stream work, we are addressing Z-Stream tickets
    # and not Y-Stream tickets, so we must make sure to list on Resolves
    # line only the Z-Stream tickets
    resolved_bzs = set()
    resolved_jiras = set()
    if all_zbzs or all_zjiras:
        resolved_bzs = all_zbzs
        resolved_jiras = all_zjiras
    else:
        resolved_bzs = all_bzs
        resolved_jiras = all_jiras
    print("Resolves: ", end="")
    for i, bzid in enumerate(sorted(resolved_bzs)):
        if i:
            print(", ", end="")
        print(f"rhbz#{bzid}", end="")
    for j, jid in enumerate(sorted(resolved_jiras)):
        if j or resolved_bzs:
           print(", ", end="")
        print(f"{jid}", end="")
    print("\n")

