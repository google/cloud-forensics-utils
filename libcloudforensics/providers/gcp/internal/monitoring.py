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
from typing import TYPE_CHECKING, Dict, List, Optional, Any

from libcloudforensics.providers.gcp.internal import common

if TYPE_CHECKING:
  import googleapiclient


class GoogleCloudMonitoring:
  """Class to call Google Monitoring APIs.

  https://cloud.google.com/monitoring/api/ref_v3/rest/v3/projects.timeSeries

  Attributes:
    project_id: Project name.
  """
  CLOUD_MONITORING_API_VERSION = 'v3'

  def __init__(self, project_id: str) -> None:
    """Initialize the GoogleCloudMonitoring object.

    Args:
      project_id (str): The name of the project.
    """

    self.project_id = project_id

  def GcmApi(self) -> 'googleapiclient.discovery.Resource':
    """Get a Google Cloud Monitoring service object.

    Returns:
      googleapiclient.discovery.Resource: A Google Cloud Monitoring
          service object.
    """
    return common.CreateService(
        'monitoring', self.CLOUD_MONITORING_API_VERSION)

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
    gcm_timeseries_client = service.projects().timeSeries() # pylint: disable=no-member
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


  def GetNetworkData(
      self, instance_ids: Optional[List[str]] = None,
      days: int = 2) -> List[Dict[str, Any]]:
    """Returns outbound network metrics for compute instances.

    By default returns usage for the last two days for the given instance.

    Args:
      instance_ids list[str]: Optional. A list of instance IDs to collect
        metrics for. When not provided will collect metrics for all instances
        in the project.
      days (int): Optional. The number of days to collect metrics for.

    Returns:
      List[Dict[str, Any]]: a list of network usage for each instance
      in the format
        [
          {
            'instance_name': str,
            'network_usage':
            [
              {
                'timestamp': str,
                'bytes': float
              },
            ]
          },
        ]
    """
    service = self.GcmApi()
    gcm_timeseries_client = service.projects().timeSeries() # pylint: disable=no-member
    start_time = common.FormatRFC3339(
        datetime.datetime.utcnow() - datetime.timedelta(days=days))
    end_time = common.FormatRFC3339(datetime.datetime.utcnow())

    network_filter = [
        'metric.type=',
        '"compute.googleapis.com/instance/network/sent_bytes_count" ',
        'resource.type="gce_instance"'
    ]

    if instance_ids:
      network_filter.append(
          ' AND (resource.label.instance_id = "{0:s}"'.format(instance_ids[0]))
      if len(instance_ids) > 1:
        for instance_name in instance_ids[1:]:
          network_filter.append(
              ' OR resource.label.instance_id = "{0:s}"'.format(instance_name))

    responses = common.ExecuteRequest(
        gcm_timeseries_client,
        'list',
        {
            'name': 'projects/{0:s}'.format(self.project_id),
            'filter': ''.join(network_filter),
            'interval_startTime': start_time,
            'interval_endTime': end_time,
            'aggregation_groupByFields': 'metadata.system_labels.name',
            'aggregation_alignmentPeriod': '60s',
            'aggregation_perSeriesAligner': 'ALIGN_RATE',
            'aggregation_crossSeriesReducer': 'REDUCE_SUM'
        })

    network_data = []

    for response in responses:
      time_series = response.get('timeSeries', [])
      for ts in time_series:
        instance_name = response['timeSeries'][0]['metadata'][
            'systemLabels']['name']
        points = ts['points']
        data = []
        for point in points:
          data.append({
              'timestamp': point['interval']['startTime'],
              'bytes': point['value']['doubleValue']})

        network_data.append({
            'instance_name': instance_name,
            'network_usage': data})

    return network_data

  def _BuildUsageFilter(
      self, metric_type: str, instance_ids: Optional[List[str]]) -> str:
    """Builds a metrics query filter based on a list of instance IDs.

    Args:
      metric_type str: the type of metric to filter on.
      instance_ids list[str]: a list of instance ids.

    Returns:
      str: the filter to use in a metrics query.
    """
    instances_filter = (
          ['metric.type = "{0:s}"'.format(metric_type)])
    if instance_ids:
      instances_filter.append(
          ' AND (resource.label.instance_id = "{0:s}"'.format(instance_ids[0]))
      if len(instance_ids) > 1:
        for instance_name in instance_ids[1:]:
          instances_filter.append(
              ' OR resource.label.instance_id = "{0:s}"'.format(instance_name))
      instances_filter.append(')')

    return ''.join(instances_filter)

  def GetCpuUsage(self,
    instance_ids: Optional[List[str]] = None,
    days: int = 7,
    aggregation_minutes: int = 60
    ) -> List[Dict[str, Any]]:
    """Returns CPU usage metrics for compute instances.

    By default returns hourly usage for the last seven days for all instances
    within a project.

    Args:
      instance_ids list[str]: Optional. A list of instance IDs to collect
        metrics for. When not provided will collect metrics for all instances
        in the project.
      days (int): Optional. The number of days to collect metrics for.
      aggregation_minutes (int): Optional. The minutes to aggregate on.

    Returns:
      List[Dict[str, Any]]: a list of CPU usage for each instance in the format
        [
          {
            'instance_name': str,
            'instance_id': str,
            'cpu_usage':
            [
              {
                'timestamp': str,
                'cpu_usage': float
              },
            ]
          },
        ]
    """
    service = self.GcmApi()
    gcm_timeseries_client = service.projects().timeSeries() # pylint: disable=no-member

    start_time = common.FormatRFC3339(
        datetime.datetime.utcnow() - datetime.timedelta(days=days))
    end_time = common.FormatRFC3339(datetime.datetime.utcnow())
    period = aggregation_minutes * 60
    instance_filter = self._BuildUsageFilter(
      'compute.googleapis.com/instance/cpu/utilization', instance_ids)

    responses = common.ExecuteRequest(gcm_timeseries_client, 'list', {
        'name': 'projects/{0:s}'.format(self.project_id),
        'filter': instance_filter,
        'interval_startTime': start_time,
        'interval_endTime': end_time,
        'view': 'FULL',
        'aggregation_perSeriesAligner': 'ALIGN_MEAN',
        'aggregation_alignmentPeriod': '{0:d}s'.format(period),
    })

    cpu_usage_instances = []

    for response in responses:
      time_series = response.get('timeSeries', [])
      for ts in time_series:
        instance_name = ts['metric']['labels']['instance_name']
        instance_id = ts['resource']['labels']['instance_id']
        points = ts['points']
        cpu_usage = []
        for point in points:
          cpu_usage.append({
              'timestamp': point['interval']['startTime'],
              'cpu_usage': point['value']['doubleValue']})

        cpu_usage_instances.append({
            'instance_name': instance_name,
            'instance_id': instance_id,
            'cpu_usage': cpu_usage})

    return cpu_usage_instances

  def GetInstanceGPUUsage(
      self,
      instance_ids: Optional[List[str]] = None,
      days: int = 7) -> List[Dict[str, Any]]:
    """Returns GPU usage metrics for compute instances.

    By default returns minute-wise usage for the last seven days for all
    instances within a project.

    Args:
      instance_ids list[str]: Optional. A list of instance IDs to collect
        metrics for. When not provided will collect metrics for all instances
        in the project.
      days (int): Optional. The number of days to collect metrics for.

    Returns:
      List[Dict[str, Any]]: a list of GPU usage for each instance in the format
        [
          {
            'gpu_name': str,
            'instance_id': str,
            'gpu_usage':
            [
              {
                'timestamp': str,
                'gpu_usage': float
              },
            ]
          },
        ]
    """
    service = self.GcmApi()
    gcm_timeseries_client = service.projects().timeSeries() # pylint: disable=no-member
    start_time = common.FormatRFC3339(
        datetime.datetime.utcnow() - datetime.timedelta(days=days))
    end_time = common.FormatRFC3339(datetime.datetime.utcnow())

    instance_filter = self._BuildUsageFilter(
        'agent.googleapis.com/gpu/utilization" resource.type="gce_instance',
        instance_ids)

    responses = common.ExecuteRequest(
        gcm_timeseries_client,
        'list',
        {
            'name':
                'projects/{0:s}'.format(self.project_id),
            'filter':
                instance_filter,
            'interval_startTime':
                start_time,
            'interval_endTime':
                end_time
        })

    gpu_usage_instances = []

    for response in responses:
      time_series = response.get('timeSeries', [])
      for ts in time_series:
        if ts['metric'].get('labels', None):
          gpu_name = "{0:s} ({1:s})".format(
              ts['metric']['labels']['model'],
              ts['metric']['labels']['gpu_number'])
        instance_id = ts['resource']['labels']['instance_id']
        points = ts['points']
        gpu_usage = []
        all_points_zero = True
        for point in points:
          gpu_usage.append({
              'timestamp': point['interval']['startTime'],
              'gpu_usage': point['value']['doubleValue']})
          if point['value']['doubleValue'] != 0:
            all_points_zero = False

        if not all_points_zero:
          gpu_usage_instances.append({
              'gpu_name': gpu_name,
              'instance_id': instance_id,
              'gpu_usage': gpu_usage})

    return gpu_usage_instances

  def GetNodeAccelUsage(self, days: int = 7) -> List[Dict[str, Any]]:
    """Returns GPU usage metrics for GKE nodes.

    By default returns minute-wise usage for the last seven days for all
    GKE nodes within a project.

    Args:
      days (int): Optional. The number of days to collect metrics for.

    Returns:
      List[Dict[str, Any]]: a list of GPU usage for each instance in the format
        [
          {
            'gpu_name': str,
            'cluster_name': str,
            'container_name': str,
            'pod_name': str,
            'gpu_usage':
            [
              {
                'timestamp': str,
                'gpu_usage': float
              },
            ]
          },
        ]
    """
    service = self.GcmApi()
    gcm_timeseries_client = service.projects().timeSeries() # pylint: disable=no-member

    start_time = common.FormatRFC3339(
        datetime.datetime.utcnow() - datetime.timedelta(days=days))
    end_time = common.FormatRFC3339(datetime.datetime.utcnow())

    responses = common.ExecuteRequest(
        gcm_timeseries_client,
        'list',
        {
            'name':
                'projects/{0:s}'.format(self.project_id),
            'filter':
                'metric.type="kubernetes.io/container/accelerator/duty_cycle" '
                'resource.type="k8s_container"',
            'interval_startTime':
                start_time,
            'interval_endTime':
                end_time
        })

    gpu_usage_instances = []

    for response in responses:
      time_series = response.get('timeSeries', [])
      for ts in time_series:
        gpu_name = ts['metric']['labels']['model']
        cluster_name = ts['resource']['labels']['cluster_name']
        container_name = ts['resource']['labels']['container_name']
        pod_name = ts['resource']['labels']['pod_name']
        points = ts['points']
        gpu_usage = []
        all_points_zero = True
        for point in points:
          gpu_usage.append({
              'timestamp': point['interval']['startTime'],
              'gpu_usage': point['value']['int64Value']})
          if point['value']['int64Value'] != 0:
            all_points_zero = False

        if not all_points_zero:
          gpu_usage_instances.append({
              'gpu_name': gpu_name,
              'cluster_name': cluster_name,
              'container_name': container_name,
              'pod_name': pod_name,
              'gpu_usage': gpu_usage})

    return gpu_usage_instances
