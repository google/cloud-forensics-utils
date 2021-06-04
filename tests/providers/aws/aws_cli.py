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
from libcloudforensics.providers.aws.internal import ebs
from libcloudforensics.providers.aws.internal import ec2
from libcloudforensics.providers.aws.internal.account import AWSAccount

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)


class AWSCLI:
  """AWSCLI calls the libcloudforensics CLI tool for AWS operations."""
  def __init__(self, aws: AWSAccount) -> None:
    """Initialize the CLI class.

    Attributes:
      aws (AWSAccount): The AWS account to work with.
    """
    self.aws = aws

  def StartAnalysisVm(
      self,
      vm_name: str,
      zone: str,
      attach_volumes: Optional[List[str]] = None) -> ec2.AWSInstance:
    """Start an analysis VM.

    Args:
      vm_name (str): The name of the instance to start.
      zone (str): The zone in which to start the instance.
      attach_volumes (List[str]): Optional. List of volume names to attach to
          the VM.

    Returns:
      ec2.AWSInstance: A ec2.AWSInstance object that represents the
          started VM.

    Raises:
      ResourceCreationError: If the VM could not be created.
      ResourceNotFoundError: If the created VM could not be found.
    """
    cmd = 'cloudforensics aws {0:s} startvm {1:s}'.format(  # pylint: disable=line-too-long
        zone, vm_name)
    if attach_volumes:
      cmd += ' --attach_volumes={0:s}'.format(','.join(attach_volumes))
    logger.info('CLI command: {0:s}'.format(cmd))
    try:
      output = subprocess.check_output(
          cmd.split(), stderr=subprocess.STDOUT, shell=False)
      logger.info(output)
      try:
        return self.aws.ec2.GetInstancesByName(vm_name)[0]
      except ResourceNotFoundError as error:
        raise ResourceNotFoundError(
            'Failed finding created VM in account profile {0:s}'.format(
                self.aws.aws_profile), __name__) from error
    except subprocess.CalledProcessError as error:
      raise ResourceCreationError(
          'Failed creating VM in account profile {0:s}'.format(
              self.aws.aws_profile), __name__) from error

  def CreateVolumeCopy(
      self,
      zone: str,
      dst_zone: Optional[str] = None,
      instance_id: Optional[str] = None,
      volume_id: Optional[str] = None) -> ebs.AWSVolume:
    """Create a volume copy.
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
      ebs.AWSVolume: A ebs.AWSVolume object that represents the volume
          copy.

    Raises:
      ResourceCreationError: If the volume could not be created.
      ResourceNotFoundError: If the created volume copy could not be found.
    """
    cmd = 'cloudforensics aws {0:s} copydisk'.format(zone)
    if instance_id:
      cmd += ' --instance_id={0:s}'.format(instance_id)
    elif volume_id:
      cmd += ' --volume_id={0:s}'.format(volume_id)
    if dst_zone:
      cmd += ' --dst_zone={0:s}'.format(dst_zone)
    logger.info('CLI command: {0:s}'.format(cmd))
    try:
      output = subprocess.check_output(
          cmd.split(), stderr=subprocess.STDOUT, shell=False)
      if not output:
        raise ResourceCreationError(
            'Could not find volume copy result', __name__)
      volume_copy_name = output.decode('utf-8').split(' ')[-1]
      volume_copy_name = volume_copy_name[:volume_copy_name.rindex('copy') + 4]
      logger.info(output)
      logger.info("Volume successfully copied to {0:s}".format(
          volume_copy_name))
      try:
        return self.aws.ebs.GetVolumesByName(volume_copy_name)[0]
      except ResourceNotFoundError as error:
        raise ResourceNotFoundError(
            'Failed finding copied volume in project {0:s}'.format(
                self.aws.aws_profile), __name__) from error
    except subprocess.CalledProcessError as error:
      raise ResourceCreationError('Failed copying volume', __name__) from error

  @staticmethod
  def ListImages(
      zone: str,
      qfilter: Optional[str] = None) -> List[str]:
    """List AMI images.

    Args:
      zone (str): The AWS zone in which to list the images, e.g. 'us-east-2b'.
      qfilter (str): The filter to apply.
      See https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_images  # pylint: disable=line-too-long

    Returns:
      List[str]: The AWS AMI images found.

    Raises:
      RuntimeError: If the images could not be listed.
    """
    cmd = 'cloudforensics aws {0:s} listimages'.format(zone)
    if qfilter:
      cmd += ' --filter={0:s}'.format(qfilter)
    logger.info('CLI command: {0:s}'.format(cmd))
    try:
      output = subprocess.check_output(
          cmd.split(), stderr=subprocess.STDOUT, shell=False)
      if not output:
        raise RuntimeError('Could not find any images to list')
      logger.info(output)
      # For this function, the CLI tool only prints one line per result, or
      # nothing at all. Therefore if there's an output, there's a result.
      return str(output).split('\n')
    except subprocess.CalledProcessError as error:
      raise RuntimeError('Failed retrieving AMI images') from error
