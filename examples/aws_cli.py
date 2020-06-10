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
"""Demo CLI tool for AWS."""

from datetime import datetime
from typing import TYPE_CHECKING

from libcloudforensics.providers.aws.internal import account
from libcloudforensics.providers.aws.internal import log as aws_log
from libcloudforensics.providers.aws import forensics

if TYPE_CHECKING:
  import argparse


def ListInstances(args: 'argparse.Namespace') -> None:
  """List EC2 instances in AWS account.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """

  aws_account = account.AWSAccount(args.zone)
  instances = aws_account.ListInstances()

  print('Instances found:')
  for instance in instances:
    boot_volume = instances[instance].GetBootVolume().volume_id
    print('Name: {0:s}, Boot volume: {1:s}'.format(instance, boot_volume))


def ListVolumes(args: 'argparse.Namespace') -> None:
  """List EBS volumes in AWS account.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """

  aws_account = account.AWSAccount(args.zone)
  volumes = aws_account.ListVolumes()

  print('Volumes found:')
  for volume in volumes:
    print('Name: {0:s}, Zone: {1:s}'.format(
        volume, volumes[volume].availability_zone))


def CreateVolumeCopy(args: 'argparse.Namespace') -> None:
  """Create a AWS Volume copy.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  print('Starting volume copy...')
  volume_copy = forensics.CreateVolumeCopy(args.zone,
                                           dst_zone=args.dst_zone,
                                           instance_id=args.instance_id,
                                           volume_id=args.volume_id,
                                           src_profile=args.src_profile,
                                           dst_profile=args.dst_profile)
  print(
      'Done! Volume {0:s} successfully created. You will find it in '
      'your AWS account under the name {1:s}.'.format(
          volume_copy.volume_id, volume_copy.name))


def QueryLogs(args: 'argparse.Namespace') -> None:
  """Query AWS CloudTrail log events.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  ct = aws_log.AWSCloudTrail(account.AWSAccount(args.zone))

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
