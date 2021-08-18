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
from typing import List, TypeVar, Callable, Optional

from kubernetes import client

from libcloudforensics.providers.kubernetes import selector


class K8sClient(metaclass=abc.ABCMeta):
  """Abstract class representing objects that use the Kubernetes API."""

  T = TypeVar('T')

  def __init__(self, api_client: client.ApiClient) -> None:
    """Creates an object holding Kubernetes API client.

    Args:
      api_client (client.ApiClient): The authenticated Kubernetes API client to
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


class K8sCluster(K8sClient):
  """Class representing a Kubernetes cluster."""

  def ListPods(self, namespace: Optional[str] = None) -> List['K8sPod']:
    """Lists the pods of this cluster, possibly filtering for a namespace.

    Args:
      namespace (str): Optional. The namespace in which to list the pods.

    Returns:
      List[K8sPod]: The list of pods for the namespace, or in all namespaces
        if none is specified.
    """
    api = self._Api(client.CoreV1Api)

    # Collect pods
    if namespace is not None:
      pods = api.list_namespaced_pod(namespace)
    else:
      pods = api.list_pod_for_all_namespaces()

    # Convert to node objects
    return [K8sPod(self._api_client, pod.metadata.name, pod.metadata.namespace)
            for pod in pods.items]

  def ListNodes(self) -> List['K8sNode']:
    """Lists the nodes of this cluster.

    Returns:
      List[K8sNode]: The list of nodes in this cluster.
    """
    api = self._Api(client.CoreV1Api)

    # Collect pods
    nodes = api.list_node()

    # Convert to node objects
    return [K8sNode(self._api_client, node.metadata.name)
            for node in nodes.items]


class K8sNamespacedResource(K8sResource, metaclass=abc.ABCMeta):
  """Class representing a Kubernetes resource, in a certain namespace.

  Attributes:
    name (str): The name of this resource.
    namespace (str): The Kubernetes namespace in which this resource resides.
  """

  def __init__(self, api_client: client.ApiClient, name: str,
               namespace: str) -> None:
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
    body = {
      'spec': {
        'unschedulable': True
      }
    }
    # Cordon the node with the PATCH verb
    api.patch_node(self.name, body)

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
        namespace,
        **running_on_node_selector.ToKeywords()
      )
    else:
      pods = api.list_pod_for_all_namespaces(
        **running_on_node_selector.ToKeywords()
      )

    return [K8sPod(self._api_client, pod.metadata.name, pod.metadata.namespace)
            for pod in pods.items]


class K8sPod(K8sNamespacedResource):
  """Class representing a Kubernetes pod.

  https://kubernetes.io/docs/concepts/workloads/pods/
  """

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
