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
"""AWS mocks used across tests."""

import mock

from libcloudforensics.providers.aws.internal import account, ebs, ec2
from libcloudforensics.providers.aws.internal import log as aws_log

with mock.patch('boto3.session.Session._setup_loader') as mock_session:
  mock_session.return_value = None
  FAKE_AWS_ACCOUNT = account.AWSAccount(
      default_availability_zone='fake-zone-2b')

FAKE_INSTANCE = ec2.AWSInstance(
    FAKE_AWS_ACCOUNT,
    'fake-instance-id',
    'fake-zone-2',
    'fake-zone-2b')

FAKE_INSTANCE_WITH_NAME = ec2.AWSInstance(
    FAKE_AWS_ACCOUNT,
    'fake-instance-with-name-id',
    'fake-zone-2',
    'fake-zone-2b',
    name='fake-instance')

FAKE_VOLUME = ebs.AWSVolume(
    'fake-volume-id',
    FAKE_AWS_ACCOUNT,
    'fake-zone-2',
    'fake-zone-2b',
    False)

FAKE_BOOT_VOLUME = ebs.AWSVolume(
    'fake-boot-volume-id',
    FAKE_AWS_ACCOUNT,
    'fake-zone-2',
    'fake-zone-2b',
    False,
    name='fake-boot-volume',
    device_name='/dev/spf')

FAKE_SNAPSHOT = ebs.AWSSnapshot(
    'fake-snapshot-id',
    FAKE_AWS_ACCOUNT,
    'fake-zone-2',
    'fake-zone-2b',
    FAKE_VOLUME,
    name='fake-snapshot')

FAKE_CLOUDTRAIL = aws_log.AWSCloudTrail(FAKE_AWS_ACCOUNT)

FAKE_EVENT_LIST = [
    {'EventId': '474e8265-9180-4407-a5c9-f3a86d8bb1f0',
     'EventName': 'CreateUser', 'ReadOnly': 'false'},
    {'EventId': '474e8395-9122-4407-a3b9-f3a77d8aa1f0',
     'EventName': 'AddUserToGroup', 'ReadOnly': 'false'},
]

MOCK_DESCRIBE_INSTANCES = {
    'Reservations': [{
        'Instances': [{
            'InstanceId': FAKE_INSTANCE.instance_id,
            'Placement': {
                'AvailabilityZone': FAKE_INSTANCE.availability_zone
            },
            'State': {
                'Name': 'running'
            }
        }]
    }]
}

MOCK_DESCRIBE_INSTANCES_TAGS = {
    'Reservations': [{
        'Instances': [{
            'InstanceId': FAKE_INSTANCE_WITH_NAME.instance_id,
            'Placement': {
                'AvailabilityZone': FAKE_INSTANCE_WITH_NAME.availability_zone
            },
            'State': {
                'Name': 'running'
            },
            'Tags': [{
                'Key': 'Name',
                'Value': FAKE_INSTANCE_WITH_NAME.name
            }]
        }]
    }]
}

MOCK_DESCRIBE_IMAGES = {
    'Images' : [
        {'Name': 'Ubuntu 18.04 LTS', 'Public': True},
        {'Name': 'Ubuntu 18.04 with GUI', 'Public': False}
    ]
}

MOCK_DESCRIBE_VOLUMES = {
    'Volumes': [{
        'VolumeId': FAKE_VOLUME.volume_id,
        'AvailabilityZone': FAKE_VOLUME.availability_zone,
        'Encrypted': FAKE_VOLUME.encrypted,
        'Attachments': []
    }, {
        'VolumeId': FAKE_BOOT_VOLUME.volume_id,
        'AvailabilityZone': FAKE_BOOT_VOLUME.availability_zone,
        'Encrypted': FAKE_BOOT_VOLUME.encrypted,
        'Attachments': []
    }]
}

MOCK_DESCRIBE_VOLUMES_TAGS = {
    'Volumes': [{
        'VolumeId': FAKE_BOOT_VOLUME.volume_id,
        'AvailabilityZone': FAKE_BOOT_VOLUME.availability_zone,
        'Encrypted': FAKE_BOOT_VOLUME.encrypted,
        'Attachments': [{
            'State': 'attached',
            'Device': FAKE_BOOT_VOLUME.device_name
        }],
        'Tags': [{
            'Key': 'Name',
            'Value': FAKE_BOOT_VOLUME.name
        }]
    }]
}

MOCK_LIST_INSTANCES = {
    FAKE_INSTANCE.instance_id: FAKE_INSTANCE,
    FAKE_INSTANCE_WITH_NAME.instance_id: FAKE_INSTANCE_WITH_NAME
}

MOCK_LIST_VOLUMES = {
    FAKE_VOLUME.volume_id: FAKE_VOLUME,
    FAKE_BOOT_VOLUME.volume_id: FAKE_BOOT_VOLUME
}

MOCK_CREATE_VOLUME = {
    'VolumeId': 'fake-volume-from-snapshot-id',
    'AvailabilityZone': FAKE_SNAPSHOT.availability_zone,
    'Encrypted': False
}

MOCK_CREATE_SNAPSHOT = {
    'SnapshotId': FAKE_SNAPSHOT.snapshot_id
}

MOCK_CALLER_IDENTITY = {
    'UserId': 'fake-user-id',
    'Account': 'fake-account-id'
}

MOCK_DESCRIBE_AMI = {
    'Images': [{
        'BlockDeviceMappings': [{
            'Ebs': {
                'VolumeSize': None,
                'VolumeType': None
            }
        }]
    }]
}

MOCK_RUN_INSTANCES = {
    'Instances': [{
        'InstanceId': 'new-instance-id'
    }]
}

MOCK_EVENT_LIST = {
    'Events': FAKE_EVENT_LIST
}
