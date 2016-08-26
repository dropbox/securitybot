#!/usr/bin/python
import sys
from subprocess import call

logging_file = open('/var/log/securitybot/bot_lookup.log', 'a+')
# Build arguments
c = ['env', '-u', 'PYTHONPATH', '-u', 'LD_LIBRARY_PATH', '/path/to/securitybot']
c.extend(sys.argv[1:])
call(c, stderr=logging_file)
