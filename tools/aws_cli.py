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

# pylint: disable=line-too-long
# Make sure that your AWS credentials are configured correclty, see
# https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html
"""Demo CLI tool for AWS."""

# pylint: enable=line-too-long

import json
import os

from datetime import datetime
from typing import TYPE_CHECKING

from libcloudforensics.providers.aws.internal import account
from libcloudforensics.providers.aws.internal import ec2
from libcloudforensics.providers.aws.internal import iam
from libcloudforensics.providers.aws.internal import log as aws_log
from libcloudforensics.providers.aws import forensics
from libcloudforensics import logging_utils

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)

if TYPE_CHECKING:
  import argparse


def ListInstances(args: 'argparse.Namespace') -> None:
  """List EC2 instances in AWS account.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """

  aws_account = account.AWSAccount(args.zone)
  instances = aws_account.ec2.ListInstances()

  logger.info('Instances found:')
  for instance in instances:
    boot_volume = instances[instance].GetBootVolume().volume_id
    logger.info('Name: {0:s}, Boot volume: {1:s}'.format(instance, boot_volume))


def ListVolumes(args: 'argparse.Namespace') -> None:
  """List EBS volumes in AWS account.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """

  aws_account = account.AWSAccount(args.zone)
  volumes = aws_account.ebs.ListVolumes()

  logger.info('Volumes found:')
  for volume in volumes:
    logger.info('Name: {0:s}, Zone: {1:s}'.format(
        volume, volumes[volume].availability_zone))


def CreateVolumeCopy(args: 'argparse.Namespace') -> None:
  """Create a AWS Volume copy.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  logger.info('Starting volume copy...')
  tags = None
  if args.tags:
    tags = json.loads(args.tags)
  volume_copy = forensics.CreateVolumeCopy(args.zone,
                                           dst_zone=args.dst_zone,
                                           instance_id=args.instance_id,
                                           volume_id=args.volume_id,
                                           volume_type=args.volume_type,
                                           src_profile=args.src_profile,
                                           dst_profile=args.dst_profile,
                                           tags=tags)
  logger.info(
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
    logger.info('Log events found: {0:d}'.format(len(result)))
    for event in result:
      logger.info(event)


def StartAnalysisVm(args: 'argparse.Namespace') -> None:
  """Start forensic analysis VM.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  if args.attach_volumes and len(args.attach_volumes.split(',')) > 11:
    logger.error('--attach_volumes must be < 11')
    return

  attach_volumes = []
  if args.attach_volumes:
    volumes = args.attach_volumes.split(',')
    # Check if volumes parameter exists and if there
    # are any empty entries.
    if not (volumes and all(elements for elements in volumes)):
      logger.error('parameter --attach_volumes: {0:s}'.format(
          args.attach_volumes))
      return

    # AWS recommends using device names that are within /dev/sd[f-p].
    device_letter = ord('f')
    for volume in volumes:
      attach = (volume, '/dev/sd'+chr(device_letter))
      attach_volumes.append(attach)
      device_letter = device_letter + 1

  key_name = args.ssh_key_name
  if args.generate_ssh_key_pair:
    logger.info('Generating SSH key pair for the analysis VM.')
    aws_account = account.AWSAccount(args.zone)
    key_name, private_key = aws_account.ec2.GenerateSSHKeyPair(
        args.instance_name)
    path = os.path.join(os.getcwd(), key_name + '.pem')
    with open(path, 'w') as f:
      f.write(private_key)
    logger.info(
        'Created key pair {0:s} in AWS. Your private key is saved in: '
        '{1:s}'.format(key_name, path))

  logger.info('Starting analysis VM...')
  vm = forensics.StartAnalysisVm(vm_name=args.instance_name,
                                 default_availability_zone=args.zone,
                                 boot_volume_size=int(args.boot_volume_size),
                                 boot_volume_type=args.boot_volume_type,
                                 cpu_cores=int(args.cpu_cores),
                                 ami=args.ami,
                                 ssh_key_name=key_name,
                                 attach_volumes=attach_volumes,
                                 dst_profile=args.dst_profile,
                                 subnet_id=args.subnet_id,
                                 security_group_id=args.security_group_id,
                                 userdata_file=args.launch_script)

  logger.info('Analysis VM started.')
  logger.info('Name: {0:s}, Started: {1:s}, Region: {2:s}'.format(vm[0].name,
                                                                  str(vm[1]),
                                                                  vm[0].region))


def ListImages(args: 'argparse.Namespace') -> None:
  """List AMI images and filter on AMI image 'name'.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  aws_account = account.AWSAccount(args.zone)

  qfilter = []
  if args.filter:
    qfilter = [{'Name': 'name', 'Values': [args.filter]}]

  images = aws_account.ec2.ListImages(qfilter)

  for image in images:
    logger.info('Name: {0:s}, ImageId: {1:s}, Location: {2:s}'.format(
        image['Name'], image['ImageId'], image['ImageLocation']))


def CreateBucket(args: 'argparse.Namespace') -> None:
  """Create an S3 bucket.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """

  aws_account = account.AWSAccount(args.zone)
  bucket = aws_account.s3.CreateBucket(args.name)

  logger.info('Bucket created: {0:s}'.format(bucket['Location']))


def UploadToBucket(args: 'argparse.Namespace') -> None:
  """Upload a file to an S3 bucket.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  aws_account = account.AWSAccount(args.zone)
  aws_account.s3.Put(args.bucket, args.filepath)

  logger.info('File successfully uploaded.')


def GCSToS3(args: 'argparse.Namespace') -> None:
  """Transfer a file from GCS to an S3 bucket.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  aws_account = account.AWSAccount(args.zone)
  aws_account.s3.GCSToS3(args.project, args.gcs_path, args.s3_path)

  logger.info('File successfully transferred.')

def ImageEBSSnapshotToS3(args: 'argparse.Namespace') -> None:
  """Image an EBS snapshot with the result placed into an S3 location.

  Unfortunately, this is not a natively supported operation in AWS. As such, we
  must create a instance, create a volume, mount the volume to the instance and
  perform a `dd` operation to perform the image. We acheive the creation of
  the volume, the attachment and the upload to S3 with a userdata script on the
  instance. That does mean however, the instance needs an instance profile with
  appropriate permissions.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  forensics.CopyEBSSnapshotToS3(
    instance_profile_name=args.instance_profile_name or 'ebsCopy',
    zone=args.zone,
    s3_destination=args.s3_destination,
    snapshot_id=args.snapshot_id,
    subnet_id=args.subnet_id,
    security_group_id=args.security_group_id,
    cleanup_iam=args.cleanup_iam
  )

def DeleteInstance(args: 'argparse.Namespace') -> None:
  """Delete an instance.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  aws_account = account.AWSAccount(args.zone)
  instance = aws_account.ec2.GetInstancesByNameOrId(
      args.instance_name, args.instance_id, args.region)[0]
  instance.Delete(force_delete=args.force_delete)

def InstanceNetworkQuarantine(args: 'argparse.Namespace') -> None:
  """Put an AWS Ec2 instance in network quarantine.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """

  exempted_src_subnets = []
  if args.exempted_src_subnets:
    exempted_src_subnets = args.exempted_src_subnets.split(',')
    # Check if exempted_src_subnets argument exists and if there
    # are any empty entries.
    if not (exempted_src_subnets and all(exempted_src_subnets)):
      logger.error('parameter --exempted_src_subnets: {0:s}'.format(
          args.exempted_src_subnets))
      return
  forensics.InstanceNetworkQuarantine(args.zone,
      args.instance_id, exempted_src_subnets)

def InstanceProfileMitigator(args: 'argparse.Namespace') -> None:
  """Remove an instance profile attachment from an instance. Also, optionally
  revoke existing issued tokens for the profile.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """

  forensics.InstanceProfileMitigator(args.zone, args.instance_id, args.revoke)
