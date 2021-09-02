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
"""Google Service Usage functionality."""

from typing import TYPE_CHECKING, Optional, List, Any
from libcloudforensics.providers.gcp.internal import common

if TYPE_CHECKING:
  import googleapiclient


class GoogleServiceUsage:
  """Class to call the Google Cloud Service Usage API.

  Attributes:
    project_id: Google Cloud project ID.
  """

  SERVICE_USAGE_API_VERSION = 'v1'

  def __init__(self, project_id: Optional[str] = None) -> None:
    """Initialize the GoogleServiceUsage object.

    Args:
      project_id (str): Optional. Google Cloud project ID.
    """

    self.project_id = project_id

  def GsuApi(self) -> 'googleapiclient.discovery.Resource':
    """Get a Service Usage service object.

    Returns:
      googleapiclient.discovery.Resource: A Service Usage service object.
    """

    return common.CreateService(
        'serviceusage', self.SERVICE_USAGE_API_VERSION)

  def GetEnabled(self) -> List[Any]:
    """Get enabled services/APIs for a project.

    Returns:
      List[Any]: A list of enabled services/APIs.
    """

    services_client = self.GsuApi().services() # pylint: disable=no-member
    parent = 'projects/' + self.project_id
    request = {'parent': parent, 'filter': 'state:ENABLED'}
    responses = common.ExecuteRequest(services_client, 'list', request)

    services = []
    for response in responses:
      for service in response.get('services', []):
        services.append(service['config']['name'])

    return services

  def EnableService(self, service_name: str) -> None:
    """Enable a service/API for a project.

    Args:
      service_name (str): The service to enable.
    """

    services_client = self.GsuApi().services() # pylint: disable=no-member
    name = 'projects/' + self.project_id + '/services/' + service_name
    request = {'name': name}
    common.ExecuteRequest(services_client, 'enable', request)

  def DisableService(self, service_name: str) -> None:
    """Disable a service/API for a project.

    Args:
      service_name (str): The service to disable.
    """

    services_client = self.GsuApi().services() # pylint: disable=no-member
    name = 'projects/' + self.project_id + '/services/' + service_name
    request = {'name': name}
    common.ExecuteRequest(services_client, 'disable', request)
