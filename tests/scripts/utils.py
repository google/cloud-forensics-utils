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
"""Utils test methods"""
import json
import os
from typing import List, Dict


def ReadProjectInfo(keys: List[str]) -> Dict[str, str]:
  """Read project information to run e2e test.

  Args:
    keys (List[str]): A list of mandatory dictionary keys that are expected
        to be present in the project_info file.

  Returns:
    dict: A dict with the project information.

  Raises:
    OSError: If the file cannot be found, opened or closed.
    RuntimeError: If the json file cannot be parsed.
    ValueError: If the json file does not have the required properties.
  """
  project_info_path = os.environ.get('PROJECT_INFO')
  if project_info_path is None:
    raise OSError(
        'Please make sure that you defined the '
        '"PROJECT_INFO" environment variable pointing '
        'to your project settings.')
  try:
    json_file = open(project_info_path)
    try:
      project_info = json.load(json_file)  # type: Dict[str, str]
    except ValueError as exception:
      raise RuntimeError(
          'Cannot parse JSON file. {0:s}'.format(str(exception)))
    json_file.close()
  except OSError as exception:
    raise OSError(
        'Could not open/close file {0:s}: {1:s}'.format(
            project_info_path, str(exception)))

  if not all(key in project_info for key in keys):
    raise ValueError(
        'Please make sure that your JSON file '
        'has the required entries. The file should '
        'contain at least the following: {0:s}'.format(', '.join(keys)))
  return project_info
