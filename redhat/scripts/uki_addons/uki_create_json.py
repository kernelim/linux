#!/usr/bin/env python3
#
# This script recursively inspects the 'redhat/uki_addons' directory,
# and creates a json file containing name and description of each addon found.
#
# Usage: python uki_create_json.py output_file
#
# Addon file
#-----------
# The addon files are contained into the 'redhat/uki_addons' folder.
# Each addon terminates with .addon.
# Each addon contains only two types of lines:
# Lines beginning with '#' are description and thus ignored
# All other lines are command line to be added.
# This script just parses the folder structure and creates a json reflecting
# all addons and their line found.
# For example, if we define test.addon (text: 'test1\n') in
# redhat/uki_addons/virt/rhel/x86_64, the resulting output_file will contain
# { 'virt' : { 'rhel' : { 'x86_64' : { 'test.addon' : ['test1\n'] }}}}
#
# The name of the end resulting addon is taken from the folder hierarchy, but this
# is handled by uki_create_addons.py when building the rpm. This script only
# prepares the json file to be added in the srpm. For more information about
# the folder hierarchy and what the 'common' folder is, look at
# uki_create_addons.py.
#
# The common folder, present in any folder under redhat/uki_addons
# (except the leaf folders) is used as place for default addons when the same
# addon is not defined deep in the hierarchy.
#
# How to extend the script and kernel.spec with a new arch or uki or distro
#--------------------------------------------------------------------------
# A new distro has to be added by creating the folder in redhat/uki_addons.
# See uki_create_addons.py to how the directory hierarchy in redhat/uki_addons
# is expected to be.
# After that, if the distro is a different arch from the one already supported,
# one needs to extend the %define with_efiuki in kernel.spec.template.
# If a new UKI has to be created with a different name from the existing ones,
# the logic to create the addons and call this script has to be implemented too
# in kernel.spec.template. As an example, see how the 'virt' UKI addons are
# created.

import os
import sys
import json
import subprocess

def usage(err):
    print(f'Usage: {os.path.basename(__file__)} dest_file')
    print(f'Error:{err}')
    sys.exit(1)

def find_addons():
    cmd = ['/usr/bin/find', 'uki_addons', '-name', '*.addon']
    proc_out = subprocess.run(cmd, check=True, capture_output=True, text=True)
    if proc_out.returncode == 0:
        return proc_out.stdout
    return None

def add_keys_to_obj(ret_data, keys, value):
    if len(keys) == 0:
        return
    key = keys[0]
    val = {}
    if len(keys) == 1:
        val = value
    if not key in ret_data:
        ret_data[key] = val
    ret_data = ret_data[key]
    add_keys_to_obj(ret_data, keys[1:], value)

def create_json(addons):
    obj = {}
    for el in addons:
        print(f'Processing {el} ...')
        with open(el, 'r') as f:
            lines = f.readlines()
        dirs, name = os.path.split(el)
        keys = dirs.split('/')
        if keys[0] == 'uki_addons':
            keys = keys[1:]
        keys.append(name)
        add_keys_to_obj(obj, keys, lines)
        print(f'Processing {el} completed')
    return obj

def write_json(obj, dest_file):
    with open(dest_file, 'w') as f:
        json.dump(obj , f, indent=4, sort_keys=True)
    print(f'Processed addons files are in {dest_file}')

if __name__ == "__main__":
    argc = len(sys.argv) - 1
    if argc != 1:
        usage('too few or too many parameters!')
    dest = sys.argv[1]

    output = find_addons()
    if output is None:
        usage('error finding the addons')
    addons_list = output.split()
    obj = create_json(addons_list)
    write_json(obj, dest)

