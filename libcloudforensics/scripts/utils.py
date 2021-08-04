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
from typing import Optional

FORENSICS_STARTUP_SCRIPT = 'forensics_packages_startup.sh'
FORENSICS_STARTUP_SCRIPT_AWS = 'forensics_packages_startup_aws.sh'
FORENSICS_STARTUP_SCRIPT_GCP = FORENSICS_STARTUP_SCRIPT
FORENSICS_STARTUP_SCRIPT_AZ = FORENSICS_STARTUP_SCRIPT
EBS_SNAPSHOT_COPY_SCRIPT_AWS = 'ebs_snapshot_copy_aws.sh'

def ReadStartupScript(filename: Optional[str] = '') -> str:
  """Read and return the startup script that is to be run on the forensics VM.

  Users can either write their own script to install custom packages,
  or use one of the provided ones. To use your own script, export a
  STARTUP_SCRIPT environment variable with the absolute path to it:
  "user@terminal:~$ export STARTUP_SCRIPT='absolute/path/script.sh'"

  Args:
    filename (str): the name of the script in the scripts directory to read
      Defaults to 'forensics_packages_startup.sh' if none specified.
  Returns:
    str: The script to run.

  Raises:
    OSError: If the script cannot be opened, read or closed.
  """

  try:
    script_path = None
    if not filename:
      script_path = os.environ.get('STARTUP_SCRIPT')
    if not script_path:
      # Use the provided script
      script_path = os.path.join(
          os.path.dirname(os.path.realpath(__file__)),
          filename or FORENSICS_STARTUP_SCRIPT)
    with open(script_path) as startup_script:
      return startup_script.read()
  except OSError as exception:
    raise OSError(
        'Could not open/read/close the startup script {0:s}: {1:s}'.format(
            script_path, str(exception))) from exception
