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
"""Utils method for cloud providers"""

import os

STARTUP_SCRIPT = 'startup.sh'


def ReadStartupScript() -> str:
  """Read and return the startup script that is to be run on the forensics VM.

  Users can either write their own script to install custom packages,
  or use the provided one. To use your own script, export a STARTUP_SCRIPT
  environment variable with the absolute path to it:
  "user@terminal:~$ export STARTUP_SCRIPT='absolute/path/script.sh'"

  Returns:
    str: The script to run.

  Raises:
    OSError: If the script cannot be opened, read or closed.
  """

  try:
    script_path = os.environ.get('STARTUP_SCRIPT')
    if not script_path:
      # Use the provided script
      script_path = os.path.join(
          os.path.dirname(os.path.realpath(__file__)), STARTUP_SCRIPT)
    startup_script = open(script_path)
    script = startup_script.read()
    startup_script.close()
    return script
  except OSError as exception:
    raise OSError(
        'Could not open/read/close the startup script {0:s}: {1:s}'.format(
            script_path, str(exception)))
