#!/bin/bash
# Start Conduit

# Work around https://bugs.launchpad.net/ubuntu/+source/firefox/+bug/26436
F=$(lsb_release -is)
if [ $? == 0 ]; then
  # we have LSB support
  if [ "$F" = "Ubuntu" ]; then
    # we are Ubuntu, so work around the bug
    LD_LIBRARY_PATH=/usr/lib/firefox MOZILLA_FIVE_HOME=/usr/lib/firefox python $(dirname $0)/conduit/start_conduit.py
    exit
  fi
fi

# Not Ubuntu, so run it normally
python $(dirname $0)/conduit/start_conduit.py

