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
"""Google Compute Engine resources."""

import datetime
import os
import re
import subprocess
import time

from libcloudforensics.providers.gcp.internal import build
from libcloudforensics.providers.gcp.internal import common
# The following import is only used in methods so we can ignore the cyclic
# dependency
from libcloudforensics.providers.gcp.internal import compute  # pylint: disable=cyclic-import


class GoogleComputeBaseResource(common.GoogleCloudComputeClient):
  """Base class representing a Computer Engine resource.

  Attributes:
    project_id (str): Google Cloud project ID.
    zone (str): What zone the resource is in.
    name (str): Name of the resource.
    labels (dict): Dictionary of labels for the resource, if existing.
  """

  def __init__(self, project_id, zone, name, labels=None):
    """Initialize the Google Compute Resource base object.

    Args:
      project_id (str): Google Cloud project ID.
      zone (str): What zone the resource is in.
      name (str): Name of the resource.
      labels (dict): Dictionary of labels for the resource, if existing.
    """

    self.zone = zone
    self.name = name
    self.labels = labels
    self._data = None
    self.project_id = project_id
    super(GoogleComputeBaseResource, self).__init__(self.project_id)

  def FormatLogMessage(self, message):
    """Format log messages with project specific information.

    Args:
      message (str): Message string to log.

    Returns:
      str: Formatted log message string.
    """

    return 'project:{0} {1}'.format(self.project_id, message)

  def GetValue(self, key):
    """Get specific value from the resource key value store.

    Args:
      key (str): A key of type String to get key's corresponding value.

    Returns:
      str: Value of key or None if key is missing.
    """

    self._data = self.GetOperation()  # pylint: disable=no-member
    return self._data.get(key)

  def GetSourceString(self):
    """API URL to the resource.

    Returns:
      str: The full API URL to the resource.
    """

    if self._data:
      return self._data['selfLink']
    return self.GetValue('selfLink')

  def GetResourceType(self):
    """Get the resource type from the resource key-value store.

    Returns:
      str: Resource Type which is a string with one of the following values:
          compute#instance
          compute#disk
          compute#Snapshot
    """

    if self._data:
      return self._data['kind']
    return self.GetValue('kind')

  def FormOperation(self, operation_name):
    """Form an API operation object for the compute resource.

    Example:[RESOURCE].FormOperation('setLabels')(**kwargs)
    [RESOURCE] can be type "instance", disk or "Snapshot".

    Args:
      operation_name (str): The name of the API operation you need to perform.

    Returns:
      apiclient.discovery.Resource: An API operation object for the
          referenced compute resource.

    Raises:
      RuntimeError: If resource type is not defined as a type which
          extends the GoogleComputeBaseResource class.
    """

    resource_type = self.GetResourceType()
    module = None
    if resource_type not in ['compute#instance', 'compute#Snapshot',
                             'compute#disk']:
      error_msg = (
          'Compute resource Type {0:s} is not one of the defined '
          'types in libcloudforensics library '
          '(Instance, Disk or Snapshot).').format(resource_type)
      raise RuntimeError(error_msg)
    if resource_type == 'compute#instance':
      module = self.GceApi().instances()
    elif resource_type == 'compute#disk':
      module = self.GceApi().disks()
    elif resource_type == 'compute#Snapshot':
      module = self.GceApi().snapshots()

    operation_func_to_call = getattr(module, operation_name)
    return operation_func_to_call

  def GetLabels(self):
    """Get all labels of a compute resource.

    Returns:
      dict: A dictionary of all labels.
    """

    operation = self.GetOperation()  # pylint: disable=no-member

    return operation.get('labels')

  def AddLabels(self, new_labels_dict, blocking_call=False):
    """Add or update labels of a compute resource.

    Args:
      new_labels_dict (dict): A dictionary containing the labels to be added,
          ex:{"incident_id": "1234abcd"}.
      blocking_call (bool): Optional. A boolean to decide whether the API call
          should be blocking or not, default is False.

    Returns:
      dict: The response of the API operation.

    Raises:
      RuntimeError: If the Compute resource Type is not one of instance,
          disk or snapshot.
    """

    get_operation = self.GetOperation()  # pylint: disable=no-member
    label_fingerprint = get_operation['labelFingerprint']

    existing_labels_dict = {}
    if self.GetLabels() is not None:
      existing_labels_dict = self.GetLabels()
    existing_labels_dict.update(new_labels_dict)
    labels_dict = existing_labels_dict
    request_body = {
        'labels': labels_dict,
        'labelFingerprint': label_fingerprint
    }

    resource_type = self.GetResourceType()
    response = None
    if resource_type not in ['compute#instance', 'compute#Snapshot',
                             'compute#disk']:
      error_msg = (
          'Compute resource Type {0:s} is not one of the defined '
          'types in libcloudforensics library '
          '(Instance, Disk or Snapshot) ').format(resource_type)
      raise RuntimeError(error_msg)
    if resource_type == 'compute#instance':
      response = self.FormOperation('setLabels')(
          instance=self.name, project=self.project_id, zone=self.zone,
          body=request_body).execute()
    elif resource_type == 'compute#disk':
      response = self.FormOperation('setLabels')(
          resource=self.name, project=self.project_id, zone=self.zone,
          body=request_body).execute()
    elif resource_type == 'compute#Snapshot':
      response = self.FormOperation('setLabels')(
          resource=self.name, project=self.project_id,
          body=request_body).execute()
    if blocking_call:
      self.BlockOperation(response, zone=self.zone)

    return response


class GoogleComputeInstance(GoogleComputeBaseResource):
  """Class representing a Google Compute Engine virtual machine."""

  def GetOperation(self):
    """Get API operation object for the virtual machine.

    Returns:
      dict: An API operation object for a Google Compute Engine
          virtual machine.
    """

    gce_instance_client = self.GceApi().instances()
    request = gce_instance_client.get(
        instance=self.name, project=self.project_id, zone=self.zone)
    response = request.execute()
    return response

  def GetBootDisk(self):
    """Get the virtual machine boot disk.

    Returns:
      GoogleComputeDisk: Disk object or None if no disk can be found.
    """

    for disk in self.GetValue('disks'):
      if disk['boot']:
        disk_name = disk['source'].split('/')[-1]
        return compute.GoogleCloudCompute(
            self.project_id).GetDisk(disk_name=disk_name)
    return None

  def GetDisk(self, disk_name):
    """Gets a disk attached to this virtual machine disk by name.

    Args:
      disk_name (str): The name of the disk to get.

    Returns:
      GoogleComputeDisk: Disk object.

    Raises:
      RuntimeError: If disk name is not found among those attached to the
          instance.
    """

    for disk in self.GetValue('disks'):
      if disk['source'].split('/')[-1] == disk_name:
        return compute.GoogleCloudCompute(
            self.project_id).GetDisk(disk_name=disk_name)
    error_msg = 'Disk name "{0:s}" not attached to instance'.format(disk_name)
    raise RuntimeError(error_msg)

  def ListDisks(self):
    """List all disks for the virtual machine.

    Returns:
      list(str): List of disk names.
    """

    return [disk['source'].split('/')[-1] for disk in self.GetValue('disks')]

  def __SshConnection(self):
    """Create an SSH connection to the virtual machine."""

    devnull = open(os.devnull, 'w')
    subprocess.check_call([
        'gcloud', 'compute', '--project', self.project_id, 'ssh',
        '--zone', self.zone, self.name
    ], stderr=devnull)

  def Ssh(self):
    """Connect to the virtual machine over SSH."""

    max_retries = 100  # times to retry the connection
    retries = 0

    common.LOGGER.info(
        self.FormatLogMessage('Connecting to analysis VM over SSH'))

    while retries < max_retries:
      try:
        self.__SshConnection()
        break
      except subprocess.CalledProcessError:
        retries += 1
        time.sleep(5)  # seconds between connections

  def AttachDisk(self, disk, read_write=False):
    """Attach a disk to the virtual machine.

    Args:
      disk (GoogleComputeDisk): Disk to attach.
      read_write (bool): Optional. Boolean indicating whether the disk should
          be attached in RW mode. Default is False (read-only).
    """

    mode = 'READ_ONLY'  # Default mode
    if read_write:
      mode = 'READ_WRITE'

    common.LOGGER.info(
        self.FormatLogMessage(
            'Attaching {0} to VM {1} in {2} mode'.format(
                disk.name, self.name, mode)))

    operation_config = {
        'mode': mode,
        'source': disk.GetSourceString(),
        'boot': False,
        'autoDelete': False,
    }
    gce_instance_client = self.GceApi().instances()
    request = gce_instance_client.attachDisk(
        instance=self.name, project=self.project_id, zone=self.zone,
        body=operation_config)
    response = request.execute()
    self.BlockOperation(response, zone=self.zone)

  def DetachDisk(self, disk):
    """Detach a disk from the virtual machine.

    Args:
      disk (GoogleComputeDisk): Disk to detach.
    """

    gce_instance_client = self.GceApi().instances()
    request = gce_instance_client.detachDisk(instance=self.name,
                                             project=self.project_id,
                                             zone=self.zone,
                                             deviceName=disk.name)
    response = request.execute()
    self.BlockOperation(response, zone=self.zone)


class GoogleComputeDisk(GoogleComputeBaseResource):
  """Class representing a Compute Engine disk."""

  def GetOperation(self):
    """Get API operation object for the disk.

    Returns:
      dict: An API operation object for a Google Compute Engine disk.
    """

    gce_disk_client = self.GceApi().disks()
    request = gce_disk_client.get(
        disk=self.name, project=self.project_id, zone=self.zone)
    response = request.execute()
    return response

  def Snapshot(self, snapshot_name=None):
    """Create Snapshot of the disk.

    The Snapshot name must comply with the following RegEx:
      - ^(?=.{1,63}$)[a-z]([-a-z0-9]*[a-z0-9])?$

    i.e., it must be between 1 and 63 chars, the first character must be a
    lowercase letter, and all following characters must be a dash, lowercase
    letter, or digit, except the last character, which cannot be a dash.

    Args:
      snapshot_name (str): Optional. Name of the Snapshot.

    Returns:
      GoogleComputeSnapshot: A Snapshot object.

    Raises:
      ValueError: If the name of the snapshot does not comply with the RegEx.
    """

    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    if not snapshot_name:
      snapshot_name = self.name
    truncate_at = 63 - len(timestamp) - 1
    snapshot_name = '{0}-{1}'.format(snapshot_name[:truncate_at], timestamp)
    if not common.REGEX_DISK_NAME.match(snapshot_name):
      raise ValueError(
          'Snapshot name {0:s} does not comply with '
          '{1:s}'.format(snapshot_name, common.REGEX_DISK_NAME.pattern))
    common.LOGGER.info(
        self.FormatLogMessage(
            'New Snapshot: {0}'.format(snapshot_name)))
    operation_config = {'name': snapshot_name}
    gce_disk_client = self.GceApi().disks()
    request = gce_disk_client.createSnapshot(
        disk=self.name, project=self.project_id, zone=self.zone,
        body=operation_config)
    response = request.execute()
    self.BlockOperation(response, zone=self.zone)
    return GoogleComputeSnapshot(disk=self, name=snapshot_name)


class GoogleComputeSnapshot(GoogleComputeBaseResource):
  """Class representing a Compute Engine Snapshot.

  Attributes:
    disk (GoogleComputeDisk): Disk used for the Snapshot.
  """

  def __init__(self, disk, name):
    """Initialize the Snapshot object.

    Args:
      disk (GoogleComputeDisk): Disk used for the Snapshot.
      name (str): Name of the Snapshot.
    """

    super(GoogleComputeSnapshot, self).__init__(
        project_id=disk.project_id, zone=None, name=name)
    self.disk = disk

  def GetOperation(self):
    """Get API operation object for the Snapshot.

    Returns:
      dict: An API operation object for a Google Compute Engine Snapshot.
    """

    gce_snapshot_client = self.GceApi().snapshots()
    request = gce_snapshot_client.get(
        snapshot=self.name, project=self.project_id)
    response = request.execute()
    return response

  def Delete(self):
    """Delete a Snapshot."""

    common.LOGGER.info(
        self.FormatLogMessage(
            'Deleted Snapshot: {0}'.format(self.name)))
    gce_snapshot_client = self.GceApi().snapshots()
    request = gce_snapshot_client.delete(
        project=self.project_id, snapshot=self.name)
    response = request.execute()
    self.BlockOperation(response)


class GoogleComputeImage(GoogleComputeBaseResource):
  """Class representing a Compute Engine Image.

  Attributes:
    disk (GoogleComputeDisk): Disk used for the Snapshot.
  """

  def GetOperation(self):
    """Get API operation object for the image.

    Returns:
      dict: Holding an API operation object for a Google Compute Engine Image.
    """

    gce_image_client = self.GceApi().images()
    request = gce_image_client.get(
        project=self.project_id, image=self.name)
    response = request.execute()
    return response

  def ExportImage(self, gcs_output_folder, output_name=None):
    """Export compute image to Google Cloud storage.

    Exported image is compressed and stored in .tar.gz format.

    Args:
      gcs_output_folder (str): Folder path of the exported image.
      output_name (str): Optional. Name of the output file, must end with
          .tar.gz, if not exist, the [image_name].tar.gz will be used.

    Raises:
      RuntimeError: If exported image name is invalid.
    """

    if output_name:
      if not bool(re.match("^[A-Za-z0-9-]*$", output_name)):
        raise RuntimeError(
            'Destination disk name must comply with expression ^[A-Za-z0-9-]*$')
      full_path = '{0:s}.tar.gz'.format(
          os.path.join(gcs_output_folder, output_name))
    else:
      full_path = '{0:s}.tar.gz'.format(
          os.path.join(gcs_output_folder, self.name))
    build_body = {
        'timeout': '86400s',
        'steps': [{
            'args': [
                '-source_image={0:s}'.format(self.name),
                '-destination_uri={0:s}'.format(full_path),
                '-client_id=api',
            ],
            'name': 'gcr.io/compute-image-tools/gce_vm_image_export:release',
            'env': []
        }],
        'tags': ['gce-daisy', 'gce-daisy-image-export']
    }
    cloud_build = build.GoogleCloudBuild(self.project_id)
    response = cloud_build.CreateBuild(build_body)
    cloud_build.BlockOperation(response)
    common.LOGGER.info('Image {0:s} exported to {1:s}.'.format(
        self.name, full_path))

  def Delete(self):
    """Delete Compute Disk Image from a project.
    """

    gce_image_client = self.GceApi().images()
    request = gce_image_client.delete(
        project=self.project_id, image=self.name)
    response = request.execute()
    self.BlockOperation(response)
