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
"""Module for enumeration objects."""

import abc
import itertools
from collections import defaultdict
from typing import Any, Callable, Dict, Generic, Iterable, Optional, TypeVar, \
  Tuple, List

from libcloudforensics import logging_utils
from libcloudforensics.providers.kubernetes import base
from libcloudforensics.providers.kubernetes import cluster
from libcloudforensics.providers.kubernetes import container
from libcloudforensics.providers.kubernetes import volume
from libcloudforensics.providers.kubernetes import workloads

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)

ObjT = TypeVar('ObjT')

KeyT = TypeVar('KeyT')
ValT = TypeVar('ValT')

def _Underline(text: str) -> str:
  """Underlines given text.

  Args:
    text (str): The text to be underlined.

  Returns:
    str: The underlined text.
  """
  return ''.join('\u0332{0:s}'.format(char) for char in text)

def _Bold(text: str) -> str:
  """Adds ANSI escape codes to text so that it is displayed in bold.

  Args:
    text (str): The text to be put in bold.

  Returns:
    str: The text with bold escape codes.
  """
  return '\033[1m{0:s}\033[0m'.format(text)


def _SafeMerge(*dictionaries: Dict[KeyT, ValT]) -> Dict[KeyT, ValT]:
  """Merges given dictionaries, checking if there are overlapping keys.

  Args:
    *dictionaries (Dict[KeyT, ValT]): The dictionaries to be merged.

  Returns:
    Dict[KeyT, ValT]: The resulting merged dictionary.

  Raises:
    ValueError: If keys are overlapping.
  """
  merged = {}  # type: Dict[KeyT, ValT]
  for d in dictionaries:
    if merged.keys() & d.keys():
      raise ValueError('Overlapping keys.')
    merged.update(d)
  return merged


def _FilterEmptyValues(dictionary: Dict[KeyT, ValT]) -> Dict[KeyT, ValT]:
  """Returns a dictionary with only the pairs whose value evaluated to True.

  Args:
    dictionary (Dict[KeyT, ValT]): The dictionary to be filtered.

  Returns:
    Dict[KeyT, ValT]: A resulting dictionary containing only entries whose
        values evaluated to True.
  """
  return {k: v for k, v in dictionary.items() if v}


class Enumeration(Generic[ObjT], metaclass=abc.ABCMeta):
  """Abstract base class for enumerations.

  Attributes:
    keyword (str): The keyword describing the underlying of object of this
        enumeration.
  """

  _INDENT_STRING = '    '

  def __init__(self, underlying_object: ObjT) -> None:
    """Builds an Enumeration object.

    Args:
      underlying_object (T): The underlying object of this enumeration.
    """
    self._object = underlying_object

  def Children(self) -> Iterable['Enumeration[Any]']:
    """Returns the child enumerations of this enumeration.

    Returns:
      Iterable[Enumeration[Any]]: An iterable of child enumerations of this
          enumeration.
    """
    # Default is no children. To be overridden in subclasses.
    return []

  def __PrintTable(
      self, print_func: Callable[[str], None], filter_empty: bool) -> None:
    """Displays the table of information and warnings to the user.

    Args:
      print_func (Callable[[str], None]): A printing function, typically
          already with the required indent.
      filter_empty (bool): Filter for information/warning entries that have a
          non-empty value.
    """
    # Minimize what's displayed. These aren't merged into one same dictionary
    # to enable different formatting for warnings and information.
    info = {
        k: v for k, v in self.Information().items() if not filter_empty or v
    }
    warnings = {
        k: v for k, v in self.Warnings().items() if not filter_empty or v
    }

    key_len = max(map(len, info.keys() | warnings.keys()), default=-1)
    if key_len == -1:
      # Nothing to display, info and warnings were both empty
      print_func('-')
      return

    row_max_len = 0

    def MakeRow(kv: Tuple[str, str]) -> str:
      """Creates a row from a key-value pair and updates row_max_len.

      Args:
        kv (Tuple[str, str]): The key-value pair.

      Returns:
        str: The created row.
      """
      nonlocal row_max_len
      k, v = kv
      key_str = str(k).ljust(key_len)
      val_str = str(v)
      row_str = '{0:s} : {1:s}'.format(key_str, val_str)
      row_max_len = max(row_max_len, len(row_str))
      return row_str

    rows = []  # type: List[str]
    rows.extend(MakeRow(item) for item in info.items())
    rows.extend(_Underline(MakeRow(item)) for item in warnings.items())

    sep = '-' * row_max_len
    print_func(sep)
    for row in rows:
      print_func(row)
    print_func(sep)

  def Enumerate(self, depth: int = 0, filter_empty: bool = True) -> None:
    """Enumerates the object and its children to the user.

    Args:
      depth (int): The current depth of the enumeration, determining how to
          indent the enumeration output.
      filter_empty (bool): Optional. Whether or not to filter out information
          lines for which the value is empty. Defaults to True.
    """

    def PrintFunc(text: str) -> None:
      """Displays the text to the user with the appropriate indent.

      Args:
        text (str): The text to be displayed.
      """
      logger.info(depth * self._INDENT_STRING + text)

    PrintFunc(_Bold(self.keyword))
    self.__PrintTable(PrintFunc, filter_empty)
    for child in self.Children():
      child.Enumerate(depth=depth + 1, filter_empty=filter_empty)

  def ToJson(self) -> Dict[str, Any]:
    """Converts the enumeration to a JSON object.

    Returns:
      Dict[str, Any]: This enumeration as a JSON object.
    """
    children_by_keyword = defaultdict(list)
    for child in self.Children():
      children_by_keyword[child.keyword].append(child.ToJson())
    return _SafeMerge(self.Information(), self.Warnings(), children_by_keyword)

  def Information(self) -> Dict[str, Any]:
    """Returns information about the underlying object in a key-value format.

    Returns:
      Dict[str, Any]: Information about the underlying object in a key-value
          format.
    """
    return {}

  def Warnings(self) -> Dict[str, Any]:
    """Returns warnings about the underlying object in a key-value format.

    Returns:
      Dict[str, Any]: Warnings about the underlying object, in a key-value
          format.
    """
    return {}

  @property
  @abc.abstractmethod
  def keyword(self) -> str:
    """The keyword describing the underlying object."""


class ContainerEnumeration(Enumeration[container.K8sContainer]):
  """Enumeration for a Kubernetes container."""

  @property
  def keyword(self) -> str:
    """Override of abstract property."""
    return 'Container'

  def Information(self) -> Dict[str, Any]:
    """Method override."""
    return {
        'Name': self._object.Name(),
        'Image': self._object.Image(),
        'Mounts': self._object.VolumeMounts(),
        'DeclaredPorts': self._object.ContainerPorts(),
    }

  def Warnings(self) -> Dict[str, Any]:
    """Method override."""
    warnings = {}
    if self._object.IsPrivileged():
      warnings['Privileged'] = 'Yes'
    return warnings


class VolumeEnumeration(Enumeration[volume.K8sVolume]):
  """Enumeration for a Kubernetes volume."""

  @property
  def keyword(self) -> str:
    """Override of abstract property."""
    return 'Volume'

  def Information(self) -> Dict[str, Any]:
    """Method override."""
    return {
        'Name': self._object.Name(),
        'Type': self._object.Type(),
        'HostPath': self._object.HostPath()
    }


class PodsEnumeration(Enumeration[base.K8sPod]):
  """Enumeration for a Kubernetes pod."""

  @property
  def keyword(self) -> str:
    """Override of abstract property."""
    return 'Pod'

  def Children(self) -> Iterable[Enumeration[Any]]:
    """Method override."""
    return itertools.chain(
        map(ContainerEnumeration, self._object.ListContainers()),
        map(VolumeEnumeration, self._object.ListVolumes()))

  def Information(self) -> Dict[str, Any]:
    """Method override."""
    return {
        'Name': self._object.name,
        'Namespace': self._object.namespace,
        'Node': self._object.GetNode().name,
    }


class NodeEnumeration(Enumeration[base.K8sNode]):
  """Enumeration for a Kubernetes node."""

  def __init__(
      self, underlying_object: base.K8sNode,
      namespace: Optional[str] = None) -> None:
    """Builds a NodeEnumeration.

    Args:
      underlying_object (T): The underlying object of this enumeration.
      namespace (str): Optional. The namespace in which to list the child
          pods of this enumeration.
    """
    super().__init__(underlying_object)
    self.namespace = namespace

  @property
  def keyword(self) -> str:
    """Override of abstract property"""
    return 'Node'

  def Children(self) -> Iterable[Enumeration[Any]]:
    """Method override."""
    return map(PodsEnumeration, self._object.ListPods(namespace=self.namespace))

  def Information(self) -> Dict[str, Any]:
    """Method override."""
    return {
        'Name': self._object.name,
        'ExtIP': self._object.ExternalIP(),
        'IntIP': self._object.InternalIP(),
    }


class ClusterEnumeration(Enumeration[cluster.K8sCluster]):
  """Enumeration for a Kubernetes cluster."""

  def __init__(
      self,
      underlying_object: cluster.K8sCluster,
      namespace: Optional[str] = None) -> None:
    """Builds a ClusterEnumeration.

    Args:
        underlying_object (T): The underlying object of this enumeration.
        namespace (str): Optional. The namespace in which to list the child
            nodes of this enumeration.
    """
    super().__init__(underlying_object)
    self.namespace = namespace

  @property
  def keyword(self) -> str:
    """Override of abstract property."""
    return 'KubernetesCluster'

  def Children(self) -> Iterable[Enumeration[Any]]:
    """Method override."""
    for node in self._object.ListNodes():
      yield NodeEnumeration(node, namespace=self.namespace)


class WorkloadEnumeration(Enumeration[workloads.K8sWorkload]):
  """Enumeration of a Kubernetes workload."""

  @property
  def keyword(self) -> str:
    """Override of abstract property."""
    return 'Workload'

  def Children(self) -> Iterable[Enumeration[Any]]:
    """Method override."""
    return map(PodsEnumeration, self._object.GetCoveredPods())

  def Information(self) -> Dict[str, Any]:
    """Method override."""
    return {
        'Name': self._object.name,
        'Namespace': self._object.namespace,
    }
