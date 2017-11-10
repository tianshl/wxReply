#!/usr/bin/env bash

rm -rf .tmp
rm -rf __pycache__
rm -rf dist
rm -rf wxReply.egg-info
python3 setup.py check
python3 setup.py sdist
python3 setup.py sdist register upload