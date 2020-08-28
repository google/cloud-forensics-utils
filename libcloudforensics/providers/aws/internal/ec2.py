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

import binascii
import os
from typing import TYPE_CHECKING, Dict, Optional, List, Any, Tuple

import botocore
from libcloudforensics import errors
from libcloudforensics.scripts import utils

from libcloudforensics.providers.aws.internal import common

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
      ResourceNotFoundError: If no boot volume could be found.
    """

    boot_device = self.aws_account.ResourceApi(
        common.EC2_SERVICE).Instance(self.instance_id).root_device_name
    volumes = self.ListVolumes()

    for volume_id in volumes:
      if volumes[volume_id].device_name == boot_device:
        return volumes[volume_id]

    raise errors.ResourceNotFoundError(
        'Boot volume not found for instance: {0:s}'.format(self.instance_id),
        __name__)

  def GetVolume(self, volume_id: str) -> 'ebs.AWSVolume':
    """Get a volume attached to the instance by ID.

    Args:
      volume_id (str): The ID of the volume to get.

    Returns:
      AWSVolume: The AWSVolume object.

    Raises:
      ResourceNotFoundError: If volume_id is not found amongst the volumes
          attached to the instance.
    """

    volume = self.ListVolumes().get(volume_id)
    if not volume:
      raise errors.ResourceNotFoundError(
          'Volume {0:s} is not attached to instance {1:s}'.format(
              volume_id, self.instance_id), __name__)
    return volume

  def ListVolumes(self) -> Dict[str, 'ebs.AWSVolume']:
    """List all volumes for the instance.

    Returns:
      Dict[str, AWSVolume]: Dictionary mapping volume IDs to their respective
          AWSVolume object.
    """

    return self.aws_account.ebs.ListVolumes(
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

    client = self.aws_account.ClientApi(common.EC2_SERVICE)
    try:
      client.attach_volume(Device=device_name,
                           InstanceId=self.instance_id,
                           VolumeId=volume.volume_id)
    except client.exceptions.ClientError as exception:
      raise RuntimeError('Could not attach volume {0:s}: {1:s}'.format(
          volume.volume_id, str(exception))) from exception

    volume.device_name = device_name


class EC2:
  """Class that represents AWS EC2 instance services."""

  def __init__(self,
               aws_account: 'account.AWSAccount') -> None:
    """Initialize the AWS ec2 client object.

    Args:
      aws_account (AWSAccount): An AWS account object.
    """
    self.aws_account = aws_account

  def ListInstances(
      self,
      region: Optional[str] = None,
      filters: Optional[List[Dict[str, Any]]] = None,
      show_terminated: bool = False) -> Dict[str, AWSInstance]:
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
    client = self.aws_account.ClientApi(common.EC2_SERVICE, region=region)
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
          aws_instance = AWSInstance(
              self.aws_account, instance_id, zone[:-1], zone)

          for tag in instance.get('Tags', []):
            if tag.get('Key') == 'Name':
              aws_instance.name = tag.get('Value')
              break

          instances[instance_id] = aws_instance
    return instances

  def GetInstancesByNameOrId(
      self,
      instance_name: Optional[str] = None,
      instance_id: Optional[str] = None,
      region: Optional[str] = None) -> List[AWSInstance]:
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
                       '{1:s}'.format(str(instance_name), str(instance_id)))
    if instance_name:
      return self.GetInstancesByName(instance_name, region=region)
    # mypy complains that instance_id may be None here, but at this point in the
    # code it never is, so it's safe to ignore the warning.
    return [self.GetInstanceById(instance_id, region=region)]  # type: ignore

  def GetInstancesByName(self,
                         instance_name: str,
                         region: Optional[str] = None) -> List[AWSInstance]:
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

    instances = self.ListInstances(region=region)
    return [instance for instance in instances.values() if
            instance.name == instance_name]

  def GetInstanceById(self,
                      instance_id: str,
                      region: Optional[str] = None) -> AWSInstance:
    """Get an instance from an AWS account by its ID.

    Args:
      instance_id (str): The instance id.
      region (str): Optional. The region to look the instance in.
          If none provided, the default_region associated to the AWSAccount
          object will be used.

    Returns:
      AWSInstance: An Amazon EC2 Instance object.

    Raises:
      ResourceNotFoundError: If instance does not exist.
    """

    instances = self.ListInstances(region=region)
    instance = instances.get(instance_id)
    if not instance:
      raise errors.ResourceNotFoundError(
          'Instance {0:s} was not found in AWS account'.format(instance_id),
          __name__)
    return instance

  def ListImages(
      self,
      qfilter: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """List AMI images.

    Args:
      qfilter (List[Dict]): The filter expression.
      See https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_images  # pylint: disable=line-too-long

    Returns:
      List[Dict[str, Any]]: The list of images with their properties.

    Raises:
      RuntimeError: If the images could not be listed.
    """
    if not qfilter:
      qfilter = []

    client = self.aws_account.ClientApi(common.EC2_SERVICE)
    try:
      images = client.describe_images(
          Filters=qfilter)  # type: Dict[str, List[Dict[str, Any]]]
    except client.exceptions.ClientError as exception:
      raise RuntimeError(str(exception)) from exception

    return images['Images']

  def GetOrCreateAnalysisVm(
      self,
      vm_name: str,
      boot_volume_size: int,
      ami: str,
      cpu_cores: int,
      boot_volume_type: str = 'gp2',
      packages: Optional[List[str]] = None,
      ssh_key_name: Optional[str] = None,
      tags: Optional[Dict[str, str]] = None) -> Tuple[AWSInstance, bool]:
    """Get or create a new virtual machine for analysis purposes.

    Args:
      vm_name (str): The instance name tag of the virtual machine.
      boot_volume_size (int): The size of the analysis VM boot volume (in GB).
      ami (str): The Amazon Machine Image ID to use to create the VM.
      cpu_cores (int): Number of CPU cores for the analysis VM.
      boot_volume_type (str): Optional. The volume type for the boot volume
          of the VM. Can be one of 'standard'|'io1'|'gp2'|'sc1'|'st1'. The
          default is 'gp2'.
      packages (List[str]): Optional. List of packages to install in the VM.
      ssh_key_name (str): Optional. A SSH key pair name linked to the AWS
          account to associate with the VM. If none provided, the VM can only
          be accessed through in-browser SSH from the AWS management console
          with the EC2 client connection package (ec2-instance-connect). Note
          that if this package fails to install on the target VM, then the VM
          will not be accessible. It is therefore recommended to fill in this
          parameter.
      tags (Dict[str, str]): Optional. A dictionary of tags to add to the
          instance, for example {'TicketID': 'xxx'}. An entry for the instance
          name is added by default.

    Returns:
      Tuple[AWSInstance, bool]: A tuple with an AWSInstance object and a
          boolean indicating if the virtual machine was created (True) or
          reused (False).

    Raises:
      ResourceCreationError: If the virtual machine cannot be created.
    """

    # Re-use instance if it already exists, or create a new one.
    instances = self.GetInstancesByName(vm_name)
    if instances:
      created = False
      return instances[0], created

    instance_type = common.GetInstanceTypeByCPU(cpu_cores)
    startup_script = utils.ReadStartupScript()
    if packages:
      startup_script = startup_script.replace('${packages[@]}', ' '.join(
          packages))

    # Install ec2-instance-connect to allow SSH connections from the browser.
    startup_script = startup_script.replace(
        '(exit ${exit_code})',
        'apt -y install ec2-instance-connect && (exit ${exit_code})')

    if not tags:
      tags = {}
    tags['Name'] = vm_name

    client = self.aws_account.ClientApi(common.EC2_SERVICE)
    vm_args = {
        'BlockDeviceMappings':
            [self._GetBootVolumeConfigByAmi(
                ami, boot_volume_size, boot_volume_type)],
        'ImageId': ami,
        'MinCount': 1,
        'MaxCount': 1,
        'InstanceType': instance_type,
        'TagSpecifications': [common.CreateTags(common.INSTANCE, tags)],
        'UserData': startup_script,
        'Placement': {
            'AvailabilityZone': self.aws_account.default_availability_zone}
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
      raise errors.ResourceCreationError(
          'Could not create instance {0:s}: {1!s}'.format(vm_name, exception),
          __name__) from exception

    instance = AWSInstance(self.aws_account,
                           instance_id,
                           self.aws_account.default_region,
                           self.aws_account.default_availability_zone,
                           name=vm_name)
    created = True
    return instance, created

  def _GetBootVolumeConfigByAmi(self,
                                ami: str,
                                boot_volume_size: int,
                                boot_volume_type: str) -> Dict[str, Any]:
    """Return a boot volume configuration for a given AMI and boot volume size.

    Args:
      ami (str): The Amazon Machine Image ID.
      boot_volume_size (int): Size of the boot volume, in GB.
      boot_volume_type (str): Type of the boot volume.

    Returns:
      Dict[str, str|Dict]]: A BlockDeviceMappings configuration for the
          specified AMI.

    Raises:
      ResourceNotFoundError: If AMI details cannot be found.
    """

    client = self.aws_account.ClientApi(common.EC2_SERVICE)
    try:
      image = client.describe_images(ImageIds=[ami])
    except client.exceptions.ClientError as exception:
      raise errors.ResourceNotFoundError(
          'Could not find image information for AMI {0:s}: {1!s}'.format(
              ami, exception), __name__) from exception

    # If the call to describe_images was successful, then the API's response
    # is expected to contain at least one image and its corresponding block
    # device mappings information.
    # pylint: disable=line-too-long
    block_device_mapping = image['Images'][0]['BlockDeviceMappings'][0]  # type: Dict[str, Any]
    # pylint: enable=line-too-long
    block_device_mapping['Ebs']['VolumeSize'] = boot_volume_size
    block_device_mapping['Ebs']['VolumeType'] = boot_volume_type
    if boot_volume_type == 'io1':
      # If using the io1 volume type, we must specify Iops, see
      # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/
      # services/ec2.html#EC2.Client.create_volume. io1 volumes allow for a
      # ratio of 50 IOPS per 1 GiB.
      block_device_mapping['Ebs']['Iops'] = boot_volume_size * 50
    return block_device_mapping

  def GenerateSSHKeyPair(self, vm_name: str) -> Tuple[str, str]:
    """Generate a SSH key pair and returns its name and private key.

    Args:
      vm_name (str): The VM name for which to generate the key pair.

    Returns:
      Tuple[str, str]: A tuple containing the key name and the private key for
          the generated SSH key pair.

    Raises:
      ValueError: If vm_name is None.
      ResourceCreationError: If the key could not be created.
    """

    if not vm_name:
      raise ValueError('Parameter vm_name must not be None.')

    # SSH key names need to be unique, therefore we add a random 10 chars hex
    # string.
    key_name = '{0:s}-{1:s}-ssh'.format(
        vm_name, binascii.b2a_hex(os.urandom(10)).decode('utf-8'))
    client = self.aws_account.ClientApi(common.EC2_SERVICE)
    try:
      key = client.create_key_pair(KeyName=key_name)
    except client.exceptions.ClientError as exception:
      raise errors.ResourceCreationError(
          'Could not create SSH key pair: {0!s}'.format(
              exception), __name__) from exception
    # If the call was successful, the response contains key information
    return key['KeyName'], key['KeyMaterial']
