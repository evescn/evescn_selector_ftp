# -*- coding: utf-8 -*-
# @Author    : Evescn
# @time      : 2020/11/26 10:56
# @File      : settings.py
# @Software  : PyCharm
import os
import logging
from core import logger

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HOST_IP = 'localhost'
HOST_PORT = 9998

LOG_LEVEL = logging.INFO

LOG_TYPES = {
    'transaction': 'transactions.log',
    'access': 'access.log',
}

# access logger
access_logger = logger.logger('access')
