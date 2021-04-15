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

from typing import TYPE_CHECKING, Dict, Optional, Any

from libcloudforensics import errors
from libcloudforensics.providers.aws.internal import common

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
      acl: Optional[str] = 'private') -> Dict[str, Any]:
    """Create an S3 storage bucket.

    Args:
      name (str): The name of the bucket.
      region (str): Optional. The region in which the bucket resides.
      acl (str): The canned ACL with which to create the bucket.

    Appropriate values for the Canned ACLs are here:
    https://docs.aws.amazon.com/AmazonS3/latest/userguide/acl-overview.html#canned-acl  # pylint: disable=line-too-long
    """

    client = self.aws_account.ClientApi(common.S3_SERVICE)
    try:
      return client.create_bucket(
          Bucket=name,
          ACL=acl,
          CreateBucketConfiguration={'LocationConstraint':
              region or self.aws_account.default_region})  # type: Dict[str, str]
    except client.exceptions.ClientError as exception:
      raise errors.ResourceCreationError(
          'Could not create bucket {0:s}: {1:s}'.format(
              name, str(exception)),
          __name__) from exception
