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

from googleapiclient.errors import HttpError

from libcloudforensics.providers.gcp.internal import common
from libcloudforensics.providers.gcp.internal import compute_resources  # pylint: disable=cyclic-import
from libcloudforensics.scripts import utils


class GoogleCloudCompute(common.GoogleCloudComputeClient):
  """Class representing all Google Cloud Compute objects in a project.
  Attributes:
    project_id: Project name.
    default_zone: Default zone to create new resources in.
  """

  def __init__(self, project_id, default_zone=None):
    """Initialize the Google Compute Resources in a project.

    Args:
      project_id (str): Google Cloud project ID.
      default_zone (str): Optional. Default zone to create new resources in.
          None means GlobalZone.
    """

    self.project_id = project_id
    self.default_zone = default_zone
    self._instances = None
    self._disks = None
    super(GoogleCloudCompute, self).__init__(self.project_id)

  def Instances(self, refresh=True):
    """Get all instances in the project.

    Args:
      refresh (boolean): Optional. Returns refreshed result if True.

    Returns:
      dict: Dictionary mapping instance names (str) to their respective
          GoogleComputeInstance object.
    """
    if not refresh and self._instances:
      return self._instances
    self._instances = self.ListInstances()
    return self._instances

  def Disks(self, refresh=True):
    """Get all disks in the project.

    Args:
      refresh (boolean): Optional. Returns refreshed result if True.

    Returns:
      dict: Dictionary mapping disk names (str) to their respective
          GoogleComputeDisk object.
    """
    if not refresh and self._disks:
      return self._disks
    self._disks = self.ListDisks()
    return self._disks

  def ListInstances(self):
    """List instances in project.

    Returns:
      dict: Dictionary mapping instance names (str) to their respective
          GoogleComputeInstance object.
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
            instances[name] = compute_resources.GoogleComputeInstance(
                self.project_id, zone, name, labels=instance.get('labels'))
        except KeyError:
          pass

    return instances

  def ListDisks(self):
    """List disks in project.

    Returns:
      dict: Dictionary mapping disk names (str) to their respective
          GoogleComputeDisk object.
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
            disks[name] = compute_resources.GoogleComputeDisk(
                self.project_id, zone, name, labels=disk.get('labels'))
        except KeyError:
          pass

    return disks

  def GetInstance(self, instance_name):
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

  def GetDisk(self, disk_name):
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

  def CreateDiskFromSnapshot(  # pylint: disable=missing-type-doc
      self, snapshot, disk_name=None, disk_name_prefix='',
      disk_type='pd-standard'):
    """Create a new disk based on a Snapshot.

    Args:
      snapshot (libcloudforensics.providers.gcp.internal.compute_resources
          .GoogleComputeSnapshot): Snapshot to use.
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
    return compute_resources.GoogleComputeDisk(
        project_id=self.project_id, zone=self.default_zone, name=disk_name)

  def GetOrCreateAnalysisVm(self,
                            vm_name,
                            boot_disk_size,
                            disk_type='pd-standard',
                            cpu_cores=4,
                            image_project='ubuntu-os-cloud',
                            image_family='ubuntu-1804-lts',
                            packages=None):
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
      packages (list[str]): Optional. List of packages to install in the VM.

    Returns:
      tuple(GoogleComputeInstance, bool): A tuple with a virtual machine object
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
    instance = compute_resources.GoogleComputeInstance(
        project_id=self.project_id, zone=self.default_zone, name=vm_name)
    created = True
    return instance, created

  def ListInstanceByLabels(self, labels_filter, filter_union=True):
    """List VMs in a project with one/all of the provided labels.

    This will call the __ListByLabel on instances() API object
    with the proper labels filter and return a dict with name and metadata
    for each instance, e.g.:
        {'instance-1': {'zone': 'us-central1-a', 'labels': {'id': '123'}}

    Args:
      labels_filter (dict): A dict of labels to find e.g. {'id': '123'}.
      filter_union (bool): Optional. A Boolean; True to get the union of all
          filters, False to get the intersection.

    Returns:
      dict: Dictionary mapping instances to their respective
          GoogleComputeInstance object.
    """

    instance_service_object = self.GceApi().instances()
    return self.__ListByLabel(
        labels_filter, instance_service_object, filter_union)

  def ListDiskByLabels(self, labels_filter, filter_union=True):
    """List Disks in a project with one/all of the provided labels.

    This will call the __ListByLabel on disks() API object
    with the proper labels filter and return a dict with name and metadata
    for each disk, e.g.:
        {'disk-1': {'zone': 'us-central1-a', 'labels': {'id': '123'}}

    Args:
      labels_filter (dict): A dict of labels to find e.g. {'id': '123'}.
      filter_union (bool): Optional. A Boolean; True to get the union of all
          filters, False to get the intersection.

    Returns:
      dict: Dictionary mapping disks to their respective GoogleComputeDisk
          object.
    """

    disk_service_object = self.GceApi().disks()
    return self.__ListByLabel(labels_filter, disk_service_object, filter_union)

  def __ListByLabel(self, labels_filter, service_object, filter_union):
    """List Disks/VMs in a project with one/all of the provided labels.

    Private method used to select different compute resources by labels.

    Args:
      labels_filter (dict):  A dict of labels to find e.g. {'id': '123'}.
      service_object (apiclient.discovery.Resource): Google Compute Engine
          (Disk | Instance) service object.
      filter_union (bool): A boolean; True to get the union of all filters,
          False to get the intersection.

    Returns:
      dict: Dictionary mapping instances/disks to their respective
          GoogleComputeInstance/GoogleComputeDisk object.

    Raises:
      RuntimeError: If the operation doesn't complete on GCP.
    """

    if not isinstance(filter_union, bool):
      error_msg = (
          'filter_union parameter must be of Type boolean {0:s} is an '
          'invalid argument.').format(filter_union)
      raise RuntimeError(error_msg)

    resource_dict = {}
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
            resource_dict[name] = compute_resources.GoogleComputeInstance(
                self.project_id, zone, name, labels=resource['labels'])

          for resource in resource_scoped_list.get('disks', []):
            name = resource['name']
            resource_dict[name] = compute_resources.GoogleComputeDisk(
                self.project_id, zone, name, labels=resource['labels'])

      request = service_object.aggregatedList_next(
          previous_request=request, previous_response=response)
    return resource_dict

  def CreateImageFromDisk(self, src_disk, name=None):
    """Creates an image from a persistent disk.

    Args:
      src_disk (GoogleComputeDisk): Source disk for the image.
      name (str): Optional. Name of the image to create. Default
          is [src_disk]_image.

    Returns:
      libcloudforensics.providers.gcp.internal.compute.GoogleComputeImage:
          A Google Compute Image object.
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
    return compute_resources.GoogleComputeImage(self.project_id, None, name)
