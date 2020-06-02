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
"""Google compute functionality."""

import time

from libcloudforensics.providers.gcp.internal import common


class GoogleCloudBuild:
  """Class to call Google Cloud Build APIs.

  Attributes:
    gcb_api_client: Client to interact with GCB APIs.
  """
  CLOUD_BUILD_API_VERSION = 'v1'

  def __init__(self, project_id):
    """Initialize the GoogleCloudBuild object.

    Args:
      project_id (str): The name of the project.
    """

    self.gcb_api_client = None
    self.project_id = project_id

  def GcbApi(self):
    """Get a Google Cloud Build service object.

    Returns:
      apiclient.discovery.Resource: A Google Cloud Build service object.
    """

    if self.gcb_api_client:
      return self.gcb_api_client
    self.gcb_api_client = common.CreateService(
        'cloudbuild', self.CLOUD_BUILD_API_VERSION)
    return self.gcb_api_client

  def CreateBuild(self, build_body):
    """Create a cloud build.

    Args:
      build_body (dict): A dictionary that describes how to find the source
          code and how to build it.

    Returns:
      dict: Represents long-running operation that is the result of
          a network API call.
    """
    cloud_build_client = self.GcbApi().projects().builds()
    build_info = cloud_build_client.create(
        projectId=self.project_id, body=build_body).execute()
    build_metadata = build_info['metadata']['build']
    common.LOGGER.info(
        'Build started, logs bucket: {0:s}, logs URL: {1:s}'.format(
            build_metadata['logsBucket'], build_metadata['logUrl']))
    return build_info

  def BlockOperation(self, response):  # pylint: disable=arguments-differ
    """Block execution until API operation is finished.

    Args:
      response (dict): Google Cloud Build API response.

    Returns:
      dict: Holding the response of a get operation on an
          API object of type operations.

    Raises:
      RuntimeError: If API call failed.
    """
    service = self.GcbApi()
    while True:
      request = service.operations().get(name=response['name'])
      response = request.execute()
      if response.get('done') and response.get('error'):
        build_metadata = response['metadata']['build']
        raise RuntimeError(
            ': {0:1}, logs bucket: {1:s}, logs URL: {2:s}'.format(
                response['error']['message'], build_metadata['logsBucket'],
                build_metadata['logUrl']))

      if response.get('done') and response.get('response'):
        return response
      time.sleep(5)  # Seconds between requests
