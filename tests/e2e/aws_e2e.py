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

import json
import os
import unittest
import logging

from libcloudforensics import aws

log = logging.getLogger()
EC2_SERVICE = 'ec2'


class EndToEndTest(unittest.TestCase):
  """End to end test on AWS.

  This end-to-end test runs directly on AWS and tests that:
    1. The aws.py module connects to the target instance and makes a snapshot
        of the boot volume (by default) or of the volume passed in parameter
        to the aws.CreateVolumeCopy() method.
    2. A new volume is created from the taken snapshot.

  To run this test, add your project information to a project_info.json file:

  {
    "instance": "xxx", # required
    "zone": "xxx" # required
    "volume_id": "xxx", # optional
  }

  Export a PROJECT_INFO environment variable with the absolute path to your
  file: "user@terminal:~$ export PROJECT_INFO='absolute/path/project_info.json'"

  You will also need to configure your AWS account credentials as per the
  guidelines in https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html # pylint: disable=line-too-long
  """

  @classmethod
  def setUpClass(cls):
    try:
      project_info = ReadProjectInfo()
    except (OSError, RuntimeError, ValueError) as exception:
      raise unittest.SkipTest(str(exception))
    cls.instance_to_analyse = project_info['instance']
    cls.zone = project_info['zone']
    cls.volume_to_forensic = project_info.get('volume_id', None)
    cls.aws = aws.AWSAccount(cls.zone)
    cls.analysis_vm_name = 'new-vm-for-analysis'
    cls.analysis_vm, _ = aws.StartAnalysisVm(
        cls.analysis_vm_name, cls.zone, 10, 4)
    cls.volumes = []

  def test_end_to_end_boot_volume(self):
    """End to end test on AWS.

    This end-to-end test runs directly on AWS and tests that:
      1. The aws.py module connects to the target instance and makes a snapshot
          of the boot volume (by default) or of the volume passed in
          parameter to the aws.CreateVolumeCopy() method.
      2. A new volume is created from the taken snapshot.
    """

    # Make a copy of the boot volume of the instance to analyse
    boot_volume_copy = aws.CreateVolumeCopy(
        self.zone,
        instance_id=self.instance_to_analyse
        # volume_id=None by default, boot volume of instance will be copied
    )

    # The volume copy should be attached to the AWS account
    self.volumes.append(
        self.aws.ResourceApi(EC2_SERVICE).Volume(boot_volume_copy.volume_id))
    self.assertEqual(self.volumes[-1].volume_id, boot_volume_copy.volume_id)

  def test_end_to_end_other_volume(self):
    """End to end test on AWS.

    This end-to-end test runs directly on AWS and tests that:
      1. The aws.py module connects to the target instance and makes a
          snapshot of volume passed to the 'volume_id' parameter in the
          CreateVolumeCopy() method.
      2. A new volume is created from the taken snapshot.
    """

    if not self.volume_to_forensic:
      return

    # Make a copy of another volume of the instance to analyse
    other_volume_copy = aws.CreateVolumeCopy(
        self.zone,
        volume_id=self.volume_to_forensic)

    # The volume copy should be attached to the AWS account
    self.volumes.append(
        self.aws.ResourceApi(EC2_SERVICE).Volume(other_volume_copy.volume_id))
    self.assertEqual(self.volumes[-1].volume_id, other_volume_copy.volume_id)

  def test_end_to_end_vm(self):
    """End to end test on AWS.

    This tests that an analysis VM is correctly created and that a volume
        passed to the attach_volume parameter is correctly attached.
    """

    volume_to_attach = aws.CreateVolumeCopy(
        self.zone,
        volume_id=self.volume_to_forensic)
    self.volumes.append(volume_to_attach)
    # Create and start the analysis VM and attach the boot volume
    self.analysis_vm, _ = aws.StartAnalysisVm(
        self.analysis_vm_name,
        self.zone,
        10,
        4,
        attach_volume=volume_to_attach,
        device_name='/dev/sdp'
    )

    # The forensic instance should be live in the analysis AWS account and
    # the volume should be attached
    instance = self.aws.ResourceApi(EC2_SERVICE).Instance(
        self.analysis_vm.instance_id)
    self.assertEqual(instance.instance_id, self.analysis_vm.instance_id)
    self.assertIn(volume_to_attach.volume_id,
                  [vol.volume_id for vol in instance.volumes.all()])

  @classmethod
  def tearDownClass(cls):
    client = cls.aws.ClientApi(EC2_SERVICE)
    # Delete the instance
    instance = cls.aws.ResourceApi(EC2_SERVICE).Instance(
        cls.analysis_vm.instance_id)
    instance.terminate()
    client.get_waiter('instance_terminated').wait(InstanceIds=[
        instance.instance_id])

    # Delete the volumes
    for volume in cls.volumes:
      log.info('Deleting volume: {0:s}.'.format(volume.volume_id))
      try:
        client.delete_volume(VolumeId=volume.volume_id)
        client.get_waiter('volume_deleted').wait(VolumeIds=[volume.volume_id])
      except client.exceptions.ClientError as exception:
        raise RuntimeError('Could not complete cleanup: {0:s}'.format(
            str(exception)))
      log.info('Volume {0:s} successfully deleted.'.format(volume.volume_id))


def ReadProjectInfo():
  """Read project information to run e2e test.

  Returns:
    dict: A dict with the project information.

  Raises:
    OSError: If the file cannot be found, opened or closed.
    RuntimeError: If the json file cannot be parsed.
    ValueError: If the json file does not have the required properties.
  """
  project_info = os.environ.get('PROJECT_INFO')
  if project_info is None:
    raise OSError('Please make sure that you defined the '
                  '"PROJECT_INFO" environment variable pointing '
                  'to your project settings.')
  try:
    json_file = open(project_info)
    try:
      project_info = json.load(json_file)
    except ValueError as exception:
      raise RuntimeError('Cannot parse JSON file. {0:s}'.format(
          str(exception)))
    json_file.close()
  except OSError as exception:
    raise OSError('Could not open/close file {0:s}: {1:s}'.format(
        project_info, str(exception)))

  if not all(key in project_info for key in ['instance', 'zone']):
    raise ValueError('Please make sure that your JSON file '
                     'has the required entries. The file should '
                     'contain at least the following: ["instance", "zone"].')

  return project_info


if __name__ == '__main__':
  unittest.main()
