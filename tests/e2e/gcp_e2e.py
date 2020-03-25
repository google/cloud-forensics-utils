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
"""End to end test for the gcp module."""

import unittest
import logging
import json
import time
import os

from googleapiclient.errors import HttpError

from libcloudforensics import gcp

log = logging.getLogger()


class EndToEndTest(unittest.TestCase):
  """End to end test on GCP.

  This end-to-end test runs directly on GCP and tests that:
    1. The gcp.py module connects to the target instance and makes a snapshot
    of the boot disk (by default) or of the disk passed in parameter to the
    gcp.create_disk_copy() method.
    2. A new disk is created from the taken snapshot.
    3. If an analysis VM already exists, the module will attach the disk
    copy to the VM. Otherwise, it will create a new GCP instance for analysis
    purpose and attach the disk copy to it.

  To run this test, add your project information to a project_info.json file:

  {
    "project_id": "xxx", # required
    "instance": "xxx", # required
    "disk": "xxx", # optional
    "zone": "xxx" # required
  }

  Export a PROJECT_INFO environment variable with the absolute path to your
  file: "user@terminal:~$ export PROJECT_INFO='absolute/path/project_info.json'"
  """

  def __init__(self, *args, **kwargs):
    super(EndToEndTest, self).__init__(*args, **kwargs)
    try:
      project_info = ReadProjectInfo()
    except (OSError, RuntimeError, ValueError) as exception:
      self.error_msg = str(exception)
      return
    self.project_id = project_info['project_id']
    self.instance_to_analyse = project_info['instance']
    # Optional: test a disk other than the boot disk
    self.disk_to_forensic = project_info.get('disk', None)
    self.zone = project_info['zone']
    self.gcp = gcp.GoogleCloudProject(self.project_id, self.zone)

  def setUp(self):
    if hasattr(self, 'error_msg'):
      raise unittest.SkipTest(self.error_msg)
    self.boot_disk_copy = None
    self.disk_to_forensic_copy = None
    self.analysis_vm = None
    self.analysis_vm_name = 'new-vm-for-analysis'

  def test_end_to_end_boot_disk(self):
    """End to end test on GCP.

    This end-to-end test runs directly on GCP and tests that:
      1. The gcp.py module connects to the target instance and makes a
      snapshot of the boot disk.
      2. A new disk is created from the taken snapshot.
      3. If an analysis VM already exists, the module will attach the disk
      copy to the VM. Otherwise, it will create a new GCP instance for
      analysis purpose and attach the boot disk copy to it.
    """

    # Make a copy of the boot disk of the instance to analyse
    self.boot_disk_copy = gcp.CreateDiskCopy(
        src_proj=self.project_id,
        dst_proj=self.project_id,
        instance_name=self.instance_to_analyse,
        zone=self.zone,
        # disk_name=None by default, boot disk will be copied
    )

    # The disk copy should be attached to the analysis project
    operation = self.gcp.GceApi().disks().get(
        project=self.project_id,
        zone=self.zone,
        disk=self.boot_disk_copy.name).execute()
    result = self.gcp.GceOperation(operation, zone=self.zone)
    self.assertEqual(result['name'], self.boot_disk_copy.name)

    # Create and start the analysis VM and attach the boot disk
    self.analysis_vm, _ = gcp.StartAnalysisVm(
        project=self.project_id,
        vm_name=self.analysis_vm_name,
        zone=self.zone,
        boot_disk_size=10,
        cpu_cores=4,
        attach_disk=self.boot_disk_copy
    )

    # The forensic instance should be live in the analysis GCP project and
    # the disk should be attached
    operation = self.gcp.GceApi().instances().get(
        project=self.project_id,
        zone=self.zone,
        instance=self.analysis_vm_name).execute()
    result = self.gcp.GceOperation(operation, zone=self.zone)
    self.assertEqual(result['name'], self.analysis_vm_name)

    for disk in result['disks']:
      if disk['source'].split("/")[-1] == self.boot_disk_copy.name:
        return
    self.fail('Error: could not find the disk {0:s} in instance {1:s}'.format(
        self.boot_disk_copy.name, self.analysis_vm_name
    ))

  def test_end_to_end_other_disk(self):
    """End to end test on GCP.

    This end-to-end test runs directly on GCP and tests that:
      1. The gcp.py module connects to the target instance and makes a
      snapshot of disk passed to the 'disk_name' parameter in the
      create_disk_copy() method.
      2. A new disk is created from the taken snapshot.
      3. If an analysis VM already exists, the module will attach the disk
      copy to the VM. Otherwise, it will create a new GCP instance for
      analysis purpose and attach the boot disk copy to it.
    """

    # Make a copy of another disk of the instance to analyse
    self.disk_to_forensic_copy = gcp.CreateDiskCopy(
        src_proj=self.project_id,
        dst_proj=self.project_id,
        instance_name=self.instance_to_analyse,
        zone=self.zone,
        disk_name=self.disk_to_forensic
    )

    # The disk copy should be attached to the analysis project
    operation = self.gcp.GceApi().disks().get(
        project=self.project_id,
        zone=self.zone,
        disk=self.disk_to_forensic_copy.name).execute()
    result = self.gcp.GceOperation(operation, zone=self.zone)
    self.assertEqual(result['name'], self.disk_to_forensic_copy.name)

    # Create and start the analysis VM and attach the disk to forensic
    self.analysis_vm, _ = gcp.StartAnalysisVm(
        project=self.project_id,
        vm_name=self.analysis_vm_name,
        zone=self.zone,
        boot_disk_size=10,
        cpu_cores=4,
        attach_disk=self.disk_to_forensic_copy
    )

    # The forensic instance should be live in the analysis GCP project and
    # the disk should be attached
    operation = self.gcp.GceApi().instances().get(
        project=self.project_id,
        zone=self.zone,
        instance=self.analysis_vm_name).execute()
    result = self.gcp.GceOperation(operation, zone=self.zone)
    self.assertEqual(result['name'], self.analysis_vm_name)

    for disk in result['disks']:
      if disk['source'].split("/")[-1] == self.disk_to_forensic_copy.name:
        return
    self.fail('Error: could not find the disk {0:s} in instance {1:s}'.format(
        self.disk_to_forensic_copy.name, self.analysis_vm_name
    ))

  def tearDown(self):
    project = gcp.GoogleCloudProject(project_id=self.project_id,
                                     default_zone=self.zone)

    disks = self.analysis_vm.ListDisks()

    # delete the created forensics VMs
    log.info('Deleting analysis instance: {0:s}.'.format(
        self.analysis_vm.name))
    operation = project.GceApi().instances().delete(
        project=project.project_id,
        zone=self.zone,
        instance=self.analysis_vm.name
    ).execute()
    try:
      project.GceOperation(operation, block=True)
    except HttpError:
      # GceOperation triggers a while(True) loop that checks on the
      # operation ID. Sometimes it loops one more time right when the
      # operation has finished and thus the associated ID doesn't exists
      # anymore, throwing an HttpError. We can ignore this.
      pass
    log.info('Instance {0:s} successfully deleted.'.format(
        self.analysis_vm.name))

    # delete the copied disks
    # we ignore the disk that was created for the analysis VM (disks[0]) as
    # it is deleted in the previous operation
    for disk in disks[1:]:
      log.info('Deleting disk: {0:s}.'.format(disk))
      while True:
        try:
          operation = project.GceApi().disks().delete(
              project=project.project_id,
              zone=self.zone,
              disk=disk
          ).execute()
          project.GceOperation(operation, block=True)
          break
        except HttpError as exception:
          # The gce api will throw a 400 until the analysis vm's deletion is
          # correctly propagated. When the disk is finally deleted, it will
          # throw a 404 not found if it looped one more time after deletion.
          if exception.resp.status == 404:
            break
          if exception.resp.status != 400:
            log.warning('Could not delete the disk {0:s}: {1:s}'.format(
                disk, str(exception)
            ))
          # Throttle the requests to one every 10 seconds
          time.sleep(10)

      log.info('Disk {0:s} successfully deleted.'.format(
          disk))


def ReadProjectInfo():
  """ Read project information to run e2e test.

  Returns:
    dict: A dict with the project information.

  Raises:
    OSError: if the file cannot be found, opened or closed.
    RuntimeError: if the json file cannot be parsed.
    ValueError: if the json file does not have the required properties.
  """
  project_info = os.environ.get('PROJECT_INFO')
  if project_info is None:
    raise OSError('Error: please make sure that you defined the '
                  '"PROJECT_INFO" environment variable pointing '
                  'to your project settings.')
  try:
    json_file = open(project_info)
    try:
      project_info = json.load(json_file)
    except ValueError as exception:
      raise RuntimeError('Error: cannot parse JSON file. {0:s}'.format(
          str(exception)))
    json_file.close()
  except OSError as exception:
    raise OSError('Error: could not open/close file {0:s}: {1:s}'.format(
        project_info, str(exception)
    ))

  if not all(key in project_info for key in ['project_id', 'instance',
                                             'zone']):
    raise ValueError('Error: please make sure that your JSON file '
                     'has the required entries. The file should '
                     'contain at least the following: ["project_id", '
                     '"instance", "zone"].')

  return project_info


if __name__ == '__main__':
  unittest.main()
