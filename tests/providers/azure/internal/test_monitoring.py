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
"""Tests for the azure module - monitoring.py"""

import typing
import unittest
import mock

from tests.providers.azure import azure_mocks


class AZMonitoringTest(unittest.TestCase):
  """Test Azure monitoring class."""
  # pylint: disable=line-too-long

  @typing.no_type_check
  @mock.patch('azure.mgmt.monitor.v2018_01_01.operations._metric_definitions_operations.MetricDefinitionsOperations.list')
  def testListAvailableMetricsForResource(self, mock_list_metrics):
    """Test that metrics are correctly listed."""
    mock_list_metrics.return_value = azure_mocks.MOCK_LIST_METRICS
    metrics = azure_mocks.FAKE_MONITORING.ListAvailableMetricsForResource(
        'fake-resource-id')
    self.assertEqual(1, len(metrics))
    self.assertIn('fake-metric', metrics)

  @typing.no_type_check
  @mock.patch('azure.mgmt.monitor.v2018_01_01.operations._metrics_operations.MetricsOperations.list')
  def testGetMetricsForResource(self, mock_list_metrics_operations):
    """Test that metrics values are correctly retrieved."""
    mock_list_metrics_operations.return_value = azure_mocks.MOCK_METRIC_OPERATION
    metrics = azure_mocks.FAKE_MONITORING.GetMetricsForResource(
        'fake-resource-id', 'fake-metric')
    self.assertIn('fake-metric', metrics)
    self.assertEqual(1, len(metrics['fake-metric']))
    self.assertEqual('fake-value', metrics['fake-metric']['fake-time-stamp'])
