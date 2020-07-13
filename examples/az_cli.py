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

from datetime import datetime
from typing import TYPE_CHECKING

from libcloudforensics import logging_utils
from libcloudforensics.providers.azure.internal import account, monitoring
from libcloudforensics.providers.azure import forensics

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)

if TYPE_CHECKING:
  import argparse


def ListInstances(args: 'argparse.Namespace') -> None:
  """List instances in Azure subscription.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """

  az_account = account.AZAccount(args.default_resource_group_name)
  instances = az_account.ListInstances(
      resource_group_name=args.resource_group_name)

  logger.info('Instances found:')
  for instance in instances.values():
    boot_disk = instance.GetBootDisk().name
    logger.info('Name: {0:s}, Boot disk: {1:s}'.format(instance, boot_disk))


def ListDisks(args: 'argparse.Namespace') -> None:
  """List disks in Azure subscription.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """

  az_account = account.AZAccount(args.default_resource_group_name)
  disks = az_account.ListDisks(resource_group_name=args.resource_group_name)

  logger.info('Disks found:')
  for disk in disks:
    logger.info('Name: {0:s}, Region: {1:s}'.format(disk, disks[disk].region))


def CreateDiskCopy(args: 'argparse.Namespace') -> None:
  """Create an Azure disk copy.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  logger.info('Starting disk copy...')
  disk_copy = forensics.CreateDiskCopy(args.default_resource_group_name,
                                       instance_name=args.instance_name,
                                       disk_name=args.disk_name,
                                       disk_type=args.disk_type,
                                       region=args.region,
                                       src_profile=args.src_profile,
                                       dst_profile=args.dst_profile)
  logger.info('Done! Disk {0:s} successfully created.'.format(disk_copy.name))


def ListMetrics(args: 'argparse.Namespace') -> None:
  """List Azure Monitoring metrics for a resource.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  az_account = account.AZAccount(args.default_resource_group_name)
  az_monitoring = monitoring.AZMonitoring(az_account)
  metrics = az_monitoring.ListAvailableMetricsForResource(args.resource_id)
  for metric in metrics:
    logger.info('Available metric: {0:s}'.format(metric))


def QueryMetrics(args: 'argparse.Namespace') -> None:
  """Query Azure Monitoring metrics for a resource.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.

  Raises:
    RuntimeError: If from_date or to_date could not be parsed.
  """
  az_account = account.AZAccount(args.default_resource_group_name)
  az_monitoring = monitoring.AZMonitoring(az_account)
  from_date, to_date = args.from_date, args.to_date
  if from_date and to_date:
    try:
      from_date = datetime.strptime(from_date, '%Y-%m-%dT%H:%M:%SZ')
      to_date = datetime.strptime(to_date, '%Y-%m-%dT%H:%M:%SZ')
    except ValueError as exception:
      raise RuntimeError('Cannot parse date: {0:s}'.format(str(exception)))
  metrics = az_monitoring.GetMetricsForResource(
      args.resource_id,
      metrics=args.metrics,
      from_date=from_date,
      to_date=to_date,
      interval=args.interval,
      aggregation=args.aggregation or 'Total',
      qfilter=args.qfilter)

  for metric in metrics:
    logger.info('Metric: {0:s}'.format(metric))
    for value in metrics[metric]:
      logger.info('Value: {0:s}'.format(value))
