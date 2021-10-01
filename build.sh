#!/bin/bash
cd /mnt/user/appdata/nastool/src/
rm nas-tools.tar
tar -cvf nas-tools.tar nas-tools/
docker build -t jxxghp/nas-tools:latest .
docker push jxxghp/nas-tools:latest
