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
"""Kubernetes workload classes extending the base hierarchy."""

import abc
from typing import List, Dict

from kubernetes.client import (
  AppsV1Api,
  CoreV1Api,
  # Types
  V1Deployment,
)

from libcloudforensics.providers.kubernetes.base import (
  K8sNamespacedResource,
  K8sPod,
)
from libcloudforensics.providers.kubernetes.selector import K8sSelector


class K8sWorkload(K8sNamespacedResource, metaclass=abc.ABCMeta):
  """Abstract class representing Kubernetes workloads.

  A Kubernetes workload could be a ReplicaSet, a Deployment, a StatefulSet.
  """

  @abc.abstractmethod
  def GetCoveredPods(self) -> List[K8sPod]:
    """Gets a list of Kubernetes pods covered by this workload.

    Returns:
      List[K8sPod]: A list of pods covered by this workload.
    """


class K8sDeployment(K8sWorkload):
  """Class representing a Kubernetes deployment."""

  def Read(self) -> V1Deployment:
    api = self._Api(AppsV1Api)
    return api.read_namespaced_deployment(self.name, self.namespace)

  def MatchLabels(self) -> Dict[str, str]:
    """Gets the labels that will be on the pods of this workload.

    Returns:
      Dict[str, str]: The labels that will be on the pods of this workload.
    """
    read = self.Read()
    if read.spec.selector.match_expressions is not None:
      raise NotImplementedError('matchExpressions exist, meaning pods matching '
                                'matchLabels will be inaccurate.')
    match_labels: Dict[str, str] = read.spec.selector.match_labels
    return match_labels

  def GetCoveredPods(self) -> List[K8sPod]:
    api = self._Api(CoreV1Api)

    # Get the labels for this workload, and create a selector
    selector = K8sSelector.FromLabelsDict(self.MatchLabels())

    # Extract the pods
    pods = api.list_namespaced_pod(
      self.namespace,
      **selector.ToKeywords()
    )

    # Convert to pod objects
    return [K8sPod(self._api_client, pod.metadata.name, pod.metadata.namespace)
            for pod in pods.items]
