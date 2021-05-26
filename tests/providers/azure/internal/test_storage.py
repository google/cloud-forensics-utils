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
"""Tests for the azure module - storage.py"""

import typing
import unittest
import mock

from libcloudforensics import errors
from tests.providers.azure import azure_mocks


class AZStorageTest(unittest.TestCase):
  """Test Azure storage class."""
  # pylint: disable=line-too-long

  @mock.patch('azure.mgmt.storage.v2021_04_01.operations._storage_accounts_operations.StorageAccountsOperations.list_keys')
  @mock.patch('azure.mgmt.storage.v2021_04_01.operations._storage_accounts_operations.StorageAccountsOperations.begin_create')
  @typing.no_type_check
  def testCreateStorageAccount(self, mock_create, mock_list_keys):
    """Test that a storage account is created and its information retrieved"""
    # pylint: disable=protected-access
    mock_create.return_value.result.return_value = azure_mocks.MOCK_STORAGE_ACCOUNT
    mock_list_keys.return_value = azure_mocks.MOCK_LIST_KEYS
    account_id, account_key = azure_mocks.FAKE_ACCOUNT.storage.CreateStorageAccount(
        'fakename')
    self.assertEqual('fakestorageid', account_id)
    self.assertEqual('fake-key-value', account_key)

    with self.assertRaises(errors.InvalidNameError) as error:
      _, _ = azure_mocks.FAKE_ACCOUNT.storage.CreateStorageAccount(
          'fake-non-conform-name')
    # pylint: enable=protected-access
    self.assertEqual('Storage account name fake-non-conform-name does not '
                     'comply with ^[a-z0-9]{1,24}$', str(error.exception))
