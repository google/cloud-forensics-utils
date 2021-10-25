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
from libcloudforensics import logging_utils
from libcloudforensics import prompts
from libcloudforensics.providers.kubernetes import base
from libcloudforensics.providers.kubernetes import cluster as k8s
from libcloudforensics.providers.kubernetes import netpol

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)


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
    pods: List[base.K8sPod],
    existing_policies_prompt: bool = False
) -> Optional[netpol.K8sTargetedDenyAllNetworkPolicy]:
  """Isolates pods via a deny-all NetworkPolicy.

  Args:
    cluster (k8s.K8sCluster): The cluster in which to create the deny-all
        policy.
    pods (List[base.K8sPod]): The pods to patch with the labels of the created
        deny-all NetworkPolicy.
    existing_policies_prompt (bool): Optional. If True, the user will be
        prompted with options to patch, delete or leave the existing network
        policies. Defaults to False.

  Returns:
    netpol.K8sTargetedDenyAllNetworkPolicy: Optional. The deny-all network
        policy that was created to isolate the pods. If no pods were supplied,
        None is returned.

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

  namespace = pods[0].namespace
  if any(pod.namespace != namespace for pod in pods):
    raise ValueError('Supplied pods are not in the same namespace.')

  # Keep in mind that this does not create the network policy in the cluster,
  # it just creates the K8sNetworkPolicy object
  deny_all_policy = cluster.TargetedDenyAllNetworkPolicy(namespace)

  # If other network policies exist, they need to be handled, otherwise the
  # deny-all NetworkPolicy may have no effect. There are a two options to do
  # this, either patching the network policies or deleting them.
  existing_policies = cluster.ListNetworkPolicies(namespace=namespace)

  def PatchExistingNetworkPolicies() -> None:
    for policy in existing_policies:
      policy.Patch(not_match_labels=deny_all_policy.labels)

  def DeleteExistingNetworkPolicies() -> None:
    for policy in existing_policies:
      policy.Delete()

  if existing_policies and existing_policies_prompt:
    logger.warning('There are existing NetworkPolicy objects.')
    prompt_sequence = prompts.PromptSequence(
        prompts.MultiPrompt(
            options=[
                prompts.PromptOption(
                    'Delete existing NetworkPolicy objects in same namespace',
                    DeleteExistingNetworkPolicies),
                prompts.PromptOption(
                    'Patch existing NetworkPolicy objects in same namespace',
                    PatchExistingNetworkPolicies),
                prompts.PromptOption('Leave existing NetworkPolicy objects')
            ]))
    prompt_sequence.Run()

  # Tag the pods covered by the workload with the selecting label of the
  # deny-all NetworkPolicy
  for pod in pods:
    pod.AddLabels(deny_all_policy.labels)

  deny_all_policy.Create()

  return deny_all_policy
