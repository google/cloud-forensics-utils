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

from azure.identity import DefaultAzureCredential

from libcloudforensics import logging_utils
from libcloudforensics import errors

if TYPE_CHECKING:
  # TYPE_CHECKING is always False at runtime, therefore it is safe to ignore
  # the following cyclic import, as it it only used for type hints
  from libcloudforensics.providers.azure.internal import compute  # pylint: disable=cyclic-import

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)

# pylint: disable=line-too-long
# See https://docs.microsoft.com/en-us/azure/azure-resource-manager/management/resource-name-rules
# pylint: enable=line-too-long
REGEX_DISK_NAME = re.compile('^[\\w]{1,80}$')
REGEX_SNAPSHOT_NAME = re.compile('^(?=.{1,80}$)[a-zA-Z0-9]([\\w,-]*[\\w])?$')
REGEX_ACCOUNT_STORAGE_NAME = re.compile('^[a-z0-9]{1,24}$')
REGEX_COMPUTE_RESOURCE_ID = re.compile(
    '/subscriptions/.+/resourceGroups/.+/providers/Microsoft.Compute/.+/.+')

DEFAULT_DISK_COPY_PREFIX = 'evidence'

UBUNTU_1804_SKU = '18.04-LTS'


def _ParseCredentialsFile(profile_name: str) -> Dict[str, Any]:
  """Parse Azure credentials.json file.

  Args:
    profile_name (str): A name for the Azure account information to retrieve.
        The .json file should have the following format:

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
    Dict[str, str]: A dict containing the required account_info fields.

  Raises:
    CredentialsConfigurationError: If there are environment variables that
        are not set or if the credentials file has missing entries/profiles.
    FileNotFoundError: If the credentials file is not found.
    InvalidFileFormatError: If the credentials file couldn't be parsed.
  """
  path = os.getenv('AZURE_CREDENTIALS_PATH')
  if not path:
    path = os.path.expanduser('~/.azure/credentials.json')

  if not os.path.exists(path):
    raise FileNotFoundError(
        'Credentials file not found. Please place it in '
        '"~/.azure/credentials.json" or specify an absolute path to it in '
        'the AZURE_CREDENTIALS_PATH environment variable.')

  with open(path) as profiles:
    try:
      account_info: Dict[str, Any] = json.load(profiles).get(profile_name)
    except ValueError as exception:
      raise errors.InvalidFileFormatError(
          'Could not decode JSON file. Please verify the file format:'
          ' {0!s}'.format(exception), __name__) from exception
    if not account_info:
      raise errors.CredentialsConfigurationError(
          'Profile name {0:s} not found in credentials file {1:s}'.format(
              profile_name, path), __name__)
    required_entries = ['subscriptionId', 'clientId', 'clientSecret',
                        'tenantId']
    if not all(account_info.get(entry) for entry in required_entries):
      raise errors.CredentialsConfigurationError(
          'Please make sure that your JSON file has the required entries. The '
          'file should contain at least the following: {0:s}'.format(
              ', '.join(required_entries)), __name__)

  return account_info


def _CheckAzureCliCredentials() -> Optional[str]:
  """Test if AzureCliCredentials are configured, returning the subscription
  id if successful.

  Returns:
    str: the subscription_id of the credentials if properly configured or else
      None.

  Raises:
    CredentialsConfigurationError: If AzureCliCredentials are configured but
      the active subscription could not be determined.
  """
  tokens = None

  config_dir = os.getenv('AZURE_CONFIG_DIR')
  if not config_dir:
    config_dir = os.path.expanduser('~/.azure/')

  tokens_path = os.path.join(config_dir, 'accessTokens.json')
  profile_path = os.path.join(config_dir, 'azureProfile.json')

  if not os.path.exists(tokens_path) or not os.path.exists(profile_path):
    return None

  with open(tokens_path, encoding='utf-8-sig') as tokens_fd:
    tokens = json.load(tokens_fd)

  # If tokens are not found then Azure CLI auth is not configured.
  if not tokens:
    return None

  with open(profile_path, encoding='utf-8-sig') as profile_fd:
    profile = json.load(profile_fd)

    for subscription in profile['subscriptions']:
      if subscription['isDefault']:
        return str(subscription["id"])

    raise errors.CredentialsConfigurationError(
        'AzureCliCredentials tokens found but could not determine active '
        'subscription. No "isDefault" set in "{0:s}"'.format(config_dir),
        __name__)


def GetCredentials(profile_name: Optional[str] = None
                   ) -> Tuple[str, DefaultAzureCredential]:
  # pylint: disable=line-too-long
  """Get Azure credentials, trying three different methods:

  1. If profile_name is provided it will attempt to parse credentials from a
     credentials.json file, failing if this raises an exception.
  2. Environment variables as per
     https://docs.microsoft.com/en-us/azure/developer/python/azure-sdk-authenticate
  3. Azure CLI credentials.

  Args:
    profile_name (str): A name for the Azure account information to retrieve.
        If provided, then the library will look into ~/.azure/credentials.json
        for the account information linked to profile_name.

  Returns:
    Tuple[str, DefaultAzureCredential]: Subscription ID and
        corresponding Azure credentials.

  Raises:
    CredentialsConfigurationError: If none of the credential methods work.
  """
  # pylint: enable=line-too-long
  if profile_name:
    account_info = _ParseCredentialsFile(profile_name)
    # Set environment variables for DefaultAzureCredentials.
    os.environ['AZURE_SUBSCRIPTION_ID'] = account_info['subscriptionId']
    os.environ['AZURE_CLIENT_ID'] = account_info['clientId']
    os.environ['AZURE_CLIENT_SECRET'] = account_info['clientSecret']
    os.environ['AZURE_TENANT_ID'] = account_info['tenantId']

  # Check if environment variables are already set for DefaultAzureCredentials.
  subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')
  client_id = os.getenv("AZURE_CLIENT_ID")
  secret = os.getenv("AZURE_CLIENT_SECRET")
  tenant = os.getenv("AZURE_TENANT_ID")

  if not (subscription_id and client_id and secret and tenant):
    logger.info('EnvironmentCredentials unavailable, falling back to '
          'AzureCliCredentials.')
    # Will be automatically picked up by DefaultAzureCredential if configured.
    subscription_id = _CheckAzureCliCredentials()

  if not subscription_id:
    raise errors.CredentialsConfigurationError(
        'No supported credentials found. If using environment variables '
        'please make sure to define: [AZURE_SUBSCRIPTION_ID, AZURE_CLIENT_ID, '
        'AZURE_CLIENT_SECRET, AZURE_TENANT_ID].', __name__)

  return subscription_id, DefaultAzureCredential()


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


def GenerateDiskName(snapshot: 'compute.AZComputeSnapshot',
                     disk_name_prefix: Optional[str] = None) -> str:
  """Generate a new disk name for the disk to be created from the Snapshot.

  The disk name must comply with the following RegEx:
      - ^[\\w]{1-80}$

  i.e., it must be between 1 and 80 chars, and can only contain alphanumeric
  characters and underscores.

  Args:
    snapshot (AZComputeSnapshot): A disk's Snapshot.
    disk_name_prefix (str): Optional. A prefix for the disk name.

  Returns:
    str: A name for the disk.

  Raises:
    InvalidNameError: If the disk name does not comply with the RegEx.
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
    raise errors.InvalidNameError(
        'Disk name {0:s} does not comply with '
        '{1:s}'.format(disk_name, REGEX_DISK_NAME.pattern), __name__)

  return disk_name
