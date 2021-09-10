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
"""Kubernetes mock response objects, used for testing."""
from unittest import mock

MOCK_API_CLIENT = mock.Mock()


def MakeMockNodes(amount: int) -> mock.Mock:
  """Make mock Kubernetes API response node list, see V1NodeList."""
  mock_nodes = mock.Mock()
  mock_nodes.items = []
  for i in range(amount):
    name = 'fake-node-{0:d}'.format(i)
    mock_nodes.items.append(MakeMockNode(name))
  return mock_nodes


def MakeMockNode(name: str) -> mock.Mock:
  """Make mock Kubernetes API response node, see V1Node."""
  mock_node = mock.Mock()
  mock_node.metadata.name = name
  return mock_node


def MakeMockPod(name: str, namespace: str, node_name: str) -> mock.Mock:
  """Make mock Kubernetes API response pod, see V1Pod."""
  mock_pod = mock.Mock()
  mock_pod.metadata.name = name
  mock_pod.metadata.namespace = namespace
  mock_pod.spec.node_name = node_name
  return mock_pod
