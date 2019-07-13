#!/usr/bin/env python
# -*- coding: utf8 -*-
import sys
from pynbt import NBTFile


def main(argv):
    with open(sys.argv[1], 'rb') as fin:
        n = NBTFile(fin)
        print(n.pretty())

if __name__ == '__main__':
    sys.exit(main(sys.argv))
