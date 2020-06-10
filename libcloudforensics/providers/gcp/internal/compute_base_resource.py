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
"""Google Compute Engine resources."""

from typing import TYPE_CHECKING, Dict, Optional, Any

from libcloudforensics.providers.gcp.internal import common

if TYPE_CHECKING:
  import googleapiclient


class GoogleComputeBaseResource(common.GoogleCloudComputeClient):
  """Base class representing a Computer Engine resource.

  Attributes:
    project_id (str): Google Cloud project ID.
    zone (str): What zone the resource is in.
    name (str): Name of the resource.
    labels (Dict): Dictionary of labels for the resource, if existing.
  """

  def __init__(self,
               project_id: str,
               zone: str,
               name: str,
               labels: Optional[Dict[str, Any]] = None) -> None:
    """Initialize the Google Compute Resource base object.

    Args:
      project_id (str): Google Cloud project ID.
      zone (str): What zone the resource is in.
      name (str): Name of the resource.
      labels (Dict): Dictionary of labels for the resource, if existing.
    """

    self.zone = zone
    self.name = name
    self.labels = labels
    self._data = None
    self.project_id = project_id  # type: str
    super(GoogleComputeBaseResource, self).__init__(self.project_id)

  def FormatLogMessage(self, message: str) -> str:
    """Format log messages with project specific information.

    Args:
      message (str): Message string to log.

    Returns:
      str: Formatted log message string.
    """

    return 'project:{0} {1}'.format(self.project_id, message)

  def GetValue(self, key: str) -> str:
    """Get specific value from the resource key value store.

    Args:
      key (str): A key of type String to get key's corresponding value.

    Returns:
      str: Value of key or None if key is missing.
    """

    # pylint: disable=no-member
    self._data = self.GetOperation()  # type: ignore
    return self._data.get(key)  # type: ignore

  def GetSourceString(self) -> str:
    """API URL to the resource.

    Returns:
      str: The full API URL to the resource.
    """

    if self._data:
      return self._data['selfLink']
    return self.GetValue('selfLink')

  def GetResourceType(self) -> str:
    """Get the resource type from the resource key-value store.

    Returns:
      str: Resource Type which is a string with one of the following values:
          compute#instance
          compute#disk
          compute#Snapshot
    """

    if self._data:
      return self._data['kind']
    return self.GetValue('kind')

  def FormOperation(
      self,
      operation_name: str) -> 'googleapiclient.discovery.Resource':
    """Form an API operation object for the compute resource.

    Example:[RESOURCE].FormOperation('setLabels')(**kwargs)
    [RESOURCE] can be type "instance", disk or "Snapshot".

    Args:
      operation_name (str): The name of the API operation you need to perform.

    Returns:
      googleapiclient.discovery.Resource: An API operation object for the
          referenced compute resource.

    Raises:
      RuntimeError: If resource type is not defined as a type which
          extends the GoogleComputeBaseResource class.
    """

    resource_type = self.GetResourceType()
    module = None
    if resource_type not in ['compute#instance', 'compute#Snapshot',
                             'compute#disk']:
      error_msg = (
          'Compute resource Type {0:s} is not one of the defined '
          'types in libcloudforensics library '
          '(Instance, Disk or Snapshot).').format(resource_type)
      raise RuntimeError(error_msg)
    if resource_type == 'compute#instance':
      module = self.GceApi().instances()
    elif resource_type == 'compute#disk':
      module = self.GceApi().disks()
    elif resource_type == 'compute#Snapshot':
      module = self.GceApi().snapshots()

    operation_func_to_call = getattr(module, operation_name)
    return operation_func_to_call

  def GetLabels(self) -> Dict[str, Any]:
    """Get all labels of a compute resource.

    Returns:
      Dict: A dictionary of all labels.
    """

    # pylint: disable=no-member
    operation = self.GetOperation()  # type: ignore
    return operation.get('labels')  # type: ignore

  def AddLabels(self,
                new_labels_dict: Dict[str, Any],
                blocking_call: Optional[bool] = False) -> Optional[Any]:
    """Add or update labels of a compute resource.

    Args:
      new_labels_dict (Dict): A dictionary containing the labels to be added,
          ex:{"incident_id": "1234abcd"}.
      blocking_call (bool): Optional. A boolean to decide whether the API call
          should be blocking or not, default is False.

    Returns:
      Optional[Any]: The response of the API operation (a Dict if the call is
          successful).

    Raises:
      RuntimeError: If the Compute resource Type is not one of instance,
          disk or snapshot.
    """

    # pylint: disable=no-member
    get_operation = self.GetOperation()  # type: ignore
    label_fingerprint = get_operation['labelFingerprint']

    existing_labels_dict = {}
    if self.GetLabels() is not None:
      existing_labels_dict = self.GetLabels()
    existing_labels_dict.update(new_labels_dict)
    labels_dict = existing_labels_dict
    request_body = {
        'labels': labels_dict,
        'labelFingerprint': label_fingerprint
    }

    resource_type = self.GetResourceType()
    response = None
    if resource_type not in ['compute#instance', 'compute#Snapshot',
                             'compute#disk']:
      error_msg = (
          'Compute resource Type {0:s} is not one of the defined '
          'types in libcloudforensics library '
          '(Instance, Disk or Snapshot) ').format(resource_type)
      raise RuntimeError(error_msg)
    if resource_type == 'compute#instance':
      response = self.FormOperation('setLabels')(
          instance=self.name, project=self.project_id, zone=self.zone,
          body=request_body).execute()
    elif resource_type == 'compute#disk':
      response = self.FormOperation('setLabels')(
          resource=self.name, project=self.project_id, zone=self.zone,
          body=request_body).execute()
    elif resource_type == 'compute#Snapshot':
      response = self.FormOperation('setLabels')(
          resource=self.name, project=self.project_id,
          body=request_body).execute()
    if blocking_call:
      self.BlockOperation(response, zone=self.zone)  # type: ignore

    return response
