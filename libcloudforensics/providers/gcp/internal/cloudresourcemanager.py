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

from typing import TYPE_CHECKING, Dict, List, Any
from googleapiclient import errors as google_api_errors
from libcloudforensics.providers.gcp.internal import common

if TYPE_CHECKING:
  import googleapiclient


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
