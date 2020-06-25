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
"""Google Cloud Storage functionalities."""

import base64
from typing import TYPE_CHECKING, Dict, Any, Optional, Tuple
from libcloudforensics.providers.gcp.internal import common

if TYPE_CHECKING:
  import googleapiclient


class GoogleCloudStorage:
  """Class to call Google Cloud Storage APIs.

  Attributes:
    gcs_api_client: Client to interact with GCS APIs.
  """
  CLOUD_STORAGE_API_VERSION = 'v1'

  def __init__(self, project_id: Optional[str] = None) -> None:
    """Initialize the GoogleCloudStorage object.

    Args:
      project_id (str): Optional. Google Cloud project ID.
    """

    self.gcs_api_client = None
    self.project_id = project_id

  def GcsApi(self) -> 'googleapiclient.discovery.Resource':
    """Get a Google Cloud Storage service object.

    Returns:
      googleapiclient.discovery.Resource: A Google Cloud Storage service object.
    """

    if self.gcs_api_client:
      return self.gcs_api_client
    self.gcs_api_client = common.CreateService(
        'storage', self.CLOUD_STORAGE_API_VERSION)
    return self.gcs_api_client

  def SplitGcsPath(self, gcs_path: str) -> Tuple[str, str]:
    """Split GCS path to bucket name and object URI.

    Args:
      gcs_path (str): File path to a resource in GCS.
          Ex: gs://bucket/folder/obj

    Returns:
      Tuple[str, str]: Bucket name. Object URI.
    """

    _, _, full_path = gcs_path.partition('//')
    bucket, _, object_uri = full_path.partition('/')
    return bucket, object_uri

  def GetOperationObject(
      self, gcs_path: str,
      user_project: Optional[str] = None) -> Dict[str, Any]:
    """Get API operation object for Google Cloud Storage object.

    Args:
      gcs_path (str): File path to a resource in GCS.
          Ex: gs://bucket/folder/obj
      user_project (str): The project ID to be billed for this request.
          Required for Requester Pays buckets.

    Returns:
      Dict: An API operation object for a Google Cloud Storage object.
    """

    bucket, object_path = self.SplitGcsPath(gcs_path)
    gcs_api_client = self.GcsApi().objects()
    request = gcs_api_client.get(
        bucket=bucket, object=object_path, userProject=user_project)
    response = request.execute()  # type: Dict[str, Any]
    return response

  def GetMD5Object(
      self,
      gcs_path: str,
      user_project: Optional[str] = None,
      in_hex: Optional[bool] = False) -> str:
    """"Gets MD5 hash value of the object as a (base64 | hex) string.

    Args:
      gcs_path (str): File path to a resource in GCS.
          Ex: gs://bucket/folder/obj
      user_project (str): The project ID to be billed for this request.
          Required for Requester Pays buckets.
      in_hex (boolean): Optional. Return the result as a hex string.
          Default is False.

    Returns:
      str: MD5 hash of the object as a (base64 | hex) string.
    """

    md5_base64 = self.GetOperationObject(gcs_path, user_project)['md5Hash']
    if in_hex:
      return base64.b64decode(md5_base64).hex()
    return md5_base64  # type: ignore

  def GetSizeObject(
      self, gcs_path: str, user_project: Optional[str] = None) -> str:
    """"Gets Content-Length of the object in bytes.

    Args:
      gcs_path (str): File path to a resource in GCS.
          Ex: gs://bucket/folder/obj
      user_project (str): The project ID to be billed for this request.
          Required for Requester Pays buckets.

    Returns:
      str: Content-Length of the data in bytes.
    """

    bytes_count = self.GetOperationObject(gcs_path, user_project)['size']
    return bytes_count  # type: ignore
