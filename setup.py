#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2017 Google Inc.
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
"""This is the setup file for the project."""

# yapf: disable
import sys

from setuptools import find_packages
from setuptools import setup

# make sure libcloudforensics is in path
sys.path.insert(0, '.')

import libcloudforensics  # pylint: disable=wrong-import-position

description = (
    'libcloudforensics is a set of tools to help acquire forensic evidence from'
    ' cloud platforms.'
)


def parse_requirements(filename):
  with open(filename) as requirements:
    # Skipping -i https://pypi.org/simple
    return requirements.readlines()[1:]


setup(
    name='libcloudforensics',
    version=libcloudforensics.__version__,
    description=description,
    long_description=description,
    license='Apache License, Version 2.0',
    url='http://github.com/google/cloud-forensics-utils/',
    maintainer='Cloud-forensics-utils development team',
    maintainer_email='cloud-forensics-utils-dev@googlegroups.com',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    packages=find_packages(),
    include_package_data=True,
    package_data={
      'libcloudforensics': ['libcloudforensics/scripts/*']
    },
    entry_points={'console_scripts': [
        'libcloudforensics = examples.libcloudforensics:Main']},
    zip_safe=False,
    install_requires=[req for req in parse_requirements('requirements.txt')],
    tests_require=[req for req in parse_requirements('requirements-dev.txt')],
)
