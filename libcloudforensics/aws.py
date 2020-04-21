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
"""Library for incident response operations on AWS EC2."""
import binascii
import datetime
import logging
import re

import boto3
import botocore

log = logging.getLogger()

EC2_SERVICE = 'ec2'
ACCOUNT_SERVICE = 'sts'
REGEX_TAG_VALUE = re.compile('^.{1,255}$')


class AWSAccount:
  """Class representing an AWS account.

  Attributes:
    default_availability_zone (str): Default zone within the region to create
        new resources in.
  """
  def __init__(self, default_availability_zone):
    self.default_availability_zone = default_availability_zone
    # The region is given by the zone minus the last letter
    # https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html#using-regions-availability-zones-describe # pylint: disable=line-too-long
    self.default_region = self.default_availability_zone[:-1]

  def ClientApi(self, service, region=None):
    """Create an AWS client object.

    Args:
      service (str): The AWS service to use.
      region (str): Optional. The region is which to create new resources in.

    Returns:
      boto3.Session.Client: An AWS EC2 client object.
    """
    if region:
      return boto3.session.Session().client(
          service_name=service, region_name=region)
    return boto3.session.Session().client(
        service_name=service, region_name=self.default_region)

  def ResourceApi(self, service, region=None):
    """Create an AWS resource object.

    Args:
      service (str): The AWS service to use.
      region (str): Optional. The region is which to create new resources in.

    Returns:
      boto3.Session.Resource: An AWS EC2 resource object.
    """
    if region:
      return boto3.session.Session().resource(
          service_name=service, region_name=region)
    return boto3.session.Session().resource(
        service_name=service, region_name=self.default_region)

  def ListInstances(self, region=None, filters=None, show_terminated=False):
    """List instances of an AWS account.

    Example usage:
      ListInstances(region='us-east-1', filters=[
          {'Name':'instance-id', 'Values':['some-instance-id']}])

    Args:
      region (str): Optional. The region from which to list instances.
      filters (list(dict)): Optional. Filters for the query.
      show_terminated (bool): Optional. Include terminated instances in the
          list.

    Returns:
      dict: Dictionary with name and metadata for each instance.

    Raises:
      RuntimeError: If instances can't be listed.
    """
    if not filters:
      filters = []

    instances = {}
    next_token = None
    client = self.ClientApi(EC2_SERVICE, region=region)

    while True:
      try:
        if next_token:
          response = client.describe_instances(
              Filters=filters, NextToken=next_token)
        else:
          response = client.describe_instances(Filters=filters)
      except client.exceptions.ClientError as exception:
        raise RuntimeError('Could not retrieve instances: {0:s}'.format(
            str(exception)))

      for reservation in response['Reservations']:
        for instance in reservation['Instances']:
          # If reservation['Instances'] contains any entry, then the
          # instance's state is expected to be present in the API's response.
          if instance['State']['Name'] == 'terminated' and not show_terminated:
            continue

          zone = instance['Placement']['AvailabilityZone']
          instance_info = {
              'region': zone[:-1],
              'zone': zone
          }

          for tag in instance.get('Tags', []):
            if tag.get('Key') == 'Name':
              instance_info['name'] = tag.get('Value')
              break

          instances[instance['InstanceId']] = instance_info

      next_token = response.get('NextToken')
      if not next_token:
        break

    return instances

  def ListVolumes(self, region=None, filters=None):
    """List volumes of an AWS account.

    Example usage:
      # List volumes attached to the instance 'some-instance-id'
      ListVolumes(filters=[
          {'Name':'attachment.instance-id', 'Values':['some-instance-id']}])

    Args:
      region (str): Optional. The region from which to list the volumes.
      filters (list(dict)): Optional. Filter for the query.

    Returns:
      dict: Dictionary with name and metadata for each volume.

    Raises:
      RuntimeError: If volumes can't be listed.
    """
    if not filters:
      filters = []

    volumes = {}
    next_token = None
    client = self.ClientApi(EC2_SERVICE, region=region)

    while True:
      try:
        if next_token:
          response = client.describe_volumes(
              Filters=filters, NextToken=next_token)
        else:
          response = client.describe_volumes(Filters=filters)
      except client.exceptions.ClientError as exception:
        raise RuntimeError('Could not retrieve volumes: {0:s}'.format(
            str(exception)))

      for volume in response['Volumes']:
        volume_info = {
            'region': self.default_region,
            'zone': volume['AvailabilityZone']
        }

        for tag in volume.get('Tags', []):
          if tag.get('Key') == 'Name':
            volume_info['name'] = tag.get('Value')
            break

        if len(volume['Attachments']) > 0:
          volume_info['device'] = volume['Attachments'][0]['Device']

        volumes[volume['VolumeId']] = volume_info

      next_token = response.get('NextToken')
      if not next_token:
        break

    return volumes

  def GetInstancesByNameOrId(self,
                             instance_name=None,
                             instance_id=None,
                             region=None):
    """Get instances from an AWS account by their name tag or an ID.

    Exactly one of [instance_name, instance_id] must be specified. If looking up
    an instance by its ID, the method returns a list with exactly one
    element. If looking up instances by their name tag (which are not unique
    across instances), then the method will return a list of all instances
    with that name tag, or an empty list if no instances with matching name
    tag could be found.

    Args:
      instance_name (str): Optional. The instance name tag of the instance to
          get.
      instance_id (str): Optional. The instance id of the instance to get.
      region (str): Optional. The region to look the instance in.

    Returns:
      list(AWSInstance): A list of Amazon EC2 Instance objects.

    Raises:
      ValueError: If both instance_name and instance_id are None or if both
          are set.
    """
    if (not instance_name and not instance_id) or (instance_name and instance_id):  # pylint: disable=line-too-long
      raise ValueError('You must specify exactly one of [instance_name, '
                       'instance_id]. Got instance_name: {0:s}, instance_id: '
                       '{1:s}'.format(instance_name, instance_id))
    if instance_name:
      return self.GetInstancesByName(instance_name, region=region)

    return [self.GetInstanceById(instance_id, region=region)]

  def GetVolumesByNameOrId(self,
                           volume_name=None,
                           volume_id=None,
                           region=None):
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

    Returns:
      list(AWSVolume): A list of Amazon EC2 Volume objects.

    Raises:
      ValueError: If both volume_name and volume_id are None or if both
          are set.
    """
    if (not volume_name and not volume_id) or (volume_name and volume_id):
      raise ValueError('You must specify exactly one of [volume_name, '
                       'volume_id]. Got volume_name: {0:s}, volume_id: '
                       '{1:s}'.format(volume_name, volume_id))
    if volume_name:
      return self.GetVolumesByName(volume_name, region=region)

    return [self.GetInstanceById(volume_id, region=region)]

  def CreateVolumeFromSnapshot(self,
                               snapshot,
                               volume_name=None,
                               volume_name_prefix=''):
    """Create a new volume based on a snapshot.

    Args:
      snapshot (AWSSnapshot): Snapshot to use.
      volume_name (str): Optional. String to use as new volume name.
      volume_name_prefix (str): Optional. String to prefix the volume name with.

    Returns:
      AWSVolume: An AWS EBS Volume.

    Raises:
      ValueError: If the volume name does not comply with the RegEx.
      RuntimeError: If the volume could not be created.
    """

    if not volume_name:
      volume_name = self._GenerateVolumeName(
          snapshot, volume_name_prefix=volume_name_prefix)

    if not REGEX_TAG_VALUE.match(volume_name):
      raise ValueError('Volume name {0:s} does not comply with '
                       '{1:s}'.format(volume_name, REGEX_TAG_VALUE.pattern))

    client = self.ClientApi(EC2_SERVICE)
    try:
      volume = client.create_volume(
          AvailabilityZone=snapshot.availability_zone,
          SnapshotId=snapshot.snapshot_id,
          TagSpecifications=[GetTagForResourceType('volume', volume_name)])
      volume_id = volume['VolumeId']
      zone = volume['AvailabilityZone']
      # Wait for volume creation completion
      client.get_waiter('volume_available').wait(VolumeIds=[volume_id])
    except (client.exceptions.ClientError,
            botocore.exceptions.WaiterError) as exception:
      raise RuntimeError('Could not create volume {0:s} from snapshot '
                         '{1:s}: {2:s}'.format(volume_name, snapshot.name,
                                               str(exception)))

    return AWSVolume(volume_id,
                     self,
                     self.default_region,
                     zone,
                     name=volume_name)

  def _GenerateVolumeName(self, snapshot, volume_name_prefix=None):
    """Generate a new volume name given a volume's snapshot.

    Args:
      snapshot (AWSSnapshot): A volume's Snapshot.
      volume_name_prefix (str): Optional. Prefix for the volume name.

    Returns:
      str: A name for the volume.

    Raises:
      ValueError: if the volume name does not comply with the RegEx.
    """

    # Max length of tag values in AWS is 255 characters
    # UserId is expected to be set if the call to the EC2 API is successful.
    # https://boto3.amazonaws.com/v1/documentation/api/1.9.42/reference/services/sts.html#STS.Client.get_caller_identity for more details. # pylint: disable=line-too-long
    user_id = self.ClientApi(ACCOUNT_SERVICE).get_caller_identity()['UserId']
    volume_id = user_id + snapshot.volume.volume_id
    volume_id_crc32 = '{0:08x}'.format(
        binascii.crc32(volume_id.encode()) & 0xffffffff)
    truncate_at = 255 - len(volume_id_crc32) - len('-copy') - 1
    if volume_name_prefix:
      volume_name_prefix += '-'
      if len(volume_name_prefix) > truncate_at:
        # The volume name prefix is too long
        volume_name_prefix = volume_name_prefix[:truncate_at]
      truncate_at -= len(volume_name_prefix)
      volume_name = '{0:s}{1:s}-{2:s}-copy'.format(
          volume_name_prefix, snapshot.name[:truncate_at], volume_id_crc32)
    else:
      volume_name = '{0:s}-{1:s}-copy'.format(
          snapshot.name[:truncate_at], volume_id_crc32)

    return volume_name

  def GetInstanceById(self, instance_id, region=None):
    """Get an instance from an AWS account by its ID.

    Args:
      instance_id (str): The instance id.
      region (str): Optional. The region to look the instance in.

    Returns:
      AWSInstance: An Amazon EC2 Instance object.

    Raises:
      RuntimeError: If instance does not exist.
    """
    if not region:
      region = self.default_region

    instances = self.ListInstances(region=region)
    instance = instances.get(instance_id)
    if not instance:
      error_msg = 'Instance {0:s} was not found in AWS account'.format(
          instance_id)
      raise RuntimeError(error_msg)

    zone = instance['zone']

    return AWSInstance(self, instance_id, region, zone)

  def GetInstancesByName(self, instance_name, region=None):
    """Get all instances from an AWS account with matching name tag.

    Args:
      instance_name (str): The instance name tag.
      region (str): Optional. The region to look the instance in.

    Returns:
      list(AWSInstance): A list of EC2 Instance objects. If no instance with
          matching name tag is found, the method returns an empty list.
    """
    if not region:
      region = self.default_region

    matching_instances = []
    all_instances = self.ListInstances(region=region)
    for instance_id in all_instances:
      if all_instances[instance_id].get('name') == instance_name:
        matching_instances.append(
            AWSInstance(self,
                        instance_id,
                        region,
                        all_instances[instance_id]['zone'],
                        name=instance_name)
        )
    return matching_instances

  def GetVolumeById(self, volume_id, region=None):
    """Get a volume from an AWS account by its ID.

    Args:
      volume_id (str): The volume id.
      region (str): Optional. The region to look the volume in.

    Returns:
      AWSVolume: An Amazon EC2 Volume object.

    Raises:
      RuntimeError: If volume does not exist.
    """
    if not region:
      region = self.default_region

    volumes = self.ListVolumes(region=region)
    volume = volumes.get(volume_id)
    if not volume:
      error_msg = 'Volume {0:s} was not found in AWS account'.format(
          volume_id)
      raise RuntimeError(error_msg)

    zone = volume['zone']

    return AWSVolume(volume_id, self, region, zone)

  def GetVolumesByName(self, volume_name, region=None):
    """Get all volumes from an AWS account with matching name tag.

    Args:
      volume_name (str): The volume name tag.
      region (str): Optional. The region to look the volume in.

    Returns:
      list(AWSVolume): A list of EC2 Volume objects. If no volume with
          matching name tag is found, the method returns an empty list.
    """
    if not region:
      region = self.default_region

    matching_volumes = []
    all_volumes = self.ListVolumes(region=region)
    for volume_id in all_volumes:
      if all_volumes[volume_id].get('name', None) == volume_name:
        matching_volumes.append(
            AWSVolume(volume_id,
                      self,
                      region,
                      all_volumes[volume_id]['zone'],
                      name=volume_name)
        )
    return matching_volumes


class AWSInstance:
  """Class representing an AWS EC2 instance.

  Attributes:
    aws_account (AWSAccount): The account for the instance.
    instance_id (str): The id of the instance.
    region (str): The region the instance is in.
    availability_zone (str): The zone within the region in which the instance
        is.
    name (str): Optional. The name tag (if any) of the instance.
  """
  def __init__(self,
               aws_account,
               instance_id,
               region,
               availability_zone,
               name=None):
    """Initialize the AWS EC2 instance.

    Args:
      aws_account (AWSAccount): The account for the instance.
      instance_id (str): The id of the instance.
      region (str): The region the instance is in.
      availability_zone (str): The zone within the region in which the instance
          is.
      name (str): Optional. The name tag (if any) of the instance.
    """
    self.aws_account = aws_account
    self.instance_id = instance_id
    self.region = region
    self.availability_zone = availability_zone
    self.name = name

  def GetBootVolume(self):
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
      if volumes[volume_id]['device'] == boot_device:
        return AWSVolume(volume_id,
                         self.aws_account,
                         self.region,
                         self.availability_zone)

    error_msg = 'Boot volume not found for instance: {0:s}'.format(
        self.instance_id)
    raise RuntimeError(error_msg)

  def ListVolumes(self):
    """List all volumes for the instance.

    Returns:
      dict: Dictionary with name and metadata for each volume.
    """
    return self.aws_account.ListVolumes(
        filters=[{
            'Name': 'attachment.instance-id',
            'Values': [self.instance_id]}])


class AWSElasticBlockStore:
  """Class representing an AWS EBS resource.

  Attributes:
    aws_account (AWSAccount): The account for the resource.
    region (str): The region the EBS is in.
    availability_zone (str): The zone within the region in which the EBS is.
    name (str): The name tag (if any) of the EBS resource.
  """
  def __init__(self, aws_account, region, availability_zone, name=None):
    """Initialize the AWS EBS resource.

    Args:
      aws_account (AWSAccount): The account for the resource.
      region (str): The region the EBS is in.
      availability_zone (str): The zone within the region in which the EBS is.
      name (str): Optional. The name tag (if any) of the EBS resource.
    """
    self.aws_account = aws_account
    self.region = region
    self.availability_zone = availability_zone
    self.name = name


class AWSVolume(AWSElasticBlockStore):
  """Class representing an AWS EBS volume.

  Attributes:
    volume_id (str): The id of the volume.
    aws_account (AWSAccount): The account for the volume.
    region (str): The region the volume is in.
    availability_zone (str): The zone within the region in which the volume is.
    name (str): Optional. The name tag (if any) of the volume.
  """
  def __init__(self,
               volume_id,
               aws_account,
               region,
               availability_zone,
               name=None):
    """Initialize an AWS EBS volume.

    Args:
      volume_id (str): The id of the volume.
      aws_account (AWSAccount): The account for the volume.
      region (str): The region the volume is in.
      availability_zone (str): The zone within the region in which the volume
          is.
      name (str): Optional. The name tag (if any) of the volume.
    """
    super(AWSVolume, self).__init__(aws_account,
                                    region,
                                    availability_zone,
                                    name)
    self.volume_id = volume_id

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
          TagSpecifications=[GetTagForResourceType('snapshot', snapshot_name)])

      snapshot_id = snapshot.get('SnapshotId')
      # Wait for snapshot completion
      client.get_waiter('snapshot_completed').wait(SnapshotIds=[snapshot_id])
    except (client.exceptions.ClientError,
            botocore.exceptions.WaiterError) as exception:
      raise RuntimeError('Could not create snapshot for volume {0:s}: '
                         '{1:s}'.format(self.volume_id, str(exception)))

    return AWSSnapshot(snapshot_id, self, name=snapshot_name)


class AWSSnapshot(AWSElasticBlockStore):
  """Class representing an AWS EBS snapshot.

  Attributes:
    snapshot_id (str): The id of the snapshot.
    volume (AWSVolume): The volume from which the snapshot was taken.
    name (str): Optional. The name tag (if any) of the snapshot.
  """
  def __init__(self, snapshot_id, volume, name=None):
    """Initialize an AWS EBS snapshot.

    Args:
      snapshot_id (str): The id of the snapshot.
      volume (AWSVolume): The volume from which the snapshot was taken.
      name (str): Optional. The name tag (if any) of the snapshot.
    """
    super(AWSSnapshot, self).__init__(volume.aws_account,
                                      volume.region,
                                      volume.availability_zone,
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


def CreateVolumeCopy(instance_id, zone, volume_id=None):
  """Create a copy of an AWS EBS Volume.

  Args:
    instance_id (str): Instance ID of the instance using the volume
        to be copied.
    zone (str): The zone within the region to create the new resource in.
    volume_id (str): Optional. ID of the volume to copy. If None,
        boot volume will be copied.

  Returns:
    AWSVolume: An AWS EBS Volume object.

  Raises:
    RuntimeError: If there are errors copying the volume.
  """

  aws_account = AWSAccount(zone)
  instance = aws_account.GetInstanceById(instance_id)
  try:
    if volume_id:
      volume_to_copy = aws_account.GetVolumeById(volume_id)
    else:
      volume_to_copy = instance.GetBootVolume()

    log.info('Volume copy of {0:s} started...'.format(volume_to_copy.volume_id))
    snapshot = volume_to_copy.Snapshot()
    new_volume = aws_account.CreateVolumeFromSnapshot(
        snapshot, volume_name_prefix='evidence')
    snapshot.Delete()
    log.info('Volume {0:s} successfully copied to {1:s}'.format(
        volume_to_copy.volume_id, new_volume.volume_id))

  except RuntimeError as exception:
    error_msg = 'Copying volume {0:s}: {1!s}'.format(
        volume_id, exception)
    raise RuntimeError(error_msg)

  return new_volume


def GetTagForResourceType(resource, name):
  """Create a dictionary for AWS Tag Specifications.

  Args:
    resource (str): The type of AWS resource.
    name (str): The name of the resource.

  Returns:
    dict: A dictionary for AWS Tag Specifications.
  """
  return {
      'ResourceType': resource,
      'Tags': [
          {
              'Key': 'Name',
              'Value': name
          }
      ]
  }
