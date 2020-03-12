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

from googleapiclient.errors import HttpError

from libcloudforensics import gcp

import unittest
import logging
import json
import time

log = logging.getLogger()


class EndToEndTest(unittest.TestCase):
  """End to end test on GCP.
  Test that gcp.py is able to correctly make a copy of the boot disk and of another given disk
  attached to a given instance. The copies are then attached to another instance to run
  forensics on the disk copies.
  Add your project information to a project.info file:
  {
    "project_id": "xxx",
    "instance": "xxx",
    "disk": "xxx", # optional
    "zone": "xxx"
  }
  """

  def setUp(self):
    super(EndToEndTest, self).setUp()
    self.boot_disk_copy = None
    self.disk_to_forensic_copy = None
    self.analysis_vm = None
    self.analysis_vm_name = 'new-vm-for-analysis'
    try:
      with open('project.info') as json_file:
        data = json.load(json_file)
        self.project_id = data['project_id']
        self.instance_to_analyse = data['instance']
        # Optional: test a disk other than the boot disk
        if 'disk' in data:
          self.disk_to_forensic = data['disk']
        else:
          self.disk_to_forensic = None
        self.zone = data['zone']
    except IOError as exception:
      raise unittest.SkipTest('Could not set up end to end test: {0:s}'.format(str(exception)))

  def test_end_to_end(self):
    """End to end test on GCP.
    Test that gcp.py is able to correctly make a copy of the boot disk and of another given disk
    attached to a given instance. The copies are then attached to another instance to run
    forensics on the disk copies.
    """

    # Make a copy of the boot disk of the instance to analyse
    log.info('Boot disk copy started for instance: {0:s}.'
             .format(self.instance_to_analyse))
    self.boot_disk_copy = gcp.create_disk_copy(
      src_proj=self.project_id,
      dst_proj=self.project_id,
      instance_name=self.instance_to_analyse,
      zone=self.zone
    )
    log.info('Boot disk successfully copied: {0:s}.'
             .format(self.boot_disk_copy.name))
    self.assertIsInstance(self.boot_disk_copy, gcp.GoogleComputeDisk)
    self.assertTrue(self.boot_disk_copy.name.startswith('evidence-'))
    self.assertTrue(self.boot_disk_copy.name.endswith('-copy'))

    # Create and start the analysis VM and attach the boot disk
    log.info('Starting a new instance: {0:s} for forensics analysis.'
             .format(self.analysis_vm_name))
    self.analysis_vm, created = gcp.start_analysis_vm(
      project=self.project_id,
      vm_name=self.analysis_vm_name,
      zone=self.zone,
      boot_disk_size=10,
      cpu_cores=4,
      attach_disk=self.boot_disk_copy
    )
    log.info('Instance {0:s} started.'
             .format(self.analysis_vm_name))
    self.assertIsInstance(self.analysis_vm, gcp.GoogleComputeInstance)
    self.assertTrue(created)
    self.assertEqual(self.analysis_vm.name, 'new-vm-for-analysis')

    if self.disk_to_forensic is not None:
      # Make a copy of another disk of the instance to analyse
      log.info('{0:s} disk copy started for instance: {1:s}.'
               .format(self.disk_to_forensic, self.instance_to_analyse))
      self.disk_to_forensic_copy = gcp.create_disk_copy(
        src_proj=self.project_id,
        dst_proj=self.project_id,
        instance_name=self.instance_to_analyse,
        zone=self.zone,
        disk_name=self.disk_to_forensic
      )
      log.info('{0:s} disk successfully copied: {1:s}.'.
               format(self.disk_to_forensic, self.disk_to_forensic_copy.name))
      self.assertIsInstance(self.disk_to_forensic_copy, gcp.GoogleComputeDisk)
      self.assertTrue(self.disk_to_forensic_copy.name.startswith('evidence-'))
      self.assertTrue(self.disk_to_forensic_copy.name.endswith('-copy'))

      # Use existing forensics VM and attach the other disk
      log.info('Attaching disk {0:s} to existing instance {1:s}.'
               .format(self.disk_to_forensic_copy.name, self.analysis_vm_name))
      self.analysis_vm, created = gcp.start_analysis_vm(
        project=self.project_id,
        vm_name=self.analysis_vm_name,
        zone=self.zone,
        boot_disk_size=10,
        cpu_cores=4,
        attach_disk=self.disk_to_forensic_copy
      )
      self.assertIsInstance(self.analysis_vm, gcp.GoogleComputeInstance)
      self.assertFalse(created)
      self.assertEqual(self.analysis_vm.name, 'new-vm-for-analysis')

    disks = self.analysis_vm.list_disks()
    log.warning(disks)
    if self.disk_to_forensic is not None:
      self.assertEqual(disks,
                       ['new-vm-for-analysis',
                        self.boot_disk_copy.name,
                        self.disk_to_forensic_copy.name])
    else:
      self.assertEqual(disks,
                       ['new-vm-for-analysis',
                        self.boot_disk_copy.name])

    # Cleanup after testing
    self.__clean()

  def __clean(self):
    project = gcp.GoogleCloudProject(project_id=self.project_id, default_zone=self.zone)

    # delete the created forensics VMs
    log.info('Deleting analysis instance: {0:s}.'
             .format(self.analysis_vm.name))
    operation = project.gce_api().instances().delete(
      project=project.project_id,
      zone=self.zone,
      instance=self.analysis_vm.name
    ).execute()
    try:
      project.gce_operation(operation, block=True)
    except HttpError:
      pass
    log.info('Instance {0:s} successfully deleted.'
             .format(self.analysis_vm.name))

    # We wait 5min before trying to delete the disk so that GCE propagates the previous operation,
    # as the instance first needs to be stopped, and then deleted.
    time.sleep(300)

    # delete the copied disks
    log.info('Deleting disk: {0:s}.'
             .format(self.boot_disk_copy.name))
    operation = project.gce_api().disks().delete(
      project=project.project_id,
      zone=self.zone,
      disk=self.boot_disk_copy.name
    ).execute()
    try:
      project.gce_operation(operation, block=True)
    except HttpError:
      pass
    log.info('Disk {0:s} successfully deleted.'
             .format(self.boot_disk_copy.name))

    if self.disk_to_forensic is not None:
      log.info('Deleting disk: {0:s}.'
               .format(self.disk_to_forensic_copy.name))
      time.sleep(120)
      operation = project.gce_api().disks().delete(
        project=project.project_id,
        zone=self.zone,
        disk=self.disk_to_forensic_copy.name
      ).execute()
      try:
        project.gce_operation(operation, block=True)
      except HttpError:
        pass
      log.info('Disk {0:s} successfully deleted.'
               .format(self.disk_to_forensic_copy.name))


if __name__ == '__main__':
  unittest.main()
