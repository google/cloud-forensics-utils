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

from typing import TYPE_CHECKING, List, Any
from libcloudforensics.providers.gcp.internal import common

if TYPE_CHECKING:
  import googleapiclient


class GoogleServiceUsage:
  """Class to call the Google Cloud Service Usage API."""

  SERVICE_USAGE_API_VERSION = 'v1'

  def GsuApi(self) -> 'googleapiclient.discovery.Resource':
    """Get a Service Usage service object.

    Returns:
      googleapiclient.discovery.Resource: A Service Usage service object.
    """

    return common.CreateService(
        'serviceusage', self.SERVICE_USAGE_API_VERSION)

  def GetEnabled(self, project_number: str) -> List[Any]:
    """Get enabled services/APIs for a project.

    Args:
      project_number (str): The project_number to fetch enabled APIs for.

    Returns:
      List[Any]: A list of enabled services/APIs.
    """

    services_client = self.GsuApi().services() # pylint: disable=no-member
    parent = 'projects/' + project_number
    request = {'parent': parent, 'filter': 'state:ENABLED'}
    responses = common.ExecuteRequest(services_client, 'list', request)

    services = []
    for response in responses:
      for service in response.get('services', []):
        services.append(service['config']['name'])

    return services

  def EnableService(self, project_number: str, service_name: str) -> None:
    """Enable a service/API for a project.

    Args:
      project_number (str): The project_number to enable the service for.
      service_name (str): The service to enable.
    """

    services_client = self.GsuApi().services() # pylint: disable=no-member
    name = 'projects/' + project_number + '/services/' + service_name
    request = {'name': name}
    common.ExecuteRequest(services_client, 'enable', request)

  def DisableService(self, project_number: str, service_name: str) -> None:
    """Disable a service/API for a project.

    Args:
      project_number (str): The project_number to disable the service for.
      service_name (str): The service to disable.
    """

    services_client = self.GsuApi().services() # pylint: disable=no-member
    name = 'projects/' + project_number + '/services/' + service_name
    request = {'name': name}
    common.ExecuteRequest(services_client, 'disable', request)
