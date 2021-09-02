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
from typing import TYPE_CHECKING, Any, Dict

from kubernetes import client
from kubernetes.config import kube_config

from libcloudforensics import logging_utils
from libcloudforensics.providers.gcp.internal import common
from libcloudforensics.providers.kubernetes import cluster

if TYPE_CHECKING:
  import googleapiclient

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)


class GoogleKubernetesEngine:
  """Base class for calling GKE APIs."""

  GKE_API_VERSION = 'v1'

  def GkeApi(self) -> 'googleapiclient.discovery.Resource':
    """Gets a Google Container service object.

    https://container.googleapis.com/$discovery/rest?version=v1

    Returns:
      googleapiclient.discovery.Resource: A Google Container service object.
    """
    return common.CreateService('container', self.GKE_API_VERSION)


class GkeCluster(GoogleKubernetesEngine):
  """Class to call GKE and Kubernetes APIs on a GKE resource.

  https://cloud.google.com/kubernetes-engine/docs/reference/rest
  https://kubernetes.io/docs/reference/

  Attributes:
    project_id (str): The GCP project name.
    zone (str): The GCP zone for this project.
    cluster_id (str): The name of the GKE cluster.
  """

  def __init__(self, project_id: str, zone: str, cluster_id: str) -> None:
    """Creates a GKE cluster resource.

    Args:
      project_id (str): The GCP project name.
      zone (str): The GCP zone for this project.
      cluster_id (str): The name of the GKE cluster.
    """
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

  def _GetK8sApiClient(self) -> client.ApiClient:
    """Builds an authenticated Kubernetes API client.

    This method builds a kubeconfig file similarly to
    `gcloud container clusters get-credentials CLUSTER_NAME`, and then
    creates a Kubernetes API client from it. This API client can then be
    used in the Kubernetes classes

    Returns:
      client.ApiClient: An authenticated Kubernetes API client.
    """
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
      Dict[str, Any]: GKE API response to 'get' operation for this cluster.
    """
    clusters = self.GkeApi().projects().locations().clusters()  # pylint: disable=no-member
    request = clusters.get(name=self.name)
    response = request.execute()  # type: Dict[str, Any]
    return response

  def GetK8sCluster(self) -> cluster.K8sCluster:
    """Returns the Kubernetes cluster of this GKE cluster.

    Returns:
      cluster.K8sCluster: The Kubernetes cluster matching this GKE cluster,
          exposing methods to call the Kubernetes API.
    """
    return cluster.K8sCluster(self._GetK8sApiClient())
