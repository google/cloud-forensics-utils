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
"""Tests for AWS module - s3.py."""

import typing
import unittest
import mock

from tests.providers.aws import aws_mocks


class AWSS3Test(unittest.TestCase):
  """Test AWS S3 class."""
  # pylint: disable=line-too-long

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ClientApi')
  def testCreateBucket(self, mock_s3_api):
    """Test that the Bucket is created."""
    storage = mock_s3_api.return_value.create_bucket
    storage.return_value = aws_mocks.MOCK_CREATE_BUCKET
    create_bucket = aws_mocks.FAKE_STORAGE.CreateBucket('test-bucket')

    storage.assert_called_with(
        Bucket='test-bucket',
        ACL='private',
        CreateBucketConfiguration={
            'LocationConstraint': aws_mocks.FAKE_AWS_ACCOUNT.default_region
        })
    self.assertEqual(200, create_bucket['ResponseMetadata']['HTTPStatusCode'])
    self.assertEqual('http://test-bucket.s3.amazonaws.com/', create_bucket['Location'])

    create_bucket = aws_mocks.FAKE_STORAGE.CreateBucket('test-bucket', region='us-east-1')
    storage.assert_called_with(
        Bucket='test-bucket',
        ACL='private')
