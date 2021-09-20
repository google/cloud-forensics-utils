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
from typing import Dict
from typing import Optional
from unittest import mock

from libcloudforensics.providers.kubernetes import base
from libcloudforensics.providers.kubernetes import workloads

from kubernetes import client

MOCK_API_CLIENT = mock.Mock()

Labels = Dict[str, str]


def MakeV1ObjectMeta(
    name: Optional[str] = None,
    namespace: Optional[str] = None,
    labels: Optional[Labels] = None) -> client.V1ObjectMeta:
  """Make Kubernetes API response metadata, see V1ObjectMeta."""
  return client.V1ObjectMeta(name=name, namespace=namespace, labels=labels)


def MakeV1NodeList(amount: int) -> client.V1NodeList:
  """Make Kubernetes API Node list response, see V1NodeList."""
  items = [MakeV1Node('node-{0:d}'.format(i)) for i in range(amount)]
  return client.V1NodeList(items=items)


def MakeV1PodList(amount: int) -> client.V1PodList:
  """Make Kubernetes API Pod list response, see V1PodList."""
  items = [MakeV1Pod(name='pod-{0:d}'.format(i)) for i in range(amount)]
  return client.V1PodList(items=items)


def MakeV1Node(name: str) -> client.V1Node:
  """Make Kubernetes API Node response, see V1Node."""
  return client.V1Node(metadata=MakeV1ObjectMeta(name=name))


def MakeV1Pod(
    name: Optional[str] = None,
    namespace: Optional[str] = None,
    node_name: Optional[str] = None,
    labels: Optional[Labels] = None) -> client.V1Pod:
  """Make Kubernetes API Pod response, see V1Pod."""
  return client.V1Pod(
      metadata=MakeV1ObjectMeta(name=name, namespace=namespace, labels=labels),
      spec=client.V1PodSpec(node_name=node_name, containers=[]))


def MakeV1PodTemplateSpec(labels: Labels) -> client.V1PodTemplateSpec:
  """Make Kubernetes API template spec response, see V1PodTemplateSpec."""
  return client.V1PodTemplateSpec(metadata=MakeV1ObjectMeta(labels=labels))


def MakeV1ReplicaSet(
    name: Optional[str] = None,
    namespace: Optional[str] = None,
    template_spec_labels: Optional[Labels] = None) -> client.V1ReplicaSet:
  """Make Kubernetes API ReplicaSet response, V1ReplicaSet."""
  return client.V1ReplicaSet(
      metadata=MakeV1ObjectMeta(name=name, namespace=namespace),
      spec=client.V1ReplicaSetSpec(
          selector=client.V1LabelSelector(),
          template=MakeV1PodTemplateSpec(template_spec_labels)))


def MakeV1Deployment(
    name: Optional[str] = None,
    namespace: Optional[str] = None,
    template_spec_labels: Optional[Labels] = None,
    match_labels: Optional[Labels] = None) -> client.V1Deployment:
  """Make Kubernetes API response deployment, see V1Deployment."""
  return client.V1Deployment(
      metadata=MakeV1ObjectMeta(name=name, namespace=namespace),
      spec=client.V1DeploymentSpec(
          selector=client.V1LabelSelector(match_labels=match_labels),
          template=MakeV1PodTemplateSpec(template_spec_labels)))


def MakeMockK8sPod(
    name: str, namespace: str, read_response: client.V1Pod) -> base.K8sPod:
  """Make mock Kubernetes Pod by patching Read method."""
  mock_pod = base.K8sPod(MOCK_API_CLIENT, name, namespace)
  mock_pod.Read = mock.Mock()
  mock_pod.Read.return_value = read_response
  return mock_pod


def MakeMockK8sDeployment(
    name: str, namespace: str,
    read_response: client.V1Deployment) -> workloads.K8sDeployment:
  """Make mock Kubernetes Deployment by patching Read method."""
  mock_deploy = workloads.K8sDeployment(MOCK_API_CLIENT, name, namespace)
  mock_deploy.Read = mock.Mock()
  mock_deploy.Read.return_value = read_response
  return mock_deploy
