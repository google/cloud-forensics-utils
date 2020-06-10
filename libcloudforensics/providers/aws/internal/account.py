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
"""Library for incident response operations on AWS EC2.

Library to make forensic images of Amazon Elastic Block Store devices and create
analysis virtual machine to be used in incident response.
"""

import binascii
import json
from typing import Dict, List, Tuple, Optional, Any

import boto3
import botocore

from libcloudforensics.providers.aws.internal import ec2
from libcloudforensics.providers.aws.internal import ebs
from libcloudforensics.providers.aws.internal import common
from libcloudforensics.scripts import utils


class AWSAccount:
  """Class representing an AWS account.

  Attributes:
    default_availability_zone (str): Default zone within the region to create
        new resources in.
    aws_profile (str): The AWS profile defined in the AWS
        credentials file to use.
  """

  def __init__(self,
               default_availability_zone: str,
               aws_profile: Optional[str] = None) -> None:
    """Initialize the AWS account.

    Args:
      default_availability_zone (str): Default zone within the region to create
          new resources in.
      aws_profile (str): Optional. The AWS profile defined in the AWS
          credentials file to use.
    """

    self.aws_profile = aws_profile or 'default'
    self.default_availability_zone = default_availability_zone
    # The region is given by the zone minus the last letter
    # https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html#using-regions-availability-zones-describe # pylint: disable=line-too-long
    self.default_region = self.default_availability_zone[:-1]

  def ClientApi(self,
                service: str,
                region: Optional[str] = None) -> 'botocore.client.EC2':  # pylint: disable=no-member
    """Create an AWS client object.

    Args:
      service (str): The AWS service to use.
      region (str): Optional. The region in which to create new resources. If
          none provided, the default_region associated to the AWSAccount
          object will be used.
    Returns:
      botocore.client.EC2: An AWS EC2 client object.
    """

    if region:
      return boto3.session.Session(profile_name=self.aws_profile).client(
          service_name=service, region_name=region)
    return boto3.session.Session(profile_name=self.aws_profile).client(
        service_name=service, region_name=self.default_region)

  def ResourceApi(self,
                  service: str,
                  # pylint: disable=line-too-long
                  region: Optional[str] = None) -> 'boto3.resources.factory.ec2.ServiceResource':  # type: ignore
    # pylint: enable=line-too-long
    """Create an AWS resource object.

    Args:
      service (str): The AWS service to use.
      region (str): Optional. The region in which to create new resources. If
          none provided, the default_region associated to the AWSAccount
          object will be used.

    Returns:
      boto3.resources.factory.ec2.ServiceResource: An AWS EC2 resource object.
    """

    if region:
      return boto3.session.Session(profile_name=self.aws_profile).resource(
          service_name=service, region_name=region)
    return boto3.session.Session(profile_name=self.aws_profile).resource(
        service_name=service, region_name=self.default_region)

  def ListInstances(
      self,
      region: Optional[str] = None,
      filters: Optional[List[Dict[str, Any]]] = None,
      show_terminated: bool = False) -> Dict[str, ec2.AWSInstance]:
    """List instances of an AWS account.

    Example usage:
      ListInstances(region='us-east-1', filters=[
          {'Name':'instance-id', 'Values':['some-instance-id']}])

    Args:
      region (str): Optional. The region from which to list instances.
          If none provided, the default_region associated to the AWSAccount
          object will be used.
      filters (List[Dict]): Optional. Filters for the query. Filters are
          given as a list of dictionaries, e.g.: {'Name': 'someFilter',
          'Values': ['value1', 'value2']}.
      show_terminated (bool): Optional. Include terminated instances in the
          list.

    Returns:
      Dict[str, AWInstance]: Dictionary mapping instance IDs (str) to their
          respective AWSInstance object.

    Raises:
      RuntimeError: If instances can't be listed.
    """

    if not filters:
      filters = []

    instances = {}
    client = self.ClientApi(common.EC2_SERVICE, region=region)
    responses = common.ExecuteRequest(
        client, 'describe_instances', {'Filters': filters})

    for response in responses:
      for reservation in response['Reservations']:
        for instance in reservation['Instances']:
          # If reservation['Instances'] contains any entry, then the
          # instance's state is expected to be present in the API's response.
          if instance['State']['Name'] == 'terminated' and not show_terminated:
            continue

          zone = instance['Placement']['AvailabilityZone']
          instance_id = instance['InstanceId']
          aws_instance = ec2.AWSInstance(
              self, instance_id, zone[:-1], zone)

          for tag in instance.get('Tags', []):
            if tag.get('Key') == 'Name':
              aws_instance.name = tag.get('Value')
              break

          instances[instance_id] = aws_instance
    return instances

  def ListVolumes(
      self,
      region: Optional[str] = None,
      # pylint: disable=line-too-long
      filters: Optional[List[Dict[str, Any]]] = None) -> Dict[str, ebs.AWSVolume]:
      # pylint: enable=line-too-long
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
    client = self.ClientApi(common.EC2_SERVICE, region=region)
    responses = common.ExecuteRequest(
        client, 'describe_volumes', {'Filters': filters})
    for response in responses:
      for volume in response['Volumes']:
        volume_id = volume['VolumeId']
        aws_volume = ebs.AWSVolume(volume_id,
                                   self,
                                   self.default_region,
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

  def GetInstancesByNameOrId(
      self,
      instance_name: str = '',
      instance_id: str = '',
      region: Optional[str] = None) -> List[ec2.AWSInstance]:
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
          If none provided, the default_region associated to the AWSAccount
          object will be used.

    Returns:
      List[AWSInstance]: A list of Amazon EC2 Instance objects.

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

  def GetInstancesByName(self,
                         instance_name: str,
                         region: Optional[str] = None) -> List[ec2.AWSInstance]:
    """Get all instances from an AWS account with matching name tag.

    Args:
      instance_name (str): The instance name tag.
      region (str): Optional. The region to look the instance in.
          If none provided, the default_region associated to the AWSAccount
          object will be used.

    Returns:
      List[AWSInstance]: A list of EC2 Instance objects. If no instance with
          matching name tag is found, the method returns an empty list.
    """

    matching_instances = []
    instances = self.ListInstances(region=region)
    for instance_id in instances:
      aws_instance = instances[instance_id]
      if aws_instance.name == instance_name:
        matching_instances.append(aws_instance)
    return matching_instances

  def GetInstanceById(self,
                      instance_id: str,
                      region: Optional[str] = None) -> ec2.AWSInstance:
    """Get an instance from an AWS account by its ID.

    Args:
      instance_id (str): The instance id.
      region (str): Optional. The region to look the instance in.
          If none provided, the default_region associated to the AWSAccount
          object will be used.

    Returns:
      AWSInstance: An Amazon EC2 Instance object.

    Raises:
      RuntimeError: If instance does not exist.
    """

    instances = self.ListInstances(region=region)
    instance = instances.get(instance_id)
    if not instance:
      error_msg = 'Instance {0:s} was not found in AWS account'.format(
          instance_id)
      raise RuntimeError(error_msg)
    return instance

  def GetVolumesByNameOrId(self,
                           volume_name: str = '',
                           volume_id: str = '',
                           region: Optional[str] = None) -> List[ebs.AWSVolume]:
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
                       '{1:s}'.format(volume_name, volume_id))
    if volume_name:
      return self.GetVolumesByName(volume_name, region=region)

    return [self.GetVolumeById(volume_id, region=region)]

  def GetVolumesByName(self,
                       volume_name: str,
                       region: Optional[str] = None) -> List[ebs.AWSVolume]:
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

    matching_volumes = []
    volumes = self.ListVolumes(region=region)
    for volume_id in volumes:
      volume = volumes[volume_id]
      if volume.name == volume_name:
        matching_volumes.append(volume)
    return matching_volumes

  def GetVolumeById(self,
                    volume_id: str,
                    region: Optional[str] = None) -> ebs.AWSVolume:
    """Get a volume from an AWS account by its ID.

    Args:
      volume_id (str): The volume id.
      region (str): Optional. The region to look the volume in.
          If none provided, the default_region associated to the AWSAccount
          object will be used.

    Returns:
      AWSVolume: An Amazon EC2 Volume object.

    Raises:
      RuntimeError: If volume does not exist.
    """

    volumes = self.ListVolumes(region=region)
    volume = volumes.get(volume_id)
    if not volume:
      error_msg = 'Volume {0:s} was not found in AWS account'.format(
          volume_id)
      raise RuntimeError(error_msg)
    return volume

  def CreateVolumeFromSnapshot(
      self,
      snapshot: ebs.AWSSnapshot,
      volume_name: Optional[str] = None,
      volume_name_prefix: str = '',
      kms_key_id: Optional[str] = None) -> ebs.AWSVolume:
    """Create a new volume based on a snapshot.

    Args:
      snapshot (AWSSnapshot): Snapshot to use.
      volume_name (str): Optional. String to use as new volume name.
      volume_name_prefix (str): Optional. String to prefix the volume name with.
      kms_key_id (str): Optional. A KMS key id to encrypt the volume with.

    Returns:
      AWSVolume: An AWS EBS Volume.

    Raises:
      ValueError: If the volume name does not comply with the RegEx.
      RuntimeError: If the volume could not be created.
    """

    if not volume_name:
      volume_name = self._GenerateVolumeName(
          snapshot, volume_name_prefix=volume_name_prefix)

    if not common.REGEX_TAG_VALUE.match(volume_name):
      raise ValueError(
          'Volume name {0:s} does not comply with '
          '{1:s}'.format(volume_name, common.REGEX_TAG_VALUE.pattern))

    client = self.ClientApi(common.EC2_SERVICE)
    create_volume_args = {
        'AvailabilityZone': snapshot.availability_zone,
        'SnapshotId': snapshot.snapshot_id,
        'TagSpecifications':
            [common.GetTagForResourceType('volume', volume_name)]
    }
    if kms_key_id:
      create_volume_args['Encrypted'] = True
      create_volume_args['KmsKeyId'] = kms_key_id
    try:
      volume = client.create_volume(**create_volume_args)
      volume_id = volume['VolumeId']
      # Wait for volume creation completion
      client.get_waiter('volume_available').wait(VolumeIds=[volume_id])
    except (client.exceptions.ClientError,
            botocore.exceptions.WaiterError) as exception:
      raise RuntimeError('Could not create volume {0:s} from snapshot '
                         '{1:s}: {2:s}'.format(volume_name, snapshot.name,
                                               str(exception)))

    zone = volume['AvailabilityZone']
    encrypted = volume['Encrypted']

    return ebs.AWSVolume(volume_id,
                         self,
                         self.default_region,
                         zone,
                         encrypted,
                         name=volume_name)

  def GetOrCreateAnalysisVm(
      self,
      vm_name: str,
      boot_volume_size: int,
      ami: str,
      cpu_cores: int,
      packages: Optional[List[str]] = None,
      ssh_key_name: Optional[str] = None) -> Tuple[ec2.AWSInstance, bool]:
    """Get or create a new virtual machine for analysis purposes.

    Args:
      vm_name (str): The instance name tag of the virtual machine.
      boot_volume_size (int): The size of the analysis VM boot volume (in GB).
      ami (str): The Amazon Machine Image ID to use to create the VM.
      cpu_cores (int): Number of CPU cores for the analysis VM.
      packages (List[str]): Optional. List of packages to install in the VM.
      ssh_key_name (str): Optional. A SSH key pair name linked to the AWS
          account to associate with the VM. If none provided, the VM can only
          be accessed through in-browser SSH from the AWS management console
          with the EC2 client connection package (ec2-instance-connect). Note
          that if this package fails to install on the target VM, then the VM
          will not be accessible. It is therefore recommended to fill in this
          parameter.

    Returns:
      Tuple[AWSInstance, bool]: A tuple with an AWSInstance object and a
          boolean indicating if the virtual machine was created (True) or
          reused (False).

    Raises:
      RuntimeError: If the virtual machine cannot be found or created.
    """

    # Re-use instance if it already exists, or create a new one.
    try:
      instances = self.GetInstancesByName(vm_name)
      if instances:
        created = False
        return instances[0], created
    except RuntimeError:
      pass

    instance_type = common.GetInstanceTypeByCPU(cpu_cores)
    startup_script = utils.ReadStartupScript()
    if packages:
      startup_script = startup_script.replace('${packages[@]}', ' '.join(
          packages))

    # Install ec2-instance-connect to allow SSH connections from the browser.
    startup_script = startup_script.replace(
        '(exit ${exit_code})',
        'apt -y install ec2-instance-connect && (exit ${exit_code})')

    client = self.ClientApi(common.EC2_SERVICE)
    vm_args = {
        'BlockDeviceMappings':
            [self._GetBootVolumeConfigByAmi(ami, boot_volume_size)],
        'ImageId': ami,
        'MinCount': 1,
        'MaxCount': 1,
        'InstanceType': instance_type,
        'TagSpecifications':
            [common.GetTagForResourceType('instance', vm_name)],
        'UserData': startup_script,
        'Placement': {'AvailabilityZone': self.default_availability_zone}
    }
    if ssh_key_name:
      vm_args['KeyName'] = ssh_key_name
    # Create the instance in AWS
    try:
      instance = client.run_instances(**vm_args)
      # If the call to run_instances was successful, then the API response
      # contains the instance ID for the new instance.
      instance_id = instance['Instances'][0]['InstanceId']
      # Wait for the instance to be running
      client.get_waiter('instance_running').wait(InstanceIds=[instance_id])
      # Wait for the status checks to pass
      client.get_waiter('instance_status_ok').wait(InstanceIds=[instance_id])
    except (client.exceptions.ClientError,
            botocore.exceptions.WaiterError) as exception:
      raise RuntimeError('Could not create instance {0:s}: {1:s}'.format(
          vm_name, str(exception)))

    instance = ec2.AWSInstance(self,
                               instance_id,
                               self.default_region,
                               self.default_availability_zone,
                               name=vm_name)
    created = True
    return instance, created

  def GetAccountInformation(self, info: str) -> str:
    """Get information about the AWS account in use.

    If the call succeeds, then the response from the STS API is expected to
    have the following entries:
      - UserId
      - Account
      - Arn
    See https://boto3.amazonaws.com/v1/documentation/api/1.9.42/reference/services/sts.html#STS.Client.get_caller_identity for more details. # pylint: disable=line-too-long

    Args:
      info (str): The account information to retrieve. Must be one of [UserID,
          Account, Arn]
    Returns:
      str: The information requested.

    Raises:
      KeyError: If the requested information doesn't exist.
    """

    account_information = self.ClientApi(
        common.ACCOUNT_SERVICE).get_caller_identity()  # type: Dict[str, str]
    if not account_information.get(info):
      raise KeyError('Key must be one of ["UserId", "Account", "Arn"]')
    return account_information[info]

  def CreateKMSKey(self) -> str:
    """Create a KMS key.

    Returns:
      str: The KMS key ID for the key that was created.

    Raises:
      RuntimeError: If the key could not be created.
    """

    client = self.ClientApi(common.KMS_SERVICE)
    try:
      kms_key = client.create_key()
    except client.exceptions.ClientError as exception:
      raise RuntimeError('Could not create KMS key: {0:s}'.format(
          str(exception)))

    # The response contains the key ID
    return kms_key['KeyMetadata']['KeyId']  # type: ignore

  def ShareKMSKeyWithAWSAccount(self,
                                kms_key_id: str,
                                aws_account_id: str) -> None:
    """Share a KMS key.

    Args:
      kms_key_id (str): The KMS key ID of the key to share.
      aws_account_id (str): The AWS Account ID to share the KMS key with.

    Raises:
      RuntimeError: If the key could not be shared.
    """

    share_policy = {
        'Sid': 'Allow use of the key',
        'Effect': 'Allow',
        'Principal': {
            'AWS': 'arn:aws:iam::{0:s}:root'.format(aws_account_id)
        },
        'Action': [
            # kms:*crypt and kms:ReEncrypt* are necessary to transfer
            # encrypted EBS resources across accounts.
            'kms:Encrypt',
            'kms:Decrypt',
            'kms:ReEncrypt*',
            # kms:CreateGrant is necessary to transfer encrypted EBS
            # resources across regions.
            'kms:CreateGrant'
        ],
        'Resource': '*'
    }
    client = self.ClientApi(common.KMS_SERVICE)
    try:
      policy = json.loads(client.get_key_policy(
          KeyId=kms_key_id, PolicyName='default')['Policy'])
      policy['Statement'].append(share_policy)
      # Update the key policy so that it is shared with the AWS account.
      client.put_key_policy(
          KeyId=kms_key_id, PolicyName='default', Policy=json.dumps(policy))
    except client.exceptions.ClientError as exception:
      raise RuntimeError('Could not share KMS key {0:s}: {1:s}'.format(
          kms_key_id, str(exception)))

  def DeleteKMSKey(self, kms_key_id: Optional[str] = None) -> None:
    """Delete a KMS key.

    Schedule the KMS key for deletion. By default, users have a 30 days
        window before the key gets deleted.

    Args:
      kms_key_id (str): The ID of the KMS key to delete.

    Raises:
      RuntimeError: If the key could not be scheduled for deletion.
    """

    if not kms_key_id:
      return

    client = self.ClientApi(common.KMS_SERVICE)
    try:
      client.schedule_key_deletion(KeyId=kms_key_id)
    except client.exceptions.ClientError as exception:
      raise RuntimeError('Could not schedule the KMS key: {0:s} for '
                         'deletion'.format(str(exception)))

  def _GenerateVolumeName(self,
                          snapshot: ebs.AWSSnapshot,
                          volume_name_prefix: Optional[str] = None) -> str:
    """Generate a new volume name given a volume's snapshot.

    Args:
      snapshot (AWSSnapshot): A volume's Snapshot.
      volume_name_prefix (str): Optional. Prefix for the volume name.

    Returns:
      str: A name for the volume.

    Raises:
      ValueError: If the volume name does not comply with the RegEx.
    """

    # Max length of tag values in AWS is 255 characters
    user_id = self.GetAccountInformation('UserId')
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
          volume_name_prefix,
          snapshot.name[:truncate_at],  # type: ignore
          volume_id_crc32)
    else:
      volume_name = '{0:s}-{1:s}-copy'.format(
          snapshot.name[:truncate_at], volume_id_crc32)  # type: ignore

    return volume_name

  def _GetBootVolumeConfigByAmi(self,
                                ami: str,
                                boot_volume_size: int) -> Dict[str, Any]:
    """Return a boot volume configuration for a given AMI and boot volume size.

    Args:
      ami (str): The Amazon Machine Image ID.
      boot_volume_size (int): Size of the boot volume, in GB.

    Returns:
      Dict[str, str|Dict]]: A BlockDeviceMappings configuration for the
          specified AMI.

    Raises:
      RuntimeError: If AMI details cannot be found.
    """

    client = self.ClientApi(common.EC2_SERVICE)
    try:
      image = client.describe_images(ImageIds=[ami])
    except client.exceptions.ClientError as exception:
      raise RuntimeError(
          'Could not find image information for AMI {0:s}: {1:s}'.format(
              ami, str(exception)))

    # If the call to describe_images was successful, then the API's response
    # is expected to contain at least one image and its corresponding block
    # device mappings information.
    # pylint: disable=line-too-long
    block_device_mapping = image['Images'][0]['BlockDeviceMappings'][0]  # type: Dict[str, Any]
    # pylint: enable=line-too-long
    block_device_mapping['Ebs']['VolumeSize'] = boot_volume_size
    return block_device_mapping
