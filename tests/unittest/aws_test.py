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
"""Tests for aws module."""

import unittest

import mock

from libcloudforensics import aws

FAKE_AWS_ACCOUNT = aws.AWSAccount(default_availability_zone='fake-zone-2b')
FAKE_INSTANCE = aws.AWSInstance(
    FAKE_AWS_ACCOUNT,
    'fake-instance-id',
    'fake-zone-2',
    'fake-zone-2b',
    name='fake-instance')
FAKE_INSTANCE_WITH_NAME = aws.AWSInstance(
    FAKE_AWS_ACCOUNT,
    'fake-instance-with-name-id',
    'fake-zone-2',
    'fake-zone-2b',
    name='fake-instance')
FAKE_VOLUME = aws.AWSVolume(
    'fake-volume-id',
    FAKE_AWS_ACCOUNT,
    'fake-zone-2',
    'fake-zone-2b')
FAKE_BOOT_VOLUME = aws.AWSVolume(
    'fake-boot-volume-id',
    FAKE_AWS_ACCOUNT,
    'fake-zone-2',
    'fake-zone-2b',
    name='fake-boot-volume')
FAKE_SNAPSHOT = aws.AWSSnapshot(
    'fake-snapshot-id',
    FAKE_VOLUME,
    name='fake-snapshot')

MOCK_DESCRIBE_INSTANCES = {
    'Reservations': [{
        'Instances': [{
            'InstanceId': FAKE_INSTANCE.instance_id,
            'Placement': {
                'AvailabilityZone': FAKE_INSTANCE.availability_zone
            },
            'State': {
                'Name': 'running'
            }
        }]
    }]
}

MOCK_DESCRIBE_INSTANCES_TAGS = {
    'Reservations': [{
        'Instances': [{
            'InstanceId': FAKE_INSTANCE.instance_id,
            'Placement': {
                'AvailabilityZone': FAKE_INSTANCE.availability_zone
            },
            'State': {
                'Name': 'running'
            },
            'Tags': [{
                'Key': 'Name',
                'Value': FAKE_INSTANCE.name
            }]
        }]
    }]
}

MOCK_DESCRIBE_VOLUMES = {
    'Volumes': [{
        'VolumeId': FAKE_VOLUME.volume_id,
        'AvailabilityZone': FAKE_VOLUME.availability_zone,
        'Attachments': []
    }, {
        'VolumeId': FAKE_BOOT_VOLUME.volume_id,
        'AvailabilityZone': FAKE_BOOT_VOLUME.availability_zone,
        'Attachments': []
    }]
}

MOCK_DESCRIBE_VOLUMES_TAGS = {
    'Volumes': [{
        'VolumeId': FAKE_BOOT_VOLUME.volume_id,
        'AvailabilityZone': FAKE_BOOT_VOLUME.availability_zone,
        'Attachments': [{
            'Device': '/dev/spf'
        }],
        'Tags': [{
            'Key': 'Name',
            'Value': FAKE_BOOT_VOLUME.name
        }]
    }]
}

MOCK_LIST_INSTANCES = {
    FAKE_INSTANCE.instance_id: {
        'region': FAKE_INSTANCE.region,
        'zone': FAKE_INSTANCE.availability_zone
    },
    FAKE_INSTANCE_WITH_NAME.instance_id: {
        'region': FAKE_INSTANCE_WITH_NAME.region,
        'zone': FAKE_INSTANCE_WITH_NAME.availability_zone,
        'name': FAKE_INSTANCE_WITH_NAME.name
    }
}

MOCK_LIST_VOLUMES = {
    FAKE_VOLUME.volume_id: {
        'region': FAKE_VOLUME.region,
        'zone': FAKE_VOLUME.availability_zone,
    },
    FAKE_BOOT_VOLUME.volume_id: {
        'region': FAKE_BOOT_VOLUME.region,
        'zone': FAKE_BOOT_VOLUME.availability_zone,
        'name': FAKE_BOOT_VOLUME.name,
        'device': '/dev/spf'
    }
}

MOCK_CREATE_VOLUME = {
    'VolumeId': 'fake-volume-from-snapshot-id',
    'AvailabilityZone': FAKE_SNAPSHOT.availability_zone
}

MOCK_CREATE_SNAPSHOT = {
    'SnapshotId': FAKE_SNAPSHOT.snapshot_id
}

MOCK_CALLER_IDENTITY = {
    'UserId': 'fake-user-id'
}


class AWSAccountTest(unittest.TestCase):
  """Test AWSAccount class."""

  @mock.patch('libcloudforensics.aws.AWSAccount.ClientApi')
  def testListInstances(self, mock_ec2_api):
    """Test that instances of an account are correctly listed."""
    describe_instances = mock_ec2_api.return_value.describe_instances
    describe_instances.return_value = MOCK_DESCRIBE_INSTANCES
    instances = FAKE_AWS_ACCOUNT.ListInstances()
    self.assertEqual(1, len(instances))
    self.assertIn('fake-instance-id', instances)
    self.assertEqual('fake-zone-2', instances['fake-instance-id']['region'])
    self.assertEqual('fake-zone-2b', instances['fake-instance-id']['zone'])

    describe_instances.return_value = MOCK_DESCRIBE_INSTANCES_TAGS
    instances = FAKE_AWS_ACCOUNT.ListInstances()
    self.assertIn('fake-instance-id', instances)
    self.assertEqual('fake-instance', instances['fake-instance-id']['name'])

  @mock.patch('libcloudforensics.aws.AWSAccount.ClientApi')
  def testListVolumes(self, mock_ec2_api):
    """Test that volumes of an account are correctly listed."""
    describe_volumes = mock_ec2_api.return_value.describe_volumes
    describe_volumes.return_value = MOCK_DESCRIBE_VOLUMES
    volumes = FAKE_AWS_ACCOUNT.ListVolumes()
    self.assertEqual(2, len(volumes))
    self.assertIn('fake-volume-id', volumes)
    self.assertIn('fake-boot-volume-id', volumes)
    self.assertEqual('fake-zone-2', volumes['fake-volume-id']['region'])
    self.assertEqual('fake-zone-2b', volumes['fake-volume-id']['zone'])

    describe_volumes.return_value = MOCK_DESCRIBE_VOLUMES_TAGS
    volumes = FAKE_AWS_ACCOUNT.ListVolumes()
    self.assertIn('fake-boot-volume-id', volumes)
    self.assertEqual('fake-boot-volume', volumes['fake-boot-volume-id']['name'])
    self.assertEqual('/dev/spf', volumes['fake-boot-volume-id']['device'])

  @mock.patch('libcloudforensics.aws.AWSAccount.ListInstances')
  def testGetInstanceById(self, mock_list_instances):
    """Test that an instance of an account can be found by its ID."""
    mock_list_instances.return_value = MOCK_LIST_INSTANCES
    found_instance = FAKE_AWS_ACCOUNT.GetInstanceById(
        FAKE_INSTANCE.instance_id)
    self.assertIsInstance(found_instance, aws.AWSInstance)
    self.assertEqual('fake-instance-id', found_instance.instance_id)
    self.assertEqual('fake-zone-2', found_instance.region)
    self.assertEqual('fake-zone-2b', found_instance.availability_zone)
    self.assertRaises(
        RuntimeError,
        FAKE_AWS_ACCOUNT.GetInstanceById,
        'non-existent-instance-id')

  @mock.patch('libcloudforensics.aws.AWSAccount.ListInstances')
  def testGetInstancesByName(self, mock_list_instances):
    """Test that an instance of an account can be found by its name."""
    mock_list_instances.return_value = MOCK_LIST_INSTANCES
    found_instances = FAKE_AWS_ACCOUNT.GetInstancesByName(
        FAKE_INSTANCE_WITH_NAME.name)
    self.assertEqual(1, len(found_instances))
    self.assertIsInstance(found_instances[0], aws.AWSInstance)
    self.assertEqual(
        'fake-instance-with-name-id', found_instances[0].instance_id)
    self.assertEqual('fake-zone-2', found_instances[0].region)
    self.assertEqual('fake-zone-2b', found_instances[0].availability_zone)

    found_instances = FAKE_AWS_ACCOUNT.GetInstancesByName(
        'non-existent-instance-name')
    self.assertEqual(0, len(found_instances))

  @mock.patch('libcloudforensics.aws.AWSAccount.ListInstances')
  def testGetInstancesByNameOrId(self, mock_list_instances):
    """Test that an instance of an account can be found by its name or ID."""
    mock_list_instances.return_value = MOCK_LIST_INSTANCES
    found_instances = FAKE_AWS_ACCOUNT.GetInstancesByNameOrId(
        instance_id=FAKE_INSTANCE.instance_id)
    self.assertEqual(1, len(found_instances))
    self.assertEqual('fake-instance-id', found_instances[0].instance_id)

    found_instances = FAKE_AWS_ACCOUNT.GetInstancesByNameOrId(
        instance_name=FAKE_INSTANCE_WITH_NAME.name)
    self.assertEqual(1, len(found_instances))
    self.assertEqual(
        'fake-instance-with-name-id', found_instances[0].instance_id)

    self.assertRaises(ValueError, FAKE_AWS_ACCOUNT.GetInstancesByNameOrId)
    self.assertRaises(
        ValueError,
        FAKE_AWS_ACCOUNT.GetInstancesByNameOrId,
        instance_id=FAKE_INSTANCE.instance_id,
        instance_name=FAKE_INSTANCE_WITH_NAME.name)

  @mock.patch('libcloudforensics.aws.AWSAccount.ListVolumes')
  def testGetVolumeById(self, mock_list_volumes):
    """Test that a volume of an account can be found by its ID."""
    mock_list_volumes.return_value = MOCK_LIST_VOLUMES
    found_volume = FAKE_AWS_ACCOUNT.GetVolumeById(
        FAKE_VOLUME.volume_id)
    self.assertIsInstance(found_volume, aws.AWSVolume)
    self.assertEqual('fake-volume-id', found_volume.volume_id)
    self.assertEqual('fake-zone-2', found_volume.region)
    self.assertEqual('fake-zone-2b', found_volume.availability_zone)

  @mock.patch('libcloudforensics.aws.AWSAccount.ListVolumes')
  def testGetVolumesByName(self, mock_list_volumes):
    """Test that a volume of an account can be found by its name."""
    mock_list_volumes.return_value = MOCK_LIST_VOLUMES
    found_volumes = FAKE_AWS_ACCOUNT.GetVolumesByName(
        FAKE_BOOT_VOLUME.name)
    self.assertEqual(1, len(found_volumes))
    self.assertEqual('fake-boot-volume-id', found_volumes[0].volume_id)
    self.assertEqual('fake-zone-2', found_volumes[0].region)
    self.assertEqual('fake-zone-2b', found_volumes[0].availability_zone)

    found_volumes = FAKE_AWS_ACCOUNT.GetVolumesByName(
        'non-existent-volume-name')
    self.assertEqual(0, len(found_volumes))

  @mock.patch('libcloudforensics.aws.AWSAccount.ListVolumes')
  def testGetVolumesByNameOrId(self, mock_list_volumes):
    """Test that a volume of an account can be found by its name or ID."""
    mock_list_volumes.return_value = MOCK_LIST_VOLUMES
    found_volumes = FAKE_AWS_ACCOUNT.GetVolumesByNameOrId(
        volume_id=FAKE_VOLUME.volume_id)
    self.assertEqual(1, len(found_volumes))
    self.assertEqual('fake-volume-id', found_volumes[0].volume_id)

    found_volumes = FAKE_AWS_ACCOUNT.GetVolumesByNameOrId(
        volume_name=FAKE_BOOT_VOLUME.name)
    self.assertEqual(1, len(found_volumes))
    self.assertEqual(
        'fake-boot-volume-id', found_volumes[0].volume_id)

    self.assertRaises(ValueError, FAKE_AWS_ACCOUNT.GetVolumesByNameOrId)
    self.assertRaises(
        ValueError,
        FAKE_AWS_ACCOUNT.GetVolumesByNameOrId,
        volume_id=FAKE_VOLUME.volume_id,
        volume_name=FAKE_BOOT_VOLUME.name)

  @mock.patch('libcloudforensics.aws.AWSAccount.ClientApi')
  def testCreateVolumeFromSnapshot(self, mock_ec2_api):
    """Test the creation of a volume from a snapshot."""
    caller_identity = mock_ec2_api.return_value.get_caller_identity
    mock_ec2_api.return_value.create_volume.return_value = MOCK_CREATE_VOLUME
    caller_identity.return_value = MOCK_CALLER_IDENTITY

    # CreateVolumeFromSnapshot(
    #     Snapshot=FAKE_SNAPSHOT, volume_name=None, volume_name_prefix='')
    volume_from_snapshot = FAKE_AWS_ACCOUNT.CreateVolumeFromSnapshot(
        FAKE_SNAPSHOT)
    self.assertIsInstance(volume_from_snapshot, aws.AWSVolume)
    self.assertEqual(
        'fake-volume-from-snapshot-id', volume_from_snapshot.volume_id)
    self.assertEqual('fake-snapshot-d69d57c3-copy', volume_from_snapshot.name)

    # CreateVolumeFromSnapshot(
    #     Snapshot=FAKE_SNAPSHOT,
    #     volume_name='new-forensics-volume',
    #     volume_name_prefix='')
    volume_from_snapshot = FAKE_AWS_ACCOUNT.CreateVolumeFromSnapshot(
        FAKE_SNAPSHOT, volume_name='new-forensics-volume')
    self.assertIsInstance(volume_from_snapshot, aws.AWSVolume)
    self.assertEqual(
        'fake-volume-from-snapshot-id', volume_from_snapshot.volume_id)
    self.assertEqual('new-forensics-volume', volume_from_snapshot.name)

    # CreateVolumeFromSnapshot(
    #     Snapshot=FAKE_SNAPSHOT, volume_name=None, volume_name_prefix='prefix')
    volume_from_snapshot = FAKE_AWS_ACCOUNT.CreateVolumeFromSnapshot(
        FAKE_SNAPSHOT, volume_name_prefix='prefix')
    self.assertIsInstance(volume_from_snapshot, aws.AWSVolume)
    self.assertEqual(
        'fake-volume-from-snapshot-id', volume_from_snapshot.volume_id)
    self.assertEqual(
        'prefix-fake-snapshot-d69d57c3-copy', volume_from_snapshot.name)

  @mock.patch('libcloudforensics.aws.AWSAccount.ClientApi')
  def testGenerateVolumeName(self, mock_ec2_api):
    """Test the generation of AWS volume name tag.

    The volume name tag must comply with the following RegEx: ^.{1,255}$
        i.e., it must be between 1 and 255 chars.
    """
    caller_identity = mock_ec2_api.return_value.get_caller_identity
    caller_identity.return_value = MOCK_CALLER_IDENTITY
    # pylint: disable=protected-access
    volume_name = FAKE_AWS_ACCOUNT._GenerateVolumeName(FAKE_SNAPSHOT)
    self.assertEqual('fake-snapshot-d69d57c3-copy', volume_name)

    volume_name = FAKE_AWS_ACCOUNT._GenerateVolumeName(
        FAKE_SNAPSHOT, volume_name_prefix='prefix')
    self.assertEqual('prefix-fake-snapshot-d69d57c3-copy', volume_name)
    # pylint: enable=protected-access


class AWSInstanceTest(unittest.TestCase):
  """Test AWSInstance class."""

  @mock.patch('libcloudforensics.aws.AWSAccount.ResourceApi')
  @mock.patch('libcloudforensics.aws.AWSAccount.ClientApi')
  def testGetBootVolume(self, mock_ec2_api, mock_resource_api):
    """Test that the boot volume is retrieved if existing."""
    describe_volumes = mock_ec2_api.return_value.describe_volumes
    instance = mock_resource_api.return_value.Instance
    describe_volumes.return_value = MOCK_DESCRIBE_VOLUMES_TAGS
    instance.return_value.root_device_name = '/dev/spf'

    boot_volume = FAKE_INSTANCE.GetBootVolume()
    self.assertIsInstance(boot_volume, aws.AWSVolume)
    self.assertEqual('fake-boot-volume-id', boot_volume.volume_id)


class AWSVolumeTest(unittest.TestCase):
  """Test AWSVolume class."""

  @mock.patch('libcloudforensics.aws.AWSAccount.ClientApi')
  def testSnapshot(self, mock_ec2_api):
    """Test that a snapshot of the volume is created."""
    snapshot = mock_ec2_api.return_value.create_snapshot
    snapshot.return_value = MOCK_CREATE_SNAPSHOT
    mock_ec2_api.return_value.get_waiter.return_value.wait.return_value = None

    # Snapshot(snapshot_name=None). Snapshot should start with the volume's name
    snapshot = FAKE_VOLUME.Snapshot()
    self.assertIsInstance(snapshot, aws.AWSSnapshot)
    # Part of the snapshot name is taken from a timestamp, therefore we only
    # assert for the beginning of the string.
    self.assertTrue(snapshot.name.startswith('fake-volume'))

    # Snapshot(snapshot_name='my-Snapshot'). Snapshot should start with
    # 'my-Snapshot'
    snapshot = FAKE_VOLUME.Snapshot(snapshot_name='my-snapshot')
    self.assertIsInstance(snapshot, aws.AWSSnapshot)
    # Same as above regarding the timestamp.
    self.assertTrue(snapshot.name.startswith('my-snapshot'))


if __name__ == '__main__':
  unittest.main()
