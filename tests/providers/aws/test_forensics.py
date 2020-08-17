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
"""Tests for aws module - forensics.py."""

import typing
import unittest
import mock

from libcloudforensics import errors
from libcloudforensics.providers.aws.internal import ebs

from libcloudforensics.providers.aws import forensics
from tests.providers.aws import aws_mocks


class AWSForensicsTest(unittest.TestCase):
  """Test the forensics.py public methods."""
  # pylint: disable=line-too-long

  @typing.no_type_check
  @mock.patch('boto3.session.Session._setup_loader')
  @mock.patch('libcloudforensics.providers.aws.internal.ebs.AWSVolume.GetVolumeType')
  @mock.patch('libcloudforensics.providers.aws.internal.ebs.AWSVolume.Snapshot')
  @mock.patch('libcloudforensics.providers.aws.internal.ebs.EBS.GetVolumeById')
  @mock.patch('libcloudforensics.providers.aws.internal.ebs.EBS.GetAccountInformation')
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ClientApi')
  def testCreateVolumeCopy1(self,
                            mock_ec2_api,
                            mock_account,
                            mock_get_volume,
                            mock_snapshot,
                            mock_volume_type,
                            mock_loader):
    """Test that a volume is correctly cloned."""
    aws_mocks.FAKE_SNAPSHOT.name = aws_mocks.FAKE_VOLUME.volume_id
    mock_ec2_api.return_value.create_volume.return_value = aws_mocks.MOCK_CREATE_VOLUME
    mock_account.return_value = aws_mocks.MOCK_CALLER_IDENTITY
    mock_get_volume.return_value = aws_mocks.FAKE_VOLUME
    mock_snapshot.return_value = aws_mocks.FAKE_SNAPSHOT
    mock_volume_type.return_value = 'standard'
    mock_loader.return_value = None

    # CreateVolumeCopy(zone, volume_id='fake-volume-id'). This should grab
    # the volume 'fake-volume-id'.
    new_volume = forensics.CreateVolumeCopy(
        aws_mocks.FAKE_INSTANCE.availability_zone, volume_id=aws_mocks.FAKE_VOLUME.volume_id)
    mock_get_volume.assert_called_with('fake-volume-id')
    self.assertIsInstance(new_volume, ebs.AWSVolume)
    self.assertTrue(new_volume.name.startswith('evidence-'))
    self.assertIn('fake-volume-id', new_volume.name)
    self.assertTrue(new_volume.name.endswith('-copy'))

  @typing.no_type_check
  @mock.patch('boto3.session.Session._setup_loader')
  @mock.patch('libcloudforensics.providers.aws.internal.ebs.AWSVolume.GetVolumeType')
  @mock.patch('libcloudforensics.providers.aws.internal.ebs.AWSVolume.Snapshot')
  @mock.patch('libcloudforensics.providers.aws.internal.ec2.AWSInstance.GetBootVolume')
  @mock.patch('libcloudforensics.providers.aws.internal.ec2.EC2.GetInstanceById')
  @mock.patch('libcloudforensics.providers.aws.internal.ebs.EBS.GetAccountInformation')
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ClientApi')
  def testCreateVolumeCopy2(self,
                            mock_ec2_api,
                            mock_account,
                            mock_get_instance,
                            mock_get_volume,
                            mock_snapshot,
                            mock_volume_type,
                            mock_loader):
    """Test that a volume is correctly cloned."""
    aws_mocks.FAKE_SNAPSHOT.name = aws_mocks.FAKE_BOOT_VOLUME.volume_id
    mock_ec2_api.return_value.create_volume.return_value = aws_mocks.MOCK_CREATE_VOLUME
    mock_account.return_value = aws_mocks.MOCK_CALLER_IDENTITY
    mock_get_instance.return_value = aws_mocks.FAKE_INSTANCE
    mock_get_volume.return_value = aws_mocks.FAKE_BOOT_VOLUME
    mock_snapshot.return_value = aws_mocks.FAKE_SNAPSHOT
    mock_volume_type.return_value = 'standard'
    mock_loader.return_value = None

    # CreateVolumeCopy(zone, instance='fake-instance-id'). This should grab
    # the boot volume of the instance.
    new_volume = forensics.CreateVolumeCopy(
        aws_mocks.FAKE_INSTANCE.availability_zone, instance_id=aws_mocks.FAKE_INSTANCE.instance_id)
    mock_get_instance.assert_called_with('fake-instance-id')
    self.assertIsInstance(new_volume, ebs.AWSVolume)
    self.assertTrue(new_volume.name.startswith('evidence-'))
    self.assertIn('fake-boot-volume-id', new_volume.name)
    self.assertTrue(new_volume.name.endswith('-copy'))

  @typing.no_type_check
  @mock.patch('boto3.session.Session._setup_loader')
  @mock.patch('libcloudforensics.providers.aws.internal.ebs.EBS.ListVolumes')
  @mock.patch('libcloudforensics.providers.aws.internal.ec2.EC2.ListInstances')
  def testCreateVolumeCopy3(self,
                            mock_list_instances,
                            mock_list_volumes,
                            mock_loader):
    """Test that a volume is correctly cloned."""
    mock_loader.return_value = None
    # Should raise a ValueError exception  as no volume_id or instance_id is
    # specified.
    with self.assertRaises(ValueError):
      forensics.CreateVolumeCopy(aws_mocks.FAKE_INSTANCE.availability_zone)

    # Should raise a ResourceCreationError as we are querying a non-existent
    # instance.
    mock_list_instances.return_value = {}
    with self.assertRaises(errors.ResourceCreationError):
      forensics.CreateVolumeCopy(
          aws_mocks.FAKE_INSTANCE.availability_zone,
          instance_id='non-existent-instance-id')

    # Should raise a ResourceCreationError as we are querying a non-existent
    # volume.
    mock_list_volumes.return_value = {}
    with self.assertRaises(errors.ResourceCreationError):
      forensics.CreateVolumeCopy(
          aws_mocks.FAKE_INSTANCE.availability_zone,
          volume_id='non-existent-volume-id')
