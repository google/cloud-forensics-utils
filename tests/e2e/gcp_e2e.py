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
        copy to the VM. Otherwise, it will create a new GCP instance for
        analysis purpose and attach the disk copy to it.

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

  @classmethod
  def setUpClass(cls):
    try:
      project_info = ReadProjectInfo()
    except (OSError, RuntimeError, ValueError) as exception:
      raise unittest.SkipTest(str(exception))
    cls.project_id = project_info['project_id']
    cls.instance_to_analyse = project_info['instance']
    # Optional: test a disk other than the boot disk
    cls.disk_to_forensic = project_info.get('disk', None)
    cls.zone = project_info['zone']
    cls.gcp = gcp.GoogleCloudProject(cls.project_id, cls.zone)
    cls.analysis_vm_name = 'new-vm-for-analysis'
    # Create and start the analysis VM
    cls.analysis_vm, _ = gcp.StartAnalysisVm(
        project=cls.project_id, vm_name=cls.analysis_vm_name, zone=cls.zone,
        boot_disk_size=10, boot_disk_type='pd-ssd', cpu_cores=4)

  def setUp(self):
    self.project_id = EndToEndTest.project_id
    self.instance_to_analyse = EndToEndTest.instance_to_analyse
    self.disk_to_forensic = EndToEndTest.disk_to_forensic
    self.gcp = EndToEndTest.gcp
    self.zone = EndToEndTest.zone
    self.analysis_vm_name = EndToEndTest.analysis_vm.name
    self.boot_disk_copy = None
    self.disk_to_forensic_copy = None

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
    gce_disk_client = self.gcp.GceApi().disks()
    request = gce_disk_client.get(
        project=self.project_id, zone=self.zone, disk=self.boot_disk_copy.name)
    result = request.execute()
    self.assertEqual(result['name'], self.boot_disk_copy.name)

    # Get the analysis VM and attach the evidence boot disk
    self.analysis_vm, _ = gcp.StartAnalysisVm(
        project=self.project_id, vm_name=self.analysis_vm_name, zone=self.zone,
        boot_disk_size=10, boot_disk_type='pd-ssd', cpu_cores=4,
        attach_disk=[self.boot_disk_copy])

    # The forensic instance should be live in the analysis GCP project and
    # the disk should be attached
    gce_instance_client = self.gcp.GceApi().instances()
    request = gce_instance_client.get(
        project=self.project_id, zone=self.zone, instance=self.analysis_vm_name)
    result = request.execute()
    self.assertEqual(result['name'], self.analysis_vm_name)

    for disk in result['disks']:
      if disk['boot']:
        request = gce_disk_client.get(project=self.project_id,
                                      zone=self.zone,
                                      disk=disk['source'].split('/')[-1])
        boot_disk = request.execute()
        self.assertEqual('pd-ssd', boot_disk['type'].rsplit('/', 1)[-1])
      if disk['source'].split('/')[-1] == self.boot_disk_copy.name:
        return
    self.fail(
        'Error: could not find the disk {0:s} in instance {1:s}'.format(
            self.boot_disk_copy.name, self.analysis_vm_name))

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
        src_proj=self.project_id, dst_proj=self.project_id,
        instance_name=self.instance_to_analyse, zone=self.zone,
        disk_name=self.disk_to_forensic)

    # The disk copy should be existing in the analysis project
    gce_disk_client = self.gcp.GceApi().disks()
    request = gce_disk_client.get(
        project=self.project_id, zone=self.zone,
        disk=self.disk_to_forensic_copy.name)
    result = request.execute()
    self.assertEqual(result['name'], self.disk_to_forensic_copy.name)

    # Get the analysis VM and attach the evidence disk to forensic
    self.analysis_vm, _ = gcp.StartAnalysisVm(
        project=self.project_id, vm_name=self.analysis_vm_name, zone=self.zone,
        boot_disk_size=10, boot_disk_type='pd-ssd', cpu_cores=4,
        attach_disk=[self.disk_to_forensic_copy])

    # The forensic instance should be live in the analysis GCP project and
    # the disk should be attached
    gce_instance_client = self.gcp.GceApi().instances()
    request = gce_instance_client.get(
        project=self.project_id, zone=self.zone, instance=self.analysis_vm_name)
    result = request.execute()
    self.assertEqual(result['name'], self.analysis_vm_name)

    for disk in result['disks']:
      if disk['boot']:
        request = gce_disk_client.get(project=self.project_id,
                                      zone=self.zone,
                                      disk=disk['source'].split('/')[-1])
        boot_disk = request.execute()
        self.assertEqual('pd-ssd', boot_disk['type'].rsplit('/', 1)[-1])
      if disk['source'].split('/')[-1] == self.disk_to_forensic_copy.name:
        return
    self.fail(
        'Error: could not find the disk {0:s} in instance {1:s}'.format(
            self.disk_to_forensic_copy.name, self.analysis_vm_name))

  @classmethod
  def tearDownClass(cls):
    analysis_vm = cls.analysis_vm
    zone = cls.zone
    project = cls.gcp
    disks = analysis_vm.ListDisks()
    # delete the created forensics VMs
    log.info('Deleting analysis instance: {0:s}.'.format(analysis_vm.name))
    gce_instance_client = project.GceApi().instances()
    request = gce_instance_client.delete(
        project=project.project_id, zone=zone, instance=analysis_vm.name)
    response = request.execute()
    try:
      project.BlockOperation(response)
    except HttpError:
      # BlockOperation triggers a while(True) loop that checks on the
      # operation ID. Sometimes it loops one more time right when the
      # operation has finished and thus the associated ID doesn't exists
      # anymore, throwing an HttpError. We can ignore this.
      pass
    log.info('Instance {0:s} successfully deleted.'.format(analysis_vm.name))

    # delete the copied disks
    # we ignore the disk that was created for the analysis VM (disks[0]) as
    # it is deleted in the previous operation
    for disk in disks[1:]:
      log.info('Deleting disk: {0:s}.'.format(disk))
      while True:
        try:
          gce_disk_client = project.GceApi().disks()
          request = gce_disk_client.delete(
              project=project.project_id, zone=zone, disk=disk)
          response = request.execute()
          project.BlockOperation(response)
          break
        except HttpError as exception:
          # The gce api will throw a 400 until the analysis vm's deletion is
          # correctly propagated. When the disk is finally deleted, it will
          # throw a 404 not found if it looped one more time after deletion.
          if exception.resp.status == 404:
            break
          if exception.resp.status != 400:
            log.warning(
                'Could not delete the disk {0:s}: {1:s}'.format(
                    disk, str(exception)))
          # Throttle the requests to one every 10 seconds
          time.sleep(10)

      log.info('Disk {0:s} successfully deleted.'.format(disk))


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
    raise OSError(
        'Please make sure that you defined the '
        '"PROJECT_INFO" environment variable pointing '
        'to your project settings.')
  try:
    json_file = open(project_info)
    try:
      project_info = json.load(json_file)
    except ValueError as exception:
      raise RuntimeError(
          'Cannot parse JSON file. {0:s}'.format(str(exception)))
    json_file.close()
  except OSError as exception:
    raise OSError(
        'Could not open/close file {0:s}: {1:s}'.format(
            project_info, str(exception)))

  if not all(key in project_info for key in ['project_id', 'instance', 'zone']):
    raise ValueError(
        'Please make sure that your JSON file '
        'has the required entries. The file should '
        'contain at least the following: ["project_id", '
        '"instance", "zone"].')

  return project_info


if __name__ == '__main__':
  unittest.main()
