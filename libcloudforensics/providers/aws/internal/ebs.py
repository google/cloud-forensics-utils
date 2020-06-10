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

from datetime import datetime
from typing import TYPE_CHECKING, Dict, Optional, Union

import botocore

from libcloudforensics.providers.aws.internal import common

if TYPE_CHECKING:
  # TYPE_CHECKING is always False at runtime, therefore it is safe to ignore
  # the following cyclic import, as it it only used for type hints
  from libcloudforensics.providers.aws.internal import account  # pylint: disable=cyclic-import


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
               aws_account: 'account.AWSAccount',
               region: str,
               availability_zone: str,
               encrypted: bool,
               name: Optional[str] = None) -> None:
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
               volume_id: str,
               aws_account: 'account.AWSAccount',
               region: str,
               availability_zone: str,
               encrypted: bool,
               name: Optional[str] = None,
               device_name: Optional[str] = None) -> None:
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

  def Snapshot(self, snapshot_name: Optional[str] = None) -> 'AWSSnapshot':
    """Create a snapshot of the volume.

    Args:
      snapshot_name (str): Optional. Name tag of the snapshot.

    Returns:
      AWSSnapshot: A snapshot object.

    Raises:
      ValueError: If the snapshot name does not comply with the RegEx.
      RuntimeError: If the snapshot could not be created.
    """

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    if not snapshot_name:
      snapshot_name = self.volume_id
    truncate_at = 255 - len(timestamp) - 1
    snapshot_name = '{0}-{1}'.format(snapshot_name[:truncate_at], timestamp)
    if not common.REGEX_TAG_VALUE.match(snapshot_name):
      raise ValueError('Snapshot name {0:s} does not comply with '
                       '{1:s}'.format(snapshot_name,
                                      common.REGEX_TAG_VALUE.pattern))

    client = self.aws_account.ClientApi(common.EC2_SERVICE)
    try:
      snapshot = client.create_snapshot(
          VolumeId=self.volume_id,
          TagSpecifications=[common.GetTagForResourceType(
              'snapshot', snapshot_name)])

      snapshot_id = snapshot.get('SnapshotId')
      # Wait for snapshot completion
      client.get_waiter('snapshot_completed').wait(
          SnapshotIds=[snapshot_id],
          WaiterConfig={'Delay': 30, 'MaxAttempts': 100})
    except (client.exceptions.ClientError,
            botocore.exceptions.WaiterError) as exception:
      raise RuntimeError('Could not create snapshot for volume {0:s}: '
                         '{1:s}'.format(self.volume_id, str(exception)))

    return AWSSnapshot(snapshot_id,
                       self.aws_account,
                       self.aws_account.default_region,
                       self.aws_account.default_availability_zone,
                       self,
                       name=snapshot_name)

  def Delete(self) -> None:
    """Delete a volume."""
    client = self.aws_account.ClientApi(common.EC2_SERVICE)
    try:
      client.delete_volume(VolumeId=self.volume_id)
    except client.exceptions.ClientError as exception:
      raise RuntimeError('Could not delete volume {0:s}: {1:s}'.format(
          self.volume_id, str(exception)))


class AWSSnapshot(AWSElasticBlockStore):
  """Class representing an AWS EBS snapshot.

  Attributes:
    snapshot_id (str): The id of the snapshot.
    aws_account (AWSAccount): The account for the snapshot.
    region (str): The region the snapshot is in.
    availability_zone (str): The zone within the region in which the snapshot
        is.
    volume (AWSVolume): The volume from which the snapshot was taken.
    name (str): The name tag of the snapshot, if existing.
  """

  def __init__(self,
               snapshot_id: str,
               aws_account: 'account.AWSAccount',
               region: str,
               availability_zone: str,
               volume: AWSVolume,
               name: Optional[str] = None) -> None:
    """Initialize an AWS EBS snapshot.

    Args:
      snapshot_id (str): The id of the snapshot.
      aws_account (AWSAccount): The account for the snapshot.
      region (str): The region the snapshot is in.
      availability_zone (str): The zone within the region in which the snapshot
          is.
      volume (AWSVolume): The volume from which the snapshot was taken.
      name (str): Optional. The name tag of the snapshot, if existing.
    """

    super(AWSSnapshot, self).__init__(aws_account,
                                      region,
                                      availability_zone,
                                      volume.encrypted,
                                      name)
    self.snapshot_id = snapshot_id
    self.volume = volume

  def Copy(
      self,
      kms_key_id: Optional[str] = None,
      delete: bool = False,
      deletion_account: Optional['account.AWSAccount'] = None) -> 'AWSSnapshot':
    """Copy a snapshot.

    Args:
      kms_key_id (str): Optional. A KMS key id to encrypt the snapshot copy
          with. If set to None but the source snapshot is encrypted,
          then the copy will be encrypted too (with the key used by the
          source snapshot).
      delete (bool): Optional. If set to True, the snapshot being copied will
          be deleted prior to returning the copy. Default is False.
      deletion_account (AWSAccount): Optional. An AWSAccount object to use to
          delete the snapshot if 'delete' is set to True. Since accounts operate
          per region, this can be useful when copying snapshots across regions
          (which requires one AWSAccount object per region as per
          boto3.session.Session() requirements) and wanting to delete the source
          snapshot located in a different region than the copy being created.

    Returns:
      AWSSnapshot: A copy of the snapshot.

    Raises:
      RuntimeError: If the snapshot could not be copied.
    """

    client = self.aws_account.ClientApi(common.EC2_SERVICE)
    copy_args = {
        'SourceRegion': self.region,
        'SourceSnapshotId': self.snapshot_id
    }  # type: Dict[str, Union[str, bool]]
    if kms_key_id:
      copy_args['Encrypted'] = True
      copy_args['KmsKeyId'] = kms_key_id
    try:
      response = client.copy_snapshot(**copy_args)
    except client.exceptions.ClientError as exception:
      raise RuntimeError('Could not copy snapshot {0:s}: {1:s}'.format(
          self.snapshot_id, str(exception)))

    snapshot_copy = AWSSnapshot(
        # The response contains the new snapshot ID
        response['SnapshotId'],
        self.aws_account,
        self.aws_account.default_region,
        self.aws_account.default_availability_zone,
        self.volume,
        name='{0:s}-copy'.format(self.snapshot_id)
    )

    # Wait for the copy to be available
    client.get_waiter('snapshot_completed').wait(
        SnapshotIds=[snapshot_copy.snapshot_id],
        WaiterConfig={'Delay': 30, 'MaxAttempts': 100})

    if delete:
      if deletion_account:
        self.aws_account = deletion_account
      self.Delete()

    return snapshot_copy

  def Delete(self) -> None:
    """Delete a snapshot."""

    client = self.aws_account.ClientApi(common.EC2_SERVICE)
    try:
      client.delete_snapshot(SnapshotId=self.snapshot_id)
    except client.exceptions.ClientError as exception:
      raise RuntimeError('Could not delete snapshot {0:s}: {1:s}'.format(
          self.snapshot_id, str(exception)))

  def ShareWithAWSAccount(self, aws_account_id: str) -> None:
    """Share the snapshot with another AWS account ID.

    Args:
      aws_account_id (str): The AWS Account ID to share the snapshot with.
    """

    snapshot = self.aws_account.ResourceApi(common.EC2_SERVICE).Snapshot(
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
