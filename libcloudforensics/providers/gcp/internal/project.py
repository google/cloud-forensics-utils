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
"""Google Cloud Project resources and services."""

from __future__ import unicode_literals

from typing import Optional

import libcloudforensics.providers.gcp.internal.build as build_module
import libcloudforensics.providers.gcp.internal.compute as compute_module
import libcloudforensics.providers.gcp.internal.function as function_module
import libcloudforensics.providers.gcp.internal.gke as gke_module
import libcloudforensics.providers.gcp.internal.log as log_module
import libcloudforensics.providers.gcp.internal.monitoring as monitoring_module
import libcloudforensics.providers.gcp.internal.storage as storage_module


class GoogleCloudProject:
  """Class representing a Google Cloud Project.

  Attributes:
    project_id: Google Cloud project ID.
    default_zone: Default zone to create new resources in.

  Example use:
    gcp = GoogleCloudProject("your_project_name", "us-east")
    gcp.compute.ListInstances()
  """

  def __init__(self,
               project_id: str,
               default_zone: Optional[str] = None) -> None:
    """Initialize the GoogleCloudProject object.

    Args:
      project_id (str): The name of the project.
      default_zone (str): Optional. Default zone to create new resources in.
          None means GlobalZone.
    """

    self.project_id = project_id
    self.default_zone = default_zone
    self._compute = None  # type: Optional[compute_module.GoogleCloudCompute]
    self._function = None  # type: Optional[function_module.GoogleCloudFunction]
    self._gke = None  # type: Optional[gke_module.GoogleKubernetesEngine]
    self._build = None  # type: Optional[build_module.GoogleCloudBuild]
    self._log = None  # type: Optional[log_module.GoogleCloudLog]
    self._storage = None  # type: Optional[storage_module.GoogleCloudStorage]
    # pylint: disable=line-too-long
    self._monitoring = None  # type: Optional[monitoring_module.GoogleCloudMonitoring]
    # pylint: enable=line-too-long

  @property
  def compute(self) -> compute_module.GoogleCloudCompute:
    """Get a GoogleCloudCompute object for the project.

    Returns:
      GoogleCloudCompute: Object that represents Google Cloud Compute Engine.
    """

    if self._compute:
      return self._compute
    self._compute = compute_module.GoogleCloudCompute(
        self.project_id, self.default_zone)
    return self._compute

  @property
  def function(self) -> function_module.GoogleCloudFunction:
    """Get a GoogleCloudFunction object for the project.

    Returns:
      GoogleCloudFunction: Object that represents Google Cloud Function.
    """

    if self._function:
      return self._function
    self._function = function_module.GoogleCloudFunction(
        self.project_id)
    return self._function

  @property
  def gke(self) -> gke_module.GoogleKubernetesEngine:
    """Get a GoogleKubernetesEngine object for the project.

    Returns:
      GoogleKubernetesEngine: Object that represents Google Kubernetes Engine.
    """

    if self._gke:
      return self._gke
    self._gke = gke_module.GoogleKubernetesEngine()
    return self._gke

  @property
  def build(self) -> build_module.GoogleCloudBuild:
    """Get a GoogleCloudBuild object for the project.

    Returns:
      GoogleCloudBuild: Object that represents Google Cloud Build.
    """

    if self._build:
      return self._build
    self._build = build_module.GoogleCloudBuild(
        self.project_id)
    return self._build

  @property
  def log(self) -> log_module.GoogleCloudLog:
    """Get a GoogleCloudLog object for the project.

    Returns:
      GoogleCloudLog: Object that represents Google Cloud Logging.
    """

    if self._log:
      return self._log
    self._log = log_module.GoogleCloudLog(
        self.project_id)
    return self._log

  @property
  def storage(self) -> storage_module.GoogleCloudStorage:
    """Get a GoogleCloudStorage object for the project.

    Returns:
      GoogleCloudLog: Object that represents Google Cloud Logging.
    """

    if self._storage:
      return self._storage
    self._storage = storage_module.GoogleCloudStorage(
        self.project_id)
    return self._storage

  @property
  def monitoring(self) -> monitoring_module.GoogleCloudMonitoring:
    """Get a GoogleCloudMonitoring object for the project.

    Returns:
      GoogleCloudMonitoring: Object that represents Google Monitoring.
    """

    if self._monitoring:
      return self._monitoring
    self._monitoring = monitoring_module.GoogleCloudMonitoring(
        self.project_id)
    return self._monitoring
