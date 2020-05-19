# -*- coding: utf-8 -*-
# Copyright 2020 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Common utilities."""
import binascii
import logging
import os
import re
import socket

from google.auth import default
from google.auth.exceptions import DefaultCredentialsError
from googleapiclient.discovery import build

log = logging.getLogger()
RETRY_MAX = 10
REGEX_DISK_NAME = re.compile('^(?=.{1,63}$)[a-z]([-a-z0-9]*[a-z0-9])?$')
STARTUP_SCRIPT = 'scripts/startup.sh'


def GenerateDiskName(snapshot, disk_name_prefix=None):
  """Generate a new disk name for the disk to be created from the Snapshot.

  The disk name must comply with the following RegEx:
      - ^(?=.{1,63}$)[a-z]([-a-z0-9]*[a-z0-9])?$

  i.e., it must be between 1 and 63 chars, the first character must be a
  lowercase letter, and all following characters must be a dash, lowercase
  letter, or digit, except the last character, which cannot be a dash.

  Args:
    snapshot (GoogleComputeSnapshot): A disk's Snapshot.
    disk_name_prefix (str): Optional. A prefix for the disk name.

  Returns:
    str: A name for the disk.

  Raises:
    ValueError: If the disk name does not comply with the RegEx.
  """

  # Max length of disk names in GCP is 63 characters
  project_id = snapshot.project.project_id
  disk_id = project_id + snapshot.disk.name
  disk_id_crc32 = '{0:08x}'.format(
      binascii.crc32(disk_id.encode()) & 0xffffffff)
  truncate_at = 63 - len(disk_id_crc32) - len('-copy') - 1
  if disk_name_prefix:
    disk_name_prefix += '-'
    if len(disk_name_prefix) > truncate_at:
      # The disk name prefix is too long
      disk_name_prefix = disk_name_prefix[:truncate_at]
    truncate_at -= len(disk_name_prefix)
    disk_name = '{0:s}{1:s}-{2:s}-copy'.format(
        disk_name_prefix, snapshot.name[:truncate_at], disk_id_crc32)
  else:
    disk_name = '{0:s}-{1:s}-copy'.format(
        snapshot.name[:truncate_at], disk_id_crc32)

  if not REGEX_DISK_NAME.match(disk_name):
    raise ValueError(
        'Disk name {0:s} does not comply with '
        '{1:s}'.format(disk_name, REGEX_DISK_NAME.pattern))

  return disk_name


def CreateService(service_name, api_version):
  """Creates an GCP API service.

  Args:
    service_name (str): Name of the GCP service to use.
    api_version (str): Version of the GCP service API to use.

  Returns:
    apiclient.discovery.Resource: API service resource.

  Raises:
    RuntimeError: If Application Default Credentials could not be obtained or if
        service build times out.
  """

  try:
    credentials, _ = default()
  except DefaultCredentialsError as error:
    error_msg = (
        'Could not get application default credentials: {0!s}\n'
        'Have you run $ gcloud auth application-default '
        'login?').format(error)
    raise RuntimeError(error_msg)

  service_built = False
  for retry in range(RETRY_MAX):
    try:
      service = build(
          service_name, api_version, credentials=credentials,
          cache_discovery=False)
      service_built = True
    except socket.timeout:
      log.info(
          'Timeout trying to build service {0:s} (try {1:s} of {2:s})'.format(
              service_name, retry, RETRY_MAX))

    if service_built:
      break

  if not service_built:
    error_msg = (
        'Failures building service {0:s} caused by multiple '
        'timeouts').format(service_name)
    raise RuntimeError(error_msg)

  return service


def ReadStartupScript():
  """Read and return the startup script that is to be run on the forensics VM.

  Users can either write their own script to install custom packages,
  or use the provided one. To use your own script, export a STARTUP_SCRIPT
  environment variable with the absolute path to it:
  "user@terminal:~$ export STARTUP_SCRIPT='absolute/path/script.sh'"

  Returns:
    str: The script to run.
  Raises:
    OSError: If the script cannot be opened, read or closed.
  """

  try:
    startup_script = os.environ.get('STARTUP_SCRIPT')
    if not startup_script:
      # Use the provided script
      startup_script = os.path.join(
          os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
              os.path.realpath(__file__))))), STARTUP_SCRIPT)
    startup_script = open(startup_script)
    script = startup_script.read()
    startup_script.close()
    return script
  except OSError as exception:
    raise OSError(
        'Could not open/read/close the startup script {0:s}: '
        '{1:s}'.format(startup_script, str(exception)))
