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
"""Tests for aws module - common.py."""

import typing
import unittest

from libcloudforensics.providers.aws.internal import common


class AWSCommonTest(unittest.TestCase):
  """Test the common.py public methods"""

  @typing.no_type_check
  def testCreateTags(self):
    """Test that tag specifications are correclty created"""
    tag_specifications = common.CreateTags(common.VOLUME, {'Name': 'fake-name'})
    self.assertEqual('volume', tag_specifications['ResourceType'])
    self.assertEqual(1, len(tag_specifications['Tags']))
    self.assertEqual('Name', tag_specifications['Tags'][0]['Key'])
    self.assertEqual('fake-name', tag_specifications['Tags'][0]['Value'])

    tag_specifications = common.CreateTags(
        common.VOLUME, {'Name': 'fake-name', 'FakeTag': 'fake-tag'})
    self.assertEqual(2, len(tag_specifications['Tags']))
    self.assertEqual('FakeTag', tag_specifications['Tags'][1]['Key'])
    self.assertEqual('fake-tag', tag_specifications['Tags'][1]['Value'])

  @typing.no_type_check
  def testGetInstanceTypeByCPU(self):
    """Test that the instance type matches the requested amount of CPU cores."""
    self.assertEqual('m4.large', common.GetInstanceTypeByCPU(2))
    self.assertEqual('m4.16xlarge', common.GetInstanceTypeByCPU(64))
    with self.assertRaises(ValueError):
      common.GetInstanceTypeByCPU(0)
    with self.assertRaises(ValueError):
      common.GetInstanceTypeByCPU(256)
