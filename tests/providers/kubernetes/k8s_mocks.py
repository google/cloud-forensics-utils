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
"""Kubernetes mock response objects, used for testing."""
from typing import Dict, Optional
from unittest import mock

from kubernetes import client

MOCK_API_CLIENT = mock.Mock()

Labels = Dict[str, str]

# pylint: disable=line-too-long

def V1ObjectMeta(
    name: Optional[str] = None,
    namespace: Optional[str] = None,
    labels: Optional[Labels] = None) -> client.V1ObjectMeta:
  """Make Kubernetes API response metadata, see V1ObjectMeta.

  https://github.com/kubernetes-client/python/blob/master/kubernetes/docs/V1ObjectMeta.md
  """
  return client.V1ObjectMeta(name=name, namespace=namespace, labels=labels)


def V1NodeList(amount: int) -> client.V1NodeList:
  """Make Kubernetes API Node list response, see V1NodeList.

  https://github.com/kubernetes-client/python/blob/master/kubernetes/docs/V1NodeList.md
  """
  items = [V1Node('node-{0:d}'.format(i)) for i in range(amount)]
  return client.V1NodeList(items=items)


def V1PodList(amount: int) -> client.V1PodList:
  """Make Kubernetes API Pod list response, see V1PodList.

  https://github.com/kubernetes-client/python/blob/master/kubernetes/docs/V1PodList.md
  """
  items = [V1Pod(name='pod-{0:d}'.format(i)) for i in range(amount)]
  return client.V1PodList(items=items)

def V1NetworkPolicyList(
    amount: int, namespace: str) -> client.V1NetworkPolicyList:
  """Make Kubernetes API NetworkPolicy list, see V1NetworkPolicyList.

  https://github.com/kubernetes-client/python/blob/master/kubernetes/docs/V1NetworkPolicyList.md
  """
  items = [
      V1NetworkPolicy('netpol-{0:d}'.format(i), namespace)
      for i in range(amount)
  ]
  return client.V1NetworkPolicyList(items=items)

def V1NetworkPolicy(name: str, namespace: str) -> client.V1NetworkPolicy:
  """Make Kubernetes API NetworkPolicy response, see V1NetworkPolicy.

  https://github.com/kubernetes-client/python/blob/master/kubernetes/docs/V1NetworkPolicy.md
  """
  return client.V1NetworkPolicy(
      metadata=V1ObjectMeta(name=name, namespace=namespace))

def V1Service(selector_labels: Labels) -> client.V1Service:
  """Make Kubernetes API service response, see V1Service.

  https://github.com/kubernetes-client/python/blob/master/kubernetes/docs/V1Service.md
  """
  return client.V1Service(spec=client.V1ServiceSpec(selector=selector_labels))

def V1Node(name: str) -> client.V1Node:
  """Make Kubernetes API Node response, see V1Node.

  https://github.com/kubernetes-client/python/blob/master/kubernetes/docs/V1Node.md
  """
  return client.V1Node(metadata=V1ObjectMeta(name=name))


def V1Pod(
    name: Optional[str] = None,
    namespace: Optional[str] = None,
    node_name: Optional[str] = None,
    labels: Optional[Labels] = None) -> client.V1Pod:
  """Make Kubernetes API Pod response, see V1Pod.

  https://github.com/kubernetes-client/python/blob/master/kubernetes/docs/V1Pod.md
  """
  return client.V1Pod(
      metadata=V1ObjectMeta(name=name, namespace=namespace, labels=labels),
      spec=client.V1PodSpec(node_name=node_name, containers=[]))


def V1PodTemplateSpec(labels: Labels) -> client.V1PodTemplateSpec:
  """Make Kubernetes API template spec response, see V1PodTemplateSpec.

  https://github.com/kubernetes-client/python/blob/master/kubernetes/docs/V1PodTemplateSpec.md
  """
  return client.V1PodTemplateSpec(metadata=V1ObjectMeta(labels=labels))


def V1ReplicaSet(
    name: Optional[str] = None,
    namespace: Optional[str] = None,
    template_spec_labels: Optional[Labels] = None) -> client.V1ReplicaSet:
  """Make Kubernetes API ReplicaSet response, V1ReplicaSet.

  https://github.com/kubernetes-client/python/blob/master/kubernetes/docs/V1ReplicaSet.md
  """
  return client.V1ReplicaSet(
      metadata=V1ObjectMeta(name=name, namespace=namespace),
      spec=client.V1ReplicaSetSpec(
          selector=client.V1LabelSelector(),
          template=V1PodTemplateSpec(template_spec_labels or {})))


def V1Deployment(
    name: Optional[str] = None,
    namespace: Optional[str] = None,
    template_spec_labels: Optional[Labels] = None,
    match_labels: Optional[Labels] = None) -> client.V1Deployment:
  """Make Kubernetes API response deployment, see V1Deployment.

  https://github.com/kubernetes-client/python/blob/master/kubernetes/docs/V1Deployment.md
  """
  return client.V1Deployment(
      metadata=V1ObjectMeta(name=name, namespace=namespace),
      spec=client.V1DeploymentSpec(
          selector=client.V1LabelSelector(match_labels=match_labels),
          template=V1PodTemplateSpec(template_spec_labels or {})))
