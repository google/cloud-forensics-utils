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
from typing import Optional, TYPE_CHECKING, Any, Dict

from googleapiclient.errors import HttpError

from kubernetes import client
from kubernetes.config import kube_config

from libcloudforensics import errors
from libcloudforensics import logging_utils
from libcloudforensics.providers.gcp.internal import common
from libcloudforensics.providers.kubernetes import base
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


class GkeCluster(cluster.K8sCluster, GoogleKubernetesEngine):
  """Class to call GKE and Kubernetes APIs on a GKE resource.

  https://cloud.google.com/kubernetes-engine/docs/reference/rest
  https://kubernetes.io/docs/reference/

  Attributes:
    project_id (str): The GCP project name.
    location (str): The GCP region/zone for this cluster.
    cluster_id (str): The name of the GKE cluster.
  """

  def __init__(self, project_id: str, location: str, cluster_id: str) -> None:
    """Creates a GKE cluster resource.

    Args:
      project_id (str): The GCP project name.
      location (str): The GCP zone for this cluster.
      cluster_id (str): The name of the GKE cluster.
    """
    self.project_id = project_id
    self.location = location
    self.cluster_id = cluster_id
    cluster.K8sCluster.__init__(self, self._GetK8sApiClient())

  @property
  def name(self) -> str:
    """Name of the GKE cluster resource, for use in API calls.

    Returns:
      str: Full name of the cluster resource.
    """
    return 'projects/{0:s}/locations/{1:s}/clusters/{2:s}'.format(
        self.project_id,
        self.location,
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
        self.location,
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
    try:
      response = request.execute()  # type: Dict[str, Any]
    except HttpError as exception:
      if exception.resp.status == 404:
        raise errors.ResourceNotFoundError(
          '{0:s} not found: {1!s}'.format(self.name, exception),
          __name__) from exception
      raise errors.ResourceNotFoundError(
        'Unknown error occured when getting cluster {0:s}: {1!s}'.format(
            self.name, exception),
        __name__) from exception
    return response

  def _MakeQuery(self, query_type: str) -> str:
    """Creates a query string filtering for this cluster and the given type.

    Args:
      query_type (str): The query type string (the value for the resource.type
          key).

    Returns:
      str: The query string filtering for this cluster and the given type.
    """
    return (
        'resource.type="{query_type:s}"\n'
        'resource.labels.project_id="{project_id:s}"\n'
        'resource.labels.cluster_name="{cluster_id:s}"\n'
        'resource.labels.location="{location:s}"\n'.format(
            query_type=query_type,
            project_id=self.project_id,
            cluster_id=self.cluster_id,
            location=self.location))

  def ClusterLogsQuery(
      self, workload: Optional[base.K8sWorkload] = None) -> str:
    """Creates the GCP k8s_cluster logs query string for this cluster.

    A workload may optionally be specified, in which case the returned query
    string will be more specific to only cover that workload.

    Args:
      workload (base.K8sWorkload): Optional. A workload to specify in the query
          string.

    Returns:
      str: The k8s_cluster logs query string.
    """
    query = self._MakeQuery('k8s_cluster')
    if workload:
      query += workload.GcpClusterLogsQuerySupplement()
    return query.strip()

  def ContainerLogsQuery(
      self, workload: Optional[base.K8sWorkload] = None) -> str:
    """Returns the GCP k8s_container logs query string for this cluster.

    A workload may optionally be specified, in which case the returned query
    string will be more specific to only cover that workload.

    Args:
      workload (base.K8sWorkload): Optional. A workload to specify in the query
          string.

    Returns:
      str: The k8s_container logs query string.
    """
    query = self._MakeQuery('k8s_container')
    if workload:
      query += workload.GcpContainerLogsQuerySupplement()
    return query.strip()

  def _GetValue(self, *keys: str, default: Any = None) -> Any:
    """Gets a nested value from this cluster's 'GET' using a list of keys.

    Args:
      *keys (str): The key path to the nested value.
      default (Any): Optional. If a key from the key path is not present,
          this value will be returned. Defaults to None.

    Returns:
      Any: The value at the end of the key path, or the default value if
          a key was not present

    Raises:
      KeyError: If an object along the key path was not a dict.
    """
    current = self.GetOperation()
    for key in keys:
      if isinstance(current, dict):
        if key in current:
          current = current[key]
        else:
          return default
      else:
        raise KeyError('Nested object was not a dict.')
    return current

  def IsWorkloadIdentityEnabled(self) -> bool:
    """Returns whether the workload identity is enabled.

    Returns:
      bool: True if workload identity is enabled, False otherwise.
    """
    return bool(
        self._GetValue(
            'nodeConfig',
            'workloadMetadataConfig',
            'mode') == 'GKE_METADATA')

  def IsLegacyEndpointsDisabled(self) -> bool:
    """Returns whether legacy endpoints are enabled.

    Returns:
      bool: True if legacy endpoints are disabled, False otherwise.
    """
    return bool(
        self._GetValue(
            'nodeConfig',
            'metadata',
            'disable-legacy-endpoints') == 'true')

  def IsNetworkPolicyEnabled(self) -> bool:
    """Override of abstract method."""
    return bool(self._GetValue('networkPolicy', 'enabled', default=False))
