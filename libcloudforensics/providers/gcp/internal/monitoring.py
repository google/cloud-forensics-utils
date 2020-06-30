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
"""Google Cloud Monitoring functionality."""

import datetime
from typing import TYPE_CHECKING, Dict

from libcloudforensics.providers.gcp.internal import common

if TYPE_CHECKING:
  import googleapiclient


class GoogleCloudMonitoring:
  """Class to call Google Monitoring APIs.

  https://cloud.google.com/monitoring/api/ref_v3/rest/v3/projects.timeSeries

  Attributes:
    project_id: Project name.
    gcm_api_client: Client to interact with Monitoring APIs.
  """
  CLOUD_MONITORING_API_VERSION = 'v3'

  def __init__(self, project_id: str) -> None:
    """Initialize the GoogleCloudMonitoring object.

    Args:
      project_id (str): The name of the project.
    """

    self.gcm_api_client = None
    self.project_id = project_id

  def GcmApi(self) -> 'googleapiclient.discovery.Resource':
    """Get a Google Cloud Monitoring service object.

    Returns:
      googleapiclient.discovery.Resource: A Google Cloud Monitoring
          service object.
    """
    if self.gcm_api_client:
      return self.gcm_api_client
    self.gcm_api_client = common.CreateService(
        'monitoring', self.CLOUD_MONITORING_API_VERSION)
    return self.gcm_api_client

  def ActiveServices(self, timeframe: int = 30) -> Dict[str, int]:
    """List active services in the project (default: last 30 days).

    Args:
      timeframe (int): Optional. The number (in days) for
          which to measure activity.

    Returns:
      Dict[str, int]: Dictionary mapping service name to number of uses.
    """
    start_time = common.FormatRFC3339(
        datetime.datetime.utcnow() - datetime.timedelta(days=timeframe))
    end_time = common.FormatRFC3339(datetime.datetime.utcnow())
    period = timeframe * 24 * 60 * 60
    service = self.GcmApi()
    gcm_timeseries_client = service.projects().timeSeries()
    responses = common.ExecuteRequest(gcm_timeseries_client, 'list', {
        'name': 'projects/{0:s}'.format(self.project_id),
        'filter':
            'metric.type="serviceruntime.googleapis.com/api/request_count"',
        'interval_startTime': start_time,
        'interval_endTime': end_time,
        'aggregation_groupByFields': 'resource.labels.service',
        'aggregation_perSeriesAligner': 'ALIGN_SUM',
        'aggregation_alignmentPeriod': '{0:d}s'.format(period),
        'aggregation_crossSeriesReducer': 'REDUCE_SUM',
    })
    ret = {}
    for response in responses:
      for ts in response.get('timeSeries', []):
        service = ts.get('resource', {}).get('labels', {}).get('service', '')
        if service:
          points = ts.get('points', [])
          if points:
            val = points[0].get('value', {}).get('int64Value', '')
            if val:
              ret[service] = int(val)
    return ret
