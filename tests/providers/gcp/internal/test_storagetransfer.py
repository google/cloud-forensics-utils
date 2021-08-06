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
"""Tests for the gcp module - storagetransfer.py"""


import typing
import unittest
import mock

from libcloudforensics import errors
from tests.providers.gcp import gcp_mocks


class GoogleCloudStorageTransferTest(unittest.TestCase):
  """Test Google Cloud Storage Transfer class."""
  # pylint: disable=line-too-long

  @typing.no_type_check
  @mock.patch('boto3.session.Session.get_credentials')
  @mock.patch('boto3.session.Session._setup_loader')
  @mock.patch('libcloudforensics.providers.gcp.internal.storagetransfer.GoogleCloudStorageTransfer.GcstApi')
  def testS3ToGCS(self, mock_gcst_api, mock_loader, mock_creds):
    """Test S3ToGCS operation."""
    api_job_create = mock_gcst_api.return_value.transferJobs.return_value.create
    api_job_create.return_value.execute.return_value = gcp_mocks.MOCK_STORAGE_TRANSFER_JOB
    api_job_get = mock_gcst_api.return_value.transferOperations.return_value.list
    api_job_get.return_value.execute.return_value = gcp_mocks.MOCK_STORAGE_TRANSFER_OPERATION
    mock_loader.return_value = None
    creds = mock.MagicMock()
    creds.access_key = 'ABC'
    creds.secret_key = 'DEF'
    mock_creds.return_value = creds

    transfer_results = gcp_mocks.FAKE_GCST.S3ToGCS(
        's3://s3_source_bucket/file.name',
        'fake-zone-2b',
        'gs://gcs_sink_bucket/test_path')
    self.assertEqual(1, len(transfer_results['operations']))
    self.assertEqual('s3_source_bucket', transfer_results['operations'][0]['metadata']['transferSpec']['awsS3DataSource']['bucketName'])
    self.assertEqual('30', transfer_results['operations'][0]['metadata']['counters']['bytesCopiedToSink'])

  @typing.no_type_check
  @mock.patch('boto3.session.Session.get_credentials')
  def testS3ToGCSNoCreds(self, mock_creds):
    """Test S3TOGCS operation when no AWS credentials exist."""
    with self.assertRaises(errors.TransferCreationError):
      mock_creds.return_value = mock.MagicMock()
      gcp_mocks.FAKE_GCST.S3ToGCS(
          's3://s3_source_bucket/file.name',
          'fake-zone-2b',
          'gs://gcs_sink_bucket/test_path')

  @typing.no_type_check
  @mock.patch('boto3.session.Session.get_credentials')
  def testS3ToGCSTempCreds(self, mock_creds):
    """Test S3TOGCS operation when temporary AWS credentials exist."""
    creds = mock.MagicMock()
    creds.access_key = 'ASIA'
    creds.secret_key = 'DEF'
    mock_creds.return_value = creds
    with self.assertRaises(errors.TransferCreationError):
      gcp_mocks.FAKE_GCST.S3ToGCS(
          's3://s3_source_bucket/file.name',
          'fake-zone-2b',
          'gs://gcs_sink_bucket/test_path')
