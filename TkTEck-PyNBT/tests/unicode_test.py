#!/usr/bin/env python
# -*- coding: utf8 -*-
import unittest
from pynbt import *


class UnicodeTest(unittest.TestCase):
    def test_unicode_key(self):
        n = NBTFile(name='')
        n[u'ä'] = TAG_String('')

    def test_unicode_string(self):
        n = NBTFile(name='')
        n['unicode'] = TAG_String(u'ä')

    def test_unicode_pretty(self):
        n = NBTFile(name='')
        n[u'ä'] = TAG_String(u'ä')
        n.pretty()

    def test_unicode_str(self):
        n = NBTFile(name='')
        n[u'ä'] = TAG_String(u'ä')
        str(n[u'ä'])

    def test_unicode_unicode(self):
        n = NBTFile(name='')
        n[u'ä'] = TAG_String(u'ä')
        unicode(n[u'ä'])

if __name__ == '__main__':
    unittest.main()
