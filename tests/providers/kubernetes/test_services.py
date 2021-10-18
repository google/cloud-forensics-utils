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
"""Tests on Kubernetes service objects."""
import typing
import unittest

import mock
from kubernetes import client

from libcloudforensics.providers.kubernetes import services
from tests.providers.kubernetes import k8s_mocks


class K8sServiceTest(unittest.TestCase):
  """Test the K8sService methods."""

  @typing.no_type_check
  @mock.patch.object(client.CoreV1Api, 'list_namespaced_pod')
  def testListCoveredPods(self, list_namespaced_pod):
    """Test that GetCoveredPods calls API correctly and returns correctly."""
    mock_pods = k8s_mocks.V1PodList(4)
    list_namespaced_pod.return_value = mock_pods
    service = services.K8sService(
        k8s_mocks.MOCK_API_CLIENT, 'service-name', 'service-namespace')
    with mock.patch.object(service, 'Read') as read:
      read.return_value = k8s_mocks.V1Service(selector_labels={'app': 'nginx'})
      self.assertEqual(
        {(pod.metadata.name, pod.metadata.namespace)
         for pod in mock_pods.items},
        {(pod.name, pod.namespace)
         for pod in service.GetCoveredPods()})
    list_namespaced_pod.assert_called_once_with(
        'service-namespace', label_selector='app=nginx')
