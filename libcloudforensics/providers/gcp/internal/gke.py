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
"""Google Kubernetes Engine functionalities."""

import abc
from typing import TYPE_CHECKING, Any, Dict, List
from kubernetes import client
from kubernetes.config import kube_config
from libcloudforensics.providers.gcp.internal import compute
from libcloudforensics.providers.gcp.internal import common

if TYPE_CHECKING:
  import googleapiclient


class K8sSelector:
  """Class to build K8s API selectors."""

  class Component(abc.ABC):
    """Component of the selector."""

    @abc.abstractmethod
    def ToString(self):
      """Returns the component of the selector."""

  class Node(Component):
    """Component for running on a particular node."""

    def __init__(self, node) -> None:
      super().__init__()
      self.node = node

    def ToString(self):
      return 'spec.nodeName={0:s}'.format(self.node)

  class Running(Component):
    """Component for a running pod."""

    def ToString(self):
      return 'status.phase!=Failed,status.phase!=Succeeded'


  def __init__(self, *selectors):
    self.selectors = selectors

  def ToString(self):
    """Builds the selector string to be passed to the K8s API."""
    return ','.join(map(lambda s: s.ToString(), self.selectors))


class GoogleKubernetesEngine:
  """Class to call Google Kubernetes Engine (GKE) APIs.

  https://cloud.google.com/kubernetes-engine/docs/reference/rest
  """
  GKE_API_VERSION = 'v1'

  @staticmethod
  def _GkeApi() -> 'googleapiclient.discovery.Resource':
    """Gets a Google Container service object.

    https://container.googleapis.com/$discovery/rest?version=v1

    Returns:
      googleapiclient.discovery.Resource: A Google Container service object.
    """
    return common.CreateService(
        'container', GoogleKubernetesEngine.GKE_API_VERSION)


class GkeCluster(GoogleKubernetesEngine):
  """Class facilitating GKE API and K8s API functions calls on a cluster."""

  def __init__(self, project_id, zone, cluster_id) -> None:
    super().__init__()
    self.project_id = project_id
    self.zone = zone
    self.cluster_id = cluster_id

  @property
  def name(self):
    """Property to retrieve the name of the cluster, for use in API calls.

    Returns:
      str: Full name of the cluster.
    """
    return 'projects/{0:s}/locations/{1:s}/clusters/{2:s}'.format(
        self.project_id,
        self.zone,
        self.cluster_id,
    )

  def _K8sApi(self) -> 'client.CoreV1Api':
    """Creates an authenticated Kubernetes API client.

    Returns:
      kubernetes.client.CoreV1Api: An authenticated client to
        the Kubernetes API server.
    """
    # Retrieve cluster information via GKE API
    get = self.GetOperation()
    # Extract fields for kubeconfig
    ca_data = get['masterAuth']['clusterCaCertificate']
    # Context string is built the same way that gcloud does
    # in get-credentials
    context = '_'.join([
        'gke',
        self.project_id,
        self.zone,
        self.name,
    ])
    # Build kubeconfig dict and load
    kubeconfig = client.Configuration()
    loader = kube_config.KubeConfigLoader({
        'apiVersion': self.GKE_API_VERSION,
        'current-context': context,
        'clusters': [{
            'name': context,
            'cluster': {
                'certificate-authority-data': ca_data,
                'server': 'https://{0:s}'.format(get['endpoint']),
            }
        }],
        'contexts': [{
            'name': context, 'context': {
                'cluster': context, 'user': context
            }
        }],
        'users': [{
            'name': context, 'user': {
                'auth-provider': {
                    'name': 'gcp'
                }
            }
        }]
    })
    loader.load_and_set(kubeconfig)
    return client.CoreV1Api(client.ApiClient(kubeconfig))

  def GetOperation(self) -> Dict[str, Any]:
    """Get GKE API operation object for the GKE cluster.

    Returns:
      Dict[str, Any]: GKE API response to 'get' operation for this
        cluster.
    """
    clusters = self._GkeApi().projects().locations().clusters()  # pylint: disable=no-member
    request = clusters.get(name=self.name)
    response = request.execute()
    return response

  def GetInstances(self) -> List[compute.GoogleComputeInstance]:
    """Gets the GCE instances of the cluster".

    Returns:
      List[compute.GoogleComputeInstance]: GCE instances belonging to
        the cluster.
    """
    instances = []
    for node in self._K8sApi().list_node().items:
      instance = compute.GoogleComputeInstance(
          self.project_id, self.zone, node.metadata.name)
      instances.append(instance)
    return instances

  def GetRunningPods(self, node: str):
    """Returns the pods running for a particular node"""
    selector = K8sSelector(
      K8sSelector.Node(node),
      K8sSelector.Running(),
    )
    pods = self._K8sApi().list_pod_for_all_namespaces(
      field_selector=selector.ToString())
    for pod in pods.items:
      print(pod.metadata.name)
    return pods
