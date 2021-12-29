#!/bin/bash
cd /volume1/docker/nastool/src/
rm -rf ./nas-tools
rm nas-tools.tar
git clone https://github.com/jxxghp/nas-tools
tar -cvf nas-tools.tar nas-tools/
docker build -t jxxghp/nas-tools:latest .
docker push jxxghp/nas-tools:latest
