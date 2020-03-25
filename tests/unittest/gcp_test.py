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

import unittest
import re

from googleapiclient.errors import HttpError

import mock
import six

from libcloudforensics import gcp

# For the forensics analysis
FAKE_ANALYSIS_PROJECT = gcp.GoogleCloudProject(
    'fake-target-project',
    'fake-zone'
)
FAKE_ANALYSIS_VM = gcp.GoogleComputeInstance(
    FAKE_ANALYSIS_PROJECT,
    'fake-zone',
    'fake-analysis-vm'
)

# Source project with the instance that needs forensicating
FAKE_SOURCE_PROJECT = gcp.GoogleCloudProject(
    'fake-source-project',
    'fake-zone'
)
FAKE_INSTANCE = gcp.GoogleComputeInstance(
    FAKE_SOURCE_PROJECT,
    'fake-zone',
    'fake-instance'
)
FAKE_DISK = gcp.GoogleComputeDisk(
    FAKE_SOURCE_PROJECT,
    'fake-zone',
    'fake-disk'
)
FAKE_BOOT_DISK = gcp.GoogleComputeDisk(
    FAKE_SOURCE_PROJECT,
    'fake-zone',
    'fake-boot-disk'
)
FAKE_SNAPSHOT = gcp.GoogleComputeSnapshot(
    FAKE_DISK,
    'fake-snapshot'
)
FAKE_SNAPSHOT_LONG_NAME = gcp.GoogleComputeSnapshot(
    FAKE_DISK,
    'this-is-a-kind-of-long-fake-snapshot-name-and-is-definitely-over-63-chars'
)
FAKE_DISK_COPY = gcp.GoogleComputeDisk(
    FAKE_SOURCE_PROJECT,
    'fake-zone',
    'fake-disk-copy'
)

# Mock struct to mimic GCP's API responses
MOCK_INSTANCES_AGGREGATED = {
    # See https://cloud.google.com/compute/docs/reference/rest/v1/instances
    # /aggregatedList for complete structure
    'items': {
        0: {
            'instances': [
                {
                    'name': FAKE_INSTANCE.name,
                    'zone': '/' + FAKE_INSTANCE.zone
                }
            ]
        }
    }
}

MOCK_DISKS_AGGREGATED = {
    # See https://cloud.google.com/compute/docs/reference/rest/v1/disks
    # /aggregatedList for complete structure
    'items': {
        0: {
            'disks': [
                {
                    'name': FAKE_BOOT_DISK.name,
                    'zone': '/' + FAKE_BOOT_DISK.zone
                }
            ]
        },
        1: {
            'disks': [
                {
                    'name': FAKE_DISK.name,
                    'zone': '/' + FAKE_DISK.zone
                }
            ]
        }
    }
}

MOCK_LIST_INSTANCES = {
    FAKE_INSTANCE.name: {
        'zone': FAKE_INSTANCE.zone
    }
}

MOCK_LIST_DISKS = {
    FAKE_DISK.name: {
        'zone': FAKE_DISK.zone
    },
    FAKE_BOOT_DISK.name: {
        'zone': FAKE_BOOT_DISK.zone
    }
}

MOCK_GCE_OPERATION_INSTANCES_LABELS_SUCCESS = {
    'items': {
        '/zone': {
            'instances': [
                {
                    'name': FAKE_INSTANCE.name,
                    'zone': '/' + FAKE_INSTANCE.zone,
                    'labels': {
                        'id': '123'
                    }
                }
            ]
        }
    }
}

MOCK_GCE_OPERATION_DISKS_LABELS_SUCCESS = {
    'items': {
        '/zone': {
            'disks': [
                {
                    'name': FAKE_DISK.name,
                    'labels': {
                        'id': '123'
                    }
                },
                {
                    'name': FAKE_BOOT_DISK.name,
                    'labels': {
                        'some': 'thing'
                    }
                }
            ]
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
    'name': FAKE_INSTANCE.name,
    'disks': [
        {
            'boot': True,
            'source': '/' + FAKE_BOOT_DISK.name,
        },
        {
            'boot': False,
            'source': '/' + FAKE_DISK.name,
            'initializeParams': {
                'diskName': FAKE_DISK.name
            }
        }
    ]
}

# See: https://cloud.google.com/compute/docs/reference/rest/v1/disks
REGEX_DISK_NAME = re.compile('^(?=.{1,63}$)[a-z]([-a-z0-9]*[a-z0-9])?$')


class GoogleCloudProjectTest(unittest.TestCase):
  """Test Google Cloud project class."""

  def testFormatLogMessage(self):
    """Test formatting log message."""
    msg = 'Test message'
    formatted_msg = FAKE_ANALYSIS_PROJECT.FormatLogMessage(msg)
    self.assertIsInstance(formatted_msg, six.string_types)
    self.assertEqual(
        formatted_msg,
        'project:{0:s} {1:s}'.format(FAKE_ANALYSIS_PROJECT.project_id, msg)
    )

  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GceOperation')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GceApi')
  def testListInstances(self, mock_gce_api, mock_gce_operation):
    """Test that instances of project are correctly listed."""
    mock_gce_api.return_value.instances.return_value.aggregatedList \
      .return_value.execute.return_value = None
    mock_gce_operation.return_value = MOCK_INSTANCES_AGGREGATED
    instances = FAKE_ANALYSIS_PROJECT.ListInstances()
    self.assertEqual(len(instances), 1)
    self.assertTrue('fake-instance' in instances)
    self.assertEqual(instances['fake-instance']['zone'], 'fake-zone')

  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GceOperation')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GceApi')
  def testListDisks(self, mock_gce_api, mock_gce_operation):
    """Test that disks of instances are correctly listed."""
    mock_gce_api.return_value.disks.return_value.aggregatedList.return_value \
      .execute.return_value = None
    mock_gce_operation.return_value = MOCK_DISKS_AGGREGATED
    disks = FAKE_ANALYSIS_PROJECT.ListDisks()
    self.assertEqual(len(disks), 2)
    self.assertTrue('fake-disk' in disks and 'fake-boot-disk' in disks)
    self.assertEqual(disks['fake-disk']['zone'], 'fake-zone')
    self.assertEqual(disks['fake-boot-disk']['zone'], 'fake-zone')

  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.ListInstances')
  def testGetInstance(self, mock_list_instances):
    """Test that an instance of a project can be found."""
    mock_list_instances.return_value = MOCK_LIST_INSTANCES
    found_instance = FAKE_SOURCE_PROJECT.GetInstance(
        FAKE_INSTANCE.name, FAKE_INSTANCE.zone)
    self.assertIsInstance(found_instance, gcp.GoogleComputeInstance)
    self.assertEqual(found_instance.project, FAKE_SOURCE_PROJECT)
    self.assertEqual(found_instance.name, 'fake-instance')
    self.assertEqual(found_instance.zone, 'fake-zone')
    # pylint: disable=protected-access
    self.assertEqual(found_instance._data, FAKE_INSTANCE._data)
    self.assertRaises(
        RuntimeError, FAKE_SOURCE_PROJECT.GetInstance, 'non-existent-instance')

  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.ListDisks')
  def testGetDisk(self, mock_list_disks):
    """Test that a disk of an instance can be found."""
    mock_list_disks.return_value = MOCK_LIST_DISKS
    found_disk = FAKE_SOURCE_PROJECT.GetDisk(FAKE_DISK.name)
    self.assertIsInstance(found_disk, gcp.GoogleComputeDisk)
    self.assertEqual(found_disk.project, FAKE_SOURCE_PROJECT)
    self.assertEqual(found_disk.name, 'fake-disk')
    self.assertEqual(found_disk.zone, 'fake-zone')
    self.assertRaises(
        RuntimeError, FAKE_SOURCE_PROJECT.GetDisk, 'non-existent-disk')

  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GceOperation')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GceApi')
  def testCreateDiskFromSnapshot(self, mock_gce_api, mock_gce_operation):
    """Test the creation of a disk from a Snapshot."""
    mock_gce_api.return_value.disks.return_value.insert.return_value.execute \
      .return_value = None
    mock_gce_operation.return_value = None

    # CreateDiskFromSnapshot(Snapshot=FAKE_SNAPSHOT, disk_name=None,
    # disk_name_prefix='')
    disk_from_snapshot = FAKE_ANALYSIS_PROJECT.CreateDiskFromSnapshot(
        FAKE_SNAPSHOT)
    self.assertIsInstance(
        disk_from_snapshot, gcp.GoogleComputeDisk)
    self.assertEqual(
        disk_from_snapshot.name, gcp.GenerateDiskName(
            FAKE_SNAPSHOT))

    # CreateDiskFromSnapshot(Snapshot=FAKE_SNAPSHOT,
    # disk_name='new-forensics-disk', disk_name_prefix='')
    disk_from_snapshot = FAKE_ANALYSIS_PROJECT.CreateDiskFromSnapshot(
        FAKE_SNAPSHOT,
        disk_name='new-forensics-disk'
    )
    self.assertIsInstance(disk_from_snapshot, gcp.GoogleComputeDisk)
    self.assertEqual(
        disk_from_snapshot.name,
        'new-forensics-disk'
    )

    # CreateDiskFromSnapshot(Snapshot=FAKE_SNAPSHOT, disk_name=None,
    # disk_name_prefix='prefix')
    disk_from_snapshot = FAKE_ANALYSIS_PROJECT.CreateDiskFromSnapshot(
        FAKE_SNAPSHOT,
        disk_name_prefix='prefix'
    )
    self.assertIsInstance(disk_from_snapshot, gcp.GoogleComputeDisk)
    self.assertEqual(
        disk_from_snapshot.name,
        gcp.GenerateDiskName(
            FAKE_SNAPSHOT, disk_name_prefix='prefix')
    )

    # CreateDiskFromSnapshot(Snapshot=FAKE_SNAPSHOT,
    # disk_name='new-forensics-disk', disk_name_prefix='prefix')
    disk_from_snapshot = FAKE_ANALYSIS_PROJECT.CreateDiskFromSnapshot(
        FAKE_SNAPSHOT,
        disk_name='new-forensics-disk',
        disk_name_prefix='prefix'
    )
    self.assertIsInstance(disk_from_snapshot, gcp.GoogleComputeDisk)
    self.assertEqual(
        disk_from_snapshot.name,
        'new-forensics-disk'
    )

    # CreateDiskFromSnapshot(Snapshot=FAKE_SNAPSHOT,
    # disk_name='fake-disk') where 'fake-disk' exists already
    mock_gce_api.return_value.disks.return_value.insert.return_value.execute \
      .side_effect = HttpError(
          resp=mock.Mock(status=409),
          content=b'Disk already exists'
      )
    with self.assertRaises(RuntimeError) as context:
      _ = FAKE_ANALYSIS_PROJECT.CreateDiskFromSnapshot(
          FAKE_SNAPSHOT, disk_name=FAKE_DISK.name)
    self.assertEqual(str(context.exception), 'Disk {0:s} already exists'.format(
        'fake-disk'
    ))

    # other network issue should fail the disk creation
    mock_gce_api.return_value.disks.return_value.insert.return_value.execute \
      .side_effect = HttpError(
          resp=mock.Mock(status=418),
          content=b'I am a teapot'
      )
    with self.assertRaises(RuntimeError) as context:
      _ = FAKE_ANALYSIS_PROJECT.CreateDiskFromSnapshot(
          FAKE_SNAPSHOT, FAKE_DISK.name)
    self.assertTrue('status: 418' in str(context.exception))

  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GetInstance')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GceOperation')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GceApi')
  def testGetOrCreateAnalysisVm(self, mock_gce_api,
                                mock_gce_operation, mock_get_instance):
    """Test that a new virtual machine is created if it doesn't exist,
    or that the existing one is returned. """
    mock_gce_api.return_value.images.return_value.getFromFamily.return_value \
      .execute.return_value = None
    mock_gce_api.return_value.instances.return_value.insert.return_value \
      .execute.return_value = None
    mock_gce_operation.return_value = None
    mock_get_instance.return_value = FAKE_ANALYSIS_VM

    # GetOrCreateAnalysisVm(existing_vm, boot_disk_size)
    vm, created = FAKE_ANALYSIS_PROJECT.GetOrCreateAnalysisVm(
        FAKE_ANALYSIS_VM.name, boot_disk_size=1)
    self.assertIsInstance(vm, gcp.GoogleComputeInstance)
    self.assertEqual(vm.name, 'fake-analysis-vm')
    self.assertFalse(created)

    # GetOrCreateAnalysisVm(non_existing_vm, boot_disk_size) mocking the
    # GetInstance() call to throw a runtime error to mimic an instance that
    # wasn't found
    mock_get_instance.side_effect = RuntimeError()
    mock_gce_operation.return_value = {
        'selfLink': 'value'
    }
    vm, created = FAKE_ANALYSIS_PROJECT.GetOrCreateAnalysisVm(
        'non-existent-analysis-vm', boot_disk_size=1)
    self.assertIsInstance(vm, gcp.GoogleComputeInstance)
    self.assertEqual(vm.name, 'non-existent-analysis-vm')
    self.assertTrue(created)

  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GceOperation')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GceApi')
  def testListInstanceByLabels(self, mock_gce_api, mock_gce_operation):
    """Test that instances are correctly listed when searching with a filter."""
    mock_gce_api.return_value.instances.return_value.aggregatedList \
      .return_value.execute.return_value = None
    # To exit the loop
    mock_gce_api.return_value.instances.return_value.aggregatedList_next \
      .return_value = None
    # Labels found, GCE API will return instances
    mock_gce_operation.return_value = \
      MOCK_GCE_OPERATION_INSTANCES_LABELS_SUCCESS
    instances = FAKE_ANALYSIS_PROJECT.ListInstanceByLabels(
        labels_filter={'id': '123'})
    self.assertEqual(len(instances), 1)
    self.assertTrue(FAKE_INSTANCE.name in instances)

    # Labels not found, GCE API will return no items
    mock_gce_operation.return_value = MOCK_GCE_OPERATION_LABELS_FAILED
    instances = FAKE_ANALYSIS_PROJECT.ListInstanceByLabels(
        labels_filter={'id': '123'})
    self.assertEqual(len(instances), 0)

  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GceOperation')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GceApi')
  def testListDisksByLabels(self, mock_gce_api, mock_gce_operation):
    """Test that disks are correctly listed when searching with a filter."""
    mock_gce_api.return_value.disks.return_value.aggregatedList.return_value \
      .execute.return_value = None
    # To exit the loop
    mock_gce_api.return_value.disks.return_value.aggregatedList_next \
      .return_value = None
    # Labels found, GCE API will return disks
    mock_gce_operation.return_value = MOCK_GCE_OPERATION_DISKS_LABELS_SUCCESS
    disks = FAKE_ANALYSIS_PROJECT.ListDiskByLabels(
        labels_filter={'id': '123', 'some': 'thing'})
    self.assertEqual(len(disks), 2)
    self.assertTrue('fake-disk' in disks and 'fake-boot-disk' in disks)

    # Labels not found, GCE API will return no items
    mock_gce_operation.return_value = MOCK_GCE_OPERATION_LABELS_FAILED
    instances = FAKE_ANALYSIS_PROJECT.ListDiskByLabels(
        labels_filter={'id': '123'})
    self.assertEqual(len(instances), 0)


class GoogleComputeBaseResourceTest(unittest.TestCase):
  """Test Google Cloud Compute Base Resource class."""

  @mock.patch('libcloudforensics.gcp.GoogleComputeInstance.GetOperation')
  def testGetValue(self, mock_get_operation):
    """Test that the correct value is retrieved for the given key."""
    mock_get_operation.return_value.execute.return_value = {
        # See https://cloud.google.com/compute/docs/reference/rest/v1/instances
        # /get for complete structure
        'name': FAKE_INSTANCE.name
    }
    self.assertEqual(FAKE_INSTANCE.GetValue('name'), 'fake-instance')
    self.assertIsNone(FAKE_INSTANCE.GetValue('key'))


class GoogleComputeInstanceTest(unittest.TestCase):
  """Test Google Cloud Compute Instance class."""

  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.ListDisks')
  @mock.patch('libcloudforensics.gcp.GoogleComputeInstance.GetOperation')
  def testGetBootDisk(self, mock_get_operation, mock_list_disks):
    """Test that a boot disk is retrieved if existing."""
    mock_get_operation.return_value.execute.return_value = \
      MOCK_GCE_OPERATION_INSTANCES_GET
    mock_list_disks.return_value = MOCK_LIST_DISKS

    boot_disk = FAKE_INSTANCE.GetBootDisk()
    self.assertIsInstance(boot_disk, gcp.GoogleComputeDisk)
    self.assertEqual(boot_disk.name, 'fake-boot-disk')

  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.ListDisks')
  @mock.patch('libcloudforensics.gcp.GoogleComputeInstance.GetOperation')
  def testGetDisk(self, mock_get_operation, mock_list_disks):
    """Test that a disk is retrieved by its name, if existing."""
    mock_get_operation.return_value.execute.return_value = \
      MOCK_GCE_OPERATION_INSTANCES_GET
    mock_list_disks.return_value = MOCK_LIST_DISKS

    # Normal disk
    disk = FAKE_INSTANCE.GetDisk(FAKE_DISK.name)
    self.assertIsInstance(disk, gcp.GoogleComputeDisk)
    self.assertEqual(disk.name, 'fake-disk')

    # Boot disk
    disk = FAKE_INSTANCE.GetDisk(FAKE_BOOT_DISK.name)
    self.assertIsInstance(disk, gcp.GoogleComputeDisk)
    self.assertEqual(disk.name, 'fake-boot-disk')

    # Disk that's not attached to the instance
    self.assertRaises(RuntimeError, FAKE_INSTANCE.GetDisk, 'non-existent-disk')

  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.ListDisks')
  @mock.patch('libcloudforensics.gcp.GoogleComputeInstance.GetOperation')
  def testListDisks(self, mock_get_operation, mock_list_disks):
    """Test that a all disks of an instance are correctly retrieved."""
    mock_get_operation.return_value.execute.return_value = \
      MOCK_GCE_OPERATION_INSTANCES_GET
    mock_list_disks.return_value = MOCK_LIST_DISKS

    disks = FAKE_INSTANCE.ListDisks()
    self.assertEqual(len(disks), 2)
    self.assertEqual(disks, ['fake-boot-disk', 'fake-disk'])


class GoogleComputeDiskTest(unittest.TestCase):
  """Test Google Cloud Compute Disk class."""

  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GceApi')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GceOperation')
  def testSnapshot(self, mock_gce_operation, mock_gce_api):
    """Test that a Snapshot of the disk is created."""
    mock_gce_operation.return_value = None
    mock_gce_api.return_value.disks.return_value.createSnapshot.return_value \
      .execute.return_value = None

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

  @mock.patch('libcloudforensics.gcp.GoogleComputeInstance.GetBootDisk')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GetInstance')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GceOperation')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GceApi')
  def testCreateDiskCopy1(self, mock_gce_api, mock_gce_operation,
                          mock_get_instance, mock_get_boot_disk):
    """Test that a disk from a remote project is duplicated and attached to
    an analysis project. """
    mock_gce_api.return_value.instances.return_value.aggregatedList \
      .return_value.execute.return_value = None
    mock_gce_operation.return_value = MOCK_INSTANCES_AGGREGATED
    mock_get_instance.return_value = FAKE_INSTANCE
    mock_get_boot_disk.return_value = FAKE_BOOT_DISK

    # create_disk_copy(src_proj, dst_proj, instance_name='fake-instance',
    # zone='fake-zone', disk_name=None) Should grab the boot disk
    new_disk = gcp.CreateDiskCopy(FAKE_SOURCE_PROJECT.project_id,
                                  FAKE_ANALYSIS_PROJECT.project_id,
                                  instance_name=FAKE_INSTANCE.name,
                                  zone=FAKE_INSTANCE.zone,
                                  disk_name=None)
    self.assertIsInstance(new_disk, gcp.GoogleComputeDisk)
    self.assertTrue(new_disk.name.startswith('evidence-'))
    self.assertTrue('fake-boot-disk' in new_disk.name)
    self.assertTrue(new_disk.name.endswith('-copy'))

  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GetDisk')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GceOperation')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GceApi')
  def testCreateDiskCopy2(self, mock_gce_api, mock_gce_operation,
                          mock_get_disk):
    """Test that a disk from a remote project is duplicated and attached to
    an analysis project. """
    mock_gce_api.return_value.instances.return_value.aggregatedList \
      .return_value.execute.return_value = None
    mock_gce_operation.return_value = MOCK_INSTANCES_AGGREGATED
    mock_get_disk.return_value = FAKE_DISK

    # create_disk_copy(src_proj, dst_proj, instance_name=None,
    # zone='fake-zone', disk_name='fake-disk') Should grab 'fake-disk'
    new_disk = gcp.CreateDiskCopy(FAKE_SOURCE_PROJECT.project_id,
                                  FAKE_ANALYSIS_PROJECT.project_id,
                                  instance_name=None,
                                  zone=FAKE_INSTANCE.zone,
                                  disk_name=FAKE_DISK.name)
    self.assertIsInstance(new_disk, gcp.GoogleComputeDisk)
    self.assertTrue(new_disk.name.startswith('evidence-'))
    self.assertTrue('fake-disk' in new_disk.name)
    self.assertTrue(new_disk.name.endswith('-copy'))

  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GceOperation')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GceApi')
  def testCreateDiskCopy3(self, mock_gce_api, mock_gce_operation):
    """Test that a disk from a remote project is duplicated and attached to
    an analysis project. """
    mock_gce_api.return_value.instances.return_value.aggregatedList \
      .return_value.execute.return_value = None
    mock_gce_operation.return_value = MOCK_INSTANCES_AGGREGATED

    # create_disk_copy(src_proj, dst_proj, instance_name=None,
    # zone='fake-zone', disk_name='non-existent-disk') Should raise an
    # exception
    self.assertRaises(RuntimeError,
                      gcp.CreateDiskCopy,
                      FAKE_SOURCE_PROJECT.project_id,
                      FAKE_ANALYSIS_PROJECT.project_id,
                      instance_name=None,
                      zone=FAKE_INSTANCE.zone,
                      disk_name='non-existent-disk')

    # create_disk_copy(src_proj, dst_proj,
    # instance_name='non-existent-instance', zone='fake-zone',
    # disk_name=None) Should raise an exception
    self.assertRaises(RuntimeError,
                      gcp.CreateDiskCopy,
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

    disk_name = gcp.GenerateDiskName(
        FAKE_SNAPSHOT
    )
    self.assertEqual(disk_name, 'fake-snapshot-857c0b16-copy')
    self.assertTrue(REGEX_DISK_NAME.match(disk_name))

    disk_name = gcp.GenerateDiskName(
        FAKE_SNAPSHOT_LONG_NAME
    )
    self.assertEqual(
        disk_name,
        'this-is-a-kind-of-long-fake-snapshot-name-and-is--857c0b16-copy')
    self.assertTrue(REGEX_DISK_NAME.match(disk_name))

    disk_name = gcp.GenerateDiskName(
        FAKE_SNAPSHOT,
        disk_name_prefix='some-not-so-long-disk-name-prefix'
    )
    self.assertEqual(
        disk_name,
        'some-not-so-long-disk-name-prefix-fake-snapshot-857c0b16-copy')
    self.assertTrue(REGEX_DISK_NAME.match(disk_name))

    disk_name = gcp.GenerateDiskName(
        FAKE_SNAPSHOT_LONG_NAME,
        disk_name_prefix='some-not-so-long-disk-name-prefix'
    )
    self.assertEqual(
        disk_name,
        'some-not-so-long-disk-name-prefix-this-is-a-kind--857c0b16-copy')
    self.assertTrue(REGEX_DISK_NAME.match(disk_name))

    disk_name = gcp.GenerateDiskName(
        FAKE_SNAPSHOT,
        disk_name_prefix='some-really-really-really-really-really-really-long'
                         '-disk-name-prefix'
    )
    self.assertEqual(
        disk_name,
        'some-really-really-really-really-really-really-lo-857c0b16-copy')
    self.assertTrue(REGEX_DISK_NAME.match(disk_name))

    disk_name = gcp.GenerateDiskName(
        FAKE_SNAPSHOT_LONG_NAME,
        disk_name_prefix='some-really-really-really-really-really-really-long'
                         '-disk-name-prefix'
    )
    self.assertEqual(
        disk_name,
        'some-really-really-really-really-really-really-lo-857c0b16-copy')
    self.assertTrue(REGEX_DISK_NAME.match(disk_name))

    # Disk prefix cannot start with a capital letter
    self.assertRaises(ValueError, gcp.GenerateDiskName, FAKE_SNAPSHOT,
                      'Some-prefix-that-starts-with-a-capital-letter')


if __name__ == '__main__':
  unittest.main()
