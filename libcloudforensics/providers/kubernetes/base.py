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
"""Kubernetes core class structure."""

import abc
from typing import List, TypeVar, Callable, Optional

from kubernetes.client import (
  ApiClient,
  # APIs
  CoreV1Api,
  AppsV1Api,
  # Types
  V1Pod,
)

from libcloudforensics.providers.kubernetes.selector import K8sSelector


class K8sClient(metaclass=abc.ABCMeta):
  """Abstract class representing objects that use the Kubernetes API."""

  T = TypeVar('T')

  def __init__(self, api_client: ApiClient):
    """Creates an object holding Kubernetes API client.

    Args:
      api_client (ApiClient): The authenticated Kubernetes API client to
       the cluster.
    """
    self._api_client = api_client

  def _Api(self, api: Callable[[ApiClient], T]) -> T:
    return api(self._api_client)


class K8sResource(K8sClient, metaclass=abc.ABCMeta):
  """Abstract class representing a Kubernetes resource."""

  def __init__(self, api_client: ApiClient, name: str):
    """Creates a Kubernetes resource holding Kubernetes API client.

    Args:
      api_client (ApiClient): The authenticated Kubernetes API client to
       the cluster.
      name (str): The name of this resource.
    """
    super(K8sResource, self).__init__(api_client)
    self.name = name

  @abc.abstractmethod
  def Read(self) -> object:
    """Returns the resulting read operation for the resource.

    For example, a Node resource would call CoreV1Api.read_node, a Pod
    resource would call CoreV1Api.read_namespaced_pod. The return values
    of these read calls do not share a base class, hence the object return
    type.
    """


class K8sCluster(K8sClient):
  """Class representing a Kubernetes cluster."""

  def ListPods(self, namespace: Optional[str]) -> List['K8sPod']:
    """"""
    api = self._Api(CoreV1Api)

    # Collect pods
    if namespace is not None:
      pods = api.list_namespaced_pod(namespace)
    else:
      pods = api.list_pod_for_all_namespaces()

    # Convert to node objects
    return [K8sPod(self._api_client, pod.metadata.name, pod.metadata.namespace)
            for pod in pods.items]


class K8sNamespacedResource(K8sResource, metaclass=abc.ABCMeta):
  """Class representing a Kubernetes resource, in a certain namespace."""

  def __init__(self, api_client: ApiClient, name: str, namespace: str):
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

  def Read(self):
    api = self._Api(CoreV1Api)
    return api.read_node(self.name)

  def Cordon(self):
    """Cordons the node, making the node unschedulable.

    https://kubernetes.io/docs/concepts/architecture/nodes/#manual-node-administration  # pylint: disable=line-too-long
    """
    api = self._Api(CoreV1Api)
    # Create the body as per the API call to PATCH in
    # `kubectl cordon NODE_NAME`
    body = {
      'spec': {
        'unschedulable': True
      }
    }
    # Cordon the node with the PATCH verb
    api.patch_node(self.name, body)

  def ListPods(self, namespace: Optional[str]):
    api = self._Api(CoreV1Api)

    # The pods must be running, and must be on this node,
    # the selectors here are as per the API calls in `kubectl
    # describe node NODE_NAME`
    selector = K8sSelector(
      K8sSelector.Node(self.name),
      K8sSelector.Running(),
    )

    if namespace is not None:
      pods = api.list_namespaced_pod(
        namespace,
        **selector.ToKeywords()
      )
    else:
      pods = api.list_pod_for_all_namespaces(
        **selector.ToKeywords()
      )

    return [K8sPod(self._api_client, pod.metadata.name, pod.metadata.namespace)
            for pod in pods.items]


class K8sPod(K8sNamespacedResource):

  def Read(self) -> V1Pod:
    api = self._Api(CoreV1Api)
    return api.read_namespaced_pod(self.name, self.namespace)

  def GetNode(self) -> K8sNode:
    return K8sNode(self._api_client, self.Read().spec.node_name)
