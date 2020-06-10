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
"""Forensics on AWS."""
from typing import TYPE_CHECKING, Tuple, List, Optional

from libcloudforensics.providers.aws.internal.common import UBUNTU_1804_AMI, LOGGER  # pylint: disable=line-too-long
from libcloudforensics.providers.aws.internal import account

if TYPE_CHECKING:
  from libcloudforensics.providers.aws.internal import ebs, ec2


def CreateVolumeCopy(zone: str,
                     dst_zone: Optional[str] = None,
                     instance_id: Optional[str] = None,
                     volume_id: Optional[str] = None,
                     src_profile: Optional[str] = None,
                     dst_profile: Optional[str] = None) -> 'ebs.AWSVolume':
  """Create a copy of an AWS EBS Volume.

  By default, the volume copy will be created in the same AWS account where
  the source volume sits. If you want the volume copy to be created in a
  different AWS account, you can specify one in the dst_profile parameter.
  The following example illustrates how you should configure your AWS
  credentials file for such a use case.

  # AWS credentials file
  [default] # default account to use with AWS
  aws_access_key_id=foo
  aws_secret_access_key=bar

  [investigation] # source account for a particular volume to be copied from
  aws_access_key_id=foo1
  aws_secret_access_key=bar1

  [forensics] # destination account to create the volume copy in
  aws_access_key_id=foo2
  aws_secret_access_key=bar2

  # Copies the boot volume from instance "instance_id" from the default AWS
  # account to the default AWS account.
  volume_copy = CreateDiskCopy(zone, instance_id='instance_id')

  # Copies the boot volume from instance "instance_id" from the default AWS
  # account to the 'forensics' AWS account.
  volume_copy = CreateDiskCopy(
      zone, instance_id='instance_id', dst_profile='forensics')

  # Copies the boot volume from instance "instance_id" from the
  # 'investigation' AWS account to the 'forensics' AWS account.
  volume_copy = CreateDiskCopy(
      zone,
      instance_id='instance_id',
      src_profile='investigation',
      dst_profile='forensics')

  Args:
    zone (str): The AWS zone in which the volume is located, e.g. 'us-east-2b'.
    dst_zone (str): Optional. The AWS zone in which to create the volume
        copy. By default, this is the same as 'zone'.
    instance_id (str): Optional. Instance ID of the instance using the volume
        to be copied. If specified, the boot volume of the instance will be
        copied. If volume_id is also specified, then the volume pointed by
        that volume_id will be copied.
    volume_id (str): Optional. ID of the volume to copy. If not set,
        then instance_id needs to be set and the boot volume will be copied.
    src_profile (str): Optional. If the AWS account containing the volume
        that needs to be copied is different from the default account
        specified in the AWS credentials file then you can specify a
        different profile name here (see example above).
    dst_profile (str): Optional. If the volume copy needs to be created in a
        different AWS account, you can specify a different profile name here
        (see example above).

  Returns:
    AWSVolume: An AWS EBS Volume object.

  Raises:
    RuntimeError: If there are errors copying the volume, or errors during
        KMS key creation/sharing if the target volume is encrypted.
    ValueError: If both instance_id and volume_id are missing.
  """

  if not instance_id and not volume_id:
    raise ValueError(
        'You must specify at least one of [instance_id, volume_id].')

  source_account = account.AWSAccount(zone, aws_profile=src_profile)
  destination_account = account.AWSAccount(zone, aws_profile=dst_profile)
  kms_key_id = None

  try:
    if volume_id:
      volume_to_copy = source_account.GetVolumeById(volume_id)
    elif instance_id:
      instance = source_account.GetInstanceById(instance_id)
      volume_to_copy = instance.GetBootVolume()

    LOGGER.info('Volume copy of {0:s} started...'.format(
        volume_to_copy.volume_id))
    snapshot = volume_to_copy.Snapshot()

    source_account_id = source_account.GetAccountInformation('Account')
    destination_account_id = destination_account.GetAccountInformation(
        'Account')

    if source_account_id != destination_account_id:
      if volume_to_copy.encrypted:
        # Generate one-time use KMS key that will be shared with the
        # destination account.
        kms_key_id = source_account.CreateKMSKey()
        source_account.ShareKMSKeyWithAWSAccount(
            kms_key_id, destination_account_id)
        # Create a copy of the initial snapshot and encrypts it with the
        # shared key
        snapshot = snapshot.Copy(kms_key_id=kms_key_id, delete=True)
      snapshot.ShareWithAWSAccount(destination_account_id)

    if dst_zone and dst_zone != zone:
      # Assign the new zone to the destination account and assign it to the
      # snapshot so that it can copy it
      destination_account = account.AWSAccount(
          dst_zone, aws_profile=dst_profile)
      snapshot.aws_account = destination_account
      snapshot = snapshot.Copy(delete=True, deletion_account=source_account)

    new_volume = destination_account.CreateVolumeFromSnapshot(
        snapshot, volume_name_prefix='evidence')
    snapshot.Delete()
    # Delete the one-time use KMS key, if one was generated
    source_account.DeleteKMSKey(kms_key_id)
    LOGGER.info('Volume {0:s} successfully copied to {1:s}'.format(
        volume_to_copy.volume_id, new_volume.volume_id))

  except RuntimeError as exception:
    error_msg = 'Copying volume {0:s}: {1!s}'.format(
        (volume_id or instance_id), exception)
    raise RuntimeError(error_msg)

  return new_volume


def StartAnalysisVm(
    vm_name: str,
    default_availability_zone: str,
    boot_volume_size: int,
    ami: str = UBUNTU_1804_AMI,
    cpu_cores: int = 4,
    attach_volumes: Optional[List[Tuple[str, str]]] = None,
    dst_profile: Optional[str] = None,
    ssh_key_name: Optional[str] = None) -> Tuple['ec2.AWSInstance', bool]:
  """Start a virtual machine for analysis purposes.

  Look for an existing AWS instance with tag name vm_name. If found,
  this instance will be started and used as analysis VM. If not found, then a
  new vm with that name will be created, started and returned.

  Args:
    vm_name (str): The name for the virtual machine.
    default_availability_zone (str): Default zone within the region to create
        new resources in.
    boot_volume_size (int): The size of the analysis VM boot volume (in GB).
    ami (str): Optional. The Amazon Machine Image ID to use to create the VM.
        Default is a version of Ubuntu 18.04.
    cpu_cores (int): Optional. The number of CPU cores to create the machine
        with. Default is 4.
    attach_volumes (List[Tuple[str, str]]): Optional. List of tuples
        containing the volume IDs (str) to attach and their respective device
        name (str, e.g. /dev/sdf). Note that it is mandatory to provide a
        unique device name per volume to attach.
    dst_profile (str): Optional. The AWS account in which to create the
        analysis VM. This is the profile name that is defined in your AWS
        credentials file.
    ssh_key_name (str): Optional. A SSH key pair name linked to the AWS
        account to associate with the VM. If none provided, the VM can only
        be accessed through in-browser SSH from the AWS management console
        with the EC2 client connection package (ec2-instance-connect). Note
        that if this package fails to install on the target VM, then the VM
        will not be accessible. It is therefore recommended to fill in this
        parameter.

  Returns:
    Tuple[AWSInstance, bool]: a tuple with a virtual machine object
        and a boolean indicating if the virtual machine was created or not.
  """
  aws_account = account.AWSAccount(
      default_availability_zone, aws_profile=dst_profile)
  analysis_vm, created = aws_account.GetOrCreateAnalysisVm(
      vm_name,
      boot_volume_size,
      ami,
      cpu_cores,
      ssh_key_name=ssh_key_name)
  for volume_id, device_name in (attach_volumes or []):
    analysis_vm.AttachVolume(aws_account.GetVolumeById(volume_id), device_name)
  return analysis_vm, created
