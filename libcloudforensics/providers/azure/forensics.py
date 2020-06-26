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
    instance_name: str,
    disk_name: Optional[str] = None,
    disk_type: Optional[str] = 'Standard_LRS') -> 'compute.AZDisk':
  """Creates a copy of an Azure Compute Disk.

  Args:
    subscription_id (str): The Azure subscription ID to use.
    instance_name (str): Instance name using the disk to be copied.
    disk_name (str): Optional. Name of the disk to copy. If None, boot disk
        will be copied.
    disk_type (str): Optional. The sku name for the disk to create. Can be
          Standard_LRS, Premium_LRS, StandardSSD_LRS, or UltraSSD_LRS.

  Returns:
    AZDisk: An Azure Compute Disk object.

  Raises:
    RuntimeError: If there are errors copying the disk
  """

  az_account = account.AZAccount(subscription_id)
  instance = az_account.GetInstance(instance_name) if instance_name else None

  try:
    if disk_name:
      disk_to_copy = az_account.GetDisk(disk_name)
    else:
      disk_to_copy = instance.GetBootDisk()  # type: ignore
    common.LOGGER.info('Disk copy of {0:s} started...'.format(
        disk_to_copy.name))
    snapshot = disk_to_copy.Snapshot()
    new_disk = az_account.CreateDiskFromSnapshot(
        snapshot, disk_name_prefix='evidence', disk_type=disk_type)
    snapshot.Delete()
    common.LOGGER.info(
        'Disk {0:s} successfully copied to {1:s}'.format(
            disk_to_copy.name, new_disk.name))
  except RuntimeError as exception:
    error_msg = 'Cannot copy disk "{0:s}": {1!s}'.format(disk_name, exception)
    raise RuntimeError(error_msg)

  return new_disk
