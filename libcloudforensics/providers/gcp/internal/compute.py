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
"""Google Compute Engine functionalities."""

import os
import subprocess
import time
from typing import Dict, Tuple, List, TYPE_CHECKING, Union, Optional, Any

from googleapiclient.errors import HttpError

from libcloudforensics.providers.gcp.internal import build
from libcloudforensics.providers.gcp.internal import common
from libcloudforensics.providers.gcp.internal import compute_base_resource
from libcloudforensics.scripts import utils
from libcloudforensics import logging_utils
from libcloudforensics import errors

if TYPE_CHECKING:
  import googleapiclient

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)

# Default general purpose machine type used for the forensics VM
DEFAULT_MACHINE_TYPE = 'e2-standard'

# Supported number of cores for the default machine type
# https://cloud.google.com/compute/docs/general-purpose-machines#e2-standard
E2_STANDARD_CPU_CORES = [2, 4, 8, 16, 32]

# Numerical policy_level value for non-hierarchical FW rules
NON_HIERARCHICAL_FW_POLICY_LEVEL = 999

class GoogleCloudCompute(common.GoogleCloudComputeClient):
  """Class representing all Google Cloud Compute objects in a project.

  Attributes:
    project_id: Project name.
    default_zone: Default zone to create new resources in.
  """

  def __init__(
      self, project_id: str, default_zone: Optional[str] = None) -> None:
    """Initialize the Google Compute Resources in a project.

    Args:
      project_id (str): Google Cloud project ID.
      default_zone (str): Optional. Default zone to create new resources in.
          Default is us-central1-f.
    """

    self.project_id = project_id  # type: str
    self.default_zone = default_zone or 'us-central1-f'
    self._instances = {}  # type: Dict[str, GoogleComputeInstance]
    self._disks = {}  # type: Dict[str, GoogleComputeDisk]
    super().__init__(self.project_id)

  def Instances(self,
                refresh: bool = True
                ) -> Dict[str, 'GoogleComputeInstance']:
    """Get all instances in the project.

    Args:
      refresh (boolean): Optional. Returns refreshed result if True.

    Returns:
      Dict[str, GoogleComputeInstance]: Dictionary mapping instance names
          (str) to their respective GoogleComputeInstance object.
    """
    if not refresh and self._instances:
      return self._instances
    self._instances = self.ListInstances()
    return self._instances

  def Disks(self,
            refresh: bool = True
            ) -> Dict[str, 'GoogleComputeDisk']:
    """Get all disks in the project.

    Args:
      refresh (boolean): Optional. Returns refreshed result if True.

    Returns:
      Dict[str, GoogleComputeDisk]: Dictionary mapping disk names (str) to
          their respective GoogleComputeDisk object.
    """
    if not refresh and self._disks:
      return self._disks
    self._disks = self.ListDisks()
    return self._disks

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
            deletion_protection = instance.get('deletionProtection', False)
            instances[name] = GoogleComputeInstance(
                self.project_id,
                zone,
                name,
                labels=instance.get('labels'),
                deletion_protection=deletion_protection)
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
      ResourceNotFoundError: If instance does not exist.
    """

    instances = self.Instances()
    instance = instances.get(instance_name)
    if not instance:
      raise errors.ResourceNotFoundError(
          'Instance {0:s} was not found in project {1:s}'.format(
              instance_name, self.project_id), __name__)
    return instance

  def GetDisk(self, disk_name: str) -> 'GoogleComputeDisk':
    """Get a GCP disk object.

    Args:
      disk_name (str): Name of the disk.

    Returns:
      GoogleComputeDisk: Disk object.

    Raises:
      ResourceNotFoundError: When the specified disk cannot be found in project.
    """

    disks = self.Disks()
    disk = disks.get(disk_name)
    if not disk:
      raise errors.ResourceNotFoundError(
          'Disk {0:s} was not found in project {1:s}'.format(
              disk_name, self.project_id), __name__)
    return disk

  def CreateDiskFromSnapshot(
      self,
      snapshot: 'GoogleComputeSnapshot',
      disk_name: Optional[str] = None,
      disk_name_prefix: Optional[str] = None,
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
      ResourceCreationError: If the disk could not be created.
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
        raise errors.ResourceCreationError(
            'Disk {0:s} already exists: {1!s}'.format(disk_name, exception),
            __name__) from exception
      raise errors.ResourceCreationError(
          'Unknown error occurred when creating disk from Snapshot:'
          ' {0!s}'.format(exception), __name__) from exception
    self.BlockOperation(response, zone=self.default_zone)
    return GoogleComputeDisk(
        project_id=self.project_id,
        zone=self.default_zone,
        name=disk_name)

  def GetOrCreateAnalysisVm(self,
                            vm_name: str,
                            boot_disk_size: int,
                            disk_type: str = 'pd-standard',
                            cpu_cores: int = 4,
                            image_project: str = 'ubuntu-os-cloud',
                            image_family: str = 'ubuntu-1804-lts',
                            packages: Optional[List[str]] = None
                            ) -> Tuple['GoogleComputeInstance', bool]:
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
      ValueError: If the requested number of CPU cores is not available for the
          machine type.
    """

    # Re-use instance if it already exists, or create a new one.
    try:
      instance = self.GetInstance(vm_name)
      created = False
      return instance, created
    except errors.ResourceNotFoundError:
      pass

    if cpu_cores not in E2_STANDARD_CPU_CORES:
      raise ValueError(
          'Number of requested CPU cores ({0:d}) not available for machine type'
          ' {1:s}'.format(cpu_cores, DEFAULT_MACHINE_TYPE))

    machine_type = 'zones/{0:s}/machineTypes/{1:s}-{2:d}'.format(
        self.default_zone, DEFAULT_MACHINE_TYPE, cpu_cores)
    ubuntu_image = self.GceApi().images().getFromFamily(
        project=image_project, family=image_family).execute()
    source_disk_image = ubuntu_image['selfLink']

    startup_script = utils.ReadStartupScript(utils.FORENSICS_STARTUP_SCRIPT_GCP)

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
                'type': 'ONE_TO_ONE_NAT', 'name': 'External NAT'
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
                'key': 'startup-script',  # Analysis software to install.
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

  def ListInstanceByLabels(self,
                           labels_filter: Dict[str, str],
                           filter_union: bool = True
                           )-> Dict[str, 'GoogleComputeInstance']:
    """List VMs in a project with one/all of the provided labels.

    This will call the _ListByLabel function on an instances() API object
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
    return self._ListByLabel(
        labels_filter, instance_service_object, filter_union)

  def ListDiskByLabels(self,
                       labels_filter: Dict[str, str],
                       filter_union: bool = True
                       ) -> Dict[str, 'GoogleComputeDisk']:
    """List Disks in a project with one/all of the provided labels.

    This will call the _ListByLabel function on a disks() API object
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
    return self._ListByLabel(
        labels_filter, disk_service_object, filter_union)

  def ListReservedExternalIps(self, zone: str) -> List[str]:
    """Lists all static external IP addresses that are available to a zone.

    The method first converts the zone to a region,
    and then queries the GCE addresses resource.

    Args:
      zone (str): The zone in which the returned IPs would be available.

    Returns:
      List[str]: The list of available IPs in the specified zone.

    Raises:
      ValueError: If the zone is malformed.
      errors.ResourceNotFoundError: If the request did not succeed.
    """
    # Convert zone to region
    zone_parts = zone.split('-')
    if len(zone_parts) != 3:
      raise ValueError('Invalid zone: {0:s}.'.format(zone))
    region = '-'.join(zone_parts[:-1])
    # Request list of addresses
    addresses_client = self.GceApi().addresses()
    params = {
      'project': self.project_id,
      'region': region
   }
    try:
      responses = common.ExecuteRequest(addresses_client, 'list', params)
    except HttpError as exception:
      message = 'Unable to list external IPs for {0:s}: {1:s}'.format(
        self.project_id,
        exception.error_details)
      raise errors.ResourceNotFoundError(message, __name__) from exception
    ip_addresses = []
    for response in responses:
      for address in response.get('items', []):
        is_reserved = address['status'] == 'RESERVED'
        is_external = address['addressType'] == 'EXTERNAL'
        if is_reserved and is_external:
          ip_address = address['address']
          ip_addresses.append(ip_address)
    return ip_addresses

  def _ListByLabel(self,
                   labels_filter: Dict[str, str],
                   service_object: 'googleapiclient.discovery.Resource',
                   filter_union: bool) -> Dict[str, Any]:
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
      TypeError: If filter_union is not of type bool
      RuntimeError: If the operation doesn't complete on GCP.
    """

    if not isinstance(filter_union, bool):
      raise TypeError('Filter_union parameter must be of Type boolean. {0:s} '
                      'is an invalid argument.'.format(filter_union))

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
          is [src_disk.name]-[TIMESTAMP('%Y%m%d%H%M%S')].

    Returns:
      GoogleComputeImage: A Google Compute Image object.

    Raises:
      InvalidNameError: If the GCE Image name is invalid.
    """

    if name:
      if not common.REGEX_DISK_NAME.match(name):
        raise errors.InvalidNameError(
            'Image name {0:s} does not comply with {1:s}'.format(
                name, common.REGEX_DISK_NAME.pattern), __name__)
      name = name[:common.COMPUTE_NAME_LIMIT]
    else:
      name = common.GenerateUniqueInstanceName(src_disk.name,
                                               common.COMPUTE_NAME_LIMIT)
    image_body = {
        'name':
            name,
        'sourceDisk':
            'projects/{project_id}/zones/{zone}/disks/{src_disk}'.format(
                project_id=src_disk.project_id,
                zone=src_disk.zone,
                src_disk=src_disk.name)
    }
    gce_image_client = self.GceApi().images()
    request = gce_image_client.insert(
        project=self.project_id, body=image_body, forceCreate=True)
    response = request.execute()
    self.BlockOperation(response)
    return GoogleComputeImage(self.project_id, '', name)

  def CreateImageFromGcsTarGz(
      self,
      gcs_uri: str,
      name: Optional[str] = None) -> 'GoogleComputeImage':
    """Creates a GCE image from a Gzip compressed Tar archive in GCS.

    Args:
      gcs_uri (str): Path to the compressed image archive
          (image.tar.gz) in Cloud Storage. It must be a gzip compressed
          tar archive with the extension .tar.gz.
          ex: 'https://storage.cloud.google.com/foo/bar.tar.gz'
          'gs://foo/bar.tar.gz'
          'foo/bar.tar.gz'
      name (str): Optional. Name of the image to create. Default
          is [src_disk.name]-[TIMESTAMP('%Y%m%d%H%M%S')].

    Returns:
      GoogleComputeImage: A Google Compute Image object.

    Raises:
      InvalidNameError: If the GCE Image name is invalid.
      ValueError: If the extension of the archived image is invalid.
    """

    if name:
      if not common.REGEX_DISK_NAME.match(name):
        raise errors.InvalidNameError(
            'Image name {0:s} does not comply with {1:s}'.format(
                name, common.REGEX_DISK_NAME.pattern), __name__)
      name = name[:common.COMPUTE_NAME_LIMIT]
    else:
      name = common.GenerateUniqueInstanceName('imported-image',
                                               common.COMPUTE_NAME_LIMIT)

    if not gcs_uri.lower().endswith('.tar.gz'):
      raise ValueError(
          'Image imported from {0:s} must be a GZIP compressed TAR '
          'archive with the extension: .tar.gz'.format(gcs_uri))
    gcs_uri = os.path.relpath(gcs_uri, 'gs://')
    if not gcs_uri.startswith(common.STORAGE_LINK_URL):
      gcs_uri = os.path.join(common.STORAGE_LINK_URL, gcs_uri)
    image_body = {
        'name': name,
        'rawDisk': {
            'source': gcs_uri
        }
    }
    gce_image_client = self.GceApi().images()
    request = gce_image_client.insert(
        project=self.project_id, body=image_body, forceCreate=True)
    response = request.execute()
    self.BlockOperation(response)
    return GoogleComputeImage(self.project_id, '', name)

  def CreateDiskFromImage(self,
                          src_image: 'GoogleComputeImage',
                          zone: str,
                          name: Optional[str] = None) -> 'GoogleComputeDisk':
    """Creates a GCE persistent disk from a GCE image.

    Args:
      src_image (GoogleComputeImage): Source image for the disk.
      zone (str): Zone to create the new disk in.
      name (str): Optional. Name of the disk to create. Default
          is [src_image.name]-[TIMESTAMP('%Y%m%d%H%M%S')].

    Returns:
      GoogleComputeDisk: A Google Compute Disk object.

    Raises:
      InvalidNameError: If GCE disk name is invalid.
    """

    if name:
      if not common.REGEX_DISK_NAME.match(name):
        raise errors.InvalidNameError(
            'Disk name {0:s} does not comply with {1:s}'.format(
                name, common.REGEX_DISK_NAME.pattern), __name__)
      name = name[:common.COMPUTE_NAME_LIMIT]
    else:
      name = common.GenerateUniqueInstanceName(src_image.name,
                                               common.COMPUTE_NAME_LIMIT)

    disk_body = {
        'name':
            name,
        'sourceImage':
            'projects/{project_id}/global/images/{src_image}'.format(
                project_id=src_image.project_id, src_image=src_image.name)
    }
    gce_disk_client = self.GceApi().disks()
    request = gce_disk_client.insert(
        project=self.project_id, body=disk_body, zone=zone)
    response = request.execute()
    self.BlockOperation(response, zone)
    return GoogleComputeDisk(self.project_id, zone, name)

  def ImportImageFromStorage(self,
                             storage_image_path: str,
                             image_name: Optional[str] = None,
                             bootable: bool = False,
                             os_name: Optional[str] = None,
                             guest_environment: bool = True) -> 'GoogleComputeImage':  # pylint: disable=line-too-long
    """Import GCE image from Cloud storage.

    The import tool supports raw disk images and most virtual disk
    file formats, valid import formats are:
    [raw (dd), qcow2, qcow , vmdk, vdi, vhd, vhdx, qed, vpc].

    Args:
      storage_image_path (str): Path to the source image in Cloud Storage.
      image_name (str): Optional. Name of the imported image,
          default is "imported-image-" appended with a timestamp
          in "%Y%m%d%H%M%S" format.
      bootable (bool): Optional. True if the imported image is bootable.
          Default is False. If True the os_name must be specified.
      os_name (str): Optional. Name of the operating system on the bootable
          image. For supported versions please see:
          https://cloud.google.com/sdk/gcloud/reference/compute/images/import#--os  # pylint: disable=line-too-long
          For known limitations please see:
          https://googlecloudplatform.github.io/compute-image-tools/image-import.html#compatibility-and-known-limitations  # pylint: disable=line-too-long
      guest_environment (bool): Optional. Install Google Guest Environment on a
          bootable image. Relevant only if image is bootable. Default True.

    Returns:
      GoogleComputeImage: A Google Compute Image object.

    Raises:
      ValueError: If bootable is True and os_name not specified.
      InvalidNameError: If imported image name is invalid.
    """

    supported_os = [
        'centos-6', 'centos-7', 'centos-8', 'debian-8', 'debian-9',
        'opensuse-15', 'rhel-6', 'rhel-6-byol', 'rhel-7', 'rhel-7-byol',
        'rhel-8', 'rhel-8-byol', 'sles-12-byol', 'sles-15-byol',
        'ubuntu-1404', 'ubuntu-1604', 'ubuntu-1804', 'windows-10-x64-byol',
        'windows-10-x86-byol', 'windows-2008r2', 'windows-2008r2-byol',
        'windows-2012', 'windows-2012-byol', 'windows-2012r2',
        'windows-2012r2-byol', 'windows-2016', 'windows-2016-byol',
        'windows-2019', 'windows-2019-byol', 'windows-7-x64-byol',
        'windows-7-x86-byol', 'windows-8-x64-byol', 'windows-8-x86-byol']

    if not bootable:
      img_type = '-data_disk'
    elif not os_name:
      raise ValueError(
          'For bootable images, operating system name'
          ' (os_name) must be specified.')
    elif os_name not in supported_os:
      logger.warning(
          ('Operating system of the imported image is not within the '
           'supported list:\n{0:s}\nFor the up-to-date list please refer '
           'to:\n{1:s}').format(
               ', '.join(supported_os),
               'https://cloud.google.com/sdk/gcloud/reference/compute/images/import#--os'))  # pylint: disable=line-too-long
    else:
      img_type = '-os={0:s}'.format(os_name)
    if image_name:
      if not common.REGEX_DISK_NAME.match(image_name):
        raise errors.InvalidNameError(
            'Imported image name {0:s} does not comply with {1:s}'.format(
                image_name, common.REGEX_DISK_NAME.pattern), __name__)
      image_name = image_name[:common.COMPUTE_NAME_LIMIT]
    else:
      image_name = common.GenerateUniqueInstanceName('imported-image',
                                                     common.COMPUTE_NAME_LIMIT)
    args_list = [
        '-image_name={0:s}'.format(image_name),
        '-source_file={0:s}'.format(storage_image_path),
        '-timeout=86400s',
        '-client_id=api',
        img_type
    ]
    if bootable and not guest_environment:
      args_list.append('-no_guest_environment')
    build_body = {
        'steps': [{
            'args': args_list,
            'name': 'gcr.io/compute-image-tools/gce_vm_image_import:release',
            'env': ['BUILD_ID=$BUILD_ID']
        }],
        'timeout': '86400s',
        'tags': ['gce-daisy', 'gce-daisy-image-import']
    }
    cloud_build = build.GoogleCloudBuild(self.project_id)
    response = cloud_build.CreateBuild(build_body)
    cloud_build.BlockOperation(response)
    logger.info(
        'Image {0:s} imported as GCE image {1:s}.'.format(
            storage_image_path, image_name))
    return GoogleComputeImage(self.project_id, '', image_name)

  def InsertFirewallRule(self, body: Dict[str, Any]) -> None:
    """Insert a firewall rule to the project.

    Args:
      body (Dict): The request body.
          https://googleapis.github.io/google-api-python-client/docs/dyn/compute_v1.firewalls.html#insert  # pylint: disable=line-too-long
    """

    logger.info( 'Inserting firewall rule {0:s}, '
            'targeting tags: {1!s}.'.format(body['name'], body['targetTags'] ))
    firewall_client = self.GceApi().firewalls()
    request = firewall_client.insert(project=self.project_id, body=body)
    response = request.execute()
    self.BlockOperation(response)


class GoogleComputeInstance(compute_base_resource.GoogleComputeBaseResource):
  """Class representing a Google Compute Engine virtual machine."""

  def GetOperation(self) -> Dict[str, Any]:
    """Get API operation object for the virtual machine.

    Returns:
      Dict: An API operation object for a Google Compute Engine
          virtual machine.
          https://cloud.google.com/compute/docs/reference/rest/v1/instances/get#response-body
    """

    gce_instance_client = self.GceApi().instances()
    request = gce_instance_client.get(
        instance=self.name, project=self.project_id, zone=self.zone)
    response = request.execute()  # type: Dict[str, Any]
    return response

  def GetBootDisk(self) -> 'GoogleComputeDisk':
    """Get the virtual machine boot disk.

    Returns:
      GoogleComputeDisk: Disk object.

    Raises:
      ResourceNotFoundError: If no boot disk could be found.
    """

    for disk in self.GetValue('disks'):
      if disk['boot']:
        disk_name = disk['source'].split('/')[-1]
        return GoogleCloudCompute(self.project_id).GetDisk(disk_name=disk_name)
    raise errors.ResourceNotFoundError(
        'Boot disk not found for instance {0:s}'.format(self.name),
        __name__)

  def GetDisk(self, disk_name: str) -> 'GoogleComputeDisk':
    """Gets a disk attached to this virtual machine disk by name.

    Args:
      disk_name (str): The name of the disk to get.

    Returns:
      GoogleComputeDisk: Disk object.

    Raises:
      ResourceNotFoundError: If disk name is not found among those attached to
          the instance.
    """

    for disk in self.GetValue('disks'):
      if disk['source'].split('/')[-1] == disk_name:
        return GoogleCloudCompute(self.project_id).GetDisk(disk_name=disk_name)
    raise errors.ResourceNotFoundError(
        'Disk {0:s} was not found in instance {1:s}'.format(
            disk_name, self.name), __name__)

  def ListDisks(self) -> Dict[str, 'GoogleComputeDisk']:
    """List all disks for the virtual machine.

    Returns:
      Dict[str, GoogleComputeDisk]: Dictionary mapping disk names to their
          respective GoogleComputeDisk object.
    """

    disks = {}
    disk_names = [
        disk['source'].split('/')[-1]
        for disk in self.GetValue('disks')
    ]
    for name in disk_names:
      disks[name] = self.GetDisk(name)
    return disks

  def _SshConnection(self) -> None:
    """Create an SSH connection to the virtual machine."""

    with open(os.devnull, 'w') as devnull:
      cmd_list = ['gcloud',
                  'compute',
                  '--project',
                  self.project_id,
                  'ssh',
                  '--zone',
                  self.zone,
                  self.name]
      subprocess.check_call(cmd_list, stderr=devnull)

  def Ssh(self) -> None:
    """Connect to the virtual machine over SSH."""

    max_retries = 100  # times to retry the connection
    retries = 0

    logger.info(
        self.FormatLogMessage('Connecting to analysis VM over SSH'))

    while retries < max_retries:
      try:
        self._SshConnection()
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

    logger.info(
        self.FormatLogMessage(
            'Attaching {0:s} to VM {1:s} in {2:s} mode'.format(
                disk.name, self.name, mode)))

    operation_config = {
        'mode': mode,
        'source': disk.GetSourceString(),
        'deviceName': disk.name,
        'boot': False,
        'autoDelete': False,
    }
    gce_instance_client = self.GceApi().instances()
    request = gce_instance_client.attachDisk(
        instance=self.name,
        project=self.project_id,
        zone=self.zone,
        body=operation_config)
    response = request.execute()
    self.BlockOperation(response, zone=self.zone)

  def DetachDisk(self, disk: 'GoogleComputeDisk') -> None:
    """Detach a disk from the virtual machine.

    Args:
      disk (GoogleComputeDisk): Disk to detach.
    """

    gce_instance_client = self.GceApi().instances()
    request = gce_instance_client.detachDisk(
        instance=self.name,
        project=self.project_id,
        zone=self.zone,
        deviceName=disk.name)
    response = request.execute()
    self.BlockOperation(response, zone=self.zone)

  def Delete(
      self, delete_disks: bool = False, force_delete: bool = False) -> None:
    """Delete an Instance.

    Args:
      delete_disks (bool): force delete all attached disks (ignores the 'Keep
          when instance is deleted' bit).
      force_delete (bool): force delete the instance, even if deletionProtection
          is set to true.
    """
    if not force_delete and self.deletion_protection:
      logger.warning('This instance is protected against accidental deletion.'
                     'To delete it, pass the flag force_delete=True.')
      # We can abort directly since calling the API will fail.
      return

    disks_to_delete = []
    if delete_disks:
      disks_to_delete = [
          disk['source'].split('/')[-1] for disk in self.GetValue('disks')]

    gce_instance_client = self.GceApi().instances()

    if force_delete and self.deletion_protection:
      logger.info('Deletion protection detected. Disabling due to '
                  'force_delete=True')
      try:
        request = gce_instance_client.setDeletionProtection(
            project=self.project_id,
            zone=self.zone,
            resource=self.name,
            deletionProtection=False)
        response = request.execute()
      except HttpError as exception:
        logger.error('Unable to toggle deleteProtection on instance {0:s}: '
                     '{1:s}'.format(self.name, str(exception)))
        raise errors.ResourceDeletionError(
            'Unable to toggle deleteProtection on instance {0:s}: {1!s}'.format(
                self.name, exception), __name__) from exception
      self.BlockOperation(response, zone=self.zone)

    logger.info(
        self.FormatLogMessage('Deleting Instance: {0:s}'.format(self.name)))
    try:
      request = gce_instance_client.delete(
          project=self.project_id, instance=self.name, zone=self.zone)
      response = request.execute()
    except HttpError as exception:
      if exception.resp.status == 404:
        logger.warning(
            ('Can not find resource {0:s}, it might be already '
             'deleted. API call resulted in the following error: '
             '{1:s}').format(self.name, str(exception)))
      else:
        logger.error((
            'While deleting GCE instance {0:s} the following error occurred: '
            '{1:s}').format(self.name, str(exception)))
        raise errors.ResourceDeletionError(
            'Could not delete instance {0:s}: {1!s}'.format(
                self.name, exception), __name__) from exception

    self.BlockOperation(response, zone=self.zone)

    for disk_name in disks_to_delete:
      try:
        disk = GoogleCloudCompute(self.project_id).GetDisk(disk_name=disk_name)
        disk.Delete()
      except (errors.ResourceDeletionError, errors.ResourceNotFoundError):
        logger.info(
            self.FormatLogMessage(
                'Could not find disk: {0:s}, skipping'.format(disk_name)))

  def AssignExternalIp(self,
                       net_if: str,
                       ip_addr: Optional[str] = None) -> None:
    """Assigns an external IP to an instance's network interface.

    The instance must not have an IP assigned to the network interface when
    calling this method. If the IP address is specified, it must be one that
    is available to the project.

    Args:
      net_if (str): The instance's network interface to which the IP address
        must be assigned.
      ip_addr (str): Optional. The static IP address that exposes the network
        interface. If None, the assigned IP address will be ephemeral.

    Raises:
      errors.ResourceCreationError: If the assignment did not succeed.
    """
    body = {}
    if ip_addr is not None:
      body['natIP'] = ip_addr
    instances_client = self.GceApi().instances()
    params = {
      'project': self.project_id,
      'zone': self.zone,
      'instance': self.name,
      'networkInterface': net_if,
      'body': body
    }
    try:
      # Safe to unpack, as the response is not paged
      response = common.ExecuteRequest(instances_client,
                                       'addAccessConfig',
                                       params)[0]
    except HttpError as exception:
      message = 'Unable to assign IP to {0:s}: {1:s}'.format(
        self.name,
        exception.error_details)
      raise errors.ResourceCreationError(message, __name__) from exception
    self.BlockOperation(response, self.zone)

  def RemoveExternalIps(self) -> Dict[str, str]:
    """Removes any external IP of the instance, breaking ongoing connections.

    Note that if the instance's IP address was static, that
    the IP will still belong to the project.

    Returns:
      Dict[str, str]: A mapping from an instance's network
        interfaces to the corresponding removed external IP.

    Raises:
      errors.ResourceDeletionError: If the removal did not succeed.
    """
    external_ip_addresses = {}
    # Iterate through instance's network interfaces, removing
    # all access configurations (NAT)
    instance_info = self.GetOperation()
    for network_interface in instance_info.get('networkInterfaces', []):
      access_configs = network_interface.get('accessConfigs', [])
      if len(access_configs) == 0:
        # No way to access this network interface externally,
        # skip the removal
        continue
      network_interface_name = network_interface['name']
      # From the `get` operation response documentation, for
      # the `networkInterfaces[].accessConfigs[]` field:
      #
      # > Currently, only one access config, ONE_TO_ONE_NAT, is
      #   supported.
      #
      # It is thus safe to access only the first element.
      access_config = access_configs[0]
      access_config_name = access_config['name']
      external_ip_address = access_config['natIP']
      logger.info(
        'Deleting access config for {0:s} (external IP: {1:s})'.format(
          self.name,
          external_ip_address,
        ))
      # Execute the IP address removal by deleting access config
      gce_instance_client = self.GceApi().instances()
      params = {
        'project': self.project_id,
        'zone': self.zone,
        'instance': self.name,
        'accessConfig': access_config_name,
        'networkInterface': network_interface_name
      }
      try:
        # Safe to unpack since this response is not paged
        response = common.ExecuteRequest(gce_instance_client,
                                         'deleteAccessConfig',
                                         params)[0]
      except HttpError as exception:
        message = 'Unable to delete access config for {0:s}: {1:s}'.format(
          self.name,
          exception.error_details)
        raise errors.ResourceDeletionError(message, __name__) from exception
      self.BlockOperation(response, zone=self.zone)
      # Save deleted external IP address
      external_ip_addresses[network_interface_name] = external_ip_address
    # Return the deleted external IP address for future use
    return external_ip_addresses

  def AbandonFromMIG(self, instance_group: str) -> None:
    """Abandons the instance from the managed instance group.

    Args:
      instance_group (str): The instance group that this instance should
          be abondoned from.

    Raises:
      errors.OperationFailedError: If the request did not succeed.
    """

    def RaiseException(exception: Exception) -> None:
      msg = ('Unable to abandon {0:s} '
             'from managed instance group {1:s}.').format(
        self.name,
        instance_group,
      )
      raise errors.OperationFailedError(msg, __name__) from exception

    mig_client = self.GceApi().instanceGroupManagers()
    params = {
      'project': self.project_id,
      'zone': self.zone,
      'instanceGroupManager': instance_group,
      'body': {
        'instances': [
          'zones/{0:s}/instances/{1:s}'.format(self.zone, self.name)
        ]
      }
    }

    try:
      op = common.ExecuteRequest(mig_client, 'abandonInstances', params)[0]
    except HttpError as exception:
      RaiseException(exception)

    try:
      self.BlockOperation(op, zone=self.zone)
    except RuntimeError as exception:
      RaiseException(exception)

  def SetTags(self, new_tags: List[str]) -> None:
    """Sets tags for the compute instance.

    Tags are used to configure firewall rules and network routes.

    Args:
      new_tags (List[str]): A list of tags. Each tag must be 1-63
          characters long, and comply with RFC1035.

    Raises:
      InvalidNameError: If the name of the tags does not
          comply with RFC1035.
    """

    logger.info(
        self.FormatLogMessage(', adding tags {0!s} to instance '
            '{1:s}.'.format(new_tags, self.name)))
    for tag in new_tags:
      if not common.COMPUTE_RFC1035_REGEX.match(tag):
        raise errors.InvalidNameError(
            'Network Tag {0:s} does not comply with {1:s}.'.format(
                tag, common.COMPUTE_RFC1035_REGEX.pattern), __name__)

    get_operation = self.GetOperation()
    tags_dict = get_operation['tags']
    existing_tags = tags_dict.get('items', [])
    tags_fingerprint = tags_dict['fingerprint']
    tags = existing_tags + new_tags
    request_body = {
      'fingerprint': tags_fingerprint,
      'items': tags,
      }

    gce_instance_client = self.GceApi().instances()
    request = gce_instance_client.setTags(
      project=self.project_id,
      zone=self.zone,
      instance=self.name,
      body=request_body
    )
    response = request.execute()
    self.BlockOperation(response, zone=self.zone)

  def GetPowerState(self) -> str:
    """
    Gets the current power state of the instance.

    As per https://cloud.google.com/compute/docs/reference/rest/v1/instances/get
    this can return one of the following possible values: PROVISIONING, STAGING,
    RUNNING, STOPPING, SUSPENDING, SUSPENDED, REPAIRING, and TERMINATED
    """
    return str(self.GetOperation()['status'])

  def Stop(self) -> None:
    """
    Stops the instance.

    Raises:
      errors.InstanceStateChangeError: If the Stop operation is unsuccessful
    """

    logger.info('Stopping instance "{0:s}"'.format(self.name))
    try:
      gce_instance_client = self.GceApi().instances()
      request = gce_instance_client.stop(
          project=self.project_id, instance=self.name, zone=self.zone)
      response = request.execute()
      self.BlockOperation(response, zone=self.zone)
    except HttpError as exception:
      raise errors.InstanceStateChangeError('Could not stop instance: {0:s}'
          .format(str(exception)), __name__)

  def Start(self) -> None:
    """
    Starts the instance.

    Raises:
      errors.InstanceStateChangeError: If the Start operation is unsuccessful
    """

    logger.info('Starting instance "{0:s}"'.format(self.name))
    try:
      gce_instance_client = self.GceApi().instances()
      request = gce_instance_client.start(
          project=self.project_id, instance=self.name, zone=self.zone)
      response = request.execute()
      self.BlockOperation(response, zone=self.zone)
    except HttpError as exception:
      raise errors.InstanceStateChangeError('Could not start instance: {0:s}'
          .format(str(exception)), __name__)

  def DetachServiceAccount(self) -> None:
    """
    Detach a service account from the instance

    Raises:
      errors.ServiceAccountRemovalError: if en error occurs while
          detaching the service account
    """

    logger.info('Detaching service account from instance "{0:s}"'
        .format(self.name))
    try:
      gce_instance_client = self.GceApi().instances()
      request = gce_instance_client.setServiceAccount(
          project=self.project_id, instance=self.name, zone=self.zone, body={})
      response = request.execute()
      self.BlockOperation(response, zone=self.zone)
    except HttpError as exception:
      raise errors.ServiceAccountRemovalError('Service account detatchment '
          'failure: {0:s}'.format(str(exception)), __name__)

  def _NormaliseFirewallL4Config(self, l4config: List[Any]) -> List[Any]:
    """Normalise l4config dict key names that differ between policies and
    firewalls.

    Args:
      l4config List[Any]: the l4config to be normalised

    Returns:
      List[Any]: the normalised l4config"""
    normalised_l4config = []
    for config in l4config:
      normalised = {}
      if 'ipProtocol' in config:
        normalised['ip_protocol'] = config['ipProtocol']
      elif 'IPProtocol' in config:
        normalised['ip_protocol'] = config['IPProtocol']
      if 'ports' in config:
        normalised['ports'] = config['ports']
      normalised_l4config.append(normalised)

    return normalised_l4config

  def _NormaliseFirewallRules(self, nic_rules: Dict[str, Any]) -> List[Any]:
    """Normalise firewall policies and firewall rules into a common format.

    Args:
      nic_rules: the effective firewall rules for an individual NIC.

    Returns:
      List[Dict[str, Any]]: The normalised firewall rules for a NIC with
        individual rules in the following format:
        {
          'type': 'policy' or 'firewall',
          'policy_level': int,
          'priority': int,
          'direction': 'INGRESS' or 'EGRESS',
          'l4config': [
            {
              'ip_protocol': str,
              'ports': List[str]
            }]
          'ips': List[str],
          'action': 'allow' or 'deny' or 'goto_next'
        }
    """

    normalised_rules = []
    firewall_policies = nic_rules['firewallPolicys']
    firewalls = nic_rules['firewalls']

    for policy_level, policy in enumerate(firewall_policies):
      for rule in policy['rules']:
        is_ingress = rule['direction'] == 'INGRESS'
        normalised_rule = {
            'type': 'policy',
            'policy_level': policy_level,
            'priority': rule['priority'],
            'direction': rule['direction'],
            'l4config': self._NormaliseFirewallL4Config(
                rule['match']['layer4Configs']),
            'ips': (rule['match']['srcIpRanges'] if is_ingress else
                    rule['match']['destIpRanges']),
            'action': rule['action']}
        normalised_rules.append(normalised_rule)

    for rule in firewalls:
      is_ingress = rule['direction'] == 'INGRESS'
      is_allow = 'allowed' in rule
      normalised_rule = {
          'type': 'firewall',
          'policy_level': NON_HIERARCHICAL_FW_POLICY_LEVEL,
          'priority': rule['priority'],
          'direction': rule['direction'],
          'l4config': self._NormaliseFirewallL4Config(
              rule['allowed'] if is_allow else rule['denied']),
          'ips': (rule['sourceRanges'] if is_ingress else
              rule['destinationRanges']),
          'action': 'allow' if is_allow else 'deny'}
      normalised_rules.append(normalised_rule)

    return normalised_rules

  def GetEffectiveFirewallRules(self) -> Dict[str, List[Any]]:
    """Get the effective firewall rules for an instance.

    Returns:
      Dict[str, List[Any]]: The effective firewall rules per NIC.
    """
    gce_instance_client = self.GceApi().instances()
    instance_info = self.GetOperation()
    fw_rules = {}

    for nic in instance_info.get('networkInterfaces', []):
      nic_name = nic['name']
      nic_fw_rules = []
      request = {'project': self.project_id, 'instance': self.name,
          'zone': self.zone, 'networkInterface': nic_name}
      responses = common.ExecuteRequest(
          gce_instance_client, 'getEffectiveFirewalls', request)
      for response in responses:
        nic_fw_rules.extend(self._NormaliseFirewallRules(response))
      fw_rules[nic_name] = nic_fw_rules

    return fw_rules


class GoogleComputeDisk(compute_base_resource.GoogleComputeBaseResource):
  """Class representing a Compute Engine disk."""

  def GetOperation(self) -> Dict[str, Any]:
    """Get API operation object for the disk.

    Returns:
      Dict: An API operation object for a Google Compute Engine disk.
          https://cloud.google.com/compute/docs/reference/rest/v1/disks/get#response-body
    """

    gce_disk_client = self.GceApi().disks()
    request = gce_disk_client.get(
        disk=self.name, project=self.project_id, zone=self.zone)
    response = request.execute()  # type: Dict[str, Any]
    return response

  def Snapshot(self,
               snapshot_name: Optional[str] = None) -> 'GoogleComputeSnapshot':
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
      InvalidNameError: If the name of the snapshot does not comply with the
          RegEx.
    """

    if not snapshot_name:
      snapshot_name = self.name
    snapshot_name = common.GenerateUniqueInstanceName(snapshot_name,
                                                      common.COMPUTE_NAME_LIMIT)
    if not common.REGEX_DISK_NAME.match(snapshot_name):
      raise errors.InvalidNameError(
          'Snapshot name {0:s} does not comply with {1:s}'.format(
              snapshot_name, common.REGEX_DISK_NAME.pattern), __name__)
    logger.info(
        self.FormatLogMessage('New Snapshot: {0:s}'.format(snapshot_name)))
    operation_config = {'name': snapshot_name}
    gce_disk_client = self.GceApi().disks()
    request = gce_disk_client.createSnapshot(
        disk=self.name,
        project=self.project_id,
        zone=self.zone,
        body=operation_config)
    response = request.execute()
    self.BlockOperation(response, zone=self.zone)
    return GoogleComputeSnapshot(disk=self, name=snapshot_name)

  def Delete(self) -> None:
    """Delete a Disk."""

    gce_disk_client = self.GceApi().disks()
    try:
      request = gce_disk_client.delete(
          project=self.project_id, disk=self.name, zone=self.zone)
      request.execute()
    except HttpError as exception:
      if exception.resp.status == 404:
        logger.warning(
            ('Can not find resource {0:s}, it might be already '
             'deleted. API call resulted in the following error: '
             '{1:s}').format(self.name, str(exception)))
      else:
        logger.error((
            'While deleting GCE disk {0:s} the following error occurred: '
            '{1:s}').format(self.name, str(exception)))
        raise errors.ResourceDeletionError(
            'Could not delete disk {0:s}: {1!s}'.format(
                self.name, exception), __name__) from exception
    logger.info(
        self.FormatLogMessage('Deleted Disk: {0:s}'.format(self.name)))

  def GetDiskType(self) -> str:
    """Return the disk type.

    Returns:
      str: The disk type.
    """
    # 'type': https://www.googleapis.com/compute/v1/projects/<>/zones/us
    # -central1-a/diskTypes/pd-standard
    disk_type = self.GetOperation()['type'].split('/')[-1]  # type: str
    return disk_type


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

    super().__init__(project_id=disk.project_id, zone=disk.zone, name=name)
    self.disk = disk

  def GetOperation(self) -> Dict[str, Any]:
    """Get API operation object for the Snapshot.

    Returns:
      Dict: An API operation object for a Google Compute Engine Snapshot.
          https://cloud.google.com/compute/docs/reference/rest/v1/snapshots/get#response-body
    """

    gce_snapshot_client = self.GceApi().snapshots()
    request = gce_snapshot_client.get(
        snapshot=self.name, project=self.project_id)
    response = request.execute()  # type: Dict[str, Any]
    return response

  def Delete(self) -> None:
    """Delete a Snapshot."""

    logger.info(
        self.FormatLogMessage('Deleting Snapshot: {0:s}'.format(self.name)))
    gce_snapshot_client = self.GceApi().snapshots()
    request = gce_snapshot_client.delete(
        project=self.project_id, snapshot=self.name)
    response = request.execute()
    self.BlockOperation(response)


class GoogleComputeImage(compute_base_resource.GoogleComputeBaseResource):
  """Class representing a Compute Engine Image."""

  def GetOperation(self) -> Dict[str, Any]:
    """Get API operation object for the image.

    Returns:
      Dict: Holding an API operation object for a Google Compute Engine Image.
          https://cloud.google.com/compute/docs/reference/rest/v1/images/get#response-body
    """

    gce_image_client = self.GceApi().images()
    request = gce_image_client.get(project=self.project_id, image=self.name)
    response = request.execute()  # type: Dict[str, Any]
    return response

  def ExportImage(self,
                  gcs_output_folder: str,
                  output_name: Optional[str] = None) -> None:
    """Export compute image to Google Cloud storage.

    Exported image is compressed and stored in .tar.gz format.

    Args:
      gcs_output_folder (str): Folder path of the exported image.
      output_name (str): Optional. Name of the output file. Name will be
          appended with .tar.gz. Default is [image_name].tar.gz.

    Raises:
      InvalidNameError: If exported image name is invalid.
    """

    if output_name:
      if not common.REGEX_DISK_NAME.match(output_name):
        raise errors.InvalidNameError(
            'Exported image name {0:s} does not comply with {1:s}'.format(
                output_name, common.REGEX_DISK_NAME.pattern), __name__)
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
    logger.info(
        'Image {0:s} exported to {1:s}.'.format(self.name, full_path))

  def Delete(self) -> None:
    """Delete Compute Disk Image from a project."""

    gce_image_client = self.GceApi().images()
    request = gce_image_client.delete(project=self.project_id, image=self.name)
    response = request.execute()
    self.BlockOperation(response)
