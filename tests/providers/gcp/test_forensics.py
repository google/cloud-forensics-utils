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
"""Tests for the gcp module - forensics.py"""

import typing
import unittest
import mock

from libcloudforensics import errors
from libcloudforensics.providers.gcp import forensics
from libcloudforensics.providers.gcp.internal import compute

from tests.providers.gcp import gcp_mocks


class GCPForensicsTest(unittest.TestCase):
  """Test forensics.py methods and common.py helper methods."""
  # pylint: disable=line-too-long

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeDisk.GetDiskType')
  @mock.patch('libcloudforensics.providers.gcp.internal.common.GoogleCloudComputeClient.BlockOperation')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeInstance.GetDisk')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeInstance.GetBootDisk')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.GetInstance')
  @mock.patch('libcloudforensics.providers.gcp.internal.common.GoogleCloudComputeClient.GceApi')
  def testCreateDiskCopy1(self,
                          mock_gce_api,
                          mock_get_instance,
                          mock_get_boot_disk,
                          mock_get_disk,
                          mock_block_operation,
                          mock_disk_type):
    """Test that a disk from a remote project is duplicated and attached to
    an analysis project. """
    instances = mock_gce_api.return_value.instances.return_value.aggregatedList
    instances.return_value.execute.return_value = gcp_mocks.MOCK_INSTANCES_AGGREGATED
    mock_get_instance.return_value = gcp_mocks.FAKE_INSTANCE
    mock_get_boot_disk.return_value = gcp_mocks.FAKE_BOOT_DISK
    mock_block_operation.return_value = None
    mock_disk_type.return_value = 'fake-disk-type'

    # create_disk_copy(
    #     src_proj,
    #     dst_proj,
    #     zone='fake-zone',
    #     instance_name='fake-instance',
    #     disk_name=None) Should grab the boot disk
    new_disk = forensics.CreateDiskCopy(gcp_mocks.FAKE_SOURCE_PROJECT.project_id,
                                        gcp_mocks.FAKE_ANALYSIS_PROJECT.project_id,
                                        zone=gcp_mocks.FAKE_INSTANCE.zone,
                                        instance_name=gcp_mocks.FAKE_INSTANCE.name)
    mock_get_instance.assert_called_with(gcp_mocks.FAKE_INSTANCE.name)
    mock_get_disk.assert_not_called()
    self.assertIsInstance(new_disk, compute.GoogleComputeDisk)
    self.assertTrue(new_disk.name.startswith('evidence-'))
    self.assertIn('fake-boot-disk', new_disk.name)
    self.assertTrue(new_disk.name.endswith('-copy'))

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeDisk.GetDiskType')
  @mock.patch('libcloudforensics.providers.gcp.internal.common.GoogleCloudComputeClient.BlockOperation')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeInstance.GetBootDisk')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.GetDisk')
  @mock.patch('libcloudforensics.providers.gcp.internal.common.GoogleCloudComputeClient.GceApi')
  def testCreateDiskCopy2(self,
                          mock_gce_api,
                          mock_get_disk,
                          mock_get_boot_disk,
                          mock_block_operation,
                          mock_disk_type):
    """Test that a disk from a remote project is duplicated and attached to
    an analysis project. """
    instances = mock_gce_api.return_value.instances.return_value.aggregatedList
    instances.return_value.execute.return_value = gcp_mocks.MOCK_INSTANCES_AGGREGATED
    mock_get_disk.return_value = gcp_mocks.FAKE_DISK
    mock_block_operation.return_value = None
    mock_disk_type.return_value = 'fake-disk-type'

    # create_disk_copy(
    #     src_proj,
    #     dst_proj,
    #     zone='fake-zone',
    #     instance_name=None,
    #     disk_name='fake-disk') Should grab 'fake-disk'
    new_disk = forensics.CreateDiskCopy(gcp_mocks.FAKE_SOURCE_PROJECT.project_id,
                                        gcp_mocks.FAKE_ANALYSIS_PROJECT.project_id,
                                        zone=gcp_mocks.FAKE_INSTANCE.zone,
                                        disk_name=gcp_mocks.FAKE_DISK.name)
    mock_get_disk.assert_called_with(gcp_mocks.FAKE_DISK.name)
    mock_get_boot_disk.assert_not_called()
    self.assertIsInstance(new_disk, compute.GoogleComputeDisk)
    self.assertTrue(new_disk.name.startswith('evidence-'))
    self.assertIn('fake-disk', new_disk.name)
    self.assertTrue(new_disk.name.endswith('-copy'))

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.ListInstances')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.ListDisks')
  def testCreateDiskCopy3(self, mock_list_disks, mock_list_instances):
    """Test that a disk from a remote project is duplicated and attached to
    an analysis project. """
    mock_list_disks.return_value = gcp_mocks.MOCK_DISKS_AGGREGATED
    mock_list_instances.return_value = gcp_mocks.MOCK_INSTANCES_AGGREGATED

    # create_disk_copy(
    #     src_proj,
    #     dst_proj,
    #     zone='fake-zone',
    #     instance_name=None,
    #     disk_name='non-existent-disk') Should raise an exception
    with self.assertRaises(errors.ResourceNotFoundError):
      forensics.CreateDiskCopy(gcp_mocks.FAKE_SOURCE_PROJECT.project_id,
                               gcp_mocks.FAKE_ANALYSIS_PROJECT.project_id,
                               zone=gcp_mocks.FAKE_INSTANCE.zone,
                               disk_name='non-existent-disk')

    # create_disk_copy(
    #     src_proj,
    #     dst_proj,
    #     instance_name='non-existent-instance',
    #     zone='fake-zone',
    #     disk_name=None) Should raise an exception
    with self.assertRaises(errors.ResourceNotFoundError):
      forensics.CreateDiskCopy(gcp_mocks.FAKE_SOURCE_PROJECT.project_id,
                               gcp_mocks.FAKE_ANALYSIS_PROJECT.project_id,
                               instance_name='non-existent-instance',
                               zone=gcp_mocks.FAKE_INSTANCE.zone, disk_name='')
