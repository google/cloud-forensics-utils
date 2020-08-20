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
    FAKE_SOURCE_PROJECT.project_id, 'fake-zone', 'fake-instance')

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

FAKE_LOGS = gcp_log.GoogleCloudLog('fake-target-project')

FAKE_LOG_LIST = [
    'projects/fake-target-project/logs/GCEGuestAgent',
    'projects/fake-target-project/logs/OSConfigAgent'
]

FAKE_LOG_ENTRIES = [{
    'logName': 'test_log',
    'timestamp': '123456789',
    'textPayload': 'insert.compute.create'
}, {
    'logName': 'test_log',
    'timestamp': '123456789',
    'textPayload': 'insert.compute.create'
}]

FAKE_NEXT_PAGE_TOKEN = 'abcdefg1234567'
FAKE_GCS = gcp_storage.GoogleCloudStorage('fake-target-project')
FAKE_GCB = gcp_build.GoogleCloudBuild('fake-target-project')
FAKE_MONITORING = gcp_monitoring.GoogleCloudMonitoring('fake-target-project')

# Mock struct to mimic GCP's API responses
MOCK_INSTANCES_AGGREGATED = {
    # See https://cloud.google.com/compute/docs/reference/rest/v1/instances
    # /aggregatedList for complete structure
    'items': {
        0: {
            'instances': [{
                'name': FAKE_INSTANCE.name,
                'zone': '/' + FAKE_INSTANCE.zone
            }]
        }
    }
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
                'zone': '/' + FAKE_BOOT_DISK.zone
            }]
        },
        1: {
            'disks': [{
                'name': FAKE_DISK.name,
                'zone': '/' + FAKE_DISK.zone
            }]
        }
    }
}

MOCK_LIST_INSTANCES = {FAKE_INSTANCE.name: FAKE_INSTANCE}

MOCK_LIST_DISKS = {
    FAKE_DISK.name: FAKE_DISK,
    FAKE_BOOT_DISK.name: FAKE_BOOT_DISK
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

MOCK_GCE_OPERATION_INSTANCES_GET = {
    # See https://cloud.google.com/compute/docs/reference/rest/v1/instances/get
    # for complete structure
    'name':
        FAKE_INSTANCE.name,
    'disks': [{
        'boot': True,
        'source': '/' + FAKE_BOOT_DISK.name,
    }, {
        'boot': False,
        'source': '/' + FAKE_DISK.name,
        'initializeParams': {
            'diskName': FAKE_DISK.name
        }
    }]
}

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

# See: https://cloud.google.com/compute/docs/reference/rest/v1/disks
REGEX_DISK_NAME = re.compile('^(?=.{1,63}$)[a-z]([-a-z0-9]*[a-z0-9])?$')
STARTUP_SCRIPT = 'scripts/startup.sh'
