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
"""Demo script for making volume copies on AWS."""

import argparse
from libcloudforensics import aws

if __name__ == '__main__':
  # Make sure that your AWS credentials are configured correclty, see
  # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html #pylint: disable=line-too-long
  parser = argparse.ArgumentParser(
      description='Demo script for making volume copies on AWS. Example '
                  'usage: python -m examples.aws_snapshot --volume_id=xxx '
                  '--src_account=foo --dst_account=bar us-east-2b')
  parser.add_argument(
      'zone',
      help='The AWS zone in which resources are located, e.g. us-east-2b')
  parser.add_argument(
      '--volume_id',
      help='The AWS unique volume ID of the volume to copy. If none '
           'specified, then --instance_id must be specified and the boot '
           'volume of the AWS instance will be copied.')
  parser.add_argument('--instance_id', help='The AWS unique instance ID')
  parser.add_argument('--src_account', help='The name of the profile for the '
                                            'source account, as defined in '
                                            'the AWS credentials file.')
  parser.add_argument('--dst_account', help='The name of the profile for the '
                                            'destination account, as defined '
                                            'in the AWS credentials file.')

  args = parser.parse_args()
  print('Starting volume copy...')
  volume_copy = aws.CreateVolumeCopy(
      args.zone,
      instance_id=args.instance_id,
      volume_id=args.volume_id,
      src_account=args.src_account,
      dst_account=args.dst_account)
  print('Done! Volume {0:s} successfully created. You will find it in '
        'your AWS account under the name {1:s}.'.format(
            volume_copy.volume_id, volume_copy.name))
