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

import collections
from typing import TYPE_CHECKING, List, Dict, Any, Optional, Tuple
from libcloudforensics.providers.gcp.internal import common

if TYPE_CHECKING:
  import googleapiclient


def SplitGcsPath(gcs_path: str) -> Tuple[str, str]:
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


class GoogleCloudStorage:
  """Class to call Google Cloud Storage APIs.

  Attributes:
    gcs_api_client: Client to interact with GCS APIs.
    project_id: Google Cloud project ID.
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

  def GetObjectMetadata(self,
                        gcs_path: str,
                        user_project: Optional[str] = None) -> Dict[str, Any]:
    """Get API operation object metadata for Google Cloud Storage object.

    Args:
      gcs_path (str): File path to a resource in GCS.
          Ex: gs://bucket/folder/obj
      user_project (str): The project ID to be billed for this request.
          Required for Requester Pays buckets.

    Returns:
      Dict: An API operation object for a Google Cloud Storage object.
           https://cloud.google.com/storage/docs/json_api/v1/objects#resource
    """
    if not gcs_path.startswith('gs://'):
      gcs_path = 'gs://' + gcs_path
    bucket, object_path = SplitGcsPath(gcs_path)
    gcs_objects = self.GcsApi().objects()
    request = gcs_objects.get(
        bucket=bucket, object=object_path, userProject=user_project)
    response = request.execute()  # type: Dict[str, Any]
    return response

  def GetBucketACLs(self,
                    bucket: str,
                    user_project: Optional[str] = None) -> Dict[str, List[str]]:
    """Get ACLs for a Google Cloud Storage bucket.

    This includes both ACL entries and IAM policies.

    Args:
      bucket (str): Name of a bucket in GCS.
          Ex: logs_bucket_1
      user_project (str): The project ID to be billed for this request.
          Required for Requester Pays buckets.

    Returns:
      Dict: A mapping of role to members of that role.
    """
    ret = collections.defaultdict(list)
    if bucket.startswith('gs://'):
      # Can change to removeprefix() in 3.9
      bucket = bucket[5:]
    gcs_bac = self.GcsApi().bucketAccessControls()
    request = gcs_bac.list(
        bucket=bucket, userProject=user_project)
    # https://cloud.google.com/storage/docs/json_api/v1/bucketAccessControls#resource
    ac_response = request.execute()
    for item in ac_response.get('items', []):
      if item.get('kind') == 'storage#bucketAccessControl':  # Sanity check
        ret[item['role']].append(item['entity'])
    gcs_buckets = self.GcsApi().buckets()
    request = gcs_buckets.getIamPolicy(bucket=bucket)
    # https://cloud.google.com/storage/docs/json_api/v1/buckets/getIamPolicy
    iam_response = request.execute()
    for item in iam_response.get('bindings', []):
      for member in item.get('members', []):
        ret[item['role']].append(member)
    return ret

  def ListBucketObjects(self, bucket: str) -> List[Dict[str, Any]]:
    """List objects (with metadata) in a Google Cloud Storage bucket.

    Args:
      bucket (str):  Name of a bucket in GCS.

    Returns:
      List of Object Dicts (see GetObjectMetadata)
    """
    if bucket.startswith('gs://'):
      # Can change to removeprefix() in 3.9
      bucket = bucket[5:]
    gcs_objects = self.GcsApi().objects()
    request = gcs_objects.list(bucket=bucket)
    objects = request.execute()  # type: Dict[str, Any]
    return objects.get('items', [])
