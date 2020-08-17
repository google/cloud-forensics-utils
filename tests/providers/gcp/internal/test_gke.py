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


class GoogleKubernetesEngineTest(unittest.TestCase):
  """Test Google Kubernetes Engine class."""

  FAKE_GKE = gke.GoogleKubernetesEngine()
  MOCK_GKE_CLUSTER_OBJECT = {
      "name": "test-cluster",
      "location": "fake-region"
  }

  # pylint: disable=line-too-long
  @typing.no_type_check
  @mock.patch('libcloudforensics.providers.gcp.internal.gke.GoogleKubernetesEngine.GkeApi')
  def testGetCluster(self, mock_gke_api):
    """Test GKE cluster Get operation."""
    cluster_mock = GoogleKubernetesEngineTest.MOCK_GKE_CLUSTER_OBJECT
    fake_gke = GoogleKubernetesEngineTest.FAKE_GKE
    api_cluster_object = mock_gke_api.return_value.projects.return_value.locations.return_value.clusters.return_value
    api_cluster_object.get.return_value.execute.return_value = cluster_mock
    get_results = fake_gke.GetCluster(
        'projects/fake-project/locations/fake-region/clusters/fake-cluster')
    self.assertEqual(cluster_mock, get_results)
