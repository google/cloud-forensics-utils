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
"""Tests for gcp module."""

from __future__ import unicode_literals

import os
import unittest
import re

from googleapiclient.errors import HttpError

import mock
import six

from libcloudforensics import gcp

# For the forensics analysis
FAKE_ANALYSIS_PROJECT = gcp.GoogleCloudProject(
    'fake-target-project', 'fake-zone')
FAKE_ANALYSIS_VM = gcp.GoogleComputeInstance(
    FAKE_ANALYSIS_PROJECT, 'fake-zone', 'fake-analysis-vm')

# Source project with the instance that needs forensicating
FAKE_SOURCE_PROJECT = gcp.GoogleCloudProject('fake-source-project', 'fake-zone')
FAKE_INSTANCE = gcp.GoogleComputeInstance(
    FAKE_SOURCE_PROJECT, 'fake-zone', 'fake-instance')
FAKE_DISK = gcp.GoogleComputeDisk(FAKE_SOURCE_PROJECT, 'fake-zone', 'fake-disk')
FAKE_BOOT_DISK = gcp.GoogleComputeDisk(
    FAKE_SOURCE_PROJECT, 'fake-zone', 'fake-boot-disk')
FAKE_SNAPSHOT = gcp.GoogleComputeSnapshot(FAKE_DISK, 'fake-snapshot')
FAKE_SNAPSHOT_LONG_NAME = gcp.GoogleComputeSnapshot(
    FAKE_DISK,
    'this-is-a-kind-of-long-fake-snapshot-name-and-is-definitely-over-63-chars')
FAKE_DISK_COPY = gcp.GoogleComputeDisk(
    FAKE_SOURCE_PROJECT, 'fake-zone', 'fake-disk-copy')

# Mock struct to mimic GCP's API responses
MOCK_INSTANCES_AGGREGATED = {
    # See https://cloud.google.com/compute/docs/reference/rest/v1/instances
    # /aggregatedList for complete structure
    'items': {
        0: {
            'instances': [{
                'name': FAKE_INSTANCE.name,
                'zone': '/' + FAKE_INSTANCE.zone
            }]
        }
    }
}

MOCK_DISKS_AGGREGATED = {
    # See https://cloud.google.com/compute/docs/reference/rest/v1/disks
    # /aggregatedList for complete structure
    'items': {
        0: {
            'disks': [{
                'name': FAKE_BOOT_DISK.name,
                'zone': '/' + FAKE_BOOT_DISK.zone
            }]
        },
        1: {
            'disks': [{
                'name': FAKE_DISK.name,
                'zone': '/' + FAKE_DISK.zone
            }]
        }
    }
}

MOCK_LIST_INSTANCES = {FAKE_INSTANCE.name: FAKE_INSTANCE}

MOCK_LIST_DISKS = {
    FAKE_DISK.name: FAKE_DISK,
    FAKE_BOOT_DISK.name: FAKE_BOOT_DISK
}

MOCK_GCE_OPERATION_INSTANCES_LABELS_SUCCESS = {
    'items': {
        'zone': {
            'instances': [{
                'name': FAKE_INSTANCE.name,
                'zone': '/' + FAKE_INSTANCE.zone,
                'labels': {
                    'id': '123'
                }
            }]
        }
    }
}

MOCK_GCE_OPERATION_DISKS_LABELS_SUCCESS = {
    'items': {
        'zone': {
            'disks': [{
                'name': FAKE_DISK.name,
                'labels': {
                    'id': '123'
                }
            }, {
                'name': FAKE_BOOT_DISK.name,
                'labels': {
                    'some': 'thing'
                }
            }]
        }
    }
}

MOCK_GCE_OPERATION_LABELS_FAILED = {
    'items': {},
    'warning': {
        'code': 404,
        'message': 'Not Found'
    }
}

MOCK_GCE_OPERATION_INSTANCES_GET = {
    # See https://cloud.google.com/compute/docs/reference/rest/v1/instances/get
    # for complete structure
    'name':
        FAKE_INSTANCE.name,
    'disks': [{
        'boot': True,
        'source': '/' + FAKE_BOOT_DISK.name,
    }, {
        'boot': False,
        'source': '/' + FAKE_DISK.name,
        'initializeParams': {
            'diskName': FAKE_DISK.name
        }
    }]
}

# See: https://cloud.google.com/compute/docs/reference/rest/v1/disks
REGEX_DISK_NAME = re.compile('^(?=.{1,63}$)[a-z]([-a-z0-9]*[a-z0-9])?$')
STARTUP_SCRIPT = 'startup_script.sh'


class GoogleCloudProjectTest(unittest.TestCase):
  """Test Google Cloud project class."""

  def testFormatLogMessage(self):
    """Test formatting log message."""
    msg = 'Test message'
    formatted_msg = FAKE_ANALYSIS_PROJECT.FormatLogMessage(msg)
    self.assertIsInstance(formatted_msg, six.string_types)
    self.assertEqual('project:fake-target-project Test message', formatted_msg)

  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GceApi')
  def testListInstances(self, mock_gce_api):
    """Test that instances of project are correctly listed."""
    instances = mock_gce_api.return_value.instances.return_value.aggregatedList
    instances.return_value.execute.return_value = MOCK_INSTANCES_AGGREGATED
    list_instances = FAKE_ANALYSIS_PROJECT.ListInstances()
    self.assertEqual(1, len(list_instances))
    self.assertEqual('fake-instance', list_instances['fake-instance'].name)
    self.assertEqual('fake-zone', list_instances['fake-instance'].zone)

  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GceApi')
  def testListDisks(self, mock_gce_api):
    """Test that disks of instances are correctly listed."""
    disks = mock_gce_api.return_value.disks.return_value.aggregatedList
    disks.return_value.execute.return_value = MOCK_DISKS_AGGREGATED
    list_disks = FAKE_ANALYSIS_PROJECT.ListDisks()
    self.assertEqual(2, len(list_disks))
    self.assertEqual('fake-disk', list_disks['fake-disk'].name)
    self.assertEqual('fake-boot-disk', list_disks['fake-boot-disk'].name)
    self.assertEqual('fake-zone', list_disks['fake-disk'].zone)
    self.assertEqual('fake-zone', list_disks['fake-boot-disk'].zone)

  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.ListInstances')
  def testGetInstance(self, mock_list_instances):
    """Test that an instance of a project can be found."""
    mock_list_instances.return_value = MOCK_LIST_INSTANCES
    found_instance = FAKE_SOURCE_PROJECT.GetInstance(
        FAKE_INSTANCE.name)
    self.assertIsInstance(found_instance, gcp.GoogleComputeInstance)
    self.assertEqual(FAKE_SOURCE_PROJECT, found_instance.project)
    self.assertEqual('fake-instance', found_instance.name)
    self.assertEqual('fake-zone', found_instance.zone)
    # pylint: disable=protected-access
    self.assertEqual(FAKE_INSTANCE._data, found_instance._data)
    # pylint: enable=protected-access
    self.assertRaises(
        RuntimeError, FAKE_SOURCE_PROJECT.GetInstance, 'non-existent-instance')

  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.ListDisks')
  def testGetDisk(self, mock_list_disks):
    """Test that a disk of an instance can be found."""
    mock_list_disks.return_value = MOCK_LIST_DISKS
    found_disk = FAKE_SOURCE_PROJECT.GetDisk(FAKE_DISK.name)
    self.assertIsInstance(found_disk, gcp.GoogleComputeDisk)
    self.assertEqual(FAKE_SOURCE_PROJECT, found_disk.project)
    self.assertEqual('fake-disk', found_disk.name)
    self.assertEqual('fake-zone', found_disk.zone)
    self.assertRaises(
        RuntimeError, FAKE_SOURCE_PROJECT.GetDisk, 'non-existent-disk')

  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.BlockOperation')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GceApi')
  def testCreateDiskFromSnapshot(self, mock_gce_api, mock_block_operation):
    """Test the creation of a disk from a Snapshot."""
    mock_block_operation.return_value = None
    disks = mock_gce_api.return_value.disks
    disks.return_value.insert.return_value.execute.return_value = None

    # CreateDiskFromSnapshot(Snapshot=FAKE_SNAPSHOT, disk_name=None,
    # disk_name_prefix='')
    disk_from_snapshot = FAKE_ANALYSIS_PROJECT.CreateDiskFromSnapshot(
        FAKE_SNAPSHOT)
    self.assertIsInstance(disk_from_snapshot, gcp.GoogleComputeDisk)
    self.assertEqual('fake-snapshot-857c0b16-copy', disk_from_snapshot.name)

    # CreateDiskFromSnapshot(Snapshot=FAKE_SNAPSHOT,
    # disk_name='new-forensics-disk', disk_name_prefix='')
    disk_from_snapshot = FAKE_ANALYSIS_PROJECT.CreateDiskFromSnapshot(
        FAKE_SNAPSHOT, disk_name='new-forensics-disk')
    self.assertIsInstance(disk_from_snapshot, gcp.GoogleComputeDisk)
    self.assertEqual('new-forensics-disk', disk_from_snapshot.name)

    # CreateDiskFromSnapshot(Snapshot=FAKE_SNAPSHOT, disk_name=None,
    # disk_name_prefix='prefix')
    disk_from_snapshot = FAKE_ANALYSIS_PROJECT.CreateDiskFromSnapshot(
        FAKE_SNAPSHOT, disk_name_prefix='prefix')
    self.assertIsInstance(disk_from_snapshot, gcp.GoogleComputeDisk)
    self.assertEqual(
        'prefix-fake-snapshot-857c0b16-copy', disk_from_snapshot.name)

    # CreateDiskFromSnapshot(Snapshot=FAKE_SNAPSHOT,
    # disk_name='new-forensics-disk', disk_name_prefix='prefix')
    disk_from_snapshot = FAKE_ANALYSIS_PROJECT.CreateDiskFromSnapshot(
        FAKE_SNAPSHOT,
        disk_name='new-forensics-disk',
        disk_name_prefix='prefix')
    self.assertIsInstance(disk_from_snapshot, gcp.GoogleComputeDisk)
    self.assertEqual('new-forensics-disk', disk_from_snapshot.name)

    # CreateDiskFromSnapshot(Snapshot=FAKE_SNAPSHOT,
    # disk_name='fake-disk') where 'fake-disk' exists already
    disks.return_value.insert.return_value.execute.side_effect = HttpError(
        resp=mock.Mock(status=409),
        content=b'Disk already exists'
    )
    with self.assertRaises(RuntimeError) as context:
      _ = FAKE_ANALYSIS_PROJECT.CreateDiskFromSnapshot(
          FAKE_SNAPSHOT, disk_name=FAKE_DISK.name)
    self.assertEqual(
        'Disk {0:s} already exists'.format('fake-disk'), str(context.exception))

    # other network issue should fail the disk creation
    disks.return_value.insert.return_value.execute.side_effect = HttpError(
        resp=mock.Mock(status=418),
        content=b'I am a teapot'
    )
    with self.assertRaises(RuntimeError) as context:
      _ = FAKE_ANALYSIS_PROJECT.CreateDiskFromSnapshot(
          FAKE_SNAPSHOT, FAKE_DISK.name)
    self.assertIn('status: 418', str(context.exception))

  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GetInstance')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.BlockOperation')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GceApi')
  def testGetOrCreateAnalysisVm(
      self, mock_gce_api, mock_block_operation, mock_get_instance):
    """Test that a new virtual machine is created if it doesn't exist,
    or that the existing one is returned. """
    images = mock_gce_api.return_value.images
    images.return_value.getFromFamily.return_value.execute.return_value = {
        'selfLink': 'value'}
    instances = mock_gce_api.return_value.instances
    instances.return_value.insert.return_value .execute.return_value = None
    mock_block_operation.return_value = None
    mock_get_instance.return_value = FAKE_ANALYSIS_VM

    # GetOrCreateAnalysisVm(existing_vm, boot_disk_size)
    vm, created = FAKE_ANALYSIS_PROJECT.GetOrCreateAnalysisVm(
        FAKE_ANALYSIS_VM.name, boot_disk_size=1)
    self.assertIsInstance(vm, gcp.GoogleComputeInstance)
    self.assertEqual('fake-analysis-vm', vm.name)
    self.assertFalse(created)

    # GetOrCreateAnalysisVm(non_existing_vm, boot_disk_size) mocking the
    # GetInstance() call to throw a runtime error to mimic an instance that
    # wasn't found
    mock_get_instance.side_effect = RuntimeError()
    vm, created = FAKE_ANALYSIS_PROJECT.GetOrCreateAnalysisVm(
        'non-existent-analysis-vm', boot_disk_size=1)
    self.assertIsInstance(vm, gcp.GoogleComputeInstance)
    self.assertEqual('non-existent-analysis-vm', vm.name)
    self.assertTrue(created)

  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.ListInstanceByLabels')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GceApi')
  def testListInstanceByLabels(
      self, mock_gce_api, mock_labels):
    """Test that instances are correctly listed when searching with a filter."""
    mock_gce_api.return_value.instances.return_value = None
    mock_labels.return_value = MOCK_GCE_OPERATION_INSTANCES_LABELS_SUCCESS
    instances = FAKE_ANALYSIS_PROJECT.ListInstanceByLabels(
        labels_filter={'id': '123'})
    if 'zone' in instances['items']:
      instance_names = [
          instance['name']
          for instance in instances['items']['zone']['instances']
      ]
    else:
      instance_names = []
    self.assertEqual(1, len(instance_names))
    self.assertIn(FAKE_INSTANCE.name, instance_names)

    # Labels not found, GCE API will return no items
    mock_labels.return_value = MOCK_GCE_OPERATION_LABELS_FAILED
    instances = FAKE_ANALYSIS_PROJECT.ListInstanceByLabels(
        labels_filter={'id': '123'})
    if 'zone' in instances['items']:
      instance_names = [
          instance['name']
          for instance in instances['items']['zone']['instances']
      ]
    else:
      instance_names = []
    self.assertEqual(0, len(instance_names))

  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.ListDiskByLabels')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GceApi')
  def testListDisksByLabels(self, mock_gce_api, mock_labels):
    """Test that disks are correctly listed when searching with a filter."""
    mock_gce_api.return_value.disks.return_value = None
    mock_labels.return_value = MOCK_GCE_OPERATION_DISKS_LABELS_SUCCESS
    # Labels found, GCE API will return disks
    disks = FAKE_ANALYSIS_PROJECT.ListDiskByLabels(
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
    mock_labels.return_value = MOCK_GCE_OPERATION_LABELS_FAILED
    disks = FAKE_ANALYSIS_PROJECT.ListDiskByLabels(labels_filter={'id': '123'})
    if 'zone' in disks['items']:
      disk_names = [disk['name'] for disk in disks['items']['zone']['disks']]
    else:
      disk_names = []
    self.assertEqual(0, len(disk_names))

  def testReadStartupScript(self):
    """Test that the startup script is correctly read."""
    # No environment variable set, reading default script
    # pylint: disable=protected-access
    script = FAKE_SOURCE_PROJECT._ReadStartupScript()
    self.assertTrue(script.startswith('#!/bin/bash'))
    self.assertTrue(script.endswith('(exit ${exit_code})\n'))

    # Environment variable set to custom script
    os.environ['STARTUP_SCRIPT'] = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), STARTUP_SCRIPT)
    script = FAKE_SOURCE_PROJECT._ReadStartupScript()
    self.assertEqual('# THIS IS A CUSTOM BASH SCRIPT', script)

    # Bogus environment variable, should raise an exception
    os.environ['STARTUP_SCRIPT'] = '/bogus/path'
    self.assertRaises(OSError, FAKE_SOURCE_PROJECT._ReadStartupScript)
    os.environ['STARTUP_SCRIPT'] = ''
    # pylint: enable=protected-access


class GoogleComputeBaseResourceTest(unittest.TestCase):
  """Test Google Cloud Compute Base Resource class."""

  @mock.patch('libcloudforensics.gcp.GoogleComputeInstance.GetOperation')
  def testGetValue(self, mock_get_operation):
    """Test that the correct value is retrieved for the given key."""
    mock_get_operation.return_value = {
        # https://cloud.google.com/compute/docs/reference/rest/v1/instances/get
        'name': FAKE_INSTANCE.name
    }
    self.assertEqual('fake-instance', FAKE_INSTANCE.GetValue('name'))
    self.assertIsNone(FAKE_INSTANCE.GetValue('key'))


class GoogleComputeInstanceTest(unittest.TestCase):
  """Test Google Cloud Compute Instance class."""

  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.ListDisks')
  @mock.patch('libcloudforensics.gcp.GoogleComputeInstance.GetOperation')
  def testGetBootDisk(self, mock_get_operation, mock_list_disks):
    """Test that a boot disk is retrieved if existing."""
    mock_get_operation.return_value = MOCK_GCE_OPERATION_INSTANCES_GET
    mock_list_disks.return_value = MOCK_LIST_DISKS

    boot_disk = FAKE_INSTANCE.GetBootDisk()
    self.assertIsInstance(boot_disk, gcp.GoogleComputeDisk)
    self.assertEqual('fake-boot-disk', boot_disk.name)

  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.ListDisks')
  @mock.patch('libcloudforensics.gcp.GoogleComputeInstance.GetOperation')
  def testGetDisk(self, mock_get_operation, mock_list_disks):
    """Test that a disk is retrieved by its name, if existing."""
    mock_get_operation.return_value = MOCK_GCE_OPERATION_INSTANCES_GET
    mock_list_disks.return_value = MOCK_LIST_DISKS

    # Normal disk
    disk = FAKE_INSTANCE.GetDisk(FAKE_DISK.name)
    self.assertIsInstance(disk, gcp.GoogleComputeDisk)
    self.assertEqual('fake-disk', disk.name)

    # Boot disk
    disk = FAKE_INSTANCE.GetDisk(FAKE_BOOT_DISK.name)
    self.assertIsInstance(disk, gcp.GoogleComputeDisk)
    self.assertEqual('fake-boot-disk', disk.name)

    # Disk that's not attached to the instance
    self.assertRaises(RuntimeError, FAKE_INSTANCE.GetDisk, 'non-existent-disk')

  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.ListDisks')
  @mock.patch('libcloudforensics.gcp.GoogleComputeInstance.GetOperation')
  def testListDisks(self, mock_get_operation, mock_list_disks):
    """Test that a all disks of an instance are correctly retrieved."""
    mock_get_operation.return_value = MOCK_GCE_OPERATION_INSTANCES_GET
    mock_list_disks.return_value = MOCK_LIST_DISKS

    disks = FAKE_INSTANCE.ListDisks()
    self.assertEqual(2, len(disks))
    self.assertEqual(['fake-boot-disk', 'fake-disk'], disks)


class GoogleComputeDiskTest(unittest.TestCase):
  """Test Google Cloud Compute Disk class."""

  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.BlockOperation')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GceApi')
  def testSnapshot(self, mock_gce_api, mock_block_operation):
    """Test that a Snapshot of the disk is created."""
    disks = mock_gce_api.return_value.disks
    disks.return_value.createSnapshot.return_value.execute.return_value = None
    mock_block_operation.return_value = None

    # Snapshot(snapshot_name=None). Snapshot should start with the disk's name
    snapshot = FAKE_DISK.Snapshot()
    self.assertIsInstance(snapshot, gcp.GoogleComputeSnapshot)
    self.assertTrue(snapshot.name.startswith('fake-disk'))

    # Snapshot(snapshot_name='my-Snapshot'). Snapshot should start with
    # 'my-Snapshot'
    snapshot = FAKE_DISK.Snapshot(snapshot_name='my-snapshot')
    self.assertIsInstance(snapshot, gcp.GoogleComputeSnapshot)
    self.assertTrue(snapshot.name.startswith('my-snapshot'))

    # Snapshot(snapshot_name='Non-compliant-name'). Should raise a ValueError
    self.assertRaises(ValueError, FAKE_DISK.Snapshot, 'Non-compliant-name')


class GCPTest(unittest.TestCase):
  """Test the gcp.py public methods."""

  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.BlockOperation')
  @mock.patch('libcloudforensics.gcp.GoogleComputeInstance.GetBootDisk')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GetInstance')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GceApi')
  def testCreateDiskCopy1(self,
                          mock_gce_api,
                          mock_get_instance,
                          mock_get_boot_disk,
                          mock_block_operation):
    """Test that a disk from a remote project is duplicated and attached to
    an analysis project. """
    instances = mock_gce_api.return_value.instances.return_value.aggregatedList
    instances.return_value.execute.return_value = MOCK_INSTANCES_AGGREGATED
    mock_get_instance.return_value = FAKE_INSTANCE
    mock_get_boot_disk.return_value = FAKE_BOOT_DISK
    mock_block_operation.return_value = None

    # create_disk_copy(src_proj, dst_proj, instance_name='fake-instance',
    #     zone='fake-zone', disk_name=None) Should grab the boot disk
    new_disk = gcp.CreateDiskCopy(
        FAKE_SOURCE_PROJECT.project_id,
        FAKE_ANALYSIS_PROJECT.project_id,
        instance_name=FAKE_INSTANCE.name,
        zone=FAKE_INSTANCE.zone,
        disk_name=None)
    self.assertIsInstance(new_disk, gcp.GoogleComputeDisk)
    self.assertTrue(new_disk.name.startswith('evidence-'))
    self.assertIn('fake-boot-disk', new_disk.name)
    self.assertTrue(new_disk.name.endswith('-copy'))

  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.BlockOperation')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GetDisk')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GceApi')
  def testCreateDiskCopy2(self,
                          mock_gce_api,
                          mock_get_disk,
                          mock_block_operation):
    """Test that a disk from a remote project is duplicated and attached to
    an analysis project. """
    instances = mock_gce_api.return_value.instances.return_value.aggregatedList
    instances.return_value.execute.return_value = MOCK_INSTANCES_AGGREGATED
    mock_get_disk.return_value = FAKE_DISK
    mock_block_operation.return_value = None

    # create_disk_copy(
    #     src_proj,
    #     dst_proj,
    #     instance_name=None,
    #     zone='fake-zone',
    #     disk_name='fake-disk') Should grab 'fake-disk'
    new_disk = gcp.CreateDiskCopy(
        FAKE_SOURCE_PROJECT.project_id,
        FAKE_ANALYSIS_PROJECT.project_id,
        instance_name=None,
        zone=FAKE_INSTANCE.zone,
        disk_name=FAKE_DISK.name)
    self.assertIsInstance(new_disk, gcp.GoogleComputeDisk)
    self.assertTrue(new_disk.name.startswith('evidence-'))
    self.assertIn('fake-disk', new_disk.name)
    self.assertTrue(new_disk.name.endswith('-copy'))

  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.ListInstances')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.ListDisks')
  def testCreateDiskCopy3(self, mock_list_disks, mock_list_instances):
    """Test that a disk from a remote project is duplicated and attached to
    an analysis project. """
    mock_list_disks.return_value = MOCK_DISKS_AGGREGATED
    mock_list_instances.return_value = MOCK_INSTANCES_AGGREGATED

    # create_disk_copy(
    #     src_proj,
    #     dst_proj,
    #     instance_name=None,
    #     zone='fake-zone',
    #     disk_name='non-existent-disk') Should raise an exception
    self.assertRaises(
        RuntimeError,
        gcp.CreateDiskCopy,
        FAKE_SOURCE_PROJECT.project_id,
        FAKE_ANALYSIS_PROJECT.project_id,
        instance_name=None,
        zone=FAKE_INSTANCE.zone,
        disk_name='non-existent-disk')

    # create_disk_copy(
    #     src_proj,
    #     dst_proj,
    #     instance_name='non-existent-instance',
    #     zone='fake-zone',
    #     disk_name=None) Should raise an exception
    self.assertRaises(
        RuntimeError, gcp.CreateDiskCopy,
        FAKE_SOURCE_PROJECT.project_id,
        FAKE_ANALYSIS_PROJECT.project_id,
        instance_name='non-existent-instance',
        zone=FAKE_INSTANCE.zone,
        disk_name='')

  def testGenerateDiskName(self):
    """Test that the generated disk name is always within GCP boundaries.

    The disk name must comply with the following RegEx:
      - ^(?=.{1,63}$)[a-z]([-a-z0-9]*[a-z0-9])?$

    i.e., it must be between 1 and 63 chars, the first character must be a
    lowercase letter, and all following characters must be a dash, lowercase
    letter, or digit, except the last character, which cannot be a dash.
    """

    disk_name = gcp.GenerateDiskName(FAKE_SNAPSHOT)
    self.assertEqual('fake-snapshot-857c0b16-copy', disk_name)
    self.assertTrue(REGEX_DISK_NAME.match(disk_name))

    disk_name = gcp.GenerateDiskName(FAKE_SNAPSHOT_LONG_NAME)
    self.assertEqual(
        'this-is-a-kind-of-long-fake-snapshot-name-and-is--857c0b16-copy',
        disk_name)
    self.assertTrue(REGEX_DISK_NAME.match(disk_name))

    disk_name = gcp.GenerateDiskName(
        FAKE_SNAPSHOT, disk_name_prefix='some-not-so-long-disk-name-prefix')
    self.assertEqual(
        'some-not-so-long-disk-name-prefix-fake-snapshot-857c0b16-copy',
        disk_name)
    self.assertTrue(REGEX_DISK_NAME.match(disk_name))

    disk_name = gcp.GenerateDiskName(
        FAKE_SNAPSHOT_LONG_NAME,
        disk_name_prefix='some-not-so-long-disk-name-prefix')
    self.assertEqual(
        'some-not-so-long-disk-name-prefix-this-is-a-kind--857c0b16-copy',
        disk_name)
    self.assertTrue(REGEX_DISK_NAME.match(disk_name))

    disk_name = gcp.GenerateDiskName(
        FAKE_SNAPSHOT,
        disk_name_prefix='some-really-really-really-really-really-really-long'
        '-disk-name-prefix')
    self.assertEqual(
        'some-really-really-really-really-really-really-lo-857c0b16-copy',
        disk_name)
    self.assertTrue(REGEX_DISK_NAME.match(disk_name))

    disk_name = gcp.GenerateDiskName(
        FAKE_SNAPSHOT_LONG_NAME,
        disk_name_prefix='some-really-really-really-really-really-really-long'
        '-disk-name-prefix')
    self.assertEqual(
        'some-really-really-really-really-really-really-lo-857c0b16-copy',
        disk_name)
    self.assertTrue(REGEX_DISK_NAME.match(disk_name))

    # Disk prefix cannot start with a capital letter
    self.assertRaises(
        ValueError,
        gcp.GenerateDiskName,
        FAKE_SNAPSHOT,
        'Some-prefix-that-starts-with-a-capital-letter')


if __name__ == '__main__':
  unittest.main()
