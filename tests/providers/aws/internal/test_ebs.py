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
"""Tests for aws module - ebs.py."""

import typing
import unittest
import mock

from libcloudforensics.providers.aws.internal import ebs
from tests.providers.aws import aws_mocks


class AWSVolumeTest(unittest.TestCase):
  """Test AWSVolume class."""
  # pylint: disable=line-too-long

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ClientApi')
  def testSnapshot(self, mock_ec2_api):
    """Test that a snapshot of the volume is created."""
    snapshot = mock_ec2_api.return_value.create_snapshot
    snapshot.return_value = aws_mocks.MOCK_CREATE_SNAPSHOT
    mock_ec2_api.return_value.get_waiter.return_value.wait.return_value = None

    # Snapshot(tags=None). Snapshot name should be the volume's id.
    snapshot = aws_mocks.FAKE_VOLUME.Snapshot()
    self.assertIsInstance(snapshot, ebs.AWSSnapshot)
    self.assertEqual('fake-volume-id-snapshot', snapshot.name)

    # Snapshot(tags={'Name': 'my-snapshot'}). Snapshot should be 'my-snapshot'.
    snapshot = aws_mocks.FAKE_VOLUME.Snapshot(tags={'Name': 'my-snapshot'})
    self.assertIsInstance(snapshot, ebs.AWSSnapshot)
    self.assertEqual('my-snapshot', snapshot.name)


class AWSSnapshotTest(unittest.TestCase):
  """Test AWSSnapshot class."""
  # pylint: disable=line-too-long

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ClientApi')
  def testCopy(self, mock_ec2_api):
    """Test that a copy of the snapshot is created."""
    snapshot_copy = mock_ec2_api.return_value.copy_snapshot
    snapshot_copy.return_value = aws_mocks.MOCK_CREATE_SNAPSHOT
    mock_ec2_api.return_value.get_waiter.return_value.wait.return_value = None

    copy = aws_mocks.FAKE_SNAPSHOT.Copy()
    self.assertIsInstance(copy, ebs.AWSSnapshot)
    self.assertEqual('fake-snapshot-id-copy', copy.name)
    mock_ec2_api.return_value.delete_snapshot.assert_not_called()

    _ = aws_mocks.FAKE_SNAPSHOT.Copy(delete=True)
    mock_ec2_api.return_value.delete_snapshot.assert_called()


class EBSTest(unittest.TestCase):
  """Test EBS class."""
  # pylint: disable=line-too-long

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ClientApi')
  def testListVolumes(self, mock_ec2_api):
    """Test that volumes of an account are correctly listed."""
    describe_volumes = mock_ec2_api.return_value.describe_volumes
    describe_volumes.return_value = aws_mocks.MOCK_DESCRIBE_VOLUMES
    volumes = aws_mocks.FAKE_AWS_ACCOUNT.ebs.ListVolumes()
    self.assertEqual(2, len(volumes))
    self.assertIn('fake-volume-id', volumes)
    self.assertIn('fake-boot-volume-id', volumes)
    self.assertEqual('fake-zone-2', volumes['fake-volume-id'].region)
    self.assertEqual(
        'fake-zone-2b', volumes['fake-volume-id'].availability_zone)

    describe_volumes.return_value = aws_mocks.MOCK_DESCRIBE_VOLUMES_TAGS
    volumes = aws_mocks.FAKE_AWS_ACCOUNT.ebs.ListVolumes()
    self.assertIn('fake-boot-volume-id', volumes)
    self.assertEqual('fake-boot-volume', volumes['fake-boot-volume-id'].name)
    self.assertEqual('/dev/spf', volumes['fake-boot-volume-id'].device_name)

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.ebs.EBS.ListVolumes')
  def testGetVolumeById(self, mock_list_volumes):
    """Test that a volume of an account can be found by its ID."""
    mock_list_volumes.return_value = aws_mocks.MOCK_LIST_VOLUMES
    found_volume = aws_mocks.FAKE_AWS_ACCOUNT.ebs.GetVolumeById(
        aws_mocks.FAKE_VOLUME.volume_id)
    self.assertIsInstance(found_volume, ebs.AWSVolume)
    self.assertEqual('fake-volume-id', found_volume.volume_id)
    self.assertEqual('fake-zone-2', found_volume.region)
    self.assertEqual('fake-zone-2b', found_volume.availability_zone)

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.ebs.EBS.ListVolumes')
  def testGetVolumesByName(self, mock_list_volumes):
    """Test that a volume of an account can be found by its name."""
    mock_list_volumes.return_value = aws_mocks.MOCK_LIST_VOLUMES
    found_volumes = aws_mocks.FAKE_AWS_ACCOUNT.ebs.GetVolumesByName(
        aws_mocks.FAKE_BOOT_VOLUME.name)
    self.assertEqual(1, len(found_volumes))
    self.assertEqual('fake-boot-volume-id', found_volumes[0].volume_id)
    self.assertEqual('fake-zone-2', found_volumes[0].region)
    self.assertEqual('fake-zone-2b', found_volumes[0].availability_zone)

    found_volumes = aws_mocks.FAKE_AWS_ACCOUNT.ebs.GetVolumesByName(
        'non-existent-volume-name')
    self.assertEqual(0, len(found_volumes))

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.ebs.EBS.ListVolumes')
  def testGetVolumesByNameOrId(self, mock_list_volumes):
    """Test that a volume of an account can be found by its name or ID."""
    mock_list_volumes.return_value = aws_mocks.MOCK_LIST_VOLUMES
    found_volumes = aws_mocks.FAKE_AWS_ACCOUNT.ebs.GetVolumesByNameOrId(
        volume_id=aws_mocks.FAKE_VOLUME.volume_id)
    self.assertEqual(1, len(found_volumes))
    self.assertEqual('fake-volume-id', found_volumes[0].volume_id)

    found_volumes = aws_mocks.FAKE_AWS_ACCOUNT.ebs.GetVolumesByNameOrId(
        volume_name=aws_mocks.FAKE_BOOT_VOLUME.name)
    self.assertEqual(1, len(found_volumes))
    self.assertEqual(
        'fake-boot-volume-id', found_volumes[0].volume_id)

    with self.assertRaises(ValueError):
      aws_mocks.FAKE_AWS_ACCOUNT.ebs.GetVolumesByNameOrId()

    with self.assertRaises(ValueError):
      aws_mocks.FAKE_AWS_ACCOUNT.ebs.GetVolumesByNameOrId(
          volume_id=aws_mocks.FAKE_VOLUME.volume_id,
          volume_name=aws_mocks.FAKE_BOOT_VOLUME.name)

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ClientApi')
  def testCreateVolumeFromSnapshot(self, mock_ec2_api):
    """Test the creation of a volume from a snapshot."""
    caller_identity = mock_ec2_api.return_value.get_caller_identity
    mock_ec2_api.return_value.create_volume.return_value = aws_mocks.MOCK_CREATE_VOLUME
    caller_identity.return_value = aws_mocks.MOCK_CALLER_IDENTITY

    # CreateVolumeFromSnapshot(
    #     Snapshot=aws_mocks.FAKE_SNAPSHOT, volume_name=None,
    #     volume_name_prefix='')
    volume_from_snapshot = aws_mocks.FAKE_AWS_ACCOUNT.ebs.CreateVolumeFromSnapshot(
        aws_mocks.FAKE_SNAPSHOT)
    self.assertIsInstance(volume_from_snapshot, ebs.AWSVolume)
    self.assertEqual(
        'fake-volume-from-snapshot-id', volume_from_snapshot.volume_id)
    self.assertEqual('fake-snapshot-d69d57c3-copy', volume_from_snapshot.name)

    # CreateVolumeFromSnapshot(
    #     Snapshot=aws_mocks.FAKE_SNAPSHOT,
    #     volume_name='new-forensics-volume',
    #     volume_name_prefix='')
    volume_from_snapshot = aws_mocks.FAKE_AWS_ACCOUNT.ebs.CreateVolumeFromSnapshot(
        aws_mocks.FAKE_SNAPSHOT, volume_name='new-forensics-volume')
    self.assertIsInstance(volume_from_snapshot, ebs.AWSVolume)
    self.assertEqual(
        'fake-volume-from-snapshot-id', volume_from_snapshot.volume_id)
    self.assertEqual('new-forensics-volume', volume_from_snapshot.name)

    # CreateVolumeFromSnapshot(
    #     Snapshot=aws_mocks.FAKE_SNAPSHOT, volume_name=None,
    #     volume_name_prefix='prefix')
    volume_from_snapshot = aws_mocks.FAKE_AWS_ACCOUNT.ebs.CreateVolumeFromSnapshot(
        aws_mocks.FAKE_SNAPSHOT, volume_name_prefix='prefix')
    self.assertIsInstance(volume_from_snapshot, ebs.AWSVolume)
    self.assertEqual(
        'fake-volume-from-snapshot-id', volume_from_snapshot.volume_id)
    self.assertEqual(
        'prefix-fake-snapshot-d69d57c3-copy', volume_from_snapshot.name)

    with self.assertRaises(ValueError) as error:
      aws_mocks.FAKE_AWS_ACCOUNT.ebs.CreateVolumeFromSnapshot(
          aws_mocks.FAKE_SNAPSHOT, volume_type='invalid-volume-type')
    self.assertEqual('Volume type must be one of [standard, io1, gp2, sc1, '
                     'st1]. Got: invalid-volume-type', str(error.exception))

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ClientApi')
  def testGenerateVolumeName(self, mock_ec2_api):
    """Test the generation of AWS volume name tag.

    The volume name tag must comply with the following RegEx: ^.{1,255}$
        i.e., it must be between 1 and 255 chars.
    """
    caller_identity = mock_ec2_api.return_value.get_caller_identity
    caller_identity.return_value = aws_mocks.MOCK_CALLER_IDENTITY
    # pylint: disable=protected-access
    volume_name = aws_mocks.FAKE_AWS_ACCOUNT.ebs._GenerateVolumeName(
        aws_mocks.FAKE_SNAPSHOT)
    self.assertEqual('fake-snapshot-d69d57c3-copy', volume_name)

    volume_name = aws_mocks.FAKE_AWS_ACCOUNT.ebs._GenerateVolumeName(
        aws_mocks.FAKE_SNAPSHOT, volume_name_prefix='prefix')
    # pylint: enable=protected-access
    self.assertEqual('prefix-fake-snapshot-d69d57c3-copy', volume_name)
