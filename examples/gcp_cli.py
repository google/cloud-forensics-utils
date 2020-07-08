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

from datetime import datetime
import json
import sys
from typing import TYPE_CHECKING

# pylint: disable=line-too-long
from libcloudforensics.providers.gcp.internal import log as gcp_log
from libcloudforensics.providers.gcp.internal import monitoring as gcp_monitoring
from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.gcp.internal import storage as gcp_storage
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
                                  args.zone,
                                  instance_name=args.instance_name,
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

  Raises:
    ValueError: If the start or end date is not properly formatted.
  """
  logs = gcp_log.GoogleCloudLog(args.project)

  try:
    if args.start:
      datetime.strptime(args.start, '%Y-%m-%dT%H:%M:%SZ')
    if args.end:
      datetime.strptime(args.end, '%Y-%m-%dT%H:%M:%SZ')
  except ValueError as error:
    sys.exit(str(error))

  qfilter = ''

  if args.start:
    qfilter += 'timestamp>="{0:s}" '.format(args.start)
  if args.start and args.end:
    qfilter += 'AND '
  if args.end:
    qfilter += 'timestamp<="{0:s}" '.format(args.end)

  if args.filter and (args.start or args.end):
    qfilter += 'AND '
    qfilter += args.filter
  elif args.filter:
    qfilter += args.filter

  results = logs.ExecuteQuery(qfilter)
  print('Found {0:d} log entries:'.format(len(results)))
  for line in results:
    print(json.dumps(line))


def CreateDiskFromGCSImage(args: 'argparse.Namespace') -> None:
  """Creates GCE persistent disk from image in GCS.

  Please refer to doc string of forensics.CreateDiskFromGCSImage
  function for more details on how the image is created.

  Args:
      args (argparse.Namespace): Arguments from ArgumentParser.
  """

  result = forensics.CreateDiskFromGCSImage(
      args.project, args.gcs_path, args.zone, name=args.disk_name)

  print('Disk creation completed.')
  print('Project ID: {0:s}'.format(result['project_id']))
  print('Disk name: {0:s}'.format(result['disk_name']))
  print('Zone: {0:s}'.format(result['zone']))
  print('size in bytes: {0:s}'.format(result['bytes_count']))
  print('MD5 hash of source image in hex: {0:s}'.format(result['md5Hash']))


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
    print('{0:s}: {1:s}'.format(apiname, usage))


def GetBucketACLs(args: 'argparse.Namespace') -> None:
  """Retrieve the Access Controls for a GCS bucket.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  gcs = gcp_storage.GoogleCloudStorage(args.project)
  bucket_acls = gcs.GetBucketACLs(args.path)
  for role in bucket_acls:
    print('{0:s}: {1:s}'.format(role, ', '.join(bucket_acls[role])))


def GetGCSObjectMetadata(args: 'argparse.Namespace') -> None:
  """List the details of an object in a GCS bucket.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  gcs = gcp_storage.GoogleCloudStorage(args.project)
  results = gcs.GetObjectMetadata(args.path)
  if results.get('kind') == 'storage#objects':
    for item in results.get('items', []):
      for key, value in item.items():
        print('{0:s}: {1:s}'.format(key, value))
      print('---------')
  else:
    for key, value in results.items():
      print('{0:s}: {1:s}'.format(key, value))


def ListBucketObjects(args: 'argparse.Namespace') -> None:
  """List the objects in a GCS bucket.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  gcs = gcp_storage.GoogleCloudStorage(args.project)
  results = gcs.ListBucketObjects(args.path)
  for obj in results:
    print('{0:s} {1:s}b [{2:s}]'.format(
        obj.get('id', 'ID not found'), obj.get('size', 'Unknown size'),
        obj.get('contentType', 'Unknown Content-Type')))
