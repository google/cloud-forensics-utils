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
"""Kubernetes selector class structure."""

import abc
from collections import defaultdict
from typing import Dict


class K8sSelector:
  """Class to build K8s API selectors."""

  class Component(abc.ABC):
    """Component of the selector."""

    @abc.abstractmethod
    def ToString(self) -> str:
      """Builds the string of this selector component.

      Returns:
        str: The string of this selector component.
      """

    @property
    @abc.abstractmethod
    def keyword(self) -> str:
      """The keyword argument to which this selector component belongs."""

  class LabelComponent(Component, metaclass=abc.ABCMeta):
    """Selector component on labels."""

    @property
    def keyword(self) -> str:
      return 'label_selector'

  class FieldComponent(Component, metaclass=abc.ABCMeta):
    """Selector component on fields."""

    @property
    def keyword(self) -> str:
      return 'field_selector'

  class Name(FieldComponent):
    """Selector component having a particular name."""

    def __init__(self, name: str) -> None:
      self._name = name

    def ToString(self) -> str:
      return 'metadata.name={0:s}'.format(self._name)

  class Node(FieldComponent):
    """Selector component for being on a particular node."""

    def __init__(self, node: str) -> None:
      self._node = node

    def ToString(self) -> str:
      return 'spec.nodeName={0:s}'.format(self._node)

  class Running(FieldComponent):
    """Selector component for a running pod."""

    def ToString(self) -> str:
      return 'status.phase!=Failed,status.phase!=Succeeded'

  class Label(LabelComponent):
    """Selector component for a label's key-value pair."""

    def __init__(self, key: str, value: str) -> None:
      self._key = key
      self._value = value

    def ToString(self) -> str:
      return '{0:s}={1:s}'.format(self._key, self._value)

  def __init__(self, *selectors: Component) -> None:
    self._selectors = selectors

  def ToKeywords(self) -> Dict[str, str]:
    """Builds the keyword arguments to be passed to the K8s API.

    Returns:
      Dict[str, str]: The keyword arguments to be passed to a Kubernetes
          API call.
    """
    keywords = defaultdict(list)
    for selector in self._selectors:
      keywords[selector.keyword].append(selector.ToString())
    return {k: ','.join(vs) for k, vs in keywords.items()}

  @classmethod
  def FromLabelsDict(cls, labels: Dict[str, str]) -> 'K8sSelector':
    """Builds a selector from the given label key-value pairs.

    Args:
      labels (Dict[str, str]): The label key-value pairs.

    Returns:
      K8sSelector: The resulting selector object.
    """
    args = map(lambda k: K8sSelector.Label(k, labels[k]), labels)
    return cls(*args)
