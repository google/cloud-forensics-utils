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
"""End to end test for the gcp cli utility."""
import subprocess
import typing
import unittest
import time
import warnings

from googleapiclient.errors import HttpError

from libcloudforensics.errors import ResourceCreationError
from libcloudforensics.errors import ResourceNotFoundError
from libcloudforensics.providers.gcp.internal import common
from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics import logging_utils
from tests.scripts import utils
from tests.providers.gcp.gcp_cli import GCPCLIHelper

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
  """End to end test on GCP.

  This end-to-end test runs directly on GCP and tests that:
    1. The project.py module connects to the target instance and makes a
        snapshot of the boot disk (by default) or of the disk passed in
        parameter to the forensics.CreateDiskCopy() method.
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
  @typing.no_type_check
  @IgnoreWarnings
  def setUpClass(cls):
    try:
      project_info = utils.ReadProjectInfo(['project_id', 'instance', 'zone'])
    except (OSError, RuntimeError, ValueError) as exception:
      raise unittest.SkipTest(str(exception))
    cls.project_id = project_info['project_id']
    cls.instance_to_analyse = project_info['instance']
    # Optional: test a disk other than the boot disk
    cls.disk_to_forensic = project_info.get('disk', None)
    cls.zone = project_info['zone']
    cls.gcp = gcp_project.GoogleCloudProject(cls.project_id, cls.zone)
    cls.analysis_vm_name = 'new-vm-for-analysis'
    cls.cli = GCPCLIHelper(cls.gcp)
    cls.analysis_vm = cls._RunStartAnalysisVm(
        cls.analysis_vm_name, cls.zone)

  @typing.no_type_check
  @IgnoreWarnings
  def setUp(self):
    self.project_id = EndToEndTest.project_id
    self.instance_to_analyse = EndToEndTest.instance_to_analyse
    self.disk_to_forensic = EndToEndTest.disk_to_forensic
    self.zone = EndToEndTest.zone
    self.analysis_vm_name = EndToEndTest.analysis_vm.name
    self.boot_disk_copy = None
    self.disk_to_forensic_copy = None

  @typing.no_type_check
  @IgnoreWarnings
  def test_end_to_end_boot_disk(self):
    """End to end test on GCP.

    This end-to-end test runs directly on GCP and tests that:
      1. The project.py module connects to the target instance and makes a
            snapshot of the boot disk.
      2. A new disk is created from the taken snapshot.
      3. If an analysis VM already exists, the module will attach the disk
            copy to the VM. Otherwise, it will create a new GCP instance for
            analysis purpose and attach the boot disk copy to it.
    """

    # Make a copy of the boot disk of the instance to analyse
    self.boot_disk_copy = self._RunCreateDiskCopy(
        instance_name=self.instance_to_analyse,
        # disk_name=None by default, boot disk will be copied
    )

    gcp_client_api = common.GoogleCloudComputeClient(self.project_id).GceApi()

    # The disk copy should be attached to the analysis project
    gce_disk_client = gcp_client_api.disks()
    request = gce_disk_client.get(
        project=self.project_id, zone=self.zone, disk=self.boot_disk_copy.name)
    result = request.execute()
    self.assertEqual(result['name'], self.boot_disk_copy.name)

    # Get the analysis VM and attach the evidence boot disk
    self.analysis_vm = self._RunStartAnalysisVm(
        self.analysis_vm_name,
        self.zone,
        attach_disks=[self.boot_disk_copy.name])

    # The forensic instance should be live in the analysis GCP project and
    # the disk should be attached
    gce_instance_client = gcp_client_api.instances()
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

  @typing.no_type_check
  @IgnoreWarnings
  def test_end_to_end_other_disk(self):
    """End to end test on GCP.

    This end-to-end test runs directly on GCP and tests that:
      1. The project.py module connects to the target instance and makes a
          snapshot of disk passed to the 'disk_name' parameter in the
          forensics.CreateDiskCopy() method.
      2. A new disk is created from the taken snapshot.
      3. If an analysis VM already exists, the module will attach the disk
          copy to the VM. Otherwise, it will create a new GCP instance for
          analysis purpose and attach the boot disk copy to it.
    """

    # Make a copy of another disk of the instance to analyse
    self.disk_to_forensic_copy = self._RunCreateDiskCopy(
        disk_name=self.disk_to_forensic)

    gcp_client_api = common.GoogleCloudComputeClient(self.project_id).GceApi()

    # The disk copy should be existing in the analysis project
    gce_disk_client = gcp_client_api.disks()
    request = gce_disk_client.get(
        project=self.project_id, zone=self.zone,
        disk=self.disk_to_forensic_copy.name)
    result = request.execute()
    self.assertEqual(result['name'], self.disk_to_forensic_copy.name)

    # Get the analysis VM and attach the evidence disk to forensic
    self.analysis_vm = self._RunStartAnalysisVm(
        self.analysis_vm_name,
        self.zone,
        attach_disks=[self.disk_to_forensic_copy.name])

    # The forensic instance should be live in the analysis GCP project and
    # the disk should be attached
    gce_instance_client = gcp_client_api.instances()
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
  @typing.no_type_check
  def _RunStartAnalysisVm(cls, instance_name, zone, attach_disks=None):
    cmd = cls.cli.PrepareStartAnalysisVmCmd(
        instance_name, zone, attach_disks=attach_disks)
    try:
      output = subprocess.check_output(
          cmd.split(), stderr=subprocess.STDOUT, shell=False)
    except subprocess.CalledProcessError as error:
      raise ResourceCreationError(
          'Failed creating VM in project {0:s}'.format(
              cls.gcp.project_id), __name__) from error
    logger.info(output)
    try:
      return cls.gcp.compute.GetInstance(instance_name)
    except ResourceNotFoundError as error:
      raise ResourceNotFoundError(
          'Failed finding created VM in project {0:s}'.format(
              cls.gcp.project_id), __name__) from error

  @classmethod
  @typing.no_type_check
  def _RunCreateDiskCopy(cls, instance_name=None, disk_name=None):
    cmd = cls.cli.PrepareCreateDiskCopyCmd(
        instance_name=instance_name, disk_name=disk_name)
    try:
      output = subprocess.check_output(
          cmd.split(), stderr=subprocess.STDOUT, shell=False)
    except subprocess.CalledProcessError as error:
      raise ResourceCreationError('Failed copying disk', __name__) from error

    if not output:
      raise ResourceCreationError('Could not find disk copy result', __name__)
    disk_copy_name = output.decode('utf-8').split(' ')[-1]
    disk_copy_name = disk_copy_name[:disk_copy_name.find('copy') + 4]
    logger.info(output)
    logger.info("Disk successfully copied to {0:s}".format(disk_copy_name))

    try:
      return cls.gcp.compute.GetDisk(disk_copy_name)
    except ResourceNotFoundError as error:
      raise ResourceNotFoundError(
          'Failed finding copied disk in project {0:s}'.format(
              cls.gcp.project_id), __name__) from error

  @classmethod
  @typing.no_type_check
  @IgnoreWarnings
  def tearDownClass(cls):
    analysis_vm = cls.analysis_vm
    zone = cls.zone
    project = cls.gcp
    disks = analysis_vm.ListDisks()
    gcp_client = common.GoogleCloudComputeClient(project.project_id)
    # delete the created forensics VMs
    logger.info('Deleting analysis instance: {0:s}.'.format(
        analysis_vm.name))
    gce_instance_client = gcp_client.GceApi().instances()
    request = gce_instance_client.delete(
        project=project.project_id, zone=zone, instance=analysis_vm.name)
    response = request.execute()
    try:
      gcp_client.BlockOperation(response)
    except HttpError:
      # BlockOperation triggers a while(True) loop that checks on the
      # operation ID. Sometimes it loops one more time right when the
      # operation has finished and thus the associated ID doesn't exists
      # anymore, throwing an HttpError. We can ignore this.
      pass
    logger.info('Instance {0:s} successfully deleted.'.format(
        analysis_vm.name))

    # delete the copied disks
    # we ignore the disk that was created for the analysis VM (disks[0]) as
    # it is deleted in the previous operation
    for disk in list(disks.keys())[1:]:
      logger.info('Deleting disk: {0:s}.'.format(disk))
      while True:
        try:
          gce_disk_client = gcp_client.GceApi().disks()
          request = gce_disk_client.delete(
              project=project.project_id, zone=zone, disk=disk)
          response = request.execute()
          gcp_client.BlockOperation(response)
          break
        except HttpError as exception:
          # The gce api will throw a 400 until the analysis vm's deletion is
          # correctly propagated. When the disk is finally deleted, it will
          # throw a 404 not found if it looped one more time after deletion.
          if exception.resp.status == 404:
            break
          if exception.resp.status != 400:
            logger.warning(
                'Could not delete the disk {0:s}: {1:s}'.format(
                    disk, str(exception)))
          # Throttle the requests to one every 10 seconds
          time.sleep(10)

      logger.info('Disk {0:s} successfully deleted.'.format(disk))


if __name__ == '__main__':
  unittest.main()
