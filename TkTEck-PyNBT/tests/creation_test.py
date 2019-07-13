#!/usr/bin/env python
# -*- coding: utf8 -*-
import unittest
from pynbt import *


class CreationTest(unittest.TestCase):
    def setUp(self):
        self.nbt = NBTFile(name='')

    def test_save(self):
        n = self.nbt
        n['byte'] = TAG_Byte(0)
        n['short'] = TAG_Short(1)
        n['int'] = TAG_Int(2)
        n['float'] = TAG_Float(3.)
        n['double'] = TAG_Double(4.)
        n['string'] = TAG_String('Testing')
        n['int_array'] = TAG_Int_Array([45, 5, 6])
        n['byte_array'] = TAG_Byte_Array([4, 3, 2])
        n['long_array'] = TAG_Long_Array([5, 6, 7])
        n['list'] = TAG_List(TAG_Int, [
            TAG_Int(4)
        ])
        n['autolist_int'] = TAG_List(TAG_Int, [
            5,
            6,
            7,
            30240,
            -340
        ])
        n['autolist_compound'] = TAG_List(TAG_Compound, [
            {
                'name': TAG_String('ABC'),
                'health': TAG_Double(3.5)
            }
        ])
        with open('__test__.nbt', 'wb') as io:
            self.nbt.save(io)

if __name__ == '__main__':
    unittest.main()
