import abc
import itertools
from collections import defaultdict
from typing import Generic, TypeVar, Iterable, Dict, Optional, Callable, Any

from libcloudforensics.providers.kubernetes import (
    base, cluster, container, volume)

T = TypeVar('T')


def _SafeMerge(*dicts: Dict):
  merged = {}
  for d in dicts:
    if merged.keys() & d.keys():
      raise ValueError('Overlapping keys.')
    merged.update(d)
  return merged


class Enumeration(Generic[T], metaclass=abc.ABCMeta):
  INDENT_STRING = '  '

  def __init__(self, starting_object: T):
    self._object = starting_object

  def Children(self) -> 'Iterable[Enumeration]':
    return []

  def __PrintTable(self, print_func: Callable[[str], Any]) -> None:
    # Filter out information for which the value is false
    info = {k: v for k, v in self.Information().items() if v}

    keylen = max(map(lambda k: len(str(k)), info), default=0)
    rows = []
    for k, v in info.items():
      key_str = str(k).ljust(keylen)
      val_str = str(v)
      rows.append('{0:s} : {1:s}'.format(key_str, val_str))
    sep = '-' * max(map(len, rows), default=5)
    print_func(sep)
    for row in rows:
      print_func(row)
    print_func(sep)

  def Enumerate(self, depth: int = 0):

    def output(t):
      return print(depth * self.INDENT_STRING + t)

    # Title
    output(self.keyword)
    self.__PrintTable(output)
    # Enumerate children
    children = list(self.Children())
    for i, child in enumerate(children):
      child.Enumerate(depth + 1)

  def ToJson(self):
    children_json = defaultdict(list)
    for child in self.Children():
      children_json[child.keyword].append(child.ToJson())
    return _SafeMerge(
        self.Information(),
        self.Warnings(),
        children_json,
    )

  def Information(self) -> Dict[str, str]:
    return {}

  def Warnings(self) -> Dict[str, str]:
    return {}

  @property
  @abc.abstractmethod
  def keyword(self) -> str:
    """"""


class ContainerEnumeration(Enumeration[container.K8sContainer]):

  @property
  def keyword(self) -> str:
    return 'Container'

  def Information(self) -> Dict[str, str]:
    return {
        'Name':
            self._object.Name(),
        'Image':
            self._object.Image(),
        'Mounts':
            ','.join(self._object.VolumeMounts()),
        'DeclaredPorts':
            ','.join(str(port) for port in self._object.ContainerPorts())
    }

  def Warnings(self) -> Dict[str, str]:
    warnings = {}
    if self._object.IsPrivileged():
      warnings['Privileged'] = 'Yes'
    return warnings


class VolumeEnumeration(Enumeration[volume.K8sVolume]):

  @property
  def keyword(self) -> str:
    return 'Volume'

  def Information(self) -> Dict[str, str]:
    return {
        'Name': self._object.Name(),
        'Type': self._object.Type(),
        'HostPath': self._object.HostPath()
    }


class PodsEnumeration(Enumeration[base.K8sPod]):

  @property
  def keyword(self) -> str:
    return 'Pod'

  def Children(self) -> 'Iterable[Enumeration]':
    return itertools.chain(
        map(ContainerEnumeration, self._object.ListContainers()),
        map(VolumeEnumeration, self._object.ListVolumes()))

  def Information(self) -> Dict[str, str]:
    return {
        'Name': self._object.name,
        'Namespace': self._object.namespace,
    }


class NodeEnumeration(Enumeration[base.K8sNode]):

  def __init__(self, starting_object: T, namespace: Optional[str] = None):
    super().__init__(starting_object)
    self.namespace = namespace

  @property
  def keyword(self) -> str:
    return 'Node'

  def Children(self) -> 'Iterable[PodsEnumeration]':
    return map(PodsEnumeration, self._object.ListPods(namespace=self.namespace))

  def Information(self) -> Dict[str, str]:
    return {
        'Name': self._object.name,
        'ExtIP': self._object.ExternalIP(),
        'IntIP': self._object.InternalIP(),
    }


class ClusterEnumeration(Enumeration[cluster.K8sCluster]):

  def __init__(self, starting_object: T, namespace: Optional[str] = None):
    super().__init__(starting_object)
    self.namespace = namespace

  @property
  def keyword(self) -> str:
    return 'Cluster'

  def Children(self) -> 'Iterable[NodeEnumeration]':
    for node in self._object.ListNodes():
      yield NodeEnumeration(node, namespace=self.namespace)
