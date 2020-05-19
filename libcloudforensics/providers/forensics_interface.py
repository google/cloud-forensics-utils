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
"""Forensics interface - to be implemented by each cloud provider"""

from abc import abstractmethod


class Forensics:
  """Forensics interface to be implemented by cloud providers."""
  @abstractmethod
  def CreateDiskCopy(self, **kwargs):
    """Create a disk copy."""
    raise NotImplementedError

  @abstractmethod
  def StartAnalysisVm(self, **kwargs):
    """Start an analysis VM."""
    raise NotImplementedError
