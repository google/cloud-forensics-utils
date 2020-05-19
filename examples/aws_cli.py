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

# Make sure that your AWS credentials are configured correclty, see
# https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html #pylint: disable=line-too-long
"""Demo script for making volume copies on AWS."""

import argparse
from datetime import datetime
from libcloudforensics import aws


def CreateVolumeCopy(args):
  """Create a AWS Volume copy.

  Args:
    args (dict): Arguments from ArgumentParser.
  """
  print('Starting volume copy...')
  volume_copy = aws.CreateVolumeCopy(
      args.zone, instance_id=args.instance_id, volume_id=args.volume_id,
      src_account=args.src_account, dst_account=args.dst_account)
  print(
      'Done! Volume {0:s} successfully created. You will find it in '
      'your AWS account under the name {1:s}.'.format(
          volume_copy.volume_id, volume_copy.name))


def LookupLogEvents(args):
  """Lookup AWS CloudTrail log events.

  Args:
    args (dict): Arguments from ArgumentParser.
  """
  ct = aws.AWSCloudTrail(
      aws.AWSAccount(default_availability_zone=args.zone))

  params = {}
  if args.filter:
    params['qfilter'] = args.filter
  if args.start:
    params['starttime'] = datetime.strptime(args.start, '%Y-%m-%d %H:%M:%S')
  if args.end:
    params['endtime'] = datetime.strptime(args.end, '%Y-%m-%d %H:%M:%S')

  result = ct.LookupEvents(**params)

  if result:
    print('Log events found: {0:d}'.format(len(result)))
    for event in result:
      print(event)


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Demo CLI tool for AWS')
  subparsers = parser.add_subparsers()

  parser_querylogs = subparsers.add_parser(
      'querylog', help='Query AWS CloudTrail logs')
  parser_querylogs.add_argument(
      'zone',
      help='The AWS zone in which resources are located, e.g. us-east-2b')
  parser_querylogs.add_argument('--filter', help='Query filter: \'value,key\'')
  parser_querylogs.add_argument('--start',
                                help='Start date for query (2020-05-01 11:13:00)',
                                default=None)
  parser_querylogs.add_argument('--end',
                                help='End date for query (2020-05-01 11:13:00)',
                                default=None)
  parser_querylogs.set_defaults(func=LookupLogEvents)

  parser_volumecopy = subparsers.add_parser(
      'copyvolume', help='Create a AWS Volume copy')
  parser_volumecopy.add_argument(
      'zone',
      help='The AWS zone in which resources are located, e.g. us-east-2b')
  parser_volumecopy.add_argument(
      '--volume_id',
      help='The AWS unique volume ID of the volume to copy. If none '
      'specified, then --instance_id must be specified and the boot '
      'volume of the AWS instance will be copied.')
  parser_volumecopy.add_argument(
      '--instance_id', help='The AWS unique instance ID')
  parser_volumecopy.add_argument(
      '--src_account', help='The name of the profile for the '
      'source account, as defined in the AWS credentials file.')
  parser_volumecopy.add_argument(
      '--dst_account', help='The name of the profile for the '
      'destination account, as defined in the AWS credentials file.')
  parser_volumecopy.set_defaults(func=CreateVolumeCopy)

  parsed_args = parser.parse_args()
  if parsed_args.func:
    parsed_args.func(parsed_args)
