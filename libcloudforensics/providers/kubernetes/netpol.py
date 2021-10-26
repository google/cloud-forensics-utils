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

from kubernetes import client

from libcloudforensics.providers.kubernetes import base


class K8sNetworkPolicy(base.K8sNamespacedResource):
  """Class representing a Kubernetes NetworkPolicy, enabling API calls."""

  def Delete(self, cascade: bool = True) -> None:
    """Override of abstract method. The cascade parameter is ignored."""
    api = self._Api(client.NetworkingV1Api)
    api.delete_namespaced_network_policy(self.name, self.namespace)

  def Read(self) -> client.V1NetworkPolicy:
    """Override of abstract method."""
    api = self._Api(client.NetworkingV1Api)
    return api.read_namespaced_network_policy(self.name, self.namespace)

  def Patch(
      self,
      match_labels: Optional[Dict[str, str]] = None,
      not_match_labels: Optional[Dict[str, str]] = None) -> None:
    """Patches a Kubernetes NetworkPolicy to (not) match specified labels.

    The patched NetworkPolicy will have new fields in the podSelector's
    matchLabels and matchExpressions, so that it now has to match the labels
    given in match_labels, and not match the labels in not_match_labels.

    e.g. calling this method on a policy with an empty podSelector with args:

    ```
    match_labels={'app': 'nginx'}
    not_match_labels={'quarantine': 'true'}
    ```

    will result in a NetworkPolicy with the following spec YAML:

    ```
      spec:
        podSelector:
          matchExpressions:
          - key: quarantine
            operator: NotIn
            values:
            - "true"
          matchLabels:
            app: nginx
    ```

    Args:
      match_labels: The matchLabels to be added to the NetworkPolicy spec.
      not_match_labels: The labels to excluded from the NetworkPolicy. Each
          of these key-value pairs will result in a line in matchExpressions
          with the format {key: KEY, operator: NotIn, values: [VALUE]}.
    """
    api = self._Api(client.NetworkingV1Api)

    match_expressions = self.Read().spec.pod_selector.match_expressions or []
    if not_match_labels:
      match_expressions.extend(
          client.V1LabelSelectorRequirement(
              key=key, operator='NotIn', values=[value]) for key,
          value in not_match_labels.items())

    api.patch_namespaced_network_policy(
        self.name,
        self.namespace,
        {
            'spec':
                client.V1NetworkPolicySpec(
                    pod_selector=client.V1LabelSelector(
                        match_labels=match_labels,
                        match_expressions=match_expressions,
                    ))
        })


class K8sNetworkPolicyWithSpec(K8sNetworkPolicy, metaclass=abc.ABCMeta):
  """Class representing a Kubernetes NetworkPolicy with an underlying spec.

  This class additionally exposes creation API calls, as specification
  arguments can now be provided.
  """

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


class K8sTargetedDenyAllNetworkPolicy(K8sNetworkPolicyWithSpec):
  """Class representing a deny-all NetworkPolicy.

  https://kubernetes.io/docs/concepts/services-networking/network-policies/#default-deny-all-ingress-and-all-egress-traffic  # pylint: disable=line-too-long

  Attributes:
    labels (Dict[str, str]): The matchLabels used by this NetworkPolicy.
  """

  def __init__(self, api_client: client.ApiClient, namespace: str) -> None:
    """Returns a deny-all Kubernetes NetworkPolicy.

    Args:
      api_client (ApiClient): The Kubernetes API client to the cluster.
      namespace (str): The namespace for this NetworkPolicy.
    """
    self._GenerateTag()
    name = 'cfu-netpol-{0:s}'.format(self._tag)
    super().__init__(api_client, name, namespace)

  def _GenerateTag(self) -> None:
    """Generates a random tag for this deny-all NetworkPolicy."""
    chars = random.choices(string.ascii_lowercase + string.digits, k=16)
    self._tag = ''.join(chars)

  @property
  def labels(self) -> Dict[str, str]:
    """The pod selector labels (matchLabels) of this policy."""
    return {'quarantineId': self._tag}

  @property
  def _spec(self) -> client.V1NetworkPolicySpec:
    """Override of abstract property."""
    return client.V1NetworkPolicySpec(
        pod_selector=client.V1LabelSelector(match_labels=self.labels),
        policy_types=[
            'Ingress',
            'Egress',
        ])
