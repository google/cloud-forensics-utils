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
"""Demo CLI tool for Azure."""

from typing import TYPE_CHECKING

from libcloudforensics.providers.azure.internal import account
from libcloudforensics.providers.azure import forensics

if TYPE_CHECKING:
  import argparse


def ListInstances(args: 'argparse.Namespace') -> None:
  """List instances in Azure subscription.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """

  az_account = account.AZAccount(args.subscription_id)
  instances = az_account.ListInstances(
      resource_group_name=args.resource_group_name)

  print('Instances found:')
  for instance in instances:
    boot_disk = instances[instance].GetBootDisk().name
    print('Name: {0:s}, Boot disk: {1:s}'.format(instance, boot_disk))


def ListDisks(args: 'argparse.Namespace') -> None:
  """List disks in Azure subscription.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """

  az_account = account.AZAccount(args.subscription_id)
  disks = az_account.ListDisks(resource_group_name=args.resource_group_name)

  print('Disks found:')
  for disk in disks:
    print('Name: {0:s}, Region: {1:s}'.format(disk, disks[disk].region))


def CreateDiskCopy(args: 'argparse.Namespace') -> None:
  """Create an Azure disk copy.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  print('Starting disk copy...')
  disk_copy = forensics.CreateDiskCopy(args.subscription_id,
                                       args.instance_name,
                                       args.disk_name,
                                       args.disk_type)
  print('Done! Disk {0:s} successfully created.'.format(disk_copy.name))
