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
"""Instance functionality."""
from typing import TYPE_CHECKING, Dict, Optional

from libcloudforensics.providers.aws.internal.common import EC2_SERVICE

if TYPE_CHECKING:
  # TYPE_CHECKING is always False at runtime, therefore it is safe to ignore
  # the following cyclic import, as it it only used for type hints
  from libcloudforensics.providers.aws.internal import account, ebs  # pylint: disable=cyclic-import


class AWSInstance:
  """Class representing an AWS EC2 instance.

  Attributes:
    aws_account (AWSAccount): The account for the instance.
    instance_id (str): The id of the instance.
    region (str): The region the instance is in.
    availability_zone (str): The zone within the region in which the instance
        is.
    name (str): The name tag of the instance, if existing.
  """

  def __init__(self,
               aws_account: 'account.AWSAccount',
               instance_id: str,
               region: str,
               availability_zone: str,
               name: Optional[str] = None) -> None:
    """Initialize the AWS EC2 instance.

    Args:
      aws_account (AWSAccount): The account for the instance.
      instance_id (str): The id of the instance.
      region (str): The region the instance is in.
      availability_zone (str): The zone within the region in which the instance
          is.
      name (str): Optional. The name tag of the instance, if existing.
    """

    self.aws_account = aws_account
    self.instance_id = instance_id
    self.region = region
    self.availability_zone = availability_zone
    self.name = name

  def GetBootVolume(self) -> 'ebs.AWSVolume':
    """Get the instance's boot volume.

    Returns:
      AWSVolume: Volume object if the volume is found.

    Raises:
      RuntimeError: If no boot volume could be found.
    """

    boot_device = self.aws_account.ResourceApi(
        EC2_SERVICE).Instance(self.instance_id).root_device_name
    volumes = self.ListVolumes()

    for volume_id in volumes:
      if volumes[volume_id].device_name == boot_device:
        return volumes[volume_id]

    error_msg = 'Boot volume not found for instance: {0:s}'.format(
        self.instance_id)
    raise RuntimeError(error_msg)

  def GetVolume(self, volume_id: str) -> 'ebs.AWSVolume':
    """Get a volume attached to the instance by ID.

    Args:
      volume_id (str): The ID of the volume to get.

    Returns:
      AWSVolume: The AWSVolume object.

    Raises:
      RuntimeError: If volume_id is not found amongst the volumes attached
          to the instance.
    """

    volume = self.ListVolumes().get(volume_id)
    if not volume:
      raise RuntimeError(
          'Volume {0:s} is not attached to instance {1:s}'.format(
              volume_id, self.instance_id))
    return volume

  def ListVolumes(self) -> Dict[str, 'ebs.AWSVolume']:
    """List all volumes for the instance.

    Returns:
      Dict[str, AWSVolume]: Dictionary mapping volume IDs to their respective
          AWSVolume object.
    """

    return self.aws_account.ListVolumes(
        filters=[{
            'Name': 'attachment.instance-id',
            'Values': [self.instance_id]}])

  def AttachVolume(self,
                   volume: 'ebs.AWSVolume',
                   device_name: str) -> None:
    """Attach a volume to the AWS instance.

    Args:
      volume (AWSVolume): The AWSVolume object to attach to the instance.
      device_name (str): The device name for the volume (e.g. /dev/sdf).

    Raises:
      RuntimeError: If the volume could not be attached.
    """

    client = self.aws_account.ClientApi(EC2_SERVICE)
    try:
      client.attach_volume(Device=device_name,
                           InstanceId=self.instance_id,
                           VolumeId=volume.volume_id)
    except client.exceptions.ClientError as exception:
      raise RuntimeError('Could not attach volume {0:s}: {1:s}'.format(
          volume.volume_id, str(exception)))

    volume.device_name = device_name
