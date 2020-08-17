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
"""Tests for the azure module - resource.py"""

import typing
import unittest
import mock

from tests.providers.azure import azure_mocks


class AZResourceTest(unittest.TestCase):
  """Test Azure monitoring class."""
  # pylint: disable=line-too-long

  @mock.patch('azure.mgmt.resource.subscriptions.v2019_11_01.operations._subscriptions_operations.SubscriptionsOperations.list')
  @typing.no_type_check
  def testListSubscriptionIDs(self, mock_list):
    """Test that subscription IDs are correctly listed"""
    mock_list.return_value = azure_mocks.MOCK_LIST_IDS
    subscription_ids = azure_mocks.FAKE_ACCOUNT.resource.ListSubscriptionIDs()
    self.assertEqual(2, len(subscription_ids))
    self.assertEqual('fake-subscription-id-1', subscription_ids[0])
