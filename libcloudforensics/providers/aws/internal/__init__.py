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
"""Exposed modules."""
from libcloudforensics.providers.aws.internal.account import AWSAccount
from libcloudforensics.providers.aws.internal.log import AWSCloudTrail
from libcloudforensics.providers.aws.internal.ebs import AWSVolume, AWSSnapshot
from libcloudforensics.providers.aws.internal.ec2 import AWSInstance
from libcloudforensics.providers.aws.internal.common import GetTagForResourceType, GetInstanceTypeByCPU, ReadStartupScript  # pylint: disable=line-too-long
