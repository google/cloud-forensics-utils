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
"""Call bash functions for e2e testing of the CLI tools"""
import subprocess
from typing import List
from typing import Optional

from libcloudforensics import logging_utils
from libcloudforensics.errors import ResourceCreationError
from libcloudforensics.errors import ResourceNotFoundError
from libcloudforensics.providers.gcp.internal.compute import GoogleComputeDisk
from libcloudforensics.providers.gcp.internal.compute import GoogleComputeInstance  # pylint: disable=line-too-long
from libcloudforensics.providers.gcp.internal.project import GoogleCloudProject

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)


class BashGCP:
  """BashGCP calls the libcloudforensics CLI tool for GCP operations."""
  def __init__(self, gcp: GoogleCloudProject) -> None:
    """Initialize the bash class.

    Attributes:
      gcp (GoogleCloudProject): The GCP project to work with.
    """
    self.gcp = gcp

  def StartAnalysisVm(
      self,
      instance_name: str,
      zone: str,
      attach_disks: Optional[List[str]] = None) -> GoogleComputeInstance:
    """Start an analysis VM.

    Args:
      instance_name (str): The name of the instance to start.
      zone (str): The zone in which to start the instance.
      attach_disks (List[str]): Optional. List of disk names to attach.

    Returns:
      GoogleComputeInstance: A GoogleComputeInstance object that represents the
          started VM.

    Raises:
      ResourceCreationError: If the VM could not be created.
      ResourceNotFoundError: If the created VM could not be found.
    """
    cmd = 'cloudforensics gcp {0:s} startvm {1:s} {2:s}'.format(
        self.gcp.project_id, instance_name, zone)
    if attach_disks:
      cmd += ' --attach_disks={0:s}'.format(','.join(attach_disks))
    logger.info('CLI command: {0:s}'.format(cmd))
    try:
      output = subprocess.check_output(
          cmd.split(), stderr=subprocess.STDOUT, shell=False)
      logger.info(output)
      try:
        return self.gcp.compute.GetInstance(instance_name)
      except ResourceNotFoundError as error:
        raise ResourceNotFoundError(
            'Failed finding created VM in project {0:s}'.format(
                self.gcp.project_id), __name__) from error
    except subprocess.CalledProcessError as error:
      raise ResourceCreationError(
          'Failed creating VM in project {0:s}'.format(
              self.gcp.project_id), __name__) from error

  def CreateDiskCopy(
      self,
      instance_name: Optional[str] = None,
      disk_name: Optional[str] = None) -> GoogleComputeDisk:
    """Create a disk copy.

    Args:
      instance_name (str): Name of the instance to copy disk from.
      disk_name (str): Name of the disk to copy.

    Returns:
      GoogleComputeDisk: A GoogleComputeDisk object that represents the disk
          copy.

    Raises:
      ResourceCreationError: If the disk could not be created.
      ResourceNotFoundError: If the created disk copy could not be found.
    """
    cmd = 'cloudforensics gcp {0:s} copydisk {0:s} {1:s}'.format(
        self.gcp.project_id, self.gcp.default_zone)
    if instance_name:
      cmd += ' --instance_name={0:s}'.format(instance_name)
    elif disk_name:
      cmd += ' --disk_name={0:s}'.format(disk_name)
    logger.info('CLI command: {0:s}'.format(cmd))
    try:
      output = subprocess.check_output(
          cmd.split(), stderr=subprocess.STDOUT, shell=False)
      if not output:
        raise ResourceCreationError('Could not find disk copy result', __name__)
      disk_copy_name = output.decode('utf-8').split(' ')[-1]
      disk_copy_name = disk_copy_name[:disk_copy_name.find('copy') + 4]
      logger.info(output)
      logger.info("Disk successfully copied to {0:s}".format(disk_copy_name))
      try:
        return self.gcp.compute.GetDisk(disk_copy_name)
      except ResourceNotFoundError as error:
        raise ResourceNotFoundError(
            'Failed finding copied disk in project {0:s}'.format(
                self.gcp.project_id), __name__) from error
    except subprocess.CalledProcessError as error:
      raise ResourceCreationError('Failed copying disk', __name__) from error
