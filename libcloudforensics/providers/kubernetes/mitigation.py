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

from libcloudforensics.providers.kubernetes import workloads


def DrainWorkloadNodesFromOtherPods(workload: workloads.K8sWorkload) -> None:
  """Drains a workload's nodes from pods that are not covered.

  Args:
    workload (workloads.K8sWorkload): The workload for which nodes
      must be drained from pods that are not covered by the workload.
  """
  nodes = set(pod.GetNode() for pod in workload.GetCoveredPods())
  for node in nodes:
    node.Cordon()
    node.Drain(lambda p: not workload.IsCoveringPod(p))
