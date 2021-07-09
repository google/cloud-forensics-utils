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
"""Azure Networking functionality."""

from typing import TYPE_CHECKING, Optional, Tuple, Any, Dict

# pylint: disable=import-error
from azure.mgmt import network
from azure.core import exceptions as azure_exceptions
# pylint: enable=import-error

from libcloudforensics import errors
from libcloudforensics.providers.azure.internal import common

if TYPE_CHECKING:
  # TYPE_CHECKING is always False at runtime, therefore it is safe to ignore
  # the following cyclic import, as it it only used for type hints
  from libcloudforensics.providers.azure.internal import account  # pylint: disable=cyclic-import


class AZNetwork:
  """Azure Networking functionality.

  Attributes:
    az_account (AZAccount): An Azure account object.
    network_client (NetworkManagementClient): An Azure network client object.
  """

  def __init__(self,
               az_account: 'account.AZAccount') -> None:
    """Initialize the Azure network class.

    Args:
      az_account (AZAccount): An Azure account object.
    """
    self.az_account = az_account
    self.network_client = network.NetworkManagementClient(
        self.az_account.credentials, self.az_account.subscription_id)

  def CreateNetworkInterface(self,
                             name: str,
                             region: Optional[str] = None) -> str:
    """Create a network interface and returns its ID.

    Args:
      name (str): The name of the network interface.
      region (str): Optional. The region in which to create the network
          interface. Default uses default_region of the AZAccount object.

    Returns:
      str: The id of the created network interface.

    Raises:
      ValueError: if name is not provided.
      ResourceCreationError: If no network interface could be created.
    """
    if not name:
      raise ValueError('name must be specified. Provided: {0!s}'.format(name))

    if not region:
      region = self.az_account.default_region

    network_interface_name = '{0:s}-nic'.format(name)
    ip_config_name = '{0:s}-ipconfig'.format(name)

    # Check if the network interface already exists, and returns its ID if so.
    try:
      nic = self.network_client.network_interfaces.get(
          self.az_account.default_resource_group_name, network_interface_name)
      nic_id = nic.id  # type: str
      return nic_id
    except azure_exceptions.ResourceNotFoundError as exception:
      # NIC doesn't exist, ignore the error as we create it later on.
      pass
    except azure_exceptions.AzureError as exception:
      raise errors.ResourceCreationError(
          'Could not create network interface: {0!s}'.format(exception),
          __name__) from exception

    # pylint: disable=unbalanced-tuple-unpacking
    # IP address, virtual network, subnet, network security group
    public_ip, _, subnet, nsg = self._CreateNetworkInterfaceElements(
        name, region=region)
    # pylint: enable=unbalanced-tuple-unpacking

    creation_data = {
        'location': region,
        'ip_configurations': [{
            'name': ip_config_name,
            'public_ip_address': public_ip,
            'subnet': {
                'id': subnet.id
            }
        }],
        'networkSecurityGroup': nsg
    }

    try:
      request = self.network_client.network_interfaces.begin_create_or_update(
          self.az_account.default_resource_group_name,
          network_interface_name,
          creation_data)
      request.wait()
    except azure_exceptions.AzureError as exception:
      raise errors.ResourceCreationError(
          'Could not create network interface: {0!s}'.format(exception),
          __name__) from exception

    network_interface_id = request.result().id  # type: str
    return network_interface_id

  def _CreateNetworkInterfaceElements(
      self,
      name_prefix: str,
      region: Optional[str] = None) -> Tuple[Any, ...]:
    """Creates required elements for creating a network interface.

    Args:
      name_prefix (str): A name prefix to use for the network interface
          elements to create.
      region (str): Optional. The region in which to create the elements.
          Default uses default_region of the AZAccount object.

    Returns:
      Tuple[Any, Any, Any, Any]: A tuple containing a public IP address object,
          a virtual network object, a subnet object and a network security
          group object.

    Raises:
      ResourceCreationError: If the elements could not be created.
    """

    if not region:
      region = self.az_account.default_region

    # IP address
    public_ip_name = '{0:s}-public-ip'.format(name_prefix)
    # Virtual Network
    vnet_name = '{0:s}-vnet'.format(name_prefix)
    # Subnet
    subnet_name = '{0:s}-subnet'.format(name_prefix)
    # Network security group
    nsg_name = '{0:s}-nsg'.format(name_prefix)

    client_to_creation_data = {
        self.network_client.public_ip_addresses: {
            'resource_group_name': self.az_account.default_resource_group_name,
            'public_ip_address_name': public_ip_name,
            'parameters': {
                'location': region,
                'public_ip_allocation_method': 'Dynamic'
            }
        },
        self.network_client.virtual_networks: {
            'resource_group_name': self.az_account.default_resource_group_name,
            'virtual_network_name': vnet_name,
            'parameters': {
                'location': region,
                'address_space': {'address_prefixes': ['10.0.0.0/16']}
            }
        },
        self.network_client.subnets: {
            'resource_group_name': self.az_account.default_resource_group_name,
            'virtual_network_name': vnet_name,
            'subnet_name': subnet_name,
            'subnet_parameters': {'address_prefix': '10.0.0.0/24'}
        },
        self.network_client.network_security_groups: {
            'resource_group_name': self.az_account.default_resource_group_name,
            'network_security_group_name': nsg_name,
            'parameters': {
                'location': region,
                # Allow SSH traffic
                'security_rules': [{
                    'name': 'Allow-SSH',
                    'direction': 'Inbound',
                    'protocol': 'TCP',
                    'source_address_prefix': '*',
                    'destination_address_prefix': '*',
                    'source_port_range': '*',
                    'destination_port_range': 22,
                    'access': 'Allow',
                    'priority': 300
                }]
            }
        }
    }  # type: Dict[str, Any]

    result = []
    try:
      for client, data in client_to_creation_data.items():
        request = common.ExecuteRequest(
            client,
            'begin_create_or_update',
            data)[0]
        request.wait()
        result.append(request.result())
    except azure_exceptions.AzureError as exception:
      raise errors.ResourceCreationError(
          'Could not create network interface elements: {0!s}'.format(
              exception), __name__) from exception
    return tuple(result)
