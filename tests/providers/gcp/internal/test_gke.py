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
"""Tests for the gcp module - gke.py"""

import typing
import unittest
import mock

from libcloudforensics.providers.gcp.internal import gke
import libcloudforensics.providers.kubernetes.cluster as k8s


class GoogleKubernetesEngineTest(unittest.TestCase):
  """Test Google Kubernetes Engine class."""


  @typing.no_type_check
  # The next two decorators enable GkeCluster to be instantiated
  @mock.patch.object(k8s.K8sCluster, '_AuthorizationCheck', mock.Mock)
  @mock.patch.object(gke.GkeCluster, '_GetK8sApiClient', mock.Mock)
  @mock.patch.object(gke.GoogleKubernetesEngine, 'GkeApi')
  def testGetCluster(self, mock_gke_api):
    """Test GkeCluster calls the API correctly and returns its response."""
    clusters_api = mock_gke_api().projects().locations().clusters()
    clusters_api.get.return_value.execute.return_value = {
      'key': 'ddbjnaxz'
    }

    cluster = gke.GkeCluster('fake-project-id', 'fake-zone', 'fake-cluster-id')
    get_operation_result = cluster.GetOperation()

    clusters_api.get.assert_called_once_with(name=cluster.name)
    self.assertEqual({'key': 'ddbjnaxz'}, get_operation_result)
