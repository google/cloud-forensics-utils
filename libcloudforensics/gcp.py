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
"""Library for incident response operations on Google Cloud Compute Engine.

Library to make forensic images of Google Compute Engine disk and create
analysis virtual machine to be used in incident response.
"""

from __future__ import unicode_literals

import binascii
import datetime
import json
import logging
import os
import re
import socket
import ssl
import subprocess
import time

from googleapiclient.discovery import build  # pylint: disable=import-error
from googleapiclient.errors import HttpError
from google.auth import default
from google.auth.exceptions import RefreshError, DefaultCredentialsError

log = logging.getLogger()

RETRY_MAX = 10
REGEX_DISK_NAME = re.compile('^(?=.{1,63}$)[a-z]([-a-z0-9]*[a-z0-9])?$')
STARTUP_SCRIPT = 'scripts/startup.sh'


def CreateService(service_name, api_version):
  """Creates an GCP API service.

  Args:
    service_name (str): Name of the GCP service to use.
    api_version (str): Version of the GCP service API to use.

  Returns:
    apiclient.discovery.Resource: API service resource.

  Raises:
    RuntimeError: If Application Default Credentials could not be obtained or if
        service build times out.
  """

  try:
    credentials, _ = default()
  except DefaultCredentialsError as error:
    error_msg = (
        'Could not get application default credentials: {0!s}\n'
        'Have you run $ gcloud auth application-default '
        'login?').format(error)
    raise RuntimeError(error_msg)

  service_built = False
  for retry in range(RETRY_MAX):
    try:
      service = build(
          service_name, api_version, credentials=credentials,
          cache_discovery=False)
      service_built = True
    except socket.timeout:
      log.info(
          'Timeout trying to build service {0:s} (try {1:s} of {2:s})'.format(
              service_name, retry, RETRY_MAX))

    if service_built:
      break

  if not service_built:
    error_msg = (
        'Failures building service {0:s} caused by multiple '
        'timeouts').format(service_name)
    raise RuntimeError(error_msg)

  return service


class GoogleCloudLog:
  """Class representing a Google Cloud Logs interface.

  Attributes:
    project_id: Project name.
    gcl_api_client: Client to interact with GCP logging API.

  Example use:
    # pylint: disable=line-too-long
    gcp = GoogleCloudLog(project_id='your_project_name')
    gcp.ListLogs()
    gcp.ExecuteQuery(filter='resource.type="gce_instance" labels."compute.googleapis.com/resource_name"="instance-1"')
    See https://cloud.google.com/logging/docs/view/advanced-queries for filter details.
  """

  LOGGING_API_VERSION = 'v2'

  def __init__(self, project_id):
    """Initialize the GoogleCloudProject object.

    Args:
      project_id (str): The name of the project.
    """

    self.project_id = project_id
    self.gcl_api_client = None

  def GclApi(self):
    """Get a Google Compute Logging service object.

    Returns:
      apiclient.discovery.Resource: A Google Compute Logging service object.
    """

    if self.gcl_api_client:
      return self.gcl_api_client
    self.gcl_api_client = CreateService('logging', self.LOGGING_API_VERSION)
    return self.gcl_api_client

  def ListLogs(self):
    """List logs in project.

    Returns:
      list: The project logs available.

    Raises:
      RuntimeError: If API call failed.
    """

    have_all_tokens = False
    page_token = None
    logs = []
    while not have_all_tokens:
      gcl_instance_client = self.GclApi().logs()
      if page_token:
        request = gcl_instance_client.list(
            parent=self.project_id, pageToken=page_token)
      else:
        request = gcl_instance_client.list(parent='projects/' + self.project_id)
      try:
        result = request.execute()
      except (RefreshError, DefaultCredentialsError) as exception:
        error_msg = (
            '{0:s}\n'
            'Something is wrong with your Application Default '
            'Credentials. Try running: '
            '$ gcloud auth application-default login'.format(str(exception)))
        raise RuntimeError(error_msg)
      for logtypes in result.get('logNames', []):
        logs.append(logtypes)
      page_token = result.get('nextPageToken')
      if not page_token:
        have_all_tokens = True

    return logs

  def ExecuteQuery(self, qfilter):
    """Query logs in GCP project.

    Args:
      qfilter (str): The query filter to use.

    Returns:
      list(dict): Log entries returned by the query.

    Raises:
      RuntimeError: If API call failed.
    """

    body = {
        'resourceNames': 'projects/' + self.project_id,
        'filter': qfilter,
        'orderBy': 'timestamp desc',
    }

    have_all_tokens = False
    page_token = None
    entries = []
    while not have_all_tokens:
      gcl_instance_client = self.GclApi().entries()
      if page_token:
        # This sleep is needed as the API rate limits. It will *not* speed
        # up the query by asking if there are new results more frequently.
        time.sleep(1)
        body['pageToken'] = page_token
        request = gcl_instance_client.list(body=body)
      else:
        request = gcl_instance_client.list(body=body)
      try:
        result = request.execute()
      except (RefreshError, DefaultCredentialsError) as exception:
        error_msg = (
            '{0:s}\n'
            'Something is wrong with your Application Default '
            'Credentials. Try running: '
            '$ gcloud auth application-default login'.format(str(exception)))
        raise RuntimeError(error_msg)
      for entry in result.get('entries', []):
        entries.append(entry)
      page_token = result.get('nextPageToken')
      if not page_token:
        have_all_tokens = True

    return entries


class GoogleCloudProject:
  """Class representing a Google Cloud Project.

  Attributes:
    project_id: Project name.
    default_zone: Default zone to create new resources in.
    gce_api_client: Client to interact with GCE APIs.

  Example use:
    gcp = GoogleCloudProject("your_project_name", "us-east")
    gcp.ListInstances()
  """

  COMPUTE_ENGINE_API_VERSION = 'v1'

  def __init__(self, project_id, default_zone=None):
    """Initialize the GoogleCloudProject object.

    Args:
      project_id (str): The name of the project.
      default_zone (str): Optional. Default zone to create new resources in. N
          one means GlobalZone.
    """

    self.project_id = project_id
    self.default_zone = default_zone
    self.gce_api_client = None

  def GceApi(self):
    """Get a Google Compute Engine service object.

    Returns:
      apiclient.discovery.Resource: A Google Compute Engine service object.
    """

    if self.gce_api_client:
      return self.gce_api_client
    self.gce_api_client = CreateService(
        'compute', self.COMPUTE_ENGINE_API_VERSION)
    return self.gce_api_client

  def BlockOperation(self, response, zone=None):
    """Block until API operation is finished.

    Args:
      response (dict): GCE API response.
      zone (str): Optional. GCP zone to execute the operation in. None means
          GlobalZone.

    Returns:
      dict: Holding the response of a get operation on an API object of type
          zoneOperations or globalOperations.

    Raises:
      RuntimeError: If API call failed.
    """

    service = self.GceApi()
    while True:
      if zone:
        request = service.zoneOperations().get(
            project=self.project_id, zone=zone, operation=response['name'])
        result = request.execute()
      else:
        request = service.globalOperations().get(
            project=self.project_id, operation=response['name'])
        result = request.execute()

      if 'error' in result:
        raise RuntimeError(result['error'])

      if result['status'] == 'DONE':
        return result
      time.sleep(5)  # Seconds between requests

  def FormatLogMessage(self, message):
    """Format log messages with project specific information.

    Args:
      message (str): Message string to log.

    Returns:
      str: Formatted log message string.
    """

    return 'project:{0} {1}'.format(self.project_id, message)

  def ListInstances(self):
    """List instances in project.

    Returns:
      dict: Dictionary mapping instance names (str) to their respective
          GoogleComputeInstance object.
    """

    have_all_tokens = False
    page_token = None
    instances = {}
    while not have_all_tokens:
      gce_instance_client = self.GceApi().instances()
      if page_token:
        request = gce_instance_client.aggregatedList(
            project=self.project_id, pageToken=page_token)
      else:
        request = gce_instance_client.aggregatedList(project=self.project_id)
      result = request.execute()
      page_token = result.get('nextPageToken')
      if not page_token:
        have_all_tokens = True

      for zone in result['items']:
        try:
          for instance in result['items'][zone]['instances']:
            _, zone = instance['zone'].rsplit('/', 1)
            name = instance['name']
            instances[name] = GoogleComputeInstance(
                self, zone, name, labels=instance.get('labels'))
        except KeyError:
          pass

    return instances

  def ListDisks(self):
    """List disks in project.

    Returns:
      dict: Dictionary mapping disk names (str) to their respective
          GoogleComputeDisk object.
    """

    have_all_tokens = False
    page_token = None
    disks = {}
    while not have_all_tokens:
      gce_disk_client = self.GceApi().disks()
      if page_token:
        request = gce_disk_client.aggregatedList(
            project=self.project_id, pageToken=page_token)
      else:
        request = gce_disk_client.aggregatedList(project=self.project_id)
      result = request.execute()
      page_token = result.get('nextPageToken')
      if not page_token:
        have_all_tokens = True
      for zone in result['items']:
        try:
          for disk in result['items'][zone]['disks']:
            _, zone = disk['zone'].rsplit('/', 1)
            name = disk['name']
            disks[name] = GoogleComputeDisk(
                self, zone, name, labels=disk.get('labels'))
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

    instances = self.ListInstances()
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

    disks = self.ListDisks()
    disk = disks.get(disk_name)
    if not disk:
      error_msg = 'Disk {0:s} was not found in project {1:s}'.format(
          disk_name, self.project_id)
      raise RuntimeError(error_msg)
    return disk

  def CreateDiskFromSnapshot(
      self, snapshot, disk_name=None, disk_name_prefix='',
      disk_type='pd-standard'):
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
      disk_name = GenerateDiskName(snapshot, disk_name_prefix)
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
    return GoogleComputeDisk(
        project=self, zone=self.default_zone, name=disk_name)

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

    startup_script = self._ReadStartupScript()

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
        project=self, zone=self.default_zone, name=vm_name)
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
            resource_dict[name] = GoogleComputeInstance(
                self, zone, name, labels=resource['labels'])

          for resource in resource_scoped_list.get('disks', []):
            name = resource['name']
            resource_dict[name] = GoogleComputeDisk(
                self, zone, name, labels=resource['labels'])

      request = service_object.aggregatedList_next(
          previous_request=request, previous_response=response)
    return resource_dict

  @staticmethod
  def _ReadStartupScript():
    """Read and return the startup script that is to be run on the forensics VM.

    Users can either write their own script to install custom packages,
    or use the provided one. To use your own script, export a STARTUP_SCRIPT
    environment variable with the absolute path to it:
    "user@terminal:~$ export STARTUP_SCRIPT='absolute/path/script.sh'"

    Returns:
      str: The script to run.
    Raises:
      OSError: If the script cannot be opened, read or closed.
    """

    try:
      startup_script = os.environ.get('STARTUP_SCRIPT')
      if not startup_script:
        # Use the provided script
        startup_script = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), STARTUP_SCRIPT)
      startup_script = open(startup_script)
      script = startup_script.read()
      startup_script.close()
      return script
    except OSError as exception:
      raise OSError(
          'Could not open/read/close the startup script {0:s}: '
          '{1:s}'.format(startup_script, str(exception)))

  def CreateImageFromDisk(self, src_disk, name=None):
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
                project_id=src_disk.project.project_id, zone=src_disk.zone,
                src_disk=src_disk.name)
    }
    gce_image_client = self.GceApi().images()
    request = gce_image_client.insert(
        project=self.project_id, body=image_body, forceCreate=True)
    response = request.execute()
    self.BlockOperation(response)
    return GoogleComputeImage(self, None, name)


class GoogleCloudFunction(GoogleCloudProject):
  """Class to call Google Cloud Functions.

  Attributes:
    region (str): Region to execute functions in.
    gcf_api_client: Client to interact with GCF APIs.
  """

  CLOUD_FUNCTIONS_API_VERSION = 'v1beta2'

  def __init__(self, project_id, region):
    """Initialize the GoogleCloudFunction object.

    Args:
      project_id (str): The name of the project.
      region (str): Region to run functions in.
    """

    self.region = region
    self.gcf_api_client = None
    super(GoogleCloudFunction, self).__init__(project_id)

  def GcfApi(self):
    """Get a Google Cloud Function service object.

    Returns:
      apiclient.discovery.Resource: A Google Cloud Function service object.
    """

    if self.gcf_api_client:
      return self.gcf_api_client
    self.gcf_api_client = CreateService(
        'cloudfunctions', self.CLOUD_FUNCTIONS_API_VERSION)
    return self.gcf_api_client

  def ExecuteFunction(self, function_name, args):
    """Executes a Google Cloud Function.

    Args:
      function_name (str): The name of the function to call.
      args (dict): Arguments to pass to the function.

    Returns:
      dict: Return value from function call.

    Raises:
      RuntimeError: When cloud function arguments cannot be serialized or
          when an HttpError is encountered.
    """

    service = self.GcfApi()
    cloud_function = service.projects().locations().functions()

    try:
      json_args = json.dumps(args)
    except TypeError as e:
      error_msg = (
          'Cloud function args [{0:s}] could not be serialized:'
          ' {1!s}').format(str(args), e)
      raise RuntimeError(error_msg)

    function_path = 'projects/{0:s}/locations/{1:s}/functions/{2:s}'.format(
        self.project_id, self.region, function_name)

    log.debug(
        'Calling Cloud Function [{0:s}] with args [{1!s}]'.format(
            function_name, args))
    try:
      function_return = cloud_function.call(
          name=function_path, body={
              'data': json_args
          }).execute()
    except (HttpError, ssl.SSLError) as e:
      error_msg = 'Cloud function [{0:s}] call failed: {1!s}'.format(
          function_name, e)
      raise RuntimeError(error_msg)

    return function_return


class GoogleCloudBuild(GoogleCloudProject):
  """Class to call Google Cloud Build APIs.

  Attributes:
    gcb_api_client: Client to interact with GCB APIs.
  """
  CLOUD_BUILD_API_VERSION = 'v1'

  def __init__(self, project_id):
    """Initialize the GoogleCloudBuild object.

    Args:
      project_id (str): The name of the project.
    """

    self.gcb_api_client = None
    super(GoogleCloudBuild, self).__init__(project_id)

  def GcbApi(self):
    """Get a Google Cloud Build service object.

    Returns:
      apiclient.discovery.Resource: A Google Cloud Build service object.
    """

    if self.gcb_api_client:
      return self.gcb_api_client
    self.gcb_api_client = CreateService(
        'cloudbuild', self.CLOUD_BUILD_API_VERSION)
    return self.gcb_api_client

  def CreateBuild(self, build_body):
    """Create a cloud build.
    Args:
      build_body (dict): A dictionary that describes how to find the source
          code and how to build it.

    Returns:
      dict: Represents long-running operation that is the result of
          a network API call.
    """
    cloud_build_client = self.GcbApi().projects().builds()
    build_info = cloud_build_client.create(
        projectId=self.project_id, body=build_body).execute()
    build_metadata = build_info['metadata']['build']
    log.info(
        'Build started, logs bucket: {0:s}, logs URL: {1:s}'.format(
            build_metadata['logsBucket'], build_metadata['logUrl']))
    return build_info

  def BlockOperation(self, response):  #  pylint: disable=arguments-differ
    """Block execution until API operation is finished.

    Args:
      response (dict): Google Cloud Build API response.

    Returns:
      dict: Holding the response of a get operation on an
          API object of type operations.

    Raises:
      RuntimeError: If API call failed.
    """
    service = self.GcbApi()
    while True:
      request = service.operations().get(name=response['name'])
      response = request.execute()
      if response.get('done') and response.get('error'):
        build_metadata = response['metadata']['build']
        raise RuntimeError(
            ': {0:1}, logs bucket: {1:s}, logs URL: {2:s}'.format(
                response['error']['message'], build_metadata['logsBucket'],
                build_metadata['logUrl']))

      if response.get('done') and response.get('response'):
        return response
      time.sleep(5)  # Seconds between requests


class GoogleComputeBaseResource:
  """Base class representing a Computer Engine resource.

  Attributes:
    project (GoogleCloudProject): Cloud project for the resource.
    zone (str): What zone the resource is in.
    name (str): Name of the resource.
    labels (dict): Dictionary of labels for the resource, if existing.
  """

  def __init__(self, project, zone, name, labels=None):
    """Initialize the Google Compute Resource base object.

    Args:
      project (GoogleCloudProject): Cloud project for the resource.
      zone (str): What zone the resource is in.
      name (str): Name of the resource.
      labels (dict): Dictionary of labels for the resource, if existing.
    """

    self.project = project
    self.zone = zone
    self.name = name
    self.labels = labels
    self._data = None

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
      module = self.project.GceApi().instances()
    elif resource_type == 'compute#disk':
      module = self.project.GceApi().disks()
    elif resource_type == 'compute#Snapshot':
      module = self.project.GceApi().snapshots()

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
          instance=self.name, project=self.project.project_id, zone=self.zone,
          body=request_body).execute()
    elif resource_type == 'compute#disk':
      response = self.FormOperation('setLabels')(
          resource=self.name, project=self.project.project_id, zone=self.zone,
          body=request_body).execute()
    elif resource_type == 'compute#Snapshot':
      response = self.FormOperation('setLabels')(
          resource=self.name, project=self.project.project_id,
          body=request_body).execute()
    if blocking_call:
      self.project.BlockOperation(response, zone=self.zone)

    return response


class GoogleComputeInstance(GoogleComputeBaseResource):
  """Class representing a Google Compute Engine virtual machine."""

  def GetOperation(self):
    """Get API operation object for the virtual machine.

    Returns:
      dict: An API operation object for a Google Compute Engine
          virtual machine.
    """

    gce_instance_client = self.project.GceApi().instances()
    request = gce_instance_client.get(
        instance=self.name, project=self.project.project_id, zone=self.zone)
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
        return self.project.GetDisk(disk_name=disk_name)
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
        return self.project.GetDisk(disk_name=disk_name)
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
        'gcloud', 'compute', '--project', self.project.project_id, 'ssh',
        '--zone', self.zone, self.name
    ], stderr=devnull)

  def Ssh(self):
    """Connect to the virtual machine over SSH."""

    max_retries = 100  # times to retry the connection
    retries = 0

    log.info(
        self.project.FormatLogMessage('Connecting to analysis VM over SSH'))

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

    log.info(
        self.project.FormatLogMessage(
            'Attaching {0} to VM {1} in {2} mode'.format(
                disk.name, self.name, mode)))

    operation_config = {
        'mode': mode,
        'source': disk.GetSourceString(),
        'boot': False,
        'autoDelete': False,
    }
    gce_instance_client = self.project.GceApi().instances()
    request = gce_instance_client.attachDisk(
        instance=self.name, project=self.project.project_id, zone=self.zone,
        body=operation_config)
    response = request.execute()
    self.project.BlockOperation(response, zone=self.zone)


class GoogleComputeDisk(GoogleComputeBaseResource):
  """Class representing a Compute Engine disk."""

  def GetOperation(self):
    """Get API operation object for the disk.

    Returns:
      dict: An API operation object for a Google Compute Engine disk.
    """

    gce_disk_client = self.project.GceApi().disks()
    request = gce_disk_client.get(
        disk=self.name, project=self.project.project_id, zone=self.zone)
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
    if not REGEX_DISK_NAME.match(snapshot_name):
      raise ValueError(
          'Snapshot name {0:s} does not comply with '
          '{1:s}'.format(snapshot_name, REGEX_DISK_NAME.pattern))
    log.info(
        self.project.FormatLogMessage(
            'New Snapshot: {0}'.format(snapshot_name)))
    operation_config = {'name': snapshot_name}
    gce_disk_client = self.project.GceApi().disks()
    request = gce_disk_client.createSnapshot(
        disk=self.name, project=self.project.project_id, zone=self.zone,
        body=operation_config)
    response = request.execute()
    self.project.BlockOperation(response, zone=self.zone)
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
        project=disk.project, zone=None, name=name)
    self.disk = disk

  def GetOperation(self):
    """Get API operation object for the Snapshot.

    Returns:
      dict: An API operation object for a Google Compute Engine Snapshot.
    """

    gce_snapshot_client = self.project.GceApi().snapshots()
    request = gce_snapshot_client.get(
        snapshot=self.name, project=self.project.project_id)
    response = request.execute()
    return response

  def Delete(self):
    """Delete a Snapshot."""

    log.info(
        self.project.FormatLogMessage(
            'Deleted Snapshot: {0}'.format(self.name)))
    gce_snapshot_client = self.project.GceApi().snapshots()
    request = gce_snapshot_client.delete(
        project=self.project.project_id, snapshot=self.name)
    response = request.execute()
    self.project.BlockOperation(response)


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

    gce_image_client = self.project.GceApi().images()
    request = gce_image_client.get(
        project=self.project.project_id, image=self.name)
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
    cloud_build = GoogleCloudBuild(self.project.project_id)
    response = cloud_build.CreateBuild(build_body)
    cloud_build.BlockOperation(response)
    log.info('Image {0:s} exported to {1:s}.'.format(self.name, full_path))

  def Delete(self):
    """Delete Compute Disk Image from a project.
    """

    gce_image_client = self.project.GceApi().images()
    request = gce_image_client.delete(
        project=self.project.project_id, image=self.name)
    response = request.execute()
    self.project.BlockOperation(response)


def CreateDiskCopy(
    src_proj, dst_proj, instance_name, zone, disk_name=None,
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

  src_proj = GoogleCloudProject(src_proj)
  dst_proj = GoogleCloudProject(dst_proj, default_zone=zone)
  instance = src_proj.GetInstance(instance_name) if instance_name else None

  try:
    if disk_name:
      disk_to_copy = src_proj.GetDisk(disk_name)
    else:
      disk_to_copy = instance.GetBootDisk()

    log.info('Disk copy of {0:s} started...'.format(disk_to_copy.name))
    snapshot = disk_to_copy.Snapshot()
    new_disk = dst_proj.CreateDiskFromSnapshot(
        snapshot, disk_name_prefix='evidence', disk_type=disk_type)
    snapshot.Delete()
    log.info(
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


def StartAnalysisVm(
    project, vm_name, zone, boot_disk_size, boot_disk_type, cpu_cores,
    attach_disk=None, image_project='ubuntu-os-cloud',
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

  project = GoogleCloudProject(project, default_zone=zone)
  analysis_vm, created = project.GetOrCreateAnalysisVm(
      vm_name, boot_disk_size, disk_type=boot_disk_type, cpu_cores=cpu_cores,
      image_project=image_project, image_family=image_family)
  for disk in (attach_disk or []):
    analysis_vm.AttachDisk(disk)
  return analysis_vm, created


def GenerateDiskName(snapshot, disk_name_prefix=None):
  """Generate a new disk name for the disk to be created from the Snapshot.

  The disk name must comply with the following RegEx:
      - ^(?=.{1,63}$)[a-z]([-a-z0-9]*[a-z0-9])?$

  i.e., it must be between 1 and 63 chars, the first character must be a
  lowercase letter, and all following characters must be a dash, lowercase
  letter, or digit, except the last character, which cannot be a dash.

  Args:
    snapshot (GoogleComputeSnapshot): A disk's Snapshot.
    disk_name_prefix (str): Optional. A prefix for the disk name.

  Returns:
    str: A name for the disk.

  Raises:
    ValueError: If the disk name does not comply with the RegEx.
  """

  # Max length of disk names in GCP is 63 characters
  project_id = snapshot.project.project_id
  disk_id = project_id + snapshot.disk.name
  disk_id_crc32 = '{0:08x}'.format(
      binascii.crc32(disk_id.encode()) & 0xffffffff)
  truncate_at = 63 - len(disk_id_crc32) - len('-copy') - 1
  if disk_name_prefix:
    disk_name_prefix += '-'
    if len(disk_name_prefix) > truncate_at:
      # The disk name prefix is too long
      disk_name_prefix = disk_name_prefix[:truncate_at]
    truncate_at -= len(disk_name_prefix)
    disk_name = '{0:s}{1:s}-{2:s}-copy'.format(
        disk_name_prefix, snapshot.name[:truncate_at], disk_id_crc32)
  else:
    disk_name = '{0:s}-{1:s}-copy'.format(
        snapshot.name[:truncate_at], disk_id_crc32)

  if not REGEX_DISK_NAME.match(disk_name):
    raise ValueError(
        'Disk name {0:s} does not comply with '
        '{1:s}'.format(disk_name, REGEX_DISK_NAME.pattern))

  return disk_name
