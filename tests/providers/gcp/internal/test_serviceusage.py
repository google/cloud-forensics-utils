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
"""Tests for the gcp module - serviceusage.py"""
import typing
import unittest

import mock

from tests.providers.gcp import gcp_mocks


class GoogleServiceUsageTest(unittest.TestCase):
  """Test Google Service Usage class."""
  # pylint: disable=line-too-long

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.common.ExecuteRequest')
  @mock.patch('libcloudforensics.providers.gcp.internal.serviceusage.GoogleServiceUsage.GsuApi')
  def testGetEnabled(self, mock_gsu_api, mock_execute_request):
    """Validates the GetEnabled function"""
    mock_execute_request.return_value = gcp_mocks.MOCK_ENABLED_SERVICES
    mock_service_usage = mock_gsu_api.return_value.services.return_value
    response = gcp_mocks.FAKE_SERVICE_USAGE.GetEnabled()

    mock_execute_request.assert_called_with(mock_service_usage,
        'list', {'parent': 'projects/fake-project', 'filter': 'state:ENABLED'})

    self.assertListEqual(response, [
        'bigquery.googleapis.com',
        'cloudapis.googleapis.com',
        'compute.googleapis.com'
      ])

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.common.ExecuteRequest')
  @mock.patch('libcloudforensics.providers.gcp.internal.serviceusage.GoogleServiceUsage.GsuApi')
  def testEnableService(self, mock_gsu_api, mock_execute_request):
    """Validates that EnableService calls ExecuteRequest with the correct
    arguments."""
    mock_service_usage = mock_gsu_api.return_value.services.return_value
    mock_execute_request.return_value = [{'name': 'operations/noop.DONE_OPERATION'}]
    gcp_mocks.FAKE_SERVICE_USAGE.EnableService('container.googleapis.com')

    mock_execute_request.assert_called_with(mock_service_usage, 'enable',
        {'name': 'projects/fake-project/services/container.googleapis.com'})

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.common.ExecuteRequest')
  @mock.patch('libcloudforensics.providers.gcp.internal.serviceusage.GoogleServiceUsage.GsuApi')
  def testDisableService(self, mock_gsu_api, mock_execute_request):
    """Validates that DisableService calls ExecuteRequest with the correct
    arguments."""
    mock_service_usage = mock_gsu_api.return_value.services.return_value
    mock_execute_request.return_value = [{'name': 'operations/noop.DONE_OPERATION'}]
    gcp_mocks.FAKE_SERVICE_USAGE.DisableService('container.googleapis.com')

    mock_execute_request.assert_called_with(mock_service_usage, 'disable',
        {'name': 'projects/fake-project/services/container.googleapis.com'})
