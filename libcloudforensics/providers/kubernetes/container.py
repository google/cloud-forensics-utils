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
"""Kubernetes container class."""
from typing import List

from kubernetes import client


class K8sContainer:
  """Class wrapping a Kubernetes container response"""

  def __init__(self, response: client.V1Container):
    """Builds a K8sContainer object.

    Args:
      response (client.V1Container): The Kubernetes Container response object
          to be wrapped.
    """
    self._response = response

  def IsPrivileged(self) -> bool:
    """Returns True if this container is privileged, False otherwise.

    Returns:
      bool: True if this container is privileged, False otherwise.
    """
    security_context = self._response.security_context
    # Conversion to bool for mypy
    return bool(security_context and security_context.privileged)

  def Name(self) -> str:
    """Returns the name of this container.

    Returns:
      str: The name if this container.
    """
    name = self._response.name  # type: str
    return name

  def Image(self) -> str:
    """Returns the image of this container.

    Returns:
      str: The image of this container.
    """
    image = self._response.image  # type: str
    return image

  def ContainerPorts(self) -> List[int]:
    """Returns the ports listed for this container.

    Returns:
      List[int]: The ports listed for this container.
    """
    ports = [
        port.container_port for port in (self._response.ports or [])
    ]  # type: List[int]
    return ports

  def VolumeMounts(self) -> List[str]:
    """Returns the volumes mounted in this container.

    Returns:
      List[str]: The volumes mounted in this container.
    """
    volumes = [
        volume.name for volume in (self._response.volume_mounts or [])
    ]  # type: List[str]
    return volumes
