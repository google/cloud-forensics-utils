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
"""Bucket functionality."""

import os
from typing import TYPE_CHECKING, List, Dict, Optional, Any

from libcloudforensics import errors
from libcloudforensics import logging_utils
from libcloudforensics.providers.aws.internal import common
from libcloudforensics.providers.gcp.internal import storage as gcp_storage
from libcloudforensics.providers.utils.storage_utils import SplitStoragePath


logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)

if TYPE_CHECKING:
  # TYPE_CHECKING is always False at runtime, therefore it is safe to ignore
  # the following cyclic import, as it it only used for type hints
  from libcloudforensics.providers.aws.internal import account  # pylint: disable=cyclic-import


class S3:
  """Class that represents AWS S3 storage services.

  Attributes:
    aws_account (AWSAccount): The account for the resource.
    name (str): The name of the bucket.
    region (str): The region in which the bucket resides.
  """

  def __init__(self,
               aws_account: 'account.AWSAccount') -> None:
    """Initialize the AWS S3 resource.

    Args:
      aws_account (AWSAccount): The account for the resource.
    """

    self.aws_account = aws_account

  def CreateBucket(
      self,
      name: str,
      region: Optional[str] = None,
      acl: str = 'private',
      tags: Optional[Dict[str, str]] = None,
      policy: Optional[str] = None) -> Dict[str, Any]:
    """Create an S3 storage bucket.

    Args:
      name (str): The name of the bucket.
      region (str): Optional. The region in which the bucket resides.
      acl (str): Optional. The canned ACL with which to create the bucket.
        Default is 'private'.
      tags (Dict[str, str]): Optional. A dictionary of tags to add to the
        bucket, for example {'TagName': 'TagValue'}.
      policy (str): Optional. A bucket policy to be applied after creation.
        It must be a valid JSON document.
    Appropriate values for the Canned ACLs are here:
    https://docs.aws.amazon.com/AmazonS3/latest/userguide/acl-overview.html#canned-acl  # pylint: disable=line-too-long

    New tags will not be set if the bucket already exists.

    Returns:
      Dict: An API operation object for a S3 bucket.
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Bucket.create  # pylint: disable=line-too-long

    Raises:
      ResourceCreationError: If the bucket couldn't be created or already exists.  # pylint: disable=line-too-long
    """

    client = self.aws_account.ClientApi(common.S3_SERVICE)
    try:
      desired_region = region or self.aws_account.default_region
      if desired_region == 'us-east-1':
        bucket = client.create_bucket(
            Bucket=name,
            ACL=acl)  # type: Dict[str, Any]
      else:
        bucket = client.create_bucket(
            Bucket=name,
            ACL=acl,
            CreateBucketConfiguration={
                'LocationConstraint': desired_region
            })
    except client.exceptions.BucketAlreadyOwnedByYou as exception:
      raise errors.ResourceCreationError(
          'Bucket {0:s} already exists: {1:s}'.format(
              name, str(exception)),
          __name__) from exception
    except client.exceptions.ClientError as exception:
      raise errors.ResourceCreationError(
          'Could not create bucket {0:s}: {1:s}'.format(
              name, str(exception)),
          __name__) from exception
    logger.info('Bucket successfully created')

    if tags:
      bucket_tags = {'TagSet': []}  # type: Dict[str, List[Dict[str, str]]]
      for k, v in tags.items():
        bucket_tags['TagSet'].append({'Key': k, 'Value': v})
      try:
        client.put_bucket_tagging(Bucket=name, Tagging=bucket_tags)
        logger.info('Tags successfully set')
      except client.exceptions.ClientError as exception:
        logger.warning(
            'Error while setting tags: {0:s} - {1:s}'.format(
                exception.response['Error'].get('Code', ''),
                exception.response['Error'].get('Message', '')))

    if policy:
      try:
        client.put_bucket_policy(Bucket=name, Policy=policy)
        logger.info('Policy successfully set')
      except client.exceptions.ClientError as exception:
        logger.warning(
            'Error while setting policy: {0:s} - {1:s}'.format(
                exception.response['Error'].get('Code', ''),
                exception.response['Error'].get('Message', '')))

    return bucket

  def Put(
      self,
      s3_path: str,
      filepath: str,
      extra_args: Optional[Dict[str, str]] = None) -> None:
    """Upload a local file to an S3 bucket.

    Keeps the local filename intact.

    Args:
      s3_path (str): Path to the target S3 bucket.
          Ex: s3://test/bucket
      filepath (str): Path to the file to be uploaded.
          Ex: /tmp/myfile
      extra_args (Dict[str, str]): Optional. A dictionary of extra arguments
        that will be directly supplied to the upload_file call.  Useful for
        specifying encryption parameters.
          Ex: {'ServerSideEncryption': "AES256"}
    Raises:
      ResourceCreationError: If the object couldn't be uploaded.
    """
    client = self.aws_account.ClientApi(common.S3_SERVICE)
    if not s3_path.startswith('s3://'):
      s3_path = 's3://' + s3_path
    if not s3_path.endswith('/'):
      s3_path = s3_path + '/'
    try:
      (bucket, path) = SplitStoragePath(s3_path)
      client.upload_file(
          filepath,
          bucket,
          '{0:s}{1:s}'.format(path, os.path.basename(filepath)),
          ExtraArgs=extra_args)
    except FileNotFoundError as exception:
      raise errors.ResourceNotFoundError(
          'Could not upload file {0:s}: {1:s}'.format(
              filepath, str(exception)),
          __name__) from exception
    except client.exceptions.ClientError as exception:
      raise errors.ResourceCreationError(
          'Could not upload file {0:s}: {1:s}'.format(
              filepath, str(exception)),
          __name__) from exception

  def GCSToS3(self,
              project_id: str,
              gcs_path: str,
              s3_path: str,
              s3_args: Optional[Dict[str, str]] = None) -> None:
    """Copy an object in GCS to an S3 bucket.

    (Creates a local copy of the file in a temporary directory)

    Args:
      project_id (str): Google Cloud project ID.
      gcs_path (str): File path to the source GCS object.
          Ex: gs://bucket/folder/obj
      s3_path (str): Path to the target S3 bucket.
          Ex: s3://test/bucket
      s3_args (Dict[str, str]): Optional. A dictionary of extra arguments to be
         supplied to the S3 Put call. Useful for specifying encryption
         parameters.
          Ex: {'ServerSideEncryption': "AES256"}
    Returns:
      Dict: An API operation object for an S3 Put request.
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.put_object  # pylint: disable=line-too-long
    Raises:
      ResourceCreationError: If the object couldn't be uploaded.
    """
    gcs = gcp_storage.GoogleCloudStorage(project_id)
    if not s3_path.startswith('s3://'):
      s3_path = 's3://' + s3_path
    if not gcs_path.startswith('gs://'):
      gcs_path = 'gs://' + gcs_path
    object_md = gcs.GetObjectMetadata(gcs_path)
    logger.warning(
        'This will download {0:s}b to a local'
        ' temporary directory before uploading it to S3.'
        .format(object_md.get('size', 'Error')))
    localcopy = gcs.GetObject(gcs_path)
    try:
      self.CreateBucket(SplitStoragePath(s3_path)[0])
    except errors.ResourceCreationError as exception:
      if 'already exists' in exception.message:
        logger.info('Target bucket already exists. Reusing.')
      else:
        raise exception
    self.Put(s3_path, localcopy, s3_args)
    logger.info('Attempting to delete local (temporary) copy')
    os.unlink(localcopy)
    logger.info('Done')

  def CheckForObject(
      self,
      bucket: str,
      key: str
    ) -> bool:
    """Check if an object exists in S3.

    Args:
      bucket (str): S3 nucket name.
      key (str): object path and name.

    Returns:
      bool: True if the object exists and you have permissions to GetObject.
        False otherwise."""
    s3_client = self.aws_account.ClientApi(common.S3_SERVICE)

    if key.startswith('/'):
      key = key.lstrip('/')

    try:
      s3_client.head_object(Bucket=bucket, Key=key)
    except s3_client.exceptions.ClientError:
      return False
    return True

  def RmObjectByPath(
      self,
      s3_path: str
    ) -> None:
    """Remove an object from S3.

    Args:
      s3_path (str): The path of the object to remove.
    """
    if not s3_path.startswith('s3://'):
      s3_path = 's3://' + s3_path
    bucket, key = SplitStoragePath(s3_path)

    self.RmObject(bucket, key)

  def RmObject(
      self,
      bucket: str,
      key: str
    ) -> None:
    """Remove an object from S3.

    Args:
      bucket (str): The S3 bucket.
      key (str): The object key (path).
    """
    if key.startswith('/'):
      key = key.lstrip('/')

    s3_client = self.aws_account.ClientApi(common.S3_SERVICE)
    s3_client.delete_object(Bucket=bucket, Key=key)

  def RmBucket(
      self,
      bucket: str
    ) -> None:
    """Delete an S3 bucket.

    Args:
      bucket (str): The bucket name.
    """
    logger.info('Deleting bucket {0:s}'.format(bucket))
    s3_client = self.aws_account.ClientApi(common.S3_SERVICE)
    s3_client.delete_bucket(Bucket=bucket)
