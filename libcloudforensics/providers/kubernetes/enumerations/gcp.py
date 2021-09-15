from typing import Any, Dict, Iterable, Optional

from libcloudforensics.providers.gcp.internal import gke
from libcloudforensics.providers.kubernetes.enumerations import base


class GkeClusterEnumeration(base.Enumeration[gke.GkeCluster]):

  def __init__(
      self, underlying_object: gke.GkeCluster,
      namespace: Optional[str] = None) -> None:
    """Builds a GkeClusterEnumeration.

    Args:
        underlying_object (T): The underlying object.
        namespace (str): Optional. The cluster namespace.
    """
    super().__init__(underlying_object)
    self.namespace = namespace

  @property
  def keyword(self) -> str:
    """Override of abstract property."""
    return 'GkeCluster'

  def Children(self) -> Iterable[base.Enumeration[Any]]:
    """Method override."""
    yield base.ClusterEnumeration(
        self._object.GetK8sCluster(), namespace=self.namespace)

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
