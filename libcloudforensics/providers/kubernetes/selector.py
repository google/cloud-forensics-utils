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
"""Kubernetes selector class structure."""

import abc
from collections import defaultdict
from typing import Dict

class K8sSelector:
  """Class to build K8s API selectors."""

  class Component(abc.ABC):
    """Component of the selector."""

    @abc.abstractmethod
    def ToString(self):
      """Builds the string of this selector component.

      Returns:
        str: The string of this selector component.
      """

    @property
    @abc.abstractmethod
    def Keyword(self):
      """Returns the keyword argument to which this selector component belongs.

      Returns:
        str: The keyword argument to which this component belongs.
      """

  class LabelComponent(Component, metaclass=abc.ABCMeta):

    @property
    def Keyword(self):
      return 'label_selector'

  class FieldComponent(Component, metaclass=abc.ABCMeta):

    @property
    def Keyword(self):
      return 'field_selector'

  class Name(FieldComponent):
    """Selector component for having a particular name."""

    def __init__(self, name: str):
      self.name = name

    def ToString(self):
      return 'metadata.name={0:s}'.format(self.name)

  class Node(FieldComponent):
    """Selector component for running on a particular node."""

    def __init__(self, node) -> None:
      self.node = node

    def ToString(self):
      return 'spec.nodeName={0:s}'.format(self.node)

  class Running(FieldComponent):
    """Selector component for a running pod."""

    def ToString(self):
      return 'status.phase!=Failed,status.phase!=Succeeded'

  class Label(LabelComponent):

    def __init__(self, key: str, value: str):
      self.key = key
      self.value = value

    def ToString(self):
      return '{0:s}={1:s}'.format(self.key, self.value)

  def __init__(self, *selectors: Component):
    self.selectors = selectors

  def ToKeywords(self) -> Dict[str, str]:
    """Builds the keyword arguments to be passed to the K8s API.

    Returns:
      Dict[str, str]: The keyword arguments to be passed to a Kubernetes
        API call.
    """
    keywords = defaultdict(list)
    for selector in self.selectors:
      keywords[selector.Keyword].append(selector.ToString())
    return {k: ','.join(vs) for k, vs in keywords.items()}

  @classmethod
  def FromLabelsDict(cls, labels: Dict[str, str]):
    """Builds a selector from the the given label key-value pairs.

    Args:
      labels (Dict[str, str]): The label key-value pairs.

    Returns:
      K8sSelector: The resulting selector object.
    """
    args = map(lambda k: K8sSelector.Label(k, labels[k]), labels)
    return cls(*args)
