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
"""Tests for the azure module - compute.py"""

import typing
import unittest
import mock

from azure.mgmt.compute.v2020_05_01 import models  # pylint: disable=import-error


from libcloudforensics import errors
from libcloudforensics.providers.azure.internal import compute
from tests.providers.azure import azure_mocks


class AZComputeTest(unittest.TestCase):
  """Test Azure compute class."""
  # pylint: disable=line-too-long

  @mock.patch('libcloudforensics.providers.azure.internal.common.ExecuteRequest')
  @typing.no_type_check
  def testListInstances(self, mock_request):
    """Test that instances of an account are correctly listed."""
    mock_request.return_value = azure_mocks.MOCK_REQUEST_INSTANCES

    # If we don't specify a resource group name, the 'list_all' method should
    # be called.
    instances = azure_mocks.FAKE_ACCOUNT.compute.ListInstances()
    mock_request.assert_called_with(mock.ANY, 'list_all')
    self.assertEqual(1, len(instances))
    self.assertIn('fake-vm-name', instances)
    instance = instances['fake-vm-name']
    self.assertEqual('fake-vm-name', instance.name)
    self.assertEqual(
        '/subscriptions/sub/resourceGroups/fake-resource-group'
        '/providers/Microsoft.Compute/type/fake-vm-name', instance.resource_id)
    self.assertEqual('fake-resource-group', instance.resource_group_name)
    self.assertEqual('fake-region', instance.region)
    self.assertEqual(['fake-zone'], instance.zones)

    # If we specify a resource group name, the 'list' method should be called.
    azure_mocks.FAKE_ACCOUNT.compute.ListInstances(
        resource_group_name=instance.resource_group_name)
    mock_request.assert_called_with(
        mock.ANY, 'list', {'resource_group_name': instance.resource_group_name})

  @mock.patch('libcloudforensics.providers.azure.internal.common.ExecuteRequest')
  @typing.no_type_check
  def testListDisks(self, mock_request):
    """Test that disks of an account are correctly listed."""
    mock_request.return_value = azure_mocks.MOCK_REQUEST_DISKS

    # If we don't specify a resource group name, the 'list' method should be
    # called.
    disks = azure_mocks.FAKE_ACCOUNT.compute.ListDisks()
    mock_request.assert_called_with(mock.ANY, 'list')
    self.assertEqual(2, len(disks))
    self.assertIn('fake-disk-name', disks)
    disk = disks['fake-disk-name']
    self.assertEqual('fake-disk-name', disk.name)
    self.assertEqual(
        '/subscriptions/sub/resourceGroups/fake-resource-group'
        '/providers/Microsoft.Compute/type/fake-disk-name', disk.resource_id)
    self.assertEqual('fake-resource-group', disk.resource_group_name)
    self.assertEqual('fake-region', disk.region)
    self.assertEqual(['fake-zone'], disk.zones)

    # If we specify a resource group name, the 'list_by_resource_group' method
    # should be called.
    azure_mocks.FAKE_ACCOUNT.compute.ListDisks(
        resource_group_name=disk.resource_group_name)
    mock_request.assert_called_with(
        mock.ANY,
        'list_by_resource_group',
        {'resource_group_name': disk.resource_group_name})

  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZCompute.ListInstances')
  @typing.no_type_check
  def testGetInstance(self, mock_list_instances):
    """Test that a particular instance from an account is retrieved."""
    mock_list_instances.return_value = azure_mocks.MOCK_LIST_INSTANCES
    instance = azure_mocks.FAKE_ACCOUNT.compute.GetInstance('fake-vm-name')
    self.assertEqual('fake-vm-name', instance.name)
    self.assertEqual(
        '/subscriptions/sub/resourceGroups/fake-resource-group'
        '/providers/Microsoft.Compute/type/fake-vm-name', instance.resource_id)
    self.assertEqual('fake-resource-group', instance.resource_group_name)
    self.assertEqual('fake-region', instance.region)
    self.assertEqual(['fake-zone'], instance.zones)

  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZCompute.ListDisks')
  @typing.no_type_check
  def testGetDisk(self, mock_list_disks):
    """Test that a particular disk from an account is retrieved."""
    mock_list_disks.return_value = azure_mocks.MOCK_LIST_DISKS
    disk = azure_mocks.FAKE_ACCOUNT.compute.GetDisk('fake-disk-name')
    self.assertEqual('fake-disk-name', disk.name)
    self.assertEqual(
        '/subscriptions/sub/resourceGroups/fake-resource-group'
        '/providers/Microsoft.Compute/type/fake-disk-name', disk.resource_id)
    self.assertEqual('fake-resource-group', disk.resource_group_name)
    self.assertEqual('fake-region', disk.region)
    self.assertEqual(['fake-zone'], disk.zones)

  @mock.patch('azure.mgmt.compute.v2020_12_01.operations._disks_operations.DisksOperations.begin_create_or_update')
  @typing.no_type_check
  def testCreateDiskFromSnapshot(self, mock_create_disk):
    """Test that a disk can be created from a snapshot."""
    # pylint: disable=line-too-long
    mock_create_disk.return_value.done.return_value = True
    mock_create_disk.return_value.result.return_value = azure_mocks.MOCK_DISK_COPY
    # CreateDiskFromSnapshot(
    #     snapshot=FAKE_SNAPSHOT, disk_name=None, disk_name_prefix='')
    disk_from_snapshot = azure_mocks.FAKE_ACCOUNT.compute.CreateDiskFromSnapshot(
        azure_mocks.FAKE_SNAPSHOT)
    self.assertIsInstance(disk_from_snapshot, compute.AZComputeDisk)
    self.assertEqual(
        'fake_snapshot_name_f4c186ac_copy', disk_from_snapshot.name)
    mock_create_disk.assert_called_with(
        azure_mocks.FAKE_SNAPSHOT.resource_group_name,
        'fake_snapshot_name_c4a46ad7_copy',
        mock.ANY)

    # CreateDiskFromSnapshot(
    #     snapshot=FAKE_SNAPSHOT,
    #     disk_name='new-forensics-disk',
    #     disk_name_prefix='')
    azure_mocks.FAKE_ACCOUNT.compute.CreateDiskFromSnapshot(
        azure_mocks.FAKE_SNAPSHOT, disk_name='new-forensics-disk')
    mock_create_disk.assert_called_with(
        azure_mocks.FAKE_SNAPSHOT.resource_group_name,
        'new-forensics-disk',
        mock.ANY)

    # CreateDiskFromSnapshot(
    #     snapshot=FAKE_SNAPSHOT, disk_name=None, disk_name_prefix='prefix')
    azure_mocks.FAKE_ACCOUNT.compute.CreateDiskFromSnapshot(
        azure_mocks.FAKE_SNAPSHOT, disk_name_prefix='prefix')
    mock_create_disk.assert_called_with(
        azure_mocks.FAKE_SNAPSHOT.resource_group_name,
        'prefix_fake_snapshot_name_c4a46ad7_copy',
        mock.ANY)

    # CreateDiskFromSnapshot(
    #     snapshot=FAKE_SNAPSHOT, disk_type='StandardSSD_LRS')
    expected_args = {
        'location': 'fake-region',
        'creation_data': {
            'sourceResourceId': '/subscriptions/sub/resourceGroups/'
                                'fake-resource-group/providers/'
                                'Microsoft.Compute/type/fake_snapshot_name',
            'create_option': models.DiskCreateOption.copy
        },
        'sku': {
            'name': 'StandardSSD_LRS'
        }
    }
    azure_mocks.FAKE_ACCOUNT.compute.CreateDiskFromSnapshot(
        azure_mocks.FAKE_SNAPSHOT, disk_type='StandardSSD_LRS')
    mock_create_disk.assert_called_with(
        azure_mocks.FAKE_SNAPSHOT.resource_group_name,
        'fake_snapshot_name_c4a46ad7_copy',
        expected_args)

  @mock.patch('azure.storage.blob._container_client.ContainerClient.create_container')
  @mock.patch('azure.storage.blob._generated._azure_blob_storage.AzureBlobStorage.__init__')
  @mock.patch('azure.storage.blob._blob_service_client.BlobServiceClient.get_blob_client')
  @mock.patch('azure.storage.blob._blob_service_client.BlobServiceClient.get_container_client')
  @mock.patch('azure.storage.blob._blob_service_client.BlobServiceClient.__init__')
  @mock.patch('libcloudforensics.providers.azure.internal.storage.AZStorage.DeleteStorageAccount')
  @mock.patch('libcloudforensics.providers.azure.internal.storage.AZStorage.CreateStorageAccount')
  @mock.patch('azure.mgmt.compute.v2020_12_01.operations._disks_operations.DisksOperations.begin_create_or_update')
  @typing.no_type_check
  def testCreateDiskFromSnapshotUri(self,
                                    mock_create_disk,
                                    mock_create_storage_account,
                                    mock_delete_storage_account,
                                    mock_blob_client,
                                    mock_get_container,
                                    mock_get_blob_client,
                                    mock_blob_storage,
                                    mock_create_container):
    """Test that a disk can be created from a snapshot URI."""
    # pylint: disable=line-too-long
    mock_create_disk.return_value.done.return_value = True
    mock_create_disk.return_value.result.return_value = azure_mocks.MOCK_DISK_COPY
    mock_create_storage_account.return_value = ('fake-account-id', 'fake-key')
    mock_blob_client.return_value = None
    mock_blob_storage.return_value = None
    mock_get_container.return_value = mock.Mock()
    mock_create_container.return_value = None
    blob_properties = mock_get_blob_client.return_value.get_blob_properties
    blob_properties.return_value = mock.Mock(copy=mock.Mock(status='success'))
    mock_delete_storage_account.return_value = None

    disk_from_snapshot_uri = azure_mocks.FAKE_ACCOUNT.compute.CreateDiskFromSnapshotURI(
        azure_mocks.FAKE_SNAPSHOT, 'fake-snapshot-uri')
    #  hashlib.sha1('/a/b/c/fake-resource-group/fake_snapshot_name'.encode(
    #     'utf-8')).hexdigest()[:23] = 97d1e8cfe4cf4d573fea2b5
    mock_create_storage_account.assert_called_with(
        '97d1e8cfe4cf4d573fea2b5', region='fake-region')
    self.assertIsInstance(disk_from_snapshot_uri, compute.AZComputeDisk)
    self.assertEqual(
        'fake_snapshot_name_f4c186ac_copy', disk_from_snapshot_uri.name)
    mock_create_disk.assert_called_with(
        azure_mocks.FAKE_SNAPSHOT.resource_group_name,
        'fake_snapshot_name_c4a46ad7_copy',
        mock.ANY)

  @mock.patch('sshpubkeys.SSHKey.parse')
  @mock.patch('libcloudforensics.scripts.utils.ReadStartupScript')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZCompute.GetInstance')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZCompute._GetInstanceType')
  @mock.patch('libcloudforensics.providers.azure.internal.network.AZNetwork.CreateNetworkInterface')
  @mock.patch('azure.mgmt.compute.v2021_04_01.operations._virtual_machines_operations.VirtualMachinesOperations.begin_create_or_update')
  @typing.no_type_check
  def testGetOrCreateAnalysisVm(self,
                                mock_vm,
                                mock_nic,
                                mock_instance_type,
                                mock_get_instance,
                                mock_script,
                                mock_ssh_parse):
    """Test that a VM is created or retrieved if it already exists."""
    mock_instance_type.return_value = 'fake-instance-type'
    mock_nic.return_value = 'fake-network-interface-id'
    mock_get_instance.return_value = azure_mocks.FAKE_INSTANCE
    mock_script.return_value = ''
    mock_ssh_parse.return_value = None

    vm, created = azure_mocks.FAKE_ACCOUNT.compute.GetOrCreateAnalysisVm(
        azure_mocks.FAKE_INSTANCE.name, 1, 4, 8192, '')
    mock_get_instance.assert_called_with(azure_mocks.FAKE_INSTANCE.name)
    mock_vm.assert_not_called()
    self.assertIsInstance(vm, compute.AZComputeVirtualMachine)
    self.assertEqual('fake-vm-name', vm.name)
    self.assertFalse(created)

    # We mock the GetInstance() call to throw a ResourceNotFoundError to mimic
    # an instance that wasn't found. This should trigger a vm to be
    # created.
    mock_get_instance.side_effect = errors.ResourceNotFoundError('', __name__)
    mock_vm.return_value.result.return_value = azure_mocks.MOCK_ANALYSIS_INSTANCE
    vm, created = azure_mocks.FAKE_ACCOUNT.compute.GetOrCreateAnalysisVm(
        'fake-analysis-vm-name', 1, 4, 8192, '')
    mock_get_instance.assert_called_with('fake-analysis-vm-name')
    mock_vm.assert_called()
    self.assertIsInstance(vm, compute.AZComputeVirtualMachine)
    self.assertEqual('fake-analysis-vm-name', vm.name)
    self.assertTrue(created)

  @mock.patch('azure.mgmt.compute.v2021_04_01.operations._virtual_machine_sizes_operations.VirtualMachineSizesOperations.list')
  @typing.no_type_check
  def testListVMSizes(self, mock_list):
    """Test that instance types are correctly listed."""
    mock_list.return_value = azure_mocks.MOCK_REQUEST_VM_SIZE
    available_vms = azure_mocks.FAKE_ACCOUNT.compute.ListInstanceTypes()
    self.assertEqual(1, len(available_vms))
    self.assertEqual('fake-vm-type', available_vms[0]['Name'])
    self.assertEqual(4, available_vms[0]['CPU'])
    self.assertEqual(8192, available_vms[0]['Memory'])

  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZCompute.ListInstanceTypes')
  @typing.no_type_check
  def testGetInstanceType(self, mock_list_instance_types):
    """Test that the instance type given a configuration is correct."""
    # pylint: disable=protected-access
    mock_list_instance_types.return_value = azure_mocks.MOCK_LIST_VM_SIZES
    instance_type = azure_mocks.FAKE_ACCOUNT.compute._GetInstanceType(4, 8192)
    self.assertEqual('fake-vm-type', instance_type)

    with self.assertRaises(ValueError):
      azure_mocks.FAKE_ACCOUNT.compute._GetInstanceType(666, 666)
    # pylint: enable=protected-access


class AZVirtualMachineTest(unittest.TestCase):
  """Test Azure virtual machine class."""
  # pylint: disable=line-too-long

  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZCompute.ListDisks')
  @mock.patch('azure.mgmt.compute.v2021_04_01.operations._virtual_machines_operations.VirtualMachinesOperations.get')
  @typing.no_type_check
  def testGetBootDisk(self, mock_get_vm, mock_list_disk):
    """Test that the boot disk from an instance is retrieved."""
    mock_get_vm.return_value = mock.Mock(
        storage_profile=mock.Mock(os_disk=azure_mocks.MOCK_BOOT_DISK))
    mock_list_disk.return_value = azure_mocks.MOCK_LIST_DISKS
    boot_disk = azure_mocks.FAKE_INSTANCE.GetBootDisk()
    mock_list_disk.assert_called_once()
    mock_list_disk.assert_called_with(
        resource_group_name=azure_mocks.FAKE_INSTANCE.resource_group_name)
    self.assertEqual('fake-boot-disk-name', boot_disk.name)

  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZComputeVirtualMachine.ListDisks')
  @typing.no_type_check
  def testGetDisk(self, mock_list_disk):
    """Test that a particular disk from an instance is retrieved."""
    mock_list_disk.return_value = azure_mocks.MOCK_LIST_DISKS
    disk = azure_mocks.FAKE_INSTANCE.GetDisk('fake-disk-name')
    self.assertEqual('fake-disk-name', disk.name)

    with self.assertRaises(errors.ResourceNotFoundError) as error:
      azure_mocks.FAKE_INSTANCE.GetDisk('non-existent-disk-name')
    self.assertEqual(
        'Disk non-existent-disk-name was not found in instance '
        '/subscriptions/sub/resourceGroups/fake-resource-group/providers/'
        'Microsoft.Compute/type/fake-vm-name', str(error.exception))

  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZCompute.ListDisks')
  @mock.patch('azure.mgmt.compute.v2021_04_01.operations._virtual_machines_operations.VirtualMachinesOperations.get')
  @typing.no_type_check
  def testListDisks(self, mock_get_vm, mock_list_disk):
    """Test that disks from an instance are correctly listed."""
    mock_get_vm.return_value = mock.Mock(
        storage_profile=mock.Mock(
            os_disk=azure_mocks.MOCK_BOOT_DISK, data_disks=[]))

    # MOCK_LIST_DISKS contains all 2 disks from the subscription
    self.assertEqual(2, len(azure_mocks.MOCK_LIST_DISKS))
    mock_list_disk.return_value = azure_mocks.MOCK_LIST_DISKS

    # The instance is expected to have only a boot disk as we mocked the
    # data_disks attribute with an empty list
    instance_disks = azure_mocks.FAKE_INSTANCE.ListDisks()
    mock_list_disk.assert_called()
    mock_list_disk.assert_called_with(
        resource_group_name=azure_mocks.FAKE_INSTANCE.resource_group_name)
    self.assertEqual(1, len(instance_disks))
    self.assertNotEqual(azure_mocks.MOCK_LIST_DISKS, instance_disks)

    # The instance is expected to have 2 disks as we mocked the
    # data_disks attribute with a non-empty list
    mock_get_vm.return_value = mock.Mock(
        storage_profile=mock.Mock(
            os_disk=azure_mocks.MOCK_BOOT_DISK,
            data_disks=[azure_mocks.MOCK_DISK]))
    instance_disks = azure_mocks.FAKE_INSTANCE.ListDisks()
    mock_list_disk.assert_called()
    mock_list_disk.assert_called_with(
        resource_group_name=azure_mocks.FAKE_INSTANCE.resource_group_name)
    self.assertEqual(2, len(instance_disks))
    self.assertEqual(azure_mocks.MOCK_LIST_DISKS, instance_disks)
