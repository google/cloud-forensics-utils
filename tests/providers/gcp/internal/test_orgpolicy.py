# -*- coding: utf-8 -*-
# Copyright 2024 Google Inc.
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
"""Tests for the gcp module - orgpolicy.py"""

import typing
import unittest
import mock

from tests.providers.gcp import gcp_mocks

from libcloudforensics.providers.gcp.internal import orgpolicy as gcp_orgpolicy

class OrgPolicyTest(unittest.TestCase):
  """Test Google Organisztion Policy class."""
  # pylint: disable=line-too-long

  @typing.no_type_check
  @mock.patch(
      'libcloudforensics.providers.gcp.internal.orgpolicy.GoogleOrgPolicy.OrgPolicyApi'
  )
  def testGetOrgPolicyForProject(self, mock_orgpolicy_api):
    """Test OrgPolicy Get Policy operation."""
    api_get_policy = mock_orgpolicy_api.return_value.projects.return_value.policies
    api_get_policy.return_value.get.return_value.execute.return_value = gcp_mocks.MOCK_ORGPOLICY_PROJECT_POLICY_GET
    policy = 'iam.allowedPolicyMemberDomains'
    result = gcp_mocks.FAKE_ORGPOLICY.getOrgPolicyForProject(policy)
    self.assertIn(policy, result['name'])
    self.assertEqual('CK+jABCDEFGHlQ0=', result['etag'])
    self.assertEqual('CK+jABCDEFGHlQ0=', result['spec']['etag'])

  @typing.no_type_check
  @mock.patch(
      'libcloudforensics.providers.gcp.internal.orgpolicy.GoogleOrgPolicy.OrgPolicyApi'
  )
  def testGetOrgConstraintsForProject(self, mock_orgpolicy_api):
    """Test OrgPolicy Get Org Constraints operation."""
    api_get_policy = mock_orgpolicy_api.return_value.projects.return_value.constraints
    api_get_policy.return_value.list.return_value.execute.return_value = gcp_mocks.MOCK_ORGCONSTRAINTS_LIST
    result = gcp_mocks.FAKE_ORGPOLICY.getOrgConstraintsForProject()
    self.assertEqual(1, len(result))
    self.assertIn('compute.storageResourceUseRestrictions', result[0]['name'])

