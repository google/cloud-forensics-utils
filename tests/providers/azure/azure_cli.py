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
"""Call libcloudforensics CLI tool for e2e testing."""
import subprocess
from typing import List, Optional

from libcloudforensics import logging_utils
from libcloudforensics.errors import ResourceCreationError
from libcloudforensics.errors import ResourceNotFoundError
from libcloudforensics.providers.azure.internal import account
from libcloudforensics.providers.azure.internal import compute

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)


class AzureCLI:
  """AzureCLI calls the libcloudforensics CLI tool for Azure operations."""

  def __init__(self, az: account.AZAccount) -> None:
    """Initialize the CLI class.

    Attributes:
      az (AZAccount): The Azure account to work with.
    """
    self.az = az

  def StartAnalysisVm(
      self,
      instance_name: str,
      attach_disks: Optional[List[str]] = None) -> compute.AZComputeVirtualMachine:  # pylint: disable=line-too-long
    """Start an analysis VM.

    Args:
      instance_name (str): The name of the instance to start.
      attach_disks (List[str]): Optional. List of volume names to attach to
          the VM.

    Returns:
      compute.AZComputeVirtualMachine: A compute.AZComputeVirtualMachine object
          that represents the started VM.

    Raises:
      ResourceCreationError: If the VM could not be created.
      ResourceNotFoundError: If the created VM could not be found.
    """
    cmd = 'cloudforensics az {0:s} startvm {1:s} --region {2:s}'.format(
        self.az.default_resource_group_name,
        instance_name,
        self.az.default_region)
    if attach_disks:
      cmd += ' --attach_disks={0:s}'.format(','.join(attach_disks))
    logger.info('CLI command: {0:s}'.format(cmd))
    try:
      output = subprocess.check_output(
          cmd.split(), stderr=subprocess.STDOUT, shell=False)
      logger.info(output)
      try:
        return self.az.compute.GetInstance(
            instance_name, self.az.default_resource_group_name)
      except ResourceNotFoundError as error:
        raise ResourceNotFoundError(
            'Failed finding created VM in resource group {0:s}'.format(
                self.az.default_resource_group_name), __name__) from error
    except subprocess.CalledProcessError as error:
      raise ResourceCreationError(
          'Failed creating VM in resource group {0:s}: {1!s}'.format(
              self.az.default_resource_group_name, error), __name__) from error

  def CreateDiskCopy(
      self,
      instance_name: Optional[str] = None,
      disk_name: Optional[str] = None,
      region: Optional[str] = None) -> compute.AZComputeDisk:
    """Create a disk copy.

    Args:
      instance_name (str): Optional. Instance name of the instance using the
          disk to be copied. If specified, the boot disk of the instance will be
          copied. If disk_name is also specified, then the disk pointed to by
          disk_name will be copied.
      disk_name (str): Optional. Name of the disk to copy. If not set,
          then instance_name needs to be set and the boot disk will be copied.
      region (str): Optional. The region in which to create the disk copy.
           Default is eastus.

    Returns:
      compute.AZComputeDisk: A compute.AZComputeDisk object that represents
          the disk copy.

    Raises:
      ResourceCreationError: If the volume could not be created.
      ResourceNotFoundError: If the created volume copy could not be found.
    """
    cmd = 'cloudforensics az {0:s} copydisk'.format(
        self.az.default_resource_group_name)
    if instance_name:
      cmd += ' --instance_name={0:s}'.format(instance_name)
    elif disk_name:
      cmd += ' --disk_name={0:s}'.format(disk_name)
    cmd += ' --region={0:s}'.format(region or self.az.default_region)
    cmd += ' --disk_type=Standard_LRS'
    logger.info('CLI command: {0:s}'.format(cmd))
    try:
      output = subprocess.check_output(
          cmd.split(), stderr=subprocess.STDOUT, shell=False)
      if not output:
        raise ResourceCreationError(
            'Could not find disk copy result', __name__)
      disk_copy_name = output.decode('utf-8').split(' ')[-1]
      disk_copy_name = disk_copy_name[:disk_copy_name.rindex('copy') + 4]
      logger.info(output)
      logger.info("Disk successfully copied to {0:s}".format(
          disk_copy_name))
      try:
        return self.az.compute.GetDisk(
            disk_copy_name, self.az.default_resource_group_name)
      except ResourceNotFoundError as error:
        raise ResourceNotFoundError(
            'Failed finding copied disk in resource group {0:s}'.format(
                self.az.default_resource_group_name), __name__) from error
    except subprocess.CalledProcessError as error:
      raise ResourceCreationError(
          'Failed copying disk: {0!s}'.format(error), __name__) from error
