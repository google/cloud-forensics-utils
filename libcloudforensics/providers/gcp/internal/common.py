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
import re
import socket
import time
from typing import TYPE_CHECKING, Dict, List, Optional, Any

from google.auth import default
from google.auth.exceptions import DefaultCredentialsError, RefreshError
from googleapiclient.discovery import build

if TYPE_CHECKING:
  import googleapiclient
  # TYPE_CHECKING is always False at runtime, therefore it is safe to ignore
  # the following cyclic import, as it it only used for type hints
  from libcloudforensics.providers.gcp.internal import compute  # pylint: disable=cyclic-import

LOGGER = logging.getLogger()
RETRY_MAX = 10
REGEX_DISK_NAME = re.compile('^(?=.{1,63}$)[a-z]([-a-z0-9]*[a-z0-9])?$')


def GenerateDiskName(snapshot: 'compute.GoogleComputeSnapshot',
                     disk_name_prefix: Optional[str] = None) -> str:
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
  project_id = snapshot.project_id
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


def CreateService(service_name: str,
                  api_version: str) -> 'googleapiclient.discovery.Resource':
  """Creates an GCP API service.

  Args:
    service_name (str): Name of the GCP service to use.
    api_version (str): Version of the GCP service API to use.

  Returns:
    googleapiclient.discovery.Resource: API service resource.

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
      LOGGER.info(
          'Timeout trying to build service {0:s} (try {1:d} of {2:d})'.format(
              service_name, retry, RETRY_MAX))

    if service_built:
      break

  if not service_built:
    error_msg = (
        'Failures building service {0:s} caused by multiple '
        'timeouts').format(service_name)
    raise RuntimeError(error_msg)

  return service


class GoogleCloudComputeClient:
  """Class representing Google Cloud Compute API client.

  Request and response dictionary content is described here:
  https://cloud.google.com/compute/docs/reference/rest/v1

  Attributes:
    project_id (str): Project name.
  """

  COMPUTE_ENGINE_API_VERSION = 'v1'

  def __init__(self, project_id: Optional[str] = None) -> None:
    """Initialize Google Cloud Engine API client object.

    Args:
     project_id (str): Optional. Project name. Needed to use BlockOperation.
    """
    self._gce_api_client = None
    self.project_id = project_id

  def GceApi(self) -> 'googleapiclient.discovery.Resource':
    """Get a Google Compute Engine service object.

    Returns:
      googleapiclient.discovery.Resource: A Google Compute Engine service
          object.
    """

    if self._gce_api_client:
      return self._gce_api_client
    self._gce_api_client = CreateService(
        'compute', self.COMPUTE_ENGINE_API_VERSION)
    return self._gce_api_client

  def BlockOperation(self,
                     response: Dict[str, Any],
                     zone: Optional[str] = None) -> Dict[str, Any]:
    """Block until API operation is finished.

    Args:
      response (Dict): GCE API response.
      zone (str): Optional. GCP zone to execute the operation in. None means
          GlobalZone.

    Returns:
      Dict: Holding the response of a get operation on an API object of type
          zoneOperations or globalOperations.

    Raises:
      RuntimeError: If API call failed.
    """

    service = self.GceApi()
    while True:
      if zone:
        request = service.zoneOperations().get(
            project=self.project_id, zone=zone, operation=response['name'])
        result = request.execute()  # type: Dict[str, Any]
      else:
        request = service.globalOperations().get(
            project=self.project_id, operation=response['name'])
        result = request.execute()

      if 'error' in result:
        raise RuntimeError(result['error'])

      if result['status'] == 'DONE':
        return result
      time.sleep(5)  # Seconds between requests


def ExecuteRequest(client: 'googleapiclient.discovery.Resource',
                   func: str,
                   kwargs: Dict[str, str],
                   throttle: bool = False) -> List[Dict[str, Any]]:
  """Execute a request to the GCP API.

  Args:
    client (googleapiclient.discovery.Resource): A GCP client object.
    func (str): A GCP function to query from the client.
    kwargs (Dict): A dictionary of parameters for the function func.
    throttle (bool): A boolean indicating if requests should be throttled. This
        is necessary for some APIs (e.g. list logs) as there is an API rate
        limit. Default is False, i.e. requests are not throttled.

  Returns:
    List[Dict]: A List of dictionaries (responses from the request).

  Raises:
    RuntimeError: If the request to the GCP API could not complete.
  """

  responses = []
  next_token = None
  while True:
    if throttle:
      time.sleep(1)
    if next_token:
      kwargs['pageToken'] = next_token
    try:
      request = getattr(client, func)
      response = request(**kwargs).execute()
    except (RefreshError, DefaultCredentialsError) as exception:
      error_msg = (
          '{0:s}\n'
          'Something is wrong with your Application Default '
          'Credentials. Try running: '
          '$ gcloud auth application-default login'.format(str(exception)))
      raise RuntimeError(error_msg)
    responses.append(response)
    next_token = response.get('nextPageToken')
    if not next_token:
      return responses
