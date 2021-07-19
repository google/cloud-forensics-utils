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
"""Google Cloud Build functionalities."""

import logging
import time
from typing import Dict, Any
import googleapiclient


from libcloudforensics.providers.gcp.internal import common


class GoogleCloudBuild:
  """Class to call Google Cloud Build APIs.

  Dictionary objects content can be found in
  https://cloud.google.com/cloud-build/docs/api/reference/rest/v1/projects.builds
  """
  CLOUD_BUILD_API_VERSION = 'v1'

  def __init__(self, project_id: str) -> None:
    """Initialize the GoogleCloudBuild object.

    Args:
      project_id (str): Google Cloud project ID.
    """

    self.project_id = project_id

  def GcbApi(self) -> 'googleapiclient.discovery.Resource':
    """Get a Google Cloud Build service object.

    Returns:
      googleapiclient.discovery.Resource: A Google Cloud Build service object.
    """

    return common.CreateService(
        'cloudbuild', self.CLOUD_BUILD_API_VERSION)

  def CreateBuild(self, build_body: Dict[str, Any]) -> Dict[str, Any]:
    """Create a cloud build.

    Args:
      build_body (Dict): A dictionary that describes how to find the source
          code and how to build it.

    Returns:
      Dict: Represents long-running operation that is the result of a network
          API call.
    """
    cloud_build_client = self.GcbApi().projects().builds() # pylint: disable=no-member
    build_info = cloud_build_client.create(
        projectId=self.project_id,
        body=build_body).execute()  # type: Dict[str, Any]
    build_metadata = build_info['metadata']['build']
    common.logger.info(
        'Build started, logs bucket: {0:s}, logs URL: {1:s}'.format(
            build_metadata['logsBucket'], build_metadata['logUrl']))
    return build_info

  def _RetryExecuteRequest(self, operation_name: str) -> Dict[str, Any]:
    """Execute GCB operation.get request and retry if error.

    Args:
      operation_name (str): The name of the operation resource,

    Returns:
      Dict: Represents long-running operation that is the result of a network
          API call.

    Raises:
      RuntimeError: If getting the Cloud Build API operation object failed.
    """
    block_retry_max = 10
    service = self.GcbApi()
    request = service.operations().get(name=operation_name) # pylint: disable=no-member
    get_success = False
    for block_retry in range(block_retry_max):
      try:
        response = request.execute()  # type: Dict[str, Any]
        get_success = True
      except googleapiclient.errors.HttpError as error:
        logging.info(
            'build.BlockOperation: Get request to cloudbuild.googleapis.com '
            'failed.\nTry {0:d} of {1:d}. Error: {2!s} '.format(
                block_retry, block_retry_max, error))
      if get_success:
        break
      if block_retry == block_retry_max - 1:
        raise RuntimeError(
            'Failure blocking Cloud Build operation: {0:s}'.format(
                operation_name))
    return response

  def BlockOperation(self, response: Dict[str, Any]) -> Dict[str, Any]:
    """Block execution until API operation is finished.

    Args:
      response (Dict): Google Cloud Build API response.

    Returns:
      Dict: Holding the response of a get operation on an API object of type
          operations.

    Raises:
      RuntimeError: If the Cloud Build failed or if getting the Cloud Build
          API operation object failed.
    """
    while True:
      response = self._RetryExecuteRequest(response['name'])
      if response.get('done') and response.get('error'):
        build_metadata = response['metadata']['build']
        raise RuntimeError(
            ': {0:1}, logs bucket: {1:s}, logs URL: {2:s}'.format(
                response['error']['message'],
                build_metadata['logsBucket'],
                build_metadata['logUrl']))

      if response.get('done') and response.get('response'):
        return response
      time.sleep(5)  # Seconds between requests
