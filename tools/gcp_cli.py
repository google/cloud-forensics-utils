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
from libcloudforensics import errors
from libcloudforensics.providers.aws.internal import s3 as aws_s3
from libcloudforensics.providers.gcp.internal import common
from libcloudforensics.providers.gcp.internal import compute as gcp_compute
from libcloudforensics.providers.gcp.internal import log as gcp_log
from libcloudforensics.providers.gcp.internal import monitoring as gcp_monitoring
from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.gcp.internal import storage as gcp_storage
from libcloudforensics.providers.gcp.internal import storagetransfer as gcp_st
from libcloudforensics.providers.gcp.internal import cloudsql as gcp_cloudsql
from libcloudforensics.providers.gcp import forensics
from libcloudforensics import logging_utils
# pylint: enable=line-too-long

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)

if TYPE_CHECKING:
  import argparse


def ListInstances(args: 'argparse.Namespace') -> None:
  """List GCE instances in GCP project.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """

  project = gcp_project.GoogleCloudProject(args.project)
  instances = project.compute.ListInstances()

  logger.info('Instances found:')
  for instance in instances:
    bootdisk = instances[instance].GetBootDisk()
    if bootdisk:
      logger.info('Name: {0:s}, Bootdisk: {1:s}'.format(
          instance, bootdisk.name))


def ListDisks(args: 'argparse.Namespace') -> None:
  """List GCE disks in GCP project.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """

  project = gcp_project.GoogleCloudProject(args.project)
  disks = project.compute.ListDisks()
  logger.info('Disks found:')
  for disk in disks:
    logger.info('Name: {0:s}, Zone: {1:s}'.format(disk, disks[disk].zone))


def CreateDiskCopy(args: 'argparse.Namespace') -> None:
  """Copy GCE disks to other GCP project.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """

  disk = forensics.CreateDiskCopy(args.project,
                                  args.dst_project,
                                  args.zone,
                                  instance_name=args.instance_name,
                                  disk_name=args.disk_name,
                                  disk_type=args.disk_type)

  logger.info('Disk copy completed.')
  logger.info('Name: {0:s}'.format(disk.name))


def DeleteInstance(args: 'argparse.Namespace') -> None:
  """Deletes a GCE instance.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """

  compute_client = gcp_compute.GoogleCloudCompute(args.project)
  instance = compute_client.GetInstance(instance_name=args.instance_name)
  instance.Delete(delete_disks=args.delete_all_disks)

  print('Instance deleted.')


def ListLogs(args: 'argparse.Namespace') -> None:
  """List GCP logs for a project.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  logs = gcp_log.GoogleCloudLog(args.project)
  results = logs.ListLogs()
  logger.info('Found {0:d} available log types:'.format(len(results)))
  for line in results:
    logger.info(line)


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
  logger.info('Found {0:d} log entries:'.format(len(results)))
  for line in results:
    logger.info(json.dumps(line))


def CreateDiskFromGCSImage(args: 'argparse.Namespace') -> None:
  """Creates GCE persistent disk from image in GCS.

  Please refer to doc string of forensics.CreateDiskFromGCSImage
  function for more details on how the image is created.

  Args:
      args (argparse.Namespace): Arguments from ArgumentParser.
  """

  result = forensics.CreateDiskFromGCSImage(
      args.project, args.gcs_path, args.zone, name=args.disk_name)

  logger.info('Disk creation completed.')
  logger.info('Project ID: {0:s}'.format(result['project_id']))
  logger.info('Disk name: {0:s}'.format(result['disk_name']))
  logger.info('Zone: {0:s}'.format(result['zone']))
  logger.info('size in bytes: {0:s}'.format(result['bytes_count']))
  logger.info('MD5 hash of source image in hex: {0:s}'.format(
      result['md5Hash']))


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
      logger.error('parameter --attach_disks: {0:s}'.format(
          args.attach_disks))
      return

  logger.info('Starting analysis VM...')
  vm = forensics.StartAnalysisVm(args.project,
                                 args.instance_name,
                                 args.zone,
                                 int(args.disk_size),
                                 args.disk_type,
                                 int(args.cpu_cores),
                                 attach_disks=attach_disks)

  logger.info('Analysis VM started.')
  logger.info('Name: {0:s}, Started: {1:s}'.format(vm[0].name, str(vm[1])))


def ListServices(args: 'argparse.Namespace') -> None:
  """List active GCP services (APIs) for a project.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  apis = gcp_monitoring.GoogleCloudMonitoring(args.project)
  results = apis.ActiveServices()
  logger.info('Found {0:d} APIs:'.format(len(results)))
  sorted_apis = sorted(results.items(), key=lambda x: x[1], reverse=True)
  for apiname, usage in sorted_apis:
    logger.info('{0:s}: {1:s}'.format(apiname, usage))


def GetBucketACLs(args: 'argparse.Namespace') -> None:
  """Retrieve the Access Controls for a GCS bucket.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  gcs = gcp_storage.GoogleCloudStorage(args.project)
  bucket_acls = gcs.GetBucketACLs(args.path)
  for role in bucket_acls:
    logger.info('{0:s}: {1:s}'.format(role, ', '.join(bucket_acls[role])))


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
        logger.info('{0:s}: {1:s}'.format(key, value))
      logger.info('---------')
  else:
    for key, value in results.items():
      logger.info('{0:s}: {1:s}'.format(key, value))


def ListBuckets(args: 'argparse.Namespace') -> None:
  """List the buckets in a GCP project.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  gcs = gcp_storage.GoogleCloudStorage(args.project)
  results = gcs.ListBuckets()
  for obj in results:
    logger.info('{0:s} : {1:s}'.format(
        obj.get('id', 'ID not found'), obj.get('selfLink', 'No link')))


def CreateBucket(args: 'argparse.Namespace') -> None:
  """Create a bucket in a GCP project.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  gcs = gcp_storage.GoogleCloudStorage(args.project)
  result = gcs.CreateBucket(args.name, labels={'created_by': 'cfu'})
  logger.info(
      '{0:s} : {1:s}'.format(
          result.get('id', 'ID not found'), result.get('selfLink', 'No link')))


def ListBucketObjects(args: 'argparse.Namespace') -> None:
  """List the objects in a GCS bucket.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  gcs = gcp_storage.GoogleCloudStorage(args.project)
  results = gcs.ListBucketObjects(args.path)
  for obj in results:
    logger.info('{0:s} {1:s}b [{2:s}]'.format(
        obj.get('id', 'ID not found'), obj.get('size', 'Unknown size'),
        obj.get('contentType', 'Unknown Content-Type')))


def GetBucketSize(args: 'argparse.Namespace') -> None:
  """Get the size of a GCS bucket.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  gcs = gcp_storage.GoogleCloudStorage(args.project)
  results = gcs.GetBucketSize(args.path)
  for obj in results:
    logger.info('{0:s}: {1:d}b'.format(
        obj, results[obj]))


def ListCloudSqlInstances(args: 'argparse.Namespace') -> None:
  """List the CloudSQL instances of a Project.

  Args:
    args (argsparse.Namespace): Arguments from ArgumentParser.
  """
  gcsql = gcp_cloudsql.GoogleCloudSQL(args.project)
  results = gcsql.ListCloudSQLInstances()
  for obj in results:
    logger.info('{0:s} {1:s} [{2:s}]'.format(
        obj.get('instanceType', 'type not found'),
        obj.get('name', 'name not known'),
        obj.get('state', 'state not known')))


def DeleteObject(args: 'argparse.Namespace') -> None:
  """Deletes an object in GCS.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  gcs = gcp_storage.GoogleCloudStorage(args.project)
  gcs.DeleteObject(args.path)

  print('Object deleted.')


def InstanceNetworkQuarantine(args: 'argparse.Namespace') -> None:
  """Put a Google Cloud instance in network quarantine.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  exempted_ips = []
  if args.exempted_src_ips:
    exempted_ips = args.exempted_src_ips.split(',')
    # Check if exempted_src_ips argument exists and if there
    # are any empty entries.
    if not (exempted_ips and all(exempted_ips)):
      logger.error('parameter --exempted_src_ips: {0:s}'.format(
          args.exempted_src_ips))
      return
  forensics.InstanceNetworkQuarantine(args.project,
      args.instance_name, exempted_ips, args.enable_logging )


def VMRemoveServiceAccount(args: 'argparse.Namespace') -> None:
  """Removes an attached service account from a VM instance.
  Requires the instance to be stopped, if it isn't already.
  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  forensics.VMRemoveServiceAccount(args.project, args.instance_name,
      args.leave_stopped)


def ExportDisksToBucket(args: 'argparse.Namespace') -> None:
  """Copy all the disks from a GCE instance to a Storage bucket.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  compute_client = gcp_compute.GoogleCloudCompute(args.project)
  gcs = gcp_storage.GoogleCloudStorage(args.project)

  s3_dest = None
  if not (args.path.startswith('gs://') or args.path.startswith('s3://')):
    sys.exit('Destination bucket path must start with gs:// or s3://')
  if args.path.startswith('s3://'):
    s3_dest = args.path
    args.path = 'gs://' + common.GenerateUniqueInstanceName('transfer-from-cfu')
    logger.info('Setting temporary bucket path to {0:s}'.format(args.path))

  logger.warning('You must enable the following APIs:')
  logger.warning(
      'https://cloud.google.com/compute/docs/images/export-image#enable-cloud-build'  # pylint: disable=line-too-long
  )
  logger.warning(
      'If transferring to an S3 bucket: https://console.cloud.google.com/apis/api/storagetransfer.googleapis.com/overview'  # pylint: disable=line-too-long
  )
  # TODO(fryy): Automatically find and delete the Daisy bucket
  logger.warning(
      'The Cloud Build will leave a bucket full of artifacts that should be deleted (including a compressed export of the disks).'  # pylint: disable=line-too-long
  )

  try:
    logger.info('Creating bucket {0:s}'.format(args.path))
    bucket = gcs.CreateBucket(args.path, labels={
        'created_by': 'cfu'
    }).get('name')
  except errors.ResourceCreationError as exception:
    if 'already exists' in exception.message:
      logger.info('Target bucket already exists. Reusing.')
      bucket = args.path
    else:
      sys.exit(str(exception))
  logger.info('Retrieving instance')
  instance = compute_client.GetInstance(instance_name=args.instance_name)
  logger.info('Listing disks')
  disks = instance.ListDisks()
  for d in disks.values():
    logger.info('Processing disk: {0:s}'.format(d.name))
    i = compute_client.CreateImageFromDisk(d)
    logger.info(
        'Image created from disk: {0:s}. Exporting to GCS.'.format(i.name))
    gcs_dest = 'gs://' + bucket
    i.ExportImage(gcs_dest)
    logger.info('Deleting image.')
    i.Delete()
    if s3_dest:
      logger.info('Transferring file {0:s} to {1:s}.'.format(gcs_dest, s3_dest))
      aws_s3.S3.GCSToS3(args.project, gcs_dest, s3_dest)


def DownloadObject(args: 'argparse.Namespace') -> None:
  """Downloads an object from GCS.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  gcs = gcp_storage.GoogleCloudStorage(args.project)
  filename = gcs.GetObject(args.path, args.dest)

  print('Object downloaded to {0:s}.'.format(filename))


def S3ToGCS(args: 'argparse.Namespace') -> None:
  """Transfer a file from S3 to a GCS bucket.

  Args:
    args (argparse.Namespace): Arguments from ArgumentParser.
  """
  gcst = gcp_st.GoogleCloudStorageTransfer(args.project)
  gcst.S3ToGCS(args.s3_path, args.zone, args.gcs_path)

  logger.info('File successfully transferred.')
