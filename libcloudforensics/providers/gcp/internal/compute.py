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
"""Google Compute Engine functionality."""

import datetime
import os
import re
import subprocess
import time
from typing import Dict, Tuple, List, TYPE_CHECKING, Union, Optional, Any

from googleapiclient.errors import HttpError

from libcloudforensics.providers.gcp.internal import common, build
from libcloudforensics.providers.gcp.internal import compute_base_resource
from libcloudforensics.scripts import utils

if TYPE_CHECKING:
  import googleapiclient


class GoogleCloudCompute(common.GoogleCloudComputeClient):
  """Class representing all Google Cloud Compute objects in a project.

  Attributes:
    project_id: Project name.
    default_zone: Default zone to create new resources in.
  """

  def __init__(self,
               project_id: str,
               default_zone: Optional[str] = None) -> None:
    """Initialize the Google Compute Resources in a project.

    Args:
      project_id (str): Google Cloud project ID.
      default_zone (str): Optional. Default zone to create new resources in.
          None means GlobalZone.
    """

    self.project_id = project_id  # type: str
    self.default_zone = default_zone
    self._instances = None
    self._disks = None
    super(GoogleCloudCompute, self).__init__(self.project_id)

  def Instances(self,
                refresh: bool = True) -> Dict[str, 'GoogleComputeInstance']:
    """Get all instances in the project.

    Args:
      refresh (boolean): Optional. Returns refreshed result if True.

    Returns:
      Dict[str, GoogleComputeInstance]: Dictionary mapping instance names
          (str) to their respective GoogleComputeInstance object.
    """
    if not refresh and self._instances:
      return self._instances
    self._instances = self.ListInstances()  # type: ignore
    return self._instances  # type: ignore

  def Disks(self,
            refresh: bool = True) -> Dict[str, 'GoogleComputeDisk']:
    """Get all disks in the project.

    Args:
      refresh (boolean): Optional. Returns refreshed result if True.

    Returns:
      Dict[str, GoogleComputeDisk]: Dictionary mapping disk names (str) to
          their respective GoogleComputeDisk object.
    """
    if not refresh and self._disks:
      return self._disks
    self._disks = self.ListDisks()  # type: ignore
    return self._disks  # type: ignore

  def ListInstances(self) -> Dict[str, 'GoogleComputeInstance']:
    """List instances in project.

    Returns:
      Dict[str, GoogleComputeInstance]: Dictionary mapping instance names (str)
          to their respective GoogleComputeInstance object.
    """

    instances = {}
    gce_instance_client = self.GceApi().instances()
    responses = common.ExecuteRequest(
        gce_instance_client, 'aggregatedList', {'project': self.project_id})

    for response in responses:
      for zone in response['items']:
        try:
          for instance in response['items'][zone]['instances']:
            _, zone = instance['zone'].rsplit('/', 1)
            name = instance['name']
            instances[name] = GoogleComputeInstance(
                self.project_id, zone, name, labels=instance.get('labels'))
        except KeyError:
          pass

    return instances

  def ListDisks(self) -> Dict[str, 'GoogleComputeDisk']:
    """List disks in project.

    Returns:
      Dict[str, GoogleComputeDisk]: Dictionary mapping disk names (str) to
          their respective GoogleComputeDisk object.
    """

    disks = {}
    gce_disk_client = self.GceApi().disks()
    responses = common.ExecuteRequest(
        gce_disk_client, 'aggregatedList', {'project': self.project_id})

    for response in responses:
      for zone in response['items']:
        try:
          for disk in response['items'][zone]['disks']:
            _, zone = disk['zone'].rsplit('/', 1)
            name = disk['name']
            disks[name] = GoogleComputeDisk(
                self.project_id, zone, name, labels=disk.get('labels'))
        except KeyError:
          pass

    return disks

  def GetInstance(self, instance_name: str) -> 'GoogleComputeInstance':
    """Get instance from project.

    Args:
      instance_name (str): The instance name.

    Returns:
      GoogleComputeInstance: A Google Compute Instance object.

    Raises:
      RuntimeError: If instance does not exist.
    """

    instances = self.Instances()
    instance = instances.get(instance_name)
    if not instance:
      error_msg = 'Instance {0:s} was not found in project {1:s}'.format(
          instance_name, self.project_id)
      raise RuntimeError(error_msg)
    return instance

  def GetDisk(self, disk_name: str) -> 'GoogleComputeDisk':
    """Get a GCP disk object.

    Args:
      disk_name (str): Name of the disk.

    Returns:
      GoogleComputeDisk: Disk object.

    Raises:
      RuntimeError: When the specified disk cannot be found in project.
    """

    disks = self.Disks()
    disk = disks.get(disk_name)
    if not disk:
      error_msg = 'Disk {0:s} was not found in project {1:s}'.format(
          disk_name, self.project_id)
      raise RuntimeError(error_msg)
    return disk

  def CreateDiskFromSnapshot(
      self,
      snapshot: 'GoogleComputeSnapshot',
      disk_name: Optional[str] = None,
      disk_name_prefix: str = '',
      disk_type: str = 'pd-standard') -> 'GoogleComputeDisk':
    """Create a new disk based on a Snapshot.

    Args:
      snapshot (GoogleComputeSnapshot): Snapshot to use.
      disk_name (str): Optional. String to use as new disk name.
      disk_name_prefix (str): Optional. String to prefix the disk name with.
      disk_type (str): Optional. URL of the disk type resource describing
          which disk type to use to create the disk. Default is pd-standard. Use
          pd-ssd to have a SSD disk. You can list all available disk types by
          running the following command: gcloud compute disk-types list

    Returns:
      GoogleComputeDisk: Google Compute Disk.

    Raises:
      RuntimeError: If the disk exists already.
    """

    if not disk_name:
      disk_name = common.GenerateDiskName(snapshot, disk_name_prefix)
    body = {
        'name':
            disk_name,
        'sourceSnapshot':
            snapshot.GetSourceString(),
        'type':
            'projects/{0:s}/zones/{1:s}/diskTypes/{2:s}'.format(
                self.project_id, self.default_zone, disk_type)
    }
    try:
      gce_disks_client = self.GceApi().disks()
      request = gce_disks_client.insert(
          project=self.project_id, zone=self.default_zone, body=body)
      response = request.execute()
    except HttpError as exception:
      if exception.resp.status == 409:
        error_msg = 'Disk {0:s} already exists'.format(disk_name)
        raise RuntimeError(error_msg)
      error_msg = (
          'Unknown error (status: {0:d}) occurred when creating disk '
          'from Snapshot:\n{1!s}').format(exception.resp.status, exception)
      raise RuntimeError(error_msg)
    self.BlockOperation(response, zone=self.default_zone)
    return GoogleComputeDisk(project_id=self.project_id,
                             zone=self.default_zone,  # type: ignore
                             name=disk_name)

  def GetOrCreateAnalysisVm(
      self,
      vm_name: str,
      boot_disk_size: int,
      disk_type: str = 'pd-standard',
      cpu_cores: int = 4,
      image_project: str = 'ubuntu-os-cloud',
      image_family: str = 'ubuntu-1804-lts',
      # pylint: disable=line-too-long
      packages: Optional[List[str]] = None) -> Tuple['GoogleComputeInstance', bool]:
      # pylint: enable=line-too-long
    """Get or create a new virtual machine for analysis purposes.

    If none of the optional parameters are specified, then by default the
    analysis VM that will be created will run Ubuntu 18.04 LTS. A default
    set of forensic tools is also installed (a custom one may be provided
    using the 'packages' argument).

    Args:
      vm_name (str): Name of the virtual machine.
      boot_disk_size (int): The size of the analysis VM boot disk (in GB).
      disk_type (str): Optional. URL of the disk type resource describing
          which disk type to use to create the disk. Default is pd-standard. Use
          pd-ssd to have a SSD disk.
      cpu_cores (int): Optional. Number of CPU cores for the virtual machine.
      image_project (str): Optional. Name of the project where the analysis VM
          image is hosted.
      image_family (str): Optional. Name of the image to use to create the
          analysis VM.
      packages (List[str]): Optional. List of packages to install in the VM.

    Returns:
      Tuple(GoogleComputeInstance, bool): A tuple with a virtual machine object
          and a boolean indicating if the virtual machine was created or not.

    Raises:
      RuntimeError: If virtual machine cannot be created.
    """

    if not self.default_zone:
      raise RuntimeError('Cannot create VM, zone information is missing')

    # Re-use instance if it already exists, or create a new one.
    try:
      instance = self.GetInstance(vm_name)
      created = False
      return instance, created
    except RuntimeError:
      pass

    machine_type = 'zones/{0}/machineTypes/n1-standard-{1:d}'.format(
        self.default_zone, cpu_cores)
    ubuntu_image = self.GceApi().images().getFromFamily(
        project=image_project, family=image_family).execute()
    source_disk_image = ubuntu_image['selfLink']

    startup_script = utils.ReadStartupScript()

    if packages:
      startup_script = startup_script.replace(
          '${packages[@]}', ' '.join(packages))

    config = {
        'name': vm_name,
        'machineType': machine_type,
        'disks': [{
            'boot': True,
            'autoDelete': True,
            'initializeParams': {
                'diskType':
                    'projects/{0:s}/zones/{1:s}/diskTypes/{2:s}'.format(
                        self.project_id, self.default_zone, disk_type),
                'sourceImage':
                    source_disk_image,
                'diskSizeGb':
                    boot_disk_size,
            }
        }],
        'networkInterfaces': [{
            'network':
                'global/networks/default',
            'accessConfigs': [{
                'type': 'ONE_TO_ONE_NAT',
                'name': 'External NAT'
            }]
        }],
        'serviceAccounts': [{
            'email':
                'default',
            'scopes': [
                'https://www.googleapis.com/auth/devstorage.read_write',
                'https://www.googleapis.com/auth/logging.write'
            ]
        }],
        'metadata': {
            'items': [{
                'key': 'startup-script',
                # Analysis software to install.
                'value': startup_script
            }]
        }
    }
    gce_instance_client = self.GceApi().instances()
    request = gce_instance_client.insert(
        project=self.project_id, zone=self.default_zone, body=config)
    response = request.execute()
    self.BlockOperation(response, zone=self.default_zone)
    instance = GoogleComputeInstance(
        project_id=self.project_id, zone=self.default_zone, name=vm_name)
    created = True
    return instance, created

  def ListInstanceByLabels(
      self,
      labels_filter: Dict[str, str],
      filter_union: bool = True) -> Dict[str, 'GoogleComputeInstance']:
    """List VMs in a project with one/all of the provided labels.

    This will call the __ListByLabel on instances() API object
    with the proper labels filter and return a Dict with name and metadata
    for each instance, e.g.:
        {'instance-1': {'zone': 'us-central1-a', 'labels': {'id': '123'}}

    Args:
      labels_filter (Dict[str, str]): A Dict of labels to find e.g.
          {'id': '123'}.
      filter_union (bool): Optional. A Boolean; True to get the union of all
          filters, False to get the intersection.

    Returns:
      Dict[str, GoogleComputeInstance]: Dictionary mapping instances to their
          respective GoogleComputeInstance object.
    """

    instance_service_object = self.GceApi().instances()
    return self.__ListByLabel(  # type: ignore
        labels_filter, instance_service_object, filter_union)

  def ListDiskByLabels(
      self,
      labels_filter: Dict[str, str],
      filter_union: bool = True) -> Dict[str, 'GoogleComputeDisk']:
    """List Disks in a project with one/all of the provided labels.

    This will call the __ListByLabel on disks() API object
    with the proper labels filter and return a Dict with name and metadata
    for each disk, e.g.:
        {'disk-1': {'zone': 'us-central1-a', 'labels': {'id': '123'}}

    Args:
      labels_filter (Dict[str, str]): A Dict of labels to find e.g.
          {'id': '123'}.
      filter_union (bool): Optional. A Boolean; True to get the union of all
          filters, False to get the intersection.

    Returns:
      Dict[str, GoogleComputeDisk]: Dictionary mapping disks to their
          respective GoogleComputeDisk object.
    """

    disk_service_object = self.GceApi().disks()
    return self.__ListByLabel(  # type: ignore
        labels_filter, disk_service_object, filter_union)

  def __ListByLabel(
      self,
      labels_filter: Dict[str, str],
      service_object: 'googleapiclient.discovery.Resource',
      filter_union: bool) -> Dict[str, Union['GoogleComputeInstance', 'GoogleComputeDisk']]:  # pylint: disable=line-too-long
    """List Disks/VMs in a project with one/all of the provided labels.

    Private method used to select different compute resources by labels.

    Args:
      labels_filter (Dict[str, str]): A Dict of labels to find e.g.
          {'id': '123'}.
      service_object (googleapiclient.discovery.Resource): Google Compute Engine
          (Disk | Instance) service object.
      filter_union (bool): A boolean; True to get the union of all filters,
          False to get the intersection.

    Returns:
      Dict[str, GoogleComputeInstance|GoogleComputeDisk]: Dictionary mapping
          instances/disks to their respective GoogleComputeInstance /
          GoogleComputeDisk object.

    Raises:
      RuntimeError: If the operation doesn't complete on GCP.
    """

    if not isinstance(filter_union, bool):
      error_msg = (
          'filter_union parameter must be of Type boolean {0:s} is an '
          'invalid argument.').format(filter_union)
      raise RuntimeError(error_msg)

    # pylint: disable=line-too-long
    resource_dict = {}  # type: Dict[str, Union[GoogleComputeInstance, GoogleComputeDisk]]
    # pylint: enable=line-too-long
    filter_expression = ''
    operation = 'AND' if filter_union else 'OR'
    for key, value in labels_filter.items():
      filter_expression += 'labels.{0:s}={1:s} {2:s} '.format(
          key, value, operation)
    filter_expression = filter_expression[:-(len(operation) + 1)]

    request = service_object.aggregatedList(
        project=self.project_id, filter=filter_expression)
    while request is not None:
      response = request.execute()

      for item in response['items'].items():
        region_or_zone_string, resource_scoped_list = item

        if 'warning' not in resource_scoped_list.keys():
          _, zone = region_or_zone_string.rsplit('/', 1)
          # Only one of the following loops will execute since the method is
          # called either with a service object Instances or Disks.
          for resource in resource_scoped_list.get('instances', []):
            name = resource['name']
            resource_dict[name] = GoogleComputeInstance(
                self.project_id, zone, name, labels=resource['labels'])

          for resource in resource_scoped_list.get('disks', []):
            name = resource['name']
            resource_dict[name] = GoogleComputeDisk(
                self.project_id, zone, name, labels=resource['labels'])

      request = service_object.aggregatedList_next(
          previous_request=request, previous_response=response)
    return resource_dict

  def CreateImageFromDisk(self,
                          src_disk: 'GoogleComputeDisk',
                          name: Optional[str] = None) -> 'GoogleComputeImage':
    """Creates an image from a persistent disk.

    Args:
      src_disk (GoogleComputeDisk): Source disk for the image.
      name (str): Optional. Name of the image to create. Default
          is [src_disk]_image.

    Returns:
      GoogleComputeImage: A Google Compute Image object.
    """
    if not name:
      name = '{0:s}_image'.format(src_disk.name)
    image_body = {
        'name':
            name,
        'sourceDisk':
            'projects/{project_id}/zones/{zone}/disks/{src_disk}'.format(
                project_id=src_disk.project_id, zone=src_disk.zone,
                src_disk=src_disk.name)
    }
    gce_image_client = self.GceApi().images()
    request = gce_image_client.insert(
        project=self.project_id, body=image_body, forceCreate=True)
    response = request.execute()
    self.BlockOperation(response)
    return GoogleComputeImage(self.project_id, None, name)  # type: ignore


class GoogleComputeInstance(compute_base_resource.GoogleComputeBaseResource):
  """Class representing a Google Compute Engine virtual machine."""

  def GetOperation(self) -> Dict[str, Any]:
    """Get API operation object for the virtual machine.

    Returns:
      Dict: An API operation object for a Google Compute Engine
          virtual machine.
    """

    gce_instance_client = self.GceApi().instances()
    request = gce_instance_client.get(
        instance=self.name, project=self.project_id, zone=self.zone)
    response = request.execute()  # type: Dict[str, Any]
    return response

  def GetBootDisk(self) -> Union['GoogleComputeDisk', None]:
    """Get the virtual machine boot disk.

    Returns:
      GoogleComputeDisk: Disk object or None if no disk can be found.
    """

    for disk in self.GetValue('disks'):
      if disk['boot']:  # type: ignore
        disk_name = disk['source'].split('/')[-1]  # type: ignore
        return GoogleCloudCompute(
            self.project_id).GetDisk(disk_name=disk_name)
    return None

  def GetDisk(self, disk_name: str) -> 'GoogleComputeDisk':
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
      if disk['source'].split('/')[-1] == disk_name:  # type: ignore
        return GoogleCloudCompute(
            self.project_id).GetDisk(disk_name=disk_name)
    error_msg = 'Disk name "{0:s}" not attached to instance'.format(disk_name)
    raise RuntimeError(error_msg)

  def ListDisks(self) -> Dict[str, 'GoogleComputeDisk']:
    """List all disks for the virtual machine.

    Returns:
      Dict[str, GoogleComputeDisk]: Dictionary mapping disk names to their
          respective GoogleComputeDisk object.
    """

    disks = {}
    disk_names = [disk['source'].split('/')[-1]  # type: ignore
                  for disk in self.GetValue('disks')]
    for name in disk_names:
      disks[name] = self.GetDisk(name)
    return disks

  def __SshConnection(self) -> None:
    """Create an SSH connection to the virtual machine."""

    devnull = open(os.devnull, 'w')
    subprocess.check_call([
        'gcloud', 'compute', '--project', self.project_id, 'ssh',
        '--zone', self.zone, self.name
    ], stderr=devnull)

  def Ssh(self) -> None:
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

  def AttachDisk(self,
                 disk: 'GoogleComputeDisk',
                 read_write: bool = False) -> None:
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

  def DetachDisk(self, disk: 'GoogleComputeDisk') -> None:
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


class GoogleComputeDisk(compute_base_resource.GoogleComputeBaseResource):
  """Class representing a Compute Engine disk."""

  def GetOperation(self) -> Dict[str, Any]:
    """Get API operation object for the disk.

    Returns:
      Dict: An API operation object for a Google Compute Engine disk.
    """

    gce_disk_client = self.GceApi().disks()
    request = gce_disk_client.get(
        disk=self.name, project=self.project_id, zone=self.zone)
    response = request.execute()  # type: Dict[str, Any]
    return response

  def Snapshot(
      self, snapshot_name: Optional[str] = None) -> 'GoogleComputeSnapshot':
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


class GoogleComputeSnapshot(compute_base_resource.GoogleComputeBaseResource):
  """Class representing a Compute Engine Snapshot.

  Attributes:
    disk (GoogleComputeDisk): Disk used for the Snapshot.
  """

  def __init__(self, disk: 'GoogleComputeDisk', name: str) -> None:
    """Initialize the Snapshot object.

    Args:
      disk (GoogleComputeDisk): Disk used for the Snapshot.
      name (str): Name of the Snapshot.
    """

    super(GoogleComputeSnapshot, self).__init__(
        project_id=disk.project_id, zone=disk.zone, name=name)
    self.disk = disk

  def GetOperation(self) -> Dict[str, Any]:
    """Get API operation object for the Snapshot.

    Returns:
      Dict: An API operation object for a Google Compute Engine Snapshot.
    """

    gce_snapshot_client = self.GceApi().snapshots()
    request = gce_snapshot_client.get(
        snapshot=self.name, project=self.project_id)
    response = request.execute()  # type: Dict[str, Any]
    return response

  def Delete(self) -> None:
    """Delete a Snapshot."""

    common.LOGGER.info(
        self.FormatLogMessage(
            'Deleted Snapshot: {0}'.format(self.name)))
    gce_snapshot_client = self.GceApi().snapshots()
    request = gce_snapshot_client.delete(
        project=self.project_id, snapshot=self.name)
    response = request.execute()
    self.BlockOperation(response)


class GoogleComputeImage(compute_base_resource.GoogleComputeBaseResource):
  """Class representing a Compute Engine Image.

  Attributes:
    disk (GoogleComputeDisk): Disk used for the Snapshot.
  """

  def GetOperation(self) -> Dict[str, Any]:
    """Get API operation object for the image.

    Returns:
      Dict: Holding an API operation object for a Google Compute Engine Image.
    """

    gce_image_client = self.GceApi().images()
    request = gce_image_client.get(
        project=self.project_id, image=self.name)
    response = request.execute()  # type: Dict[str, Any]
    return response

  def ExportImage(self,
                  gcs_output_folder: str,
                  output_name: Optional[str] = None) -> None:
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

  def Delete(self) -> None:
    """Delete Compute Disk Image from a project.
    """

    gce_image_client = self.GceApi().images()
    request = gce_image_client.delete(
        project=self.project_id, image=self.name)
    response = request.execute()
    self.BlockOperation(response)
