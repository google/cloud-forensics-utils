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
import logging
from collections import defaultdict
from typing import Any, Callable, Dict, Generic, Iterable, Optional, Tuple, \
  TypeVar

from libcloudforensics import logging_utils
from libcloudforensics.providers.kubernetes import base
from libcloudforensics.providers.kubernetes import cluster
from libcloudforensics.providers.kubernetes import container
from libcloudforensics.providers.kubernetes import services
from libcloudforensics.providers.kubernetes import volume

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)

ObjT = TypeVar('ObjT')

KeyT = TypeVar('KeyT')
ValT = TypeVar('ValT')


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
      underlying_object (ObjT): The underlying object of this enumeration.
    """
    self._object = underlying_object

  def _Children(
      self,
      namespace: Optional[str] = None  # pylint: disable=unused-argument
  ) -> Iterable['Enumeration[Any]']:
    """Returns the child enumerations of this enumeration.

    Args:
      namespace (str): Optional. The namespace in which to generate child
          enumerations.

    Returns:
      Iterable[Enumeration[Any]]: An iterable of child enumerations of this
          enumeration.
    """
    # Default is no children. To be overridden in subclasses.
    return []

  def _Populate(self, info: Dict[str, Any], warnings: Dict[str, Any]) -> None:
    """Populates the information and warning dictionaries.

    Abstract method to be overridden in subclasses.

    Args:
      info (Dict[str, Any]): The (empty) information dictionary to be populated
          with information about the underlying object's details.
      warnings (Dict[str, Any]): The (emtpy) warning dictionary to be populated
          with warnings about the underlying object. These warnings will be
          highlighted in the enumeration.
    """
    # Default is not populating the info/warning dicts. To be overridden in
    # subclasses.

  def __PrintTable(
      self, print_func: Callable[[str, int], None], filter_empty: bool) -> None:
    """Displays the table of information and warnings to the user.

    Args:
      print_func (Callable[[str, int], None]): A printing function, typically
          already with the required indent.
      filter_empty (bool): Filter for information/warning entries that have a
          non-empty value.
    """
    info, warnings = self._GetInformationAndWarnings(filter_empty=filter_empty)

    key_max_len = max(map(len, info.keys() | warnings.keys()), default=-1)
    if key_max_len == -1:
      # Nothing to display, info and warnings were both empty
      print_func('-', logging.INFO)
      return

    def MakeRow(_item: Tuple[str, Any]) -> str:
      """Creates a row from a key-value pair.

      Args:
        _item (Tuple[str, str]): The key-value pair.

      Returns:
        str: The created row.
      """
      return '{0:s} : {1!s}'.format(_item[0].ljust(key_max_len), _item[1])

    row_max_len = max(
        len(MakeRow(item))
        for item in (list(info.items()) + list(warnings.items())))
    separator = '-' * row_max_len

    print_func(separator, logging.INFO)
    for info_item in info.items():
      print_func(MakeRow(info_item), logging.INFO)
    for warning_item in warnings.items():
      print_func(MakeRow(warning_item), logging.WARNING)
    print_func(separator, logging.INFO)

  def Enumerate(
      self,
      namespace: Optional[str] = None,
      filter_empty: bool = True,
      silent: bool = False,
      _print_func: Optional[Callable[[str, int], None]] = None) -> str:
    """Enumerates the object and its children to the user.

    Args:
      namespace (str): Optional. The namespace in which to enumerate. If
          unspecified (None), enumerates in all namespaces.
      filter_empty (bool): Optional. Whether or not to filter out information
          lines for which the value is empty. Defaults to True.
      silent (bool): Optional. If True, the output from the enumeration is not
          logged to stdout.
      _print_func (Callable[[str, int], None]): Optional. The function to use
          for displaying and registering the enumeration text. Only to be used
          internally.

    Returns:
      str: The intercepted enumeration text.
    """

    rows = []

    def PrintFunc(text: str, level: int) -> None:
      """Displays and registers the given text.

      Args:
        text (str): The text to be displayed and registered.
        level (int): The log level of the text.
      """
      rows.append(text)
      if not silent:
        logger.log(level, text)

    print_func: Callable[[str, int], None]
    if _print_func is None:
      print_func = PrintFunc
    else:
      print_func = _print_func

    def ChildPrintFunc(text: str, level: int) -> None:
      """Wraps the current _print_func with an indent.

      Args:
        text (str): The text to be displayed and registered.
        level (int): The log level of the text.
      """
      print_func(self._INDENT_STRING + text, level)

    print_func(self.keyword, logging.INFO)
    self.__PrintTable(print_func, filter_empty)
    for child in self._Children(namespace=namespace):
      child.Enumerate(
          namespace=namespace,
          filter_empty=filter_empty,
          _print_func=ChildPrintFunc)

    return '\n'.join(rows)

  def ToJson(self, namespace: Optional[str] = None) -> Dict[str, Any]:
    """Converts the enumeration to a JSON object.

    Args:
      namespace (str): Optional. The namespace in which to enumerate a JSON
          object.

    Returns:
      Dict[str, Any]: This enumeration as a JSON object.
    """
    children_by_keyword = defaultdict(list)
    for child in self._Children(namespace=namespace):
      children_by_keyword[child.keyword].append(
          child.ToJson(namespace=namespace))
    info, warnings = self._GetInformationAndWarnings()
    return _SafeMerge(info, warnings, children_by_keyword)

  def _GetInformationAndWarnings(
      self,
      filter_empty: bool = False) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Gets the populated information and warning dictionaries.

    Args:
      filter_empty (bool): Optional. If True, filters out the entries in the
          dictionaries that have an empty value.

    Returns:
      Tuple[Dict[str, Any], Dict[str, Any]]: The populated information and
          warnings pair.
    """
    info = {}  # type: Dict[str, Any]
    warnings = {}  # type: Dict[str, Any]
    self._Populate(info, warnings)
    if filter_empty:
      info = _FilterEmptyValues(info)
      warnings = _FilterEmptyValues(warnings)
    return info, warnings

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

  def _Populate(self, info: Dict[str, Any], warnings: Dict[str, Any]) -> None:
    """Method override."""
    info.update({
        'Name': self._object.Name(),
        'Image': self._object.Image(),
        'Mounts': self._object.VolumeMounts(),
    })
    (warnings if self._object.IsPrivileged() else
     info)['Privileged'] = self._object.IsPrivileged()
    warnings['DeclaredPorts'] = self._object.ContainerPorts()


class VolumeEnumeration(Enumeration[volume.K8sVolume]):
  """Enumeration for a Kubernetes volume."""

  @property
  def keyword(self) -> str:
    """Override of abstract property."""
    return 'Volume'

  def _Populate(self, info: Dict[str, Any], warnings: Dict[str, Any]) -> None:
    """Method override."""
    info.update({
        'Name': self._object.Name(),
    })
    (warnings if self._object.Type() in {'host_path', 'secret'} else
     info)['Type'] = self._object.Type()
    (warnings if self._object.IsHostRootFilesystem() else
     info)['HostPath'] = self._object.HostPath()


class PodsEnumeration(Enumeration[base.K8sPod]):
  """Enumeration for a Kubernetes pod."""

  @property
  def keyword(self) -> str:
    """Override of abstract property."""
    return 'Pod'

  def _Children(self,
                namespace: Optional[str] = None) -> Iterable[Enumeration[Any]]:
    """Method override."""
    return itertools.chain(
        map(ContainerEnumeration, self._object.ListContainers()),
        map(VolumeEnumeration, self._object.ListVolumes()))

  def _Populate(self, info: Dict[str, Any], warnings: Dict[str, Any]) -> None:
    """Method override."""
    info.update({
        'Name': self._object.name,
        'Namespace': self._object.namespace,
        'NodeName': self._object.GetNode().name,
    })


class NodeEnumeration(Enumeration[base.K8sNode]):
  """Enumeration for a Kubernetes node."""

  @property
  def keyword(self) -> str:
    """Override of abstract property"""
    return 'Node'

  def _Children(self,
                namespace: Optional[str] = None) -> Iterable[Enumeration[Any]]:
    """Method override."""
    return map(PodsEnumeration, self._object.ListPods(namespace=namespace))

  def _Populate(self, info: Dict[str, Any], warnings: Dict[str, Any]) -> None:
    """Method override."""
    info.update({
        'Name': self._object.name,
        'ExternalIPs': self._object.ExternalIps(),
        'InternalIPs': self._object.InternalIps(),
    })


class ClusterEnumeration(Enumeration[cluster.K8sCluster]):
  """Enumeration for a Kubernetes cluster."""

  @property
  def keyword(self) -> str:
    """Override of abstract property."""
    return 'KubernetesCluster'

  def _Children(self,
                namespace: Optional[str] = None) -> Iterable[Enumeration[Any]]:
    """Method override."""
    for node in self._object.ListNodes():
      yield NodeEnumeration(node)


class WorkloadEnumeration(Enumeration[base.K8sWorkload]):
  """Enumeration of a Kubernetes workload."""

  @property
  def keyword(self) -> str:
    """Override of abstract property."""
    return 'Workload'

  def _Children(self,
                namespace: Optional[str] = None) -> Iterable[Enumeration[Any]]:
    """Method override."""
    return map(PodsEnumeration, self._object.GetCoveredPods())

  def _Populate(self, info: Dict[str, Any], warnings: Dict[str, Any]) -> None:
    """Method override."""
    info.update({
        'Name': self._object.name,
        'Namespace': self._object.namespace,
    })


class ServiceEnumeration(Enumeration[services.K8sService]):
  """Enumeration for a Kubernetes service."""

  @property
  def keyword(self) -> str:
    """Override of abstract property."""
    return 'Service'

  def _Children(self,
                namespace: Optional[str] = None) -> Iterable[Enumeration[Any]]:
    """Method override."""
    return map(PodsEnumeration, self._object.GetCoveredPods())

  def _Populate(self, info: Dict[str, Any], warnings: Dict[str, Any]) -> None:
    """Method override."""
    info.update({
        'Name': self._object.name,
        'Namespace': self._object.namespace,
    })
    (warnings if self._object.Type() == 'LoadBalancer' else
     info)['Type'] = self._object.Type()
    info['ExternalIPs'] = self._object.ExternalIps()
    info['ClusterIP'] = self._object.ClusterIp()
