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
import json
import os
import re

from typing import Any, List, Dict, Optional, TYPE_CHECKING, Tuple
# Pylint complains about the import but the library imports just fine,
# so we can ignore the warning.
from azure.common.credentials import ServicePrincipalCredentials  # pylint: disable=import-error

if TYPE_CHECKING:
  # TYPE_CHECKING is always False at runtime, therefore it is safe to ignore
  # the following cyclic import, as it it only used for type hints
  from libcloudforensics.providers.azure.internal import compute  # pylint: disable=cyclic-import

# pylint: disable=line-too-long
# See https://docs.microsoft.com/en-us/azure/azure-resource-manager/management/resource-name-rules
# pylint: enable=line-too-long
REGEX_DISK_NAME = re.compile('^[\\w]{1,80}$')
REGEX_SNAPSHOT_NAME = re.compile('^(?=.{1,80}$)[a-zA-Z0-9]([\\w,-]*[\\w])?$')
REGEX_ACCOUNT_STORAGE_NAME = re.compile('^[a-z0-9]{1,24}$')

DEFAULT_DISK_COPY_PREFIX = 'evidence'


def GetCredentials(profile_name: Optional[str] = None
                   ) -> Tuple[str, ServicePrincipalCredentials]:
  # pylint: disable=line-too-long
  """Get Azure credentials.

  Args:
    profile_name (str): A name for the Azure account information to retrieve.
        If not provided, the default behavior is to look for Azure credential
        information in environment variables as explained in https://docs.microsoft.com/en-us/azure/developer/python/azure-sdk-authenticate
        If provided, then the library will look into
        ~/.azure/credentials.json for the account information linked to
        profile_name. The .json file should have the following format:

        {
          'profile_name': {
              'subscriptionId': xxx,
              'tenantId': xxx,
              'clientId': xxx,
              'clientSecret': xxx
          },
          'other_profile_name': {
              'subscriptionId': yyy,
              'tenantId': yyy,
              'clientId': yyy,
              'clientSecret': yyy
          },
          ...
        }

        Note that you can specify several profiles that use the same tenantId,
        clientId and clientSecret but a different subscriptionId.
        If you set the environment variable AZURE_CREDENTIALS_PATH to an
        absolute path to the credentials file, then the library will look
        there instead of in ~/.azure/credentials.json.

  Returns:
    Tuple[str, ServicePrincipalCredentials]: Subscription ID and
        corresponding Azure credentials.

  Raises:
    RuntimeError: If the credential file is not found.
    ValueError: If the requested profile name is not found in the credential
        file or if there are missing entries in the profile name.
  """
  # pylint: enable=line-too-long
  if not profile_name:
    subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')
    client_id = os.getenv("AZURE_CLIENT_ID")
    secret = os.getenv("AZURE_CLIENT_SECRET")
    tenant = os.getenv("AZURE_TENANT_ID")
    if not (subscription_id and client_id and secret and tenant):
      raise RuntimeError('Please make sure you defined the following '
                         'environment variables: [AZURE_SUBSCRIPTION_ID,'
                         'AZURE_CLIENT_ID, AZURE_CLIENT_SECRET,'
                         'AZURE_TENANT_ID].')
    return subscription_id, ServicePrincipalCredentials(client_id,
                                                        secret,
                                                        tenant=tenant)

  path = os.getenv('AZURE_CREDENTIALS_PATH')
  if not path:
    path = os.path.expanduser('~/.azure/credentials.json')

  if not os.path.exists(path):
    raise RuntimeError('Credential files not found. Please place it in '
                       '"~/.azure/credentials.json" or specify an absolute '
                       'path to it in the AZURE_CREDENTIALS_PATH environment '
                       'variable.')

  with open(path) as profiles:
    try:
      account_info = json.load(profiles).get(profile_name)
    except ValueError as exception:
      raise ValueError('Could not decode JSON file. Please verify the file '
                       'format: {0:s}'.format(str(exception)))
    if not account_info:
      raise ValueError(
          'Profile name {0:s} not found in credentials file {1:s}'.format(
              profile_name, path))
    required_entries = ['subscriptionId', 'clientId', 'clientSecret',
                        'tenantId']
    if not all(account_info.get(entry) for entry in required_entries):
      raise ValueError(
          'Please make sure that your JSON file has the required entries. The '
          'file should contain at least the following: {0:s}'.format(
              ', '.join(required_entries)))
    return account_info['subscriptionId'], ServicePrincipalCredentials(
        account_info['clientId'],
        account_info['clientSecret'],
        tenant=account_info['tenantId'])


def ExecuteRequest(
    client: Any,
    func: str,
    kwargs: Optional[Dict[str, str]] = None) -> List[Any]:
  """Execute a request to the Azure API.

  Args:
    client (Any): An Azure operation client object.
    func (str): An Azure function to query from the client.
    kwargs (Dict): Optional. A dictionary of parameters for the function func.

  Returns:
    List[Any]: A List of Azure response objects (VirtualMachines, Disks, etc).

  Raises:
    RuntimeError: If the request to the Azure API could not complete.
  """

  if not kwargs:
    kwargs = {}

  responses = []
  next_link = ''
  while True:
    if next_link:
      kwargs['next_link'] = next_link
    request = getattr(client, func)
    response = request(**kwargs)
    responses.append(response)
    next_link = response.next_link if hasattr(response, 'next_link') else None
    if not next_link:
      return responses


def GenerateDiskName(snapshot: 'compute.AZSnapshot',
                     disk_name_prefix: Optional[str] = None) -> str:
  """Generate a new disk name for the disk to be created from the Snapshot.

  The disk name must comply with the following RegEx:
      - ^[\\w]{1-80}$

  i.e., it must be between 1 and 80 chars, and can only contain alphanumeric
  characters and underscores.

  Args:
    snapshot (AZSnapshot): A disk's Snapshot.
    disk_name_prefix (str): Optional. A prefix for the disk name.

  Returns:
    str: A name for the disk.

  Raises:
    ValueError: If the disk name does not comply with the RegEx.
  """

  # Max length of disk names in Azure is 80 characters
  subscription_id = snapshot.az_account.subscription_id
  disk_id = subscription_id + snapshot.disk.resource_id
  disk_id_crc32 = '{0:08x}'.format(
      binascii.crc32(disk_id.encode()) & 0xffffffff)
  truncate_at = 80 - len(disk_id_crc32) - len('_copy') - 1
  if disk_name_prefix:
    disk_name_prefix += '_'
    if len(disk_name_prefix) > truncate_at:
      # The disk name prefix is too long
      disk_name_prefix = disk_name_prefix[:truncate_at]
    truncate_at -= len(disk_name_prefix)
    disk_name = '{0:s}{1:s}_{2:s}_copy'.format(
        disk_name_prefix, snapshot.name[:truncate_at], disk_id_crc32)
  else:
    disk_name = '{0:s}_{1:s}_copy'.format(
        snapshot.name[:truncate_at], disk_id_crc32)
  # Azure doesn't allow dashes in disk names, only underscores. If the
  # name of the source snapshot contained dashes, we need to replace them.
  disk_name = disk_name.replace('-', '_')
  if not REGEX_DISK_NAME.match(disk_name):
    raise ValueError(
        'Disk name {0:s} does not comply with '
        '{1:s}'.format(disk_name, REGEX_DISK_NAME.pattern))

  return disk_name
