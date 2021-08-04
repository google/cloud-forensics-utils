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
"""Tests for the gcp module - monitoring.py"""
import typing
import unittest

import mock

from tests.providers.gcp import gcp_mocks


class GoogleCloudMonitoringTest(unittest.TestCase):
  """Test Google Cloud Monitoring class."""
  # pylint: disable=line-too-long

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.monitoring.GoogleCloudMonitoring.GcmApi')
  def testActiveServices(self, mock_gcm_api):
    """Validates the parsing of Monitoring API TimeSeries data."""
    services = mock_gcm_api.return_value.projects.return_value.timeSeries.return_value.list
    services.return_value.execute.return_value = gcp_mocks.MOCK_GCM_METRICS_COUNT
    active_services = gcp_mocks.FAKE_MONITORING.ActiveServices()
    self.assertIn('compute.googleapis.com', active_services)
    self.assertEqual(active_services['compute.googleapis.com'],
                     gcp_mocks.MOCK_COMPUTE_METRIC)
    self.assertIn('stackdriver.googleapis.com', active_services)
    self.assertEqual(active_services['stackdriver.googleapis.com'],
                     gcp_mocks.MOCK_STACKDRIVER_METRIC)
    self.assertIn('logging.googleapis.com', active_services)
    self.assertEqual(active_services['logging.googleapis.com'],
                     gcp_mocks.MOCK_LOGGING_METRIC)

  @typing.no_type_check
  def testBuildCpuUsageFilter(self):
    """Validates the query filter builder functionality"""
    # pylint: disable=protected-access
    instances_filter = gcp_mocks.FAKE_MONITORING._BuildCpuUsageFilter(
        ['instance-a', 'instance-b'])
    self.assertEqual(
        instances_filter, ('metric.type = "compute.googleapis.com/instance/'
        'cpu/utilization" AND (metric.label.instance_name = "instance-a" OR '
        'metric.label.instance_name = "instance-b")'))

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.monitoring.GoogleCloudMonitoring.GcmApi')
  def testGetCpuUsage(self, mock_gcm_api):
    """Validates the parsing of CPU usage metrics."""
    services = mock_gcm_api.return_value.projects.return_value.timeSeries.return_value.list
    services.return_value.execute.return_value = gcp_mocks.MOCK_GCM_METRICS_CPU
    cpu_usage = gcp_mocks.FAKE_MONITORING.GetCpuUsage()
    self.assertEqual(len(cpu_usage), 2)
    self.assertIn('instance-a_0000000000000000000', cpu_usage)
    self.assertEqual(
        cpu_usage['instance-a_0000000000000000000'],
        [('2021-01-01T00:00:00.000000Z', 0.100000000000000000)] * 24*7)
