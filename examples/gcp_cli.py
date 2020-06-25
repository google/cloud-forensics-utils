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
from typing import TYPE_CHECKING

# pylint: disable=line-too-long
from libcloudforensics.providers.gcp.internal import log as gcp_log
from libcloudforensics.providers.gcp.internal import monitoring as gcp_monitoring
from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.gcp import forensics
# pylint: enable=line-too-long

if TYPE_CHECKING:
  import argparse


def ListInstances(args: 'argparse.Namespace') -> None:
  """List GCE instances in GCP project.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """

  project = gcp_project.GoogleCloudProject(args.project)
  instances = project.compute.ListInstances()

  print('Instances found:')
  for instance in instances:
    bootdisk = instances[instance].GetBootDisk()
    if bootdisk:
      print('Name: {0:s}, Bootdisk: {1:s}'.format(instance, bootdisk.name))


def ListDisks(args: 'argparse.Namespace') -> None:
  """List GCE disks in GCP project.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """

  project = gcp_project.GoogleCloudProject(args.project)
  disks = project.compute.ListDisks()
  print('Disks found:')
  for disk in disks:
    print('Name: {0:s}, Zone: {1:s}'.format(disk, disks[disk].zone))


def CreateDiskCopy(args: 'argparse.Namespace') -> None:
  """Copy GCE disks to other GCP project.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """

  disk = forensics.CreateDiskCopy(args.project,
                                  args.dst_project,
                                  args.instance_name,
                                  args.zone,
                                  disk_name=args.disk_name)

  print('Disk copy completed.')
  print('Name: {0:s}'.format(disk.name))


def ListLogs(args: 'argparse.Namespace') -> None:
  """List GCP logs for a project.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  logs = gcp_log.GoogleCloudLog(args.project)
  results = logs.ListLogs()
  print('Found {0:d} available log types:'.format(len(results)))
  for line in results:
    print(line)


def QueryLogs(args: 'argparse.Namespace') -> None:
  """Query GCP logs.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  logs = gcp_log.GoogleCloudLog(args.project)
  results = logs.ExecuteQuery(args.filter)
  print('Found {0:d} log entries:'.format(len(results)))
  for line in results:
    print(json.dumps(line))


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
      print('error: parameter --attach_disks: {0:s}'.format(args.attach_disks))
      return

  print('Starting analysis VM...')
  vm = forensics.StartAnalysisVm(args.project,
                                 args.instance_name,
                                 args.zone,
                                 int(args.disk_size),
                                 args.disk_type,
                                 int(args.cpu_cores),
                                 attach_disks=attach_disks)

  print('Analysis VM started.')
  print('Name: {0:s}, Started: {1:s}'.format(vm[0].name, str(vm[1])))


def ListServices(args: 'argparse.Namespace') -> None:
  """List active GCP services (APIs) for a project.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  apis = gcp_monitoring.GoogleCloudMonitoring(args.project)
  results = apis.ActiveServices()
  print('Found {0:d} APIs:'.format(len(results)))
  sorted_apis = sorted(results.items(), key=lambda x: x[1], reverse=True)
  for apiname, usage in sorted_apis:
    print('{}: {}'.format(apiname, usage))
