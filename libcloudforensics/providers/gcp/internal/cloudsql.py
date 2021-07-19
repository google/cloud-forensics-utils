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
"""Google Cloud SQL functionalities."""

from typing import TYPE_CHECKING, List, Dict, Any, Optional
from libcloudforensics.providers.gcp.internal import common

if TYPE_CHECKING:
  import googleapiclient


class GoogleCloudSQL:
  """Class to call Google CloudSQL APIs.

  Attributes:
    project_id: Google Cloud project ID.
  """
  SQLADMIN_API_VERSION = 'v1beta4'

  def __init__(self, project_id: Optional[str] = None) -> None:
    """Initialize the GoogleCloudSQL object.

    Args:
      project_id (str): Optional. Google Cloud project ID.
    """

    self.project_id = project_id

  def GoogleCloudSQLApi(self) -> 'googleapiclient.discovery.Resource':
    """Get a Google CloudSQL service object.

    Returns:
      googleapiclient.discovery.Resource: A Google CloudSQL service object.
    """

    return common.CreateService(
        'sqladmin', self.SQLADMIN_API_VERSION)

  def ListCloudSQLInstances(self) -> List[Dict[str, Any]]:
    """List instances of Google CloudSQL within a project.

    Returns:
      List[Dict[str, Any]]: List of instances.
    """
    gcsql_instances = self.GoogleCloudSQLApi().instances() # pylint: disable=no-member
    request = gcsql_instances.list(project=self.project_id)
    instances = request.execute()  # type: Dict[str, Any]
    return instances.get('items', [])
