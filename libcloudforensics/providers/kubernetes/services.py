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
"""Kubernetes service classes extending the base hierarchy."""
from typing import Dict, List, Optional

from kubernetes import client

from libcloudforensics.providers.kubernetes import base
from libcloudforensics.providers.kubernetes import selector


class K8sService(base.K8sNamespacedResource):
  """Class representing a Kubernetes service."""

  def Delete(self, cascade: bool = True) -> None:
    """Override of abstract method."""
    api = self._Api(client.CoreV1Api)
    api.delete_namespaced_service(self.name, self.namespace)

  def Read(self) -> client.V1Service:
    """Override of abstract method."""
    api = self._Api(client.CoreV1Api)
    return api.read_namespaced_service(self.name, self.namespace)

  def Type(self) -> str:
    """Returns the type of this service.

    Returns:
      str: The type of this service.
    """
    return str(self.Read().spec.type)

  def Labels(self) -> Dict[str, str]:
    """Returns the selector labels for this service.

    Returns:
      Dict[str, str]: The selector labels for this service.
    """
    labels = self.Read().spec.selector  # type: Dict[str, str]
    return labels

  def GetCoveredPods(self) -> List[base.K8sPod]:
    """Returns the pods covered by this service.

    Returns:
      List[base.K8sPod]: The pods covered by this service.
    """
    api = self._Api(client.CoreV1Api)
    pods = api.list_namespaced_pod(
        self.namespace,
        **selector.K8sSelector.FromLabelsDict(self.Labels()).ToKeywords())
    return [
        base.K8sPod(
            self._api_client, pod.metadata.name, pod.metadata.namespace)
        for pod in pods.items
    ]

  def ClusterIp(self) -> Optional[str]:
    """Returns the Cluster IP of this service.

    The return type is optional to correspond to the API return type.

    Returns:
      str: Optional. The Cluster IP of this service
    """
    cluster_ip = self.Read().spec.cluster_ip  # type: Optional[str]
    return cluster_ip

  def ExternalIps(self) -> Optional[List[str]]:
    """Returns the external IPs of this service.

    The return type is optional to correspond to the API return type.

    Returns:
      List[str]: Optional. The Cluster IP of this service
    """
    external_ips = self.Read().spec.external_i_ps  # type: Optional[List[str]]
    return external_ips
