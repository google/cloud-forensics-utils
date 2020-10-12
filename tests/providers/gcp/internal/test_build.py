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
"""Tests for the gcp module - build.py"""

import typing
import unittest
import mock

from tests.providers.gcp import gcp_mocks


class GoogleCloudBuildTest(unittest.TestCase):
  """Test Google Cloud Build class."""
  # pylint: disable=line-too-long

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.build.GoogleCloudBuild.GcbApi')
  def testCreateBuild(self, mock_gcb_api):
    """Test that Cloud Builds are correctly created."""
    build_create_object = mock_gcb_api.return_value.projects.return_value.builds.return_value.create
    build_create_object.return_value.execute.return_value = gcp_mocks.MOCK_GCB_BUILDS_CREATE
    build_response = gcp_mocks.FAKE_GCB.CreateBuild({'Fake-Build_body': None})
    self.assertEqual(gcp_mocks.MOCK_GCB_BUILDS_CREATE, build_response)

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.build.GoogleCloudBuild.GcbApi')
  def testBlockOperation(self, mock_gcb_api):
    """Test that Cloud Builds are correctly blocked until done."""
    build_operation_object = mock_gcb_api.return_value.operations.return_value.get
    build_operation_object.return_value.execute.return_value = gcp_mocks.MOCK_GCB_BUILDS_SUCCESS
    block_build_success = gcp_mocks.FAKE_GCB.BlockOperation(
        gcp_mocks.MOCK_GCB_BUILDS_CREATE)
    self.assertEqual(gcp_mocks.MOCK_GCB_BUILDS_SUCCESS, block_build_success)
    build_operation_object.return_value.execute.return_value = gcp_mocks.MOCK_GCB_BUILDS_FAIL
    with self.assertRaises(RuntimeError):
      gcp_mocks.FAKE_GCB.BlockOperation(gcp_mocks.MOCK_GCB_BUILDS_CREATE)
