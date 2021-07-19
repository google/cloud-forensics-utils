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
"""Tests for aws module - ec2.py."""

import typing
import unittest
import mock

from libcloudforensics import errors
from libcloudforensics.providers.aws.internal import ebs
from libcloudforensics.providers.aws.internal import ec2
from tests.providers.aws import aws_mocks


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
    describe_volumes.return_value = aws_mocks.MOCK_DESCRIBE_VOLUMES_TAGS
    instance.return_value.root_device_name = '/dev/spf'

    boot_volume = aws_mocks.FAKE_INSTANCE.GetBootVolume()
    self.assertIsInstance(boot_volume, ebs.AWSVolume)
    self.assertEqual('fake-boot-volume-id', boot_volume.volume_id)


class EC2Test(unittest.TestCase):
  """Test the EC2 class."""
  # pylint: disable=line-too-long

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ClientApi')
  def testListInstances(self, mock_ec2_api):
    """Test that instances of an account are correctly listed."""
    describe_instances = mock_ec2_api.return_value.describe_instances
    describe_instances.return_value = aws_mocks.MOCK_DESCRIBE_INSTANCES
    instances = aws_mocks.FAKE_AWS_ACCOUNT.ec2.ListInstances()
    self.assertEqual(1, len(instances))
    self.assertIn('fake-instance-id', instances)
    self.assertEqual('fake-zone-2', instances['fake-instance-id'].region)
    self.assertEqual(
        'fake-zone-2b', instances['fake-instance-id'].availability_zone)

    describe_instances.return_value = aws_mocks.MOCK_DESCRIBE_INSTANCES_TAGS
    instances = aws_mocks.FAKE_AWS_ACCOUNT.ec2.ListInstances()
    self.assertIn('fake-instance-with-name-id', instances)
    self.assertEqual(
        'fake-instance', instances['fake-instance-with-name-id'].name)

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.ec2.EC2.ListInstances')
  def testGetInstanceById(self, mock_list_instances):
    """Test that an instance of an account can be found by its ID."""
    mock_list_instances.return_value = aws_mocks.MOCK_LIST_INSTANCES
    found_instance = aws_mocks.FAKE_AWS_ACCOUNT.ec2.GetInstanceById(
        aws_mocks.FAKE_INSTANCE.instance_id)
    self.assertIsInstance(found_instance, ec2.AWSInstance)
    self.assertEqual('fake-instance-id', found_instance.instance_id)
    self.assertEqual('fake-zone-2', found_instance.region)
    self.assertEqual('fake-zone-2b', found_instance.availability_zone)
    with self.assertRaises(errors.ResourceNotFoundError):
      aws_mocks.FAKE_AWS_ACCOUNT.ec2.GetInstanceById('non-existent-instance-id')

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.ec2.EC2.ListInstances')
  def testGetInstancesByName(self, mock_list_instances):
    """Test that an instance of an account can be found by its name."""
    mock_list_instances.return_value = aws_mocks.MOCK_LIST_INSTANCES
    found_instances = aws_mocks.FAKE_AWS_ACCOUNT.ec2.GetInstancesByName(
        aws_mocks.FAKE_INSTANCE_WITH_NAME.name)
    self.assertEqual(1, len(found_instances))
    self.assertIsInstance(found_instances[0], ec2.AWSInstance)
    self.assertEqual(
        'fake-instance-with-name-id', found_instances[0].instance_id)
    self.assertEqual('fake-zone-2', found_instances[0].region)
    self.assertEqual('fake-zone-2b', found_instances[0].availability_zone)

    found_instances = aws_mocks.FAKE_AWS_ACCOUNT.ec2.GetInstancesByName(
        'non-existent-instance-name')
    self.assertEqual(0, len(found_instances))

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.ec2.EC2.ListInstances')
  def testGetInstancesByNameOrId(self, mock_list_instances):
    """Test that an instance of an account can be found by its name or ID."""
    mock_list_instances.return_value = aws_mocks.MOCK_LIST_INSTANCES
    found_instances = aws_mocks.FAKE_AWS_ACCOUNT.ec2.GetInstancesByNameOrId(
        instance_id=aws_mocks.FAKE_INSTANCE.instance_id)
    self.assertEqual(1, len(found_instances))
    self.assertEqual('fake-instance-id', found_instances[0].instance_id)

    found_instances = aws_mocks.FAKE_AWS_ACCOUNT.ec2.GetInstancesByNameOrId(
        instance_name=aws_mocks.FAKE_INSTANCE_WITH_NAME.name)
    self.assertEqual(1, len(found_instances))
    self.assertEqual(
        'fake-instance-with-name-id', found_instances[0].instance_id)

    with self.assertRaises(ValueError):
      aws_mocks.FAKE_AWS_ACCOUNT.ec2.GetInstancesByNameOrId()

    with self.assertRaises(ValueError):
      aws_mocks.FAKE_AWS_ACCOUNT.ec2.GetInstancesByNameOrId(
          instance_id=aws_mocks.FAKE_INSTANCE.instance_id,
          instance_name=aws_mocks.FAKE_INSTANCE_WITH_NAME.name)

  @typing.no_type_check
  @mock.patch('libcloudforensics.scripts.utils.ReadStartupScript')
  @mock.patch('libcloudforensics.providers.aws.internal.ec2.EC2.GetInstancesByName')
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ClientApi')
  def testGetOrCreateVm(self,
                                mock_ec2_api,
                                mock_get_instance,
                                mock_script):
    """Test that a VM is created or retrieved if it already exists."""
    mock_get_instance.return_value = [aws_mocks.FAKE_INSTANCE_WITH_NAME]
    mock_script.return_value = ''
    # GetOrCreateVm(vm_name, boot_volume_size, AMI, cpu_cores) where
    # vm_name is the name of an analysis instance that already exists.
    vm, created = aws_mocks.FAKE_AWS_ACCOUNT.ec2.GetOrCreateVm(
        aws_mocks.FAKE_INSTANCE_WITH_NAME.name, 1, 'ami-id', 2)
    mock_get_instance.assert_called_with(aws_mocks.FAKE_INSTANCE_WITH_NAME.name)
    mock_ec2_api.return_value.run_instances.assert_not_called()
    self.assertIsInstance(vm, ec2.AWSInstance)
    self.assertEqual('fake-instance', vm.name)
    self.assertFalse(created)

    # GetOrCreateVm(non_existing_vm, boot_volume_size, AMI, cpu_cores).
    # We mock the GetInstanceById() call to return an empty list, which should
    # mimic an instance that wasn't found. This should trigger run_instances
    # to be called.
    mock_get_instance.return_value = []
    vm, created = aws_mocks.FAKE_AWS_ACCOUNT.ec2.GetOrCreateVm(
        'non-existent-instance-name', 1, 'ami-id', 2)
    mock_get_instance.assert_called_with('non-existent-instance-name')
    mock_ec2_api.return_value.run_instances.assert_called()
    self.assertIsInstance(vm, ec2.AWSInstance)
    self.assertEqual('non-existent-instance-name', vm.name)
    self.assertTrue(created)

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ClientApi')
  def testGetBootVolumeConfigByAmi(self, mock_ec2_api):
    """Test that the boot volume configuration is correctly created."""
    # pylint: disable=protected-access,line-too-long
    mock_ec2_api.return_value.describe_images.return_value = aws_mocks.MOCK_DESCRIBE_AMI
    self.assertIsNone(
        aws_mocks.MOCK_DESCRIBE_AMI['Images'][0]['BlockDeviceMappings'][0]
        ['Ebs']['VolumeSize'])
    self.assertIsNone(
        aws_mocks.MOCK_DESCRIBE_AMI['Images'][0]['BlockDeviceMappings'][0]
        ['Ebs']['VolumeType'])
    config = aws_mocks.FAKE_AWS_ACCOUNT.ec2._GetBootVolumeConfigByAmi(
        'ami-id', 50, 'fake-volume-type')
    # pylint: enable=protected-access,line-too-long
    self.assertEqual(50, config['Ebs']['VolumeSize'])
    self.assertEqual('fake-volume-type', config['Ebs']['VolumeType'])

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ClientApi')
  def testListImages(self, mock_ec2_api):
    """Test that AMI images are correctly listed."""
    describe_images = mock_ec2_api.return_value.describe_images
    describe_images.return_value = aws_mocks.MOCK_DESCRIBE_IMAGES
    images = aws_mocks.FAKE_AWS_ACCOUNT.ec2.ListImages()
    self.assertEqual(2, len(images))
    self.assertIn('Name', images[0])
