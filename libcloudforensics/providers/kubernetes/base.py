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
"""Kubernetes core class structure."""

import abc
from typing import List, TypeVar, Callable, Optional, Dict

from kubernetes import client

from libcloudforensics import logging_utils
from libcloudforensics.providers.kubernetes import container
from libcloudforensics.providers.kubernetes import selector
from libcloudforensics.providers.kubernetes import volume

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)


class K8sClient(metaclass=abc.ABCMeta):
  """Abstract class representing objects that use the Kubernetes API."""

  T = TypeVar('T')

  def __init__(self, api_client: client.ApiClient) -> None:
    """Creates an object holding Kubernetes API client.

    Args:
      api_client (client.ApiClient): The Kubernetes API client to
          the cluster.
    """
    self._api_client = api_client

  def _Api(self, api_class: Callable[[client.ApiClient], T]) -> T:
    """Given an API class, creates an instance with the authenticated client.

    Example usage:
    ```
    nodes = self._Api(CoreV1Api).list_node()
    ```

    Args:
      api_class (Callable[[ApiClient], T]): The API class.

    Returns:
      T: An authenticated instance of the desired API class.
    """
    return api_class(self._api_client)


class K8sResource(K8sClient, metaclass=abc.ABCMeta):
  """Abstract class representing a Kubernetes resource.

  Attributes:
    name (str): The name of this resource.
  """

  def __init__(self, api_client: client.ApiClient, name: str) -> None:
    """Creates a Kubernetes resource holding Kubernetes API client.

    Args:
      api_client (ApiClient): The authenticated Kubernetes API client to
          the cluster.
      name (str): The name of this resource.
    """
    super().__init__(api_client)
    self.name = name

  @abc.abstractmethod
  def Read(self) -> object:
    """Returns the resulting read operation for the resource.

    For example, a Node resource would call CoreV1Api.read_node, a Pod
    resource would call CoreV1Api.read_namespaced_pod. The return values
    of these read calls do not share a base class, hence the object return
    type.

    Returns:
      object: The result of this resource's matching read operation.
    """


class K8sNamespacedResource(K8sResource, metaclass=abc.ABCMeta):
  """Class representing a Kubernetes resource, in a certain namespace.

  Attributes:
    name (str): The name of this resource.
    namespace (str): The Kubernetes namespace in which this resource resides.
  """

  def __init__(
      self, api_client: client.ApiClient, name: str, namespace: str) -> None:
    """Creates a Kubernetes resource in the given namespace.

    Args:
      api_client (ApiClient): The authenticated Kubernetes API client to
          the cluster.
      name (str): The name of this resource.
      namespace (str): The Kubernetes namespace in which this resource
        resides
    """
    super().__init__(api_client, name)
    self.namespace = namespace

  @abc.abstractmethod
  def Delete(self, cascade: bool = True) -> None:
    """Deletes this resource from the Kubernetes cluster.

    For determining how the deletion will cascade, the propagationPolicy
    parameter for Kubernetes API is used.

    https://kubernetes.io/docs/tasks/administer-cluster/use-cascading-deletion/#set-orphan-deletion-policy  # pylint: disable=line-too-long

    Args:
      cascade (bool): Optional. If true, deletion will be propagated to child
          objects. If false, only this resource will be deleted and the child
          objects will be orphaned. Defaults to True.
    """


class K8sNode(K8sResource):
  """Class representing a Kubernetes node."""

  def Read(self) -> client.V1Node:
    """Override of abstract method."""
    api = self._Api(client.CoreV1Api)
    return api.read_node(self.name)

  def Cordon(self) -> None:
    """Cordons the node, making the node unschedulable.

    https://kubernetes.io/docs/concepts/architecture/nodes/#manual-node-administration  # pylint: disable=line-too-long
    """
    api = self._Api(client.CoreV1Api)
    # Create the body as per the API call to PATCH in
    # `kubectl cordon NODE_NAME`
    body = {'spec': {'unschedulable': True}}
    # Cordon the node with the PATCH verb
    api.patch_node(self.name, body)

  def Drain(self, pod_filter: Callable[['K8sPod'], bool]) -> None:
    """Drains all pods from this node that satisfy a filter.

    Args:
      pod_filter (Callable[[K8sPod], bool]): A predicate taking a pod as
          argument. Pods that are on this node and satisfy this predicate will
          be deleted.
    """
    for pod in self.ListPods():
      if pod_filter(pod):
        pod.Delete()

  def ListPods(self, namespace: Optional[str] = None) -> List['K8sPod']:
    """Lists the pods on this node, possibly filtering for a namespace.

    Args:
      namespace (str): Optional. The namespace in which to list the node's pods.

    Returns:
      List[K8sPod]: The list of the node's pods for the namespace, or in all
          namespaces if none is specified.
    """
    api = self._Api(client.CoreV1Api)

    # The pods must be running, and must be on this node. The selectors here
    # are as per the API calls in `kubectl describe node NODE_NAME`.
    running_on_node_selector = selector.K8sSelector(
        selector.K8sSelector.Node(self.name),
        selector.K8sSelector.Running(),
    )

    if namespace is not None:
      pods = api.list_namespaced_pod(
          namespace, **running_on_node_selector.ToKeywords())
    else:
      pods = api.list_pod_for_all_namespaces(
          **running_on_node_selector.ToKeywords())

    return [
        K8sPod(self._api_client, pod.metadata.name, pod.metadata.namespace)
        for pod in pods.items
    ]

  def ExternalIps(self) -> List[str]:
    """Returns the external IPs of this node.

    Returns:
      List[str]: The external IPs found for this node.
    """
    return [
        str(address.address)
        for address in self.Read().status.addresses
        if address.type == 'ExternalIP'
    ]

  def InternalIps(self) -> List[str]:
    """Returns the internal IPs of this node.

    Returns:
      List[str]: The internal IPs found for this node.
    """
    return [
        str(address.address)
        for address in self.Read().status.addresses
        if address.type == 'InternalIP'
    ]


class K8sWorkload(K8sNamespacedResource):
  """Abstract class representing Kubernetes workloads."""

  @abc.abstractmethod
  def GetCoveredPods(self) -> List['K8sPod']:
    """Gets a list of Kubernetes pods covered by this workload.

    Returns:
      List[K8sPod]: A list of pods covered by this workload.
    """

  def GetCoveredNodes(self) -> List[K8sNode]:
    """Gets a list of Kubernetes nodes covered by this workload.

    Returns:
      List[K8sNode]: A list of nodes covered by this workload.
    """
    nodes_by_name = {}  # type: Dict[str, K8sNode]
    for pod in self.GetCoveredPods():
      node = pod.GetNode()
      nodes_by_name[node.name] = node
    return list(nodes_by_name.values())

  @abc.abstractmethod
  def IsCoveringPod(self, pod: 'K8sPod') -> bool:
    """Determines whether a pod is covered by this workload.

    This function checks if this workload's pod match labels are a subset of the
    given pod's labels.

    Args:
      pod (K8sPod): The pod to be checked with the labels of this workload.

    Returns:
      bool: True if the pod is covered this workload, False otherwise.
    """

  @property
  @abc.abstractmethod
  def gcp_protopayload_methodname(self) -> str:
    """The "protoPayload.methodName" substring for this workload."""

  def GcpClusterLogsQuerySupplement(self) -> str:
    """Returns the lines specifying this workload for GCP k8s_cluster logs.

    Returns:
       str: The specifying query string.
    """
    return (
        'protoPayload.resourceName=~"\\b{workload_id:s}$"\n'
        'protoPayload.methodName:"{workload_type:s}."\n'.format(
            workload_id=self.name,
            workload_type=self.gcp_protopayload_methodname,
        ))

  @abc.abstractmethod
  def GcpContainerLogsQuerySupplement(self) -> str:
    """Returns the lines specifying this workload for GCP k8s_container logs.

    Returns:
       str: The specifying query string.
    """

  @abc.abstractmethod
  def OrphanPods(self) -> None:
    """Orphans the pods covered by this workload.

    Note that calling this function will entail the deletion of the object
    upon which this method was called, unless this workload is a pod.
    """


class K8sPod(K8sWorkload):
  """Class representing a Kubernetes pod.

  https://kubernetes.io/docs/concepts/workloads/pods/
  """

  @property
  def gcp_protopayload_methodname(self) -> str:
    """Override of abstract property."""
    return 'pods'

  def GcpContainerLogsQuerySupplement(self) -> str:
    """Override of abstract method."""
    return (
        'resource.labels.namespace_name="{namespace:s}"\n'
        'resource.labels.pod_name="{name:s}"\n'.format(
            namespace=self.namespace, name=self.name))

  def OrphanPods(self) -> None:
    """Override of abstract method."""
    logger.warning('Calling OrphanPods on a Pod has no effect.')

  def GetCoveredPods(self) -> List['K8sPod']:
    """Override of abstract method"""
    return [self]

  def IsCoveringPod(self, pod: 'K8sPod') -> bool:
    """Override of abstract method."""
    return bool(self.Read() == pod.Read())

  def Read(self) -> client.V1Pod:
    """Override of abstract method."""
    api = self._Api(client.CoreV1Api)
    return api.read_namespaced_pod(self.name, self.namespace)

  def GetNode(self) -> K8sNode:
    """Gets the node on which this pod is running.

    Returns:
      K8sNode: The node on which this pod is running.
    """
    return K8sNode(self._api_client, self.Read().spec.node_name)

  def ListContainers(self) -> List[container.K8sContainer]:
    """Lists the containers on this pod.

    Returns:
      List[container.K8sContainer]: The list of containers on this pod.
    """
    return list(map(container.K8sContainer, self.Read().spec.containers))

  def ListVolumes(self) -> List[volume.K8sVolume]:
    """Lists the volumes on this pod.

    Returns:
      List[volume.K8sVolume]: The list of volumes on this pod.
    """
    return list(map(volume.K8sVolume, self.Read().spec.volumes))

  def GetLabels(self) -> Dict[str, str]:
    """Gets the labels in the metadata field of this pod.

    Returns:
      Dict[str, str]: The labels in the metadata field of this pod.
    """
    labels = self.Read().metadata.labels  # type: Dict[str, str]
    return labels

  def Delete(self, cascade: bool = True) -> None:
    """Override of abstract method.

    Args:
      cascade (bool): Ignored here, as a pod's deletion will not cascade
          to any other Kubernetes objects.
    """
    api = self._Api(client.CoreV1Api)
    api.delete_namespaced_pod(self.name, self.namespace)

  def AddLabels(self, labels: Dict[str, str]) -> None:
    """Adds labels to this pod.

    Args:
      labels (Dict[str, str]): The labels to be added to this pod.
    """
    api = self._Api(client.CoreV1Api)
    api.patch_namespaced_pod(
        self.name, self.namespace, body={'metadata': {
            'labels': labels
        }})
