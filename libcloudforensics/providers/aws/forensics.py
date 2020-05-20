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
"""Forensics implementation."""
from libcloudforensics.providers.aws.internal.common import UBUNTU_1804_AMI, LOGGER  # pylint: disable=line-too-long
from libcloudforensics.providers.aws.internal import account
from libcloudforensics.providers import forensics_interface


class AWSForensics(forensics_interface.Forensics):
  """Concrete implementation of the forensics interface."""

  # pylint: disable=arguments-differ
  def CreateDiskCopy(self,
                     zone,
                     instance_id=None,
                     volume_id=None,
                     src_account=None,
                     dst_account=None):
    """Create a copy of an AWS EBS Volume.

    By default, the volume copy will be created in the same AWS account where
    the source volume sits. If you want the volume copy to be created in a
    different AWS account, you can specify one in the dst_account parameter.
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
        zone, instance_id='instance_id', dst_account='forensics')

    # Copies the boot volume from instance "instance_id" from the
    # 'investigation' AWS account to the 'forensics' AWS account.
    volume_copy = CreateDiskCopy(
        zone,
        instance_id='instance_id',
        src_account='investigation',
        dst_account='forensics')

    Args:
      zone (str): The zone within the region to create the new resource in.
      instance_id (str): Optional. Instance ID of the instance using the volume
          to be copied. If specified, the boot volume of the instance will be
          copied. If volume_id is also specified, then the volume pointed by
          that volume_id will be copied.
      volume_id (str): Optional. ID of the volume to copy. If not set,
          then instance_id needs to be set and the boot volume will be copied.
      src_account (str): Optional. If the AWS account containing the volume
          that needs to be copied is different from the default account
          specified in the AWS credentials file, then you can specify it here
          (see example above).
      dst_account (str): Optional. If the volume copy needs to be created in a
          different AWS account, you can specify it here (see example above).

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

    source_account = account.AWSAccount(zone, aws_profile=src_account)
    destination_account = account.AWSAccount(zone, aws_profile=dst_account)
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
          temporary_snapshot = snapshot.Copy(kms_key_id=kms_key_id)
          # Delete the initial snapshot
          snapshot.Delete()
          snapshot = temporary_snapshot
        snapshot.ShareWithAWSAccount(destination_account_id)

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

  # pylint: disable=arguments-differ
  def StartAnalysisVm(self,
                      vm_name,
                      default_availability_zone,
                      boot_volume_size,
                      cpu_cores=4,
                      ami=UBUNTU_1804_AMI,
                      attach_volume=None,
                      device_name=None,
                      dst_account=None):
    """Start a virtual machine for analysis purposes.

    Look for an existing AWS instance with tag name vm_name. If found,
    this instance will be started and used as analysis VM. If not found, then a
    new vm with that name will be created, started and returned.

    Args:
      vm_name (str): The name for the virtual machine.
      default_availability_zone (str): Default zone within the region to create
          new resources in.
      boot_volume_size (int): The size of the analysis VM boot volume (in GB).
      cpu_cores (int): Optional. The number of CPU cores to create the machine
          with. Default is 4.
      ami (str): Optional. The Amazon Machine Image ID to use to create the VM.
          Default is a version of Ubuntu 18.04.
      attach_volume (AWSVolume): Optional. The volume to attach.
      device_name (str): Optional. The name of the device (e.g. /dev/sdf) for
          the volume to be attached. Mandatory if attach_volume is provided.
      dst_account (str): Optional. The AWS account in which to create the
          analysis VM. This is the profile name that is defined in your AWS
          credentials file.

    Returns:
      tuple(AWSInstance, bool): a tuple with a virtual machine object
          and a boolean indicating if the virtual machine was created or not.

    Raises:
      RuntimeError: If device_name is missing when attach_volume is provided.
    """
    aws_account = account.AWSAccount(
        default_availability_zone, aws_profile=dst_account)
    analysis_vm, created = aws_account.GetOrCreateAnalysisVm(
        vm_name, boot_volume_size, cpu_cores=cpu_cores, ami=ami)
    if attach_volume:
      if not device_name:
        raise RuntimeError('If you want to attach a volume, you must also '
                           'specify a device name for that volume.')
      analysis_vm.AttachVolume(attach_volume, device_name)
    return analysis_vm, created
