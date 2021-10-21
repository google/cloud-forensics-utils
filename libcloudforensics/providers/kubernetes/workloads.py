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
"""Kubernetes workload classes extending the base hierarchy."""

import abc
from typing import List, Dict, Union

from kubernetes import client

from libcloudforensics import errors
from libcloudforensics.providers.kubernetes import base
from libcloudforensics.providers.kubernetes import selector


class K8sControlledWorkload(base.K8sWorkload):
  """Abstract class representing workloads covering pods with via a selector.

  Examples: ReplicaSet, Deployment, StatefulSet.
  """

  def GcpContainerLogsQuerySupplement(self) -> str:
    """Override of abstract method."""
    queries = [
        'resource.labels.namespace_name="{namespace:s}"'.format(
            namespace=self.namespace)
    ]
    queries.extend(
        'labels.k8s-pod/{key:s}="{value:s}"'.format(key=key, value=value)
        for key, value in self.MatchLabels().items())
    return '\n'.join(queries)

  @abc.abstractmethod
  def _PodMatchLabels(self) -> Dict[str, str]:
    """Gets the key-value pairs that pods belonging to this workload would have.

    Returns:
      Dict[str, str]: The label key-value pairs of this workload's pods.
    """

  @abc.abstractmethod
  def Read(self) -> Union[client.V1Deployment, client.V1ReplicaSet,]:
    """Override of abstract method."""  # Narrows down type hint

  def MatchLabels(self) -> Dict[str, str]:
    """Gets the label key-value pairs in the matchLabels field.

    Returns:
      Dict[str, str]: The labels in the matchLabels field.

    Raises:
      NotImplementedError: If matchExpressions exist, in which case using the
          matchLabels will be inaccurate.
    """
    read = self.Read()

    if read.spec.selector.match_expressions:
      raise NotImplementedError(
          'matchExpressions exist, meaning using '
          'matchLabels will be inaccurate.')

    match_labels = read.spec.selector.match_labels  # type: Dict[str, str]
    return match_labels

  def GetCoveredPods(self) -> List[base.K8sPod]:
    """Override of abstract method."""
    api = self._Api(client.CoreV1Api)

    labels_selector = selector.K8sSelector.FromLabelsDict(
        self._PodMatchLabels())

    pods = api.list_namespaced_pod(
        self.namespace, **labels_selector.ToKeywords())

    return [
        base.K8sPod(
            self._api_client, pod.metadata.name, pod.metadata.namespace)
        for pod in pods.items
    ]

  def IsCoveringPod(self, pod: base.K8sPod) -> bool:
    """Override of abstract method."""
    # Since labels are type Dict[str, str], we can use set-like operations
    # on the items of the dict
    return (
        self.namespace == pod.namespace and
        self._PodMatchLabels().items() <= pod.GetLabels().items())


class K8sDeployment(K8sControlledWorkload):
  """Class representing a Kubernetes deployment."""

  @property
  def gcp_protopayload_methodname(self) -> str:
    """Override of abstract property."""
    return 'deployments'

  def OrphanPods(self) -> None:
    """Override of abstract method.

    To achieve the goal of orphaning the pods, this deployment and its matching
    ReplicaSet are deleted, without cascading.
    """
    rs = self._ReplicaSet()
    self.Delete(cascade=False)
    rs.Delete(cascade=False)

  def Delete(self, cascade: bool = True) -> None:
    """Override of abstract method."""
    api = self._Api(client.AppsV1Api)
    if cascade:
      api.delete_namespaced_deployment(self.name, self.namespace)
    else:
      api.delete_namespaced_deployment(
          self.name, self.namespace, body={'propagationPolicy': 'Orphan'})

  def Read(self) -> client.V1Deployment:
    """Override of abstract method."""
    api = self._Api(client.AppsV1Api)
    return api.read_namespaced_deployment(self.name, self.namespace)

  def _ReplicaSet(self) -> 'K8sReplicaSet':
    """Gets the matching ReplicaSet of this deployment.

    Returns:
      K8sReplicaSet: The matching ReplicaSet of this deployment.

    Raises:
      errors.ResourceNotFoundError: If the matching ReplicaSet was not found.
    """

    # The matching ReplicaSet will have labels corresponding to this
    # deployment's matchLabels.
    replica_sets_selector = selector.K8sSelector.FromLabelsDict(
        self.MatchLabels())

    replica_sets = self._Api(client.AppsV1Api).list_namespaced_replica_set(
        self.namespace, **replica_sets_selector.ToKeywords()).items

    this_template_spec = self.Read().spec.template
    for replica_set in replica_sets:
      rs_template_spec = replica_set.spec.template
      # Delete the hash appended to the labels of this replicaset, so that
      # the following comparison does not factor in the hash label
      if 'pod-template-hash' in rs_template_spec.metadata.labels:
        del rs_template_spec.metadata.labels['pod-template-hash']
        if rs_template_spec == this_template_spec:
          return K8sReplicaSet(
              self._api_client,
              replica_set.metadata.name,
              replica_set.metadata.namespace,
          )

    raise errors.ResourceNotFoundError(
        'Matching ReplicaSet for deployment {0:s} not found.'.format(self.name),
        __name__)

  def _PodMatchLabels(self) -> Dict[str, str]:
    """Override of abstract method."""
    return self._ReplicaSet().MatchLabels()


class K8sReplicaSet(K8sControlledWorkload):
  """Class representing a Kubernetes deployment."""

  @property
  def gcp_protopayload_methodname(self) -> str:
    """Override of abstract property."""
    return 'replicasets'

  def OrphanPods(self) -> None:
    """Override of abstract method."""
    self.Delete(cascade=False)

  def Delete(self, cascade: bool = True) -> None:
    """Override of abstract method."""
    api = self._Api(client.AppsV1Api)
    if cascade:
      api.delete_namespaced_replica_set(self.name, self.namespace)
    else:
      api.delete_namespaced_replica_set(
          self.name, self.namespace, body={'propagationPolicy': 'Orphan'})

  def _PodMatchLabels(self) -> Dict[str, str]:
    """Override of abstract method."""
    return self.MatchLabels()

  def Read(self) -> client.V1Deployment:
    """Override of abstract method."""
    api = self._Api(client.AppsV1Api)
    return api.read_namespaced_replica_set(self.name, self.namespace)
