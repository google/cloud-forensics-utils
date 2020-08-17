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
"""Tests for aws module - log.py."""

import typing
import unittest
import mock

from tests.providers.aws import aws_mocks


class AWSCloudTrailTest(unittest.TestCase):
  """Test AWS CloudTrail class."""
  # pylint: disable=line-too-long

  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount.ClientApi')
  def testLookupEvents(self, mock_ec2_api):
    """Test that the CloudTrail event are looked up."""
    events = mock_ec2_api.return_value.lookup_events
    events.return_value = aws_mocks.MOCK_EVENT_LIST
    lookup_events = aws_mocks.FAKE_CLOUDTRAIL.LookupEvents()

    self.assertEqual(2, len(lookup_events))
    self.assertEqual(aws_mocks.FAKE_EVENT_LIST[0], lookup_events[0])
