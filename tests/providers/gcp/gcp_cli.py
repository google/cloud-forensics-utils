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
"""Prepares calls to the CLI tool for GCP operations."""
from typing import List
from typing import Optional

from libcloudforensics import logging_utils
from libcloudforensics.providers.gcp.internal.project import GoogleCloudProject

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)


class GCPCLIHelper:
  """GCPCLIHelper prepares calls to the CLI tool for GCP operations."""
  def __init__(self, gcp: GoogleCloudProject) -> None:
    """Initialize the CLI class.

    Attributes:
      gcp (GoogleCloudProject): The GCP project to work with.
    """
    self.gcp = gcp

  def PrepareStartAnalysisVmCmd(
      self,
      instance_name: str,
      zone: str,
      attach_disks: Optional[List[str]] = None) -> str:
    """Wrapper around the CLI tool to start an analysis VM.

    Args:
      instance_name (str): The name of the instance to start.
      zone (str): The zone in which to start the instance.
      attach_disks (List[str]): Optional. List of disk names to attach.

    Returns:
      str: The CLI command to run.
    """
    cmd = 'cloudforensics gcp --project={0:s} startvm {1:s} {2:s}'.format(
        self.gcp.project_id, instance_name, zone)
    if attach_disks:
      cmd += ' --attach_disks={0:s}'.format(','.join(attach_disks))
    logger.info('CLI command: {0:s}'.format(cmd))
    return cmd

  def PrepareCreateDiskCopyCmd(
      self,
      instance_name: Optional[str] = None,
      disk_name: Optional[str] = None) -> str:
    """Create a disk copy.

    Args:
      instance_name (str): Name of the instance to copy disk from.
      disk_name (str): Name of the disk to copy.

    Returns:
      str: The CLI command to run.
    """
    cmd = 'cloudforensics gcp --project={0:s} copydisk {0:s} {1:s}'.format(
        self.gcp.project_id, self.gcp.default_zone)
    if instance_name:
      cmd += ' --instance_name={0:s}'.format(instance_name)
    elif disk_name:
      cmd += ' --disk_name={0:s}'.format(disk_name)
    logger.info('CLI command: {0:s}'.format(cmd))
    return cmd
