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
import abc
from typing import Iterable, Optional, List

from kubernetes import client

from libcloudforensics import logging_utils
from libcloudforensics.providers.kubernetes import base
from libcloudforensics.providers.kubernetes import netpol
from libcloudforensics.providers.kubernetes import services
from libcloudforensics.providers.kubernetes import workloads

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)


class K8sCluster(base.K8sClient, metaclass=abc.ABCMeta):
  """Abstract class representing a Kubernetes cluster."""

  def __init__(self, api_client: client.ApiClient) -> None:
    """Creates a K8sCluster object, checking the API client's authorization.

    This constructor calls an authorization check on the api_client, to see
    whether it is authorized to do all operations on the cluster. The equivalent
    check for kubectl would be `kubectl auth can-i '*' '*' --all-namespaces`.

    Args:
      api_client (client.ApiClient): The API client to the Kubernetes cluster.
    """
    super().__init__(api_client)
    self._AuthorizationCheck()

  def ListPods(self, namespace: Optional[str] = None) -> List[base.K8sPod]:
    """Lists the pods in this cluster.

    Args:
      namespace (str): Optional. The namespace in which to list the pods. If not
          specified, pods are listed in all namespaces.

    Returns:
      List[base.K8sPod]: The list of pods.
    """
    api = self._Api(client.CoreV1Api)
    if namespace is not None:
      pods = api.list_namespaced_pod(namespace)
    else:
      pods = api.list_pod_for_all_namespaces()
    return [
        base.K8sPod(
            self._api_client, pod.metadata.name, pod.metadata.namespace)
        for pod in pods.items
    ]

  def ListDeployments(
      self, namespace: Optional[str] = None) -> List[workloads.K8sDeployment]:
    """Lists the deployments in this cluster.

    Args:
      namespace (str): Optional. The namespace in which to list the deployments.
          If not specified, deployments are listed in all namespaces.

    Returns:
      List[workloads.K8sDeployment]: The list of deployments.
    """
    api = self._Api(client.AppsV1Api)
    if namespace is not None:
      deployments = api.list_namespaced_deployment(namespace)
    else:
      deployments = api.list_deployment_for_all_namespaces()
    return [
        workloads.K8sDeployment(
            self._api_client,
            deployment.metadata.name,
            deployment.metadata.namespace) for deployment in deployments.items
    ]

  def ListReplicaSets(
      self, namespace: Optional[str] = None) -> List[workloads.K8sReplicaSet]:
    """Lists the replica sets in this cluster.

    Args:
      namespace (str): Optional. The namespace in which to list the replica
          sets. If not specified, replica sets are listed in all namespaces.

    Returns:
      List[workloads.K8sReplicaSet]: The list of replica sets.
    """
    api = self._Api(client.AppsV1Api)
    if namespace is not None:
      replica_sets = api.list_namespaced_replica_set(namespace)
    else:
      replica_sets = api.list_replica_set_for_all_namespaces()
    return [
        workloads.K8sReplicaSet(
            self._api_client,
            replica_set.metadata.name,
            replica_set.metadata.namespace)
        for replica_set in replica_sets.items
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
            self._api_client, policy.metadata.name, policy.metadata.namespace)
        for policy in policies.items
    ]

  def ListServices(
      self, namespace: Optional[str] = None) -> List[services.K8sService]:
    """Lists the services in a namespace of this cluster.

    Args:
      namespace: Optional. The namespace in which to list this cluster's
          services. If unspecified, it lists services in all namespaces of this
          cluster.

    Returns:
      The list of services.
    """
    api = self._Api(client.CoreV1Api)
    if namespace is not None:
      services_ = api.list_namespaced_service(namespace)
    else:
      services_ = api.list_service_for_all_namespaces()
    return [
        services.K8sService(
            self._api_client, service.metadata.name, service.metadata.namespace)
        for service in services_.items
    ]

  def _AuthorizationCheck(self) -> None:
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

  def FindNode(self, name: str) -> Optional[base.K8sNode]:
    """Finds a node in this cluster by its name.

    Args:
      name: The node name.

    Returns:
      The cluster node if a node's name corresponds, None otherwise
    """
    for node in self.ListNodes():
      if node.name == name:
        return node
    return None

  def FindService(self, name: str,
                  namespace: str) -> Optional[services.K8sService]:
    """Finds a service in this cluster by its name and namespace.

    Args:
      name: The service name.
      namespace: The service namespace.

    Returns:
      A service in this cluster if its name and namespace corresponds, None
          otherwise.
    """
    for service in self.ListServices():
      if service.name == name and service.namespace == namespace:
        return service
    return None

  def AllWorkloads(self,
                   namespace: Optional[str]) -> Iterable[base.K8sWorkload]:
    """Lists all workloads in this cluster.

    Currently supported workloads are deployments, replica sets and pods, and
    are listed in that order.

    Args:
      namespace (str): The namespace in which to list the workloads. If not
          specified, workloads are listed in all namespaces.

    Returns:
      Iterable[base.K8sWorkload]: An iterator for this cluster's workloads.
    """
    yield from self.ListDeployments(namespace=namespace)
    yield from self.ListReplicaSets(namespace=namespace)
    yield from self.ListPods(namespace=namespace)

  def FindWorkload(self, name: str,
                   namespace: str) -> Optional[base.K8sWorkload]:
    """Finds a workload in this cluster by its name and namespace.

    This method relies on the workloads listed in `self.AllWorkloads`.

    Args:
      name (str): The name of the workload.
      namespace (str): The namespace of the workload.

    Returns:
      base.K8sWorkload: Optional. A workload with the matching name and
          namespace.
    """
    for workload in self.AllWorkloads(namespace=namespace):
      if workload.name == name and workload.namespace == namespace:
        return workload
    return None

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

  def GetService(self, service_id: str, namespace: str) -> services.K8sService:
    """Gets a service in this cluster.

    Args:
      service_id (str): The name of the service.
      namespace (str): The namespace of the service.

    Returns:
      services.K8sService: The matching Kubernetes service.
    """
    return services.K8sService(self._api_client, service_id, namespace)

  def GetNode(self, node_name: str) -> base.K8sNode:
    """Gets a node object in this cluster.

    Args:
      node_name (str): The name of the node.

    Returns:
      base.K8sNode: The matching node object.
    """
    return base.K8sNode(self._api_client, node_name)

  def GetPod(self, pod_name: str, namespace: str) -> base.K8sPod:
    """Gets a pod object in this cluster.

    Args:
      pod_name (str): The name of the pod.
      namespace (str): The namespace of the pod.

    Returns:
      base.K8sPod: The matching pod object.
    """
    return base.K8sPod(self._api_client, pod_name, namespace)

  def GetReplicaSet(
      self, replica_set_name: str, namespace: str) -> workloads.K8sReplicaSet:
    """Gets a replica set object in this cluster.

    Args:
      replica_set_name (str): The name of the replica set.
      namespace (str): The namespace of the replica set.

    Returns:
      workloads.K8sReplicaSet: The matching replica set object.
    """
    return workloads.K8sReplicaSet(
        self._api_client, replica_set_name, namespace)

  def TargetedDenyAllNetworkPolicy(
      self, namespace: str) -> netpol.K8sTargetedDenyAllNetworkPolicy:
    """Gets a deny-all network policy for the cluster.

    Note that the returned policy is not created when using this method. It can
    be created by calling the creation method on the object.

    Args:
      namespace (str): The namespace for the returned network policy.

    Returns:
      netpol.K8sTargetedDenyAllNetworkPolicy: The matching network policy
          object. Call the creation method on the object to create the policy.
    """
    return netpol.K8sTargetedDenyAllNetworkPolicy(self._api_client, namespace)

  @abc.abstractmethod
  def IsNetworkPolicyEnabled(self) -> bool:
    """Returns whether network policies are enabled.

    Returns:
      bool: True if network policies are enabled, False otherwise.
    """
