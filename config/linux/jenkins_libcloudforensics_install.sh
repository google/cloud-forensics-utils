#!/usr/bin/env bash

# Exit on error
set -e

sudo apt-get update -q
sudo apt-get install -y python3-pip

# Install libcloudforensics pinned requirements
sudo pip3 install -r ../../requirements.txt
