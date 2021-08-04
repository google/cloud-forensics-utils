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
import datetime
import os
import shutil
import tempfile
from typing import TYPE_CHECKING, List, Dict, Any, Optional

import googleapiclient.http
from googleapiclient.errors import HttpError

from libcloudforensics import errors
from libcloudforensics import logging_utils
from libcloudforensics.providers.gcp.internal import common
# pylint: disable=line-too-long
from libcloudforensics.providers.gcp.internal import monitoring as gcp_monitoring
# pylint: enable=line-too-long
from libcloudforensics.providers.utils.storage_utils import SplitStoragePath

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)

if TYPE_CHECKING:
  import googleapiclient  # pylint: disable=ungrouped-imports


class GoogleCloudStorage:
  """Class to call Google Cloud Storage APIs.

  Attributes:
    project_id: Google Cloud project ID.
  """
  CLOUD_STORAGE_API_VERSION = 'v1'

  def __init__(self, project_id: Optional[str] = None) -> None:
    """Initialize the GoogleCloudStorage object.

    Args:
      project_id (str): Optional. Google Cloud project ID.
    """

    self.project_id = project_id

  def GcsApi(self) -> 'googleapiclient.discovery.Resource':
    """Get a Google Cloud Storage service object.

    Returns:
      googleapiclient.discovery.Resource: A Google Cloud Storage service object.
    """

    return common.CreateService(
        'storage', self.CLOUD_STORAGE_API_VERSION)

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
    bucket, object_path = SplitStoragePath(gcs_path)
    gcs_objects = self.GcsApi().objects() # pylint: disable=no-member
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
    gcs_bac = self.GcsApi().bucketAccessControls() # pylint: disable=no-member
    request = gcs_bac.list(bucket=bucket, userProject=user_project)
    # https://cloud.google.com/storage/docs/json_api/v1/bucketAccessControls#resource
    ac_response = request.execute()
    for item in ac_response.get('items', []):
      if item.get('kind') == 'storage#bucketAccessControl':  # Sanity check
        ret[item['role']].append(item['entity'])
    gcs_buckets = self.GcsApi().buckets() # pylint: disable=no-member
    request = gcs_buckets.getIamPolicy(bucket=bucket)
    # https://cloud.google.com/storage/docs/json_api/v1/buckets/getIamPolicy
    iam_response = request.execute()
    for item in iam_response.get('bindings', []):
      for member in item.get('members', []):
        ret[item['role']].append(member)
    return ret

  def ListBuckets(self) -> List[Dict[str, Any]]:
    """List buckets in a Google Cloud project.

    Returns:
      List[Dict[str, Any]]: List of object dicts.
      (https://cloud.google.com/storage/docs/json_api/v1/buckets#resource)
    """
    gcs_buckets = self.GcsApi().buckets() # pylint: disable=no-member
    request = gcs_buckets.list(project=self.project_id)
    objects = request.execute()  # type: Dict[str, Any]
    return objects.get('items', [])

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
    gcs_objects = self.GcsApi().objects() # pylint: disable=no-member
    request = gcs_objects.list(bucket=bucket)
    objects = request.execute()  # type: Dict[str, Any]
    return objects.get('items', [])

  def DeleteObject(self, gcs_path: str) -> None:
    """Deletes an object in a Google Cloud Storage bucket.

    Args:
      gcs_path (str): Full path to the object (ie: gs://bucket/dir1/dir2/obj)
    """

    if not gcs_path.startswith('gs://'):
      gcs_path = 'gs://' + gcs_path
    bucket, object_path = SplitStoragePath(gcs_path)
    gcs_objects = self.GcsApi().objects() # pylint: disable=no-member
    request = gcs_objects.delete(bucket=bucket, object=object_path)
    request.execute()  # type: Dict[str, Any]

  def GetBucketSize(self,
                    bucket: str,
                    timeframe: int = 1) -> Dict[str, int]:
    """List the size of a Google Storage Bucket in a project (default: last 1
    day).

    Note: This will list the _maximum size_
          (in bytes) the bucket had in the timeframe.

    Ref: https://cloud.google.com/monitoring/api/metrics_gcp#gcp-storage

    Args:
      bucket (str):  Name of a bucket in GCS.
      timeframe (int): Optional. The number (in days) for
          which to measure activity.
          Default: 1 day.

    Returns:
      Dict[str, int]: Dictionary mapping bucket name to its size (in bytes).
    """

    start_time = common.FormatRFC3339(
        datetime.datetime.utcnow() - datetime.timedelta(days=timeframe))
    end_time = common.FormatRFC3339(datetime.datetime.utcnow())
    period = timeframe * 24 * 60 * 60

    assert self.project_id  # Necessary for mypy check
    gcm = gcp_monitoring.GoogleCloudMonitoring(self.project_id)
    gcm_api = gcm.GcmApi()
    gcm_timeseries_client = gcm_api.projects().timeSeries() # pylint: disable=no-member
    qfilter = ('metric.type="storage.googleapis.com/storage/total_bytes" '
               'resource.type="gcs_bucket"')
    qfilter += ' resource.label.bucket_name="{0:s}"'.format(bucket)

    responses = common.ExecuteRequest(
        gcm_timeseries_client,
        'list',
        {
            'name': 'projects/{0:s}'.format(self.project_id),
            'filter': qfilter,
            'interval_startTime': start_time,
            'interval_endTime': end_time,
            'aggregation_groupByFields': 'resource.label.bucket_name',
            'aggregation_perSeriesAligner': 'ALIGN_MAX',
            'aggregation_alignmentPeriod': '{0:d}s'.format(period),
            'aggregation_crossSeriesReducer': 'REDUCE_NONE'
        })

    ret = {}
    for response in responses:
      for ts in response.get('timeSeries', []):
        bucket = ts.get('resource', {}).get('labels', {}).get('bucket_name', '')
        if bucket:
          points = ts.get('points', [])
          for point in points:
            val = point.get('value', {}).get('doubleValue', 0)
            if bucket not in ret:
              ret[bucket] = val
            elif val > ret[bucket]:
              ret[bucket] = val
    return ret

  def CreateBucket(
      self,
      bucket: str,
      labels: Optional[Dict[str, str]] = None,
      predefined_acl: str = 'private',
      predefined_default_object_acl: str = 'private') -> Dict[str, Any]:
    """Creates a Google Cloud Storage bucket in the current project.

    Args:
      bucket (str): Name of the desired bucket.
      labels (Dict[str, str]): Mapping of key/value strings to be applied as a label
        to the bucket.
        Rules for acceptable label values are located at
        https://cloud.google.com/storage/docs/key-terms#bucket-labels
      predefined_acl (str): A predefined set of Access Controls
        to apply to the bucket.
      predefined_default_object_acl (str): A predefined set of Access Controls
        to apply to the objects in the bucket.
      Values listed in https://cloud.google.com/storage/docs/json_api/v1/buckets/insert#parameters  # pylint: disable=line-too-long

    Returns:
      Dict[str, Any]: An API operation object for a Google Cloud Storage bucket.
           https://cloud.google.com/storage/docs/json_api/v1/buckets#resource
    """
    if bucket.startswith('gs://'):
      bucket = bucket[5:]
    gcs_buckets = self.GcsApi().buckets() # pylint: disable=no-member
    body = {'name': bucket, 'labels': labels}
    request = gcs_buckets.insert(
        project=self.project_id,
        predefinedAcl=predefined_acl,
        predefinedDefaultObjectAcl=predefined_default_object_acl,
        body=body)
    try:
      response = request.execute()  # type: Dict[str, Any]
    except HttpError as exception:
      if exception.resp.status == 409:
        raise errors.ResourceCreationError(
            'Bucket {0:s} already exists: {1!s}'.format(bucket, exception),
            __name__) from exception
      raise errors.ResourceCreationError(
          'Unknown error occurred when creating bucket:'
          ' {0!s}'.format(exception), __name__) from exception
    return response

  def GetObject(self,
                gcs_path: str,
                out_file: Optional[str] = None) -> str:
    """Gets the contents of an object in a Google Cloud Storage bucket.

    Args:
      gcs_path (str): Full path to the object (ie: gs://bucket/dir1/dir2/obj)
      out_file (str): Path to the local file that will be written.
        If not provided, will create a temporary file.

    Returns:
      str: The filename of the written object.

    Raises:
      ResourceCreationError: If the file couldn't be downloaded.
    """
    if not gcs_path.startswith('gs://'):
      gcs_path = 'gs://' + gcs_path
    gcs_objects = self.GcsApi().objects() # pylint: disable=no-member
    (bucket, filename) = SplitStoragePath(gcs_path)
    request = gcs_objects.get_media(bucket=bucket, object=filename)

    if not out_file:
      outputdir = tempfile.mkdtemp()
      logger.info('Created temporary directory {0:s}'.format(outputdir))
      out_file = os.path.join(outputdir, os.path.basename(filename))

    stat = shutil.disk_usage(os.path.dirname(outputdir))
    om = self.GetObjectMetadata(gcs_path)
    if 'size' not in om:
      logger.warning('Unable to retrieve object metadata before fetching')
    else:
      if int(om['size']) > stat.free:
        raise errors.ResourceCreationError(
            'Target drive does not have enough space ({0!s} free vs {1!s} needed)'  # pylint: disable=line-too-long
            .format(stat.free, om['size']),
            __name__)

    with open(out_file, 'wb') as outputfile:
      downloader = googleapiclient.http.MediaIoBaseDownload(outputfile, request)

      done = False
      while not done:
        status, done = downloader.next_chunk()
        if status.total_size > stat.free:
          raise errors.ResourceCreationError(
              'Target drive does not have enough space ({0!s} free vs {1!s} needed)'  # pylint: disable=line-too-long
              .format(stat.free, status.total_size),
              __name__)
        logger.info('Download {}%.'.format(int(status.progress() * 100)))
      logger.info('File successfully written to {0:s}'.format(out_file))

    return out_file
