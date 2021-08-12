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
"""Kubernetes functionalities."""
import abc

import kubernetes.client


class K8sResource(abc.ABC):
  """Abstract class encompassing Kubernetes resources."""

  @abc.abstractmethod
  def _K8sApi(self) -> kubernetes.client.ApiClient:
    """Creates an authenticated Kubernetes API client.

    Returns:
      kubernetes.client.ApiClient: An authenticated client to
        the Kubernetes API server.
    """
