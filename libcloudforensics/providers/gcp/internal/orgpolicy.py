# -*- coding: utf-8 -*-
# Copyright 2024 Google Inc.
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
"""Google Organization Policy API functionality."""
from typing import TYPE_CHECKING, Dict, List, Any
from googleapiclient import errors as google_api_errors

from libcloudforensics import logging_utils
from libcloudforensics.providers.gcp.internal import common

if TYPE_CHECKING:
  import googleapiclient

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)

class GoogleOrgPolicy:
  """Class to call the Google Organization Policy API.

  Attributes:
    project_id (str): Google Cloud project ID.
  """

  ORG_POLICY_API_VERSION = 'v2'

  def __init__(self, project_id: str) -> None:
    """Initialize the GoogleOrgPolicy object.

    Args:
      project_id (str): Google Cloud project ID.
    """

    self.project_id = project_id

  def OrgPolicyApi(self) -> 'googleapiclient.discovery.Resource':
    """Get an Organization Policy service object.

    Returns:
      googleapiclient.discovery.Resource: A Resource Manager service
          object.
    """

    return common.CreateService(
        'orgpolicy', self.ORG_POLICY_API_VERSION)

  def GetOrgConstraintsForProject(self) -> List[Dict[str, Any]]:
    """Retrieve all Organisation Constraints for a project.

    Returns:
        Dict[str, Any]: The policy details.

    Raises:
      HttpError: on exception.
    """
    service = self.OrgPolicyApi().projects().constraints() # pylint: disable=no-member
    parent = 'projects/{0:s}'.format(self.project_id)
    constraints: List[Dict[str, Any]] = {}
    try:
      request = service.list(parent=parent)
      constraints = request.execute()
    except google_api_errors.HttpError as he:
      if he.status_code == 404:
        return []
      raise he
    return constraints.get("constraints", [])

  def GetOrgPolicyForProject(self, policy_name: str) -> Dict[str, Any]:
    """Retrieve a particuar Organisation Policy for a resource.

    Args:
        policy_name (str): The policy to retrieve.

    Returns:
        Dict[str, Any]: The policy details.

    Raises:
      HttpError: on exception.
    """
    service = self.OrgPolicyApi().projects().policies() # pylint: disable=no-member
    request = 'projects/{0:s}/policies/{1:s}'.format(
        self.project_id, policy_name)
    try:
      response = service.get(name=request).execute()
    except google_api_errors.HttpError as he:
      if he.status_code == 404:
        return {}
      raise he
    return response

  def SetOrgProjectPolicyForProject(self, policy: Dict[str,
                                                       Any]) -> Dict[str, Any]:
    """Set a particular Organisation Policy for a resource.

    Args:
        policy (Dict[str, Any]) : The policy to create, as per
          https://cloud.google.com/resource-manager/docs/reference/orgpolicy/rest/v2/folders.policies#Policy

    Returns:
        Dict[str, Any]: The policy details.

    Raises:
      HttpError: on exception.
    """
    service = self.OrgPolicyApi().projects().policies() # pylint: disable=no-member
    parent = 'projects/{0:s}'.format(self.project_id)
    response = service.create(parent=parent, body=policy).execute()
    return response

  def DeleteOrgPolicyForProject(self, policy_name: str):
    """Delete a particular Organisation Policy for a resource.

    Args:
        policy_name (str): The policy to retrieve.

    Raises:
      HttpError: on exception.
    """
    service = self.OrgPolicyApi().projects().policies() # pylint: disable=no-member
    request = 'projects/{0:s}/policies/{1:s}'.format(
        self.project_id, policy_name)
    service.delete(name=request).execute()
