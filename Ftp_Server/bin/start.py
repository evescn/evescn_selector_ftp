# -*- coding: utf-8 -*-
# @Author    : Evescn
# @time      : 2020/11/25 17:36
# @File      : start.py
# @Software  : PyCharm

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from core import main

if __name__ == '__main__':
    main.start()