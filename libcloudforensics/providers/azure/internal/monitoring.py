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

# Pylint complains about the import but the library imports just fine,
# so we can ignore the warning.
# pylint: disable=import-error
from azure.mgmt.monitor import MonitorManagementClient
# pylint: enable=import-error
from libcloudforensics.providers.azure.internal import account

if TYPE_CHECKING:
  from datetime import datetime


class AZMonitoring:
  """Azure Monitoring.

  Attributes:
    az_account (AZAccount): An Azure account object.
    monitoring_client (MonitorManagementClient): An Azure monitoring client
        object.
  """

  def __init__(self,
               az_account: account.AZAccount) -> None:
    """Initialize the Azure monitoring class.

    Args:
      az_account (AZAccount): An Azure account object.
    """
    self.az_account = az_account
    self.monitoring_client = MonitorManagementClient(
        self.az_account.credentials, self.az_account.subscription_id)

  def ListAvailableMetricsForResource(self, resource_id: str) -> List[str]:
    """List the available metrics for a given resource.

      Args:
        resource_id (str): The resource ID from which to list available
            metrics.

      Returns:
        List[str]: A list of metrics that can be queried for the resource ID.
    """
    return [metric.name.value for metric
            in self.monitoring_client.metric_definitions.list(resource_id)]

  def GetMetricsForResource(
      self,
      resource_id: str,
      metrics: str,
      from_date: Optional['datetime'] = None,
      to_date: Optional['datetime'] = None,
      interval: Optional[str] = None,
      aggregation: str = 'Total',
      qfilter: Optional[str] = None) -> Dict[str, List[str]]:
    """Retrieve metrics for a given resource.

    Args:
      resource_id (str): The resource ID for which to lookup the metric.
      metrics (str): A comma separated list of metrics to retrieve. E.g.
          'Percentage CPU,Network In'.
      from_date (datetime.datetime): Optional. A start date from which to get
          the metric. If passed, toDate is also required.
      to_date (datetime.datetime): Optional. An end date until which to get the
          metric. If passed, fromDate is also required.
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
      Dict[str, List[str]]]: A dictionary mapping the metric to a list of the
          metric's values.
    """
    kwargs = {'metricnames': metrics, 'aggregation': aggregation}
    if from_date and to_date:
      timespan = '{0:s}/{1:s}'.format(from_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
                                      to_date.strftime('%Y-%m-%dT%H:%M:%SZ'))
      kwargs['timespan'] = timespan
    if interval:
      kwargs['interval'] = interval
    metrics_data = self.monitoring_client.metrics.list(
        resource_id, filter=qfilter, **kwargs)
    results = {}  # type: Dict[str, List[str]]
    for metric in metrics_data.value:
      values = []
      for timeserie in metric.timeseries:
        for data in timeserie.data:
          if data.time_stamp and data.total:
            values.append('{0:s}: {1:s}'.format(str(data.time_stamp),
                                                str(data.total)))
      results[metric.name.value] = values
    return results
