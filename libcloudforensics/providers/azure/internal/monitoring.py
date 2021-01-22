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
"""Azure Monitoring functionality."""

from typing import List, Optional, Dict, TYPE_CHECKING

from azure.mgmt.monitor import MonitorManagementClient
from azure.core.exceptions import HttpResponseError

if TYPE_CHECKING:
  # TYPE_CHECKING is always False at runtime, therefore it is safe to ignore
  # the following cyclic import, as it it only used for type hints
  from libcloudforensics.providers.azure.internal import account  # pylint: disable=cyclic-import
  from datetime import datetime


class AZMonitoring:
  """Azure Monitoring.

  Attributes:
    monitoring_client (MonitorManagementClient): An Azure monitoring client
        object.
  """

  def __init__(self,
               az_account: 'account.AZAccount') -> None:
    """Initialize the Azure monitoring class.

    Args:
      az_account (AZAccount): An Azure account object.
    """
    self.monitoring_client = MonitorManagementClient(
        az_account.credentials, az_account.subscription_id)

  def ListAvailableMetricsForResource(self, resource_id: str) -> List[str]:
    """List the available metrics for a given resource.

      Args:
        resource_id (str): The resource ID from which to list available
            metrics.

      Returns:
        List[str]: A list of metrics that can be queried for the resource ID.

      Raises:
        RuntimeError: If the resource could not be found.
    """
    try:
      return [metric.name.value for metric
              in self.monitoring_client.metric_definitions.list(resource_id)]
    except HttpResponseError as exception:
      raise RuntimeError(
          'Could not fetch metrics for resource {0:s}. Please make sure you '
          'specified the full resource ID url, i.e. /subscriptions/<>/'
          'resourceGroups/<>/providers/<>/<>/yourResourceName'.format(
              resource_id)) from exception

  def GetMetricsForResource(
      self,
      resource_id: str,
      metrics: str,
      from_date: Optional['datetime'] = None,
      to_date: Optional['datetime'] = None,
      interval: Optional[str] = None,
      aggregation: str = 'Total',
      qfilter: Optional[str] = None) -> Dict[str, Dict[str, str]]:
    """Retrieve metrics for a given resource.

    Args:
      resource_id (str): The resource ID for which to lookup the metric.
      metrics (str): A comma separated list of metrics to retrieve. E.g.
          'Percentage CPU,Network In'.
      from_date (datetime.datetime): Optional. A start date from which to get
          the metric. If passed, to_date is also required.
      to_date (datetime.datetime): Optional. An end date until which to get the
          metric. If passed, from_date is also required.
      interval (str): An interval for the metrics, e.g. 'PT1H' will output
          metric's values with one hour granularity.
      aggregation (str): Optional. The type of aggregation for the metric's
          values. Default is 'Total'. Possible values: 'Total', 'Average'.
          Both can be retrieved if passed as a single string, separated by a
          comma.
      qfilter (str): Optional. A filter for the query. See
          https://docs.microsoft.com/en-us/rest/api/monitor/metrics/list for
          details about filtering.

    Returns:
      Dict[str, Dict[str, str]]: A dictionary mapping the metric to a dict of
          the metric's values, per timestamp.

    Raises:
        RuntimeError: If the resource could not be found.
    """
    kwargs = {'metricnames': metrics, 'aggregation': aggregation}
    if from_date and to_date:
      timespan = '{0:s}/{1:s}'.format(from_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
                                      to_date.strftime('%Y-%m-%dT%H:%M:%SZ'))
      kwargs['timespan'] = timespan
    if interval:
      kwargs['interval'] = interval
    try:
      metrics_data = self.monitoring_client.metrics.list(
          resource_id, filter=qfilter, **kwargs)
    except HttpResponseError as exception:
      raise RuntimeError(
          'Could not fetch metrics {0:s} for resource {1:s}.  Please make '
          'sure you specified the full resource ID  url, i.e. /subscriptions/'
          '<>/resourceGroups/<>/providers/<>/<>/yourResourceName'.format(
              metrics, resource_id)) from exception
    results = {}  # type: Dict[str, Dict[str, str]]
    for metric in metrics_data.value:
      values = {}
      for timeserie in metric.timeseries:
        for data in timeserie.data:
          if data.time_stamp and data.total:
            values[str(data.time_stamp)] = str(data.total)
      results[metric.name.value] = values
    return results
