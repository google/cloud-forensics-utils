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
"""Tests for the azure module."""
import typing
import unittest
import mock

from libcloudforensics.providers.azure.internal import account, compute, common
from libcloudforensics.providers.azure import forensics

FAKE_ACCOUNT = account.AZAccount(
    'fake-subscription-id'
)

FAKE_INSTANCE = compute.AZVirtualMachine(
    FAKE_ACCOUNT,
    '/a/b/c/fake-resource-group/fake-vm-name',
    'fake-vm-name',
    'fake-region',
    ['fake-zone']
)

FAKE_DISK = compute.AZDisk(
    FAKE_ACCOUNT,
    '/a/b/c/fake-resource-group/fake-disk-name',
    'fake-disk-name',
    'fake-region',
    ['fake-zone']
)

FAKE_BOOT_DISK = compute.AZDisk(
    FAKE_ACCOUNT,
    '/a/b/c/fake-resource-group/fake-boot-disk-name',
    'fake-boot-disk-name',
    'fake-region',
    ['fake-zone']
)

FAKE_SNAPSHOT = compute.AZSnapshot(
    FAKE_ACCOUNT,
    '/a/b/c/fake-resource-group/fake_snapshot_name',
    'fake_snapshot_name',
    'fake-region',
    FAKE_DISK
)

MOCK_INSTANCE = mock.Mock(
    id='/a/b/c/fake-resource-group/fake-vm-name',
    location='fake-region',
    zones=['fake-zone']
)
MOCK_INSTANCE.name = 'fake-vm-name'
MOCK_REQUEST_INSTANCES = [[MOCK_INSTANCE]]
MOCK_LIST_INSTANCES = {
    'fake-vm-name': FAKE_INSTANCE
}

MOCK_DISK = mock.Mock(
    id='/a/b/c/fake-resource-group/fake-disk-name',
    location='fake-region',
    zones=['fake-zone']
)
MOCK_DISK.name = 'fake-disk-name'

MOCK_BOOT_DISK = mock.Mock(
    id='/a/b/c/fake-resource-group/fake-boot-disk-name',
    location='fake-region',
    zones=['fake-zone']
)
MOCK_BOOT_DISK.name = 'fake-boot-disk-name'

MOCK_DISK_COPY = mock.Mock(
    id='/a/b/c/fake-resource-group/fake_snapshot_name_f4c186ac_copy',
    location='fake-region',
    zones=['fake-zone']
)
MOCK_DISK_COPY.name = 'fake_snapshot_name_f4c186ac_copy'

MOCK_REQUEST_DISKS = [[MOCK_DISK, MOCK_BOOT_DISK]]
MOCK_LIST_DISKS = {
    'fake-disk-name': FAKE_DISK,
    'fake-boot-disk-name': FAKE_BOOT_DISK
}


class TestAccount(unittest.TestCase):
  """Test Azure account class."""
  # pylint: disable=line-too-long

  @mock.patch('libcloudforensics.providers.azure.internal.common.ExecuteRequest')
  @typing.no_type_check
  def testListInstances(self, mock_request):
    """Test that instances of an account are correctly listed."""
    mock_request.return_value = MOCK_REQUEST_INSTANCES

    # If we don't specify a resource group name, the 'list_all' method should
    # be called.
    instances = FAKE_ACCOUNT.ListInstances()
    mock_request.assert_called_with(mock.ANY, 'list_all')
    self.assertEqual(1, len(instances))
    self.assertIn('fake-vm-name', instances)
    instance = instances['fake-vm-name']
    self.assertEqual('fake-vm-name', instance.name)
    self.assertEqual(
        '/a/b/c/fake-resource-group/fake-vm-name', instance.resource_id)
    self.assertEqual('fake-resource-group', instance.resource_group_name)
    self.assertEqual('fake-region', instance.region)
    self.assertEqual(['fake-zone'], instance.zones)

    # If we specify a resource group name, the 'list' method should be called.
    FAKE_ACCOUNT.ListInstances(
        resource_group_name=instance.resource_group_name)
    mock_request.assert_called_with(
        mock.ANY, 'list', {'resource_group_name': instance.resource_group_name})

  @mock.patch('libcloudforensics.providers.azure.internal.common.ExecuteRequest')
  @typing.no_type_check
  def testListDisks(self, mock_request):
    """Test that disks of an account are correctly listed."""
    mock_request.return_value = MOCK_REQUEST_DISKS

    # If we don't specify a resource group name, the 'list' method should be
    # called.
    disks = FAKE_ACCOUNT.ListDisks()
    mock_request.assert_called_with(mock.ANY, 'list')
    self.assertEqual(2, len(disks))
    self.assertIn('fake-disk-name', disks)
    disk = disks['fake-disk-name']
    self.assertEqual('fake-disk-name', disk.name)
    self.assertEqual(
        '/a/b/c/fake-resource-group/fake-disk-name', disk.resource_id)
    self.assertEqual('fake-resource-group', disk.resource_group_name)
    self.assertEqual('fake-region', disk.region)
    self.assertEqual(['fake-zone'], disk.zones)

    # If we specify a resource group name, the 'list_by_resource_group' method
    # should be called.
    FAKE_ACCOUNT.ListDisks(resource_group_name=disk.resource_group_name)
    mock_request.assert_called_with(
        mock.ANY,
        'list_by_resource_group',
        {'resource_group_name': disk.resource_group_name})

  @mock.patch('libcloudforensics.providers.azure.internal.account.AZAccount.ListInstances')
  @typing.no_type_check
  def testGetInstance(self, mock_list_instances):
    """Test that a particular instance from an account is retrieved."""
    mock_list_instances.return_value = MOCK_LIST_INSTANCES
    instance = FAKE_ACCOUNT.GetInstance('fake-vm-name')
    self.assertEqual('fake-vm-name', instance.name)
    self.assertEqual(
        '/a/b/c/fake-resource-group/fake-vm-name', instance.resource_id)
    self.assertEqual('fake-resource-group', instance.resource_group_name)
    self.assertEqual('fake-region', instance.region)
    self.assertEqual(['fake-zone'], instance.zones)

  @mock.patch('libcloudforensics.providers.azure.internal.account.AZAccount.ListDisks')
  @typing.no_type_check
  def testGetDisk(self, mock_list_disks):
    """Test that a particular disk from an account is retrieved."""
    mock_list_disks.return_value = MOCK_LIST_DISKS
    disk = FAKE_ACCOUNT.GetDisk('fake-disk-name')
    self.assertEqual('fake-disk-name', disk.name)
    self.assertEqual(
        '/a/b/c/fake-resource-group/fake-disk-name', disk.resource_id)
    self.assertEqual('fake-resource-group', disk.resource_group_name)
    self.assertEqual('fake-region', disk.region)
    self.assertEqual(['fake-zone'], disk.zones)

  @mock.patch('azure.mgmt.compute.v2019_11_01.operations._disks_operations.DisksOperations.create_or_update')
  @typing.no_type_check
  def testCreateDiskFromSnapshot(self, mock_create_disk):
    """Test that a disk can be created from a snapshot."""
    mock_create_disk.return_value.done.return_value = True
    mock_create_disk.return_value.result.return_value = MOCK_DISK_COPY
    # CreateDiskFromSnapshot(
    #     snapshot=FAKE_SNAPSHOT, disk_name=None, disk_name_prefix='')
    disk_from_snapshot = FAKE_ACCOUNT.CreateDiskFromSnapshot(
        FAKE_SNAPSHOT)
    self.assertIsInstance(disk_from_snapshot, compute.AZDisk)
    self.assertEqual(
        'fake_snapshot_name_f4c186ac_copy', disk_from_snapshot.name)
    mock_create_disk.assert_called_with(
        FAKE_SNAPSHOT.resource_group_name,
        'fake_snapshot_name_f4c186ac_copy',
        mock.ANY,
        sku='Standard_LRS')

    # CreateDiskFromSnapshot(
    #     snapshot=FAKE_SNAPSHOT,
    #     disk_name='new-forensics-disk',
    #     disk_name_prefix='')
    FAKE_ACCOUNT.CreateDiskFromSnapshot(
        FAKE_SNAPSHOT, disk_name='new-forensics-disk')
    mock_create_disk.assert_called_with(
        FAKE_SNAPSHOT.resource_group_name,
        'new-forensics-disk',
        mock.ANY,
        sku='Standard_LRS')

    # CreateDiskFromSnapshot(
    #     snapshot=FAKE_SNAPSHOT, disk_name=None, disk_name_prefix='prefix')
    FAKE_ACCOUNT.CreateDiskFromSnapshot(
        FAKE_SNAPSHOT, disk_name_prefix='prefix')
    mock_create_disk.assert_called_with(
        FAKE_SNAPSHOT.resource_group_name,
        'prefix_fake_snapshot_name_f4c186ac_copy',
        mock.ANY,
        sku='Standard_LRS')

    # CreateDiskFromSnapshot(
    #     snapshot=FAKE_SNAPSHOT, disk_type='StandardSSD_LRS')
    FAKE_ACCOUNT.CreateDiskFromSnapshot(
        FAKE_SNAPSHOT, disk_type='StandardSSD_LRS')
    mock_create_disk.assert_called_with(
        FAKE_SNAPSHOT.resource_group_name,
        'fake_snapshot_name_f4c186ac_copy',
        mock.ANY,
        sku='StandardSSD_LRS')


class TestCommon(unittest.TestCase):
  """Test Azure common file."""

  @typing.no_type_check
  def testGenerateDiskName(self):
    """Test that disk names are correclty generated.

    The disk name must comply with the following RegEx: ^[\\w]{1,80}$
        i.e., it must be between 1 and 80 chars and be within [a-zA-Z0-9].
    """
    disk_name = common.GenerateDiskName(FAKE_SNAPSHOT)
    self.assertEqual('fake_snapshot_name_f4c186ac_copy', disk_name)

    disk_name = common.GenerateDiskName(
        FAKE_SNAPSHOT, disk_name_prefix='prefix')
    self.assertEqual('prefix_fake_snapshot_name_f4c186ac_copy', disk_name)


class TestAZVirtualMachine(unittest.TestCase):
  """Test Azure virtual machine class."""
  # pylint: disable=line-too-long

  @mock.patch('libcloudforensics.providers.azure.internal.account.AZAccount.ListDisks')
  @mock.patch('azure.mgmt.compute.v2019_12_01.operations._virtual_machines_operations.VirtualMachinesOperations.get')
  @typing.no_type_check
  def testGetBootDisk(self, mock_get_vm, mock_list_disk):
    """Test that the boot disk from an instance is retrieved."""
    mock_get_vm.return_value = mock.Mock(
        storage_profile=mock.Mock(os_disk=MOCK_BOOT_DISK))
    mock_list_disk.return_value = MOCK_LIST_DISKS
    boot_disk = FAKE_INSTANCE.GetBootDisk()
    mock_list_disk.assert_called_once()
    mock_list_disk.assert_called_with(
        resource_group_name=FAKE_INSTANCE.resource_group_name)
    self.assertEqual('fake-boot-disk-name', boot_disk.name)

  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZVirtualMachine.ListDisks')
  @typing.no_type_check
  def testGetDisk(self, mock_list_disk):
    """Test that a particular disk from an instance is retrieved."""
    mock_list_disk.return_value = MOCK_LIST_DISKS
    disk = FAKE_INSTANCE.GetDisk('fake-disk-name')
    self.assertEqual('fake-disk-name', disk.name)

    with self.assertRaises(RuntimeError):
      FAKE_INSTANCE.GetDisk('non-existent-disk-name')

  @mock.patch('libcloudforensics.providers.azure.internal.account.AZAccount.ListDisks')
  @mock.patch('azure.mgmt.compute.v2019_12_01.operations._virtual_machines_operations.VirtualMachinesOperations.get')
  @typing.no_type_check
  def testListDisks(self, mock_get_vm, mock_list_disk):
    """Test that disks from an instance are correctly listed."""
    mock_get_vm.return_value = mock.Mock(
        storage_profile=mock.Mock(os_disk=MOCK_BOOT_DISK, data_disks=[]))

    # MOCK_LIST_DISKS contains all 2 disks from the subscription
    self.assertEqual(2, len(MOCK_LIST_DISKS))
    mock_list_disk.return_value = MOCK_LIST_DISKS

    # The instance is expected to have only a boot disk as we mocked the
    # data_disks attribute with an empty list
    instance_disks = FAKE_INSTANCE.ListDisks()
    mock_list_disk.assert_called()
    mock_list_disk.assert_called_with(
        resource_group_name=FAKE_INSTANCE.resource_group_name)
    self.assertEqual(1, len(instance_disks))
    self.assertNotEqual(MOCK_LIST_DISKS, instance_disks)

    # The instance is expected to have 2 disks as we mocked the
    # data_disks attribute with a non-empty list
    mock_get_vm.return_value = mock.Mock(
        storage_profile=mock.Mock(
            os_disk=MOCK_BOOT_DISK, data_disks=[MOCK_DISK]))
    instance_disks = FAKE_INSTANCE.ListDisks()
    mock_list_disk.assert_called()
    mock_list_disk.assert_called_with(
        resource_group_name=FAKE_INSTANCE.resource_group_name)
    self.assertEqual(2, len(instance_disks))
    self.assertEqual(MOCK_LIST_DISKS, instance_disks)


class TestForensics(unittest.TestCase):
  """Test Azure forensics file."""
  # pylint: disable=line-too-long

  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZSnapshot.Delete')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZDisk.Snapshot')
  @mock.patch('libcloudforensics.providers.azure.internal.account.AZAccount.GetDisk')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZVirtualMachine.GetBootDisk')
  @mock.patch('libcloudforensics.providers.azure.internal.account.AZAccount.GetInstance')
  @mock.patch('azure.mgmt.compute.v2019_11_01.operations._disks_operations.DisksOperations.create_or_update')
  @typing.no_type_check
  def testCreateDiskCopy1(self,
                          mock_create_disk,
                          mock_get_instance,
                          mock_get_boot_disk,
                          mock_get_disk,
                          mock_snapshot,
                          mock_snapshot_delete):
    """Test that a disk copy is correctly created."""
    mock_create_disk.return_value.done.return_value = True
    mock_create_disk.return_value.result.return_value = MOCK_DISK_COPY
    mock_get_instance.return_value = FAKE_INSTANCE
    mock_get_boot_disk.return_value = FAKE_BOOT_DISK
    mock_snapshot.return_value = FAKE_SNAPSHOT
    mock_snapshot_delete.return_value = None

    # CreateDiskCopy(zone, instance_name='fake-vm-name'). This should grab
    # the boot disk of the instance.
    disk_copy = forensics.CreateDiskCopy(
        FAKE_ACCOUNT.subscription_id, instance_name=FAKE_INSTANCE.name)
    mock_get_instance.assert_called_once()
    mock_get_instance.assert_called_with('fake-vm-name')
    mock_get_boot_disk.assert_called_once()
    mock_get_disk.assert_not_called()
    self.assertIsInstance(disk_copy, compute.AZDisk)
    self.assertEqual('fake_snapshot_name_f4c186ac_copy', disk_copy.name)

  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZSnapshot.Delete')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZDisk.Snapshot')
  @mock.patch('libcloudforensics.providers.azure.internal.account.AZAccount.GetDisk')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZVirtualMachine.GetBootDisk')
  @mock.patch('libcloudforensics.providers.azure.internal.account.AZAccount.GetInstance')
  @mock.patch('azure.mgmt.compute.v2019_11_01.operations._disks_operations.DisksOperations.create_or_update')
  @typing.no_type_check
  def testCreateDiskCopy2(self,
                          mock_create_disk,
                          mock_get_instance,
                          mock_get_boot_disk,
                          mock_get_disk,
                          mock_snapshot,
                          mock_snapshot_delete):
    """Test that a disk copy is correctly created."""
    mock_create_disk.return_value.done.return_value = True
    mock_create_disk.return_value.result.return_value = MOCK_DISK_COPY
    mock_get_instance.return_value = FAKE_INSTANCE
    mock_get_disk.return_value = FAKE_DISK
    mock_snapshot.return_value = FAKE_SNAPSHOT
    mock_snapshot_delete.return_value = None

    # CreateDiskCopy(zone, disk_name='fake-disk-name'). This should grab
    # the disk 'fake-disk-name'.
    disk_copy = forensics.CreateDiskCopy(
        FAKE_ACCOUNT.subscription_id, None, disk_name=FAKE_DISK.name)
    mock_get_instance.assert_not_called()
    mock_get_boot_disk.assert_not_called()
    mock_get_disk.assert_called_once()
    mock_get_disk.assert_called_with('fake-disk-name')
    self.assertIsInstance(disk_copy, compute.AZDisk)
    self.assertEqual('fake_snapshot_name_f4c186ac_copy', disk_copy.name)

  @mock.patch('libcloudforensics.providers.azure.internal.account.AZAccount.ListDisks')
  @mock.patch('libcloudforensics.providers.azure.internal.account.AZAccount.ListInstances')
  @typing.no_type_check
  def testCreateDiskCopy3(self, mock_list_instances, mock_list_disk):
    """Test that a disk copy is correctly created."""
    mock_list_instances.return_value = {}
    mock_list_disk.return_value = {}

    # Should raise a RuntimeError in GetInstance as we are querying a
    # non-existent instance.
    with self.assertRaises(RuntimeError):
      forensics.CreateDiskCopy(
          FAKE_ACCOUNT.subscription_id, 'non-existent-vm-name')

    # Should raise a RuntimeError in GetDisk as we are querying a
    # non-existent disk.
    with self.assertRaises(RuntimeError):
      forensics.CreateDiskCopy(
          FAKE_ACCOUNT.subscription_id,
          None,
          disk_name='non-existent-disk-name')


if __name__ == '__main__':
  unittest.main()
