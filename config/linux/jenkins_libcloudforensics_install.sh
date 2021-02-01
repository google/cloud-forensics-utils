#!/usr/bin/env bash

# Exit on error
set -e

sudo apt-get update -q
sudo apt-get install -y python3-pip

# Install libcloudforensics pinned requirements
sudo pip3 install -r ../../requirements-base.txt
sudo pip3 install -r ../../requirements-aws.txt
sudo pip3 install -r ../../requirements-azure.txt
sudo pip3 install -r ../../requirements-gcp.txt
