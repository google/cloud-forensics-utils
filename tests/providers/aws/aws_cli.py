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
"""Prepares calls to the CLI tool for AWS operations."""
from typing import List, Optional

from libcloudforensics import logging_utils

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)


class AWSCLIHelper:
  """AWSCLIHelper prepares calls to the CLI tool for AWS operations."""

  @staticmethod
  def PrepareStartAnalysisVmCmd(
      vm_name: str,
      zone: str,
      attach_volumes: Optional[List[str]] = None) -> str:
    """Wrapper around the CLI tool to start an analysis VM.

    Args:
      vm_name (str): The name of the instance to start.
      zone (str): The zone in which to start the instance.
      attach_volumes (List[str]): Optional. List of volume names to attach to
          the VM.

    Returns:
      str: The CLI command to run.
    """
    cmd = 'cloudforensics aws {0:s} startvm {1:s}'.format(  # pylint: disable=line-too-long
        zone, vm_name)
    if attach_volumes:
      cmd += ' --attach_volumes={0:s}'.format(','.join(attach_volumes))
    logger.info('CLI command: {0:s}'.format(cmd))
    return cmd

  @staticmethod
  def PrepareCreateVolumeCopyCmd(
      zone: str,
      dst_zone: Optional[str] = None,
      instance_id: Optional[str] = None,
      volume_id: Optional[str] = None) -> str:
    """Wrapper around the CLI tool to create a volume copy.

    Args:
      zone (str): The AWS zone in which the volume is located, e.g.
          'us-east-2b'.
      dst_zone (str): Optional. The AWS zone in which to create the volume
        copy. By default, this is the same as 'zone'.
      instance_id (str): Optional. Instance ID of the instance using the volume
          to be copied. If specified, the boot volume of the instance will be
          copied. If volume_id is also specified, then the volume pointed by
          that volume_id will be copied.
      volume_id (str): Optional. ID of the volume to copy. If not set,
          then instance_id needs to be set and the boot volume will be copied.

    Returns:
      str: The CLI command to run.
    """
    cmd = 'cloudforensics aws {0:s} copydisk'.format(zone)
    if instance_id:
      cmd += ' --instance_id={0:s}'.format(instance_id)
    elif volume_id:
      cmd += ' --volume_id={0:s}'.format(volume_id)
    if dst_zone:
      cmd += ' --dst_zone={0:s}'.format(dst_zone)
    logger.info('CLI command: {0:s}'.format(cmd))
    return cmd

  @staticmethod
  def PrepareListImagesCmd(
      zone: str,
      qfilter: Optional[str] = None) -> str:
    """Wrapper around the CLI tool to list AMI images.

    Args:
      zone (str): The AWS zone in which to list the images, e.g. 'us-east-2b'.
      qfilter (str): The filter to apply.
      See https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_images  # pylint: disable=line-too-long

    Returns:
      str: The CLI command to run.
    """
    cmd = 'cloudforensics aws {0:s} listimages'.format(zone)
    if qfilter:
      cmd += ' --filter={0:s}'.format(qfilter)
    logger.info('CLI command: {0:s}'.format(cmd))
    return cmd
