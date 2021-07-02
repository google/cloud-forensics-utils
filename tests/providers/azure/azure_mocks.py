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
"""Azure mocks used across tests."""

import mock

from libcloudforensics.providers.azure.internal import account
from libcloudforensics.providers.azure.internal import compute
from libcloudforensics.providers.azure.internal import monitoring

RESOURCE_ID_PREFIX = ('/subscriptions/sub/resourceGroups/fake-resource-group'
                      '/providers/Microsoft.Compute/type/')

# pylint: disable=line-too-long
with mock.patch('libcloudforensics.providers.azure.internal.common.GetCredentials') as mock_creds:
  mock_creds.return_value = ('fake-subscription-id', mock.Mock())
  with mock.patch('libcloudforensics.providers.azure.internal.resource.AZResource.GetOrCreateResourceGroup') as mock_resource:
    # pylint: enable=line-too-long
    mock_resource.return_value = 'fake-resource-group'
    FAKE_ACCOUNT = account.AZAccount(
        'fake-resource-group',
        default_region='fake-region'
    )

FAKE_INSTANCE = compute.AZComputeVirtualMachine(
    FAKE_ACCOUNT,
    RESOURCE_ID_PREFIX + 'fake-vm-name',
    'fake-vm-name',
    'fake-region',
    ['fake-zone']
)

FAKE_DISK = compute.AZComputeDisk(
    FAKE_ACCOUNT,
    RESOURCE_ID_PREFIX + 'fake-disk-name',
    'fake-disk-name',
    'fake-region',
    ['fake-zone']
)

FAKE_BOOT_DISK = compute.AZComputeDisk(
    FAKE_ACCOUNT,
    RESOURCE_ID_PREFIX + 'fake-boot-disk-name',
    'fake-boot-disk-name',
    'fake-region',
    ['fake-zone']
)

FAKE_SNAPSHOT = compute.AZComputeSnapshot(
    FAKE_ACCOUNT,
    RESOURCE_ID_PREFIX + 'fake_snapshot_name',
    'fake_snapshot_name',
    'fake-region',
    FAKE_DISK
)

FAKE_MONITORING = monitoring.AZMonitoring(FAKE_ACCOUNT)

MOCK_INSTANCE = mock.Mock(
    id=RESOURCE_ID_PREFIX + 'fake-vm-name',
    location='fake-region',
    zones=['fake-zone']
)
# Name attributes for Mock objects have to be added in a separate statement,
# otherwise it becomes itself a mock object.
MOCK_INSTANCE.name = 'fake-vm-name'
MOCK_REQUEST_INSTANCES = [[MOCK_INSTANCE]]
MOCK_LIST_INSTANCES = {
    'fake-vm-name': FAKE_INSTANCE
}

MOCK_DISK = mock.Mock(
    id=RESOURCE_ID_PREFIX + 'fake-disk-name',
    location='fake-region',
    zones=['fake-zone']
)
MOCK_DISK.name = 'fake-disk-name'

MOCK_BOOT_DISK = mock.Mock(
    id=RESOURCE_ID_PREFIX + 'fake-boot-disk-name',
    location='fake-region',
    zones=['fake-zone']
)
MOCK_BOOT_DISK.name = 'fake-boot-disk-name'

MOCK_DISK_COPY = mock.Mock(
    id=RESOURCE_ID_PREFIX + 'fake_snapshot_name_f4c186ac_copy',
    location='fake-region',
    zones=['fake-zone']
)
MOCK_DISK_COPY.name = 'fake_snapshot_name_f4c186ac_copy'

MOCK_REQUEST_DISKS = [[MOCK_DISK, MOCK_BOOT_DISK]]
MOCK_LIST_DISKS = {
    'fake-disk-name': FAKE_DISK,
    'fake-boot-disk-name': FAKE_BOOT_DISK
}

MOCK_VM_SIZE = mock.Mock(
    number_of_cores=4,
    memory_in_mb=8192
)
MOCK_VM_SIZE.name = 'fake-vm-type'
MOCK_REQUEST_VM_SIZE = [MOCK_VM_SIZE]
MOCK_LIST_VM_SIZES = [{
    'Name': 'fake-vm-type',
    'CPU': 4,
    'Memory': 8192
}]

MOCK_ANALYSIS_INSTANCE = mock.Mock(
    id=RESOURCE_ID_PREFIX + 'fake-analysis-vm-name',
    location='fake-region',
    zones=['fake-zone']
)
MOCK_ANALYSIS_INSTANCE.name = 'fake-analysis-vm-name'

MOCK_LIST_IDS = [
    mock.Mock(subscription_id='fake-subscription-id-1'),
    mock.Mock(subscription_id='fake-subscription-id-2')
]

MOCK_STORAGE_ACCOUNT = mock.Mock(id='fakestorageid')

MOCK_LIST_KEYS = mock.Mock(
    keys=[mock.Mock(key_name='key1', value='fake-key-value')])

JSON_FILE = 'scripts/test_credentials.json'
STARTUP_SCRIPT = 'scripts/startup.sh'

MOCK_BLOB_PROPERTIES = mock.Mock()
MOCK_BLOB_PROPERTIES.copy = mock.Mock()
MOCK_BLOB_PROPERTIES.copy.status = 'success'

MOCK_METRICS = mock.Mock()
MOCK_METRICS.name = mock.Mock()
MOCK_METRICS.name.value = 'fake-metric'
MOCK_LIST_METRICS = [MOCK_METRICS]

MOCK_METRIC_OPERATION_VALUE = mock.Mock(timeseries=[mock.Mock(
    data=[mock.Mock(time_stamp='fake-time-stamp', total='fake-value')])])
MOCK_METRIC_OPERATION_VALUE.name = mock.Mock(value='fake-metric')
MOCK_METRIC_OPERATION = mock.Mock(value=[MOCK_METRIC_OPERATION_VALUE])

AZURE_CONFIG_DIR = 'scripts/test_azure_config_dir/'
EMPTY_AZURE_CONFIG_DIR = 'scripts/test_empty_azure_config_dir/'
