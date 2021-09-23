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
from typing import Any
from typing import Dict
from typing import Optional

from kubernetes import client


class K8sVolume:
  """Class wrapping a Kubernetes volume response."""

  def __init__(self, response: client.V1Volume):
    """Builds a K8sVolume object.

    Args:
      response (client.V1Volume): The Kubernetes Volume response object to wrap.
    """
    self._response = response

  def Name(self) -> str:
    """Returns the name of this volume.

    Returns:
      str: The name of this volume.
    """
    name = self._response.name  # type: str
    return name

  def Type(self) -> str:
    """Returns the type of this volume.

    Returns:
      str: The type of this volume.

    Raises:
      RuntimeError: If the type of this volume is not found.
    """
    # There is no attribute for a type, but rather the corresponding type
    # attribute is non-null.
    # https://github.com/kubernetes-client/python/blob/master/kubernetes/docs/V1Volume.md  # pylint: disable=line-too-long
    response_dict = self._response.to_dict()  # type: Dict[str, Any]
    for k, v in response_dict.items():
      if k != 'name' and v:
        return k
    raise RuntimeError('Volume type not found.')

  def HostPath(self) -> Optional[str]:
    """Returns the host path of this volume.

    Will return None if this volume is not hostPath type.

    Returns:
      Optional[str]: Returns the path if this is a hostPath volume, None
          otherwise
    """
    host_path = self._response.host_path
    return host_path.path if host_path else None

  def IsHostRootFilesystem(self) -> bool:
    """Returns True if this volume is the host's root filesystem.

    Returns:
      bool: True if this volume is the host's root filesystem, False otherwise.
    """
    return self.HostPath() == '/'
