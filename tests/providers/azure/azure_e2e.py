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
"""End to end test for the Azure module."""

import typing
import unittest

from msrestazure import azure_exceptions  # pylint: disable=import-error
from libcloudforensics import logging_utils
from libcloudforensics.providers.azure.internal import account
from libcloudforensics.providers.azure import forensics
from tests.scripts import utils

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)


class EndToEndTest(unittest.TestCase):
  # pylint: disable=line-too-long
  """End to end test on Azure.

  To run these tests, add your project information to a project_info.json file:

  {
    "resource_group_name": xxx,  # required
    "instance_name": xxx,  # required
    "disk_name": xxx,  # optional,
    "dst_region": xxx  # optional
  }


  Export a PROJECT_INFO environment variable with the absolute path to your
  file: "user@terminal:~$ export PROJECT_INFO='absolute/path/project_info.json'"

  You will also need to configure your AZ account credentials as per the
  guidelines in https://docs.microsoft.com/en-us/azure/developer/python/azure-sdk-authenticate?tabs=cmd
  """
  # pylint: enable=line-too-long

  @classmethod
  @typing.no_type_check
  def setUpClass(cls):
    try:
      project_info = utils.ReadProjectInfo(
          ['resource_group_name', 'instance_name'])
    except (OSError, RuntimeError, ValueError) as exception:
      raise unittest.SkipTest(str(exception))
    cls.resource_group_name = project_info['resource_group_name']
    cls.instance_to_analyse = project_info['instance_name']
    cls.disk_to_copy = project_info.get('disk_name')
    cls.dst_region = project_info.get('dst_region')
    cls.az = account.AZAccount(cls.resource_group_name)
    cls.disks = []  # List of AZDisks for test cleanup

  @typing.no_type_check
  def testBootDiskCopy(self):
    """End to end test on Azure.

    Test copying the boot disk of an instance.
    """

    disk_copy = forensics.CreateDiskCopy(
        self.resource_group_name,
        instance_name=self.instance_to_analyse
        # disk_name=None by default, boot disk of instance will be copied
    )
    # The disk should be present in Azure
    remote_disk = self.az.compute_client.disks.get(
        disk_copy.resource_group_name, disk_copy.name)
    self.assertIsNotNone(remote_disk)
    self.assertEqual(disk_copy.name, remote_disk.name)
    self._StoreDiskForCleanup(disk_copy)

  @typing.no_type_check
  def testDiskCopy(self):
    """End to end test on Azure.

    Test copying a specific disk.
    """

    if not self.disk_to_copy:
      return

    disk_copy = forensics.CreateDiskCopy(
        self.resource_group_name,
        disk_name=self.disk_to_copy)
    # The disk should be present in Azure
    remote_disk = self.az.compute_client.disks.get(
        disk_copy.resource_group_name, disk_copy.name)
    self.assertIsNotNone(remote_disk)
    self.assertEqual(disk_copy.name, remote_disk.name)

    # Since we make a copy of the same disk but in a different region in next
    # test, we need to delete the copy we just created as Azure does not
    # permit same-name disks in different regions.
    self.az.compute_client.disks.delete(
        disk_copy.resource_group_name, disk_copy.name)

  @typing.no_type_check
  def testDiskCopyToOtherZone(self):
    """End to end test on Azure.

    Test copying a specific disk to a different Azure region.
    """

    if not (self.disk_to_copy and self.dst_region):
      return

    disk_copy = forensics.CreateDiskCopy(
        self.resource_group_name,
        disk_name=self.disk_to_copy,
        region=self.dst_region)
    # The disk should be present in Azure and be in self.dst_region
    remote_disk = self.az.compute_client.disks.get(
        disk_copy.resource_group_name, disk_copy.name)
    self.assertIsNotNone(remote_disk)
    self.assertEqual(disk_copy.name, remote_disk.name)
    self.assertEqual(self.dst_region, remote_disk.location)
    self._StoreDiskForCleanup(disk_copy)

  @typing.no_type_check
  def _StoreDiskForCleanup(self, disk):
    """Store a disk for cleanup when tests finish.

    Args:
      disk (AZDisk): An Azure disk.
    """
    self.disks.append(disk)

  @classmethod
  @typing.no_type_check
  def tearDownClass(cls):
    # Delete the disks
    for disk in cls.disks:
      logger.info('Deleting disk: {0:s}.'.format(disk.name))
      try:
        cls.az.compute_client.disks.delete(disk.resource_group_name, disk.name)
      except azure_exceptions.CloudError as exception:
        raise RuntimeError('Could not complete cleanup: {0:s}'.format(
            str(exception)))
      logger.info('Disk {0:s} successfully deleted.'.format(disk.name))


if __name__ == '__main__':
  unittest.main()
