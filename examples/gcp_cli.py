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

import json
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


def ListLogs(args):
  """List GCP logs for a project.

  Args:
    args (dict): Arguments from ArgumentParser.
  """
  logs = gcp.GoogleCloudLog(args.project)
  results = logs.ListLogs()
  print('Found {0:d} available log types:'.format(len(results)))
  for line in results:
    print(line)


def QueryLogs(args):
  """Query GCP logs.

  Args:
    args (dict): Arguments from ArgumentParser.
  """
  logs = gcp.GoogleCloudLog(args.project)
  results = logs.ExecuteQuery(args.filter)
  print('Found {0:d} log entries:'.format(len(results)))
  for line in results:
    print(json.dumps(line))
