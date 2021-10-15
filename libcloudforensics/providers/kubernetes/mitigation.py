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
"""Mitigation functions to be used in end-to-end functionality."""
from typing import List, Optional

from libcloudforensics import errors
from libcloudforensics.providers.kubernetes import base
from libcloudforensics.providers.kubernetes import cluster as k8s
from libcloudforensics.providers.kubernetes import netpol


def DrainWorkloadNodesFromOtherPods(
    workload: base.K8sWorkload, cordon: bool = True) -> None:
  """Drains a workload's nodes from non-workload pods.

  Args:
    workload (base.K8sWorkload): The workload for which nodes
        must be drained from pods that are not covered by the workload.
    cordon (bool): Optional. Whether or not to cordon the nodes before draining,
        to prevent pods from appearing on the nodes again as it will be marked
        as unschedulable. Defaults to True.
  """
  nodes = workload.GetCoveredNodes()
  if cordon:
    for node in nodes:
      node.Cordon()
  for node in nodes:
    node.Drain(lambda pod: not workload.IsCoveringPod(pod))


def IsolatePodsWithNetworkPolicy(
    cluster: k8s.K8sCluster,
    pods: List[base.K8sPod]) -> Optional[netpol.K8sDenyAllNetworkPolicy]:
  """Isolates pods via a deny-all NetworkPolicy.

  Args:
    cluster (k8s.K8sCluster): The cluster in which to create the deny-all
        policy.
    pods (List[base.K8sPod]): The pods to patch with the labels of the created
        deny-all NetworkPolicy.

  Returns:
    netpol.K8sDenyAllNetworkPolicy: Optional. The deny-all network policy that
        was created to isolate the pods. If no pods were supplied, None is
        returned.

  Raises:
    ValueError: If the pods are not in the same namespace.
    errors.OperationFailedError: If NetworkPolicy is not enabled in the cluster.
  """
  if not pods:
    return None
  if not cluster.IsNetworkPolicyEnabled():
    raise errors.OperationFailedError(
        'NetworkPolicy is not enabled for the cluster. Creating the deny-all '
        'NetworkPolicy will have no effect.',
        __name__)
  if any(pod.namespace != pods[0].namespace for pod in pods):
    raise ValueError('Supplied pods are not in the same namespace.')
  # First create the NetworkPolicy in the workload's namespace
  deny_all_policy = cluster.DenyAllNetworkPolicy(pods[0].namespace)
  deny_all_policy.Create()
  # Tag the pods covered by the workload with the selecting label of the
  # deny-all NetworkPolicy
  for pod in pods:
    pod.AddLabels(deny_all_policy.labels)
  # For all other policies, specify that they are not selecting the pods
  # that are selected by the deny-all policy
  # TODO: Patch other policies

  return deny_all_policy
