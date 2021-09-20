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
"""Test on netpol Kubernetes objects."""

import unittest
from unittest import mock

from libcloudforensics.providers.kubernetes import workloads
from tests.providers.kubernetes import k8s_mocks

from kubernetes import client

class K8sWorkloadTest(unittest.TestCase):
  """Test Kubernetes NetworkPolicy API calls."""

  mock_match_labels = {
    'app': 'nginx-klzkdoho'
  }

  @mock.patch.object(workloads.K8sWorkload, '__abstractmethods__', set())
  @mock.patch.object(workloads.K8sWorkload, '_PodMatchLabels')
  def testPodIsCoveredByWorkloadSameLabels(self, mock_pod_match_labels):
    """Tests that a pod is indeed covered by a workload."""
    # Override abstract method
    mock_pod_match_labels.return_value = self.mock_match_labels

    mock_pod_response = k8s_mocks.MakeV1Pod(labels=self.mock_match_labels)
    mock_pod = k8s_mocks.MakeMockK8sPod('name', 'namespace', mock_pod_response)

    workload = workloads.K8sWorkload(k8s_mocks.MOCK_API_CLIENT, 'name', 'namespace')

    self.assertTrue(workload.IsCoveringPod(mock_pod))

  @mock.patch.object(workloads.K8sWorkload, '__abstractmethods__', set())
  @mock.patch.object(workloads.K8sWorkload, '_PodMatchLabels')
  def testPodIsCoveredByWorkloadDifferentLabels(self, mock_pod_match_labels):
    """Tests that a pod is not covered by a workload with different labels."""
    # Override abstract method
    mock_pod_match_labels.return_value = self.mock_match_labels

    mock_pod_response = k8s_mocks.MakeV1Pod(labels={})
    mock_pod = k8s_mocks.MakeMockK8sPod('name', 'namespace', mock_pod_response)

    workload = workloads.K8sWorkload(k8s_mocks.MOCK_API_CLIENT, 'name', 'namespace')

    self.assertFalse(workload.IsCoveringPod(mock_pod))

  @mock.patch.object(workloads.K8sWorkload, '__abstractmethods__', set())
  @mock.patch.object(workloads.K8sWorkload, '_PodMatchLabels')
  def testPodIsCoveredByWorkloadDifferentNamespace(self, mock_pod_match_labels):
    """Tests that a pod is not covered by a workload with a different namespace."""
    # Override abstract method
    mock_pod_match_labels.return_value = self.mock_match_labels

    mock_pod_response = k8s_mocks.MakeV1Pod(labels=self.mock_match_labels)
    mock_pod = k8s_mocks.MakeMockK8sPod('name', 'production', mock_pod_response)

    workload = workloads.K8sWorkload(k8s_mocks.MOCK_API_CLIENT, 'name', 'namespace')

    self.assertFalse(workload.IsCoveringPod(mock_pod))

  @mock.patch.object(workloads.K8sWorkload, '__abstractmethods__', set())
  @mock.patch.object(workloads.K8sWorkload, '_PodMatchLabels')
  @mock.patch('kubernetes.client.CoreV1Api.list_namespaced_pod')
  def testListPodInSameNamespace(self, mock_list_pod, mock_pod_match_labels):
    """Tests that workload pods are listed in the same namespace."""
    # Override abstract method
    mock_pod_match_labels.return_value = self.mock_match_labels

    mock_namespace = 'namespace-xdwvkhrj'
    workload = workloads.K8sWorkload(k8s_mocks.MOCK_API_CLIENT, 'name', mock_namespace)
    workload.GetCoveredPods()

    self.assertEqual(mock_list_pod.call_args.args[0], mock_namespace)

  @mock.patch.object(workloads.K8sWorkload, '__abstractmethods__', set())
  @mock.patch.object(workloads.K8sWorkload, '_PodMatchLabels')
  @mock.patch('kubernetes.client.CoreV1Api.list_namespaced_pod')
  def testListPodWithWorkloadLabels(self, mock_list_pod, mock_pod_match_labels):
    """Tests that workload pods are listed with the correct labels."""
    # Override abstract method
    mock_pod_match_labels.return_value = self.mock_match_labels

    workload = workloads.K8sWorkload(k8s_mocks.MOCK_API_CLIENT, 'name', 'namespace')
    workload.GetCoveredPods()

    self.assertEqual(mock_list_pod.call_args.kwargs['label_selector'], 'app=nginx-klzkdoho')

  @mock.patch('kubernetes.client.AppsV1Api.delete_namespaced_replica_set')
  def testReplicaSetNonCascadingDeletionArgs(self, mock_delete):
    """Tests that a ReplicaSet's deletion specifies correct args."""
    workload = workloads.K8sReplicaSet(k8s_mocks.MOCK_API_CLIENT, 'name-cvjcofvh', 'namespace-gonnujrl')
    workload.Delete(cascade=False)
    mock_delete.assert_called_once_with('name-cvjcofvh', 'namespace-gonnujrl', body={'propagationPolicy': 'Orphan'})

  @mock.patch('kubernetes.client.AppsV1Api.delete_namespaced_deployment')
  def testDeploymentNonCascadingDeletionArgs(self, mock_delete):
    """Tests that a Deployment's deletion specifies correct args."""
    workload = workloads.K8sDeployment(k8s_mocks.MOCK_API_CLIENT, 'name-cvjcofvh', 'namespace-gonnujrl')
    workload.Delete(cascade=False)
    mock_delete.assert_called_once_with('name-cvjcofvh', 'namespace-gonnujrl', body={'propagationPolicy': 'Orphan'})

  @mock.patch('kubernetes.client.AppsV1Api.list_namespaced_replica_set')
  def testDeploymentReplicaSet(self, mock_list_replica_set):
    """Tests that a ReplicaSet matching the Deployment's spec is returned."""
    mock_list_replica_set_response = mock.Mock()
    mock_list_replica_set_response.items = [
      k8s_mocks.MakeV1ReplicaSet(name='replicaset-0', template_spec_labels={}),
      k8s_mocks.MakeV1ReplicaSet(name='replicaset-1', template_spec_labels={}),
      k8s_mocks.MakeV1ReplicaSet(name='replicaset-2', template_spec_labels={}),
      k8s_mocks.MakeV1ReplicaSet(name='replicaset-3', template_spec_labels={}),
      k8s_mocks.MakeV1ReplicaSet(name='replicaset-4', template_spec_labels={'app': 'nginx', 'pod-template-hash': 'abcd'}),
      k8s_mocks.MakeV1ReplicaSet(name='replicaset-5', template_spec_labels={}),
      k8s_mocks.MakeV1ReplicaSet(name='replicaset-6', template_spec_labels={}),
      k8s_mocks.MakeV1ReplicaSet(name='replicaset-7', template_spec_labels={}),
      k8s_mocks.MakeV1ReplicaSet(name='replicaset-8', template_spec_labels={}),
      k8s_mocks.MakeV1ReplicaSet(name='replicaset-9', template_spec_labels={}),
    ]

    mock_list_replica_set.return_value = mock_list_replica_set_response

    deployment_response = k8s_mocks.MakeV1Deployment(template_spec_labels={'app': 'nginx'}, match_labels={'app': 'nginx'})
    deployment = k8s_mocks.MakeMockK8sDeployment('deployment', 'default', deployment_response)

    self.assertEqual(deployment._ReplicaSet().name, 'replicaset-4')
