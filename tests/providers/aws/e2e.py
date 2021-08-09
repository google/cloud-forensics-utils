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
import warnings
import os
import botocore

from libcloudforensics.providers.aws.internal.common import EC2_SERVICE
from libcloudforensics.providers.aws.internal.common import S3_SERVICE
from libcloudforensics.providers.aws.internal import account
from libcloudforensics.providers.aws import forensics
from libcloudforensics.providers.utils.storage_utils import SplitStoragePath
from libcloudforensics import logging_utils
from tests.scripts import utils

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)


@typing.no_type_check
def IgnoreWarnings(test_func):
  """Disable logging of warning messages.

  If placed above test methods, this annotation will ignore warnings
  displayed by third parties, such as ResourceWarnings due to 'unclosed ssl
  sockets' which are printed in high quantity while running the e2e tests.
  Instead, we can ignore them so that the user can focus on the output from the
  logger.
  """
  def DoTest(self, *args, **kwargs):
    with warnings.catch_warnings():
      warnings.simplefilter("ignore", ResourceWarning)
      warnings.simplefilter("ignore", UserWarning)
      test_func(self, *args, **kwargs)
  return DoTest


class EndToEndTest(unittest.TestCase):
  """End to end test on AWS.

  To run these tests, add your project information to a project_info.json file:

  {
    "instance": "xxx", # required
    "zone": "xxx" # required
    "destination_zone": "xxx", # optional
    "volume_id": "xxx", # optional
    "encrypted_volume_id": "xxx", # optional
    "subnet_id": "xxx", # optional
    "security_group_id": "xxx", # optional
    "s3_destination": "xxx", # optional
    "snapshot_id": "xxx" # optional
  }

  Export a PROJECT_INFO environment variable with the absolute path to your
  file: "user@terminal:~$ export PROJECT_INFO='absolute/path/project_info.json'"

  You will also need to configure your AWS account credentials as per the
  guidelines in https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html # pylint: disable=line-too-long
  """

  @classmethod
  @typing.no_type_check
  @IgnoreWarnings
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
    cls.subnet_id = project_info.get('subnet_id', None)
    cls.security_group_id = project_info.get('security_group_id', None)
    cls.analysis_vm, _ = forensics.StartAnalysisVm(
        cls.analysis_vm_name,
        cls.zone,
        10,
        security_group_id=cls.security_group_id,
        subnet_id=cls.subnet_id)
    cls.volumes = []  # List of (AWSAccount, AWSVolume) tuples

  @typing.no_type_check
  @IgnoreWarnings
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
  @IgnoreWarnings
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
  @IgnoreWarnings
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
  @IgnoreWarnings
  def testListImages(self):
    """End to end test on AWS.

    Test listing AMI images with a filter.
    """

    aws_account = account.AWSAccount(self.zone)
    qfilter = [{'Name': 'name', 'Values': ['Ubuntu 18.04*']}]
    images = aws_account.ec2.ListImages(qfilter)

    self.assertGreater(len(images), 0)
    self.assertIn('Name', images[0])

  @typing.no_type_check
  @IgnoreWarnings
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
  @IgnoreWarnings
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
  @IgnoreWarnings
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
  @IgnoreWarnings
  def tearDownClass(cls):
    # Delete the instance
    cls.analysis_vm.Delete()

    # Delete the volumes
    for aws_account, volume in cls.volumes:
      logger.info('Deleting volume: {0:s}.'.format(volume.volume_id))
      client = aws_account.ClientApi(EC2_SERVICE)
      try:
        client.delete_volume(VolumeId=volume.volume_id)
        client.get_waiter('volume_deleted').wait(VolumeIds=[volume.volume_id])
      except (client.exceptions.ClientError,
              botocore.exceptions.WaiterError) as exception:
        raise RuntimeError('Could not complete cleanup: {0:s}'.format(
            str(exception))) from exception
      logger.info('Volume {0:s} successfully deleted.'.format(volume.volume_id))

class CopyEBSSnapshotToS3E2ETest(unittest.TestCase):
  """End to end test on AWS.

  To run this tests, add your project information to a project_info.json file:
  {
    "zone": "xxx", # required
    "s3_destination": "xxx", # required
    "snapshot_id": "xxx", # required
    "subnet_id": "xxx", # optional
    "security_group_id": "xxx" # optional
  }

  Export a PROJECT_INFO environment variable with the absolute path to your
  file: "user@terminal:~$ export PROJECT_INFO='absolute/path/project_info.json'"
  You will also need to configure your AWS account credentials as per the
  guidelines in https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html # pylint: disable=line-too-long
  """

  @classmethod
  @typing.no_type_check
  @IgnoreWarnings
  def setUpClass(cls):
    try:
      project_info = utils.ReadProjectInfo(
          ['s3_destination', 'zone', 'snapshot_id'])
    except (OSError, RuntimeError, ValueError) as exception:
      raise unittest.SkipTest(str(exception))
    cls.zone = project_info['zone']
    cls.aws = account.AWSAccount(cls.zone)
    cls.subnet_id = project_info.get('subnet_id', None)
    cls.security_group_id = project_info.get('security_group_id', None)
    cls.s3_destination = project_info.get('s3_destination', None)
    cls.snapshot_id = project_info.get('snapshot_id', None)

  @typing.no_type_check
  @IgnoreWarnings
  def testCopyEBSSnapshotToS3(self):
    """End to end test on AWS.

    Test copying an EBS snapshot into S3.
    """

    if not self.s3_destination.startswith('s3://'):
      self.s3_destination = 's3://' + self.s3_destination
    path_components = SplitStoragePath(self.s3_destination)
    bucket = path_components[0]
    object_path = path_components[1]

    forensics.CopyEBSSnapshotToS3(
      self.s3_destination,
      self.snapshot_id,
      'ebsCopy',
      self.zone,
      subnet_id=self.subnet_id,
      security_group_id=self.security_group_id,
      cleanup_iam=True)

    aws_account = account.AWSAccount(self.zone)
    directory = '{0:s}/{1:s}/'.format(object_path, self.snapshot_id)
    self.assertEqual(
      aws_account.s3.CheckForObject(bucket, directory + 'image.bin'), True)
    self.assertEqual(
      aws_account.s3.CheckForObject(bucket, directory + 'log.txt'), True)
    self.assertEqual(
      aws_account.s3.CheckForObject(bucket, directory + 'hlog.txt'), True)
    self.assertEqual(
      aws_account.s3.CheckForObject(bucket, directory + 'mlog.txt'), True)

    # Cleanup
    aws_account.s3.RmObject(bucket, directory + 'image.bin')
    aws_account.s3.RmObject(bucket, directory + 'log.txt')
    aws_account.s3.RmObject(bucket, directory + 'hlog.txt')
    aws_account.s3.RmObject(bucket, directory + 'mlog.txt')


class S3EndToEndTest(unittest.TestCase):
  """End to end test on AWS.

  To run this tests, add your project information to a project_info.json file:
  {
    "zone": "xxx" # required
    "s3_bucket": "xxx", # required, should not exist
  }
  Export a PROJECT_INFO environment variable with the absolute path to your
  file: "user@terminal:~$ export PROJECT_INFO='absolute/path/project_info.json'"
  You will also need to configure your AWS account credentials as per the
  guidelines in https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html # pylint: disable=line-too-long
  """

  @classmethod
  @typing.no_type_check
  @IgnoreWarnings
  def setUpClass(cls):
    try:
      project_info = utils.ReadProjectInfo(['s3_bucket', 'zone'])
    except (OSError, RuntimeError, ValueError) as exception:
      raise unittest.SkipTest(str(exception))
    cls.zone = project_info['zone']
    cls.s3_bucket = project_info['s3_bucket']

  @typing.no_type_check
  @IgnoreWarnings
  def testS3(self):
    """S3 End to end test on AWS.

    Test creating a bucket, uploading an object, fetching it, removing the
    object and deleting the bucket.
    """
    aws_account = account.AWSAccount(self.zone)
    client = aws_account.ClientApi(S3_SERVICE)
    key = __file__.split('/')[-1]
    local_path = os.path.realpath(__file__)

    # Create the bucket
    aws_account.s3.CreateBucket(self.s3_bucket)
    self.assertIn('LocationConstraint',
      client.get_bucket_location(Bucket=self.s3_bucket))

    # Upload an object
    aws_account.s3.Put(self.s3_bucket, local_path)
    self.assertTrue(aws_account.s3.CheckForObject(self.s3_bucket, key))

    # Remove the object
    aws_account.s3.RmObject(self.s3_bucket, key)
    self.assertFalse(aws_account.s3.CheckForObject(self.s3_bucket, key))

    # Remove the bucket
    aws_account.s3.RmBucket(self.s3_bucket)
    with self.assertRaises(client.exceptions.ClientError):
      client.get_bucket_location(Bucket=self.s3_bucket)

  @classmethod
  @typing.no_type_check
  @IgnoreWarnings
  def tearDownClass(cls):
    try:
      aws_account = account.AWSAccount(cls.zone)
      aws_account.s3.RmBucket(cls.s3_bucket)
    except botocore.exceptions.ClientError:
      # Was already deleted, or failed creation
      pass


if __name__ == '__main__':
  unittest.main()
