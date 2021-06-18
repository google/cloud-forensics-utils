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
"""Azure Compute functionality."""

import base64
import hashlib
from time import sleep
from typing import Optional, List, Dict, TYPE_CHECKING, Tuple, Any

# Pylint complains about the import but the library imports just fine,
# so we can ignore the warning.
# pylint: disable=import-error
import sshpubkeys
from msrestazure import azure_exceptions
from azure.storage import blob
from azure.core import exceptions
from azure.mgmt import compute as compute_sdk
from azure.mgmt.compute.v2020_05_01 import models
# pylint: enable=import-error

from libcloudforensics import logging_utils
from libcloudforensics import errors
from libcloudforensics.providers.azure.internal import compute_base_resource  # pylint: disable=line-too-long, ungrouped-imports
from libcloudforensics.providers.azure.internal import common  # pylint: disable=line-too-long, ungrouped-imports

from libcloudforensics.scripts import utils

if TYPE_CHECKING:
  # TYPE_CHECKING is always False at runtime, therefore it is safe to ignore
  # the following cyclic import, as it it only used for type hints
  from libcloudforensics.providers.azure.internal import account  # pylint: disable=cyclic-import

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)


class AZCompute:
  """Class representing all Azure Compute objects in an account.

  Attributes:
    az_account: An Azure account object.
    compute_client (ComputeManagementClient): An Azure compute client object.
  """
  def __init__(self, az_account: 'account.AZAccount') -> None:
    """Initialize the AZCompute class.

    Args:
      az_account (AZAccount): An Azure account object.
    """
    self.az_account = az_account
    self.compute_client = compute_sdk.ComputeManagementClient(
        self.az_account.credentials,
        self.az_account.subscription_id
    )  # type: compute_sdk.ComputeManagementClient

  def ListInstances(self,
                    resource_group_name: Optional[str] = None
                    ) -> Dict[str, 'AZComputeVirtualMachine']:
    """List instances in an Azure subscription / resource group.

    Args:
      resource_group_name (str): Optional. The resource group name to list
          instances from. If none specified, then all instances in the Azure
          subscription will be listed.

    Returns:
      Dict[str, AZComputeVirtualMachine]: Dictionary mapping instance names
          (str) to their respective AZComputeVirtualMachine object.
    """
    instances = {}  # type: Dict[str, AZComputeVirtualMachine]
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
        instances[instance.name] = AZComputeVirtualMachine(
            self.az_account,
            instance.id,
            instance.name,
            instance.location,
            zones=instance.zones)
    return instances

  def ListDisks(
      self,
      resource_group_name: Optional[str] = None) -> Dict[str, 'AZComputeDisk']:
    """List disks in an Azure subscription / resource group.

    Args:
      resource_group_name (str): Optional. The resource group name to list
          disks from. If none specified, then all disks in the AZ
          subscription will be listed.

    Returns:
      Dict[str, AZComputeDisk]: Dictionary mapping disk names (str) to their
          respective AZComputeDisk object.
    """
    disks = {}  # type: Dict[str, AZComputeDisk]
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
        disks[disk.name] = AZComputeDisk(self.az_account,
                                         disk.id,
                                         disk.name,
                                         disk.location,
                                         zones=disk.zones)
    return disks

  def GetInstance(
      self,
      instance_name: str,
      resource_group_name: Optional[str] = None) -> 'AZComputeVirtualMachine':
    """Get instance from AZ subscription / resource group.

    Args:
      instance_name (str): The instance name.
      resource_group_name (str): Optional. The resource group name to look
          the instance in. If none specified, then the instance will be fetched
          from the AZ subscription.

    Returns:
      AZComputeVirtualMachine: An Azure virtual machine object.

    Raises:
      ResourceNotFoundError: If the instance was not found in the subscription/
          resource group.
    """
    instances = self.ListInstances(resource_group_name=resource_group_name)
    if instance_name not in instances:
      raise errors.ResourceNotFoundError(
          'Instance {0:s} was not found in subscription {1:s}'.format(
              instance_name, self.az_account.subscription_id), __name__)
    return instances[instance_name]

  def GetDisk(
      self,
      disk_name: str,
      resource_group_name: Optional[str] = None) -> 'AZComputeDisk':
    """Get disk from AZ subscription / resource group.

    Args:
      disk_name (str): The disk name.
      resource_group_name (str): Optional. The resource group name to look
          the disk in. If none specified, then the disk will be fetched from
          the AZ subscription.

    Returns:
      AZComputeDisk: An Azure Compute Disk object.

    Raises:
      ResourceNotFoundError: If the disk was not found in the subscription/
          resource group.
    """
    disks = self.ListDisks(resource_group_name=resource_group_name)
    if disk_name not in disks:
      raise errors.ResourceNotFoundError(
          'Disk {0:s} was not found in subscription {1:s}'.format(
              disk_name, self.az_account.subscription_id), __name__)
    return disks[disk_name]

  def CreateDiskFromSnapshot(
      self,
      snapshot: 'AZComputeSnapshot',
      region: Optional[str] = None,
      disk_name: Optional[str] = None,
      disk_name_prefix: Optional[str] = None,
      disk_type: str = 'Standard_LRS') -> 'AZComputeDisk':
    """Create a new disk based on a Snapshot.

    Args:
      snapshot (AZComputeSnapshot): Snapshot to use.
      region (str): Optional. The region in which to create the disk. If not
          provided, the disk will be created in the default_region associated to
          the AZAccount object.
      disk_name (str): Optional. String to use as new disk name.
      disk_name_prefix (str): Optional. String to prefix the disk name with.
      disk_type (str): Optional. The sku name for the disk to create. Can be
          Standard_LRS, Premium_LRS, StandardSSD_LRS, or UltraSSD_LRS. The
          default value is Standard_LRS.

    Returns:
      AZComputeDisk: Azure Compute Disk.

    Raises:
      ResourceCreationError: If the disk could not be created.
    """

    if not disk_name:
      disk_name = common.GenerateDiskName(snapshot,
                                          disk_name_prefix=disk_name_prefix)

    if not region:
      region = self.az_account.default_region

    creation_data = {
        'location': region,
        'creation_data': {
            'sourceResourceId': snapshot.resource_id,
            'create_option': models.DiskCreateOption.copy
        },
        'sku': {'name': disk_type}
    }

    try:
      logger.info('Creating disk: {0:s}'.format(disk_name))
      request = self.compute_client.disks.begin_create_or_update(
          self.az_account.default_resource_group_name,
          disk_name,
          creation_data)
      while not request.done():
        sleep(5)  # Wait 5 seconds before checking disk status again
      disk = request.result()
      logger.info('Disk {0:s} successfully created'.format(disk_name))
    except azure_exceptions.CloudError as exception:
      raise errors.ResourceCreationError(
          'Could not create disk from snapshot {0:s}: {1!s}'.format(
              snapshot.resource_id, exception), __name__) from exception

    return AZComputeDisk(self.az_account,
                         disk.id,
                         disk.name,
                         disk.location,
                         disk.zones)

  def CreateDiskFromSnapshotURI(
      self,
      snapshot: 'AZComputeSnapshot',
      snapshot_uri: str,
      region: Optional[str] = None,
      disk_name: Optional[str] = None,
      disk_name_prefix: Optional[str] = None,
      disk_type: str = 'Standard_LRS') -> 'AZComputeDisk':
    """Create a new disk based on a SAS snapshot URI.

    This is useful if e.g. one wants to make a copy of a disk in a separate
    Azure account. This method will create a temporary Azure Storage account
    within the destination account, import the snapshot from a downloadable
    link (the source account needs to share the snapshot through a SAS link)
    and then create a disk from the VHD file saved in storage. The Azure
    storage account is then deleted.

    Args:
      snapshot (AZComputeSnapshot): Source snapshot to use.
      snapshot_uri (str): The URI of the snapshot to copy.
      region (str): Optional. The region in which to create the disk. If not
          provided, the disk will be created in the default_region associated to
          the AZAccount object.
      disk_name (str): Optional. String to use as new disk name.
      disk_name_prefix (str): Optional. String to prefix the disk name with.
      disk_type (str): Optional. The sku name for the disk to create. Can be
          Standard_LRS, Premium_LRS, StandardSSD_LRS, or UltraSSD_LRS.
          Default is Standard_LRS.

    Returns:
      AZComputeDisk: Azure Compute Disk.

    Raises:
      ResourceCreationError: If the disk could not be created.
    """

    if not region:
      region = self.az_account.default_region

    # Create a temporary Azure account storage to import the snapshot
    storage_account_name = hashlib.sha1(
        snapshot.resource_id.encode('utf-8')).hexdigest()[:23]
    storage_account_url = 'https://{0:s}.blob.core.windows.net'.format(
        storage_account_name)
    # pylint: disable=line-too-long
    storage_account_id, storage_account_access_key = self.az_account.storage.CreateStorageAccount(
        storage_account_name, region=region)
    # pylint: enable=line-too-long
    blob_service_client = blob.BlobServiceClient(
        account_url=storage_account_url, credential=storage_account_access_key)

    # Create a container within the Storage to receive the imported snapshot
    container_name = storage_account_name + '-container'
    snapshot_vhd_name = snapshot.name + '.vhd'
    container_client = blob_service_client.get_container_client(container_name)
    try:
      logger.info('Creating blob container {0:s}'.format(container_name))
      container_client.create_container()
      logger.info('Blob container {0:s} successfully created'.format(
          container_name))
    except exceptions.ResourceExistsError:
      # The container already exists, so we can re-use it
      logger.warning('Reusing existing container: {0:s}'.format(container_name))

    # Download the snapshot from the URI to the storage
    copied_blob = blob_service_client.get_blob_client(
        container_name, snapshot_vhd_name)
    logger.info('Importing snapshot to container from URI {0:s}. '
                'Depending on the size of the snapshot, this process is going '
                'to take a while.'.format(snapshot_uri))
    copied_blob.start_copy_from_url(snapshot_uri)
    copy_status = copied_blob.get_blob_properties().copy.status
    while copy_status != 'success':
      sleep(5)  # Wait for the vhd to be imported in the Azure storage container
      copy_status = copied_blob.get_blob_properties().copy.status
      if copy_status in ('aborted', 'failed'):
        raise errors.ResourceCreationError(
            'Could not import the snapshot from URI {0:s}'.format(
                snapshot_uri), __name__)
      logger.debug('Importing snapshot from URI {0:s}'.format(snapshot_uri))
    logger.info('Snapshot successfully imported from URI {0:s}'.format(
        snapshot_uri))

    if not disk_name:
      disk_name = common.GenerateDiskName(snapshot,
                                          disk_name_prefix=disk_name_prefix)

    # Create a new disk from the imported snapshot
    creation_data = {
        'location': region,
        'creation_data': {
            'source_uri': copied_blob.url,
            'storage_account_id': storage_account_id,
            'create_option': models.DiskCreateOption.import_enum
        },
        'sku': {'name': disk_type}
    }

    try:
      logger.info('Creating disk: {0:s}'.format(disk_name))
      request = self.compute_client.disks.begin_create_or_update(
          self.az_account.default_resource_group_name,
          disk_name,
          creation_data)
      while not request.done():
        sleep(5)  # Wait 5 seconds before checking disk status again
      disk = request.result()
      logger.info('Disk {0:s} successfully created'.format(disk_name))
    except azure_exceptions.CloudError as exception:
      raise errors.ResourceCreationError(
          'Could not create disk from URI {0:s}: {1!s}'.format(
              snapshot_uri, exception), __name__) from exception

    # Cleanup the temporary account storage
    self.az_account.storage.DeleteStorageAccount(storage_account_name)

    return AZComputeDisk(self.az_account,
                         disk.id,
                         disk.name,
                         disk.location,
                         disk.zones)

  def GetOrCreateAnalysisVm(
      self,
      vm_name: str,
      boot_disk_size: int,
      cpu_cores: int,
      memory_in_mb: int,
      ssh_public_key: str,
      region: Optional[str] = None,
      packages: Optional[List[str]] = None,
      tags: Optional[Dict[str, str]] = None
  ) -> Tuple['AZComputeVirtualMachine', bool]:
    """Get or create a new virtual machine for analysis purposes.

    Args:
      vm_name (str): The instance name tag of the virtual machine.
      boot_disk_size (int): The size of the analysis VM boot volume (in GB).
      cpu_cores (int): Number of CPU cores for the analysis VM.
      memory_in_mb (int): The memory size (in MB) for the analysis VM.
      ssh_public_key (str): A SSH public key data to associate with the
          VM. This must be provided as otherwise the VM will not be
          accessible.
      region (str): Optional. The region in which to create the vm. If not
          provided, the vm will be created in the default_region
          associated to the AZAccount object.
      packages (List[str]): Optional. List of packages to install in the VM.
      tags (Dict[str, str]): Optional. A dictionary of tags to add to the
          instance, for example {'TicketID': 'xxx'}. An entry for the
          instance name is added by default.

    Returns:
      Tuple[AZComputeVirtualMachine, bool]: A tuple with an
          AZComputeVirtualMachine object and a boolean indicating if the
          virtual machine was created (True) or reused (False).

    Raises:
      RuntimeError: If the provided SSH key is invalid.
      ResourceCreationError: If the virtual machine cannot be found or created.
    """

    # Re-use instance if it already exists, or create a new one.
    try:
      instance = self.GetInstance(vm_name)
      if instance:
        created = False
        return instance, created
    except errors.ResourceNotFoundError:
      pass

    # Validate SSH public key format
    try:
      sshpubkeys.SSHKey(ssh_public_key, strict=True).parse()
    except sshpubkeys.InvalidKeyError as exception:
      raise RuntimeError('The provided public SSH key is invalid: '
                         '{0:s}'.format(str(exception))) from exception

    instance_type = self._GetInstanceType(cpu_cores, memory_in_mb)
    startup_script = utils.ReadStartupScript(utils.FORENSICS_STARTUP_SCRIPT_AZ)
    if packages:
      startup_script = startup_script.replace('${packages[@]}', ' '.join(
          packages))

    if not region:
      region = self.az_account.default_region

    creation_data = {
        'location': region,
        'properties': {
            'hardwareProfile': {'vmSize': instance_type},
            'storageProfile': {
                'imageReference': {
                    'sku': common.UBUNTU_1804_SKU,
                    'publisher': 'Canonical',
                    'version': 'latest',
                    'offer': 'UbuntuServer'}
            },
            'osDisk': {
                'caching': 'ReadWrite',
                'managedDisk': {'storageAccountType': 'Standard_LRS'},
                'name': 'os-disk-{0:s}'.format(vm_name),
                'diskSizeGb': boot_disk_size,
                'createOption': models.DiskCreateOption.from_image
            },
            'osProfile': {
                'adminUsername': 'AzureUser',
                'computerName': vm_name,
                # Azure requires the startup script to be sent as a b64 string
                'customData': base64.b64encode(
                    str.encode(startup_script)).decode('utf-8'),
                'linuxConfiguration': {
                    'ssh': {
                        'publicKeys': [{
                            'path': '/home/AzureUser/.ssh/authorized_keys',
                            'keyData': ssh_public_key}]
                    }
                }
            },
            'networkProfile': {
                'networkInterfaces': [
                    # pylint: disable=line-too-long
                    # This is necessary when creating a VM from the SDK.
                    # See https://docs.microsoft.com/en-us/azure/virtual-machines/windows/python
                    # pylint: enable=line-too-long
                    {'id': self.az_account.network.CreateNetworkInterface(
                        vm_name, region)}
                ]
            }
        }
    }  # type: Dict[str, Any]

    if tags:
      creation_data['tags'] = tags

    try:
      request = self.compute_client.virtual_machines.begin_create_or_update(
          self.az_account.default_resource_group_name,
          vm_name,
          creation_data
      )
      while not request.done():
        sleep(5)  # Wait 5 seconds before checking disk status again
      vm = request.result()
    except azure_exceptions.CloudError as exception:
      raise errors.ResourceCreationError(
          'Could not create instance {0:s}: {1!s}'.format(vm_name, exception),
          __name__) from exception

    instance = AZComputeVirtualMachine(self.az_account,
                                       vm.id,
                                       vm.name,
                                       vm.location,
                                       zones=vm.zones)
    created = True
    return instance, created

  def ListInstanceTypes(self,
                        region: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns a list of available VM sizes for a given region.

    Args:
      region (str): Optional. The region in which to look the instance types.
          By default, look in the default_region associated to the AZAccount
          object.

    Returns:
      List[Dict[str, str]]: A list of available vm size. Each size is a
          dictionary containing the name of the configuration, the number of
          CPU cores, and the amount of available memory (in MB).
          E.g.: {'Name': 'Standard_B1ls', 'CPU': 1, 'Memory': 512}
    """
    if not region:
      region = self.az_account.default_region
    available_vms = self.compute_client.virtual_machine_sizes.list(region)
    vm_sizes = []
    for vm in available_vms:
      vm_sizes.append({
          'Name': vm.name,
          'CPU': vm.number_of_cores,
          'Memory': vm.memory_in_mb
      })
    return vm_sizes

  def _GetInstanceType(self, cpu_cores: int, memory_in_mb: int) -> str:
    """Returns an instance type for the given number of CPU cores / memory.

    Args:
      cpu_cores (int): The number of CPU cores.
      memory_in_mb (int): The amount of memory (in MB).

    Returns:
      str: The instance type for the given configuration.

    Raises:
      ValueError: If no instance type matches the requested configuration.
    """
    vm_sizes = self.ListInstanceTypes()
    for size in vm_sizes:
      if size['CPU'] == cpu_cores and size['Memory'] == memory_in_mb:
        instance_type = size['Name']  # type: str
        return instance_type
    raise ValueError(
        'No instance type found for the requested configuration: {0:d} CPU '
        'cores, {1:d} MB memory.'.format(cpu_cores, memory_in_mb))


class AZComputeVirtualMachine(compute_base_resource.AZComputeResource):
  """Class that represents Azure virtual machines."""

  def __init__(self,
               az_account: 'account.AZAccount',
               resource_id: str,
               name: str,
               region: str,
               zones: Optional[List[str]] = None) -> None:
    """Initialize the AZComputeVirtualMachine class.

    Args:
      az_account (AZAccount): An Azure account object.
      resource_id (str): The Azure ID of the virtual machine.
      name (str): The virtual machine's name.
      region (str): The region in which the virtual machine is located.
      zones (List[str]): Optional. Availability zones within the region where
          the virtual machine is located / replicated.
    """
    super().__init__(az_account,
                     resource_id,
                     name,
                     region,
                     zones=zones)

  def GetBootDisk(self) -> 'AZComputeDisk':
    """Get the instance's boot disk.

    Returns:
      AZComputeDisk: Disk object if the disk is found.

    Raises:
      ResourceNotFoundError: If no boot disk could be found.
    """
    # pylint: disable=line-too-long
    disks = self.az_account.compute.ListDisks(
        resource_group_name=self.resource_group_name)  # type: Dict[str, AZComputeDisk]
    # pylint: enable=line-too-long
    boot_disk_name = self.compute_client.virtual_machines.get(
        self.resource_group_name, self.name).storage_profile.os_disk.name
    if boot_disk_name not in disks:
      raise errors.ResourceNotFoundError(
          'Boot disk not found for instance {0:s}'.format(self.resource_id),
          __name__)
    return disks[boot_disk_name]

  def GetDisk(self, disk_name: str) -> 'AZComputeDisk':
    """Get a disk attached to the instance by ID.

    Args:
      disk_name (str): The ID of the disk to get.

    Returns:
      AZComputeDisk: The disk object.

    Raises:
      ResourceNotFoundError: If disk_name is not found amongst the disks
          attached to the instance.
    """
    disks = self.ListDisks()
    if disk_name not in disks:
      raise errors.ResourceNotFoundError(
          'Disk {0:s} was not found in instance {1:s}'.format(
              disk_name, self.resource_id), __name__)
    return disks[disk_name]

  def ListDisks(self) -> Dict[str, 'AZComputeDisk']:
    """List all disks for the instance.

    Returns:
      Dict[str, AZComputeDisk]: Dictionary mapping disk names to their
          respective AZComputeDisk object.
    """
    disks = self.az_account.compute.ListDisks(
        resource_group_name=self.resource_group_name)
    vm_disks = self.compute_client.virtual_machines.get(
        self.resource_group_name, self.name).storage_profile
    vm_disks_names = [disk.name for disk in vm_disks.data_disks]
    vm_disks_names.append(vm_disks.os_disk.name)
    return {disk_name: disks[disk_name] for disk_name in vm_disks_names}

  def AttachDisk(self, disk: 'AZComputeDisk') -> None:
    """Attach a disk to the virtual machine.

    Args:
      disk (AZComputeDisk): Disk to attach.

    Raises:
      RuntimeError: If the disk could not be attached.
    """
    vm = self.compute_client.virtual_machines.get(
        self.resource_group_name, self.name)
    data_disks = vm.storage_profile.data_disks
    # ID to assign to the data disk to attach
    lun = 0 if len(data_disks) == 0 else len(data_disks) + 1

    update_data = {
        'lun': lun,
        'name': disk.name,
        'create_option': models.DiskCreateOption.attach,
        'managed_disk': {'id': disk.resource_id}
    }

    data_disks.append(update_data)

    try:
      request = self.compute_client.virtual_machines.begin_update(
          self.resource_group_name, self.name, vm)
      while not request.done():
        sleep(5)  # Wait 5 seconds before checking vm status again
    except azure_exceptions.CloudError as exception:
      raise RuntimeError(
          'Could not attach disk {0:s} to instance {1:s}: {2:s}'.format(
              disk.name, self.name, str(exception))) from exception


class AZComputeDisk(compute_base_resource.AZComputeResource):
  """Class that represents Azure disks."""

  def __init__(self,
               az_account: 'account.AZAccount',
               resource_id: str,
               name: str,
               region: str,
               zones: Optional[List[str]] = None) -> None:
    """Initialize the AZComputeDisk class.

    Args:
      az_account (AZAccount): An Azure account object.
      resource_id (str): The Azure ID of the disk.
      name (str): The disk name.
      region (str): The region in which the disk is located.
      zones (List[str]): Optional. Availability zone within the region where
          the disk is located.
    """
    super().__init__(az_account,
                     resource_id,
                     name,
                     region,
                     zones=zones)

  def Snapshot(self,
               snapshot_name: Optional[str] = None,
               tags: Optional[Dict[str, str]] = None) -> 'AZComputeSnapshot':
    """Create a snapshot of the disk.

    Args:
      snapshot_name (str): Optional. A name for the snapshot. If none
          provided, one will be generated based on the disk's name.
      tags (Dict[str, str]): Optional. A dictionary of tags to add to the
          snapshot, for example {'TicketID': 'xxx'}.

    Returns:
      AZComputeSnapshot: A snapshot object.

    Raises:
      InvalidNameError: If the snapshot name does not comply with the RegEx.
      ResourceCreationError: If the snapshot could not be created.
    """

    if not snapshot_name:
      snapshot_name = self.name + '_snapshot'
      truncate_at = 80 - 1
      snapshot_name = snapshot_name[:truncate_at]
      if not common.REGEX_SNAPSHOT_NAME.match(snapshot_name):
        raise errors.InvalidNameError(
            'Snapshot name {0:s} does not comply with {1:s}'.format(
                snapshot_name, common.REGEX_SNAPSHOT_NAME.pattern), __name__)

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
      request = self.compute_client.snapshots.begin_create_or_update(
          self.resource_group_name,
          snapshot_name,
          creation_data)
      while not request.done():
        sleep(5)  # Wait 5 seconds before checking snapshot status again
      snapshot = request.result()
      logger.info('Snapshot {0:s} successfully created'.format(snapshot_name))
    except azure_exceptions.CloudError as exception:
      raise errors.ResourceCreationError(
          'Could not create snapshot for disk {0:s}: {1!s}'.format(
              self.resource_id, exception), __name__) from exception

    return AZComputeSnapshot(self.az_account,
                             snapshot.id,
                             snapshot.name,
                             snapshot.location,
                             self)

  def GetDiskType(self) -> str:
    """Return the SKU disk type.

    Returns:
      str: The SKU disk type.
    """
    disk = self.compute_client.disks.get(
        self.resource_group_name, self.name)
    disk_type = disk.sku.name  # type: str
    return disk_type


class AZComputeSnapshot(compute_base_resource.AZComputeResource):
  """Class that represents Azure snapshots.

  Attributes:
    disk (AZComputeDisk): The disk from which the snapshot was taken.
  """

  def __init__(self,
               az_account: 'account.AZAccount',
               resource_id: str,
               name: str,
               region: str,
               source_disk: AZComputeDisk) -> None:
    """Initialize the AZComputeDisk class.

    Args:
      az_account (AZAccount): An Azure account object.
      resource_id (str): The Azure ID of the snapshot.
      name (str): The snapshot name.
      region (str): The region in which the snapshot is located.
      source_disk (AZComputeDisk): The disk from which the snapshot was taken.
    """
    super().__init__(az_account,
                     resource_id,
                     name,
                     region)

    self.disk = source_disk

  def Delete(self) -> None:
    """Delete a snapshot.

    Raises:
      ResourceDeletionError: If the snapshot could not be deleted.
    """

    try:
      logger.info('Deleting snapshot: {0:s}'.format(self.name))
      request = self.compute_client.snapshots.begin_delete(
          self.resource_group_name, self.name)
      while not request.done():
        sleep(5)  # Wait 5 seconds before checking snapshot status again
      logger.info('Snapshot {0:s} successfully deleted.'.format(self.name))
    except azure_exceptions.CloudError as exception:
      raise errors.ResourceDeletionError(
          'Could not delete snapshot {0:s}: {1!s}'.format(
              self.resource_id, exception), __name__) from exception

  def GrantAccessAndGetURI(self) -> str:
    """Grant access to a snapshot and return its access URI.

    Returns:
      str: The access URI for the snapshot.
    """
    logger.info('Generating SAS URI for snapshot: {0:s}'.format(self.name))
    access_grant = models.GrantAccessData(
        access='Read', duration_in_seconds=3600)
    access_request = self.compute_client.snapshots.begin_grant_access(
        self.resource_group_name, self.name, access_grant)
    snapshot_uri = access_request.result().access_sas  # type: str
    logger.info('SAS URI generated: {0:s}'.format(snapshot_uri))
    return snapshot_uri

  def RevokeAccessURI(self) -> None:
    """Revoke access to a snapshot."""
    logger.info('Revoking SAS URI for snapshot {0:s}'.format(self.name))
    request = self.compute_client.snapshots.begin_revoke_access(
        self.resource_group_name, self.name)
    request.wait()
    logger.info('SAS URI revoked for snapshot {0:s}'.format(self.name))
