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
from typing import TYPE_CHECKING, Any, Dict, List

from kubernetes import client
from kubernetes.config import kube_config

from libcloudforensics import logging_utils, errors
from libcloudforensics.providers.gcp.internal import common
from libcloudforensics.providers.gcp.internal import compute
from libcloudforensics.providers.kubernetes.base import K8sResource
from libcloudforensics.providers.kubernetes.selector import K8sSelector

if TYPE_CHECKING:
  import googleapiclient

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)


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

  def __init__(self, project_id: str, zone: str, cluster_id: str) -> None:
    """Creates a GKE resource.

    Args:
      project_id (str): The GCP project name.
      zone (str): The GCP zone for this project.
      cluster_id (str): The name of the GKE cluster.
    """
    super().__init__()
    self.project_id = project_id
    self.zone = zone
    self.cluster_id = cluster_id

  @property
  def name(self) -> str:
    """Name of the GKE cluster resource, for use in API calls.

    Returns:
      str: Full name of the cluster resource.
    """
    return 'projects/{0:s}/locations/{1:s}/clusters/{2:s}'.format(
      self.project_id,
      self.zone,
      self.cluster_id,
    )

  def _K8sApi(self) -> client.ApiClient:
    # Retrieve cluster information via GKE API
    get_op = self.GetOperation()
    # Extract fields for kubeconfig
    ca_data = get_op['masterAuth']['clusterCaCertificate']
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
          'server': 'https://{0:s}'.format(get_op['endpoint']),
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
    return client.ApiClient(kubeconfig)

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

  def _Node(self, node_name) -> 'GkeNode':
    """Creates a GKE Node object from this GKE resource.

    Args:
      node_name (str): The name of the node.

    Returns:
      GkeNode: GKE Node object from this resource.
    """
    return GkeNode(self.project_id, self.zone, self.cluster_id, node_name)

  def _Pod(self, pod_name) -> 'GkePod':
    """Creates a GKE Pod object from this GKE resource.

    Args:
      pod_name (str): The name of the pod.

    Returns:
      GkePod: GKE Pod object from this resource.
    """
    return GkePod(self.project_id, self.zone, self.cluster_id, pod_name)


class GkeCluster(GkeResource):
  """Class facilitating GKE API and K8s API functions calls on a cluster."""

  def GetInstances(self) -> List[compute.GoogleComputeInstance]:
    """Gets the GCE instances of the cluster".

    Returns:
      List[compute.GoogleComputeInstance]: GCE instances belonging to
        the cluster.
    """
    return [node.Instance() for node in self.GetNodes()]

  def GetNodes(self) -> List['GkeNode']:
    """Gets the Kubernetes nodes of the cluster.

    Returns:
      List[GkeNode]: GKE nodes belonging to the cluster.
    """
    api = client.CoreV1Api(self._K8sApi())

    # Collect nodes
    nodes = api.list_node().items

    # Convert to node objects
    return [self._Node(node.metadata.name) for node in nodes]


class GkeWorkload(GkeResource):
  """Class facilitating API calls on a GKE cluster's workload."""

  def __init__(self, project_id: str, zone: str, cluster_id: str,
               workload_name: str):
    super().__init__(project_id, zone, cluster_id)
    self.workload_name = workload_name

  def _Labels(self) -> Dict[str, str]:
    """Gets the match labels that are defined by this workload.

    https://kubernetes.io/docs/concepts/overview/working-with-objects/
    labels/#resources-that-support-set-based-requirements

    Returns:
      Dict[str, str]: The matchLabels of the workload.

    Raises:
      NotImplementedError: If matchExpressions exist. Using these labels in this
        case would be inaccurate, and the logic behind matchExpressions is not
        implemented at this stage.
    """
    api = client.AppsV1Api(self._K8sApi())

    # Selector to match the name of this workload
    selector = K8sSelector(
      K8sSelector.Name(self.workload_name)
    )

    # Find deployment TODO: This may be something else than a deployment
    deployments = api.list_deployment_for_all_namespaces(
      **selector.ToKeywords()
    ).items
    if len(deployments) == 0:
      message = 'Deployment matching workload {0:s} was not found.'.format(
        self.workload_name
      )
      raise errors.ResourceNotFoundError(message)
    deployment = deployments[0]

    # Extract selectors
    if deployment.spec.selector.match_expressions is not None:
      # If match expressions exist, using these labels to find the pods
      # covered by this workload will be inaccurate
      raise NotImplementedError('matchExpressions exist, meaning '
                                'pods matching matchLabels will be inaccurate.')
    return deployment.spec.selector.match_labels

  def GetCoveredPods(self) -> List['GkePod']:
    """Gets the pods covered by this workload.

    Returns:
      List[GkePod]: The pods covered by this workload
    """
    api = client.CoreV1Api(self._K8sApi())

    # Get the labels for this workload, and create a selector
    selector = K8sSelector.FromDict(self._Labels())

    # Extract the pods
    pods = api.list_pod_for_all_namespaces(
      **selector.ToKeywords()
    ).items

    # Convert to pod objects
    return [self._Pod(pod.metadata.name) for pod in pods]


class GkePod(GkeResource):
  """Class facilitating API calls for a Pod in a GKE cluster."""

  def __init__(self, project_id, zone, cluster_id, pod_name) -> None:
    super().__init__(project_id, zone, cluster_id)
    self.pod_name = pod_name

  def GetNode(self) -> 'GkeNode':
    """Get the GKE node that this pod is running on.

    Returns:
      GkeNode: The GKE node this pod is running on.
    """
    api = client.CoreV1Api(self._K8sApi())

    # Find a pod with a name corresponding to this pod
    selector = K8sSelector(
      K8sSelector.Name(self.pod_name)
    )

    pods = api.list_pod_for_all_namespaces(
      **selector.ToKeywords()
    ).items
    if len(pods) == 0:
      raise errors.ResourceNotFoundError(
        'Pod matching {0:s} was not found'.format(self.pod_name))
    pod = pods[0]

    return self._Node(pod.spec.node_name)


class GkeNode(GkeResource):
  """Class facilitating API functions calls on a GKE cluster's node."""

  def __init__(self, project_id: str, zone: str, cluster_id: str,
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

  def GetRunningPods(self) -> List['GkePod']:
    """Returns the pods running on the node.

    Returns:
      List[GkePod]: The pods running on this node."""
    api = client.CoreV1Api(self._K8sApi())

    # The pods must be running, and must be on this node,
    # the selectors here are as per the API calls in `kubectl
    # describe node NODE_NAME`
    selector = K8sSelector(
      K8sSelector.Node(self.node_name),
      K8sSelector.Running(),
    )

    pods = api.list_pod_for_all_namespaces(
      **selector.ToKeywords()
    ).items
    if len(pods) == 0:
      logger.warning(
        "No pods found on node {0:s}, node may be misspelled".format(
          self.node_name))

    return [self._Pod(pod.metadata.name) for pod in pods]

  def Cordon(self) -> None:
    """Cordons the node, making the node unschedulable.

    https://kubernetes.io/docs/concepts/architecture
    /nodes/#manual-node-administration
    """
    api = client.CoreV1Api(self._K8sApi())

    # Create the body as per the API call to PATCH in
    # `kubectl cordon NODE_NAME`
    body = {
      'spec': {
        'unschedulable': True
      }
    }

    # Cordon the node with the PATCH verb
    api.patch_node(self.node_name, body)
