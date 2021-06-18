#!/bin/bash
#
# Startup script to execute when bootstrapping a new forensic VM.
# The script will install forensics packages to perform analysis.

max_retry=100

gift_ppa_track='stable'

# Default packages to install
# This can be overwritten in GetOrCreateAnalysisVm(
#   packages=['package1', 'package2', ...])
packages=(
  binutils
  docker-explorer-tools
  htop
  jq
  libbde-tools
  libfsapfs-tools
  libfvde-tools
  ncdu
  plaso-tools
  sleuthkit
  upx-ucl
)

err() {
  echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')]: $*" >&2
}

install_packages() {
  add-apt-repository -y -u ppa:gift/${gift_ppa_track}
  apt -y install ${packages[@]}
}

# Try to install the packages
for try in $(seq 1 ${max_retry}); do
  [[ ${try} -gt 1 ]] && sleep 5
  install_packages && exit_code=0 && break || exit_code=$?
  err "Failed to install forensics packages, retrying in 5 seconds."
done;

(exit ${exit_code})
