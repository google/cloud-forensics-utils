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
import typing
import unittest

import mock

from libcloudforensics.providers.aws.internal import account, common, ebs, ec2
from libcloudforensics.providers.aws.internal import log as aws_log
from libcloudforensics.providers.aws import forensics

FAKE_AWS_ACCOUNT = account.AWSAccount(
    default_availability_zone='fake-zone-2b')
FAKE_INSTANCE = ec2.AWSInstance(
    FAKE_AWS_ACCOUNT,
    'fake-instance-id',
    'fake-zone-2',
    'fake-zone-2b')
FAKE_INSTANCE_WITH_NAME = ec2.AWSInstance(
    FAKE_AWS_ACCOUNT,
    'fake-instance-with-name-id',
    'fake-zone-2',
    'fake-zone-2b',
    name='fake-instance')
FAKE_VOLUME = ebs.AWSVolume(
    'fake-volume-id',
    FAKE_AWS_ACCOUNT,
    'fake-zone-2',
    'fake-zone-2b',
    False)
FAKE_BOOT_VOLUME = ebs.AWSVolume(
    'fake-boot-volume-id',
    FAKE_AWS_ACCOUNT,
    'fake-zone-2',
    'fake-zone-2b',
    False,
    name='fake-boot-volume',
    device_name='/dev/spf')
FAKE_SNAPSHOT = ebs.AWSSnapshot(
    'fake-snapshot-id',
    FAKE_AWS_ACCOUNT,
    'fake-zone-2',
    'fake-zone-2b',
    FAKE_VOLUME,
    name='fake-snapshot')
FAKE_CLOUDTRAIL = aws_log.AWSCloudTrail(FAKE_AWS_ACCOUNT)
FAKE_EVENT_LIST = [
    {'EventId': '474e8265-9180-4407-a5c9-f3a86d8bb1f0',
     'EventName': 'CreateUser', 'ReadOnly': 'false'},
    {'EventId': '474e8395-9122-4407-a3b9-f3a77d8aa1f0',
     'EventName': 'AddUserToGroup', 'ReadOnly': 'false'},
]

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
            'InstanceId': FAKE_INSTANCE_WITH_NAME.instance_id,
            'Placement': {
                'AvailabilityZone': FAKE_INSTANCE_WITH_NAME.availability_zone
            },
            'State': {
                'Name': 'running'
            },
            'Tags': [{
                'Key': 'Name',
                'Value': FAKE_INSTANCE_WITH_NAME.name
            }]
        }]
    }]
}

MOCK_DESCRIBE_VOLUMES = {
    'Volumes': [{
        'VolumeId': FAKE_VOLUME.volume_id,
        'AvailabilityZone': FAKE_VOLUME.availability_zone,
        'Encrypted': FAKE_VOLUME.encrypted,
        'Attachments': []
    }, {
        'VolumeId': FAKE_BOOT_VOLUME.volume_id,
        'AvailabilityZone': FAKE_BOOT_VOLUME.availability_zone,
        'Encrypted': FAKE_BOOT_VOLUME.encrypted,
        'Attachments': []
    }]
}

MOCK_DESCRIBE_VOLUMES_TAGS = {
    'Volumes': [{
        'VolumeId': FAKE_BOOT_VOLUME.volume_id,
        'AvailabilityZone': FAKE_BOOT_VOLUME.availability_zone,
        'Encrypted': FAKE_BOOT_VOLUME.encrypted,
        'Attachments': [{
            'State': 'attached',
            'Device': FAKE_BOOT_VOLUME.device_name
        }],
        'Tags': [{
            'Key': 'Name',
            'Value': FAKE_BOOT_VOLUME.name
        }]
    }]
}

MOCK_LIST_INSTANCES = {
    FAKE_INSTANCE.instance_id: FAKE_INSTANCE,
    FAKE_INSTANCE_WITH_NAME.instance_id: FAKE_INSTANCE_WITH_NAME
}

MOCK_LIST_VOLUMES = {
    FAKE_VOLUME.volume_id: FAKE_VOLUME,
    FAKE_BOOT_VOLUME.volume_id: FAKE_BOOT_VOLUME
}

MOCK_CREATE_VOLUME = {
    'VolumeId': 'fake-volume-from-snapshot-id',
    'AvailabilityZone': FAKE_SNAPSHOT.availability_zone,
    'Encrypted': False
}

MOCK_CREATE_SNAPSHOT = {
    'SnapshotId': FAKE_SNAPSHOT.snapshot_id
}

MOCK_CALLER_IDENTITY = {
    'UserId': 'fake-user-id'
}

MOCK_DESCRIBE_AMI = {
    'Images': [{
        'BlockDeviceMappings': [{
            'Ebs': {
                'VolumeSize': None
            }
        }]
    }]
}

MOCK_RUN_INSTANCES = {
    'Instances': [{
        'InstanceId': 'new-instance-id'
    }]
}

MOCK_EVENT_LIST = {
    'Events': FAKE_EVENT_LIST
}


class AWSAccountTest(unittest.TestCase):
  """Test AWSAccount class."""
  # pylint: disable=line-too-long

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ClientApi')
  def testListInstances(self, mock_ec2_api):
    """Test that instances of an account are correctly listed."""
    describe_instances = mock_ec2_api.return_value.describe_instances
    describe_instances.return_value = MOCK_DESCRIBE_INSTANCES
    instances = FAKE_AWS_ACCOUNT.ListInstances()
    self.assertEqual(1, len(instances))
    self.assertIn('fake-instance-id', instances)
    self.assertEqual('fake-zone-2', instances['fake-instance-id'].region)
    self.assertEqual(
        'fake-zone-2b', instances['fake-instance-id'].availability_zone)

    describe_instances.return_value = MOCK_DESCRIBE_INSTANCES_TAGS
    instances = FAKE_AWS_ACCOUNT.ListInstances()
    self.assertIn('fake-instance-with-name-id', instances)
    self.assertEqual(
        'fake-instance', instances['fake-instance-with-name-id'].name)

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ClientApi')
  def testListVolumes(self, mock_ec2_api):
    """Test that volumes of an account are correctly listed."""
    describe_volumes = mock_ec2_api.return_value.describe_volumes
    describe_volumes.return_value = MOCK_DESCRIBE_VOLUMES
    volumes = FAKE_AWS_ACCOUNT.ListVolumes()
    self.assertEqual(2, len(volumes))
    self.assertIn('fake-volume-id', volumes)
    self.assertIn('fake-boot-volume-id', volumes)
    self.assertEqual('fake-zone-2', volumes['fake-volume-id'].region)
    self.assertEqual(
        'fake-zone-2b', volumes['fake-volume-id'].availability_zone)

    describe_volumes.return_value = MOCK_DESCRIBE_VOLUMES_TAGS
    volumes = FAKE_AWS_ACCOUNT.ListVolumes()
    self.assertIn('fake-boot-volume-id', volumes)
    self.assertEqual('fake-boot-volume', volumes['fake-boot-volume-id'].name)
    self.assertEqual('/dev/spf', volumes['fake-boot-volume-id'].device_name)

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ListInstances')
  def testGetInstanceById(self, mock_list_instances):
    """Test that an instance of an account can be found by its ID."""
    mock_list_instances.return_value = MOCK_LIST_INSTANCES
    found_instance = FAKE_AWS_ACCOUNT.GetInstanceById(
        FAKE_INSTANCE.instance_id)
    self.assertIsInstance(found_instance, ec2.AWSInstance)
    self.assertEqual('fake-instance-id', found_instance.instance_id)
    self.assertEqual('fake-zone-2', found_instance.region)
    self.assertEqual('fake-zone-2b', found_instance.availability_zone)
    self.assertRaises(
        RuntimeError,
        FAKE_AWS_ACCOUNT.GetInstanceById,
        'non-existent-instance-id')

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ListInstances')
  def testGetInstancesByName(self, mock_list_instances):
    """Test that an instance of an account can be found by its name."""
    mock_list_instances.return_value = MOCK_LIST_INSTANCES
    found_instances = FAKE_AWS_ACCOUNT.GetInstancesByName(
        FAKE_INSTANCE_WITH_NAME.name)
    self.assertEqual(1, len(found_instances))
    self.assertIsInstance(found_instances[0], ec2.AWSInstance)
    self.assertEqual(
        'fake-instance-with-name-id', found_instances[0].instance_id)
    self.assertEqual('fake-zone-2', found_instances[0].region)
    self.assertEqual('fake-zone-2b', found_instances[0].availability_zone)

    found_instances = FAKE_AWS_ACCOUNT.GetInstancesByName(
        'non-existent-instance-name')
    self.assertEqual(0, len(found_instances))

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ListInstances')
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

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ListVolumes')
  def testGetVolumeById(self, mock_list_volumes):
    """Test that a volume of an account can be found by its ID."""
    mock_list_volumes.return_value = MOCK_LIST_VOLUMES
    found_volume = FAKE_AWS_ACCOUNT.GetVolumeById(
        FAKE_VOLUME.volume_id)
    self.assertIsInstance(found_volume, ebs.AWSVolume)
    self.assertEqual('fake-volume-id', found_volume.volume_id)
    self.assertEqual('fake-zone-2', found_volume.region)
    self.assertEqual('fake-zone-2b', found_volume.availability_zone)

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ListVolumes')
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

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ListVolumes')
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

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ClientApi')
  def testCreateVolumeFromSnapshot(self, mock_ec2_api):
    """Test the creation of a volume from a snapshot."""
    caller_identity = mock_ec2_api.return_value.get_caller_identity
    mock_ec2_api.return_value.create_volume.return_value = MOCK_CREATE_VOLUME
    caller_identity.return_value = MOCK_CALLER_IDENTITY

    # CreateVolumeFromSnapshot(
    #     Snapshot=FAKE_SNAPSHOT, volume_name=None, volume_name_prefix='')
    volume_from_snapshot = FAKE_AWS_ACCOUNT.CreateVolumeFromSnapshot(
        FAKE_SNAPSHOT)
    self.assertIsInstance(volume_from_snapshot, ebs.AWSVolume)
    self.assertEqual(
        'fake-volume-from-snapshot-id', volume_from_snapshot.volume_id)
    self.assertEqual('fake-snapshot-d69d57c3-copy', volume_from_snapshot.name)

    # CreateVolumeFromSnapshot(
    #     Snapshot=FAKE_SNAPSHOT,
    #     volume_name='new-forensics-volume',
    #     volume_name_prefix='')
    volume_from_snapshot = FAKE_AWS_ACCOUNT.CreateVolumeFromSnapshot(
        FAKE_SNAPSHOT, volume_name='new-forensics-volume')
    self.assertIsInstance(volume_from_snapshot, ebs.AWSVolume)
    self.assertEqual(
        'fake-volume-from-snapshot-id', volume_from_snapshot.volume_id)
    self.assertEqual('new-forensics-volume', volume_from_snapshot.name)

    # CreateVolumeFromSnapshot(
    #     Snapshot=FAKE_SNAPSHOT, volume_name=None, volume_name_prefix='prefix')
    volume_from_snapshot = FAKE_AWS_ACCOUNT.CreateVolumeFromSnapshot(
        FAKE_SNAPSHOT, volume_name_prefix='prefix')
    self.assertIsInstance(volume_from_snapshot, ebs.AWSVolume)
    self.assertEqual(
        'fake-volume-from-snapshot-id', volume_from_snapshot.volume_id)
    self.assertEqual(
        'prefix-fake-snapshot-d69d57c3-copy', volume_from_snapshot.name)

  @typing.no_type_check
  @mock.patch('libcloudforensics.scripts.utils.ReadStartupScript')
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.GetInstancesByName')
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ClientApi')
  def testGetOrCreateAnalysisVm(self,
                                mock_ec2_api,
                                mock_get_instance,
                                mock_script):
    """Test that a VM is created or retrieved if it already exists."""
    mock_get_instance.return_value = [FAKE_INSTANCE_WITH_NAME]
    mock_script.return_value = ''
    # GetOrCreateAnalysisVm(vm_name, boot_volume_size, AMI, cpu_cores) where
    # vm_name is the name of an analysis instance that already exists.
    vm, created = FAKE_AWS_ACCOUNT.GetOrCreateAnalysisVm(
        FAKE_INSTANCE_WITH_NAME.name, 1, 'ami-id', 2)
    mock_get_instance.assert_called_with(FAKE_INSTANCE_WITH_NAME.name)
    mock_ec2_api.return_value.run_instances.assert_not_called()
    self.assertIsInstance(vm, ec2.AWSInstance)
    self.assertEqual('fake-instance', vm.name)
    self.assertFalse(created)

    # GetOrCreateAnalysisVm(non_existing_vm, boot_volume_size, AMI, cpu_cores).
    # We mock the GetInstanceById() call to throw a RuntimeError to mimic
    # an instance that wasn't found. This should trigger run_instances to be
    # called.
    mock_get_instance.side_effect = RuntimeError()
    vm, created = FAKE_AWS_ACCOUNT.GetOrCreateAnalysisVm(
        'non-existent-instance-name', 1, 'ami-id', 2)
    mock_get_instance.assert_called_with('non-existent-instance-name')
    mock_ec2_api.return_value.run_instances.assert_called()
    self.assertIsInstance(vm, ec2.AWSInstance)
    self.assertEqual('non-existent-instance-name', vm.name)
    self.assertTrue(created)

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ClientApi')
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
    # pylint: enable=protected-access
    self.assertEqual('prefix-fake-snapshot-d69d57c3-copy', volume_name)

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ClientApi')
  def testGetBootVolumeConfigByAmi(self, mock_ec2_api):
    """Test that the boot volume configuration is correctly created."""
    mock_ec2_api.return_value.describe_images.return_value = MOCK_DESCRIBE_AMI
    self.assertIsNone(
        MOCK_DESCRIBE_AMI['Images'][0]['BlockDeviceMappings'][0]['Ebs']['VolumeSize'])  # pylint: disable=line-too-long
    # pylint: disable=protected-access
    config = FAKE_AWS_ACCOUNT._GetBootVolumeConfigByAmi('ami-id', 50)
    # pylint: enable=protected-access
    self.assertEqual(50, config['Ebs']['VolumeSize'])

  @typing.no_type_check
  def testGetInstanceTypeByCPU(self):
    """Test that the instance type matches the requested amount of CPU cores."""
    # pylint: disable=protected-access
    self.assertEqual('m4.large', common.GetInstanceTypeByCPU(2))
    self.assertEqual('m4.16xlarge', common.GetInstanceTypeByCPU(64))
    self.assertRaises(ValueError, common.GetInstanceTypeByCPU, 0)
    self.assertRaises(ValueError, common.GetInstanceTypeByCPU, 256)
    # pylint: enable=protected-access


class AWSInstanceTest(unittest.TestCase):
  """Test AWSInstance class."""
  # pylint: disable=line-too-long

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ResourceApi')
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ClientApi')
  def testGetBootVolume(self, mock_ec2_api, mock_resource_api):
    """Test that the boot volume is retrieved if existing."""
    describe_volumes = mock_ec2_api.return_value.describe_volumes
    instance = mock_resource_api.return_value.Instance
    describe_volumes.return_value = MOCK_DESCRIBE_VOLUMES_TAGS
    instance.return_value.root_device_name = '/dev/spf'

    boot_volume = FAKE_INSTANCE.GetBootVolume()
    self.assertIsInstance(boot_volume, ebs.AWSVolume)
    self.assertEqual('fake-boot-volume-id', boot_volume.volume_id)


class AWSVolumeTest(unittest.TestCase):
  """Test AWSVolume class."""
  # pylint: disable=line-too-long

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ClientApi')
  def testSnapshot(self, mock_ec2_api):
    """Test that a snapshot of the volume is created."""
    snapshot = mock_ec2_api.return_value.create_snapshot
    snapshot.return_value = MOCK_CREATE_SNAPSHOT
    mock_ec2_api.return_value.get_waiter.return_value.wait.return_value = None

    # Snapshot(snapshot_name=None). Snapshot should start with the volume's name
    snapshot = FAKE_VOLUME.Snapshot()
    self.assertIsInstance(snapshot, ebs.AWSSnapshot)
    # Part of the snapshot name is taken from a timestamp, therefore we only
    # assert for the beginning of the string.
    self.assertTrue(snapshot.name.startswith('fake-volume'))

    # Snapshot(snapshot_name='my-Snapshot'). Snapshot should start with
    # 'my-Snapshot'
    snapshot = FAKE_VOLUME.Snapshot(snapshot_name='my-snapshot')
    self.assertIsInstance(snapshot, ebs.AWSSnapshot)
    # Same as above regarding the timestamp.
    self.assertTrue(snapshot.name.startswith('my-snapshot'))


class AWSSnapshotTest(unittest.TestCase):
  """Test AWSSnapshot class."""

  # pylint: disable=line-too-long
  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ClientApi')
  def testCopy(self, mock_ec2_api):
    """Test that a copy of the snapshot is created."""
    snapshot_copy = mock_ec2_api.return_value.copy_snapshot
    snapshot_copy.return_value = MOCK_CREATE_SNAPSHOT
    mock_ec2_api.return_value.get_waiter.return_value.wait.return_value = None

    copy = FAKE_SNAPSHOT.Copy()
    self.assertIsInstance(copy, ebs.AWSSnapshot)
    self.assertEqual('fake-snapshot-id-copy', copy.name)
    mock_ec2_api.return_value.delete_snapshot.assert_not_called()

    copy = FAKE_SNAPSHOT.Copy(delete=True)
    mock_ec2_api.return_value.delete_snapshot.assert_called()


class AWSCloudTrailTest(unittest.TestCase):
  """Test AWS CloudTrail class."""
  # pylint: disable=line-too-long

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ClientApi')
  def testLookupEvents(self, mock_ec2_api):
    """Test that the CloudTrail event are looked up."""
    events = mock_ec2_api.return_value.lookup_events
    events.return_value = MOCK_EVENT_LIST
    lookup_events = FAKE_CLOUDTRAIL.LookupEvents()

    self.assertEqual(2, len(lookup_events))
    self.assertEqual(FAKE_EVENT_LIST[0], lookup_events[0])


class AWSTest(unittest.TestCase):
  """Test the account.py public methods."""
  # pylint: disable=line-too-long

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.ebs.AWSVolume.Snapshot')
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.GetVolumeById')
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.GetAccountInformation')
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ClientApi')
  def testCreateVolumeCopy1(self,
                            mock_ec2_api,
                            mock_account,
                            mock_get_volume,
                            mock_snapshot):
    """Test that a volume is correctly cloned."""
    FAKE_SNAPSHOT.name = FAKE_VOLUME.volume_id
    mock_ec2_api.return_value.create_volume.return_value = MOCK_CREATE_VOLUME
    mock_account.return_value = 'fake-account-id'
    mock_get_volume.return_value = FAKE_VOLUME
    mock_snapshot.return_value = FAKE_SNAPSHOT

    # CreateVolumeCopy(zone, volume_id='fake-volume-id'). This should grab
    # the volume 'fake-volume-id'.
    new_volume = forensics.CreateVolumeCopy(
        FAKE_INSTANCE.availability_zone, volume_id=FAKE_VOLUME.volume_id)
    mock_get_volume.assert_called_with('fake-volume-id')
    self.assertIsInstance(new_volume, ebs.AWSVolume)
    self.assertTrue(new_volume.name.startswith('evidence-'))
    self.assertIn('fake-volume-id', new_volume.name)
    self.assertTrue(new_volume.name.endswith('-copy'))

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.ebs.AWSVolume.Snapshot')
  @mock.patch('libcloudforensics.providers.aws.internal.ec2.AWSInstance.GetBootVolume')
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.GetInstanceById')
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.GetAccountInformation')
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ClientApi')
  def testCreateVolumeCopy2(self,
                            mock_ec2_api,
                            mock_account,
                            mock_get_instance,
                            mock_get_volume,
                            mock_snapshot):
    """Test that a volume is correctly cloned."""
    FAKE_SNAPSHOT.name = FAKE_BOOT_VOLUME.volume_id
    mock_ec2_api.return_value.create_volume.return_value = MOCK_CREATE_VOLUME
    mock_account.return_value = 'fake-account-id'
    mock_get_instance.return_value = FAKE_INSTANCE
    mock_get_volume.return_value = FAKE_BOOT_VOLUME
    mock_snapshot.return_value = FAKE_SNAPSHOT

    # CreateVolumeCopy(zone, instance='fake-instance-id'). This should grab
    # the boot volume of the instance.
    new_volume = forensics.CreateVolumeCopy(
        FAKE_INSTANCE.availability_zone, instance_id=FAKE_INSTANCE.instance_id)
    mock_get_instance.assert_called_with('fake-instance-id')
    self.assertIsInstance(new_volume, ebs.AWSVolume)
    self.assertTrue(new_volume.name.startswith('evidence-'))
    self.assertIn('fake-boot-volume-id', new_volume.name)
    self.assertTrue(new_volume.name.endswith('-copy'))

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ListVolumes')
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ListInstances')
  def testCreateVolumeCopy3(self, mock_list_instances, mock_list_volumes):
    """Test that a volume is correctly cloned."""
    # Should raise a ValueError exception  as no volume_id or instance_id is
    # specified.
    self.assertRaises(
        ValueError, forensics.CreateVolumeCopy, FAKE_INSTANCE.availability_zone)

    # Should raise a RuntimeError in GetInstanceById as we are querying a
    # non-existent instance.
    mock_list_instances.return_value = {}
    self.assertRaises(RuntimeError,
                      forensics.CreateVolumeCopy,
                      FAKE_INSTANCE.availability_zone,
                      instance_id='non-existent-instance-id')

    # Should raise a RuntimeError in GetVolumeById as we are querying a
    # non-existent volume.
    mock_list_volumes.return_value = {}
    self.assertRaises(RuntimeError,
                      forensics.CreateVolumeCopy,
                      FAKE_INSTANCE.availability_zone,
                      volume_id='non-existent-volume-id')


if __name__ == '__main__':
  unittest.main()
