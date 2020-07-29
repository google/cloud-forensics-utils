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

# Make sure that your AWS/GCP  credentials are configured correclty
"""CLI tools for libcloudforensics."""

import argparse
import sys

from typing import Tuple, List, Optional, Any, Dict
from examples import aws_cli, az_cli, gcp_cli

PROVIDER_TO_FUNC = {
    'aws': {
        'copydisk': aws_cli.CreateVolumeCopy,
        'listimages': aws_cli.ListImages,
        'listinstances': aws_cli.ListInstances,
        'listdisks': aws_cli.ListVolumes,
        'querylogs': aws_cli.QueryLogs,
        'startvm': aws_cli.StartAnalysisVm
    },
    'az': {
        'copydisk': az_cli.CreateDiskCopy,
        'listinstances': az_cli.ListInstances,
        'listdisks': az_cli.ListDisks
    },
    'gcp': {
        'copydisk': gcp_cli.CreateDiskCopy,
        'creatediskgcs': gcp_cli.CreateDiskFromGCSImage,
        'listdisks': gcp_cli.ListDisks,
        'listinstances': gcp_cli.ListInstances,
        'listlogs': gcp_cli.ListLogs,
        'listservices': gcp_cli.ListServices,
        'querylogs': gcp_cli.QueryLogs,
        'startvm': gcp_cli.StartAnalysisVm,
        'bucketacls': gcp_cli.GetBucketACLs,
        'objectmetadata': gcp_cli.GetGCSObjectMetadata,
        'listobjects': gcp_cli.ListBucketObjects
    }
}


def AddParser(
    provider: str,
    # pylint: disable=protected-access
    provider_parser: argparse._SubParsersAction,
    # pylint: enable=protected-access
    func: str,
    func_helper: str,
    args: Optional[List[Tuple[str, str, Optional[Any]]]] = None) -> None:
  """Create a new parser object for a provider's functionality.

  Args:
    provider (str): The cloud provider offering the function. This should be
        one of ['aws', 'gcp'].
    provider_parser (_SubParsersAction): A provider's subparser object from
        argparse.ArgumentParser.
    func (str): The name of the function to look for in the given provider
        and to add parsing options for.
    func_helper (str): A helper text describing what the function does.
    args (List[Tuple]): Optional. A list of arguments to add
        to the parser. Each argument is a tuple containing the action (str) to
        add to the parser, a helper text (str), and a default value (Any or
        None).

  Raises:
    NotImplementedError: If the requested provider or function is not
        implemented.
  """
  if provider not in PROVIDER_TO_FUNC:
    raise NotImplementedError('Requested provider is not implemented')
  if func not in PROVIDER_TO_FUNC[provider]:
    raise NotImplementedError('Requested functionality {0:s} is not '
                              'implemented for provider {1:s}'.format(
                                  func, provider))
  func_parser = provider_parser.add_parser(func, help=func_helper)
  if args:
    for argument, helper_text, default_value in args:
      kwargs = {'help': helper_text}  # type: Dict[str, Any]
      if isinstance(default_value, bool):
        kwargs['action'] = 'store_true'
      else:
        kwargs['default'] = default_value
      func_parser.add_argument(argument, **kwargs)  # type: ignore
  func_parser.set_defaults(func=PROVIDER_TO_FUNC[provider][func])


def Main() -> None:
  """Main function for libcloudforensics CLI."""

  parser = argparse.ArgumentParser(description='CLI tool for AWS and GCP.')
  subparsers = parser.add_subparsers()

  aws_parser = subparsers.add_parser('aws', help='Tools for AWS')
  az_parser = subparsers.add_parser('az', help='Tools for Azure')
  gcp_parser = subparsers.add_parser('gcp', help='Tools for GCP')

  # AWS parser options
  aws_parser.add_argument('zone', help='The AWS zone in which resources are '
                                       'located, e.g. us-east-2b')
  aws_subparsers = aws_parser.add_subparsers()
  AddParser('aws', aws_subparsers, 'listinstances',
            'List EC2 instances in AWS account.')
  AddParser('aws', aws_subparsers, 'listdisks',
            'List EBS volumes in AWS account.')
  AddParser('aws', aws_subparsers, 'copydisk', 'Create an AWS volume copy.',
            args=[
                ('--dst_zone', 'The AWS zone in which to copy the volume. By '
                               'default this is the same as "zone".',
                 None),
                ('--instance_id', 'The AWS unique instance ID', None),
                ('--volume_id', 'The AWS unique volume ID of the volume to '
                                'copy. If none specified, then --instance_id '
                                'must be specified and the boot volume of the '
                                'AWS instance will be copied.', None),
                ('--src_profile', 'The name of the profile for the source '
                                  'account, as defined in the AWS credentials '
                                  'file.', None),
                ('--dst_profile', 'The name of the profile for the destination '
                                  'account, as defined in the AWS credentials '
                                  'file.', None),
                ('--tags', 'A string dictionary of tags to add to the volume '
                           'copy. ', None)
            ])
  AddParser('aws', aws_subparsers, 'querylogs', 'Query AWS CloudTrail logs',
            args=[
                ('--filter', 'Query filter: \'value,key\'', ''),
                ('--start', 'Start date for query (2020-05-01 11:13:00)', None),
                ('--end', 'End date for query (2020-05-01 11:13:00)', None)
            ])
  AddParser('aws', aws_subparsers, 'startvm', 'Start a forensic analysis VM.',
            args=[
                ('instance_name', 'Name of EC2 instance to re-use or create.',
                 ''),
                ('--boot_volume_size', 'Size of instance boot volume in GB.',
                 '50'),
                ('--cpu_cores', 'Instance CPU core count.', '4'),
                ('--ami', 'AMI ID to use as base image. Will search '
                          'Ubuntu 18.04 LTS server x86_64 for chosen region '
                          'by default.', ''),
                ('--ssh_key_name', 'SSH key pair name. This is the name of an '
                                   'existing SSH key pair in the AWS account '
                                   'where the VM will live. Alternatively, '
                                   'use --generate_ssh_key_pair to create a '
                                   'new key pair in the AWS account.', None),
                ('--generate_ssh_key_pair', 'Generate a new SSH key pair in '
                                            'the AWS account where the '
                                            'analysis VM will be created. '
                                            'Returns the private key at the '
                                            'end of the process. '
                                            'Takes precedence over '
                                            '--ssh_key_name', False),
                ('--attach_volumes', 'Comma separated list of volume IDs '
                                     'to attach. Maximum of 11.', None),
                ('--dst_profile', 'The name of the profile for the destination '
                                  'account, as defined in the AWS credentials '
                                  'file.', None)
            ])
  AddParser('aws', aws_subparsers, 'listimages', 'List AMI images.',
            args=[
                ('--filter', 'Filter to apply to Name of AMI image.', None),
            ])

  # Azure parser options
  az_parser.add_argument('default_resource_group_name',
                         help='The default resource group name in which to '
                              'create resources')
  az_subparsers = az_parser.add_subparsers()
  AddParser('az', az_subparsers, 'listinstances',
            'List instances in Azure subscription.',
            args=[
                ('--resource_group_name', 'The resource group name from '
                                          'which to list instances.', None)
            ])
  AddParser('az', az_subparsers, 'listdisks',
            'List disks in Azure subscription.',
            args=[
                ('--resource_group_name', 'The resource group name from '
                                          'which to list disks.', None)
            ])
  AddParser('az', az_subparsers, 'copydisk', 'Create an Azure disk copy.',
            args=[
                ('--instance_name', 'The instance name.', None),
                ('--disk_name', 'The name of the disk to copy. If none '
                                'specified, then --instance_name must be '
                                'specified and the boot disk of the Azure '
                                'instance will be copied.', None),
                ('--disk_type', 'The SKU name for the disk to create. '
                                'Can be Standard_LRS, Premium_LRS, '
                                'StandardSSD_LRS, or UltraSSD_LRS. Default is '
                                'Standard_LRS', 'Standard_LRS'),
                ('--region', 'The region in which to create the disk copy. If '
                             'not provided, the disk copy will be created in '
                             'the "eastus" region.', 'eastus'),
                ('--src_profile', 'The Azure profile information to use as '
                                  'source account for the disk copy. Default '
                                  'will look into environment variables to '
                                  'authenticate the requests.', None),
                ('--dst_profile', 'The Azure profile information to use as '
                                  'destination account for the disk copy. If '
                                  'not provided, the default behavior is to '
                                  'use the same destination profile as the '
                                  'source profile.', None)
            ])

  # GCP parser options
  gcp_parser.add_argument('project', help='GCP project ID.')
  gcp_subparsers = gcp_parser.add_subparsers()
  AddParser('gcp', gcp_subparsers, 'listinstances',
            'List GCE instances in GCP project.')
  AddParser('gcp', gcp_subparsers, 'listdisks',
            'List GCE disks in GCP project.')
  AddParser('gcp', gcp_subparsers, 'copydisk', 'Create a GCP disk copy.',
            args=[
                ('dst_project', 'Destination GCP project.', ''),
                ('zone', 'Zone to create the disk in.', ''),
                ('--instance_name', 'Name of the instance to copy disk from.',
                 ''),
                ('--disk_name', 'Name of the disk to copy. If none specified, '
                                'then --instance_name must be specified and '
                                'the boot disk of the instance will be copied.',
                 None)
            ])
  AddParser('gcp', gcp_subparsers, 'startvm', 'Start a forensic analysis VM.',
            args=[
                ('instance_name', 'Name of the GCE instance to create.',
                 ''),
                ('zone', 'Zone to create the instance in.', ''),
                ('--disk_size', 'Size of disk in GB.', '50'),
                ('--disk_type', 'Type of disk.', 'pd-ssd'),
                ('--cpu_cores', 'Instance CPU core count.', '4'),
                ('--attach_disks', 'Comma seperated list of disk names '
                                   'to attach.', None)
            ])
  AddParser('gcp', gcp_subparsers, 'querylogs', 'Query GCP logs.',
            args=[
                ('--filter', 'Query filter', None),
                ('--start', 'Start date for query (2020-05-01T11:13:00Z)',
                 None),
                ('--end', 'End date for query (2020-05-01T11:13:00Z)', None)
            ])
  AddParser('gcp', gcp_subparsers, 'listlogs', 'List GCP logs for a project.')
  AddParser('gcp', gcp_subparsers, 'listservices',
            'List active services for a project.')
  AddParser('gcp', gcp_subparsers, 'creatediskgcs', 'Creates GCE persistent '
                                                    'disk from image in GCS.',
            args=[('gcs_path', 'Path to the source image in GCS.', ''),
                  ('zone', 'Zone to create the disk in.', ''),
                  ('--disk_name',
                   'Name of the disk to create. If None, name '
                   'will be printed at the end.',
                   None)])
  AddParser('gcp', gcp_subparsers, 'bucketacls', 'List ACLs of a GCS bucket.',
            args=[
                ('path', 'Path to bucket.', None),
            ])
  AddParser('gcp', gcp_subparsers, 'objectmetadata', 'List the details of an '
                                                     'object in a GCS bucket.',
            args=[
                ('path', 'Path to object.', None)
            ])
  AddParser('gcp', gcp_subparsers, 'listobjects', 'List the objects in a '
                                                  'GCS bucket.',
            args=[
                ('path', 'Path to bucket.', None),
            ])

  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)

  parsed_args = parser.parse_args()

  if hasattr(parsed_args, 'func'):
    parsed_args.func(parsed_args)


if __name__ == '__main__':
  Main()
