# -*- coding: utf-8 -*-
# Copyright 2021 Google Inc.
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
"""Google Cloud Resource Manager functionality."""
from typing import TYPE_CHECKING, Dict, List, Any, Optional
from googleapiclient import errors as google_api_errors

from libcloudforensics import logging_utils
from libcloudforensics.providers.gcp.internal import common

if TYPE_CHECKING:
  import googleapiclient

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)


class GoogleCloudResourceManager:
  """Class to call the Google Cloud Resource Manager API.

  Attributes:
    project_id: Google Cloud project ID.
  """

  RESOURCE_MANAGER_API_VERSION = 'v3'
  RESOURCE_TYPES = ['projects', 'folders', 'organizations']

  def __init__(self, project_id: str) -> None:
    """Initialize the GoogleCloudResourceManager object.

    Args:
      project_id (str): Google Cloud project ID.
    """

    self.project_id = project_id

  def GrmApi(self) -> 'googleapiclient.discovery.Resource':
    """Get a Resource Manager service object.

    Returns:
      googleapiclient.discovery.Resource: A Resource Manager service
          object.
    """

    return common.CreateService(
        'cloudresourcemanager', self.RESOURCE_MANAGER_API_VERSION)

  def ProjectAncestry(self) -> List[Any]:
    """List ancestor resources for a project.

    Returns:
      List[Any]: the list of ancestor resources. If the caller doesn't have
        permissions to call GetResource on a folder or organization this list
        will be incomplete.
    """

    ancestry = []
    current_resource = self.GetResource('projects/' + self.project_id)
    ancestry.append(current_resource)

    while 'parent' in current_resource:
      parent_name = current_resource['parent']
      try:
        current_resource = self.GetResource(parent_name)
      except google_api_errors.HttpError:
        # If the caller doesn't have permission to call GetResource on a
        # folder/organization at least record name from the child resource.
        current_resource = {
          'name': parent_name
        }
      ancestry.append(current_resource)

    return ancestry

  def GetResource(self, name: str) -> Dict[str, Any]:
    """Get a Cloud Resource Manager resource.

    Args:
      name (str): a resource identifier in the format
        resource_type/resource_number e.g. projects/123456789012 where
        project_type is one of projects, folders or organizations.

    Returns:
      Dict[str, Any]: The resource details.

    Raises:
      TypeError: if an invalid resource type is provided.
    """
    resource_type = name.split('/')[0]
    if resource_type not in self.RESOURCE_TYPES:
      raise TypeError('Invalid resource type "{0:s}", resource must be one of '
          '"projects", "folders" or "organizations" provided in the format '
          '"resource_type/resource_number".'.format(name))

    service = self.GrmApi()
    resource_client = getattr(service, resource_type)()
    request = {'name': name}
    # Safe to unpack
    response = common.ExecuteRequest(resource_client, 'get', request)[0]
    return response

  def DeleteResource(self, name: str) -> Dict[str, Any]:
    """Delete a Cloud Resource Manager resource.

    Args:
      name (str): a resource identifier in the format
        resource_type/resource_number e.g. projects/123456789012 where
        project_type is one of projects or folders.

    Returns:
      Dict[str, Any]: The operation's result details.

    Raises:
      TypeError: if an invalid resource type is provided.
    """
    resource_type = name.split('/')[0]
    if resource_type not in self.RESOURCE_TYPES[:-1]:
      raise TypeError('Invalid resource type "{0:s}", resource must be one of '
                      '"projects" or "folders" provided in the format '
                      '"resource_type/resource_number".'.format(name))
    service = self.GrmApi()
    resource_client = getattr(service, resource_type)()
    request = {'name': name}
    # Safe to unpack
    response = common.ExecuteRequest(resource_client, 'delete', request)[0]
    logger.info("Resource {0:s} was set for deletion.".format(name))
    return response

  def GetIamPolicy(self, name: str) -> Dict[str, Any]:
    """Get IAM policy bindings for a resource.

    Args:
      name (str): a resource identifier in the format
        resource_type/resource_number e.g. projects/123456789012 where
        project_type is one of projects, folders or organizations.

    Returns:
      Dict[str, Any]: The policy bindings for the resource.

    Raises:
      TypeError: if an invalid resource type is provided.
    """
    resource_type = name.split('/')[0]
    if resource_type not in self.RESOURCE_TYPES:
      raise TypeError('Invalid resource type "{0:s}", resource must be one of '
          '"projects", "folders" or "organizations" provided in the format '
          '"resource_type/resource_number".'.format(name))
    service = self.GrmApi()
    resource_client = getattr(service, resource_type)()
    request = {'resource': name}
    # Safe to unpack
    response = common.ExecuteRequest(
        resource_client, 'getIamPolicy', request)[0]

    return response

  def GetOrgPolicy(self, resource: str, constraint: str) -> Dict[str, Any]:
    """Gets a particular Org Policy on a resource.

    Args:
      resource (str): a resource identifier in the format
        resource_type/resource_number e.g. projects/123456789012 where
        project_type is one of projects, folders or organizations.
      constraint (str): the name of the constraint to get.

    Returns:
      Dict[str, Any]: The Org Policy details.
        See https://cloud.google.com/resource-manager/reference/rest/v1/Policy

    Raises:
      TypeError: if an invalid resource type is provided.
    """
    resource_type = resource.split('/')[0]
    if resource_type not in self.RESOURCE_TYPES:
      raise TypeError('Invalid resource type "{0:s}", resource must be one of '
          '"projects", "folders" or "organizations" provided in the format '
          '"resource_type/resource_number".'.format(resource))

    if not constraint.startswith('constraints/'):
      constraint = 'constraints/' + constraint

    # Override API version, since this doesn't exist in v2 or v3
    self.RESOURCE_MANAGER_API_VERSION = 'v1'  # pylint: disable=invalid-name
    service = self.GrmApi()
    resource_client = getattr(service, resource_type)()
    response: Dict[str, Any] = resource_client.getOrgPolicy(
        resource=resource, body={'constraint': constraint}
    ).execute()
    return response

  def ListOrgPolicy(self, resource: str) -> Dict[str, Any]:
    """Lists all Org Policies on a resource.

    Args:
      resource (str): a resource identifier in the format
        resource_type/resource_number e.g. projects/123456789012 where
        project_type is one of projects, folders or organizations.

    Returns:
      Dict[str, Any]: The Org Policy details.
        See https://cloud.google.com/resource-manager/reference/rest/v1/Policy

    Raises:
      TypeError: if an invalid resource type is provided.
    """
    resource_type = resource.split('/')[0]
    if resource_type not in self.RESOURCE_TYPES:
      raise TypeError('Invalid resource type "{0:s}", resource must be one of '
          '"projects", "folders" or "organizations" provided in the format '
          '"resource_type/resource_number".'.format(resource))

    # Override API version, since this doesn't exist in v2 or v3
    self.RESOURCE_MANAGER_API_VERSION = 'v1'
    service = self.GrmApi()
    resource_client = getattr(service, resource_type)()
    response: Dict[str, Any] = resource_client.listOrgPolicies(
        resource=resource).execute()
    return response

  def SetOrgPolicy(
      self, resource: str, policy: Dict[str, Any],
      etag: Optional[str] = None) -> Dict[str, Any]:
    """Updates the specified Policy on the resource.
    Creates a new Policy for that Constraint on the resource if one does
    not exist.
    

    Args:
      resource (str): a resource identifier in the format
        resource_type/resource_number e.g. projects/123456789012 where
        project_type is one of projects, folders or organizations.
      policy (dict): The policy to create, as per
        https://cloud.google.com/resource-manager/reference/rest/v1/Policy
      etag (str): The current version, for concurrency control.
        Not supplying an etag on the request Policy results in an unconditional
        write of the Policy.

    Returns:
      Dict[str, Any]: The Org Policy that was created.
        https://cloud.google.com/resource-manager/reference/rest/v1/Policy

    Raises:
      TypeError: if an invalid resource type is provided.
    """
    resource_type = resource.split('/')[0]
    if resource_type not in self.RESOURCE_TYPES:
      raise TypeError('Invalid resource type "{0:s}", resource must be one of '
          '"projects", "folders" or "organizations" provided in the format '
          '"resource_type/resource_number".'.format(resource))

    # Override API version, since this doesn't exist in v2 or v3
    self.RESOURCE_MANAGER_API_VERSION = 'v1'
    service = self.GrmApi()
    resource_client = getattr(service, resource_type)()
    body = {'policy': policy}
    if etag:
      body['policy']['etag'] = etag
    response: Dict[str, Any] = resource_client.setOrgPolicy(resource=resource,
                                            body=body).execute()
    return response

  def DeleteOrgPolicy(
      self, resource: str, constraint: str, etag: Optional[str] = None) -> bool:
    """Removes a particular Org Policy on a resource.

    Args:
      resource (str): a resource identifier in the format
        resource_type/resource_number e.g. projects/123456789012 where
        project_type is one of projects, folders or organizations.
      constraint (str): the name of the constraint to get.
      etag (str): The current version, for concurrency control.
        Not sending an etag will cause the Policy to be cleared blindly.

    Returns:
      bool: True if successful, False otherwise.

    Raises:
      TypeError: if an invalid resource type is provided.
    """
    resource_type = resource.split('/')[0]
    if resource_type not in self.RESOURCE_TYPES:
      raise TypeError('Invalid resource type "{0:s}", resource must be one of '
          '"projects", "folders" or "organizations" provided in the format '
          '"resource_type/resource_number".'.format(resource))

    if not constraint.startswith('constraints/'):
      constraint = 'constraints/' + constraint

    # Override API version, since this doesn't exist in v2 or v3
    self.RESOURCE_MANAGER_API_VERSION = 'v1'
    service = self.GrmApi()
    resource_client = getattr(service, resource_type)()
    body = {'constraint': constraint}
    if etag:
      body['etag'] = etag
    response: Dict[str, Any] = resource_client.clearOrgPolicy(
        resource=resource, body=body).execute()
    if not response:
      return True
    logger.warning("Unable to delete Org Policy: {0}".format(response))
    return False
