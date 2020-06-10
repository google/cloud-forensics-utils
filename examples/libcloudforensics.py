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
"""CLI tools for libcloudforensics"""

import sys

import argparse
from typing import Tuple, List, Union, Optional

from examples import aws_cli, gcp_cli


PROVIDER_TO_FUNC = {
    'aws': {
        'listinstances': aws_cli.ListInstances,
        'listdisks': aws_cli.ListVolumes,
        'copydisk': aws_cli.CreateVolumeCopy,
        'querylogs': aws_cli.QueryLogs
    },
    'gcp': {
        'listinstances': gcp_cli.ListInstances,
        'listdisks': gcp_cli.ListDisks,
        'copydisk': gcp_cli.CreateDiskCopy,
        'querylogs': gcp_cli.QueryLogs,
        'listlogs': gcp_cli.ListLogs
    }
}


def AddParser(
    provider: str,
    # pylint: disable=protected-access
    provider_parser: argparse._SubParsersAction,
    # pylint: enable=protected-access
    func: str,
    func_helper: str,
    args: Optional[List[Tuple[str, str, Optional[str]]]] = None) -> None:
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
        add to the parser, a helper text (str), and a default value (str or
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
      kwargs = {'help': helper_text, 'default': default_value}
      func_parser.add_argument(argument, **kwargs)  # type: ignore
  func_parser.set_defaults(func=PROVIDER_TO_FUNC[provider][func])


def Main() -> None:
  """Main function for libcloudforensics CLI."""

  parser = argparse.ArgumentParser(description='CLI tool for AWS and GCP.')
  subparsers = parser.add_subparsers()

  aws_parser = subparsers.add_parser('aws', help='Tools for AWS')
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
                                  'file.', None)
            ])
  AddParser('aws', aws_subparsers, 'querylogs', 'Query AWS CloudTrail logs',
            args=[
                ('--filter', 'Query filter: \'value,key\'', ''),
                ('--start', 'Start date for query (2020-05-01 11:13:00)', None),
                ('--end', 'End date for query (2020-05-01 11:13:00)', None)
            ])

  # GCP parser options
  gcp_parser.add_argument('project', help='Source GCP project.')
  gcp_subparsers = gcp_parser.add_subparsers()
  AddParser('gcp', gcp_subparsers, 'listinstances',
            'List GCE instances in GCP project.')
  AddParser('gcp', gcp_subparsers, 'listdisks',
            'List GCE disks in GCP project.')
  AddParser('gcp', gcp_subparsers, 'copydisk', 'Create a GCP disk copy.',
            args=[
                ('dstproject', 'Destination GCP project.', ''),
                ('instancename', 'Name of the instance to copy disk from.', ''),
                ('zone', 'Zone to create the disk in.', '')
            ])
  AddParser('gcp', gcp_subparsers, 'querylogs', 'Query GCP logs.',
            args=[
                ('--filter', 'Query filter.', None)
            ])
  AddParser('gcp', gcp_subparsers, 'listlogs', 'List GCP logs for a project.')

  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)

  parsed_args = parser.parse_args()

  if hasattr(parsed_args, 'func'):
    parsed_args.func(parsed_args)


if __name__ == '__main__':
  Main()
