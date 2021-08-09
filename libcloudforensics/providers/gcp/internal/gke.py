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

from typing import Optional, TYPE_CHECKING, Any, Dict, List
from kubernetes import client
from kubernetes.config import kube_config
from libcloudforensics.providers.gcp.internal import compute
from libcloudforensics.providers.gcp.internal import common
from libcloudforensics.providers.kubernetes import K8sResource, K8sSelector

if TYPE_CHECKING:
  import googleapiclient


class GoogleKubernetesEngine:
  """Base class for calling GKE APIs."""

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


class GkeResource(GoogleKubernetesEngine, K8sResource):
  """Class to call GKE and Kubernetes APIs on a GKE resource.

  https://cloud.google.com/kubernetes-engine/docs/reference/rest
  https://kubernetes.io/docs/reference/
  """

  def __init__(self, project_id, zone, cluster_id) -> None:
    super().__init__()
    self.project_id = project_id
    self.zone = zone
    self.cluster_id = cluster_id

  @property
  def name(self):
    """Name of the GKE cluster resource, for use in API calls.

    Returns:
      str: Full name of the cluster resource.
    """
    return 'projects/{0:s}/locations/{1:s}/clusters/{2:s}'.format(
        self.project_id,
        self.zone,
        self.cluster_id,
    )

  def _K8sApi(self) -> 'client.CoreV1Api':
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
    """Get GKE API operation object for the GKE resource.

    Returns:
      Dict[str, Any]: GKE API response to 'get' operation for this
        cluster.
    """
    clusters = self._GkeApi().projects().locations().clusters()  # pylint: disable=no-member
    request = clusters.get(name=self.name)
    response = request.execute()
    return response


class GkeCluster(GkeResource):
  """Class facilitating GKE API and K8s API functions calls on a cluster."""

  def _Node(self, node_name):
    return GkeNode(self.project_id, self.zone, self.cluster_id, node_name)

  def GetInstances(self) -> List[compute.GoogleComputeInstance]:
    """Gets the GCE instances of the cluster".

    Returns:
      List[compute.GoogleComputeInstance]: GCE instances belonging to
        the cluster.
    """
    return [node.Instance() for node in self.GetNodes()]

  def GetNodes(self, workload: Optional[str] = None) -> List['GkeNode']:
    """Gets the Kubernetes nodes of the cluster

    Args:
      workload (str): Optional: The workload identifier whose
        nodes must be returned.

    Returns:
      List[GkeNode]: GKE nodes belonging to the cluster, potentially
        filtered for specified workload.
    """
    nodes = []
    if workload is None:
      for node in self._K8sApi().list_node().items:
        nodes.append(self._Node(node.metadata.name))
    else:
      # Retrieve pods that ar running the workload
      selector = 'app={0:s}'.format(workload)
      pods = self._K8sApi().list_pod_for_all_namespaces(
        label_selector=selector).items
      # Collect node names
      node_names = {pod.spec.node_name for pod in pods}
      # Convert to node objects
      for name in node_names:
        nodes.append(self._Node(name))
    return nodes

class GkeNode(GkeResource):
  """Class facilitating API functions calls on a GKE cluster's node."""

  def __init__(
      self, project_id: str, zone: str, cluster_id: str,
      node_name: str) -> None:
    super().__init__(project_id, zone, cluster_id)
    self.node_name = node_name

  def Instance(self) -> compute.GoogleComputeInstance:
    """Returns the GCE instance matching this node.

    Returns:
      GoogleComputeInstance: The instance matching this node.
    """
    return compute.GoogleComputeInstance(
      self.project_id,
      self.zone,
      self.node_name
    )

  def GetRunningPods(self):
    """Returns the pods running on the node."""
    selector = K8sSelector(
        K8sSelector.Node(self.node_name),
        K8sSelector.Running(),
    )
    pods = self._K8sApi().list_pod_for_all_namespaces(
        field_selector=selector.ToString())
    for pod in pods.items:
      print(pod.metadata.name)
    return pods

  def Cordon(self):
    """Cordons the node."""
    body = {
      'spec': {
        'unschedulable': True
      }
    }
    self._K8sApi().patch_node(self.node_name, body)
