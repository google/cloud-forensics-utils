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
"""Azure Resource functionality."""

from typing import TYPE_CHECKING, List

# pylint: disable=import-error
from azure.mgmt import resource
from msrestazure import azure_exceptions
# pylint: enable=import-error

from libcloudforensics import logging_utils

if TYPE_CHECKING:
  # TYPE_CHECKING is always False at runtime, therefore it is safe to ignore
  # the following cyclic import, as it it only used for type hints
  from libcloudforensics.providers.azure.internal import account  # pylint: disable=cyclic-import


logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)


class AZResource:
  """Azure resource functionality.

  Attributes:
    az_account (AZAccount): An Azure account object.
    resource_client (ResourceManagementClient): An Azure resource client object.
    subscription_client (SubscriptionClient): An Azure subscription client
        object.
  """

  def __init__(self,
               az_account: 'account.AZAccount') -> None:
    """Initialize the Azure resource class.

    Args:
      az_account (AZAccount): An Azure account object.
    """
    self.az_account = az_account
    self.resource_client = resource.ResourceManagementClient(
        self.az_account.credentials, self.az_account.subscription_id)
    self.subscription_client = resource.SubscriptionClient(
        self.az_account.credentials)

  def GetOrCreateResourceGroup(self, resource_group_name: str) -> str:
    """Check if a resource group exists, and create it otherwise.

    Args:
      resource_group_name (str); The name of the resource group to check
          existence for. If it does not exist, create it.

    Returns:
      str: The resource group name.
    """
    try:
      self.resource_client.resource_groups.get(resource_group_name)
    except azure_exceptions.CloudError:
      # Group doesn't exist, creating it
      logger.info('Resource group {0:s} not found, creating it.'.format(
          resource_group_name))
      creation_data = {
          'location': self.az_account.default_region
      }
      self.resource_client.resource_groups.create_or_update(
          resource_group_name, creation_data)
      logger.info('Resource group {0:s} successfully created.'.format(
          resource_group_name))
    return resource_group_name

  def ListSubscriptionIDs(self) -> List[str]:
    """List subscription ids from an Azure account.

    Returns:
      List[str]: A list of all subscription IDs from the Azure account.
    """
    subscription_ids = self.subscription_client.subscriptions.list()
    return [sub.subscription_id for sub in subscription_ids]
