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

import base64
import hashlib
from time import sleep
from typing import Optional, Dict, Tuple, List, Any

# Pylint complains about the import but the library imports just fine,
# so we can ignore the warning.
# pylint: disable=import-error
import sshpubkeys
from azure.core import exceptions
from azure.mgmt import compute as azure_compute
from azure.mgmt import resource, storage, network
from azure.mgmt.compute.v2020_05_01 import models
from azure.storage import blob
from msrestazure import azure_exceptions
# pylint: enable=import-error

from libcloudforensics.providers.azure.internal import compute, common
from libcloudforensics import logging_utils
from libcloudforensics.scripts import utils

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)


class AZAccount:
  """Class that represents an Azure Account.

  Attributes:
    subscription_id (str): The Azure subscription ID to use.
    credentials (ServicePrincipalCredentials): An Azure credentials object.
    compute_client (ComputeManagementClient): An Azure compute client object.
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
    self.compute_client = azure_compute.ComputeManagementClient(
        self.credentials, self.subscription_id)
    self.storage_client = storage.StorageManagementClient(
        self.credentials, self.subscription_id)
    self.resource_client = resource.ResourceManagementClient(
        self.credentials, self.subscription_id)
    self.network_client = network.NetworkManagementClient(
        self.credentials, self.subscription_id)
    self.default_resource_group_name = self._GetOrCreateResourceGroup(
        default_resource_group_name)

  def ListSubscriptionIDs(self) -> List[str]:
    """List subscription ids from an Azure account.

    Returns:
      List[str]: A list of all subscription IDs from the Azure account.
    """
    subscription_client = resource.SubscriptionClient(self.credentials)
    subscription_ids = subscription_client.subscriptions.list()
    return [sub.subscription_id for sub in subscription_ids]

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
      region: Optional[str] = None,
      disk_name: Optional[str] = None,
      disk_name_prefix: Optional[str] = None,
      disk_type: str = 'Standard_LRS') -> compute.AZDisk:
    """Create a new disk based on a Snapshot.

    Args:
      snapshot (AZSnapshot): Snapshot to use.
      region (str): Optional. The region in which to create the disk. If not
          provided, the disk will be created in the default_region associated to
          the AZAccount object.
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

    if not region:
      region = self.default_region

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
      request = self.compute_client.disks.create_or_update(
          self.default_resource_group_name,
          disk_name,
          creation_data)
      while not request.done():
        sleep(5)  # Wait 5 seconds before checking disk status again
      disk = request.result()
      logger.info('Disk {0:s} successfully created'.format(disk_name))
    except azure_exceptions.CloudError as exception:
      raise RuntimeError('Could not create disk from snapshot {0:s}: {1:s}'
                         .format(snapshot.resource_id, str(exception)))

    return compute.AZDisk(self,
                          disk.id,
                          disk.name,
                          disk.location,
                          disk.zones)

  def CreateDiskFromSnapshotURI(
      self,
      snapshot: compute.AZSnapshot,
      snapshot_uri: str,
      region: Optional[str] = None,
      disk_name: Optional[str] = None,
      disk_name_prefix: Optional[str] = None,
      disk_type: str = 'Standard_LRS') -> compute.AZDisk:
    """Create a new disk based on a SAS snapshot URI.

    This is useful if e.g. one wants to make a copy of a disk in a separate
    Azure account. This method will create a temporary Azure Storage account
    within the destination account, import the snapshot from a downloadable
    link (the source account needs to share the snapshot through a SAS link)
    and then create a disk from the VHD file saved in storage. The Azure
    storage account is then deleted.

    Args:
      snapshot (AZSnapshot): Source snapshot to use.
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
      AZDisk: Azure Compute Disk.

    Raises:
      RuntimeError: If the disk could not be created.
    """

    if not region:
      region = self.default_region

    # Create a temporary Azure account storage to import the snapshot
    storage_account_name = hashlib.sha1(
        snapshot.resource_id.encode('utf-8')).hexdigest()[:23]
    storage_account_url = 'https://{0:s}.blob.core.windows.net'.format(
        storage_account_name)
    storage_account_id, storage_account_access_key = self._CreateStorageAccount(
        storage_account_name, region=region)
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
        raise RuntimeError('Could not import the snapshot from URI '
                           '{0:s}'.format(snapshot_uri))
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
      request = self.compute_client.disks.create_or_update(
          self.default_resource_group_name,
          disk_name,
          creation_data)
      while not request.done():
        sleep(5)  # Wait 5 seconds before checking disk status again
      disk = request.result()
      logger.info('Disk {0:s} successfully created'.format(disk_name))
    except azure_exceptions.CloudError as exception:
      raise RuntimeError('Could not create disk from URI {0:s}: {1:s}'
                         .format(snapshot_uri, str(exception)))

    # Cleanup the temporary account storage
    self._DeleteStorageAccount(storage_account_name)

    return compute.AZDisk(self,
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
  ) -> Tuple[compute.AZVirtualMachine, bool]:
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
      Tuple[AWSInstance, bool]: A tuple with an AZVirtualMachine object
          and a boolean indicating if the virtual machine was created
          (True) or reused (False).

    Raises:
      RuntimeError: If the virtual machine cannot be found or created.
    """

    # Re-use instance if it already exists, or create a new one.
    try:
      instance = self.GetInstance(vm_name)
      if instance:
        created = False
        return instance, created
    except RuntimeError:
      pass

    # Validate SSH public key format
    try:
      sshpubkeys.SSHKey(ssh_public_key, strict=True).parse()
    except sshpubkeys.InvalidKeyError as exception:
      raise RuntimeError('The provided public SSH key is invalid: '
                         '{0:s}'.format(str(exception)))

    instance_type = self._GetInstanceType(cpu_cores, memory_in_mb)
    startup_script = utils.ReadStartupScript()
    if packages:
      startup_script = startup_script.replace('${packages[@]}', ' '.join(
          packages))

    if not region:
      region = self.default_region

    creation_data = {
        'location': region,
        'properties': {
            'hardwareProfile': {'vmSize': instance_type},
            'storageProfile': {
                'imageReference': {
                    'sku': '18.04-LTS',
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
                    {'id': self._CreateNetworkInterfaceForVM(vm_name, region)}
                ]
            }
        }
    }  # type: Dict[str, Any]

    if tags:
      creation_data['tags'] = tags

    try:
      request = self.compute_client.virtual_machines.create_or_update(
          self.default_resource_group_name,
          vm_name,
          creation_data
      )
      while not request.done():
        sleep(5)  # Wait 5 seconds before checking disk status again
      vm = request.result()
    except azure_exceptions.CloudError as exception:
      raise RuntimeError('Could not create instance {0:s}: {1:s}'.format(
          vm_name, str(exception)))

    instance = compute.AZVirtualMachine(self,
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
      region = self.default_region
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

  def _CreateNetworkInterfaceForVM(self,
                                   vm_name: str,
                                   region: Optional[str] = None) -> str:
    """Create a network interface and returns its ID.
    This is necessary when creating a VM from the SDK.
    See https://docs.microsoft.com/en-us/azure/virtual-machines/windows/python

    Args:
      vm_name (str): The name of the VM to create the network interface for.
      region (str): Optional. The region in which to create the network
          interface. Default uses default_region of the AZAccount object.

    Returns:
      str: The id of the created network interface.

    Raises:
      ValueError: if vm_name is not provided.
      RuntimeError: If no network interface could be created.
    """
    if not vm_name:
      raise ValueError(
          'vm_name must be specified. Provided: {0!s}'.format(vm_name))

    if not region:
      region = self.default_region

    network_interface_name = '{0:s}-nic'.format(vm_name)
    ip_config_name = '{0:s}-ipconfig'.format(vm_name)

    # Check if the network interface already exists, and returns its ID if so.
    try:
      nic = self.network_client.network_interfaces.get(
          self.default_resource_group_name, network_interface_name)
      nic_id = nic.id  # type: str
      return nic_id
    except azure_exceptions.CloudError:
      # NIC doesn't exist, ignore the error and create it
      pass

    # pylint: disable=unbalanced-tuple-unpacking
    public_ip, _, subnet = self._CreateNetworkInterfaceElements(
        vm_name, region=region)
    # pylint: enable=unbalanced-tuple-unpacking

    creation_data = {
        'location': region,
        'ip_configurations': [{
            'name': ip_config_name,
            'public_ip_address': public_ip,
            'subnet': {
                'id': subnet.id
            }
        }]
    }

    try:
      request = self.network_client.network_interfaces.create_or_update(
          self.default_resource_group_name,
          network_interface_name,
          creation_data)
      request.wait()
    except azure_exceptions.CloudError as exception:
      raise RuntimeError('Could not create network interface: {0:s}'.format(
          str(exception)))

    network_interface_id = request.result().id  # type: str
    return network_interface_id

  def _CreateNetworkInterfaceElements(
      self,
      vm_name: str,
      region: Optional[str] = None) -> Tuple[Any, ...]:
    """Creates required elements for creating a network interface.

    Args:
      vm_name (str): The name of the VM to create the network interface
          elements for.
      region (str): Optional. The region in which to create the elements.
          Default uses default_region of the AZAccount object.

    Returns:
      Tuple[Any, Any, Any]: A tuple containing a public IP address object,
          a virtual network object and a subnet object.

    Raises:
      RuntimeError: If the elements could not be created.
    """

    if not region:
      region = self.default_region

    public_ip_name = '{0:s}-public-ip'.format(vm_name)
    vnet_name = '{0:s}-vnet'.format(vm_name)
    subnet_name = '{0:s}-subnet'.format(vm_name)

    client_to_creation_data = {
        self.network_client.public_ip_addresses: {
            'resource_group_name': self.default_resource_group_name,
            'public_ip_address_name': public_ip_name,
            'parameters': {
                'location': region,
                'public_ip_allocation_method': 'Dynamic'
            }
        },
        self.network_client.virtual_networks: {
            'resource_group_name': self.default_resource_group_name,
            'virtual_network_name': vnet_name,
            'parameters': {
                'location': region,
                'address_space': {'address_prefixes': ['10.0.0.0/16']}
            }
        },
        self.network_client.subnets: {
            'resource_group_name': self.default_resource_group_name,
            'virtual_network_name': vnet_name,
            'subnet_name': subnet_name,
            'subnet_parameters': {
                'address_prefix': '10.0.0.0/24'
            }
        }
    }  # type: Dict[str, Any]

    result = []
    try:
      for client in client_to_creation_data:
        request = common.ExecuteRequest(
            client, 'create_or_update', client_to_creation_data[client])[0]
        request.wait()
        result.append(request.result())
    except azure_exceptions.CloudError as exception:
      raise RuntimeError('Could not create network interface elements: '
                         '{0:s}'.format(str(exception)))
    return tuple(result)

  def _CreateStorageAccount(self,
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
      ValueError: If the storage account name is invalid.
    """

    if not common.REGEX_ACCOUNT_STORAGE_NAME.match(storage_account_name):
      raise ValueError(
          'Storage account name {0:s} does not comply with {1:s}'.format(
              storage_account_name, common.REGEX_ACCOUNT_STORAGE_NAME.pattern))

    if not region:
      region = self.default_region

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
    request = self.storage_client.storage_accounts.create(
        self.default_resource_group_name,
        storage_account_name,
        creation_data
    )
    logger.info('Storage account {0:s} successfully created'.format(
        storage_account_name))
    storage_account = request.result()
    storage_account_keys = self.storage_client.storage_accounts.list_keys(
        self.default_resource_group_name, storage_account_name)
    storage_account_keys = {key.key_name: key.value
                            for key in storage_account_keys.keys}
    storage_account_id = storage_account.id  # type: str
    storage_account_key = storage_account_keys['key1']  # type: str
    return storage_account_id, storage_account_key

  def _DeleteStorageAccount(self, storage_account_name: str) -> None:
    """Delete an account storage.

    Raises:
      RuntimeError: if the storage account could not be deleted.
    """
    try:
      logger.info('Deleting storage account: {0:s}'.format(
          storage_account_name))
      self.storage_client.storage_accounts.delete(
          self.default_resource_group_name, storage_account_name)
      logger.info('Storage account {0:s} successfully deleted'.format(
          storage_account_name))
    except azure_exceptions.CloudError as exception:
      raise RuntimeError('Could not delete account storage {0:s}: {1:s}'
                         .format(storage_account_name, str(exception)))

  def _GetOrCreateResourceGroup(self, resource_group_name: str) -> str:
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
          'location': self.default_region
      }
      self.resource_client.resource_groups.create_or_update(
          resource_group_name, creation_data)
      logger.info('Resource group {0:s} successfully created.'.format(
          resource_group_name))
    return resource_group_name
