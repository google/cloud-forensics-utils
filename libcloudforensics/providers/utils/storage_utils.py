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
"""Cross-provider functionalities."""


from typing import Tuple


def SplitStoragePath(path: str) -> Tuple[str, str]:
  """Split a path to bucket name and object URI.

  Args:
    path (str): File path to a resource in GCS.
        Ex: gs://bucket/folder/obj

  Returns:
    Tuple[str, str]: Bucket name. Object URI.
  """

  _, _, full_path = path.partition('//')
  bucket, _, object_uri = full_path.partition('/')
  return bucket, object_uri
