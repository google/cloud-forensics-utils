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
"""Demo CLI tool for GCP."""

import argparse
from libcloudforensics import gcp


def ListInstances(args):
  """List GCE instances in GCP project.

  Args:
    args (dict): Arguments from ArgumentParser.
  """

  project = gcp.GoogleCloudProject(args.project)
  instances = project.ListInstances()

  print('Instances found:')
  for instance in instances:
    bootdisk_name = instances[instance].GetBootDisk().name
    print('Name: {0:s}, Bootdisk: {1:s}'.format(instance, bootdisk_name))


def ListDisks(args):
  """List GCE disks in GCP project.

  Args:
    args (dict): Arguments from ArgumentParser.
  """

  project = gcp.GoogleCloudProject(args.project)
  disks = project.ListDisks()
  print('Disks found:')
  for disk in disks:
    print('Name: {0:s}, Zone: {1:s}'.format(disk, disks[disk].zone))


def CreateDiskCopy(args):
  """Copy GCE disks to other GCP project.

  Args:
    args (dict): Arguments from ArgumentParser.
  """

  disk = gcp.CreateDiskCopy(
      args.project, args.dstproject, args.instancename, args.zone)

  print('Disk copy completed.')
  print('Name: {0:s}'.format(disk.name))


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Demo CLI tool for GCP')
  parser.add_argument('--project', help='The GCP project name')

  subparsers = parser.add_subparsers()

  parser_listdisks = subparsers.add_parser('listdisks')
  parser_listdisks.set_defaults(func=ListDisks)

  parser_listdisks = subparsers.add_parser('listinstances')
  parser_listdisks.set_defaults(func=ListInstances)

  parser_creatediskcopy = subparsers.add_parser('creatediskcopy')
  parser_creatediskcopy.add_argument(
      '--dstproject', help='Destination GCP project')
  parser_creatediskcopy.add_argument('--zone', help='Zone to create disk in')
  parser_creatediskcopy.add_argument(
      '--instancename', help='Instance to copy disk from')
  parser_creatediskcopy.set_defaults(func=CreateDiskCopy)

  parsed_args = parser.parse_args()
  if parsed_args.func:
    parsed_args.func(parsed_args)
