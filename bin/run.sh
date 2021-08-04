#!/bin/bash
ps -ef | grep /nas-tools/run.py | grep -v grep | awk '{print $2}' | xargs kill -9
sleep 1
nohup python /nas-tools/run.py &
