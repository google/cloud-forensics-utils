# -*- coding: utf-8 -*-
# Copyright 2021 Google Inc.
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
"""End to end test for the aws cli utility."""
import subprocess
import typing
import unittest
import warnings
from time import sleep

import botocore
from libcloudforensics.errors import ResourceNotFoundError
from libcloudforensics.errors import ResourceCreationError
from libcloudforensics.providers.aws.internal.common import EC2_SERVICE
from libcloudforensics.providers.aws.internal import account
from libcloudforensics import logging_utils
from tests.providers.aws import aws_cli
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
    cls.cli = aws_cli.AWSCLIHelper()
    cls.analysis_vm = cls._RunStartAnalysisVm(cls.analysis_vm_name, cls.zone)
    cls.volumes = []  # List of (AWSAccount, AWSVolume) tuples

  @typing.no_type_check
  @IgnoreWarnings
  def testBootVolumeCopy(self):
    """End to end test on AWS.

    Test copying the boot volume of an instance.
    """

    volume_copy = self._RunCreateVolumeCopy(
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

    volume_copy = self._RunCreateVolumeCopy(
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

    # Assert that the source volume is in the source zone
    self.assertEqual(self.zone, self.aws.ResourceApi(EC2_SERVICE).Volume(
        self.volume_to_copy).availability_zone)

    # Create the copy
    volume_copy = self._RunCreateVolumeCopy(
        self.zone, dst_zone=self.dst_zone, volume_id=self.volume_to_copy)

    # The volume should be created in AWS, and should be in the dest zone
    aws_account = account.AWSAccount(self.dst_zone)
    aws_volume = aws_account.ResourceApi(EC2_SERVICE).Volume(
        volume_copy.volume_id)
    self.assertEqual(aws_volume.volume_id, volume_copy.volume_id)
    self.assertNotEqual(self.zone, aws_volume.availability_zone)
    self.assertEqual(self.dst_zone, aws_volume.availability_zone)

    self._StoreVolumeForCleanup(aws_account, aws_volume)

  @typing.no_type_check
  @IgnoreWarnings
  def testListImages(self):
    """End to end test on AWS.

    Test listing AMI images with a filter.
    """

    qfilter = 'ubuntu*'
    cmd = self.cli.PrepareListImagesCmd(self.zone, qfilter=qfilter)
    try:
      output = subprocess.check_output(
          cmd.split(), stderr=subprocess.STDOUT, shell=False)
    except subprocess.CalledProcessError as error:
      raise RuntimeError('Failed retrieving AMI images') from error
    if not output:
      raise RuntimeError('Could not find any images to list')
    logger.info(output)
    # For this function, the CLI tool only prints one line per result, or
    # nothing at all. Therefore if there's an output, there's a result.
    images = str(output).split('\n')
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

    # Assert that the source volume is encrypted
    self.assertTrue(self.aws.ResourceApi(EC2_SERVICE).Volume(
        self.encrypted_volume_to_copy).encrypted)

    # Create the copy
    volume_copy = self._RunCreateVolumeCopy(
        self.zone, volume_id=self.encrypted_volume_to_copy)

    # The volume should be created in AWS, and should also be encrypted
    aws_volume = self.aws.ResourceApi(EC2_SERVICE).Volume(volume_copy.volume_id)
    self.assertEqual(aws_volume.volume_id, volume_copy.volume_id)
    self.assertTrue(aws_volume.encrypted)

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

    # Assert that the source volume is encrypted and in the source zone
    self.assertTrue(self.aws.ResourceApi(EC2_SERVICE).Volume(
        self.encrypted_volume_to_copy).encrypted)
    self.assertEqual(self.zone, self.aws.ResourceApi(EC2_SERVICE).Volume(
        self.volume_to_copy).availability_zone)

    # Create the copy
    volume_copy = self._RunCreateVolumeCopy(
        self.zone,
        dst_zone=self.dst_zone,
        volume_id=self.encrypted_volume_to_copy)

    # The volume should be created in AWS in the dest zone, and should also
    # be encrypted
    aws_account = account.AWSAccount(self.dst_zone)
    aws_volume = aws_account.ResourceApi(EC2_SERVICE).Volume(
        volume_copy.volume_id)
    self.assertEqual(aws_volume.volume_id, volume_copy.volume_id)
    self.assertTrue(aws_volume.encrypted)
    self.assertNotEqual(self.zone, aws_volume.availability_zone)
    self.assertEqual(self.dst_zone, aws_volume.availability_zone)

    self._StoreVolumeForCleanup(aws_account, aws_volume)

  @typing.no_type_check
  @IgnoreWarnings
  def testStartVm(self):
    """End to end test on AWS.

    Test creating an analysis VM and attaching a copied volume to it.
    """

    volume_copy = self._RunCreateVolumeCopy(
        self.zone, volume_id=self.volume_to_copy)
    self.volumes.append((self.aws, volume_copy))
    # Create and start the analysis VM and attach the boot volume
    self.analysis_vm = self._RunStartAnalysisVm(
        self.analysis_vm_name,
        self.zone,
        attach_volumes=[volume_copy.volume_id]
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
  def _RunStartAnalysisVm(cls, vm_name, zone, attach_volumes=None):
    cmd = cls.cli.PrepareStartAnalysisVmCmd(
        vm_name, zone, attach_volumes=attach_volumes)
    try:
      output = subprocess.check_output(
          cmd.split(), stderr=subprocess.STDOUT, shell=False)
    except subprocess.CalledProcessError as error:
      raise ResourceCreationError(
          'Failed creating VM in account profile {0:s}'.format(
              cls.aws.aws_profile), __name__) from error
    logger.info(output)
    try:
      return cls.aws.ec2.GetInstancesByName(vm_name)[0]
    except ResourceNotFoundError as error:
      raise ResourceNotFoundError(
          'Failed finding created VM in account profile {0:s}'.format(
              cls.aws.aws_profile), __name__) from error

  @classmethod
  @typing.no_type_check
  def _RunCreateVolumeCopy(
      cls, zone, dst_zone=None, instance_id=None, volume_id=None):
    cmd = cls.cli.PrepareCreateVolumeCopyCmd(
        zone, dst_zone=dst_zone, instance_id=instance_id, volume_id=volume_id)
    try:
      output = subprocess.check_output(
          cmd.split(), stderr=subprocess.STDOUT, shell=False)
    except subprocess.CalledProcessError as error:
      raise ResourceCreationError('Failed copying volume', __name__) from error
    if not output:
      raise ResourceCreationError(
          'Could not find volume copy result', __name__)
    volume_copy_name = output.decode('utf-8').split(' ')[-1]
    volume_copy_name = volume_copy_name[:volume_copy_name.rindex('copy') + 4]
    logger.info(output)
    logger.info("Volume successfully copied to {0:s}".format(
        volume_copy_name))
    try:
      return cls.aws.ebs.GetVolumesByName(volume_copy_name)[0]
    except ResourceNotFoundError as error:
      raise ResourceNotFoundError(
          'Failed finding copied volume in account profile {0:s}'.format(
              cls.aws.aws_profile), __name__) from error

  @classmethod
  @typing.no_type_check
  @IgnoreWarnings
  def tearDownClass(cls):
    # Wait a bit so that AWS sync
    sleep(30)
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
        if 'InvalidVolume.NotFound' in str(exception):
          # Volume already deleted, continue
          continue
        raise RuntimeError('Could not complete cleanup: {0:s}'.format(
            str(exception))) from exception
      logger.info('Volume {0:s} successfully deleted.'.format(volume.volume_id))


if __name__ == '__main__':
  unittest.main()
