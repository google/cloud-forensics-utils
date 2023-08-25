#!/usr/bin/env bash

# Exit on error
set -e

sudo apt-get update -q
sudo apt-get install -y python3-pip
sudo pip3 install poetry

# Install libcloudforensics pinned requirements
sudo python -m poetry install --with dev
