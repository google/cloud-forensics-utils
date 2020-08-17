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
"""Azure Compute Base Resource."""

from typing import Optional, List, TYPE_CHECKING

from azure.mgmt import compute as compute_sdk  # pylint: disable=import-error

from libcloudforensics import errors
from libcloudforensics.providers.azure.internal import common

if TYPE_CHECKING:
  # TYPE_CHECKING is always False at runtime, therefore it is safe to ignore
  # the following cyclic import, as it it only used for type hints
  from libcloudforensics.providers.azure.internal import account  # pylint: disable=cyclic-import, ungrouped-imports


class AZComputeResource:
  """Class that represent an Azure compute resource.

  Attributes:
    az_account (AZAccount): An Azure account object.
    resource_group_name (str): The Azure resource group name for the resource.
    resource_id (str): The Azure resource ID.
    name (str): The resource's name.
    region (str): The region in which the resource is located.
    zones (List[str]): Optional. Availability zones within the region where
        the resource is located.
  """

  def __init__(self,
               az_account: 'account.AZAccount',
               resource_id: str,
               name: str,
               region: str,
               zones: Optional[List[str]] = None) -> None:
    """Initialize the AZComputeResource class.

    Args:
      az_account (AZAccount): An Azure account object.
      resource_id (str): The Azure resource ID.
      name (str): The resource's name.
      region (str): The region in which the resource is located.
      zones (List[str]): Optional. Availability zones within the region where
          the resource is located.

    Raises:
      InvalidNameError: If the resource ID is malformed.
    """

    if not common.REGEX_COMPUTE_RESOURCE_ID.match(resource_id):
      raise errors.InvalidNameError(
          'Malformed resource ID: expected {0:s}, got {1:s}'.format(
              common.REGEX_COMPUTE_RESOURCE_ID.pattern, resource_id), __name__)

    self.az_account = az_account
    # Format of resource_id: /subscriptions/{id}/resourceGroups/{
    # resource_group_name}/providers/Microsoft.Compute/{resourceType}/{resource}
    self.resource_group_name = resource_id.split('/')[4]
    self.resource_id = resource_id
    self.name = name
    self.region = region
    self.zones = zones

  @property
  def compute_client(self) -> compute_sdk.ComputeManagementClient:
    """Return the Azure compute client object associated to the Azure
        account.

    Returns:
      ComputeManagementClient: An Azure compute client object.
    """
    return self.az_account.compute.compute_client
