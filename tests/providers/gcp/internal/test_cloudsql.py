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
"""Tests for the gcp module - cloudsql.py"""

import typing
import unittest
import mock

from tests.providers.gcp import gcp_mocks

class GoogleCloudSqlTest(unittest.TestCase):
  """Test Google CloudSql class."""
  # pylint: disable=line-too-long

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.cloudsql.GoogleCloudSQL.GoogleCloudSQLApi')
  def testListCloudSqlInstances(self, mock_gcsql_api):
    """Test GCSql instance List operation."""
    api_list_instances = mock_gcsql_api.return_value.instances.return_value.list
    api_list_instances.return_value.execute.return_value = gcp_mocks.MOCK_GCSQL_INSTANCES
    list_results = gcp_mocks.FAKE_CLOUDSQLINSTANCE.ListCloudSQLInstances()
    self.assertEqual(1, len(list_results))
    self.assertEqual('FAKE_INSTANCE', list_results[0]['instanceType'])
    self.assertEqual('fake', list_results[0]['name'])
