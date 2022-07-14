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
"""GCP mocks used across tests."""

import re

# pylint: disable=line-too-long
from libcloudforensics.providers.gcp.internal import build as gcp_build
from libcloudforensics.providers.gcp.internal import compute
from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.gcp.internal import log as gcp_log
from libcloudforensics.providers.gcp.internal import monitoring as gcp_monitoring
from libcloudforensics.providers.gcp.internal import storage as gcp_storage
from libcloudforensics.providers.gcp.internal import storagetransfer as gcp_storagetransfer
from libcloudforensics.providers.gcp.internal import cloudsql as gcp_cloudsql
from libcloudforensics.providers.gcp.internal import cloudresourcemanager as gcp_resourcemanager
from libcloudforensics.providers.gcp.internal import serviceusage as gcp_serviceusage
from libcloudforensics.providers.gcp.internal import bigquery as gcp_bigquery
# pylint: enable=line-too-long

FAKE_ANALYSIS_PROJECT = gcp_project.GoogleCloudProject(
    'fake-target-project', 'fake-zone')

FAKE_ANALYSIS_VM = compute.GoogleComputeInstance(
    FAKE_ANALYSIS_PROJECT.project_id, 'fake-zone', 'fake-analysis-vm')

FAKE_IMAGE = compute.GoogleComputeImage(
    FAKE_ANALYSIS_PROJECT.project_id, '', 'fake-image')

# Source project with the instance that needs forensicating
FAKE_SOURCE_PROJECT = gcp_project.GoogleCloudProject(
    'fake-source-project', 'fake-zone')

FAKE_INSTANCE = compute.GoogleComputeInstance(
    FAKE_SOURCE_PROJECT.project_id, 'fake-zone', 'fake-instance',
    resource_id='0123456789012345678')

FAKE_INSTANCE_NAME_DUP = compute.GoogleComputeInstance(
    FAKE_SOURCE_PROJECT.project_id, 'fake-zone2', 'fake-instance',
    resource_id='1234567890123456789')

FAKE_DISK = compute.GoogleComputeDisk(
    FAKE_SOURCE_PROJECT.project_id, 'fake-zone', 'fake-disk')

FAKE_BOOT_DISK = compute.GoogleComputeDisk(
    FAKE_SOURCE_PROJECT.project_id, 'fake-zone', 'fake-boot-disk')

FAKE_SNAPSHOT = compute.GoogleComputeSnapshot(
    FAKE_DISK, 'fake-snapshot')

FAKE_SNAPSHOT_LONG_NAME = compute.GoogleComputeSnapshot(
    FAKE_DISK,
    'this-is-a-kind-of-long-fake-snapshot-name-and-is-definitely-over-63-chars')

FAKE_DISK_COPY = compute.GoogleComputeDisk(
    FAKE_SOURCE_PROJECT.project_id, 'fake-zone', 'fake-disk-copy')

FAKE_LOGS = gcp_log.GoogleCloudLog(['fake-target-project'])

FAKE_LOG_LIST = [
    'projects/fake-target-project/logs/GCEGuestAgent',
    'projects/fake-target-project/logs/OSConfigAgent'
]

STARTUP_SCRIPT = 'scripts/startup.sh'

FAKE_LOG_ENTRIES = [{
    'logName': 'test_log',
    'timestamp': '123456789',
    'textPayload': 'insert.compute.create'
}, {
    'logName': 'test_log',
    'timestamp': '123456789',
    'textPayload': 'insert.compute.create'
}]

# pylint: disable=line-too-long
FAKE_NEXT_PAGE_TOKEN = 'abcdefg1234567'
FAKE_GCS = gcp_storage.GoogleCloudStorage('fake-target-project')
FAKE_GCST = gcp_storagetransfer.GoogleCloudStorageTransfer('fake-target-project')
FAKE_GCB = gcp_build.GoogleCloudBuild('fake-target-project')
FAKE_MONITORING = gcp_monitoring.GoogleCloudMonitoring('fake-target-project')
FAKE_CLOUDSQLINSTANCE = gcp_cloudsql.GoogleCloudSQL('fake-target-project')
FAKE_CLOUD_RESOURCE_MANAGER = gcp_resourcemanager.GoogleCloudResourceManager('fake-project')
FAKE_SERVICE_USAGE = gcp_serviceusage.GoogleServiceUsage('fake-project')
FAKE_BIGQUERY = gcp_bigquery.GoogleBigQuery('fake-target-project')
# pylint: enable=line-too-long

# Mock struct to mimic GCP's API responses
MOCK_INSTANCES_AGGREGATED = {
    # See https://cloud.google.com/compute/docs/reference/rest/v1/instances
    # /aggregatedList for complete structure
    'items': {
        0: {
            'instances': [{
                'name': FAKE_INSTANCE.name,
                'zone': '/' + FAKE_INSTANCE.zone,
                'id': FAKE_INSTANCE.resource_id
            }]
        }
    }
}

# Mock struct to mimic GCP's API responses
MOCK_INSTANCE_ABANDONED = {
    # See https://cloud.google.com/compute/docs/reference/rest/v1/
    # instanceGroupManagers/abandonInstances for complete structure
    'status': 'DONE'
}

# Mock struct to mimic GCP's API responses
MOCK_LOGS_LIST = {
    # See https://cloud.google.com/logging/docs/reference/v2/rest/v2
    # /ListLogsResponse for complete structure
    'logNames': FAKE_LOG_LIST
}

MOCK_LOG_ENTRIES = {
    # See https://cloud.google.com/logging/docs/reference/v2/rest/v2
    # /entries/list/ListLogsResponse for complete structure
    'entries': FAKE_LOG_ENTRIES
}

MOCK_DISKS_AGGREGATED = {
    # See https://cloud.google.com/compute/docs/reference/rest/v1/disks
    # /aggregatedList for complete structure
    'items': {
        0: {
            'disks': [{
                'name': FAKE_BOOT_DISK.name,
                'zone': '/' + FAKE_BOOT_DISK.zone,
		'id': '01234567890123456789'
            }]
        },
        1: {
            'disks': [{
                'name': FAKE_DISK.name,
                'zone': '/' + FAKE_DISK.zone,
		'id': '0123456789012345678'
            }]
        }
    }
}

MOCK_LIST_INSTANCES = {'0123456789012345678': FAKE_INSTANCE}

MOCK_LIST_DISKS = {
    '0123456789012345678': FAKE_DISK,
    '01234567890123456789': FAKE_BOOT_DISK
}

MOCK_GCE_OPERATION_INSTANCES_LABELS_SUCCESS = {
    'items': {
        'zone': {
            'instances': [{
                'name': FAKE_INSTANCE.name,
                'zone': '/' + FAKE_INSTANCE.zone,
                'labels': {
                    'id': '123'
                }
            }]
        }
    }
}

MOCK_GCE_OPERATION_DISKS_LABELS_SUCCESS = {
    'items': {
        'zone': {
            'disks': [{
                'name': FAKE_DISK.name,
                'labels': {
                    'id': '123'
                }
            }, {
                'name': FAKE_BOOT_DISK.name,
                'labels': {
                    'some': 'thing'
                }
            }]
        }
    }
}

MOCK_GCE_OPERATION_LABELS_FAILED = {
    'items': {},
    'warning': {
        'code': 404,
        'message': 'Not Found'
    }
}

# pylint: disable=line-too-long
MOCK_NETWORK_INTERFACES = [
    {
        'network': 'https://www.googleapis.com/compute/v1/projects/fake-project/global/networks/default',
        'subnetwork': 'https://www.googleapis.com/compute/v1/projects/fake-project/regions/fake-region/subnetworks/default',
        'networkIP': '10.1.1.1',
        'name': 'nic0',
        'accessConfigs': [
            {
                'type': 'ONE_TO_ONE_NAT',
                'name': 'External NAT',
                'natIP': '0.0.0.0',
                'networkTier': 'PREMIUM',
                'kind': 'compute#accessConfig'
                }
        ],
        'fingerprint': 'bm9mcGZwZnA=',
        'kind': 'compute#networkInterface'
    }
]

MOCK_GCE_OPERATION_INSTANCES_GET = {
    # See https://cloud.google.com/compute/docs/reference/rest/v1/instances/get
    # for complete structure
    'name':
        FAKE_INSTANCE.name,
    'machineType': 'https://www.googleapis.com/compute/v1/projects/fake-project/zones/us-central1-a/machineTypes/e2-medium',
    'status': 'RUNNING',
    'zone': 'https://www.googleapis.com/compute/v1/projects/ake-project/zones/us-central1-a',
    'disks': [{
        'boot': True,
        'source': '/' + FAKE_BOOT_DISK.name,
        'diskSizeGb': '10'
    }, {
        'boot': False,
        'source': '/' + FAKE_DISK.name,
        'initializeParams': {
            'diskName': FAKE_DISK.name
        }
    }],
    'networkInterfaces': MOCK_NETWORK_INTERFACES,
    'metadata': {
    'fingerprint': 'b4UswdFiBpQ=',
    'items': [
      {
        'key': 'startup-script',
        'value': STARTUP_SCRIPT
      }
    ],
    'kind': 'compute#metadata'
  }
}
# pylint: enable=line-too-long

MOCK_GCS_BUCKETS = {
    'kind':
        'storage#buckets',
    'items': [{
        'kind': 'storage#bucket',
        'id': 'fake-bucket',
        'selfLink': 'https://www.googleapis.com/storage/v1/b/fake-bucket',
        'projectNumber': '123456789',
        'name': 'fake-bucket',
        'timeCreated': '2020-01-01T01:02:03.456Z',
        'updated': '2020-07-09T05:58:11.393Z',
        'metageneration': '8',
        'iamConfiguration': {
            'bucketPolicyOnly': {
                'enabled': True, 'lockedTime': '2020-10-04T05:47:28.721Z'
            },
            'uniformBucketLevelAccess': {
                'enabled': True, 'lockedTime': '2020-10-04T05:47:28.721Z'
            }
        },
        'location': 'US-EAST1',
        'locationType': 'region',
        'defaultEventBasedHold': False,
        'storageClass': 'STANDARD',
        'etag': 'CAg='
    }]
}

MOCK_GCS_OBJECT_METADATA = {
    'kind': 'storage#object',
    'id': 'fake-bucket/foo/fake.img/12345',
    'size': '5555555555',
    'md5Hash': 'MzFiYWIzY2M0MTJjNGMzNjUyZDMyNWFkYWMwODA5YTEgIGNvdW50MQo=',
}

MOCK_GCS_BUCKET_OBJECTS = {
    'items': [
        MOCK_GCS_OBJECT_METADATA
    ]
}

MOCK_GCS_BUCKET_ACLS = {
    'kind': 'storage#bucketAccessControls',
    'items': [
        {
            'kind': 'storage#bucketAccessControl',
            'id': 'test_bucket_1/project-editors-1',
            'bucket': 'test_bucket_1',
            'entity': 'project-editors-1',
            'role': 'OWNER',
        },
        {
            'kind': 'storage#bucketAccessControl',
            'id': 'test_bucket_1/project-owners-1',
            'bucket': 'test_bucket_1',
            'entity': 'project-owners-1',
            'role': 'OWNER',
        }
    ]
}

MOCK_GCS_BUCKET_IAM = {
        'bindings': [{
            'role': 'roles/storage.legacyBucketOwner',
            'members': ['projectEditor:project1', 'projectOwner:project1'],
        }]
}

MOCK_GCB_BUILDS_CREATE = {
    'name': 'operations/build/fake-project/12345',
    'metadata': {
        'build': {
            'id': '12345',
            'timeout': '12345s',
            'projectId': 'fake-project',
            'logsBucket': 'gs://fake-uri',
            "logUrl": "https://fake-url"
        }
    }
}

MOCK_GCB_BUILDS_SUCCESS = {
    'done': True,
    'response': {
        'id': 'fake-id'
    },
    'metadata': {
        'build': {
            'id': '12345',
            'timeout': '12345s',
            'projectId': 'fake-project',
            'logsBucket': 'gs://fake-uri',
            "logUrl": "https://fake-url"
        }
    }
}

MOCK_GCB_BUILDS_FAIL = {
    'done': True,
    'error': {
        'code': 2,
        'message': 'Build failed; check build logs for details'
    },
    'metadata': {
        'build': {
            'id': '12345',
            'timeout': '12345s',
            'projectId': 'fake-project',
            'logsBucket': 'gs://fake-uri',
            "logUrl": "https://fake-url"
        }
    }
}

MOCK_STACKDRIVER_METRIC = 6693417
MOCK_COMPUTE_METRIC = 8093
MOCK_LOGGING_METRIC = 1

MOCK_GCM_METRICS_COUNT = {
    'timeSeries': [{
        'metric': {
            'type': 'serviceruntime.googleapis.com/api/request_count'
        },
        'resource': {
            'type': 'consumed_api',
            'labels': {
                'project_id': 'fake-target-project',
                'service': 'stackdriver.googleapis.com'
            }
        },
        'metricKind': 'DELTA',
        'valueType': 'INT64',
        'points': [{
            'interval': {
                'startTime': '2020-05-18T00:00:00Z',
                'endTime': '2020-06-17T00:00:00Z'
            },
            'value': {
                'int64Value': MOCK_STACKDRIVER_METRIC
            }
        }]
    }, {
        'metric': {
            'type': 'serviceruntime.googleapis.com/api/request_count'
        },
        'resource': {
            'type': 'consumed_api',
            'labels': {
                'service': 'compute.googleapis.com',
                'project_id': 'fake-target-project'
            }
        },
        'metricKind': 'DELTA',
        'valueType': 'INT64',
        'points': [{
            'interval': {
                'startTime': '2020-05-18T00:00:00Z',
                'endTime': '2020-06-17T00:00:00Z'
            },
            'value': {
                'int64Value': MOCK_COMPUTE_METRIC
            }
        }]
    }, {
        'metric': {
            'type': 'serviceruntime.googleapis.com/api/request_count'
        },
        'resource': {
            'type': 'consumed_api',
            'labels': {
                'service': 'logging.googleapis.com',
                'project_id': 'fake-target-project'
            }
        },
        'metricKind': 'DELTA',
        'valueType': 'INT64',
        'points': [{
            'interval': {
                'startTime': '2020-05-18T00:00:00Z',
                'endTime': '2020-06-17T00:00:00Z'
            },
            'value': {
                'int64Value': MOCK_LOGGING_METRIC
            }
        }]
    }],
    'unit': '1'
}

MOCK_GCM_METRICS_BUCKETSIZE = {
  "timeSeries": [
    {
      "metric": {
        "labels": {
          "storage_class": "REGIONAL"
        },
        "type": "storage.googleapis.com/storage/total_bytes"
      },
      "resource": {
        "type": "gcs_bucket",
        "labels": {
          "bucket_name": "test_bucket_1",
          "project_id": "fake-project",
          "location": "us-east1"
        }
      },
      "metricKind": "GAUGE",
      "valueType": "DOUBLE",
      "points": [
        {
          "interval": {
            "startTime": "2021-04-07T00:00:00Z",
            "endTime": "2021-04-07T00:00:00Z"
          },
          "value": {
            "doubleValue": 30
          }
        },
        {
          "interval": {
            "startTime": "2021-04-06T00:05:00Z",
            "endTime": "2021-04-06T00:05:00Z"
          },
          "value": {
            "doubleValue": 60
          }
        }
      ]
    }
  ],
  "unit": "By"
}

MOCK_GCSQL_INSTANCES = {
    'items': [
    {
        'kind': 'sql#instance',
        'state': 'RUNNABLE',
        'databaseVersion': 'MYSQL_5_7',
        'settings': {
            'authorizedGaeApplications': [],
            'tier': 'db',
            'kind': 'sql#settings',
            'availabilityType': '5555',
            'pricingPlan': '66666',
            'replicationType': '777777',
            'activationPolicy': '888888',
            'ipConfiguration': {
                'privateNetwork': 'projects/test/networks/default',
                'authorizedNetworks': [],
                'ipv4Enabled': 'false'
            },
            'locationPreference': {
                'zone': 'as-central1-a',
                'kind': 'sql#locationPreference'
            },
            'dataDiskType': 'HDD',
            'maintenanceWindow': {
                'kind': 'sql#maintenanceWindow',
                'hour': '2',
                'day': '3'
            },
            'backupConfiguration': {
                'startTime': '00:00',
                'kind': 'sql#backupConfiguration',
                'location': 'as',
                'enabled': 'true',
                'binaryLogEnabled': 'true',
                'replicationLogArchivingEnabled': 'false',
                'pointInTimeRecoveryEnabled': 'false'
            },
            'settingsVersion': '0',
            'storageAutoResizeLimit': '0',
            'storageAutoResize': 'true',
            'dataDiskSizeGb': '100000'
        },
        'etag': '99999999999',
        'ipAddresses': [
            {
                'type': 'PRIVATE',
                'ipAddress': '10.0.0.0'
            }
        ],
        'serverCaCert': {
            'kind': 'sql#sslCert',
            'certSerialNumber': '0',
            'cert': '222222222',
            'commonName': '11111111',
            'sha1Fingerprint': '33333333',
            'instance': 'test',
            'createTime': '2020',
            'expirationTime': '2030'
        },
        'instanceType': 'FAKE_INSTANCE',
        'project': 'test',
        'serviceAccountEmailAddress': 'test.com',
        'backendType': 'GEN',
        'selfLink': 'test.com',
        'connectionName': 'test:as-central1:test-mysql',
        'name': 'fake',
        'region': 'as-central1',
        'gceZone': 'as-central1-a'
    }
    ]
}

MOCK_GCM_METRICS_CPU_POINTS = [
    {
        'interval': {
            'startTime': '2021-01-01T00:00:00.000000Z',
            'endTime': '2021-01-01T00:00:00.000000Z'
        },
        'value': {
            'doubleValue': 0.100000000000000000
        }
    }
] * 24 * 7

MOCK_GCM_METRICS_CPU = {
    'timeSeries': [
        {
            'metric': {
                'labels': {
                    'instance_name': 'instance-a'
                },
                'type': 'compute.googleapis.com/instance/cpu/utilization'
            },
            'resource': {
                'type': 'gce_instance',
                'labels': {
                    'instance_id': '0000000000000000001',
                    'zone': 'us-central1-a',
                    'project_id': 'fake-project'
                }
            },
            'metricKind': 'GAUGE',
            'valueType': 'DOUBLE',
            'points': MOCK_GCM_METRICS_CPU_POINTS
        },
        {
            'metric': {
                'labels': {
                    'instance_name': 'instance-b'
                },
                'type': 'compute.googleapis.com/instance/cpu/utilization'
            },
            'resource': {
                'type': 'gce_instance',
                'labels': {
                    'instance_id': '0000000000000000002',
                    'zone': 'us-central1-a',
                    'project_id': 'fake-project'
                }
            },
            'metricKind': 'GAUGE',
            'valueType': 'DOUBLE',
            'points': MOCK_GCM_METRICS_CPU_POINTS
        }
    ],
    'unit': '10^2.%'
}

# See: https://cloud.google.com/compute/docs/reference/rest/v1/disks
REGEX_DISK_NAME = re.compile('^(?=.{1,63}$)[a-z]([-a-z0-9]*[a-z0-9])?$')

# pylint: disable=line-too-long
MOCK_SSH_VERBOSE_STDERR = b"""debug1: SSH2_MSG_SERVICE_ACCEPT received
    debug1: Authentications that can continue: publickey,password,keyboard-interactive
    debug1: Next authentication method: publickey"""

MOCK_STORAGE_TRANSFER_JOB = {
    'name': 'transferJobs/12345',
    'description': 'created_by_cfu',
    'projectId': 'fake-project',
    'transferSpec': {
        'awsS3DataSource': {
            'bucketName': 's3_source_bucket'
        },
        'gcsDataSink': {
            'bucketName': 'gcs_sink_bucket', 'path': 'test_path/'
        },
        'objectConditions': {
            'includePrefixes': ['file.name']
        }
    },
    'schedule': {
        'scheduleStartDate': {
            'year': 2021, 'month': 1, 'day': 1
        },
        'scheduleEndDate': {
            'year': 2021, 'month': 1, 'day': 1
        },
        'endTimeOfDay': {}
    },
    'status': 'ENABLED',
    'creationTime': '2021-01-01T06:47:03.533112128Z',
    'lastModificationTime': '2021-01-01T06:47:03.533112128Z'
}

MOCK_STORAGE_TRANSFER_OPERATION = {
    "operations": [{
        "name": "transferOperations/transferJobs-12345-6789",
        "metadata": {
            "@type":
                "type.googleapis.com/google.storagetransfer.v1.TransferOperation",  # pylint: disable=line-too-long
            "name":
                "transferOperations/transferJobs-12345-6789",
            "projectId":
                "fake-project",
            "transferSpec": {
                "awsS3DataSource": {
                    "bucketName": "s3_source_bucket"
                },
                "gcsDataSink": {
                    "bucketName": "gcs_sink_bucket", 'path': 'test_path/'
                },
                "objectConditions": {
                    "includePrefixes": ['file.name']
                }
            },
            "startTime":
                "2021-01-01T06:00:39.321276602Z",
            "endTime":
                "2021-01-01T06:00:59.938282352Z",
            "status":
                "SUCCESS",
            "counters": {
                "objectsFoundFromSource": "1",
                "bytesFoundFromSource": "30",
                "objectsCopiedToSink": "1",
                "bytesCopiedToSink": "30"
            },
            "transferJobName":
                "transferJobs/12345"
        },
        "done": True,
        "response": {
            "@type": "type.googleapis.com/google.protobuf.Empty"
        }
    }]
}

# pylint: disable=line-too-long
MOCK_EFFECTIVE_FIREWALLS = {
    "firewallPolicys": [
        {
            "name": "111111111111",
            "rules": [
                {
                    "action": "allow",
                    "description": "",
                    "direction": "INGRESS",
                    "kind": "compute#firewallPolicyRule",
                    "match": {
                        "layer4Configs": [
                        {
                            "ipProtocol": "tcp"
                        }
                        ],
                        "srcIpRanges": [
                            "8.8.8.8/24"
                        ]
                    },
                    "priority": 1
                }
            ]
        },
        {
            "name": "222222222222",
            "rules": [
                {
                    "action": "goto_next",
                    "description": "",
                    "direction": "INGRESS",
                    "kind": "compute#firewallPolicyRule",
                    "match": {
                        "layer4Configs": [
                        {
                            "ipProtocol": "tcp"
                        }
                        ],
                        "srcIpRanges": [
                        "8.8.4.4/24"
                        ]
                    },
                    "priority": 1
                }
            ]
        }
    ],
    "firewalls": [
        {
            "allowed": [
                {
                    "IPProtocol": "tcp"
                }
            ],
            "creationTimestamp": "2021-01-01T00:00:00.000+00:00",
            "description": "allow all",
            "direction": "INGRESS",
            "disabled": False,
            "id": "1111111111111111111",
            "kind": "compute#firewall",
            "logConfig": {
                "enable": False
            },
            "name": "default-111111111111111111111111",
            "network": "https://www.googleapis.com/compute/v1/projects/fake-project/global/networks/default",
            "priority": 1000,
            "selfLink": "https://www.googleapis.com/compute/v1/projects/fake-project/global/firewalls/default-111111111111111111111111",
            "sourceRanges": [
                "0.0.0.0/0"
            ]
        }
    ]
}
# pylint: enable=line-too-long

MOCK_CLOUD_RESOURCE_PROJECT = {
    "createTime": "2020-01-01T00:00:00.000Z",
    "displayName": "fake-project",
    "etag": "Tm90IGFuIGV0YWd4eHh4eA==",
    "name": "projects/000000000000",
    "parent": "folders/111111111111",
    "projectId": "fake-project",
    "state": "ACTIVE",
    "updateTime": "2020-01-01T00:00:00.000Z"
  }

MOCK_CLOUD_RESOURCE_FOLDER = {
    "createTime": "2020-01-01T00:00:00.000Z",
    "displayName": "fake-folder",
    "etag": "Tm90IGFuIGV0YWd4eHh4eA==",
    "name": "folders/111111111111",
    "parent": "organizations/222222222222",
    "state": "ACTIVE",
    "updateTime": "2020-01-01T00:00:00.000Z"
}

MOCK_CLOUD_RESOURCE_ORGANIZATION = {
    "createTime": "2020-01-01T00:00:00.000Z",
    "directoryCustomerId": "bm9jdXN0",
    "displayName": "fake-organization.com",
    "etag": "Tm90IGFuIGV0YWd4eHh4eA==",
    "name": "organizations/222222222222",
    "state": "ACTIVE",
    "updateTime": "2020-01-01T00:00:00.000Z"
}

# pylint: disable=line-too-long
MOCK_ENABLED_SERVICES = [
    {
        "services": [
            {
                "config": {
                    "name": "bigquery.googleapis.com",
                    "title": "BigQuery API"
                },
                "name": "projects/000000000000/services/bigquery.googleapis.com",
                "state": "ENABLED"
            },
            {
                "config": {
                    "name": "cloudapis.googleapis.com",
                    "title": "Google Cloud APIs"
                },
                "name": "projects/000000000000/services/cloudapis.googleapis.com",
                "state": "ENABLED"
            },
            {
                "config": {
                    "name": "compute.googleapis.com",
                    "title": "Compute Engine API"
                },
                "name": "projects/000000000000/services/compute.googleapis.com",
                "state": "ENABLED"
            }
        ]
    }
]

MOCK_COMPUTE_NETWORK = {
  "id": "3640003993983414",
  "creationTimestamp": "2019-11-15T02:42:01.395-08:00",
  "name": "fake_network",
  "description": "Default network for the project",
  "selfLink": "https://www.googleapis.com/compute/v1/projects/fake-project/global/networks/default",
  "autoCreateSubnetworks": True,
  "subnetworks": [
    "https://www.googleapis.com/compute/v1/projects/fake-project/regions/us-central1/subnetworks/default",
    "https://www.googleapis.com/compute/v1/projects/fake-project/regions/europe-north1/subnetworks/default",
    "https://www.googleapis.com/compute/v1/projects/fake-project/regions/europe-west3/subnetworks/default"
  ],
  "routingConfig": {
    "routingMode": "REGIONAL"
  },
  "kind": "compute#network"
}

MOCK_MACHINE_TYPES = {
  "id": "801030",
  "creationTimestamp": "1969-12-31T16:00:00.000-08:00",
  "name": "c2-standard-30",
  "description": "Compute Optimized: 30 vCPUs, 120 GB RAM",
  "guestCpus": 30,
  "memoryMb": 122880,
  "imageSpaceGb": 0,
  "maximumPersistentDisks": 128,
  "maximumPersistentDisksSizeGb": "263168",
  "zone": "us-central1-a",
  "selfLink": "https://www.googleapis.com/compute/v1/projects/eids-disk-cleaner-test/zones/us-central1-a/machineTypes/c2-standard-30",
  "isSharedCpu": False,
  "kind": "compute#machineType"
}

MOCK_DISK_TYPES = {
  "creationTimestamp": "1969-12-31T16:00:00.000-08:00",
  "name": "pd-standard",
  "description": "Standard Persistent Disk",
  "validDiskSize": "10GB-65536GB",
  "zone": "https://www.googleapis.com/compute/v1/projects/eids-disk-cleaner-test/zones/us-central1-a",
  "selfLink": "https://www.googleapis.com/compute/v1/projects/eids-disk-cleaner-test/zones/us-central1-a/diskTypes/pd-standard",
  "defaultDiskSizeGb": "500",
  "kind": "compute#diskType"
}

MOCK_COMPUTE_IMAGE = {
  "id": "2427010555319344057",
  "creationTimestamp": "2021-09-16T08:40:06.506-07:00",
  "name": "debian-10-buster-v20210916",
  "description": "Debian, Debian GNU/Linux, 10 (buster), amd64 built on 20210916, supports Shielded VM features",
  "sourceType": "RAW",
  "rawDisk": {
    "source": "",
    "containerType": "TAR"
  },
  "status": "READY",
  "archiveSizeBytes": "1180353600",
  "diskSizeGb": "10",
  "licenses": [
    "https://www.googleapis.com/compute/v1/projects/debian-cloud/global/licenses/debian-10-buster"
  ],
  "family": "debian-10",
  "selfLink": "https://www.googleapis.com/compute/v1/projects/debian-cloud/global/images/debian-10-buster-v20210916",
  "labelFingerprint": "42WmSpB8rSM=",
  "guestOsFeatures": [
    {
      "type": "UEFI_COMPATIBLE"
    },
    {
      "type": "VIRTIO_SCSI_MULTIQUEUE"
    }
  ],
  "licenseCodes": [
    "5543610867827062957"
  ],
  "storageLocations": [
    "eu",
    "asia",
    "us"
  ],
  "kind": "compute#image"
}

MOCK_BIGQUERY_JOBS = {
	"etag": "ABCde1FGHiJklmn23op4rs==",
	"kind": "bigquery#jobList",
	"jobs": [{
		"id": "fake-target-project:europe-west1.bquxjob_12345678_abcdefghij1k",
		"kind": "bigquery#job",
		"jobReference": {
			"projectId": "fake-target-project",
			"jobId": "bquxjob_12345678_abcdefghij1k",
			"location": "europe-west1"
		},
		"state": "DONE",
		"statistics": {
			"creationTime": "1640804415278",
			"startTime": "1640804415351",
			"endTime": "1640804415457",
			"totalBytesProcessed": "0",
			"query": {
				"totalBytesProcessed": "0",
				"totalBytesBilled": "0",
				"cacheHit": True,
				"statementType": "SELECT"
			}
		},
		"configuration": {
			"query": {
				"query": "SELECT * FROM `fake-target-project.fake-target-project-dataset.fake-target-project-table`",
				"destinationTable": {
					"projectId": "fake-target-project",
					"datasetId": "_1a2b34c567890d1efghi2j345678kl9012mn34c5",
					"tableId": "anona1234c5d67890123efg45678hij90kl23mnoprst"
				},
				"writeDisposition": "WRITE_TRUNCATE",
				"priority": "INTERACTIVE",
				"useLegacySql": False
			},
			"jobType": "QUERY"
		},
		"status": {
			"state": "DONE"
		},
		"user_email": "fake-user-email@test.com"
	}]
}

MOCK_IAM_POLICY = {
  "version": 1,
  "etag": "bm90X2V0YWc=",
  "bindings": [
    {
      "role": "roles/cloudbuild.builds.builder",
      "members": [
        "serviceAccount:012345678901@cloudbuild.gserviceaccount.com"
      ]
    },
    {
      "role": "roles/owner",
      "members": [
        "serviceAccount:fake_sa@fake-project.iam.gserviceaccount.com",
        "user:fakeaccount@fakedomain.com"
      ]
    }
  ]
}
