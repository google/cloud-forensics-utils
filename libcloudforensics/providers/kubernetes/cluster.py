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
"""Kubernetes cluster class, starting point for Kubernetes API calls."""
from typing import Optional, List

from kubernetes import client

from libcloudforensics import logging_utils
from libcloudforensics.providers.kubernetes import base
from libcloudforensics.providers.kubernetes import netpol
from libcloudforensics.providers.kubernetes import workloads

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)


class K8sCluster(base.K8sClient):
  """Class representing a Kubernetes cluster."""

  def __init__(self, api_client: client.ApiClient) -> None:
    """Creates a K8sCluster object, checking the API client's authorization.

    This constructor calls an authorization check on the api_client, to see
    whether it is authorized to do all operations on the cluster. The equivalent
    check for kubectl would be `kubectl auth can-i '*' '*' --all-namespaces`.

    Args:
      api_client (client.ApiClient): The API client to the Kubernetes cluster.
    """
    super().__init__(api_client)
    self.__AuthorizationCheck()

  def ListPods(self, namespace: Optional[str] = None) -> List[base.K8sPod]:
    """Lists the pods of this cluster, possibly filtering for a namespace.

    Args:
      namespace (str): Optional. The namespace in which to list the pods.

    Returns:
      List[base.K8sPod]: The list of pods for the namespace, or in all
          namespaces if none is specified.
    """
    api = self._Api(client.CoreV1Api)

    # Collect pods
    if namespace is not None:
      pods = api.list_namespaced_pod(namespace)
    else:
      pods = api.list_pod_for_all_namespaces()

    # Convert to node objects
    return [
        base.K8sPod(
            self._api_client, pod.metadata.name, pod.metadata.namespace)
        for pod in pods.items
    ]

  def ListNodes(self) -> List[base.K8sNode]:
    """Lists the nodes of this cluster.

    Returns:
      List[base.K8sNode]: The list of nodes in this cluster.
    """
    api = self._Api(client.CoreV1Api)

    # Collect pods
    nodes = api.list_node()

    # Convert to node objects
    return [
        base.K8sNode(self._api_client, node.metadata.name)
        for node in nodes.items
    ]

  def ListNetworkPolicies(
      self, namespace: Optional[str] = None) -> List[netpol.K8sNetworkPolicy]:
    """List the network policies in a namespace of this cluster.

    Args:
      namespace (str): Optional. The namespace in which to list network
          policies. If unspecified, it returns network policies in all
          namespaces of this cluster.

    Returns:
      List[netpol.K8sNetworkPolicy]: The list of network policies.
    """
    api = self._Api(client.NetworkingV1Api)
    if namespace is not None:
      policies = api.list_namespaced_network_policy(namespace)
    else:
      policies = api.list_network_policy_for_all_namespaces()
    return [
        netpol.K8sNetworkPolicy(
            self._api_client, policy.name, policy.namespace)
        for policy in policies
    ]

  def __AuthorizationCheck(self) -> None:
    """Checks the authorization of this cluster's API client.

    Performs a check as per `kubectl auth can-i '*' '*' --all-namespaces`,
    logging a warning if the check did not return 'yes'.
    """
    api = self._Api(client.AuthorizationV1Api)
    response = api.create_self_subject_access_review(
        # Body from `kubectl auth can-i '*' '*' --all-namespaces`
        {'spec': {
            'resourceAttributes': {
                'verb': '*', 'resource': '*'
            }
        }})
    if not response.status.allowed:
      logger.warning(
          'This object\'s client is not authorized to perform all operations'
          'on the Kubernetes cluster. API calls may fail.')

  def GetDeployment(
      self, workload_id: str, namespace: str) -> workloads.K8sDeployment:
    """Gets a deployment from the cluster.

    Args:
      workload_id (str): The name of the deployment.
      namespace (str): The namespace of the deployment.

    Returns:
      workloads.K8sDeployment: The matching Kubernetes deployment.
    """
    return workloads.K8sDeployment(self._api_client, workload_id, namespace)

  def DenyAllNetworkPolicy(
      self, namespace: str) -> netpol.K8sDenyAllNetworkPolicy:
    """Gets a deny-all network policy for the cluster.

    Note that the returned policy is not created when using this method. It can
    be created by calling the creation method on the object.

    Args:
      namespace (str): The namespace for the returned network policy.

    Returns:
      netpol.K8sDenyAllNetworkPolicy: The matching network policy object. Call
          the creation method on the object to create the policy.
    """
    return netpol.K8sDenyAllNetworkPolicy(self._api_client, namespace)
