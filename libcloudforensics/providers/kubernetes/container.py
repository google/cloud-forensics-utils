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

from kubernetes import client

class K8sContainer:

  def __init__(self, response: client.V1Container):
    self._response = response

  def IsPrivileged(self):
    security_context = self._response.security_context
    return security_context is not None and security_context.privileged

  def Name(self):
    return self._response.name

  def Image(self):
    return self._response.image

  def ContainerPorts(self):
    return [port.container_port
            for port in (self._response.ports or [])]

  def VolumeMounts(self):
    return [volume.name
            for volume in (self._response.volume_mounts or [])]