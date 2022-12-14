# This Python file uses the following encoding: utf-8

# instrument_manager.py
# author: chi
#
# DESCRIPTION
# Connects and communicates with all measurement instruments, for data acquisition
# Power supplies
# Oscilloscopes
#

# CODE STARTS HERE

import sys
import os
import usb.core
import usb.util
import visa
import time
import struct
import numpy as np


class instrument_manager:
    def __init__(self):
        # find all devices connected via usb

        # associate each device with a class of instrument
