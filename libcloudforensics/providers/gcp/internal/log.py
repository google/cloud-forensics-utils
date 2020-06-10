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
"""Log functionality."""

from typing import TYPE_CHECKING, List, Dict, Any

from libcloudforensics.providers.gcp.internal import common

if TYPE_CHECKING:
  import googleapiclient


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

  def __init__(self, project_id: str) -> None:
    """Initialize the GoogleCloudProject object.

    Args:
      project_id (str): The name of the project.
    """

    self.project_id = project_id
    self.gcl_api_client = None

  def GclApi(self) -> 'googleapiclient.discovery.Resource':
    """Get a Google Compute Logging service object.

    Returns:
      googleapiclient.discovery.Resource: A Google Compute Logging service
          object.
    """

    if self.gcl_api_client:
      return self.gcl_api_client
    self.gcl_api_client = common.CreateService(
        'logging', self.LOGGING_API_VERSION)
    return self.gcl_api_client

  def ListLogs(self) -> List[str]:
    """List logs in project.

    Returns:
      List[str]: The project logs available.

    Raises:
      RuntimeError: If API call failed.
    """

    logs = []
    gcl_instance_client = self.GclApi().logs()
    responses = common.ExecuteRequest(
        gcl_instance_client, 'list', {'parent': 'projects/' + self.project_id})

    for response in responses:
      for logtypes in response.get('logNames', []):
        logs.append(logtypes)

    return logs

  def ExecuteQuery(self, qfilter: str) -> List[Dict[str, Any]]:
    """Query logs in GCP project.

    Args:
      qfilter (str): The query filter to use.

    Returns:
      List[Dict]: Log entries returned by the query, e.g. [{'projectIds':
          [...], 'resourceNames': [...]}, {...}]

    Raises:
      RuntimeError: If API call failed.
    """

    body = {
        'resourceNames': 'projects/' + self.project_id,
        'filter': qfilter,
        'orderBy': 'timestamp desc',
    }

    entries = []
    gcl_instance_client = self.GclApi().entries()
    responses = common.ExecuteRequest(
        gcl_instance_client, 'list', body, throttle=True)

    for response in responses:
      for entry in response.get('entries', []):
        entries.append(entry)

    return entries
