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
import random
from typing import TYPE_CHECKING, List, Tuple, Optional, Dict, Any

from google.auth.exceptions import DefaultCredentialsError
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.gcp.internal import common
from libcloudforensics import logging_utils
from libcloudforensics import errors

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
    disk_type: Optional[str] = None) -> 'compute.GoogleComputeDisk':
  """Creates a copy of a Google Compute Disk.

  Args:
    src_proj (str): Name of project that holds the disk to be copied.
    dst_proj (str): Name of project to put the copied disk in.
    zone (str): Zone where the new disk is to be created.
    instance_name (str): Optional. Instance using the disk to be copied.
    disk_name (str): Optional. Name of the disk to copy. If None,
        instance_name must be specified and the boot disk will be copied.
    disk_type (str): Optional. URL of the disk type resource describing
        which disk type to use to create the disk. The default behavior is to
        use the same disk type as the source disk.

  Returns:
    GoogleComputeDisk: A Google Compute Disk object.

  Raises:
    ResourceNotFoundError: If the GCP resource is not found.
    CredentialsConfigurationError: If the library could not authenticate to GCP.
    RuntimeError: If an unknown HttpError is thrown.
    ResourceCreationError: If there are errors copying the disk.
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

    if not disk_type:
      disk_type = disk_to_copy.GetDiskType()

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

  except (RefreshError, DefaultCredentialsError) as exception:
    raise errors.CredentialsConfigurationError(
        'Something is wrong with your Application Default Credentials. Try '
        'running: $ gcloud auth application-default login: {0!s}'.format(
            exception), __name__) from exception
  except HttpError as exception:
    if exception.resp.status == 403:
      raise errors.CredentialsConfigurationError(
          'Make sure you have the appropriate permissions on the project',
          __name__) from exception
    if exception.resp.status == 404:
      raise errors.ResourceNotFoundError(
          'GCP resource not found. Maybe a typo in the project / instance / '
          'disk name?', __name__) from exception
    raise RuntimeError(exception) from exception
  except RuntimeError as exception:
    raise errors.ResourceCreationError(
        'Cannot copy disk "{0:s}": {1!s}'.format(disk_name, exception),
        __name__) from exception

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
    InvalidNameError: If the GCE disk name is invalid.
  """

  if name:
    if not common.REGEX_DISK_NAME.match(name):
      raise errors.InvalidNameError(
          'Disk name {0:s} does not comply with {1:s}'.format(
              name, common.REGEX_DISK_NAME.pattern), __name__)
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


def AddDenyAllFirewallRules(project_id: str,
                            network: str,
                            deny_ingress_tag: str,
                            deny_egress_tag: str,
                            exempted_src_ips: Optional[List[str]] = None,
                            enable_logging: bool = False) -> None:
  """Add deny-all firewall rules, of highest priority.

  Args:
    project_id (str): Google Cloud Project ID.
    network (str): URL of the network resource for thesee firewall rules.
    deny_ingress_tag (str): Target tag name to apply deny ingress rule,
        also used as a deny ingress firewall rule name.
    deny_egress_tag (str): Target tag name to apply deny egress rule,
        also used as a deny egress firewall rule name.
    exempted_src_ips (List[str]): List of IPs exempted from the deny-all
      ingress firewall rules, ex: analyst IPs.
    enable_logging (bool): Optional. Enable firewall logging.
        Default is False.

  Raises:
    InvalidNameError: If Tag names are invalid.
  """

  logger.info('Creating deny-all (ingress/egress) '
          'firewall rules in {0:s} network.'.format(network))
  project = gcp_project.GoogleCloudProject(project_id)
  if not common.COMPUTE_RFC1035_REGEX.match(deny_ingress_tag):
    raise errors.InvalidNameError(
        'Deny ingress tag name {0:s} does not comply with {1:s}'.format(
            deny_ingress_tag, common.COMPUTE_RFC1035_REGEX.pattern), __name__)
  if not common.COMPUTE_RFC1035_REGEX.match(deny_egress_tag):
    raise errors.InvalidNameError(
        'Deny egress tag name {0:s} does not comply with {1:s}'.format(
            deny_egress_tag, common.COMPUTE_RFC1035_REGEX.pattern), __name__)

  source_range = common.GenerateSourceRange(exempted_src_ips)

  deny_ingress = {
    'name': deny_ingress_tag,
    'network': network,
    'direction': 'INGRESS',
    'priority': 0,
    'targetTags': [
      deny_ingress_tag
    ],
    'denied': [
      {
        'IPProtocol': 'all'
      }
    ],
    'logConfig': {
      'enable': enable_logging
    },
    'sourceRanges': source_range
  }
  deny_egress = {
    'name': deny_egress_tag,
    'network': network,
    'direction': 'EGRESS',
    'priority': 0,
    'targetTags': [
      deny_egress_tag
    ],
    'denied': [
      {
        'IPProtocol': 'all'
      }
    ],
    'logConfig': {
      'enable': enable_logging
    },
    'destinationRanges': [
      '0.0.0.0/0'
    ]
  }
  project.compute.InsertFirewallRule(body=deny_ingress)
  project.compute.InsertFirewallRule(body=deny_egress)


def InstanceNetworkQuarantine(project_id: str,
                              instance_name: str,
                              exempted_src_ips: Optional[List[str]] = None,
                              enable_logging: bool = False) -> None:
  """Put a Google Cloud instance in network quarantine.

  Network quarantine is imposed via applying deny-all
  ingress/egress firewall rules on each network interface.

  Args:
    project_id (str): Google Cloud Project ID.
    instance_name (str): : The name of the virtual machine.
    exempted_src_ips (List[str]): List of IPs exempted from the deny-all
        ingress firewall rules, ex: analyst IPs.
    enable_logging (bool): Optional. Enable firewall logging.
        Default is False.
  """
  logger.info('Putting instance "{0:s}", in project {1:s}, in network '
              'quarantine.'.format(instance_name, project_id))
  project = gcp_project.GoogleCloudProject(project_id)
  instance = project.compute.GetInstance(instance_name)
  get_operation = instance.GetOperation()
  network_interfaces = get_operation['networkInterfaces']
  target_tags = []
  for interface in network_interfaces:
    network_url = interface["network"]
    # Adding a random suffix to the tag to avoid name collisions,
    # tags are used as firewall rule names, which need to be unique.
    tag_suffix = random.randint(10**(19),(10**20)-1)
    deny_ingress_tag = 'deny-ingress-tag-' + str(tag_suffix)
    deny_egress_tag = 'deny-egress-tag-' + str(tag_suffix)
    AddDenyAllFirewallRules(
        project_id,
        network_url,
        deny_ingress_tag,
        deny_egress_tag,
        exempted_src_ips,
        enable_logging)
    target_tags.append(deny_ingress_tag)
    target_tags.append(deny_egress_tag)
  instance.SetTags(target_tags)
  if exempted_src_ips:
    logger.info('From a host with an exempted IP, '
        'connect to the quarantined instance using:\n'
        'gcloud compute ssh --zone "{0:s}" "{1:s}" --project "{2:s}"\n'
        'Connecting from the browser via GCP console will not work.'.format(
              instance.zone, instance_name, project_id))
  # Then remove the VM's external IP address, to break all ongoing
  # connections
  logger.info('Removing external IP addresses to break ongoing connections')
  removed_ips = instance.RemoveExternalIps()
  # Now re-assign the IP address
  available_ips = set(project.compute.ListReservedExternalIps(instance.zone))
  for net_if, removed_ip in removed_ips.items():
    if removed_ip in available_ips:
      # IP address was static, re-assign static
      logger.info('Re-assigning static IP {0:s} to {1:s}'.format(
        removed_ip,
        net_if))
      instance.AssignExternalIp(net_if, removed_ip)
    else:
      # IP address was ephemeral, re-assign ephemeral
      logger.info('Re-assigning ephemeral IP to {0:s}'.format(net_if))
      instance.AssignExternalIp(net_if, None)

def VMRemoveServiceAccount(project_id: str,
                           instance_name: str,
                           leave_stopped: bool = False) -> bool:
  """
  Remove a service account attachment from a GCP VM.

  Service account attachments to VMs allow the VM to obtain credentials
  via the instance metadata service to perform API actions. Removing
  the service account attachment will prevent credentials being issued.

  Note that the instance will be powered down, if it isn't already for
  this action.

  Args:
    project_id (str): Google Cloud Project ID.
    instance_name (str): The name of the virtual machine.
    leave_stopped (bool): Optional. True to leave the machine powered off.

  Returns:
    bool: True if the service account was successfully removed, False otherwise.
  """
  logger.info('Removing service account attachment from "{0:s}",'
              ' in project {1:s}'.format(instance_name, project_id))

  valid_starting_states = ['RUNNING', 'STOPPING', 'TERMINATED']

  project = gcp_project.GoogleCloudProject(project_id)
  instance = project.compute.GetInstance(instance_name)

  # Get the initial powered state of the instance
  initial_state = instance.GetPowerState()

  if not initial_state in valid_starting_states:
    logger.error('Instance "{0:s}" is currently {1:s} which is an invalid '
               'state for this operation'.format(instance_name, initial_state))
    return False

  try:
    # Stop the instance if it is not already (or on the way)....
    if not initial_state in ('TERMINATED', 'STOPPING'):
      instance.Stop()

    # Remove the service account
    instance.DetachServiceAccount()

    # If the instance was running initially, and the option has been set,
    # start up the instance again
    if initial_state == 'RUNNING' and not leave_stopped:
      instance.Start()
  except errors.LCFError as exception:
    logger.error('Fatal exception encountered: {0:s}'.format(str(exception)))

  return True
