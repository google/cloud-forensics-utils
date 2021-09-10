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
"""Kubernetes volume class."""
from typing import Optional

from kubernetes import client


class K8sVolume:

  def __init__(self, response: client.V1Volume):
    self._response = response

  def Name(self):
    return self._response.name

  def Type(self) -> Optional[str]:
    # There is no attribute for a type, but rather the corresponding type
    # attribute is non-null. See:
    # https://github.com/kubernetes-client/python/blob/master/kubernetes/docs/V1Volume.md  # pylint: disable=line-too-long
    for k, v in self._response.to_dict().items():
      if v is not None and k is not 'name':
        return k
    return None

  def HostPath(self) -> Optional[str]:
    host_path = self._response.host_path
    return host_path.path if host_path is not None else None

  def IsRootMountedFilesystem(self):
    if self._response.host_path is not None:
      host_path = self._response.host_path
      return host_path.path == '/'
    else:
      return False