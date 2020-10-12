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
"""Google Cloud Functions functionalities."""

import json
import ssl
from typing import TYPE_CHECKING, Dict, Any
from googleapiclient.errors import HttpError
from libcloudforensics.providers.gcp.internal import common
from libcloudforensics import logging_utils

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)

if TYPE_CHECKING:
  import googleapiclient


class GoogleCloudFunction:
  """Class to call Google Cloud Functions.

  Attributes:
    project_id: Google Cloud project ID.
    gcf_api_client: Client to interact with GCF APIs.
  """

  CLOUD_FUNCTIONS_API_VERSION = 'v1'

  def __init__(self, project_id: str) -> None:
    """Initialize the GoogleCloudFunction object.

    Args:
      project_id (str): The name of the project.
    """

    self.gcf_api_client = None
    self.project_id = project_id

  def GcfApi(self) -> 'googleapiclient.discovery.Resource':
    """Get a Google Cloud Function service object.

    Returns:
      googleapiclient.discovery.Resource: A Google Cloud Function service
          object.
    """

    if self.gcf_api_client:
      return self.gcf_api_client
    self.gcf_api_client = common.CreateService(
        'cloudfunctions', self.CLOUD_FUNCTIONS_API_VERSION)
    return self.gcf_api_client

  def ExecuteFunction(self,
                      function_name: str,
                      region: str,
                      args: Dict[str, Any]) -> Dict[str, Any]:
    """Executes a Google Cloud Function.

    Args:
      function_name (str): The name of the function to call.
      region (str): Region to execute functions in.
      args (Dict): Arguments to pass to the function. Dictionary content
          details can be found in
          https://cloud.google.com/functions/docs/reference/rest/v1/projects.locations.functions  # pylint: disable=line-too-long

    Returns:
      Dict[str, str]: Return value from function call.

    Raises:
      RuntimeError: When cloud function arguments cannot be serialized or
          when an HttpError is encountered.
    """

    service = self.GcfApi()
    cloud_function = service.projects().locations().functions()

    try:
      json_args = json.dumps(args)
    except TypeError as exception:
      error_msg = (
          'Cloud function args [{0:s}] could not be serialized:'
          ' {1!s}').format(str(args), exception)
      raise RuntimeError(error_msg) from exception

    function_path = 'projects/{0:s}/locations/{1:s}/functions/{2:s}'.format(
        self.project_id, region, function_name)

    logger.debug(
        'Calling Cloud Function [{0:s}] with args [{1!s}]'.format(
            function_name, args))
    try:
      function_return = cloud_function.call(
          name=function_path, body={
              'data': json_args
          }).execute()  # type: Dict[str, Any]
    except (HttpError, ssl.SSLError) as exception:
      error_msg = 'Cloud function [{0:s}] call failed: {1!s}'.format(
          function_name, exception)
      raise RuntimeError(error_msg) from exception

    return function_return
