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
"""Library for incident response operations on Google Cloud Compute Engine.

Library to make forensic images of Google Compute Engine disk and create
analysis virtual machine to be used in incident response.
"""

from __future__ import unicode_literals

from typing import Optional

import libcloudforensics.providers.gcp.internal.compute as compute_module
import libcloudforensics.providers.gcp.internal.function as function_module
import libcloudforensics.providers.gcp.internal.log as log_module
import libcloudforensics.providers.gcp.internal.build as build_module


class GoogleCloudProject:
  """Class representing a Google Cloud Project.

  Attributes:
    project_id: Project name.
    default_zone: Default zone to create new resources in.

  Example use:
    gcp = GoogleCloudProject("your_project_name", "us-east")
    gcp.ListInstances()
  """

  COMPUTE_ENGINE_API_VERSION = 'v1'

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
    self._compute = None
    self._function = None
    self._build = None
    self._log = None

  @property
  def compute(self) -> compute_module.GoogleCloudCompute:
    """Get a GoogleCloudCompute object for the project.

    Returns:
      GoogleCloudCompute: Object that represents Google Cloud Compute Engine.
    """

    if self._compute:
      return self._compute
    self._compute = compute_module.GoogleCloudCompute(  # type: ignore
        self.project_id, self.default_zone)
    return self._compute  # type: ignore

  @property
  def function(self) -> function_module.GoogleCloudFunction:
    """Get a GoogleCloudFunction object for the project.

    Returns:
      GoogleCloudFunction: Object that represents Google Cloud Function.
    """

    if self._function:
      return self._function
    self._function = function_module.GoogleCloudFunction(  # type: ignore
        self.project_id)
    return self._function  # type: ignore

  @property
  def build(self) -> build_module.GoogleCloudBuild:
    """Get a GoogleCloudBuild object for the project.

    Returns:
      GoogleCloudBuild: Object that represents Google Cloud Build.
    """

    if self._build:
      return self._build
    self._build = build_module.GoogleCloudBuild(  # type: ignore
        self.project_id)
    return self._build  # type: ignore

  @property
  def log(self) -> log_module.GoogleCloudLog:
    """Get a GoogleCloudLog object for the project.

    Returns:
      GoogleCloudLog: Object that represents Google Cloud Logging.
    """

    if self._log:
      return self._log
    self._log = log_module.GoogleCloudLog(  # type: ignore
        self.project_id)
    return self._log  # type: ignore
