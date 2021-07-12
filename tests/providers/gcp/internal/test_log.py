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
"""Tests for the gcp module - log.py"""

import typing
import unittest
import mock

from tests.providers.gcp import gcp_mocks


class GoogleCloudLogTest(unittest.TestCase):
  """Test Google Cloud Log class."""
  # pylint: disable=line-too-long

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.log.GoogleCloudLog.GclApi')
  def testListLogs(self, mock_gcl_api):
    """Test that logs of project are correctly listed."""
    logs = mock_gcl_api.return_value.logs.return_value.list
    logs.return_value.execute.return_value = gcp_mocks.MOCK_LOGS_LIST
    list_logs = gcp_mocks.FAKE_LOGS.ListLogs()
    self.assertEqual(2, len(list_logs))
    self.assertEqual(gcp_mocks.FAKE_LOG_LIST[0], list_logs[0])

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.log.GoogleCloudLog.GclApi')
  def testExecuteQuery(self, mock_gcl_api):
    """Test that logs of project are correctly queried."""
    query = mock_gcl_api.return_value.entries.return_value.list
    query.return_value.execute.return_value = gcp_mocks.MOCK_LOG_ENTRIES
    qfilter = ['*']
    query_logs = gcp_mocks.FAKE_LOGS.ExecuteQuery(qfilter)
    self.assertEqual(2, len(query_logs))
    self.assertEqual(gcp_mocks.FAKE_LOG_ENTRIES[0], query_logs[0])
