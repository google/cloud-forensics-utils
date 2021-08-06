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
"""Generic error wrapper"""

from libcloudforensics import logging_utils


class LCFError(Exception):
  """Class to represent a cloud-forensics-utils (CFU) error.

  Attributes:
    message (str): The error message.
    name (str): Name of the module that generated the error.
  """

  def __init__(self,
               message: str,
               name: str) -> None:
    """Initializes the CFUError with provided message.

    Args:
      message (str): The error message.
      name (str): The name of the module that generated the error.
    """
    super().__init__(message)
    self.message = message
    self.name = name
    logging_utils.SetUpLogger(self.name)
    logger = logging_utils.GetLogger(self.name)
    logger.error(self.message)


class CredentialsConfigurationError(LCFError):
  """Error when an issue with the credentials configuration is encountered."""


class InvalidFileFormatError(LCFError):
  """Error when an issue with file format is encountered."""


class InvalidNameError(LCFError):
  """Error when an issue with resource name is encountered."""


class ResourceNotFoundError(LCFError):
  """Error when an issue with non-existent resource is encountered."""


class ResourceCreationError(LCFError):
  """Error when an issue with creating a new resource is encountered."""


class ResourceDeletionError(LCFError):
  """Error when an issue with deleting a resource is encountered."""


class InstanceStateChangeError(LCFError):
  """Error when an issue with changing an instance state is encountered."""


class ServiceAccountRemovalError(LCFError):
  """Error when an issue with removing a service account is encountered."""


class InstanceProfileCreationError(LCFError):
  """Error when there is an issue creating an instance profile."""


class OperationFailedError(LCFError):
  """Error when an operation did not succeed."""


class TransferCreationError(LCFError):
  """Error when an issue with creating a new transfer job is encountered."""


class TransferExecutionError(LCFError):
  """Error when an issue with running a transfer job is encountered."""
