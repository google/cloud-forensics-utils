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
"""Tests for the gcp module - compute.py"""

import os
import typing
import unittest
import mock
import six
from googleapiclient.errors import HttpError

from libcloudforensics import errors
from libcloudforensics.scripts import utils
from libcloudforensics.providers.gcp.internal import compute
from tests.providers.gcp import gcp_mocks


class GoogleCloudComputeTest(unittest.TestCase):
  """Test Google Cloud compute class."""
  # pylint: disable=line-too-long

  @typing.no_type_check
  def testFormatLogMessage(self):
    """Test formatting log message."""
    msg = 'Test message'
    formatted_msg = gcp_mocks.FAKE_INSTANCE.FormatLogMessage(msg)
    self.assertIsInstance(formatted_msg, six.string_types)
    self.assertEqual('project:fake-source-project Test message', formatted_msg)

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.common.GoogleCloudComputeClient.GceApi')
  def testListInstances(self, mock_gce_api):
    """Test that instances of project are correctly listed."""
    instances = mock_gce_api.return_value.instances.return_value.aggregatedList
    instances.return_value.execute.return_value = gcp_mocks.MOCK_INSTANCES_AGGREGATED
    list_instances = gcp_mocks.FAKE_ANALYSIS_PROJECT.compute.ListInstances()
    self.assertEqual(1, len(list_instances))
    self.assertEqual('fake-instance', list_instances['fake-instance'].name)
    self.assertEqual('fake-zone', list_instances['fake-instance'].zone)

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.common.GoogleCloudComputeClient.BlockOperation')
  @mock.patch('libcloudforensics.providers.gcp.internal.common.GoogleCloudComputeClient.GceApi')
  def testAbandonInstance(self, mock_gce_api, mock_block_operation):
    """Test that instance is abandoned from Managed Instance Group."""
    mig = mock_gce_api.return_value.instanceGroupManagers.return_value.abandonInstances
    mig_request = mig.return_value.execute
    mig_request.return_value = gcp_mocks.MOCK_INSTANCE_ABANDONED
    mock_block_operation.return_value = gcp_mocks.MOCK_INSTANCE_ABANDONED
    # Check that call completes succesfully
    gcp_mocks.FAKE_INSTANCE.AbandonFromMIG('fake-instance-group')
    self.assertTrue(mig_request.called)

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.common.GoogleCloudComputeClient.GceApi')
  def testListDisks(self, mock_gce_api):
    """Test that disks of instances are correctly listed."""
    disks = mock_gce_api.return_value.disks.return_value.aggregatedList
    disks.return_value.execute.return_value = gcp_mocks.MOCK_DISKS_AGGREGATED
    list_disks = gcp_mocks.FAKE_ANALYSIS_PROJECT.compute.ListDisks()
    self.assertEqual(2, len(list_disks))
    self.assertEqual('fake-disk', list_disks['fake-disk'].name)
    self.assertEqual('fake-boot-disk', list_disks['fake-boot-disk'].name)
    self.assertEqual('fake-zone', list_disks['fake-disk'].zone)
    self.assertEqual('fake-zone', list_disks['fake-boot-disk'].zone)

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.ListInstances')
  def testGetInstance(self, mock_list_instances):
    """Test that an instance of a project can be found."""
    mock_list_instances.return_value = gcp_mocks.MOCK_LIST_INSTANCES
    found_instance = gcp_mocks.FAKE_SOURCE_PROJECT.compute.GetInstance(gcp_mocks.FAKE_INSTANCE.name)
    self.assertIsInstance(found_instance, compute.GoogleComputeInstance)
    self.assertEqual(gcp_mocks.FAKE_SOURCE_PROJECT.project_id, found_instance.project_id)
    self.assertEqual('fake-instance', found_instance.name)
    self.assertEqual('fake-zone', found_instance.zone)
    # pylint: disable=protected-access
    self.assertEqual(gcp_mocks.FAKE_INSTANCE._data, found_instance._data)
    # pylint: enable=protected-access
    with self.assertRaises(errors.ResourceNotFoundError):
      gcp_mocks.FAKE_SOURCE_PROJECT.compute.GetInstance('non-existent-instance')

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.ListDisks')
  def testGetDisk(self, mock_list_disks):
    """Test that a disk of an instance can be found."""
    mock_list_disks.return_value = gcp_mocks.MOCK_LIST_DISKS
    found_disk = gcp_mocks.FAKE_SOURCE_PROJECT.compute.GetDisk(gcp_mocks.FAKE_DISK.name)
    self.assertIsInstance(found_disk, compute.GoogleComputeDisk)
    self.assertEqual(gcp_mocks.FAKE_SOURCE_PROJECT.project_id, found_disk.project_id)
    self.assertEqual('fake-disk', found_disk.name)
    self.assertEqual('fake-zone', found_disk.zone)
    with self.assertRaises(errors.ResourceNotFoundError):
      gcp_mocks.FAKE_SOURCE_PROJECT.compute.GetDisk('non-existent-disk')

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.common.GoogleCloudComputeClient.BlockOperation')
  @mock.patch('libcloudforensics.providers.gcp.internal.common.GoogleCloudComputeClient.GceApi')
  def testCreateDiskFromSnapshot(self, mock_gce_api, mock_block_operation):
    """Test the creation of a disk from a Snapshot."""
    mock_block_operation.return_value = None
    disks = mock_gce_api.return_value.disks
    disks.return_value.insert.return_value.execute.return_value = None

    # CreateDiskFromSnapshot(Snapshot=gcp_mocks.FAKE_SNAPSHOT, disk_name=None,
    # disk_name_prefix='')
    disk_from_snapshot = gcp_mocks.FAKE_ANALYSIS_PROJECT.compute.CreateDiskFromSnapshot(
        gcp_mocks.FAKE_SNAPSHOT)
    self.assertIsInstance(disk_from_snapshot, compute.GoogleComputeDisk)
    self.assertEqual('fake-snapshot-857c0b16-copy', disk_from_snapshot.name)

    # CreateDiskFromSnapshot(Snapshot=gcp_mocks.FAKE_SNAPSHOT,
    # disk_name='new-forensics-disk', disk_name_prefix='')
    disk_from_snapshot = gcp_mocks.FAKE_ANALYSIS_PROJECT.compute.CreateDiskFromSnapshot(
        gcp_mocks.FAKE_SNAPSHOT, disk_name='new-forensics-disk')
    self.assertIsInstance(
        disk_from_snapshot, compute.GoogleComputeDisk)
    self.assertEqual('new-forensics-disk', disk_from_snapshot.name)

    # CreateDiskFromSnapshot(Snapshot=gcp_mocks.FAKE_SNAPSHOT, disk_name=None,
    # disk_name_prefix='prefix')
    disk_from_snapshot = gcp_mocks.FAKE_ANALYSIS_PROJECT.compute.CreateDiskFromSnapshot(
        gcp_mocks.FAKE_SNAPSHOT, disk_name_prefix='prefix')
    self.assertIsInstance(
        disk_from_snapshot, compute.GoogleComputeDisk)
    self.assertEqual(
        'prefix-fake-snapshot-857c0b16-copy', disk_from_snapshot.name)

    # CreateDiskFromSnapshot(Snapshot=gcp_mocks.FAKE_SNAPSHOT,
    # disk_name='new-forensics-disk', disk_name_prefix='prefix')
    disk_from_snapshot = gcp_mocks.FAKE_ANALYSIS_PROJECT.compute.CreateDiskFromSnapshot(
        gcp_mocks.FAKE_SNAPSHOT, disk_name='new-forensics-disk',
        disk_name_prefix='prefix')
    self.assertIsInstance(
        disk_from_snapshot, compute.GoogleComputeDisk)
    self.assertEqual('new-forensics-disk', disk_from_snapshot.name)

    # CreateDiskFromSnapshot(Snapshot=gcp_mocks.FAKE_SNAPSHOT,
    # disk_name='fake-disk') where 'fake-disk' exists already
    disks.return_value.insert.return_value.execute.side_effect = HttpError(
        resp=mock.Mock(status=409), content=b'Disk already exists')
    with self.assertRaises(errors.ResourceCreationError) as context:
      _ = gcp_mocks.FAKE_ANALYSIS_PROJECT.compute.CreateDiskFromSnapshot(
          gcp_mocks.FAKE_SNAPSHOT, disk_name=gcp_mocks.FAKE_DISK.name)
    self.assertIn(
        'Disk {0:s} already exists'.format('fake-disk'), str(context.exception))

    # other network issue should fail the disk creation
    disks.return_value.insert.return_value.execute.side_effect = HttpError(
        resp=mock.Mock(status=418), content=b'I am a teapot')
    with self.assertRaises(errors.ResourceCreationError) as context:
      _ = gcp_mocks.FAKE_ANALYSIS_PROJECT.compute.CreateDiskFromSnapshot(
          gcp_mocks.FAKE_SNAPSHOT, gcp_mocks.FAKE_DISK.name)
    self.assertIn(
        'Unknown error occurred when creating disk from Snapshot',
        str(context.exception))

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.GetInstance')
  @mock.patch('libcloudforensics.providers.gcp.internal.common.GoogleCloudComputeClient.BlockOperation')
  @mock.patch('libcloudforensics.providers.gcp.internal.common.GoogleCloudComputeClient.GceApi')
  def testGetOrCreateAnalysisVm(
      self, mock_gce_api, mock_block_operation, mock_get_instance):
    """Test that a new virtual machine is created if it doesn't exist,
    or that the existing one is returned. """
    images = mock_gce_api.return_value.images
    images.return_value.getFromFamily.return_value.execute.return_value = {
        'selfLink': 'value'
    }
    instances = mock_gce_api.return_value.instances
    instances.return_value.insert.return_value.execute.return_value = None
    mock_block_operation.return_value = None
    mock_get_instance.return_value = gcp_mocks.FAKE_ANALYSIS_VM

    # GetOrCreateAnalysisVm(existing_vm, boot_disk_size)
    vm, created = gcp_mocks.FAKE_ANALYSIS_PROJECT.compute.GetOrCreateAnalysisVm(
        gcp_mocks.FAKE_ANALYSIS_VM.name, boot_disk_size=1)
    mock_get_instance.assert_called_with(gcp_mocks.FAKE_ANALYSIS_VM.name)
    instances.return_value.insert.assert_not_called()
    self.assertIsInstance(vm, compute.GoogleComputeInstance)
    self.assertEqual('fake-analysis-vm', vm.name)
    self.assertFalse(created)

    # GetOrCreateAnalysisVm(non_existing_vm, boot_disk_size) mocking the
    # GetInstance() call to throw a ResourceNotFoundError error to mimic an
    # instance that wasn't found
    mock_get_instance.side_effect = errors.ResourceNotFoundError('', __name__)
    vm, created = gcp_mocks.FAKE_ANALYSIS_PROJECT.compute.GetOrCreateAnalysisVm(
        'non-existent-analysis-vm', boot_disk_size=1)
    mock_get_instance.assert_called_with('non-existent-analysis-vm')
    instances.return_value.insert.assert_called()
    self.assertIsInstance(vm, compute.GoogleComputeInstance)
    self.assertEqual('non-existent-analysis-vm', vm.name)
    self.assertTrue(created)

    # If specifying a number of CPU cores that's not available, should throw a
    # ValueError
    with self.assertRaises(ValueError):
      _, created = gcp_mocks.FAKE_ANALYSIS_PROJECT.compute.GetOrCreateAnalysisVm(
          'non-existent-analysis-vm', boot_disk_size=1, cpu_cores=5)

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.ListInstanceByLabels')
  @mock.patch('libcloudforensics.providers.gcp.internal.common.GoogleCloudComputeClient.GceApi')
  def testListInstanceByLabels(self, mock_gce_api, mock_labels):
    """Test that instances are correctly listed when searching with a filter."""
    mock_gce_api.return_value.instances.return_value = None
    mock_labels.return_value = gcp_mocks.MOCK_GCE_OPERATION_INSTANCES_LABELS_SUCCESS
    instances = gcp_mocks.FAKE_ANALYSIS_PROJECT.compute.ListInstanceByLabels(
        labels_filter={'id': '123'})
    if 'zone' in instances['items']:
      instance_names = [
          instance['name']
          for instance in instances['items']['zone']['instances']
      ]
    else:
      instance_names = []
    self.assertEqual(1, len(instance_names))
    self.assertIn(gcp_mocks.FAKE_INSTANCE.name, instance_names)

    # Labels not found, GCE API will return no items
    mock_labels.return_value = gcp_mocks.MOCK_GCE_OPERATION_LABELS_FAILED
    instances = gcp_mocks.FAKE_ANALYSIS_PROJECT.compute.ListInstanceByLabels(
        labels_filter={'id': '123'})
    if 'zone' in instances['items']:
      instance_names = [
          instance['name']
          for instance in instances['items']['zone']['instances']
      ]
    else:
      instance_names = []
    self.assertEqual(0, len(instance_names))

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.ListDiskByLabels')
  @mock.patch('libcloudforensics.providers.gcp.internal.common.GoogleCloudComputeClient.GceApi')
  def testListDiskByLabels(self, mock_gce_api, mock_labels):
    """Test that disks are correctly listed when searching with a filter."""
    mock_gce_api.return_value.disks.return_value = None
    mock_labels.return_value = gcp_mocks.MOCK_GCE_OPERATION_DISKS_LABELS_SUCCESS
    # Labels found, GCE API will return disks
    disks = gcp_mocks.FAKE_ANALYSIS_PROJECT.compute.ListDiskByLabels(
        labels_filter={
            'id': '123',
            'some': 'thing'
        })
    if 'zone' in disks['items']:
      disk_names = [disk['name'] for disk in disks['items']['zone']['disks']]
    else:
      disk_names = []
    self.assertEqual(2, len(disk_names))
    self.assertIn('fake-disk', disk_names)
    self.assertIn('fake-boot-disk', disk_names)

    # Labels not found, GCE API will return no items
    mock_labels.return_value = gcp_mocks.MOCK_GCE_OPERATION_LABELS_FAILED
    disks = gcp_mocks.FAKE_ANALYSIS_PROJECT.compute.ListDiskByLabels(
        labels_filter={'id': '123'})
    if 'zone' in disks['items']:
      disk_names = [disk['name'] for disk in disks['items']['zone']['disks']]
    else:
      disk_names = []
    self.assertEqual(0, len(disk_names))

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.common.GoogleCloudComputeClient.BlockOperation')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeImage')
  @mock.patch('libcloudforensics.providers.gcp.internal.common.GoogleCloudComputeClient.GceApi')
  def testCreateImageFromGcsTarGz(self, mock_gce_api, mock_gce_image, mock_block_operation):
    """Test that images are correctly imported from compressed tar archives in GCS."""
    mock_block_operation.return_value = None
    mock_gce_image.return_value = gcp_mocks.FAKE_IMAGE
    image_insert = mock_gce_api.return_value.images.return_value.insert
    image_insert.return_value.execute.return_value = {'name': 'fake-image'}
    image_object = gcp_mocks.FAKE_ANALYSIS_PROJECT.compute.CreateImageFromGcsTarGz(
        'gs://fake-bucket/fake-folder/image.tar.gz', 'fake-image')
    self.assertIn('fake-image', image_object.name)
    fake_image_body = {
        'name': 'fake-image',
        'rawDisk': {
            'source': 'https://storage.cloud.google.com/fake-bucket/fake-folder/image.tar.gz'
        }
    }
    image_insert.assert_called_with(project=gcp_mocks.FAKE_ANALYSIS_PROJECT.project_id,
                                    body=fake_image_body,
                                    forceCreate=True)

  @typing.no_type_check
  def testReadStartupScript(self):
    """Test that the startup script is correctly read."""
    # No environment variable set, reading default script
    # pylint: disable=protected-access
    script = utils.ReadStartupScript(utils.FORENSICS_STARTUP_SCRIPT_GCP)
    self.assertTrue(script.startswith('#!/bin/bash'))
    self.assertTrue(script.endswith('(exit ${exit_code})\n'))

    # Environment variable set to custom script
    os.environ['STARTUP_SCRIPT'] = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.realpath(__file__))))), gcp_mocks.STARTUP_SCRIPT)
    script = utils.ReadStartupScript()
    self.assertEqual('# THIS IS A CUSTOM BASH SCRIPT', script)

    # Bogus environment variable, should raise an exception
    os.environ['STARTUP_SCRIPT'] = '/bogus/path'
    with self.assertRaises(OSError):
      utils.ReadStartupScript()
    os.environ['STARTUP_SCRIPT'] = ''
    # pylint: enable=protected-access


class GoogleComputeInstanceTest(unittest.TestCase):
  """Test Google Cloud compute instance class."""
  # pylint: disable=line-too-long

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.ListDisks')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeInstance.GetOperation')
  def testGetBootDisk(self, mock_get_operation, mock_list_disks):
    """Test that a boot disk is retrieved if existing."""
    mock_get_operation.return_value = gcp_mocks.MOCK_GCE_OPERATION_INSTANCES_GET
    mock_list_disks.return_value = gcp_mocks.MOCK_LIST_DISKS

    boot_disk = gcp_mocks.FAKE_INSTANCE.GetBootDisk()
    self.assertIsInstance(boot_disk, compute.GoogleComputeDisk)
    self.assertEqual('fake-boot-disk', boot_disk.name)

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.ListDisks')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeInstance.GetOperation')
  def testGetDisk(self, mock_get_operation, mock_list_disks):
    """Test that a disk is retrieved by its name, if existing."""
    mock_get_operation.return_value = gcp_mocks.MOCK_GCE_OPERATION_INSTANCES_GET
    mock_list_disks.return_value = gcp_mocks.MOCK_LIST_DISKS

    # Normal disk
    disk = gcp_mocks.FAKE_INSTANCE.GetDisk(gcp_mocks.FAKE_DISK.name)
    self.assertIsInstance(disk, compute.GoogleComputeDisk)
    self.assertEqual('fake-disk', disk.name)

    # Boot disk
    disk = gcp_mocks.FAKE_INSTANCE.GetDisk(gcp_mocks.FAKE_BOOT_DISK.name)
    self.assertIsInstance(disk, compute.GoogleComputeDisk)
    self.assertEqual('fake-boot-disk', disk.name)

    # Disk that's not attached to the instance
    with self.assertRaises(errors.ResourceNotFoundError):
      gcp_mocks.FAKE_INSTANCE.GetDisk('non-existent-disk')

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.ListDisks')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeInstance.GetOperation')
  def testListDisks(self, mock_get_operation, mock_list_disks):
    """Test that all disks of an instance are correctly retrieved."""
    mock_get_operation.return_value = gcp_mocks.MOCK_GCE_OPERATION_INSTANCES_GET
    mock_list_disks.return_value = gcp_mocks.MOCK_LIST_DISKS

    disks = gcp_mocks.FAKE_INSTANCE.ListDisks()
    self.assertEqual(2, len(disks))
    self.assertEqual(['fake-boot-disk', 'fake-disk'], list(disks.keys()))

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.ListDisks')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeInstance.GetOperation')
  @mock.patch('libcloudforensics.providers.gcp.internal.common.GoogleCloudComputeClient.GceApi')
  @mock.patch('libcloudforensics.providers.gcp.internal.common.GoogleCloudComputeClient.BlockOperation')
  def testDelete(
      self, mock_block_operation, mock_gce_api, mock_get_operation,
      mock_list_disks):
    """Test that all disks of an instance are correctly deleted."""
    mock_block_operation.return_value = None
    mock_get_operation.return_value = gcp_mocks.MOCK_GCE_OPERATION_INSTANCES_GET
    mock_list_disks.return_value = gcp_mocks.MOCK_LIST_DISKS

    mock_disk_delete = mock_gce_api.return_value.disks.return_value.delete
    mock_disk_delete.return_value.execute.return_value = None

    gcp_mocks.FAKE_INSTANCE.Delete(delete_disks=True)
    calls = [
        mock.call(project='fake-source-project', disk='fake-boot-disk', zone='fake-zone'),
        mock.call().execute(),
        mock.call(project='fake-source-project', disk='fake-disk', zone='fake-zone'),
        mock.call().execute(),
    ]
    mock_disk_delete.assert_has_calls(calls)

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeInstance.GetOperation')
  @mock.patch('libcloudforensics.providers.gcp.internal.common.GoogleCloudComputeClient.GceApi')
  def testGetEffectiveFirewallRules(self, mock_gce_api, mock_get_operation):
    """Tests that firewall rules are properly formatted"""
    mock_get_operation.return_value = {'networkInterfaces': gcp_mocks.MOCK_NETWORK_INTERFACES}
    mock_gce_api.return_value.instances.return_value.getEffectiveFirewalls.return_value.execute.return_value = gcp_mocks.MOCK_EFFECTIVE_FIREWALLS
    fw_rules = gcp_mocks.FAKE_INSTANCE.GetEffectiveFirewallRules()
    self.assertDictEqual(
      fw_rules,
      {'nic0': [
        {
          'type': 'policy',
          'policy_level': 0,
          'priority': 1,
          'direction': 'INGRESS',
          'l4config': [{'ip_protocol': 'tcp'}],
          'ips': ['8.8.8.8/24'],
          'action': 'allow'
        },
        {
          'type': 'policy',
          'policy_level': 1,
          'priority': 1,
          'direction': 'INGRESS',
          'l4config': [{'ip_protocol': 'tcp'}],
          'ips': ['8.8.4.4/24'],
          'action': 'goto_next'
        },
        {
          'type': 'firewall',
          'policy_level': 999,
          'priority': 1000,
          'direction': 'INGRESS',
          'l4config': [{'ip_protocol': 'tcp'}],
          'ips': ['0.0.0.0/0'],
          'action':
          'allow'
        }]})


class GoogleComputeDiskTest(unittest.TestCase):
  """Test Google Cloud Compute Disk class."""
  # pylint: disable=line-too-long

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.common.GoogleCloudComputeClient.BlockOperation')
  @mock.patch('libcloudforensics.providers.gcp.internal.common.GoogleCloudComputeClient.GceApi')
  def testSnapshot(self, mock_gce_api, mock_block_operation):
    """Test that a Snapshot of the disk is created."""
    disks = mock_gce_api.return_value.disks
    disks.return_value.createSnapshot.return_value.execute.return_value = None
    mock_block_operation.return_value = None

    # Snapshot(snapshot_name=None). Snapshot should start with the disk's name
    snapshot = gcp_mocks.FAKE_DISK.Snapshot()
    self.assertIsInstance(snapshot, compute.GoogleComputeSnapshot)
    self.assertTrue(snapshot.name.startswith('fake-disk'))

    # Snapshot(snapshot_name='my-Snapshot'). Snapshot should start with
    # 'my-Snapshot'
    snapshot = gcp_mocks.FAKE_DISK.Snapshot(snapshot_name='my-snapshot')
    self.assertIsInstance(snapshot, compute.GoogleComputeSnapshot)
    self.assertTrue(snapshot.name.startswith('my-snapshot'))

    # Snapshot(snapshot_name='Non-compliant-name'). Should raise a ValueError
    with self.assertRaises(errors.InvalidNameError):
      gcp_mocks.FAKE_DISK.Snapshot('Non-compliant-name')


if __name__ == '__main__':
  unittest.main()
