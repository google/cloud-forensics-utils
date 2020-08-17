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
"""Tests for the gcp module - compute_base_resource.py"""

import typing
import unittest
import mock

from tests.providers.gcp import gcp_mocks


class GoogleComputeBaseResourceTest(unittest.TestCase):
  """Test Google Cloud Compute Base Resource class."""
  # pylint: disable=line-too-long

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeInstance.GetOperation')
  def testGetValue(self, mock_get_operation):
    """Test that the correct value is retrieved for the given key."""
    mock_get_operation.return_value = {
        # https://cloud.google.com/compute/docs/reference/rest/v1/instances/get
        'name': gcp_mocks.FAKE_INSTANCE.name
    }
    self.assertEqual('fake-instance', gcp_mocks.FAKE_INSTANCE.GetValue('name'))
    self.assertIsNone(gcp_mocks.FAKE_INSTANCE.GetValue('key'))
