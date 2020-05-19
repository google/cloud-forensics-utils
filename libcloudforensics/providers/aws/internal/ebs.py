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
"""Disk functionality."""

import datetime

import botocore

from libcloudforensics.providers.aws import internal as aws_internal
from libcloudforensics.providers.aws.internal.common import REGEX_TAG_VALUE, EC2_SERVICE  # pylint: disable=line-too-long


class AWSElasticBlockStore:
  """Class representing an AWS EBS resource.

  Attributes:
    aws_account (AWSAccount): The account for the resource.
    region (str): The region the EBS is in.
    availability_zone (str): The zone within the region in which the EBS is.
    encrypted (bool): True if the EBS resource is encrypted, False otherwise.
    name (str): The name tag of the EBS resource, if existing.
  """

  def __init__(self,
               aws_account,
               region,
               availability_zone,
               encrypted,
               name=None):
    """Initialize the AWS EBS resource.

    Args:
      aws_account (AWSAccount): The account for the resource.
      region (str): The region the EBS is in.
      availability_zone (str): The zone within the region in which the EBS is.
      encrypted (bool): True if the EBS resource is encrypted, False otherwise.
      name (str): Optional. The name tag of the EBS resource, if existing.
    """

    self.aws_account = aws_account
    self.region = region
    self.availability_zone = availability_zone
    self.encrypted = encrypted
    self.name = name


class AWSVolume(AWSElasticBlockStore):
  """Class representing an AWS EBS volume.

  Attributes:
    volume_id (str): The id of the volume.
    aws_account (AWSAccount): The account for the volume.
    region (str): The region the volume is in.
    availability_zone (str): The zone within the region in which the volume is.
    encrypted (bool): True if the volume is encrypted, False otherwise.
    name (str): The name tag of the volume, if existing.
    device_name (str): The device name (e.g. /dev/spf) of the
        volume when it is attached to an instance, if applicable.
  """

  def __init__(self,
               volume_id,
               aws_account,
               region,
               availability_zone,
               encrypted,
               name=None,
               device_name=None):
    """Initialize an AWS EBS volume.

    Args:
      volume_id (str): The id of the volume.
      aws_account (AWSAccount): The account for the volume.
      region (str): The region the volume is in.
      availability_zone (str): The zone within the region in which the volume
          is.
      encrypted (bool): True if the volume is encrypted, False otherwise.
      name (str): Optional. The name tag of the volume, if existing.
      device_name (str): Optional. The device name (e.g. /dev/spf) of the
          volume when it is attached to an instance, if applicable.
    """

    super(AWSVolume, self).__init__(aws_account,
                                    region,
                                    availability_zone,
                                    encrypted,
                                    name)
    self.volume_id = volume_id
    self.device_name = device_name

  def Snapshot(self, snapshot_name=None):
    """Create a snapshot of the volume.

    Args:
      snapshot_name (str): Optional. Name tag of the snapshot.

    Returns:
      AWSSnapshot: A snapshot object.

    Raises:
      ValueError: If the snapshot name does not comply with the RegEx.
      RuntimeError: If the snapshot could not be created.
    """

    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    if not snapshot_name:
      snapshot_name = self.volume_id
    truncate_at = 255 - len(timestamp) - 1
    snapshot_name = '{0}-{1}'.format(snapshot_name[:truncate_at], timestamp)
    if not REGEX_TAG_VALUE.match(snapshot_name):
      raise ValueError('Snapshot name {0:s} does not comply with '
                       '{1:s}'.format(snapshot_name, REGEX_TAG_VALUE.pattern))

    client = self.aws_account.ClientApi(EC2_SERVICE)
    try:
      snapshot = client.create_snapshot(
          VolumeId=self.volume_id,
          TagSpecifications=[aws_internal.GetTagForResourceType(
              'snapshot', snapshot_name)])

      snapshot_id = snapshot.get('SnapshotId')
      # Wait for snapshot completion
      client.get_waiter('snapshot_completed').wait(SnapshotIds=[snapshot_id])
    except (client.exceptions.ClientError,
            botocore.exceptions.WaiterError) as exception:
      raise RuntimeError('Could not create snapshot for volume {0:s}: '
                         '{1:s}'.format(self.volume_id, str(exception)))

    return AWSSnapshot(snapshot_id, self, name=snapshot_name)

  def Delete(self):
    """Delete a volume."""
    client = self.aws_account.ClientApi(EC2_SERVICE)
    try:
      client.delete_volume(VolumeId=self.volume_id)
    except client.exceptions.ClientError as exception:
      raise RuntimeError('Could not delete volume {0:s}: {1:s}'.format(
          self.volume_id, str(exception)))


class AWSSnapshot(AWSElasticBlockStore):
  """Class representing an AWS EBS snapshot.

  Attributes:
    snapshot_id (str): The id of the snapshot.
    volume (AWSVolume): The volume from which the snapshot was taken.
    name (str): The name tag of the snapshot, if existing.
  """

  def __init__(self, snapshot_id, volume, name=None):
    """Initialize an AWS EBS snapshot.

    Args:
      snapshot_id (str): The id of the snapshot.
      volume (AWSVolume): The volume from which the snapshot was taken.
      name (str): Optional. The name tag of the snapshot, if existing.
    """

    super(AWSSnapshot, self).__init__(volume.aws_account,
                                      volume.region,
                                      volume.availability_zone,
                                      volume.encrypted,
                                      name)
    self.snapshot_id = snapshot_id
    self.volume = volume

  def Delete(self):
    """Delete a snapshot."""

    client = self.aws_account.ClientApi(EC2_SERVICE)
    try:
      client.delete_snapshot(SnapshotId=self.snapshot_id)
    except client.exceptions.ClientError as exception:
      raise RuntimeError('Could not delete snapshot {0:s}: {1:s}'.format(
          self.snapshot_id, str(exception)))

  def ShareWithAWSAccount(self, aws_account_id):
    """Share the snapshot with another AWS account ID.

    Args:
      aws_account_id (str): The AWS Account ID to share the snapshot with.
    """

    snapshot = self.aws_account.ResourceApi(EC2_SERVICE).Snapshot(
        self.snapshot_id)
    snapshot.modify_attribute(
        Attribute='createVolumePermission',
        CreateVolumePermission={
            'Add': [{
                'UserId': aws_account_id
            }]
        },
        OperationType='add'
    )
