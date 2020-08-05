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
"""Tests for the azure module."""
import os
import typing
import unittest
import mock

from azure.mgmt.compute.v2020_05_01 import models  # pylint: disable=import-error

from libcloudforensics.providers.azure.internal import account, compute, common, monitoring  # pylint:disable=line-too-long
from libcloudforensics.providers.azure import forensics

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


class TestAccount(unittest.TestCase):
  """Test Azure account class."""
  # pylint: disable=line-too-long

  @mock.patch('libcloudforensics.providers.azure.internal.common.ExecuteRequest')
  @typing.no_type_check
  def testListInstances(self, mock_request):
    """Test that instances of an account are correctly listed."""
    mock_request.return_value = MOCK_REQUEST_INSTANCES

    # If we don't specify a resource group name, the 'list_all' method should
    # be called.
    instances = FAKE_ACCOUNT.compute.ListInstances()
    mock_request.assert_called_with(mock.ANY, 'list_all')
    self.assertEqual(1, len(instances))
    self.assertIn('fake-vm-name', instances)
    instance = instances['fake-vm-name']
    self.assertEqual('fake-vm-name', instance.name)
    self.assertEqual(
        '/subscriptions/sub/resourceGroups/fake-resource-group'
        '/providers/Microsoft.Compute/type/fake-vm-name', instance.resource_id)
    self.assertEqual('fake-resource-group', instance.resource_group_name)
    self.assertEqual('fake-region', instance.region)
    self.assertEqual(['fake-zone'], instance.zones)

    # If we specify a resource group name, the 'list' method should be called.
    FAKE_ACCOUNT.compute.ListInstances(
        resource_group_name=instance.resource_group_name)
    mock_request.assert_called_with(
        mock.ANY, 'list', {'resource_group_name': instance.resource_group_name})

  @mock.patch('libcloudforensics.providers.azure.internal.common.ExecuteRequest')
  @typing.no_type_check
  def testListDisks(self, mock_request):
    """Test that disks of an account are correctly listed."""
    mock_request.return_value = MOCK_REQUEST_DISKS

    # If we don't specify a resource group name, the 'list' method should be
    # called.
    disks = FAKE_ACCOUNT.compute.ListDisks()
    mock_request.assert_called_with(mock.ANY, 'list')
    self.assertEqual(2, len(disks))
    self.assertIn('fake-disk-name', disks)
    disk = disks['fake-disk-name']
    self.assertEqual('fake-disk-name', disk.name)
    self.assertEqual(
        '/subscriptions/sub/resourceGroups/fake-resource-group'
        '/providers/Microsoft.Compute/type/fake-disk-name', disk.resource_id)
    self.assertEqual('fake-resource-group', disk.resource_group_name)
    self.assertEqual('fake-region', disk.region)
    self.assertEqual(['fake-zone'], disk.zones)

    # If we specify a resource group name, the 'list_by_resource_group' method
    # should be called.
    FAKE_ACCOUNT.compute.ListDisks(resource_group_name=disk.resource_group_name)
    mock_request.assert_called_with(
        mock.ANY,
        'list_by_resource_group',
        {'resource_group_name': disk.resource_group_name})

  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZCompute.ListInstances')
  @typing.no_type_check
  def testGetInstance(self, mock_list_instances):
    """Test that a particular instance from an account is retrieved."""
    mock_list_instances.return_value = MOCK_LIST_INSTANCES
    instance = FAKE_ACCOUNT.compute.GetInstance('fake-vm-name')
    self.assertEqual('fake-vm-name', instance.name)
    self.assertEqual(
        '/subscriptions/sub/resourceGroups/fake-resource-group'
        '/providers/Microsoft.Compute/type/fake-vm-name', instance.resource_id)
    self.assertEqual('fake-resource-group', instance.resource_group_name)
    self.assertEqual('fake-region', instance.region)
    self.assertEqual(['fake-zone'], instance.zones)

  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZCompute.ListDisks')
  @typing.no_type_check
  def testGetDisk(self, mock_list_disks):
    """Test that a particular disk from an account is retrieved."""
    mock_list_disks.return_value = MOCK_LIST_DISKS
    disk = FAKE_ACCOUNT.compute.GetDisk('fake-disk-name')
    self.assertEqual('fake-disk-name', disk.name)
    self.assertEqual(
        '/subscriptions/sub/resourceGroups/fake-resource-group'
        '/providers/Microsoft.Compute/type/fake-disk-name', disk.resource_id)
    self.assertEqual('fake-resource-group', disk.resource_group_name)
    self.assertEqual('fake-region', disk.region)
    self.assertEqual(['fake-zone'], disk.zones)

  @mock.patch('azure.mgmt.compute.v2020_05_01.operations._disks_operations.DisksOperations.create_or_update')
  @typing.no_type_check
  def testCreateDiskFromSnapshot(self, mock_create_disk):
    """Test that a disk can be created from a snapshot."""
    mock_create_disk.return_value.done.return_value = True
    mock_create_disk.return_value.result.return_value = MOCK_DISK_COPY
    # CreateDiskFromSnapshot(
    #     snapshot=FAKE_SNAPSHOT, disk_name=None, disk_name_prefix='')
    disk_from_snapshot = FAKE_ACCOUNT.compute.CreateDiskFromSnapshot(
        FAKE_SNAPSHOT)
    self.assertIsInstance(disk_from_snapshot, compute.AZComputeDisk)
    self.assertEqual(
        'fake_snapshot_name_f4c186ac_copy', disk_from_snapshot.name)
    mock_create_disk.assert_called_with(
        FAKE_SNAPSHOT.resource_group_name,
        'fake_snapshot_name_c4a46ad7_copy',
        mock.ANY)

    # CreateDiskFromSnapshot(
    #     snapshot=FAKE_SNAPSHOT,
    #     disk_name='new-forensics-disk',
    #     disk_name_prefix='')
    FAKE_ACCOUNT.compute.CreateDiskFromSnapshot(
        FAKE_SNAPSHOT, disk_name='new-forensics-disk')
    mock_create_disk.assert_called_with(
        FAKE_SNAPSHOT.resource_group_name,
        'new-forensics-disk',
        mock.ANY)

    # CreateDiskFromSnapshot(
    #     snapshot=FAKE_SNAPSHOT, disk_name=None, disk_name_prefix='prefix')
    FAKE_ACCOUNT.compute.CreateDiskFromSnapshot(
        FAKE_SNAPSHOT, disk_name_prefix='prefix')
    mock_create_disk.assert_called_with(
        FAKE_SNAPSHOT.resource_group_name,
        'prefix_fake_snapshot_name_c4a46ad7_copy',
        mock.ANY)

    # CreateDiskFromSnapshot(
    #     snapshot=FAKE_SNAPSHOT, disk_type='StandardSSD_LRS')
    expected_args = {
        'location': 'fake-region',
        'creation_data': {
            'sourceResourceId': '/subscriptions/sub/resourceGroups/'
                                'fake-resource-group/providers/'
                                'Microsoft.Compute/type/fake_snapshot_name',
            'create_option': models.DiskCreateOption.copy
        },
        'sku': {
            'name': 'StandardSSD_LRS'
        }
    }
    FAKE_ACCOUNT.compute.CreateDiskFromSnapshot(
        FAKE_SNAPSHOT, disk_type='StandardSSD_LRS')
    mock_create_disk.assert_called_with(
        FAKE_SNAPSHOT.resource_group_name,
        'fake_snapshot_name_c4a46ad7_copy',
        expected_args)

  @mock.patch('azure.storage.blob._container_client.ContainerClient.create_container')
  @mock.patch('azure.storage.blob._generated._azure_blob_storage.AzureBlobStorage.__init__')
  @mock.patch('azure.storage.blob._blob_service_client.BlobServiceClient.get_blob_client')
  @mock.patch('azure.storage.blob._blob_service_client.BlobServiceClient.get_container_client')
  @mock.patch('azure.storage.blob._blob_service_client.BlobServiceClient.__init__')
  @mock.patch('libcloudforensics.providers.azure.internal.storage.AZStorage.DeleteStorageAccount')
  @mock.patch('libcloudforensics.providers.azure.internal.storage.AZStorage.CreateStorageAccount')
  @mock.patch('azure.mgmt.compute.v2020_05_01.operations._disks_operations.DisksOperations.create_or_update')
  @typing.no_type_check
  def testCreateDiskFromSnapshotUri(self,
                                    mock_create_disk,
                                    mock_create_storage_account,
                                    mock_delete_storage_account,
                                    mock_blob_client,
                                    mock_get_container,
                                    mock_get_blob_client,
                                    mock_blob_storage,
                                    mock_create_container):
    """Test that a disk can be created from a snapshot URI."""
    mock_create_disk.return_value.done.return_value = True
    mock_create_disk.return_value.result.return_value = MOCK_DISK_COPY
    mock_create_storage_account.return_value = ('fake-account-id', 'fake-key')
    mock_blob_client.return_value = None
    mock_blob_storage.return_value = None
    mock_get_container.return_value = mock.Mock()
    mock_create_container.return_value = None
    blob_properties = mock_get_blob_client.return_value.get_blob_properties
    blob_properties.return_value = mock.Mock(copy=mock.Mock(status='success'))
    mock_delete_storage_account.return_value = None

    disk_from_snapshot_uri = FAKE_ACCOUNT.compute.CreateDiskFromSnapshotURI(
        FAKE_SNAPSHOT, 'fake-snapshot-uri')
    #  hashlib.sha1('/a/b/c/fake-resource-group/fake_snapshot_name'.encode(
    #     'utf-8')).hexdigest()[:23] = 97d1e8cfe4cf4d573fea2b5
    mock_create_storage_account.assert_called_with(
        '97d1e8cfe4cf4d573fea2b5', region='fake-region')
    self.assertIsInstance(disk_from_snapshot_uri, compute.AZComputeDisk)
    self.assertEqual(
        'fake_snapshot_name_f4c186ac_copy', disk_from_snapshot_uri.name)
    mock_create_disk.assert_called_with(
        FAKE_SNAPSHOT.resource_group_name,
        'fake_snapshot_name_c4a46ad7_copy',
        mock.ANY)

  @mock.patch('sshpubkeys.SSHKey.parse')
  @mock.patch('libcloudforensics.scripts.utils.ReadStartupScript')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZCompute.GetInstance')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZCompute._GetInstanceType')
  @mock.patch('libcloudforensics.providers.azure.internal.network.AZNetwork.CreateNetworkInterface')
  @mock.patch('azure.mgmt.compute.v2020_06_01.operations._virtual_machines_operations.VirtualMachinesOperations.create_or_update')
  @typing.no_type_check
  def testGetOrCreateAnalysisVm(self,
                                mock_vm,
                                mock_nic,
                                mock_instance_type,
                                mock_get_instance,
                                mock_script,
                                mock_ssh_parse):
    """Test that a VM is created or retrieved if it already exists."""
    mock_instance_type.return_value = 'fake-instance-type'
    mock_nic.return_value = 'fake-network-interface-id'
    mock_get_instance.return_value = FAKE_INSTANCE
    mock_script.return_value = ''
    mock_ssh_parse.return_value = None

    vm, created = FAKE_ACCOUNT.compute.GetOrCreateAnalysisVm(
        FAKE_INSTANCE.name, 1, 4, 8192, '')
    mock_get_instance.assert_called_with(FAKE_INSTANCE.name)
    mock_vm.assert_not_called()
    self.assertIsInstance(vm, compute.AZComputeVirtualMachine)
    self.assertEqual('fake-vm-name', vm.name)
    self.assertFalse(created)

    # We mock the GetInstance() call to throw a RuntimeError to mimic
    # an instance that wasn't found. This should trigger a vm to be
    # created.
    mock_get_instance.side_effect = RuntimeError()
    mock_vm.return_value.result.return_value = MOCK_ANALYSIS_INSTANCE
    vm, created = FAKE_ACCOUNT.compute.GetOrCreateAnalysisVm(
        'fake-analysis-vm-name', 1, 4, 8192, '')
    mock_get_instance.assert_called_with('fake-analysis-vm-name')
    mock_vm.assert_called()
    self.assertIsInstance(vm, compute.AZComputeVirtualMachine)
    self.assertEqual('fake-analysis-vm-name', vm.name)
    self.assertTrue(created)

  @mock.patch('azure.mgmt.compute.v2020_06_01.operations._virtual_machine_sizes_operations.VirtualMachineSizesOperations.list')
  @typing.no_type_check
  def testListVMSizes(self, mock_list):
    """Test that instance types are correctly listed."""
    mock_list.return_value = MOCK_REQUEST_VM_SIZE
    available_vms = FAKE_ACCOUNT.compute.ListInstanceTypes()
    self.assertEqual(1, len(available_vms))
    self.assertEqual('fake-vm-type', available_vms[0]['Name'])
    self.assertEqual(4, available_vms[0]['CPU'])
    self.assertEqual(8192, available_vms[0]['Memory'])

  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZCompute.ListInstanceTypes')
  @typing.no_type_check
  def testGetInstanceType(self, mock_list_instance_types):
    """Test that the instance type given a configuration is correct."""
    # pylint: disable=protected-access
    mock_list_instance_types.return_value = MOCK_LIST_VM_SIZES
    instance_type = FAKE_ACCOUNT.compute._GetInstanceType(4, 8192)
    self.assertEqual('fake-vm-type', instance_type)

    with self.assertRaises(ValueError):
      FAKE_ACCOUNT.compute._GetInstanceType(666, 666)
    # pylint: enable=protected-access

  @mock.patch('azure.mgmt.resource.subscriptions.v2019_11_01.operations._subscriptions_operations.SubscriptionsOperations.list')
  @typing.no_type_check
  def testListSubscriptionIDs(self, mock_list):
    """Test that subscription IDs are correctly listed"""
    mock_list.return_value = MOCK_LIST_IDS
    subscription_ids = FAKE_ACCOUNT.resource.ListSubscriptionIDs()
    self.assertEqual(2, len(subscription_ids))
    self.assertEqual('fake-subscription-id-1', subscription_ids[0])

  @mock.patch('azure.mgmt.storage.v2019_06_01.operations._storage_accounts_operations.StorageAccountsOperations.list_keys')
  @mock.patch('azure.mgmt.storage.v2019_06_01.operations._storage_accounts_operations.StorageAccountsOperations.create')
  @typing.no_type_check
  def testCreateStorageAccount(self, mock_create, mock_list_keys):
    """Test that a storage account is created and its information retrieved"""
    # pylint: disable=protected-access
    mock_create.return_value.result.return_value = MOCK_STORAGE_ACCOUNT
    mock_list_keys.return_value = MOCK_LIST_KEYS
    account_id, account_key = FAKE_ACCOUNT.storage.CreateStorageAccount(
        'fakename')
    self.assertEqual('fakestorageid', account_id)
    self.assertEqual('fake-key-value', account_key)

    with self.assertRaises(ValueError) as error:
      _, _ = FAKE_ACCOUNT.storage.CreateStorageAccount(
          'fake-non-conform-name')
    # pylint: enable=protected-access
    self.assertEqual('Storage account name fake-non-conform-name does not '
                     'comply with ^[a-z0-9]{1,24}$', str(error.exception))


class TestCommon(unittest.TestCase):
  """Test Azure common file."""

  @typing.no_type_check
  def testGenerateDiskName(self):
    """Test that disk names are correclty generated.

    The disk name must comply with the following RegEx: ^[\\w]{1,80}$
        i.e., it must be between 1 and 80 chars and be within [a-zA-Z0-9].
    """
    disk_name = common.GenerateDiskName(FAKE_SNAPSHOT)
    self.assertEqual('fake_snapshot_name_c4a46ad7_copy', disk_name)

    disk_name = common.GenerateDiskName(
        FAKE_SNAPSHOT, disk_name_prefix='prefix')
    self.assertEqual('prefix_fake_snapshot_name_c4a46ad7_copy', disk_name)

  @mock.patch('msrestazure.azure_active_directory.ServicePrincipalCredentials.__init__')
  @typing.no_type_check
  def testGetCredentials(self, mock_azure_credentials):
    """Test that credentials are parsed correctly / found."""

    mock_azure_credentials.return_value = None

    # If all environment variables are defined, things should work correctly
    os.environ['AZURE_SUBSCRIPTION_ID'] = 'fake-subscription-id'
    os.environ["AZURE_CLIENT_ID"] = 'fake-client-id'
    os.environ["AZURE_CLIENT_SECRET"] = 'fake-client-secret'
    os.environ["AZURE_TENANT_ID"] = 'fake-tenant-id'

    subscription_id, _ = common.GetCredentials()
    self.assertEqual('fake-subscription-id', subscription_id)
    mock_azure_credentials.assert_called_with(
        'fake-client-id', 'fake-client-secret', tenant='fake-tenant-id')

    # If an environment variable is missing, a RuntimeError should be raised
    del os.environ['AZURE_SUBSCRIPTION_ID']
    with self.assertRaises(RuntimeError) as error:
      _, _ = common.GetCredentials()
      mock_azure_credentials.assert_not_called()
    self.assertEqual(
        'Please make sure you defined the following environment variables: '
        '[AZURE_SUBSCRIPTION_ID,AZURE_CLIENT_ID, AZURE_CLIENT_SECRET,'
        'AZURE_TENANT_ID].', str(error.exception))

    # If a profile name is passed to the method, then it will look for a
    # credential file (default path being ~/.azure/credentials.json). We can
    # set a particular path by setting the AZURE_CREDENTIALS_PATH variable.

    # If the file is not a valid json file, should raise a ValueError
    os.environ['AZURE_CREDENTIALS_PATH'] = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.realpath(__file__)))), STARTUP_SCRIPT)
    with self.assertRaises(ValueError) as error:
      _, _ = common.GetCredentials(profile_name='foo')
      mock_azure_credentials.assert_not_called()
    self.assertEqual(
        'Could not decode JSON file. Please verify the file format: Expecting '
        'value: line 1 column 1 (char 0)', str(error.exception))

    # If the file is correctly formatted, then things should work correctly
    os.environ['AZURE_CREDENTIALS_PATH'] = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.realpath(__file__)))), JSON_FILE)
    subscription_id, _ = common.GetCredentials(
        profile_name='test_profile_name')
    self.assertEqual(
        'fake-subscription-id-from-credential-file', subscription_id)
    mock_azure_credentials.assert_called_with(
        'fake-client-id-from-credential-file',
        'fake-client-secret-from-credential-file',
        tenant='fake-tenant-id-from-credential-file')

    # If the profile name does not exist, should raise a ValueError
    with self.assertRaises(ValueError) as error:
      _, _ = common.GetCredentials(profile_name='foo')
      mock_azure_credentials.assert_not_called()
    self.assertEqual(
        'Profile name foo not found in credentials file {0:s}'.format(
            os.environ['AZURE_CREDENTIALS_PATH']), str(error.exception))

    # If the profile name exists but there are missing entries, should raise
    # a ValueError
    with self.assertRaises(ValueError) as error:
      _, _ = common.GetCredentials(profile_name='incomplete_profile_name')
      mock_azure_credentials.assert_not_called()
    self.assertEqual(
        'Profile name incomplete_profile_name not found in credentials file '
        '{0:s}'.format(
            os.environ['AZURE_CREDENTIALS_PATH']), str(error.exception))


class TestAZVirtualMachine(unittest.TestCase):
  """Test Azure virtual machine class."""
  # pylint: disable=line-too-long

  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZCompute.ListDisks')
  @mock.patch('azure.mgmt.compute.v2020_06_01.operations._virtual_machines_operations.VirtualMachinesOperations.get')
  @typing.no_type_check
  def testGetBootDisk(self, mock_get_vm, mock_list_disk):
    """Test that the boot disk from an instance is retrieved."""
    mock_get_vm.return_value = mock.Mock(
        storage_profile=mock.Mock(os_disk=MOCK_BOOT_DISK))
    mock_list_disk.return_value = MOCK_LIST_DISKS
    boot_disk = FAKE_INSTANCE.GetBootDisk()
    mock_list_disk.assert_called_once()
    mock_list_disk.assert_called_with(
        resource_group_name=FAKE_INSTANCE.resource_group_name)
    self.assertEqual('fake-boot-disk-name', boot_disk.name)

  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZComputeVirtualMachine.ListDisks')
  @typing.no_type_check
  def testGetDisk(self, mock_list_disk):
    """Test that a particular disk from an instance is retrieved."""
    mock_list_disk.return_value = MOCK_LIST_DISKS
    disk = FAKE_INSTANCE.GetDisk('fake-disk-name')
    self.assertEqual('fake-disk-name', disk.name)

    with self.assertRaises(RuntimeError) as error:
      FAKE_INSTANCE.GetDisk('non-existent-disk-name')
    self.assertEqual(
        'Disk non-existent-disk-name not found in instance: '
        '/subscriptions/sub/resourceGroups/fake-resource-group'
        '/providers/Microsoft.Compute/type/fake-vm-name', str(error.exception))

  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZCompute.ListDisks')
  @mock.patch('azure.mgmt.compute.v2020_06_01.operations._virtual_machines_operations.VirtualMachinesOperations.get')
  @typing.no_type_check
  def testListDisks(self, mock_get_vm, mock_list_disk):
    """Test that disks from an instance are correctly listed."""
    mock_get_vm.return_value = mock.Mock(
        storage_profile=mock.Mock(os_disk=MOCK_BOOT_DISK, data_disks=[]))

    # MOCK_LIST_DISKS contains all 2 disks from the subscription
    self.assertEqual(2, len(MOCK_LIST_DISKS))
    mock_list_disk.return_value = MOCK_LIST_DISKS

    # The instance is expected to have only a boot disk as we mocked the
    # data_disks attribute with an empty list
    instance_disks = FAKE_INSTANCE.ListDisks()
    mock_list_disk.assert_called()
    mock_list_disk.assert_called_with(
        resource_group_name=FAKE_INSTANCE.resource_group_name)
    self.assertEqual(1, len(instance_disks))
    self.assertNotEqual(MOCK_LIST_DISKS, instance_disks)

    # The instance is expected to have 2 disks as we mocked the
    # data_disks attribute with a non-empty list
    mock_get_vm.return_value = mock.Mock(
        storage_profile=mock.Mock(
            os_disk=MOCK_BOOT_DISK, data_disks=[MOCK_DISK]))
    instance_disks = FAKE_INSTANCE.ListDisks()
    mock_list_disk.assert_called()
    mock_list_disk.assert_called_with(
        resource_group_name=FAKE_INSTANCE.resource_group_name)
    self.assertEqual(2, len(instance_disks))
    self.assertEqual(MOCK_LIST_DISKS, instance_disks)


class TestMonitoring(unittest.TestCase):
  """Test Azure monitoring class."""

  @typing.no_type_check
  @mock.patch('azure.mgmt.monitor.v2018_01_01.operations._metric_definitions_operations.MetricDefinitionsOperations.list')
  def testListAvailableMetricsForResource(self, mock_list_metrics):
    """Test that metrics are correctly listed."""
    mock_list_metrics.return_value = MOCK_LIST_METRICS
    metrics = FAKE_MONITORING.ListAvailableMetricsForResource(
        'fake-resource-id')
    self.assertEqual(1, len(metrics))
    self.assertIn('fake-metric', metrics)

  @typing.no_type_check
  @mock.patch('azure.mgmt.monitor.v2018_01_01.operations._metrics_operations.MetricsOperations.list')
  def testGetMetricsForResource(self, mock_list_metrics_operations):
    """Test that metrics values are correctly retrieved."""
    mock_list_metrics_operations.return_value = MOCK_METRIC_OPERATION
    metrics = FAKE_MONITORING.GetMetricsForResource(
        'fake-resource-id', 'fake-metric')
    self.assertIn('fake-metric', metrics)
    self.assertEqual(1, len(metrics['fake-metric']))
    self.assertEqual('fake-value', metrics['fake-metric']['fake-time-stamp'])


class TestForensics(unittest.TestCase):
  """Test Azure forensics file."""
  # pylint: disable=line-too-long, too-many-arguments

  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZComputeDisk.GetDiskType')
  @mock.patch('libcloudforensics.providers.azure.internal.resource.AZResource.GetOrCreateResourceGroup')
  @mock.patch('libcloudforensics.providers.azure.internal.common.GetCredentials')
  @mock.patch('libcloudforensics.providers.azure.internal.resource.AZResource.ListSubscriptionIDs')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZComputeSnapshot.Delete')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZComputeDisk.Snapshot')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZCompute.GetDisk')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZComputeVirtualMachine.GetBootDisk')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZCompute.GetInstance')
  @mock.patch('azure.mgmt.compute.v2020_05_01.operations._disks_operations.DisksOperations.create_or_update')
  @typing.no_type_check
  def testCreateDiskCopy1(self,
                          mock_create_disk,
                          mock_get_instance,
                          mock_get_boot_disk,
                          mock_get_disk,
                          mock_snapshot,
                          mock_snapshot_delete,
                          mock_list_subscription_ids,
                          mock_credentials,
                          mock_resource_group,
                          mock_disk_type):
    """Test that a disk copy is correctly created.

    CreateDiskCopy(zone, instance_name='fake-vm-name', region='fake-region').
    This should grab the boot disk of the instance.
    """
    mock_create_disk.return_value.done.return_value = True
    mock_create_disk.return_value.result.return_value = MOCK_DISK_COPY
    mock_get_instance.return_value = FAKE_INSTANCE
    mock_get_boot_disk.return_value = FAKE_BOOT_DISK
    mock_snapshot.return_value = FAKE_SNAPSHOT
    mock_snapshot_delete.return_value = None
    mock_list_subscription_ids.return_value = ['fake-subscription-id']
    mock_credentials.return_value = ('fake-subscription-id', mock.Mock())
    mock_resource_group.return_value = 'fake-resource-group'
    mock_disk_type.return_value = 'fake-disk-type'

    disk_copy = forensics.CreateDiskCopy(
        FAKE_ACCOUNT.default_resource_group_name,
        instance_name=FAKE_INSTANCE.name,
        region='fake-region')
    mock_get_instance.assert_called_once()
    mock_get_instance.assert_called_with('fake-vm-name')
    mock_get_boot_disk.assert_called_once()
    mock_get_disk.assert_not_called()
    self.assertIsInstance(disk_copy, compute.AZComputeDisk)
    self.assertEqual('fake_snapshot_name_f4c186ac_copy', disk_copy.name)

  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZComputeDisk.GetDiskType')
  @mock.patch('libcloudforensics.providers.azure.internal.resource.AZResource.GetOrCreateResourceGroup')
  @mock.patch('libcloudforensics.providers.azure.internal.common.GetCredentials')
  @mock.patch('libcloudforensics.providers.azure.internal.resource.AZResource.ListSubscriptionIDs')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZComputeSnapshot.Delete')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZComputeDisk.Snapshot')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZCompute.GetDisk')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZComputeVirtualMachine.GetBootDisk')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZCompute.GetInstance')
  @mock.patch('azure.mgmt.compute.v2020_05_01.operations._disks_operations.DisksOperations.create_or_update')
  @typing.no_type_check
  def testCreateDiskCopy2(self,
                          mock_create_disk,
                          mock_get_instance,
                          mock_get_boot_disk,
                          mock_get_disk,
                          mock_snapshot,
                          mock_snapshot_delete,
                          mock_list_subscription_ids,
                          mock_credentials,
                          mock_resource_group,
                          mock_disk_type):
    """Test that a disk copy is correctly created.

    CreateDiskCopy(zone, disk_name='fake-disk-name', region='fake-region').
    This should grab the disk 'fake-disk-name'."""
    mock_create_disk.return_value.done.return_value = True
    mock_create_disk.return_value.result.return_value = MOCK_DISK_COPY
    mock_get_instance.return_value = FAKE_INSTANCE
    mock_get_disk.return_value = FAKE_DISK
    mock_snapshot.return_value = FAKE_SNAPSHOT
    mock_snapshot_delete.return_value = None
    mock_list_subscription_ids.return_value = ['fake-subscription-id']
    mock_credentials.return_value = ('fake-subscription-id', mock.Mock())
    mock_resource_group.return_value = 'fake-resource-group'
    mock_disk_type.return_value = 'fake-disk-type'

    disk_copy = forensics.CreateDiskCopy(
        FAKE_ACCOUNT.default_resource_group_name,
        disk_name=FAKE_DISK.name,
        region='fake-region')
    mock_get_instance.assert_not_called()
    mock_get_boot_disk.assert_not_called()
    mock_get_disk.assert_called_once()
    mock_get_disk.assert_called_with('fake-disk-name')
    self.assertIsInstance(disk_copy, compute.AZComputeDisk)
    self.assertEqual('fake_snapshot_name_f4c186ac_copy', disk_copy.name)

  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZComputeDisk.GetDiskType')
  @mock.patch('libcloudforensics.providers.azure.internal.resource.AZResource.GetOrCreateResourceGroup')
  @mock.patch('libcloudforensics.providers.azure.internal.common.GetCredentials')
  @mock.patch('libcloudforensics.providers.azure.internal.resource.AZResource.ListSubscriptionIDs')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZCompute.ListDisks')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZCompute.ListInstances')
  @typing.no_type_check
  def testCreateDiskCopy3(self,
                          mock_list_instances,
                          mock_list_disk,
                          mock_list_subscription_ids,
                          mock_credentials,
                          mock_resource_group,
                          mock_disk_type):
    """Test that a disk copy is correctly created.

    The first call should raise a RuntimeError in GetInstance as we are
    querying a non-existent instance. The second call should raise a
    RuntimeError in GetDisk as we are querying a non-existent disk."""
    mock_list_instances.return_value = {}
    mock_list_disk.return_value = {}
    mock_list_subscription_ids.return_value = ['fake-subscription-id']
    mock_credentials.return_value = ('fake-subscription-id', mock.Mock())
    mock_resource_group.return_value = 'fake-resource-group'
    mock_disk_type.return_value = 'fake-disk-type'

    with self.assertRaises(RuntimeError) as error:
      forensics.CreateDiskCopy(
          FAKE_ACCOUNT.default_resource_group_name,
          instance_name='non-existent-vm-name',
          region='fake-region')
    self.assertEqual(
        'Cannot copy disk "None": Instance non-existent-vm-name was not found '
        'in subscription fake-subscription-id', str(error.exception))

    with self.assertRaises(RuntimeError) as error:
      forensics.CreateDiskCopy(
          FAKE_ACCOUNT.default_resource_group_name,
          disk_name='non-existent-disk-name',
          region='fake-region')
    self.assertEqual(
        'Cannot copy disk "non-existent-disk-name": Disk non-existent-disk-name'
        ' was not found in subscription fake-subscription-id', str(error.exception))


if __name__ == '__main__':
  unittest.main()
