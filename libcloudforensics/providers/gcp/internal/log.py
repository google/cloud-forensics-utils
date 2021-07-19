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
"""Google Cloud Logging functionalities."""
from typing import Optional
from typing import TYPE_CHECKING, List, Dict, Any

from libcloudforensics.providers.gcp.internal import common

if TYPE_CHECKING:
  import googleapiclient


class GoogleCloudLog:
  """Class representing a Google Cloud Logs interface.

  Attributes:
    project_ids: List of Google Cloud project IDs.

  Example use:
    # pylint: disable=line-too-long
    gcp = GoogleCloudLog(project_id='your_project_name')
    gcp.ListLogs()
    gcp.ExecuteQuery(filter='resource.type="gce_instance" labels."compute.googleapis.com/resource_name"="instance-1"')
    See https://cloud.google.com/logging/docs/view/advanced-queries for filter details.
  """

  LOGGING_API_VERSION = 'v2'

  def __init__(self, project_ids: List[str]) -> None:
    """Initialize the GoogleCloudProject object.

    Args:
      project_ids (List[str]): List of project IDs.
    """
    self.project_ids = project_ids

  def GclApi(self) -> 'googleapiclient.discovery.Resource':
    """Get a Google Compute Logging service object.

    Returns:
      googleapiclient.discovery.Resource: A Google Compute Logging service
          object.
    """

    return common.CreateService(
        'logging', self.LOGGING_API_VERSION)

  def ListLogs(self) -> List[str]:
    """List logs in project.

    Returns:
      List[str]: The project logs available.

    Raises:
      RuntimeError: If API call failed.
    """

    logs = []
    gcl_instance_client = self.GclApi().logs() # pylint: disable=no-member
    for project_id in self.project_ids:
      responses = common.ExecuteRequest(
          gcl_instance_client,
          'list',
          {'parent': 'projects/' + project_id})
      for response in responses:
        for logtypes in response.get('logNames', []):
          logs.append(logtypes)

    return logs

  def ExecuteQuery(
      self, qfilter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Query logs in GCP project.

    Args:
      qfilter (List[str]): Optional. A list of query filters to use.

    Returns:
      List[Dict]: Log entries returned by the query, e.g. [{'projectIds':
          [...], 'resourceNames': [...]}, {...}]

    Raises:
      RuntimeError: If API call failed.
      ValueError: If the number of project IDs being queried doesn't match
          the number of provided filters.
    """

    entries = []
    gcl_instance_client = self.GclApi().entries() # pylint: disable=no-member

    if qfilter and len(self.project_ids) != len(qfilter):
      raise ValueError(
          'Several project IDs detected ({0:d}) but only {1:d} query filters '
          'provided.'.format(len(self.project_ids), len(qfilter)))

    for idx, project_id in enumerate(self.project_ids):
      body = {
          'resourceNames': 'projects/' + project_id,
          'filter': qfilter[idx] if qfilter else '',
          'orderBy': 'timestamp desc',
      }
      responses = common.ExecuteRequest(
          gcl_instance_client, 'list', {'body': body}, throttle=True)
      for response in responses:
        for entry in response.get('entries', []):
          entries.append(entry)
    return entries
