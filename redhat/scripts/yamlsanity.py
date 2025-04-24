#!/usr/bin/env python3

import sys
import yaml

def default_ctor(loader, tag_suffix, node):
    return None

if __name__ == '__main__':
    print('yaml sanity check', sys.argv[1], end=' ')

    loader = yaml.SafeLoader
    loader.add_multi_constructor('', default_ctor)

    with open(sys.argv[1], 'r') as file:
        yaml.load(file, Loader=loader)
    print('OK')
