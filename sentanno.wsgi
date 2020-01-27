#!/usr/bin/python3

import logging
import sys

logging.basicConfig(stream=sys.stderr)
sys.path.insert(0, '/var/www/flask/sentanno/')

from sentanno import create_app

application = create_app()
