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

from typing import TYPE_CHECKING, List, Tuple, Optional

from google.auth.exceptions import RefreshError, DefaultCredentialsError
from googleapiclient.errors import HttpError

from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.gcp.internal import common

if TYPE_CHECKING:
  from libcloudforensics.providers.gcp.internal import compute


def CreateDiskCopy(
    src_proj: str,
    dst_proj: str,
    instance_name: str,
    zone: str,
    disk_name: Optional[str] = None,
    disk_type: str = 'pd-standard') -> 'compute.GoogleComputeDisk':
  """Creates a copy of a Google Compute Disk.

  Args:
    src_proj (str): Name of project that holds the disk to be copied.
    dst_proj (str): Name of project to put the copied disk in.
    instance_name (str): Instance using the disk to be copied.
    zone (str): Zone where the new disk is to be created.
    disk_name (str): Optional. Name of the disk to copy. If None, boot disk
        will be copied.
    disk_type (str): Optional. URL of the disk type resource describing
        which disk type to use to create the disk. Default is pd-standard. Use
        pd-ssd to have a SSD disk.

  Returns:
    GoogleComputeDisk: A Google Compute Disk object.

  Raises:
    RuntimeError: If there are errors copying the disk
  """

  src_project = gcp_project.GoogleCloudProject(src_proj)
  dst_project = gcp_project.GoogleCloudProject(dst_proj, default_zone=zone)
  instance = src_project.compute.GetInstance(
      instance_name) if instance_name else None

  try:
    if disk_name:
      disk_to_copy = src_project.compute.GetDisk(disk_name)
    else:
      disk_to_copy = instance.GetBootDisk()  # type: ignore

    common.LOGGER.info('Disk copy of {0:s} started...'.format(
        disk_to_copy.name))
    snapshot = disk_to_copy.Snapshot()
    new_disk = dst_project.compute.CreateDiskFromSnapshot(
        snapshot, disk_name_prefix='evidence', disk_type=disk_type)
    snapshot.Delete()
    common.LOGGER.info(
        'Disk {0:s} successfully copied to {1:s}'.format(
            disk_to_copy.name, new_disk.name))

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
  analysis_vm, created = proj.compute.GetOrCreateAnalysisVm(
      vm_name, boot_disk_size, disk_type=boot_disk_type, cpu_cores=cpu_cores,
      image_project=image_project, image_family=image_family)
  for disk_name in (attach_disks or []):
    analysis_vm.AttachDisk(proj.compute.GetDisk(disk_name))
  return analysis_vm, created
