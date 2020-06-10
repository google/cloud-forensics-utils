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
"""End to end test for the aws module."""
import typing
import unittest

import botocore

from libcloudforensics.providers.aws.internal.common import LOGGER, EC2_SERVICE
from libcloudforensics.providers.aws.internal import account
from libcloudforensics.providers.aws import forensics
from tests.scripts import utils


class EndToEndTest(unittest.TestCase):
  """End to end test on AWS.

  To run these tests, add your project information to a project_info.json file:

  {
    "instance": "xxx", # required
    "zone": "xxx" # required
    "destination_zone": "xxx", # optional
    "volume_id": "xxx", # optional
    "encrypted_volume_id": "xxx", # optional
  }

  Export a PROJECT_INFO environment variable with the absolute path to your
  file: "user@terminal:~$ export PROJECT_INFO='absolute/path/project_info.json'"

  You will also need to configure your AWS account credentials as per the
  guidelines in https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html # pylint: disable=line-too-long
  """

  @classmethod
  @typing.no_type_check
  def setUpClass(cls):
    try:
      project_info = utils.ReadProjectInfo(['instance', 'zone'])
    except (OSError, RuntimeError, ValueError) as exception:
      raise unittest.SkipTest(str(exception))
    cls.instance_to_analyse = project_info['instance']
    cls.zone = project_info['zone']
    cls.dst_zone = project_info.get('destination_zone', None)
    cls.volume_to_copy = project_info.get('volume_id', None)
    cls.encrypted_volume_to_copy = project_info.get('encrypted_volume_id', None)
    cls.aws = account.AWSAccount(cls.zone)
    cls.analysis_vm_name = 'new-vm-for-analysis'
    cls.analysis_vm, _ = forensics.StartAnalysisVm(cls.analysis_vm_name,
                                                   cls.zone,
                                                   10)
    cls.volumes = []  # List of (AWSAccount, AWSVolume) tuples

  @typing.no_type_check
  def testBootVolumeCopy(self):
    """End to end test on AWS.

    Test copying the boot volume of an instance.
    """

    volume_copy = forensics.CreateVolumeCopy(
        self.zone,
        instance_id=self.instance_to_analyse
        # volume_id=None by default, boot volume of instance will be copied
    )
    # The volume should be created in AWS
    aws_volume = self.aws.ResourceApi(EC2_SERVICE).Volume(volume_copy.volume_id)
    self.assertEqual(aws_volume.volume_id, volume_copy.volume_id)
    self._StoreVolumeForCleanup(self.aws, aws_volume)

  @typing.no_type_check
  def testVolumeCopy(self):
    """End to end test on AWS.

    Test copying a specific volume.
    """

    if not self.volume_to_copy:
      return

    volume_copy = forensics.CreateVolumeCopy(
        self.zone, volume_id=self.volume_to_copy)
    # The volume should be created in AWS
    aws_volume = self.aws.ResourceApi(EC2_SERVICE).Volume(volume_copy.volume_id)
    self.assertEqual(aws_volume.volume_id, volume_copy.volume_id)
    self._StoreVolumeForCleanup(self.aws, aws_volume)

  @typing.no_type_check
  def testVolumeCopyToOtherZone(self):
    """End to end test on AWS.

    Test copying a specific volume to a different AWS availability zone.
    """

    if not (self.volume_to_copy and self.dst_zone):
      return

    volume_copy = forensics.CreateVolumeCopy(
        self.zone, dst_zone=self.dst_zone, volume_id=self.volume_to_copy)
    # The volume should be created in AWS
    aws_account = account.AWSAccount(self.dst_zone)
    aws_volume = aws_account.ResourceApi(EC2_SERVICE).Volume(
        volume_copy.volume_id)
    self.assertEqual(aws_volume.volume_id, volume_copy.volume_id)
    self._StoreVolumeForCleanup(aws_account, aws_volume)

  @typing.no_type_check
  def testEncryptedVolumeCopy(self):
    """End to end test on AWS.

    Test copying a specific encrypted volume.
    """

    if not self.encrypted_volume_to_copy:
      return

    volume_copy = forensics.CreateVolumeCopy(
        self.zone, volume_id=self.encrypted_volume_to_copy)
    # The volume should be created in AWS
    aws_volume = self.aws.ResourceApi(EC2_SERVICE).Volume(volume_copy.volume_id)
    self.assertEqual(aws_volume.volume_id, volume_copy.volume_id)
    self._StoreVolumeForCleanup(self.aws, aws_volume)

  @typing.no_type_check
  def testEncryptedVolumeCopyToOtherZone(self):
    """End to end test on AWS.

    Test copying a specific encrypted volume to a different AWS availability
    zone.
    """

    if not (self.encrypted_volume_to_copy and self.dst_zone):
      return

    volume_copy = forensics.CreateVolumeCopy(
        self.zone,
        dst_zone=self.dst_zone,
        volume_id=self.encrypted_volume_to_copy)
    # The volume should be created in AWS
    aws_account = account.AWSAccount(self.dst_zone)
    aws_volume = aws_account.ResourceApi(EC2_SERVICE).Volume(
        volume_copy.volume_id)
    self.assertEqual(aws_volume.volume_id, volume_copy.volume_id)
    self._StoreVolumeForCleanup(aws_account, aws_volume)

  @typing.no_type_check
  def testStartVm(self):
    """End to end test on AWS.

    Test creating an analysis VM and attaching a copied volume to it.
    """

    volume_copy = forensics.CreateVolumeCopy(
        self.zone, volume_id=self.volume_to_copy)
    self.volumes.append((self.aws, volume_copy))
    # Create and start the analysis VM and attach the boot volume
    self.analysis_vm, _ = forensics.StartAnalysisVm(
        self.analysis_vm_name,
        self.zone,
        10,
        attach_volumes=[(volume_copy.volume_id, '/dev/sdp')]
    )

    # The forensic instance should be live in the analysis AWS account and
    # the volume should be attached
    instance = self.aws.ResourceApi(EC2_SERVICE).Instance(
        self.analysis_vm.instance_id)
    self.assertEqual(instance.instance_id, self.analysis_vm.instance_id)
    self.assertIn(volume_copy.volume_id,
                  [vol.volume_id for vol in instance.volumes.all()])

  @typing.no_type_check
  def _StoreVolumeForCleanup(self, aws_account, volume):
    """Store a volume for cleanup when tests finish.

    Args:
      aws_account (AWSAccount): The AWS account to use.
      volume (boto3.resource.volume): An AWS volume.
    """
    self.volumes.append((aws_account, volume))

  @classmethod
  @typing.no_type_check
  def tearDownClass(cls):
    # Delete the instance
    instance = cls.aws.ResourceApi(EC2_SERVICE).Instance(
        cls.analysis_vm.instance_id)
    instance.terminate()
    cls.aws.ClientApi(EC2_SERVICE).get_waiter('instance_terminated').wait(
        InstanceIds=[instance.instance_id])

    # Delete the volumes
    for aws_account, volume in cls.volumes:
      LOGGER.info('Deleting volume: {0:s}.'.format(volume.volume_id))
      client = aws_account.ClientApi(EC2_SERVICE)
      try:
        client.delete_volume(VolumeId=volume.volume_id)
        client.get_waiter('volume_deleted').wait(VolumeIds=[volume.volume_id])
      except (client.exceptions.ClientError,
              botocore.exceptions.WaiterError) as exception:
        raise RuntimeError('Could not complete cleanup: {0:s}'.format(
            str(exception)))
      LOGGER.info('Volume {0:s} successfully deleted.'.format(volume.volume_id))


if __name__ == '__main__':
  unittest.main()
