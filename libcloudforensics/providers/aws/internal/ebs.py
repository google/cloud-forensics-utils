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

import binascii
from typing import TYPE_CHECKING, Dict, Optional, Union, List, Any

import botocore

from libcloudforensics import errors
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

    super().__init__(aws_account,
                     region,
                     availability_zone,
                     encrypted,
                     name)
    self.volume_id = volume_id
    self.device_name = device_name

  def Snapshot(self, tags: Optional[Dict[str, str]] = None) -> 'AWSSnapshot':
    """Create a snapshot of the volume.

    Args:
      tags (Dict[str, str]): Optional. A dictionary of tags to add to the
          snapshot, for example {'Name': 'my-snapshot-name', 'TicketID': 'xxx'}.

    Returns:
      AWSSnapshot: A snapshot object.

    Raises:
      InvalidNameError: If the snapshot name does not comply with the RegEx.
      ResourceCreationError: If the snapshot could not be created.
    """

    if not tags:
      tags = {}

    snapshot_name = tags.get('Name') or (self.volume_id + '-snapshot')
    truncate_at = 255 - 1
    snapshot_name = snapshot_name[:truncate_at]
    if len(snapshot_name) > 255:
      raise errors.InvalidNameError(
          'Snapshot name {0:s} is too long (>255 chars)'.format(snapshot_name),
          __name__)
    tags['Name'] = snapshot_name

    client = self.aws_account.ClientApi(common.EC2_SERVICE)
    try:
      snapshot = client.create_snapshot(
          VolumeId=self.volume_id,
          TagSpecifications=[common.CreateTags(common.SNAPSHOT, tags)])

      snapshot_id = snapshot.get('SnapshotId')
      # Wait for snapshot completion
      client.get_waiter('snapshot_completed').wait(
          SnapshotIds=[snapshot_id],
          WaiterConfig={'Delay': 30, 'MaxAttempts': 100})
    except (client.exceptions.ClientError,
            botocore.exceptions.WaiterError) as exception:
      raise errors.ResourceCreationError(
          'Could not create snapshot for volume {0:s}: {1:s}'.format(
              self.volume_id, str(exception)), __name__) from exception

    return AWSSnapshot(snapshot_id,
                       self.aws_account,
                       self.aws_account.default_region,
                       self.aws_account.default_availability_zone,
                       self,
                       name=snapshot_name)

  def Delete(self) -> None:
    """Delete a volume.

    Raises:
      ResourceDeletionError: If the volume could not be deleted.
    """
    client = self.aws_account.ClientApi(common.EC2_SERVICE)
    try:
      client.delete_volume(VolumeId=self.volume_id)
    except client.exceptions.ClientError as exception:
      raise errors.ResourceDeletionError(
          'Could not delete volume {0:s}: {1:s}'.format(
              self.volume_id, str(exception)), __name__) from exception

  def GetVolumeType(self) -> str:
    """Return the volume type.

    Returns:
      str: The volume type.
    """
    client = self.aws_account.ResourceApi(common.EC2_SERVICE)
    volume_type = client.Volume(self.volume_id).volume_type  # type: str
    return volume_type


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

    super().__init__(aws_account,
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
      ResourceCreationError: If the snapshot could not be copied.
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
      raise errors.ResourceCreationError(
          'Could not copy snapshot {0:s}: {1:s}'.format(
              self.snapshot_id, str(exception)), __name__) from exception

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
    """Delete a snapshot.

    Raises:
      ResourceDeletionError: If the snapshot could not be deleted.
    """

    client = self.aws_account.ClientApi(common.EC2_SERVICE)
    try:
      client.delete_snapshot(SnapshotId=self.snapshot_id)
    except client.exceptions.ClientError as exception:
      raise errors.ResourceDeletionError(
          'Could not delete snapshot {0:s}: {1:s}'.format(
              self.snapshot_id, str(exception)), __name__) from exception

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


class EBS:
  """Class that represents AWS EBS storage services."""

  def __init__(self,
               aws_account: 'account.AWSAccount') -> None:
    """Initialize the AWS EBS client object.

    Args:
      aws_account (AWSAccount): An AWS account object.
    """
    self.aws_account = aws_account

  def ListVolumes(
      self,
      region: Optional[str] = None,
      filters: Optional[List[Dict[str, Any]]] = None) -> Dict[str, AWSVolume]:
    """List volumes of an AWS account.

    Example usage:
      # List volumes attached to the instance 'some-instance-id'
      ListVolumes(filters=[
          {'Name':'attachment.instance-id', 'Values':['some-instance-id']}])

    Args:
      region (str): Optional. The region from which to list the volumes.
          If none provided, the default_region associated to the AWSAccount
          object will be used.
      filters (List[Dict]): Optional. Filters for the query. Filters are
          given as a list of dictionaries, e.g.: {'Name': 'someFilter',
          'Values': ['value1', 'value2']}.

    Returns:
      Dict[str, AWSVolume]: Dictionary mapping volume IDs (str) to their
          respective AWSVolume object.

    Raises:
      RuntimeError: If volumes can't be listed.
    """

    if not filters:
      filters = []

    volumes = {}
    client = self.aws_account.ClientApi(common.EC2_SERVICE, region=region)
    responses = common.ExecuteRequest(
        client, 'describe_volumes', {'Filters': filters})
    for response in responses:
      for volume in response['Volumes']:
        volume_id = volume['VolumeId']
        aws_volume = AWSVolume(volume_id,
                               self.aws_account,
                               self.aws_account.default_region,
                               volume['AvailabilityZone'],
                               volume['Encrypted'])

        for tag in volume.get('Tags', []):
          if tag.get('Key') == 'Name':
            aws_volume.name = tag.get('Value')
            break

        for attachment in volume.get('Attachments', []):
          if attachment.get('State') == 'attached':
            aws_volume.device_name = attachment.get('Device')
            break

        volumes[volume_id] = aws_volume
    return volumes

  def GetVolumesByNameOrId(self,
                           volume_name: Optional[str] = None,
                           volume_id: Optional[str] = None,
                           region: Optional[str] = None) -> List[AWSVolume]:
    """Get a volume from an AWS account by its name tag or its ID.

    Exactly one of [volume_name, volume_id] must be specified. If looking up
    a volume by its ID, the method returns a list with exactly one
    element. If looking up volumes by their name tag (which are not unique
    across volumes), then the method will return a list of all volumes
    with that name tag, or an empty list if no volumes with matching name tag
    could be found.

    Args:
      volume_name (str): Optional. The volume name tag of the volume to get.
      volume_id (str): Optional. The volume id of the volume to get.
      region (str): Optional. The region to look the volume in.
          If none provided, the default_region associated to the AWSAccount
          object will be used.

    Returns:
      List[AWSVolume]: A list of Amazon EC2 Volume objects.

    Raises:
      ValueError: If both volume_name and volume_id are None or if both
          are set.
    """

    if (not volume_name and not volume_id) or (volume_name and volume_id):
      raise ValueError('You must specify exactly one of [volume_name, '
                       'volume_id]. Got volume_name: {0:s}, volume_id: '
                       '{1:s}'.format(str(volume_name), str(volume_id)))
    if volume_name:
      return self.GetVolumesByName(volume_name, region=region)
    # mypy complains that volume_id may be None here, but at this point in the
    # code it never is, so it's safe to ignore the warning.
    return [self.GetVolumeById(volume_id, region=region)]  # type: ignore

  def GetVolumesByName(self,
                       volume_name: str,
                       region: Optional[str] = None) -> List[AWSVolume]:
    """Get all volumes from an AWS account with matching name tag.

    Args:
      volume_name (str): The volume name tag.
      region (str): Optional. The region to look the volume in.
          If none provided, the default_region associated to the AWSAccount
          object will be used.

    Returns:
      List[AWSVolume]: A list of EC2 Volume objects. If no volume with
          matching name tag is found, the method returns an empty list.
    """

    volumes = self.ListVolumes(region=region)
    return [volume for volume in volumes.values() if
            volume.name == volume_name]

  def GetVolumeById(self,
                    volume_id: str,
                    region: Optional[str] = None) -> AWSVolume:
    """Get a volume from an AWS account by its ID.

    Args:
      volume_id (str): The volume id.
      region (str): Optional. The region to look the volume in.
          If none provided, the default_region associated to the AWSAccount
          object will be used.

    Returns:
      AWSVolume: An Amazon EC2 Volume object.

    Raises:
      ResourceNotFoundError: If the volume does not exist.
    """

    volumes = self.ListVolumes(region=region)
    volume = volumes.get(volume_id)
    if not volume:
      raise errors.ResourceNotFoundError(
          'Volume {0:s} was not found in AWS account'.format(volume_id),
          __name__)
    return volume

  def CreateVolumeFromSnapshot(
      self,
      snapshot: AWSSnapshot,
      volume_name: Optional[str] = None,
      volume_name_prefix: Optional[str] = None,
      volume_type: str = 'gp2',
      kms_key_id: Optional[str] = None,
      tags: Optional[Dict[str, str]] = None) -> AWSVolume:
    """Create a new volume based on a snapshot.

    Args:
      snapshot (AWSSnapshot): Snapshot to use.
      volume_name (str): Optional. String to use as new volume name.
      volume_name_prefix (str): Optional. String to prefix the volume name with.
      volume_type (str): Optional. The volume type for the volume to create.
          Can be one of 'standard'|'io1'|'gp2'|'sc1'|'st1'. The default is
          'gp2'.
      kms_key_id (str): Optional. A KMS key id to encrypt the volume with.
      tags (Dict[str, str]): Optional. A dictionary of tags to add to the
          volume, for example {'TicketID': 'xxx'}. An entry for the volume
          name is added by default.

    Returns:
      AWSVolume: An AWS EBS Volume.

    Raises:
      InvalidNameError: If the volume name does not comply with the RegEx
      ValueError: If the volume type is invalid.
      ResourceCreationError: If the volume could not be created.
    """

    if volume_type not in ['standard', 'io1', 'gp2', 'sc1', 'st1']:
      raise ValueError('Volume type must be one of [standard, io1, gp2, sc1, '
                       'st1]. Got: {0:s}'.format(volume_type))

    if not volume_name:
      volume_name = self._GenerateVolumeName(
          snapshot, volume_name_prefix=volume_name_prefix)

    if len(volume_name) > 255:
      raise errors.InvalidNameError(
          'Volume name {0:s} is too long (>255 chars)'.format(volume_name),
          __name__)

    if not tags:
      tags = {}
    tags['Name'] = volume_name

    client = self.aws_account.ClientApi(common.EC2_SERVICE)
    create_volume_args = {
        'AvailabilityZone': snapshot.availability_zone,
        'SnapshotId': snapshot.snapshot_id,
        'TagSpecifications': [common.CreateTags(common.VOLUME, tags)],
        'VolumeType': volume_type
    }
    if kms_key_id:
      create_volume_args['Encrypted'] = True
      create_volume_args['KmsKeyId'] = kms_key_id
    if volume_type == 'io1':
      # If using the io1 volume type, we must specify Iops, see
      # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/
      # services/ec2.html#EC2.Client.create_volume. io1 volumes allow for a
      # ratio of 50 IOPS per 1 GiB.
      create_volume_args['Iops'] = self.aws_account.ResourceApi(
          common.EC2_SERVICE).Snapshot(snapshot.snapshot_id).volume_size * 50
    try:
      volume = client.create_volume(**create_volume_args)
      volume_id = volume['VolumeId']
      # Wait for volume creation completion
      client.get_waiter('volume_available').wait(VolumeIds=[volume_id])
    except (client.exceptions.ClientError,
            botocore.exceptions.WaiterError) as exception:
      raise errors.ResourceCreationError(
          'Could not create volume {0:s} from snapshot {1:s}: {2!s}'.format(
              volume_name, snapshot.name, exception), __name__) from exception

    zone = volume['AvailabilityZone']
    encrypted = volume['Encrypted']

    return AWSVolume(volume_id,
                     self.aws_account,
                     self.aws_account.default_region,
                     zone,
                     encrypted,
                     name=volume_name)

  def GetAccountInformation(self) -> Dict[str, str]:
    """Get information about the AWS account in use.

    If the call succeeds, then the response from the STS API is expected to
    have the following entries:
      - UserId
      - Account
      - Arn
    See https://boto3.amazonaws.com/v1/documentation/api/1.9.42/reference/services/sts.html#STS.Client.get_caller_identity for more details. # pylint: disable=line-too-long

    Returns:
      Dict[str, str]: The AWS account information.
    """
    account_information = self.aws_account.ClientApi(
        common.ACCOUNT_SERVICE).get_caller_identity()  # type: Dict[str, str]
    return account_information

  def _GenerateVolumeName(self,
                          snapshot: AWSSnapshot,
                          volume_name_prefix: Optional[str] = None) -> str:
    """Generate a new volume name given a volume's snapshot.

    Args:
      snapshot (AWSSnapshot): A volume's Snapshot.
      volume_name_prefix (str): Optional. Prefix for the volume name.

    Returns:
      str: A name for the volume.

    Raises:
      ValueError: If the volume name does not comply with the RegEx,
          or if AWS account information could not be retrieved.
    """

    # Max length of tag values in AWS is 255 characters
    user_id = self.GetAccountInformation().get('UserId')
    if not user_id:
      raise ValueError('Could not fetch AWS user ID')
    volume_id = user_id + snapshot.volume.volume_id
    volume_id_crc32 = '{0:08x}'.format(
        binascii.crc32(volume_id.encode()) & 0xffffffff)
    truncate_at = 255 - len(volume_id_crc32) - len('-copy') - 1
    if not snapshot.name:
      snapshot.name = snapshot.snapshot_id
    if volume_name_prefix:
      volume_name_prefix += '-'
      if len(volume_name_prefix) > truncate_at:
        # The volume name prefix is too long
        volume_name_prefix = volume_name_prefix[:truncate_at]
      truncate_at -= len(volume_name_prefix)
      volume_name = '{0:s}{1:s}-{2:s}-copy'.format(
          volume_name_prefix,
          snapshot.name[:truncate_at],
          volume_id_crc32)
    else:
      volume_name = '{0:s}-{1:s}-copy'.format(
          snapshot.name[:truncate_at], volume_id_crc32)

    return volume_name
