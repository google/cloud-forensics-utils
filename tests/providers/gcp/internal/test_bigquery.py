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
"""Tests for the gcp module - bigquery.py"""

import typing
import unittest
import mock

from tests.providers.gcp import gcp_mocks


class GoogleBigQueryTest(unittest.TestCase):
  """Test Google BigQuery class."""
  # pylint: disable=line-too-long

  @typing.no_type_check
  @mock.patch(
      'libcloudforensics.providers.gcp.internal.bigquery.GoogleBigQuery.GoogleBigQueryApi'
  )
  def testListBigQueryJobs(self, mock_bigquery_api):
    """Test BigQuery Jobs List operation."""
    api_list_jobs = mock_bigquery_api.return_value.jobs.return_value.list
    api_list_jobs.return_value.execute.return_value = gcp_mocks.MOCK_BIGQUERY_JOBS
    list_results = gcp_mocks.FAKE_BIGQUERY.ListBigQueryJobs()
    self.assertEqual(1, len(list_results))
    self.assertEqual(
        'bquxjob_12345678_abcdefghij1k',
        list_results[0]['jobReference']['jobId'])
    self.assertEqual(
        'SELECT * FROM `fake-target-project.fake-target-project-dataset.fake-target-project-table`',
        list_results[0]['configuration']['query']['query'])
