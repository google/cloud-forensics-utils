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
"""Prepares calls to the CLI tool for Azure operations."""
from typing import List, Optional

from libcloudforensics import logging_utils
from libcloudforensics.providers.azure.internal import account

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)


class AzureCLIHelper:
  """AzureCLIHelper prepares calls the CLI tool for Azure operations."""

  def __init__(self, az: account.AZAccount) -> None:
    """Initialize the CLI class.

    Attributes:
      az (AZAccount): The Azure account to work with.
    """
    self.az = az

  def PrepareStartAnalysisVmCmd(
      self,
      instance_name: str,
      attach_disks: Optional[List[str]] = None) -> str:
    """Start an analysis VM.

    Args:
      instance_name (str): The name of the instance to start.
      attach_disks (List[str]): Optional. List of volume names to attach to
          the VM.

    Returns:
      str: The CLI command to run.
    """
    cmd = 'cloudforensics az {0:s} startvm {1:s} --region {2:s}'.format(
        self.az.default_resource_group_name,
        instance_name,
        self.az.default_region)
    if attach_disks:
      cmd += ' --attach_disks={0:s}'.format(','.join(attach_disks))
    logger.info('CLI command: {0:s}'.format(cmd))
    return cmd

  def PrepareCreateDiskCopyCmd(
      self,
      instance_name: Optional[str] = None,
      disk_name: Optional[str] = None,
      region: Optional[str] = None) -> str:
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
       str: The CLI command to run.
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
    return cmd
