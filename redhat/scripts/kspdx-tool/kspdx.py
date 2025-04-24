#! /usr/bin/python3

# SPDX-License-Identifier: LGPL-2.1-or-later

import argparse
import os
import re
import subprocess
import sys

# Files to not search for SPDX patterns
ignored_files = [
    # license-rules.rst describe how to write SPDX-License-Identifier tags, skip it
    "/process/license-rules.rst",
]

# Generators, take the first SPDX identifier only to avoid
# parsing the code which adds 'SPDX-License-Identifier' to some
# other code.
generators = [
    "/scripts/atomic/gen-atomic-fallback.sh",
    "/scripts/atomic/gen-atomic-instrumented.sh",
    "/scripts/atomic/gen-atomic-long.sh",
    "/tools/bpf/bpftool/gen.c",
    "/tools/net/ynl/lib/nlspec.py",
    "/tools/net/ynl/ynl-gen-c.py",
    "/tools/testing/selftests/bpf/generate_udp_fragments.py",
]

def run_command(cmdargs, sysexit=False, canfail=False, input=None):
    res = subprocess.run(cmdargs, check=False, capture_output=True, text=True, input=input)
    if res.returncode != 0 and not canfail:
        print("%s returned %d, stdout: %s stderr: %s" % (res.args, res.returncode, res.stdout, res.stderr), file=sys.stderr)
        if sysexit:
            sys.exit(1)
        else:
            raise Exception("%s command failed" % cmdargs[0])
    return res

def get_file_source(path, commit = None):
    if not commit:
        try:
            with open(path, 'rb') as fp:
                return fp.read().decode('utf-8', errors='ignore')
        except Exception as e:
            print("Failed to read file %s: %s" % (path, e), file=sys.stderr)
            return None
    else:
        try:
            res = run_command(['git', 'show', "%s:%s" % (commit, path)])
            return res.stdout
        except Exception as e:
            print("Failed to show file %s from commit %s: %s" % (path, commit, e), file=sys.stderr)
            return None

# Valid chars in SPDX tag: a-Z,0-9,-,+,_, ,\t,(,),.
spdx_pattern = re.compile(r"(?:--|\*|#|//|\.\.)\s*SPDX-License-Identifier:\s+([a-zA-Z0-9\-_\.\t \(\)\+]+)")

def get_spdx_string(fpath, commit, default, first_only=False):
    content = get_file_source(fpath, commit)
    if content is None:
        print("Failed to get content of %s" % fpath, file=sys.stderr)
        sys.exit(1)

    r = spdx_pattern.findall(content)

    if first_only:
        r = r[:1]
    elif len(set(r)) > 1:
        print("WARNING: %s lists more than one different license, please check!" % fpath, file=sys.stderr)

    changed = True
    while changed:
        changed = False
        for i in range(len(r)):
            s = r[i]
            # Remove extra spaces
            s = " ".join(s.split())

            # Remove trailing '--' (SVG)
            s = re.sub("--$", "", s)

            # Make all operators uppercase
            s = re.sub(' or ', ' OR ', s, flags=re.IGNORECASE)
            s = re.sub(' with ', ' WITH ', s, flags=re.IGNORECASE)
            s = re.sub(' and ', ' AND ', s, flags=re.IGNORECASE)

            # Drop unneded highest level parentheses
            s = re.sub("^\((.*)\)$", "\g<1>", s)

            # Drop unneeded inner parentheses when there are no spaces
            s = re.sub("\(([^ ]+)\)", "\g<1>", s)

            # (A OR B) OR C equals A OR B OR C
            s = re.sub("\((.*) OR (.*)\) OR", "\g<1> OR \g<2> OR", s)
            # A OR (B OR C) equals A OR B OR C
            s = re.sub("OR \((.*) OR (.*)\)", "OR \g<1> OR \g<2>", s)

            # Assuming there's just one level of ORs, sort the licenses in reverse alphabetical order
            # sort only when no parentheses
            if s.find(' OR ') != -1 and s.find('(') == -1:
                s = ' OR '.join([e.strip() for e in sorted(s.split(' OR '), reverse=True)])

            # Split A and B into two items but make sure parenthes are balanced
            and_pos = 0
            while True:
                and_pos = s.find(' AND ', and_pos+1)
                if and_pos > 0:
                    l1 = s[:and_pos]
                    l2 = s[and_pos+5:]
                    if l1.count('(') == l1.count(')') and l2.count('(') == l2.count(')'):
                        r.append(l2)
                        s = l1
                        break
                else:
                    break

            if s != r[i]:
                r[i] = s
                changed = True
    if r == []:
        r = [default]

    return r

def convert_deprecated(license):
    # Deprecated ids, see https://spdx.org/licenses/
    # GPL-1.0 equals GPL-1.0-only
    license = re.sub("GPL-1.0($| )", "GPL-1.0-only\g<1>", license)
    # GPL-1.0+ equals GPL-1.0-or-later
    license = re.sub("GPL-1.0\+($| )", "GPL-1.0-or-later\g<1>", license)

    # GPL-2.0 equals GPL-2.0-only
    license = re.sub("GPL-2.0($| )", "GPL-2.0-only\g<1>", license)
    # GPL-2.0+ equals GPL-2.0-or-later
    license = re.sub("GPL-2.0\+($| )", "GPL-2.0-or-later\g<1>", license)

    # LGPL-2.0 equals LGPL-2.0-only
    license = re.sub("LGPL-2.0($| )", "LGPL-2.0-only\g<1>", license)
    # LGPL-2.0+ equals LGPL-2.0-or-later
    license = re.sub("LGPL-2.0\+($| )", "LGPL-2.0-or-later\g<1>", license)

    # LGPL-2.1 equals LGPL-2.1-only
    license = re.sub("LGPL-2.1($| )", "LGPL-2.1-only\g<1>", license)
    # LGPL-2.1+ equals LGPL-2.1-or-latery
    license = re.sub("LGPL-2.1\+($| )", "LGPL-2.1-or-later\g<1>", license)

    # Use standard uppercase 'OR'
    license = re.sub(" or ", " OR ", license)
    return license

def unique_licenses(licenses):
    res = []
    for license in licenses:
        license = convert_deprecated(license)
        already_present = False
        for existing in res:
            if license.upper() == existing.upper():
                already_present = True
        if already_present:
            continue
        res.append(license)
    return sorted(res)

def license_andlist(unique):
    s = ""
    for i in range(len(unique)):
        # Parenthes are needed for everything but a singe item
        if unique[i].find(' ') != -1 and len(unique) > 1:
            s += '(' + unique[i] + ')'
        else:
            s += unique[i]
        if i != len(unique) - 1:
            s += ' AND '
    return s

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Report SPDX-License-Identifier tag for a kernel source file/directory',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('path', help='Path in the source tree')
    parser.add_argument('-c', '--commit', help='Inspect given commit/HEAD instead of the current state')
    parser.add_argument('-d', '--default', help='Default license', default="GPL-2.0-only")
    parser.add_argument('-i', '--itemized', help='Print license[s] per file', action="store_true")
    parser.add_argument('-j', '--joint', help='Print a single statement for all discovered licenses', action="store_true")
    args = parser.parse_args()

    if os.path.isdir(args.path) and args.commit:
        print("The specified path %s is a directory and --commit was given, this is unsupported." % args.path, file=sys.stderr)

    files = []
    if os.path.isdir(args.path):
        w = os.walk(args.path)
        for (dpath, dnames, fnames) in w:
            # Skip .git objects
            if '.git' in dpath.split('/'):
                continue
            files.extend([dpath.rstrip('/') + '/' + fname for fname in fnames])
    else:
        files = [args.path]

    licenses = []
    for fpath in files:
        ignore = False
        for ignored in ignored_files:
            if fpath.endswith(ignored):
                ignore = True
                continue
        if ignore:
            continue

        generator = False
        for ignored in generators:
            if fpath.endswith(ignored):
                generator = True
                continue

        file_licenses = get_spdx_string(fpath, args.commit, args.default, generator)
        unique = unique_licenses(file_licenses)
        if not args.itemized:
            licenses.extend(unique)
        else:
            print("%s: %s" % (fpath, license_andlist(unique)))

    if not args.itemized:
        if not args.joint:
            for license in sorted(set(licenses)):
                print(license)
        else:
            print(license_andlist(sorted(set(licenses))))

    sys.exit(0)
