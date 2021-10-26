#!/bin/bash
cd /volume1/docker/nastool/src/
rm nas-tools.tar
tar -cvf nas-tools.tar nas-tools/
docker build -t jxxghp/nas-tools:latest .
docker push jxxghp/nas-tools:latest
