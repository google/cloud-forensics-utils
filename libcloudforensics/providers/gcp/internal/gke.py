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
from libcloudforensics.providers.gcp.internal import common

if TYPE_CHECKING:
  import googleapiclient


class GoogleKubernetesEngine:
  """Class to call Google Kubernetes Engine (GKE) APIs.

  https://cloud.google.com/kubernetes-engine/docs/reference/rest
  """
  GKE_API_VERSION = 'v1'

  def GkeApi(self) -> 'googleapiclient.discovery.Resource':
    """Gets a Google Container service object.

    https://container.googleapis.com/$discovery/rest?version=v1

    Returns:
      googleapiclient.discovery.Resource: A Google Container service object.
    """

    return common.CreateService(
        'container', self.GKE_API_VERSION)

  def GetCluster(self, name: str) -> Dict[str, Any]:
    """ Gets the details of a specific cluster.

    Args:
      name (str): The name (project, location, cluster) of the cluster to
          retrieve. Specified in the format `projects/*/locations/*/clusters/*`.
          For regional cluster: `/locations/[GCP_REGION]`.
          For zonal cluster: `/locations/[GCP_ZONE]`.

    Returns:
      Dict: A Google Kubernetes Engine cluster object:
          https://cloud.google.com/kubernetes-engine/docs/reference/rest/v1/projects.locations.clusters#Cluster  # pylint: disable=line-too-long
    """
    gke_clusters = self.GkeApi().projects().locations().clusters() # pylint: disable=no-member
    request = gke_clusters.get(name=name)
    response = request.execute()  # type: Dict[str, Any]
    return response
