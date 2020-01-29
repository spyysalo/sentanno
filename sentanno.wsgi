#!/usr/bin/python3

import logging
import sys

from os import path

logging.basicConfig(stream=sys.stderr)
sys.path.insert(0, path.dirname(__file__))

from sentanno import create_app

application = create_app()
