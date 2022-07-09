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

from typing import Optional, Dict, Any
from google.auth import default

import libcloudforensics.providers.gcp.internal.build as build_module
import libcloudforensics.providers.gcp.internal.compute as compute_module
import libcloudforensics.providers.gcp.internal.function as function_module
import libcloudforensics.providers.gcp.internal.gke as gke_module
import libcloudforensics.providers.gcp.internal.log as log_module
import libcloudforensics.providers.gcp.internal.monitoring as monitoring_module
import libcloudforensics.providers.gcp.internal.storage as storage_module
import libcloudforensics.providers.gcp.internal.storagetransfer\
  as storagetransfer_module
import libcloudforensics.providers.gcp.internal.cloudsql as cloudsql_module
import libcloudforensics.providers.gcp.internal.cloudresourcemanager\
  as cloudresourcemanager_module
import libcloudforensics.providers.gcp.internal.serviceusage\
  as serviceusage_module
import libcloudforensics.providers.gcp.internal.bigquery as bigquery_module

class GoogleCloudProject:
  """Class representing a Google Cloud Project.

  Attributes:
    project_id: Google Cloud project ID.
    default_zone: Default zone to create new resources in.

  Example use:
    gcp = GoogleCloudProject("your_project_name", "us-east1-b")
    gcp.compute.ListInstances()
  """

  def __init__(self,
               project_id: Optional[str] = None,
               default_zone: str = 'us-central1-f') -> None:
    """Initialize the GoogleCloudProject object.

    Args:
      project_id (str): Optional. The name of the project. If not provided, we
          look in the default gcloud environment if a project is already set. If
          none is found, we raise an AttributeError.
      default_zone (str): Optional. Default zone to create new resources in.
          Default is 'us-central1-f'.

    Raises:
        AttributeError: If no project_id was provided and none was inferred
            from the gcloud environment.
    """
    if project_id:
      self.project_id = project_id
    else:
      _, project_id = default()
      if project_id:
        self.project_id = project_id
      else:
        raise AttributeError("No project_id was found. Either pass a project_id"
                             " to the function, or set one in your gcloud SDK: "
                             "`gcloud config set project project_id`")
    self.default_zone = default_zone
    self._compute = None  # type: Optional[compute_module.GoogleCloudCompute]
    self._function = None  # type: Optional[function_module.GoogleCloudFunction]
    self._gke = None  # type: Optional[gke_module.GoogleKubernetesEngine]
    self._build = None  # type: Optional[build_module.GoogleCloudBuild]
    self._log = None  # type: Optional[log_module.GoogleCloudLog]
    self._storage = None  # type: Optional[storage_module.GoogleCloudStorage]
    # pylint: disable=line-too-long
    self._storagetransfer = None  # type: Optional[storagetransfer_module.GoogleCloudStorageTransfer]
    self._monitoring = None  # type: Optional[monitoring_module.GoogleCloudMonitoring]
    self._cloudsql = None  # type: Optional[cloudsql_module.GoogleCloudSQL]
    self._cloudresourcemanager = None  # type: Optional[cloudresourcemanager_module.GoogleCloudResourceManager]
    self._serviceusage = None  # type: Optional[serviceusage_module.GoogleServiceUsage]
    # pylint: enable=line-too-long
    self._bigquery = None  # type: Optional[bigquery_module.GoogleBigQuery]


  def Delete(self) -> Dict[str, Any]:
    """Delete a GCP project.

    Returns:
      Dict[str, Any]: The operation's result details.
    """
    return self.cloudresourcemanager.DeleteResource("projects/{0:s}".format(
      self.project_id))

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
        [self.project_id])
    return self._log

  @property
  def storage(self) -> storage_module.GoogleCloudStorage:
    """Get a GoogleCloudStorage object for the project.

    Returns:
      GoogleCloudStorage: Object that represents Google Cloud Storage.
    """

    if self._storage:
      return self._storage
    self._storage = storage_module.GoogleCloudStorage(
        self.project_id)
    return self._storage

  @property
  def storagetransfer(self
    ) -> storagetransfer_module.GoogleCloudStorageTransfer:
    """Get a GoogleCloudStorageTransfer object for the project.

    Returns:
      GoogleCloudStorageTransfer: Object that represents Google Cloud Storage
      Transfer.
    """

    if self._storagetransfer:
      return self._storagetransfer
    self._storagetransfer = storagetransfer_module.GoogleCloudStorageTransfer(
        self.project_id)
    return self._storagetransfer

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

  @property
  def cloudsql(self) -> cloudsql_module.GoogleCloudSQL:
    """Get a GoogleCloudSql object for the project.

    Returns:
      GoogleCloudSql: Object that represents Google SQL.
    """

    if self._cloudsql:
      return self._cloudsql
    self._cloudsql = cloudsql_module.GoogleCloudSQL(
        self.project_id)
    return self._cloudsql

  @property
  def cloudresourcemanager(
      self) -> cloudresourcemanager_module.GoogleCloudResourceManager:
    """Get a GoogleCloudResourceManager object for the project.

    Returns:
      GoogleCloudResourceManager: Object that represents Google cloud resource
        manager.
    """

    if self._cloudresourcemanager:
      return self._cloudresourcemanager
    self._cloudresourcemanager = (
        cloudresourcemanager_module.GoogleCloudResourceManager(
            self.project_id))
    return self._cloudresourcemanager

  @property
  def serviceusage(self) -> serviceusage_module.GoogleServiceUsage:
    """Get a GoogleServiceUsage object for the project.

    Returns:
      GoogleServiceUsage: Object that represents Google service usage.
    """

    if self._serviceusage:
      return self._serviceusage
    self._serviceusage = serviceusage_module.GoogleServiceUsage(
        self.project_id)
    return self._serviceusage

  @property
  def bigquery(self) -> bigquery_module.GoogleBigQuery:
    """Get a GoogleBigQuery object for the project.

    Returns:
      GoogleBigQuery: Object that represents Google BigQuery.
    """

    if self._bigquery:
      return self._bigquery
    self._bigquery = bigquery_module.GoogleBigQuery(
      self.project_id
    )
    return self._bigquery
