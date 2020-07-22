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

from libcloudforensics import logging_utils
from libcloudforensics.providers.azure.internal import account, common

if TYPE_CHECKING:
  from libcloudforensics.providers.azure.internal import compute

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)


def CreateDiskCopy(
    resource_group_name: str,
    instance_name: Optional[str] = None,
    disk_name: Optional[str] = None,
    disk_type: str = 'Standard_LRS',
    region: str = 'eastus',
    src_profile: Optional[str] = None,
    dst_profile: Optional[str] = None) -> 'compute.AZDisk':
  """Creates a copy of an Azure Compute Disk.

  Args:
    resource_group_name (str): The resource group in which to create the disk
        copy.
    instance_name (str): Optional. Instance name of the instance using the
        disk to be copied. If specified, the boot disk of the instance will be
        copied. If disk_name is also specified, then the disk pointed to by
        disk_name will be copied.
    disk_name (str): Optional. Name of the disk to copy. If not set,
        then instance_name needs to be set and the boot disk will be copied.
    disk_type (str): Optional. The sku name for the disk to create. Can be
        Standard_LRS, Premium_LRS, StandardSSD_LRS, or UltraSSD_LRS. The
        default value is Standard_LRS.
    region (str): Optional. The region in which to create the disk copy.
        Default is eastus.
    src_profile (str): Optional. The name of the source profile to use for the
        disk copy, i.e. the account information of the Azure account that holds
        the disk. For more information on profiles, see GetCredentials()
        in libcloudforensics.providers.azure.internal.common.py. If not
        provided, credentials will be gathered from environment variables.
    dst_profile (str): Optional. The name of the destination profile to use for
        the disk copy. The disk will be copied into the account linked to
        this profile. If not provided, the default behavior is that the
        destination profile is the same as the source profile.
        For more information on profiles, see GetCredentials() in
        libcloudforensics.providers.azure.internal.common.py

  Returns:
    AZDisk: An Azure Compute Disk object.

  Raises:
    RuntimeError: If there are errors copying the disk.
    ValueError: If both instance_name and disk_name are missing.
  """

  if not instance_name and not disk_name:
    raise ValueError(
        'You must specify at least one of [instance_name, disk_name].')

  src_account = account.AZAccount(
      resource_group_name, default_region=region, profile_name=src_profile)
  dst_account = account.AZAccount(resource_group_name,
                                  default_region=region,
                                  profile_name=(dst_profile or src_profile))

  try:
    if disk_name:
      disk_to_copy = src_account.GetDisk(disk_name)
    elif instance_name:
      instance = src_account.GetInstance(instance_name)
      disk_to_copy = instance.GetBootDisk()
    logger.info('Disk copy of {0:s} started...'.format(
        disk_to_copy.name))
    snapshot = disk_to_copy.Snapshot()

    subscription_ids = src_account.ListSubscriptionIDs()
    diff_account = dst_account.subscription_id not in subscription_ids
    diff_region = dst_account.default_region != snapshot.region

    # If the destination account is different from the source account or if the
    # destination region is different from the region in which the source
    # disk is, then we need to create the disk from a storage account in
    # which we import the previously created snapshot (cross-region/account
    # sharing).
    if diff_account or diff_region:
      logger.info('Copy requested in a different destination account/region.')
      # Create a link to download the snapshot
      snapshot_uri = snapshot.GrantAccessAndGetURI()
      # Make a snapshot copy in the destination account from the link
      new_disk = dst_account.CreateDiskFromSnapshotURI(
          snapshot,
          snapshot_uri,
          disk_name_prefix=common.DEFAULT_DISK_COPY_PREFIX,
          disk_type=disk_type)
      # Revoke download link and delete the initial copy
      snapshot.RevokeAccessURI()
    else:
      new_disk = dst_account.CreateDiskFromSnapshot(
          snapshot,
          disk_name_prefix=common.DEFAULT_DISK_COPY_PREFIX,
          disk_type=disk_type)
    snapshot.Delete()
    logger.info('Disk {0:s} successfully copied to {1:s}'.format(
        disk_to_copy.name, new_disk.name))
  except RuntimeError as exception:
    error_msg = 'Cannot copy disk "{0:s}": {1!s}'.format(
        str(disk_name), str(exception))
    raise RuntimeError(error_msg)

  return new_disk
