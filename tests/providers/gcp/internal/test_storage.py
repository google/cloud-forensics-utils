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
"""Tests for the gcp module - storage.py"""

import typing
import unittest
import mock

from tests.providers.gcp import gcp_mocks
from libcloudforensics.providers.utils.storage_utils import SplitStoragePath


class GoogleCloudStorageTest(unittest.TestCase):
  """Test Google Cloud Storage class."""
  # pylint: disable=line-too-long

  @typing.no_type_check
  def testSplitGcsPath(self):
    """Tests that GCS path split is correctly done."""
    bucket, object_uri = SplitStoragePath('gs://fake-bucket/fake-folder/fake-object')
    self.assertEqual('fake-folder/fake-object', object_uri)
    self.assertEqual('fake-bucket', bucket)

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.storage.GoogleCloudStorage.GcsApi')
  def testGetObjectMetadata(self, mock_gcs_api):
    """Test GCS object Get operation."""
    api_get_object = mock_gcs_api.return_value.objects.return_value.get
    api_get_object.return_value.execute.return_value = gcp_mocks.MOCK_GCS_OBJECT_METADATA
    get_results = gcp_mocks.FAKE_GCS.GetObjectMetadata(
        'gs://fake-bucket/foo/fake.img')
    self.assertEqual(gcp_mocks.MOCK_GCS_OBJECT_METADATA, get_results)
    self.assertEqual('5555555555', get_results['size'])
    self.assertEqual('MzFiYWIzY2M0MTJjNGMzNjUyZDMyNWFkYWMwODA5YTEgIGNvdW50MQo=', get_results['md5Hash'])

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.storage.GoogleCloudStorage.GcsApi')
  def testListBuckets(self, mock_gcs_api):
    """Test GCS bucket List operation."""
    api_list_bucket = mock_gcs_api.return_value.buckets.return_value.list
    api_list_bucket.return_value.execute.return_value = gcp_mocks.MOCK_GCS_BUCKETS
    list_results = gcp_mocks.FAKE_GCS.ListBuckets()
    self.assertEqual(1, len(list_results))
    self.assertEqual('fake-bucket', list_results[0]['name'])
    self.assertEqual('123456789', list_results[0]['projectNumber'])

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.storage.GoogleCloudStorage.GcsApi')
  def testListBucketObjects(self, mock_gcs_api):
    """Test GCS object List operation."""
    api_list_object = mock_gcs_api.return_value.objects.return_value.list
    api_list_object.return_value.execute.return_value = gcp_mocks.MOCK_GCS_BUCKET_OBJECTS
    list_results = gcp_mocks.FAKE_GCS.ListBucketObjects('gs://fake-bucket')
    self.assertEqual(1, len(list_results))
    self.assertEqual('5555555555', list_results[0]['size'])
    self.assertEqual('MzFiYWIzY2M0MTJjNGMzNjUyZDMyNWFkYWMwODA5YTEgIGNvdW50MQo=', list_results[0]['md5Hash'])

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.storage.GoogleCloudStorage.GcsApi')
  def testGetBucketACLs(self, mock_gcs_api):
    """Test GCS ACL List operation."""
    api_acl_object = mock_gcs_api.return_value.bucketAccessControls.return_value.list
    api_acl_object.return_value.execute.return_value = gcp_mocks.MOCK_GCS_BUCKET_ACLS
    api_iam_object = mock_gcs_api.return_value.buckets.return_value.getIamPolicy
    api_iam_object.return_value.execute.return_value = gcp_mocks.MOCK_GCS_BUCKET_IAM
    acl_results = gcp_mocks.FAKE_GCS.GetBucketACLs('gs://fake-bucket')
    self.assertEqual(2, len(acl_results))
    self.assertEqual(2, len(acl_results['OWNER']))
    self.assertEqual(2, len(acl_results['roles/storage.legacyBucketOwner']))

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.monitoring.GoogleCloudMonitoring.GcmApi')
  def testGetBucketSize(self, mock_gcm_api):
    """Test GCS Bucket Size operation."""
    services = mock_gcm_api.return_value.projects.return_value.timeSeries.return_value.list
    services.return_value.execute.return_value = gcp_mocks.MOCK_GCM_METRICS_BUCKETSIZE
    size_results = gcp_mocks.FAKE_GCS.GetBucketSize('gs://test_bucket_1')
    self.assertEqual(1, len(size_results))
    self.assertEqual(60, size_results['test_bucket_1'])

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.storage.GoogleCloudStorage.GcsApi')
  def testCreateBucket(self, mock_gcs_api):
    """Test GCS bucket Create operation."""
    api_create_bucket = mock_gcs_api.return_value.buckets.return_value.insert
    api_create_bucket.return_value.execute.return_value = gcp_mocks.MOCK_GCS_BUCKETS['items'][0]
    create_result = gcp_mocks.FAKE_GCS.CreateBucket('fake-bucket')

    api_create_bucket.assert_called_with(
        project='fake-target-project',
        predefinedAcl='private',
        predefinedDefaultObjectAcl='private',
        body={
            'name': 'fake-bucket', 'labels': None
        })
    self.assertEqual('fake-bucket', create_result['name'])
    self.assertEqual('123456789', create_result['projectNumber'])
