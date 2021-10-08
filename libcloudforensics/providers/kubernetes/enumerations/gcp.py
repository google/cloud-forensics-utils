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
"""GCP Enumeration classes."""
from typing import Any, Dict, Iterable, Optional

from libcloudforensics.providers.gcp.internal import gke
from libcloudforensics.providers.kubernetes.enumerations import base


class GkeClusterEnumeration(base.Enumeration[gke.GkeCluster]):
  """Enumeration class for a GKE cluster."""

  @property
  def keyword(self) -> str:
    """Override of abstract property."""
    return 'GkeCluster'

  def _Children(
      self, namespace: Optional[str] = None) -> Iterable[base.Enumeration[Any]]:
    """Method override."""
    yield base.ClusterEnumeration(self._object)

  def _Populate(self, info: Dict[str, Any], warnings: Dict[str, Any]) -> None:
    """Method override."""
    info['Name'] = self._object.cluster_id
    info['NetworkPolicy'] = (
        'Enabled' if self._object.IsNetworkPolicyEnabled() else 'Disabled')
    if self._object.IsWorkloadIdentityEnabled():
      info['WorkloadIdentity'] = 'Enabled'
    else:
      warnings['WorkloadIdentity'] = 'Disabled'
    if self._object.IsLegacyEndpointsDisabled():
      info['LegacyEndpoints'] = 'Disabled'
    else:
      warnings['LegacyEndpoints'] = 'Enabled'
