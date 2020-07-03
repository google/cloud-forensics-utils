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
"""Forensics on Azure."""

from typing import TYPE_CHECKING, Optional

from libcloudforensics.providers.azure.internal import account
from libcloudforensics.providers.azure.internal import common

if TYPE_CHECKING:
  from libcloudforensics.providers.azure.internal import compute


def CreateDiskCopy(
    subscription_id: str,
    instance_name: Optional[str] = None,
    disk_name: Optional[str] = None,
    disk_type: str = 'Standard_LRS') -> 'compute.AZDisk':
  """Creates a copy of an Azure Compute Disk.

  Args:
    subscription_id (str): The Azure subscription ID to use.
    instance_name (str): Optional. Instance name of the instance using the
        disk to be copied. If specified, the boot disk of the instance will be
        copied. If disk_name is also specified, then the disk pointed to by
        disk_name will be copied.
    disk_name (str): Optional. Name of the disk to copy. If not set,
        then instance_name needs to be set and the boot disk will be copied.
    disk_type (str): Optional. The sku name for the disk to create. Can be
          Standard_LRS, Premium_LRS, StandardSSD_LRS, or UltraSSD_LRS. The
          default value is Standard_LRS.

  Returns:
    AZDisk: An Azure Compute Disk object.

  Raises:
    RuntimeError: If there are errors copying the disk.
    ValueError: If both instance_name and disk_name are missing.
  """

  if not instance_name and not disk_name:
    raise ValueError(
        'You must specify at least one of [instance_name, disk_name].')

  az_account = account.AZAccount(subscription_id)

  try:
    if disk_name:
      disk_to_copy = az_account.GetDisk(disk_name)
    elif instance_name:
      instance = az_account.GetInstance(instance_name)
      disk_to_copy = instance.GetBootDisk()
    common.LOGGER.info('Disk copy of {0:s} started...'.format(
        disk_to_copy.name))
    snapshot = disk_to_copy.Snapshot()
    new_disk = az_account.CreateDiskFromSnapshot(
        snapshot,
        disk_name_prefix=common.DEFAULT_DISK_COPY_PREFIX,
        disk_type=disk_type)
    snapshot.Delete()
    common.LOGGER.info(
        'Disk {0:s} successfully copied to {1:s}'.format(
            disk_to_copy.name, new_disk.name))
  except RuntimeError as exception:
    error_msg = 'Cannot copy disk "{0:s}": {1!s}'.format(
        str(disk_name), str(exception))
    raise RuntimeError(error_msg)

  return new_disk
