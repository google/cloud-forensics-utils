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
"""Azure Compute Resources."""

from time import sleep
from typing import Optional, List, Dict, TYPE_CHECKING

# Pylint complains about the import but the library imports just fine,
# so we can ignore the warning.
# pylint: disable=import-error
from azure.mgmt.compute.v2020_05_01 import models
from msrestazure import azure_exceptions
# pylint: enable=import-error

from libcloudforensics import logging_utils
from libcloudforensics.providers.azure.internal import common

if TYPE_CHECKING:
  # TYPE_CHECKING is always False at runtime, therefore it is safe to ignore
  # the following cyclic import, as it it only used for type hints
  from libcloudforensics.providers.azure.internal import account  # pylint: disable=cyclic-import

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)


class AZComputeResource:
  """Class that represent an Azure compute resource

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
    """

    self.az_account = az_account
    # Format of resource_id: /subscriptions/{id}/resourceGroups/{
    # resource_group_name}/providers/Microsoft.Compute/{resourceType}/{resource}
    self.resource_group_name = resource_id.split('/')[4]
    self.resource_id = resource_id
    self.name = name
    self.region = region
    self.zones = zones


class AZVirtualMachine(AZComputeResource):
  """Class that represents Azure virtual machines."""

  def __init__(self,
               az_account: 'account.AZAccount',
               resource_id: str,
               name: str,
               region: str,
               zones: Optional[List[str]] = None) -> None:
    """Initialize the AZVirtualMachine class.

    Args:
      az_account (AZAccount): An Azure account object.
      resource_id (str): The Azure ID of the virtual machine.
      name (str): The virtual machine's name.
      region (str): The region in which the virtual machine is located.
      zones (List[str]): Optional. Availability zones within the region where
          the virtual machine is located / replicated.
    """
    super(AZVirtualMachine, self).__init__(az_account,
                                           resource_id,
                                           name,
                                           region,
                                           zones=zones)

  def GetBootDisk(self) -> 'AZDisk':
    """Get the instance's boot disk.

    Returns:
      AZDisk: Disk object if the disk is found.

    Raises:
      RuntimeError: If no boot disk could be found.
    """
    disks = self.az_account.ListDisks(
        resource_group_name=self.resource_group_name)  # type: Dict[str, AZDisk]
    boot_disk_name = self.az_account.compute_client.virtual_machines.get(
        self.resource_group_name, self.name).storage_profile.os_disk.name
    if boot_disk_name not in disks:
      error_msg = 'Boot disk not found for instance: {0:s}'.format(
          self.resource_id)
      raise RuntimeError(error_msg)
    return disks[boot_disk_name]

  def GetDisk(self, disk_name: str) -> 'AZDisk':
    """Get a disk attached to the instance by ID.

    Args:
      disk_name (str): The ID of the disk to get.

    Returns:
      AZDisk: The disk object.

    Raises:
      RuntimeError: If disk_name is not found amongst the disks attached
          to the instance.
    """
    disks = self.ListDisks()
    if disk_name not in disks:
      error_msg = 'Disk {0:s} not found in instance: {1:s}'.format(
          disk_name, self.resource_id)
      raise RuntimeError(error_msg)
    return disks[disk_name]

  def ListDisks(self) -> Dict[str, 'AZDisk']:
    """List all disks for the instance.

    Returns:
      Dict[str, AZDisk]: Dictionary mapping disk names to their respective
          AZDisk object.
    """
    disks = self.az_account.ListDisks(
        resource_group_name=self.resource_group_name)
    vm_disks = self.az_account.compute_client.virtual_machines.get(
        self.resource_group_name, self.name).storage_profile
    vm_disks_names = [disk.name for disk in vm_disks.data_disks]
    vm_disks_names.append(vm_disks.os_disk.name)
    return {disk_name: disks[disk_name] for disk_name in vm_disks_names}


class AZDisk(AZComputeResource):
  """Class that represents Azure disks."""

  def __init__(self,
               az_account: 'account.AZAccount',
               resource_id: str,
               name: str,
               region: str,
               zones: Optional[List[str]] = None) -> None:
    """Initialize the AZDisk class.

    Args:
      az_account (AZAccount): An Azure account object.
      resource_id (str): The Azure ID of the disk.
      name (str): The disk name.
      region (str): The region in which the disk is located.
      zones (List[str]): Optional. Availability zone within the region where
          the disk is located.
    """
    super(AZDisk, self).__init__(az_account,
                                 resource_id,
                                 name,
                                 region,
                                 zones=zones)

  def Snapshot(self,
               snapshot_name: Optional[str] = None,
               tags: Optional[Dict[str, str]] = None) -> 'AZSnapshot':
    """Create a snapshot of the disk.

    Args:
      snapshot_name (str): Optional. A name for the snapshot. If none
          provided, one will be generated based on the disk's name.
      tags (Dict[str, str]): Optional. A dictionary of tags to add to the
          snapshot, for example {'TicketID': 'xxx'}.

    Returns:
      AZSnapshot: A snapshot object.

    Raises:
      ValueError: If the snapshot name does not comply with the RegEx.
      RuntimeError: If the snapshot could not be created.
    """

    if not snapshot_name:
      snapshot_name = self.name + '_snapshot'
      truncate_at = 80 - 1
      snapshot_name = snapshot_name[:truncate_at]
      if not common.REGEX_SNAPSHOT_NAME.match(snapshot_name):
        raise ValueError('Snapshot name {0:s} does not comply with '
                         '{1:s}'.format(snapshot_name,
                                        common.REGEX_SNAPSHOT_NAME.pattern))

    creation_data = {
        'location': self.region,
        'creation_data': {
            'sourceResourceId': self.resource_id,
            'create_option': models.DiskCreateOption.copy
        }
    }

    if tags:
      creation_data['tags'] = tags

    try:
      logger.info('Creating snapshot: {0:s}'.format(snapshot_name))
      request = self.az_account.compute_client.snapshots.create_or_update(
          self.resource_group_name,
          snapshot_name,
          creation_data)
      while not request.done():
        sleep(5)  # Wait 5 seconds before checking snapshot status again
      snapshot = request.result()
      logger.info('Snapshot {0:s} successfully created'.format(snapshot_name))
    except azure_exceptions.CloudError as exception:
      raise RuntimeError('Could not create snapshot for disk {0:s}: {1:s}'
                         .format(self.resource_id, str(exception)))

    return AZSnapshot(self.az_account,
                      snapshot.id,
                      snapshot.name,
                      snapshot.location,
                      self)


class AZSnapshot(AZComputeResource):
  """Class that represents Azure snapshots.

  Attributes:
    disk (AZDisk): The disk from which the snapshot was taken.
  """

  def __init__(self,
               az_account: 'account.AZAccount',
               resource_id: str,
               name: str,
               region: str,
               source_disk: AZDisk) -> None:
    """Initialize the AZDisk class.

    Args:
      az_account (AZAccount): An Azure account object.
      resource_id (str): The Azure ID of the snapshot.
      name (str): The snapshot name.
      region (str): The region in which the snapshot is located.
      source_disk (AZDisk): The disk from which the snapshot was taken.
    """
    super(AZSnapshot, self).__init__(az_account,
                                     resource_id,
                                     name,
                                     region)

    self.disk = source_disk

  def Delete(self) -> None:
    """Delete a snapshot."""

    try:
      logger.info('Deleting snapshot: {0:s}'.format(self.name))
      request = self.az_account.compute_client.snapshots.delete(
          self.resource_group_name, self.name)
      while not request.done():
        sleep(5)  # Wait 5 seconds before checking snapshot status again
      logger.info('Snapshot {0:s} successfully deleted.'.format(self.name))
    except azure_exceptions.CloudError as exception:
      raise RuntimeError('Could not delete snapshot {0:s}: {1:s}'
                         .format(self.resource_id, str(exception)))

  def GrantAccessAndGetURI(self) -> str:
    """Grant access to a snapshot and return its access URI.

    Returns:
      str: The access URI for the snapshot.
    """
    logger.info('Generating SAS URI for snapshot: {0:s}'.format(self.name))
    access_request = self.az_account.compute_client.snapshots.grant_access(
        self.resource_group_name, self.name, 'Read', 3600)
    snapshot_uri = access_request.result().access_sas  # type: str
    logger.info('SAS URI generated: {0:s}'.format(snapshot_uri))
    return snapshot_uri

  def RevokeAccessURI(self) -> None:
    """Revoke access to a snapshot."""
    logger.info('Revoking SAS URI for snapshot {0:s}'.format(self.name))
    request = self.az_account.compute_client.snapshots.revoke_access(
        self.resource_group_name, self.name)
    request.wait()
    logger.info('SAS URI revoked for snapshot {0:s}'.format(self.name))
