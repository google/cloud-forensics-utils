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
"""Kubernetes classes for wrapping NetworkPolicy APIs."""
import abc
import random
import string
from typing import Dict, Optional

from libcloudforensics.providers.kubernetes import base

from kubernetes import client

class K8sNetworkPolicy(base.K8sNamespacedResource):

  def Delete(self, cascade: bool = True) -> None:
    """Override of abstract method. The cascade parameter is ignored."""
    api = self._Api(client.NetworkingV1Api)
    api.delete_namespaced_network_policy(self.name, self.namespace)

  def Read(self) -> client.V1NetworkPolicy:
    """Override of abstract method."""
    api = self._Api(client.NetworkingV1Api)
    return api.read_namespaced_network_policy(self.name, self.namespace)

class K8sNetworkPolicyWithSpec(K8sNetworkPolicy, metaclass=abc.ABCMeta):

  @property
  @abc.abstractmethod
  def _spec(self) -> client.V1NetworkPolicySpec:
    """The specification of this network policy to be used on creation."""

  @property
  def _metadata(self) -> client.V1ObjectMeta:
    """The metadata of this network policy to be used on creation."""
    return client.V1ObjectMeta(namespace=self.namespace, name=self.name)

  @property
  def _policy(self) -> client.V1NetworkPolicy:
    """The policy object of this network policy to be used on creation."""
    return client.V1NetworkPolicy(spec=self._spec, metadata=self._metadata)

  def Create(self) -> None:
    """Creates this network policy via the Kubernetes API."""
    api = self._Api(client.NetworkingV1Api)
    api.create_namespaced_network_policy(self.namespace, self._policy)

class K8sDenyAllNetworkPolicy(K8sNetworkPolicyWithSpec):

  def __init__(self, api_client: client.ApiClient, namespace: str) -> None:
    self._GenerateTag()
    name = 'cfu-netpol-{0:s}'.format(self._tag)
    super().__init__(api_client, name, namespace)

  def _GenerateTag(self) -> None:
    """Generates a tag that this deny all network policy will use."""
    chars = random.choices(string.ascii_lowercase + string.digits, k=16)
    self._tag = ''.join(chars)

  @property
  def labels(self):
    """The pod selector labels of this policy."""
    return {'quarantineId': self._tag}

  @property
  def _spec(self):
    """Override of abstract property. A deny all spec object is created.
    https://kubernetes.io/docs/concepts/services-networking/network-policies/#default-deny-all-ingress-and-all-egress-traffic  # pylint: disable=line-too-long
    """
    return client.V1NetworkPolicySpec(
      pod_selector=client.V1LabelSelector(match_labels=self.labels),
      policy_types=[
        'Ingress',
        'Egress',
      ]
    )
