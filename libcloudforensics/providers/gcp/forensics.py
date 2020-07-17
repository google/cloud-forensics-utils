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
"""Forensics on GCP."""

import base64
from typing import TYPE_CHECKING, List, Tuple, Optional, Dict, Any

from google.auth.exceptions import RefreshError, DefaultCredentialsError
from googleapiclient.errors import HttpError

from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.gcp.internal import common
from libcloudforensics import logging_utils

if TYPE_CHECKING:
  from libcloudforensics.providers.gcp.internal import compute

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)


def CreateDiskCopy(
    src_proj: str,
    dst_proj: str,
    zone: str,
    instance_name: Optional[str] = None,
    disk_name: Optional[str] = None,
    disk_type: str = 'pd-standard') -> 'compute.GoogleComputeDisk':
  """Creates a copy of a Google Compute Disk.

  Args:
    src_proj (str): Name of project that holds the disk to be copied.
    dst_proj (str): Name of project to put the copied disk in.
    zone (str): Zone where the new disk is to be created.
    instance_name (str): Optional. Instance using the disk to be copied.
    disk_name (str): Optional. Name of the disk to copy. If None,
        instance_name must be specified and the boot disk will be copied.
    disk_type (str): Optional. URL of the disk type resource describing
        which disk type to use to create the disk. Default is pd-standard. Use
        pd-ssd to have a SSD disk.

  Returns:
    GoogleComputeDisk: A Google Compute Disk object.

  Raises:
    RuntimeError: If there are errors copying the disk.
    ValueError: If both instance_name and disk_name are missing.
  """

  if not instance_name and not disk_name:
    raise ValueError(
        'You must specify at least one of [instance_name, disk_name].')

  src_project = gcp_project.GoogleCloudProject(src_proj)
  dst_project = gcp_project.GoogleCloudProject(dst_proj, default_zone=zone)

  try:
    if disk_name:
      disk_to_copy = src_project.compute.GetDisk(disk_name)
    elif instance_name:
      instance = src_project.compute.GetInstance(instance_name)
      disk_to_copy = instance.GetBootDisk()

    logger.info('Disk copy of {0:s} started...'.format(
        disk_to_copy.name))
    snapshot = disk_to_copy.Snapshot()
    logger.debug('Snapshot created: {0:s}'.format(snapshot.name))
    new_disk = dst_project.compute.CreateDiskFromSnapshot(
        snapshot, disk_name_prefix='evidence', disk_type=disk_type)
    logger.info(
        'Disk {0:s} successfully copied to {1:s}'.format(
            disk_to_copy.name, new_disk.name))
    snapshot.Delete()
    logger.debug('Snapshot {0:s} deleted.'.format(snapshot.name))

  except RefreshError as exception:
    error_msg = ('Something is wrong with your gcloud access token: '
                 '{0:s}.').format(exception)
    raise RuntimeError(error_msg)
  except DefaultCredentialsError as exception:
    error_msg = (
        'Something is wrong with your Application Default '
        'Credentials. '
        'Try running:\n  $ gcloud auth application-default login')
    raise RuntimeError(error_msg)
  except HttpError as exception:
    if exception.resp.status == 403:
      raise RuntimeError(
          'Make sure you have the appropriate permissions on the project')
    if exception.resp.status == 404:
      raise RuntimeError(
          'GCP resource not found. Maybe a typo in the project / instance / '
          'disk name?')
    raise RuntimeError(exception)
  except RuntimeError as exception:
    error_msg = 'Cannot copy disk "{0:s}": {1!s}'.format(disk_name, exception)
    raise RuntimeError(error_msg)

  return new_disk


def StartAnalysisVm(
    project: str,
    vm_name: str,
    zone: str,
    boot_disk_size: int,
    boot_disk_type: str,
    cpu_cores: int,
    attach_disks: Optional[List[str]] = None,
    image_project: str = 'ubuntu-os-cloud',
    image_family: str = 'ubuntu-1804-lts') -> Tuple['compute.GoogleComputeInstance', bool]:  # pylint: disable=line-too-long
  """Start a virtual machine for analysis purposes.

  Args:
    project (str): Project id for virtual machine.
    vm_name (str): The name of the virtual machine.
    zone (str): Zone for the virtual machine.
    boot_disk_size (int): The size of the analysis VM boot disk (in GB).
    boot_disk_type (str): URL of the disk type resource describing
        which disk type to use to create the disk. Use pd-standard for a
        standard disk and pd-ssd for a SSD disk.
    cpu_cores (int): The number of CPU cores to create the machine with.
    attach_disks (List[str]): Optional. List of disk names to attach.
    image_project (str): Optional. Name of the project where the analysis VM
        image is hosted.
    image_family (str): Optional. Name of the image to use to create the
        analysis VM.

  Returns:
    Tuple(GoogleComputeInstance, bool): A tuple with a virtual machine object
        and a boolean indicating if the virtual machine was created or not.
  """

  proj = gcp_project.GoogleCloudProject(project, default_zone=zone)
  logger.info('Starting analysis VM {0:s}'.format(vm_name))
  analysis_vm, created = proj.compute.GetOrCreateAnalysisVm(
      vm_name, boot_disk_size, disk_type=boot_disk_type, cpu_cores=cpu_cores,
      image_project=image_project, image_family=image_family)
  logger.info('VM started.')
  for disk_name in (attach_disks or []):
    logger.info('Attaching disk {0:s}'.format(disk_name))
    analysis_vm.AttachDisk(proj.compute.GetDisk(disk_name))
  logger.info('VM ready.')
  return analysis_vm, created


def CreateDiskFromGCSImage(
    project_id: str,
    storage_image_path: str,
    zone: str,
    name: Optional[str] = None) -> Dict[str, Any]:
  """Creates a GCE persistent disk from a image in GCS.

  The method supports raw disk images and most virtual disk
  file formats. Valid import formats are:
  [raw (dd), qcow2, qcow , vmdk, vdi, vhd, vhdx, qed, vpc].

  The created GCE disk might be larger than the original raw (dd)
  image stored in GCS to satisfy GCE capacity requirements:
  https://cloud.google.com/compute/docs/disks/#introduction
  However the bytes_count and the md5_hash values of the source
  image are returned with the newly created disk.
  The md5_hash can be used to verify the integrity of the
  created GCE disk, it must be compared with the hash of the
  created GCE disk from byte 0 to bytes_count. i.e:
  result['md5Hash'] = hash(created_gce_disk,
                            start_byte=0,
                            end_byte=result['bytes_count'])

  Args:
    project_id (str): Google Cloud Project ID.
    storage_image_path (str): Path to the source image in GCS.
    zone (str): Zone to create the new disk in.
    name (str): Optional. Name of the disk to create. Default
        is imported-disk-[TIMESTAMP('%Y%m%d%H%M%S')].

  Returns:
    Dict: A key value describing the imported GCE disk.
        Ex: {
          'project_id': 'fake-project',
          'disk_name': 'fake-imported-disk',
          'zone': 'fake-zone',
          'bytes_count': '1234'  # Content-Length of source image in bytes.
          'md5Hash': 'Source Image MD5 hash string in hex'
        }

  Raises:
    ValueError: If the GCE disk name is invalid.
  """

  if name:
    if not common.REGEX_DISK_NAME.match(name):
      raise ValueError(
          'Disk name {0:s} does not comply with {1:s}'.format(
              name, common.REGEX_DISK_NAME.pattern))
    name = name[:common.COMPUTE_NAME_LIMIT]
  else:
    name = common.GenerateUniqueInstanceName('imported-disk',
                                             common.COMPUTE_NAME_LIMIT)

  project = gcp_project.GoogleCloudProject(project_id)
  image_object = project.compute.ImportImageFromStorage(storage_image_path)
  disk_object = project.compute.CreateDiskFromImage(
      image_object, zone=zone, name=name)
  storage_object_md = project.storage.GetObjectMetadata(storage_image_path)
  md5_hash_hex = base64.b64decode(storage_object_md['md5Hash']).hex()
  result = {
      'project_id': disk_object.project_id,
      'disk_name': disk_object.name,
      'zone': disk_object.zone,
      'bytes_count': storage_object_md['size'],
      'md5Hash': md5_hash_hex
  }
  return result
