#!/bin/bash
# Wrapper for send_bot_alerts.py to scrub PYTHONPATH

set -e
env -u PYTHONPATH -u LD_LIBRARY_PATH ./send_bot_alerts.py "$@" >> /var/log/securitybot/send_bot_alerts.log 2>&1
