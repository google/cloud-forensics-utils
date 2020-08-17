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
"""Tests for the gcp module - common.py"""

import typing
import unittest

from libcloudforensics import errors
from libcloudforensics.providers.gcp.internal import common

from tests.providers.gcp import gcp_mocks


class GCPCommonTest(unittest.TestCase):
  """Test forensics.py methods and common.py helper methods."""
  # pylint: disable=line-too-long

  @typing.no_type_check
  def testGenerateDiskName(self):
    """Test that the generated disk name is always within GCP boundaries.

    The disk name must comply with the following RegEx:
      - ^(?=.{1,63}$)[a-z]([-a-z0-9]*[a-z0-9])?$

    i.e., it must be between 1 and 63 chars, the first character must be a
    lowercase letter, and all following characters must be a dash, lowercase
    letter, or digit, except the last character, which cannot be a dash.
    """

    disk_name = common.GenerateDiskName(gcp_mocks.FAKE_SNAPSHOT)
    self.assertEqual('fake-snapshot-857c0b16-copy', disk_name)
    self.assertTrue(gcp_mocks.REGEX_DISK_NAME.match(disk_name))

    disk_name = common.GenerateDiskName(gcp_mocks.FAKE_SNAPSHOT_LONG_NAME)
    self.assertEqual(
        'this-is-a-kind-of-long-fake-snapshot-name-and-is--857c0b16-copy',
        disk_name)
    self.assertTrue(gcp_mocks.REGEX_DISK_NAME.match(disk_name))

    disk_name = common.GenerateDiskName(
        gcp_mocks.FAKE_SNAPSHOT, disk_name_prefix='some-not-so-long-disk-name-prefix')
    self.assertEqual(
        'some-not-so-long-disk-name-prefix-fake-snapshot-857c0b16-copy',
        disk_name)
    self.assertTrue(gcp_mocks.REGEX_DISK_NAME.match(disk_name))

    disk_name = common.GenerateDiskName(
        gcp_mocks.FAKE_SNAPSHOT_LONG_NAME,
        disk_name_prefix='some-not-so-long-disk-name-prefix')
    self.assertEqual(
        'some-not-so-long-disk-name-prefix-this-is-a-kind--857c0b16-copy',
        disk_name)
    self.assertTrue(gcp_mocks.REGEX_DISK_NAME.match(disk_name))

    disk_name = common.GenerateDiskName(
        gcp_mocks.FAKE_SNAPSHOT,
        disk_name_prefix='some-really-really-really-really-really-really-long'
        '-disk-name-prefix')
    self.assertEqual(
        'some-really-really-really-really-really-really-lo-857c0b16-copy',
        disk_name)
    self.assertTrue(gcp_mocks.REGEX_DISK_NAME.match(disk_name))

    disk_name = common.GenerateDiskName(
        gcp_mocks.FAKE_SNAPSHOT_LONG_NAME,
        disk_name_prefix='some-really-really-really-really-really-really-long'
        '-disk-name-prefix')
    self.assertEqual(
        'some-really-really-really-really-really-really-lo-857c0b16-copy',
        disk_name)
    self.assertTrue(gcp_mocks.REGEX_DISK_NAME.match(disk_name))

    # Disk prefix cannot start with a capital letter
    with self.assertRaises(errors.InvalidNameError):
      common.GenerateDiskName(
          gcp_mocks.FAKE_SNAPSHOT, 'Some-prefix-that-starts-with-a-capital-letter')
