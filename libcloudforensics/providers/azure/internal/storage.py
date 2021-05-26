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
"""Azure Storage functionality."""

from typing import TYPE_CHECKING, Optional, Tuple

# pylint: disable=import-error
from azure.mgmt import storage
from msrestazure import azure_exceptions
# pylint: enable=import-error

from libcloudforensics import logging_utils
from libcloudforensics import errors
from libcloudforensics.providers.azure.internal import common

if TYPE_CHECKING:
  # TYPE_CHECKING is always False at runtime, therefore it is safe to ignore
  # the following cyclic import, as it it only used for type hints
  from libcloudforensics.providers.azure.internal import account  # pylint: disable=cyclic-import


logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)


class AZStorage:
  """Azure Storage functionality.

  Attributes:
    az_account (AZAccount): An Azure account object.
    storage_client (StorageManagementClient): An Azure storage client object.
  """

  def __init__(self,
               az_account: 'account.AZAccount') -> None:
    """Initialize the Azure storage class.

    Args:
      az_account (AZAccount): An Azure account object.
    """
    self.az_account = az_account
    self.storage_client = storage.StorageManagementClient(
        self.az_account.credentials, self.az_account.subscription_id)

  def CreateStorageAccount(self,
                           storage_account_name: str,
                           region: Optional[str] = None) -> Tuple[str, str]:
    """Create a storage account and returns its ID and access key.

    Args:
      storage_account_name (str): The name for the storage account.
      region (str): Optional. The region in which to create the storage
          account. If not provided, it will be created in the default_region
          associated to the AZAccount object.

    Returns:
      Tuple[str, str]: The storage account ID and its access key.

    Raises:
      InvalidNameError: If the storage account name is invalid.
    """

    if not common.REGEX_ACCOUNT_STORAGE_NAME.match(storage_account_name):
      raise errors.InvalidNameError(
          'Storage account name {0:s} does not comply with {1:s}'.format(
              storage_account_name, common.REGEX_ACCOUNT_STORAGE_NAME.pattern),
          __name__)

    if not region:
      region = self.az_account.default_region

    # https://docs.microsoft.com/en-us/rest/api/storagerp/srp_sku_types
    creation_data = {
        'location': region,
        'sku': {
            'name': 'Standard_RAGRS'
        },
        'kind': 'Storage'
    }

    # pylint: disable=line-too-long
    # https://docs.microsoft.com/en-us/samples/azure-samples/storage-python-manage/storage-python-manage/
    # https://docs.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-python
    # pylint: enable=line-too-long
    logger.info('Creating storage account: {0:s}'.format(storage_account_name))
    request = self.storage_client.storage_accounts.begin_create(
        self.az_account.default_resource_group_name,
        storage_account_name,
        creation_data
    )
    logger.info('Storage account {0:s} successfully created'.format(
        storage_account_name))
    storage_account = request.result()
    storage_account_keys = self.storage_client.storage_accounts.list_keys(
        self.az_account.default_resource_group_name, storage_account_name)
    storage_account_keys = {key.key_name: key.value
                            for key in storage_account_keys.keys}
    storage_account_id = storage_account.id  # type: str
    storage_account_key = storage_account_keys['key1']  # type: str
    return storage_account_id, storage_account_key

  def DeleteStorageAccount(self, storage_account_name: str) -> None:
    """Delete an account storage.

    Raises:
      ResourceDeletionError: if the storage account could not be deleted.
    """
    try:
      logger.info('Deleting storage account: {0:s}'.format(
          storage_account_name))
      self.storage_client.storage_accounts.delete(
          self.az_account.default_resource_group_name, storage_account_name)
      logger.info('Storage account {0:s} successfully deleted'.format(
          storage_account_name))
    except azure_exceptions.CloudError as exception:
      raise errors.ResourceDeletionError(
          'Could not delete account storage {0:s}: {1:s}'.format(
              storage_account_name, str(exception)), __name__) from exception
