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
"""Forensics implementation."""

from google.auth.exceptions import RefreshError, DefaultCredentialsError
from googleapiclient.errors import HttpError

from libcloudforensics.providers.forensics_interface import Forensics
from libcloudforensics.providers.gcp import internal as gcp_internal
from libcloudforensics.providers.gcp.internal.common import LOGGER


class GCPForensics(Forensics):
  """Concrete implementation of the forensics interface."""

  # pylint: disable=arguments-differ
  def CreateDiskCopy(self,
                     src_proj,
                     dst_proj,
                     instance_name,
                     zone,
                     disk_name=None,
                     disk_type='pd-standard'):
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

    src_proj = gcp_internal.GoogleCloudProject(src_proj)
    dst_proj = gcp_internal.GoogleCloudProject(dst_proj, default_zone=zone)
    instance = src_proj.GetInstance(instance_name) if instance_name else None

    try:
      if disk_name:
        disk_to_copy = src_proj.GetDisk(disk_name)
      else:
        disk_to_copy = instance.GetBootDisk()

      LOGGER.info('Disk copy of {0:s} started...'.format(disk_to_copy.name))
      snapshot = disk_to_copy.Snapshot()
      new_disk = dst_proj.CreateDiskFromSnapshot(
          snapshot, disk_name_prefix='evidence', disk_type=disk_type)
      snapshot.Delete()
      LOGGER.info(
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
      raise RuntimeError(exception, critical=True)
    except RuntimeError as exception:
      error_msg = 'Cannot copy disk "{0:s}": {1!s}'.format(disk_name, exception)
      raise RuntimeError(error_msg)

    return new_disk

  # pylint: disable=arguments-differ
  def StartAnalysisVm(self,
                      project,
                      vm_name,
                      zone,
                      boot_disk_size,
                      boot_disk_type,
                      cpu_cores,
                      attach_disk=None,
                      image_project='ubuntu-os-cloud',
                      image_family='ubuntu-1804-lts'):
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
      attach_disk (list(GoogleComputeDisk)): Optional. List of disks to attach.
      image_project (str): Optional. Name of the project where the analysis VM
          image is hosted.
      image_family (str): Optional. Name of the image to use to create the
          analysis VM.

    Returns:
      tuple(GoogleComputeInstance, bool): A tuple with a virtual machine object
          and a boolean indicating if the virtual machine was created or not.
    """

    project = gcp_internal.GoogleCloudProject(project, default_zone=zone)
    analysis_vm, created = project.GetOrCreateAnalysisVm(
        vm_name, boot_disk_size, disk_type=boot_disk_type, cpu_cores=cpu_cores,
        image_project=image_project, image_family=image_family)
    for disk in (attach_disk or []):
      analysis_vm.AttachDisk(disk)
    return analysis_vm, created
