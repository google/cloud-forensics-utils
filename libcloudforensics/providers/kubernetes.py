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
"""Kubernetes functionalities."""

import abc
import kubernetes.client


class K8sResource(abc.ABC):
  """Abstract class encompassing Kubernetes resources."""

  @abc.abstractmethod
  def _K8sApi(self) -> kubernetes.client.CoreV1Api:
    """Creates an authenticated Kubernetes API client.

    Returns:
      kubernetes.client.CoreV1Api: An authenticated client to
        the Kubernetes API server.
    """


class K8sSelector:
  """Class to build K8s API selectors."""

  class Component(abc.ABC):
    """Component of the selector."""

    @abc.abstractmethod
    def ToString(self):
      """Returns the component of the selector."""

  class Node(Component):
    """Selector component for running on a particular node."""

    def __init__(self, node) -> None:
      super().__init__()
      self.node = node

    def ToString(self):
      return 'spec.nodeName={0:s}'.format(self.node)

  class Running(Component):
    """Selector component for a running pod."""

    def ToString(self):
      return 'status.phase!=Failed,status.phase!=Succeeded'

  class Workload(Component):
    """Selector specifying which workload."""

    def __init__(self, workload) -> None:
        super().__init__()
        self.workload = workload

    def ToString(self):
        return 'metadata.labels.app={0:s}'.format(self.workload)


  def __init__(self, *selectors):
    self.selectors = selectors

  def ToString(self):
    """Builds the selector string to be passed to the K8s API."""
    return ','.join(map(lambda s: s.ToString(), self.selectors))
