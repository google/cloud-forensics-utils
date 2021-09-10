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

import time
from typing import TYPE_CHECKING, Dict, List, Any
from libcloudforensics.providers.gcp.internal import common

if TYPE_CHECKING:
  import googleapiclient


class GoogleServiceUsage:
  """Class to call the Google Cloud Service Usage API.

  Attributes:
    project_id: Google Cloud project ID.
  """

  SERVICE_USAGE_API_VERSION = 'v1'
  NOOP_API_RESPONSE = 'operations/noop.DONE_OPERATION'

  def __init__(self, project_id: str) -> None:
    """Initialize the GoogleServiceUsage object.

    Args:
      project_id (str): Google Cloud project ID.
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

  def _BlockOperation(self, response: Dict[str, Any]) -> Dict[str, Any]:
    """Block until API operation is finished.

    Args:
      response (Dict): Service Usage API response.

    Returns:
      Dict: Holding the response of a get operation on an API object of type
          Operation.
    """

    operations_api = self.GsuApi().operations() # pylint: disable=no-member

    if response['name'] == self.NOOP_API_RESPONSE:
      return response

    while True:
      request = {'name': response['name']}
      result = common.ExecuteRequest(operations_api, 'get', request)[0]
      if 'done' in result:
        return result
      time.sleep(5)  # Seconds between requests

  def EnableService(self, service_name: str) -> None:
    """Enable a service/API for a project.

    Args:
      service_name (str): The service to enable.
    """

    services_client = self.GsuApi().services() # pylint: disable=no-member
    name = 'projects/' + self.project_id + '/services/' + service_name
    request = {'name': name}
    response = common.ExecuteRequest(services_client, 'enable', request)[0]
    self._BlockOperation(response)

  def DisableService(self, service_name: str) -> None:
    """Disable a service/API for a project.

    Args:
      service_name (str): The service to disable.
    """

    services_client = self.GsuApi().services() # pylint: disable=no-member
    name = 'projects/' + self.project_id + '/services/' + service_name
    request = {'name': name}
    response = common.ExecuteRequest(services_client, 'disable', request)[0]
    self._BlockOperation(response)
