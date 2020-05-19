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

import time

from google.auth.exceptions import RefreshError, DefaultCredentialsError

from libcloudforensics.providers.gcp import internal


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
    self.gcl_api_client = internal.CreateService(
        'logging', self.LOGGING_API_VERSION)
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
