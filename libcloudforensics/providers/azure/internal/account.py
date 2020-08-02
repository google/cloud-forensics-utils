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
"""Represents an Azure account."""

from typing import Optional

# pylint: disable=line-too-long
from libcloudforensics.providers.azure.internal import common
from libcloudforensics.providers.azure.internal import compute as compute_module
from libcloudforensics.providers.azure.internal import monitoring as monitoring_module
from libcloudforensics.providers.azure.internal import network as network_module
from libcloudforensics.providers.azure.internal import resource as resource_module
from libcloudforensics.providers.azure.internal import storage as storage_module
from libcloudforensics import logging_utils
# pylint: enable=line-too-long

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)


class AZAccount:
  """Class that represents an Azure Account.

  Attributes:
    subscription_id (str): The Azure subscription ID to use.
    credentials (ServicePrincipalCredentials): An Azure credentials object.
    default_region (str): The default region to create new resources in.
    default_resource_group_name (str): The default resource group in which to
          create new resources in.
  """

  def __init__(self,
               default_resource_group_name: str,
               default_region: str = 'eastus',
               profile_name: Optional[str] = None) -> None:
    """Initialize the AZAccount class.

    Args:
      default_resource_group_name (str): The default resource group in which to
          create new resources in. If the resource group does not exists,
          it will be automatically created.
      default_region (str): Optional. The default region to create new
          resources in. Default is eastus.
      profile_name (str): Optional. The name of the profile to use for Azure
          operations. For more information on profiles, see GetCredentials()
          in libcloudforensics.providers.azure.internal.common.py. Default
          does not use profiles and will authenticate to Azure using
          environment variables.
    """
    self.subscription_id, self.credentials = common.GetCredentials(profile_name)
    self.default_region = default_region
    self._compute = None  # type: Optional[compute_module.AZCompute]
    self._monitoring = None  # type: Optional[monitoring_module.AZMonitoring]
    self._network = None  # type: Optional[network_module.AZNetwork]
    self._resource = None  # type: Optional[resource_module.AZResource]
    self._storage = None  # type: Optional[storage_module.AZStorage]
    self.default_resource_group_name = self.resource.GetOrCreateResourceGroup(
        default_resource_group_name)

  @property
  def compute(self) -> compute_module.AZCompute:
    """Get an Azure compute object for the account.

    Returns:
      AZCompute: An Azure compute object.
    """
    if self._compute:
      return self._compute
    self._compute = compute_module.AZCompute(self)
    return self._compute

  @property
  def monitoring(self) -> monitoring_module.AZMonitoring:
    """Get an Azure monitoring object for the account.

    Returns:
      AZMonitoring: An Azure monitoring object.
    """
    if self._monitoring:
      return self._monitoring
    self._monitoring = monitoring_module.AZMonitoring(self)
    return self._monitoring

  @property
  def network(self) -> network_module.AZNetwork:
    """Get an Azure network object for the account.

    Returns:
      AZNetwork: An Azure network object.
    """
    if self._network:
      return self._network
    self._network = network_module.AZNetwork(self)
    return self._network

  @property
  def resource(self) -> resource_module.AZResource:
    """Get an Azure resource object for the account.

    Returns:
      AZResource: An Azure resource object.
    """
    if self._resource:
      return self._resource
    self._resource = resource_module.AZResource(self)
    return self._resource

  @property
  def storage(self) -> storage_module.AZStorage:
    """Get an Azure storage object for the account.

    Returns:
      AZStorage: An Azure storage object.
    """
    if self._storage:
      return self._storage
    self._storage = storage_module.AZStorage(self)
    return self._storage
