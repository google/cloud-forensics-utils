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
"""Tests for the azure module - forensics.py"""

import typing
import unittest
import mock

from libcloudforensics import errors
from libcloudforensics.providers.azure.internal import compute

from libcloudforensics.providers.azure import forensics

from tests.providers.azure import azure_mocks


class AZForensicsTest(unittest.TestCase):
  """Test Azure forensics file."""
  # pylint: disable=line-too-long, too-many-arguments

  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZComputeDisk.GetDiskType')
  @mock.patch('libcloudforensics.providers.azure.internal.resource.AZResource.GetOrCreateResourceGroup')
  @mock.patch('libcloudforensics.providers.azure.internal.common.GetCredentials')
  @mock.patch('libcloudforensics.providers.azure.internal.resource.AZResource.ListSubscriptionIDs')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZComputeSnapshot.Delete')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZComputeDisk.Snapshot')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZCompute.GetDisk')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZComputeVirtualMachine.GetBootDisk')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZCompute.GetInstance')
  @mock.patch('azure.mgmt.compute.v2020_12_01.operations._disks_operations.DisksOperations.begin_create_or_update')
  @typing.no_type_check
  def testCreateDiskCopy1(self,
                          mock_create_disk,
                          mock_get_instance,
                          mock_get_boot_disk,
                          mock_get_disk,
                          mock_snapshot,
                          mock_snapshot_delete,
                          mock_list_subscription_ids,
                          mock_credentials,
                          mock_resource_group,
                          mock_disk_type):
    """Test that a disk copy is correctly created.

    CreateDiskCopy(zone, instance_name='fake-vm-name', region='fake-region').
    This should grab the boot disk of the instance.
    """
    mock_create_disk.return_value.done.return_value = True
    mock_create_disk.return_value.result.return_value = azure_mocks.MOCK_DISK_COPY
    mock_get_instance.return_value = azure_mocks.FAKE_INSTANCE
    mock_get_boot_disk.return_value = azure_mocks.FAKE_BOOT_DISK
    mock_snapshot.return_value = azure_mocks.FAKE_SNAPSHOT
    mock_snapshot_delete.return_value = None
    mock_list_subscription_ids.return_value = ['fake-subscription-id']
    mock_credentials.return_value = ('fake-subscription-id', mock.Mock())
    mock_resource_group.return_value = 'fake-resource-group'
    mock_disk_type.return_value = 'fake-disk-type'

    disk_copy = forensics.CreateDiskCopy(
        azure_mocks.FAKE_ACCOUNT.default_resource_group_name,
        instance_name=azure_mocks.FAKE_INSTANCE.name,
        region='fake-region')
    mock_get_instance.assert_called_once()
    mock_get_instance.assert_called_with('fake-vm-name')
    mock_get_boot_disk.assert_called_once()
    mock_get_disk.assert_not_called()
    self.assertIsInstance(disk_copy, compute.AZComputeDisk)
    self.assertEqual('fake_snapshot_name_f4c186ac_copy', disk_copy.name)

  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZComputeDisk.GetDiskType')
  @mock.patch('libcloudforensics.providers.azure.internal.resource.AZResource.GetOrCreateResourceGroup')
  @mock.patch('libcloudforensics.providers.azure.internal.common.GetCredentials')
  @mock.patch('libcloudforensics.providers.azure.internal.resource.AZResource.ListSubscriptionIDs')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZComputeSnapshot.Delete')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZComputeDisk.Snapshot')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZCompute.GetDisk')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZComputeVirtualMachine.GetBootDisk')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZCompute.GetInstance')
  @mock.patch('azure.mgmt.compute.v2020_12_01.operations._disks_operations.DisksOperations.begin_create_or_update')
  @typing.no_type_check
  def testCreateDiskCopy2(self,
                          mock_create_disk,
                          mock_get_instance,
                          mock_get_boot_disk,
                          mock_get_disk,
                          mock_snapshot,
                          mock_snapshot_delete,
                          mock_list_subscription_ids,
                          mock_credentials,
                          mock_resource_group,
                          mock_disk_type):
    """Test that a disk copy is correctly created.

    CreateDiskCopy(zone, disk_name='fake-disk-name', region='fake-region').
    This should grab the disk 'fake-disk-name'."""
    mock_create_disk.return_value.done.return_value = True
    mock_create_disk.return_value.result.return_value = azure_mocks.MOCK_DISK_COPY
    mock_get_instance.return_value = azure_mocks.FAKE_INSTANCE
    mock_get_disk.return_value = azure_mocks.FAKE_DISK
    mock_snapshot.return_value = azure_mocks.FAKE_SNAPSHOT
    mock_snapshot_delete.return_value = None
    mock_list_subscription_ids.return_value = ['fake-subscription-id']
    mock_credentials.return_value = ('fake-subscription-id', mock.Mock())
    mock_resource_group.return_value = 'fake-resource-group'
    mock_disk_type.return_value = 'fake-disk-type'

    disk_copy = forensics.CreateDiskCopy(
        azure_mocks.FAKE_ACCOUNT.default_resource_group_name,
        disk_name=azure_mocks.FAKE_DISK.name,
        region='fake-region')
    mock_get_instance.assert_not_called()
    mock_get_boot_disk.assert_not_called()
    mock_get_disk.assert_called_once()
    mock_get_disk.assert_called_with('fake-disk-name')
    self.assertIsInstance(disk_copy, compute.AZComputeDisk)
    self.assertEqual('fake_snapshot_name_f4c186ac_copy', disk_copy.name)

  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZComputeDisk.GetDiskType')
  @mock.patch('libcloudforensics.providers.azure.internal.resource.AZResource.GetOrCreateResourceGroup')
  @mock.patch('libcloudforensics.providers.azure.internal.common.GetCredentials')
  @mock.patch('libcloudforensics.providers.azure.internal.resource.AZResource.ListSubscriptionIDs')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZCompute.ListDisks')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZCompute.ListInstances')
  @typing.no_type_check
  def testCreateDiskCopy3(self,
                          mock_list_instances,
                          mock_list_disk,
                          mock_list_subscription_ids,
                          mock_credentials,
                          mock_resource_group,
                          mock_disk_type):
    """Test that a disk copy is correctly created.

    The first call should raise a RuntimeError in GetInstance as we are
    querying a non-existent instance. The second call should raise a
    RuntimeError in GetDisk as we are querying a non-existent disk."""
    mock_list_instances.return_value = {}
    mock_list_disk.return_value = {}
    mock_list_subscription_ids.return_value = ['fake-subscription-id']
    mock_credentials.return_value = ('fake-subscription-id', mock.Mock())
    mock_resource_group.return_value = 'fake-resource-group'
    mock_disk_type.return_value = 'fake-disk-type'

    with self.assertRaises(errors.ResourceCreationError) as error:
      forensics.CreateDiskCopy(
          azure_mocks.FAKE_ACCOUNT.default_resource_group_name,
          instance_name='non-existent-vm-name',
          region='fake-region')
    self.assertEqual(
        'Cannot copy disk "None": Instance non-existent-vm-name was not found '
        'in subscription fake-subscription-id', str(error.exception))

    with self.assertRaises(errors.ResourceCreationError) as error:
      forensics.CreateDiskCopy(
          azure_mocks.FAKE_ACCOUNT.default_resource_group_name,
          disk_name='non-existent-disk-name',
          region='fake-region')
    self.assertEqual(
        'Cannot copy disk "non-existent-disk-name": Disk non-existent-disk-name'
        ' was not found in subscription fake-subscription-id',
        str(error.exception))
