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
"""Google BigQuery functionalities."""

from typing import TYPE_CHECKING, List, Dict, Any, Optional
from libcloudforensics.providers.gcp.internal import common

if TYPE_CHECKING:
  import googleapiclient.discovery

_BIGQUERY_API_VERSION = 'v2'

class GoogleBigQuery:
  """Class to call Google BigQuery APIs.

  Attributes:
    project_id: Google Cloud project ID.
  """

  def __init__(self, project_id: Optional[str] = None) -> None:
    """Initialize the GoogleBigQuery object.

    Args:
      project_id: Optional. Google Cloud project ID.
    """

    self.project_id = project_id

  def GoogleBigQueryApi(self) -> 'googleapiclient.discovery.Resource':
    """Get a Google BigQuery service object.

    Returns:
      A Google BigQuery service object.
    """

    return common.CreateService('bigquery', _BIGQUERY_API_VERSION)

  def ListBigQueryJobs(self) -> List[Dict[str, Any]]:
    """List jobs of Google BigQuery within a project.

    Returns:
      List of jobs.
    """
    bq_jobs = self.GoogleBigQueryApi().jobs()  # pylint: disable=no-member
    request = bq_jobs.list(projectId=self.project_id, projection='full')
    jobs: List[Dict[str, Any]] = request.execute().get('jobs', [])
    return jobs
