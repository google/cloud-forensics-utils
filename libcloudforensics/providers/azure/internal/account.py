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

from time import sleep
from typing import Optional, Dict

# Pylint complains about the import but the library imports just fine,
# so we can ignore the warning.
# pylint: disable=import-error
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.compute.v2016_04_30_preview.models import DiskCreateOption
from msrestazure.azure_exceptions import CloudError
# pylint: enable=import-error

from libcloudforensics.providers.azure.internal import compute, common


class AZAccount:
  """Class that represents an Azure Account.

  Attributes:
    subscription_id (str): The Azure subscription ID to use.
    credentials (ServicePrincipalCredentials): An Azure credentials object.
    compute_client (ComputeManagementClient): An Azure compute client object.
  """

  def __init__(self, subscription_id: str) -> None:
    """Initialize the AZAccount class.

    Args:
      subscription_id (str): The Azure subscription ID to use.
    """
    self.subscription_id = subscription_id
    self.credentials = common.GetCredentials()
    self.compute_client = ComputeManagementClient(
        self.credentials, self.subscription_id)

  def ListInstances(self,
                    resource_group_name: Optional[str] = None
                    ) -> Dict[str, compute.AZVirtualMachine]:
    """List instances in an Azure subscription / resource group.

    Args:
      resource_group_name (str): Optional. The resource group name to list
          instances from. If none specified, then all instances in the Azure
          subscription will be listed.

    Returns:
      Dict[str, AZVirtualMachine]: Dictionary mapping instance names (str) to
          their respective AZVirtualMachine object.
    """
    instances = {}  # type: Dict[str, compute.AZVirtualMachine]
    az_vm_client = self.compute_client.virtual_machines
    if not resource_group_name:
      responses = common.ExecuteRequest(az_vm_client, 'list_all')
    else:
      responses = common.ExecuteRequest(
          az_vm_client,
          'list',
          {'resource_group_name': resource_group_name})
    for response in responses:
      for instance in response:
        instances[instance.name] = compute.AZVirtualMachine(
            self,
            instance.id,
            instance.name,
            instance.location,
            zones=instance.zones)
    return instances

  def ListDisks(
      self,
      resource_group_name: Optional[str] = None) -> Dict[str, compute.AZDisk]:
    """List disks in an Azure subscription / resource group.

    Args:
      resource_group_name (str): Optional. The resource group name to list
          disks from. If none specified, then all disks in the AZ
          subscription will be listed.

    Returns:
      Dict[str, AZDisk]: Dictionary mapping disk names (str) to their
          respective AZDisk object.
    """
    disks = {}  # type: Dict[str, compute.AZDisk]
    az_disk_client = self.compute_client.disks
    if not resource_group_name:
      responses = common.ExecuteRequest(az_disk_client, 'list')
    else:
      responses = common.ExecuteRequest(
          az_disk_client,
          'list_by_resource_group',
          {'resource_group_name': resource_group_name})
    for response in responses:
      for disk in response:
        disks[disk.name] = compute.AZDisk(self,
                                          disk.id,
                                          disk.name,
                                          disk.location,
                                          zones=disk.zones)
    return disks

  def GetInstance(
      self,
      instance_name: str,
      resource_group_name: Optional[str] = None) -> compute.AZVirtualMachine:
    """Get instance from AZ subscription / resource group.

    Args:
      instance_name (str): The instance name.
      resource_group_name (str): Optional. The resource group name to look
          the instance in. If none specified, then the instance will be fetched
          from the AZ subscription.

    Returns:
      AZVirtualMachine: An Azure virtual machine object.

    Raises:
      RuntimeError: If the instance was not found in the subscription / resource
          group.
    """
    instances = self.ListInstances(resource_group_name=resource_group_name)
    if instance_name not in instances:
      error_msg = 'Instance {0:s} was not found in subscription {1:s}'.format(
          instance_name, self.subscription_id)
      raise RuntimeError(error_msg)
    return instances[instance_name]

  def GetDisk(
      self,
      disk_name: str,
      resource_group_name: Optional[str] = None) -> compute.AZDisk:
    """Get disk from AZ subscription / resource group.

    Args:
      disk_name (str): The disk name.
      resource_group_name (str): Optional. The resource group name to look
          the disk in. If none specified, then the disk will be fetched from
          the AZ subscription.

    Returns:
      AZDisk: An Azure Compute Disk object.

    Raises:
      RuntimeError: If the disk was not found in the subscription / resource
          group.
    """
    disks = self.ListDisks(resource_group_name=resource_group_name)
    if disk_name not in disks:
      error_msg = 'Disk {0:s} was not found in subscription {1:s}'.format(
          disk_name, self.subscription_id)
      raise RuntimeError(error_msg)
    return disks[disk_name]

  def CreateDiskFromSnapshot(
      self,
      snapshot: compute.AZSnapshot,
      disk_name: Optional[str] = None,
      disk_name_prefix: Optional[str] = None,
      disk_type: str = 'Standard_LRS') -> compute.AZDisk:
    """Create a new disk based on a Snapshot.

    Args:
      snapshot (AZSnapshot): Snapshot to use.
      disk_name (str): Optional. String to use as new disk name.
      disk_name_prefix (str): Optional. String to prefix the disk name with.
      disk_type (str): Optional. The sku name for the disk to create. Can be
          Standard_LRS, Premium_LRS, StandardSSD_LRS, or UltraSSD_LRS. The
          default value is Standard_LRS.

    Returns:
      AZDisk: Azure Compute Disk.

    Raises:
      RuntimeError: If the disk could not be created.
    """

    if not disk_name:
      disk_name = common.GenerateDiskName(snapshot,
                                          disk_name_prefix=disk_name_prefix)
    creation_data = {
        'location': snapshot.region,
        'creation_data': {
            'sourceResourceId': snapshot.resource_id,
            'create_option': DiskCreateOption.copy
        }
    }

    try:
      request = self.compute_client.disks.create_or_update(
          snapshot.resource_group_name,
          disk_name,
          creation_data,
          sku=disk_type)
      while not request.done():
        sleep(5)  # Wait 5 seconds before checking disk status again
      disk = request.result()
    except CloudError as exception:
      raise RuntimeError('Could not create disk from snapshot {0:s}: {1:s}'
                         .format(snapshot.resource_id, str(exception)))

    return compute.AZDisk(self,
                          disk.id,
                          disk.name,
                          disk.location,
                          disk.zones)
