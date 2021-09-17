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
"""Test on netpol Kubernetes objects."""

import typing
import unittest

import mock
from kubernetes import client

from libcloudforensics.providers.kubernetes import netpol
from tests.providers.kubernetes import k8s_mocks


class K8sNetworkPolicyTest(unittest.TestCase):
  """Test Kubernetes NetworkPolicy API calls."""

  mock_spec = mock.Mock()

  @typing.no_type_check
  # Make abstract class instantiation possible and override abstract property
  @mock.patch.object(netpol.K8sNetworkPolicyWithSpec, '__abstractmethods__', set())
  @mock.patch.object(netpol.K8sNetworkPolicyWithSpec, '_spec', mock_spec)
  @mock.patch('kubernetes.client.NetworkingV1Api.create_namespaced_network_policy')
  def testNetworkPolicyCreationNamespace(self, mock_create_func):
    """Test that creating a network policy provides the correct namespace."""
    mock_namespace = mock.Mock()
    network_policy = netpol.K8sNetworkPolicyWithSpec(k8s_mocks.MOCK_API_CLIENT, 'name', mock_namespace)
    network_policy.Create()
    self.assertEqual(mock_create_func.call_args.args[0], mock_namespace)

  @typing.no_type_check
  # Make abstract class instantiation possible and override abstract property
  @mock.patch.object(netpol.K8sNetworkPolicyWithSpec, '__abstractmethods__', set())
  @mock.patch.object(netpol.K8sNetworkPolicyWithSpec, '_spec', mock_spec)
  @mock.patch('kubernetes.client.NetworkingV1Api.create_namespaced_network_policy')
  def testNetworkPolicyCreationSpec(self, mock_create_func):
    """Test that creating a network policy provides the correct spec."""
    network_policy = netpol.K8sNetworkPolicyWithSpec(k8s_mocks.MOCK_API_CLIENT, 'name', 'namespace')
    network_policy.Create()
    self.assertEqual(mock_create_func.call_args.args[1].spec, self.mock_spec)

  @typing.no_type_check
  # Make abstract class instantiation possible and override abstract property
  @mock.patch.object(netpol.K8sNetworkPolicyWithSpec, '__abstractmethods__', set())
  @mock.patch.object(netpol.K8sNetworkPolicyWithSpec, '_spec', mock_spec)
  @mock.patch('kubernetes.client.NetworkingV1Api.create_namespaced_network_policy')
  def testNetworkPolicyCreationMetadata(self, mock_create_func):
    """Test that creating a network policy provides the correct metadata."""
    mock_namespace = 'test-namespace-jsdukbvx'
    mock_name = 'test-name-jsdukbvx'
    network_policy = netpol.K8sNetworkPolicyWithSpec(k8s_mocks.MOCK_API_CLIENT, mock_name, mock_namespace)
    network_policy.Create()
    self.assertEqual(
        mock_create_func.call_args.args[1].metadata,
        client.V1ObjectMeta(name=mock_name, namespace=mock_namespace))

  @typing.no_type_check
  @mock.patch(
      'kubernetes.client.NetworkingV1Api.create_namespaced_network_policy')
  def testIsDenyAllNetworkPolicyCreationSpec(self, mock_create_func):
    """Test that a deny-all network policy creation has deny-all spec."""
    network_policy = netpol.K8sDenyAllNetworkPolicy(
        k8s_mocks.MOCK_API_CLIENT, 'default')
    network_policy.Create()
    # Check that given network policy is a deny-all policy
    provided_spec = mock_create_func.call_args.args[1].spec
    self.assertEqual(provided_spec.policy_types, ['Ingress', 'Egress'])
    self.assertIsNone(provided_spec.ingress)
    self.assertIsNone(provided_spec.egress)

  @typing.no_type_check
  @mock.patch('kubernetes.client.NetworkingV1Api.read_namespaced_network_policy')
  def testNetworkPolicyReadArgs(self, mock_read_func):
    """Test that a NetworkPolicy read is called with the correct args."""
    test_namespace = 'test-namespace-arvvbdxl'
    test_name = 'test-name-arvvbdxl'
    network_policy = netpol.K8sNetworkPolicy(k8s_mocks.MOCK_API_CLIENT, test_name, test_namespace)
    network_policy.Read()
    mock_read_func.assert_called_once_with(test_name, test_namespace)

  @typing.no_type_check
  @mock.patch('kubernetes.client.NetworkingV1Api.delete_namespaced_network_policy')
  def testNetworkPolicyDeleteArgs(self, mock_read_func):
    """Test that a NetworkPolicy read is called with the correct args."""
    test_namespace = 'test-namespace-iyykyqbc'
    test_name = 'test-name-iyykyqbc'
    network_policy = netpol.K8sNetworkPolicy(k8s_mocks.MOCK_API_CLIENT, test_name, test_namespace)
    network_policy.Delete()
    mock_read_func.assert_called_once_with(test_name, test_namespace)
