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

import os
from datetime import datetime
from typing import TYPE_CHECKING
from Crypto.PublicKey import RSA

from libcloudforensics import logging_utils
from libcloudforensics.providers.azure.internal import account
from libcloudforensics.providers.azure.internal import monitoring
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
  instances = az_account.compute.ListInstances(
      resource_group_name=args.resource_group_name)

  logger.info('Instances found:')
  for instance in instances.values():
    boot_disk = instance.GetBootDisk()
    logger.info(
        'Name: {0:s}, Boot disk: {1:s}'.format(instance.name, boot_disk.name))


def ListDisks(args: 'argparse.Namespace') -> None:
  """List disks in Azure subscription.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """

  az_account = account.AZAccount(args.default_resource_group_name)
  disks = az_account.compute.ListDisks(
      resource_group_name=args.resource_group_name)

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
  logger.info(
      'Done! Disk {0:s} successfully created. You will find it in '
      'your Azure subscription under the name {1:s}.'.format(
          disk_copy.resource_id, disk_copy.name))


def StartAnalysisVm(args: 'argparse.Namespace') -> None:
  """Start forensic analysis VM.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  attach_disks = []
  if args.attach_disks:
    attach_disks = args.attach_disks.split(',')
    # Check if attach_disks parameter exists and if there
    # are any empty entries.
    if not (attach_disks and all(elements for elements in attach_disks)):
      logger.error('error: parameter --attach_disks: {0:s}'.format(
          args.attach_disks))
      return

  ssh_public_key = args.ssh_public_key
  if not ssh_public_key:
    # According to https://docs.microsoft.com/cs-cz/samples/azure-samples/
    # resource-manager-python-template-deployment/resource-manager-python-
    # template-deployment/ there's no API to generate a new SSH key pair in
    # Azure, so we do this manually...
    ssh_public_key = _GenerateSSHKeyPair(args.instance_name)

  logger.info('Starting analysis VM...')
  vm = forensics.StartAnalysisVm(args.default_resource_group_name,
                                 args.instance_name,
                                 int(args.disk_size),
                                 ssh_public_key,
                                 cpu_cores=int(args.cpu_cores),
                                 memory_in_mb=int(args.memory_in_mb),
                                 region=args.region,
                                 attach_disks=attach_disks,
                                 dst_profile=args.dst_profile)

  logger.info('Analysis VM started.')
  logger.info('Name: {0:s}, Started: {1:s}'.format(vm[0].name, str(vm[1])))


def _GenerateSSHKeyPair(vm_name: str) -> str:
  """Generate a SSH key pair and returns its public key.

  Both public and private keys will be saved in the current directory.

  Args:
    vm_name (str): The VM name for which to generate the key pair.

  Returns:
    str: The public key for the generated SSH key pair.

  Raises:
    ValueError: If vm_name is None.
  """
  if not vm_name:
    raise ValueError('Parameter vm_name must not be None.')

  logger.info('Generating a new SSH key pair for VM: {0:s}'.format(vm_name))

  key = RSA.generate(2048)
  key_name = '{0:s}-ssh'.format(vm_name)

  public_key = key.publickey().exportKey('OpenSSH')
  path_public_key = os.path.join(os.getcwd(), key_name + '.pub')

  private_key = key.exportKey('PEM')
  path_private_key = os.path.join(os.getcwd(), key_name + '.pem')

  with open(path_private_key, 'wb') as f:
    f.write(private_key)
  with open(path_public_key, 'wb') as f:
    f.write(public_key)

  logger.info('SSH key pair generated. Public key saved in {0:s}, private key '
              'saved in {1:s}'.format(path_public_key, path_private_key))

  return public_key.decode('utf-8')


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
      raise RuntimeError(
          'Cannot parse date: {0!s}'.format(exception)) from exception
  metrics = az_monitoring.GetMetricsForResource(
      args.resource_id,
      metrics=args.metrics,
      from_date=from_date,
      to_date=to_date,
      interval=args.interval,
      aggregation=args.aggregation or 'Total',
      qfilter=args.qfilter)

  for metric, metric_value in metrics.items():
    logger.info('Metric: {0:s}'.format(metric))
    for timestamp, value in metric_value.items():
      logger.info('  Timestamp: {0:s}, value: {1:s}'.format(timestamp, value))
