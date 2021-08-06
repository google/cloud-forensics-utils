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
"""Google Cloud Storage Transfer functionalities."""


from typing import TYPE_CHECKING, Dict, Any, Optional
import datetime
import time

from libcloudforensics import errors
from libcloudforensics import logging_utils
from libcloudforensics.providers.aws.internal import account
from libcloudforensics.providers.gcp.internal import common
from libcloudforensics.providers.utils.storage_utils import SplitStoragePath

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)

if TYPE_CHECKING:
  import googleapiclient


class GoogleCloudStorageTransfer:
  """Class to call Google Cloud Storage Transfer APIs.

  Attributes:
    gcst_api_client: Client to interact with GCST APIs.
    project_id: Google Cloud project ID.
  """
  CLOUD_STORAGE_TRANSFER_API_VERSION = 'v1'

  def __init__(self, project_id: Optional[str] = None) -> None:
    """Initialize the GoogleCloudStorageTransfer object.

    Args:
      project_id (str): Optional. Google Cloud project ID.
    """

    self.gcst_api_client = None
    self.project_id = project_id

  def GcstApi(self) -> 'googleapiclient.discovery.Resource':
    """Get a Google Cloud Storage Transfer service object.

    Returns:
      googleapiclient.discovery.Resource: A Google Cloud Storage Transfer
        service object.
    """

    if self.gcst_api_client:
      return self.gcst_api_client
    self.gcst_api_client = common.CreateService(
        'storagetransfer', self.CLOUD_STORAGE_TRANSFER_API_VERSION)
    return self.gcst_api_client

  def S3ToGCS(self, s3_path: str, zone: str, gcs_path: str) -> Dict[str, Any]:
    """Copy an S3 object to a GCS bucket.

    Args:
      s3_path (str): File path to the S3 resource.
          Ex: s3://test/bucket/obj
      zone (str): The AWS zone in which resources are located.
        Available zones are listed at:
        https://cloud.google.com/storage-transfer/docs/create-manage-transfer-program#s3-to-cloud  # pylint: disable=line-too-long
      gcs_path (str): File path to the target GCS bucket.
          Ex: gs://bucket/folder
    Returns:
      Dict: An API operation object for a Google Cloud Storage Transfer operation.
        https://cloud.google.com/storage-transfer/docs/reference/rest/v1/transferOperations/list  # pylint: disable=line-too-long
    Raises:
      TransferCreationError: If the transfer couldn't be created.
      TransferExecutionError: If the transfer couldn't be run.
    """
    aws_creds = account.AWSAccount(zone).session.get_credentials()
    if (aws_creds is None or aws_creds.access_key is None or
        aws_creds.access_key.startswith('ASIA')):
      raise errors.TransferCreationError(
          'Could not create transfer. No long term AWS credentials available',
          __name__)
    s3_bucket, s3_path = SplitStoragePath(s3_path)
    gcs_bucket, gcs_path = SplitStoragePath(gcs_path)
    if not gcs_path.endswith('/'):
      gcs_path = gcs_path + '/'
    # Don't specify a path if we're writing to the bucket root.
    if gcs_path == '/':
      gcs_path = ''
    today = datetime.datetime.now()
    transfer_job_body = {
        'projectId': self.project_id,
        'description': 'created_by_cfu',
        'transferSpec': {
            'objectConditions': {
                'includePrefixes': [s3_path]
            },
            'awsS3DataSource': {
                'bucketName': s3_bucket,
                'awsAccessKey': {
                    'accessKeyId': aws_creds.access_key,
                    'secretAccessKey': aws_creds.secret_key
                }
            },
            'gcsDataSink': {
                'bucketName': gcs_bucket, 'path': gcs_path
            }
        },
        'schedule': {
            'scheduleStartDate': {
                'year': today.year, 'month': today.month, 'day': today.day
            },
            'scheduleEndDate': {
                'year': today.year, 'month': today.month, 'day': today.day
            },
            'endTimeOfDay': {}
        },
        'status': 'ENABLED'
    }
    logger.info('Creating transfer job')
    gcst_jobs = self.GcstApi().transferJobs()
    create_request = gcst_jobs.create(body=transfer_job_body)
    transfer_job = create_request.execute()
    logger.info('Job created: {0:s}'.format(str(transfer_job)))
    job_name = transfer_job.get('name', None)
    if job_name is None:
      raise errors.TransferCreationError(
          'Could not create transfer. Job output: {0:s}'.format(
              str(transfer_job)),
          __name__)
    logger.info('Job created: {0:s}'.format(job_name))
    gcst_transfers = self.GcstApi().transferOperations()
    filter_string = ('{{"projectId": "{0:s}", "jobNames": ["{1:s}"]}}').format(
        self.project_id, job_name)
    status = {}
    while 'operations' not in status:
      time.sleep(5)
      status = gcst_transfers.list(
          name='transferOperations', filter=filter_string).execute()
      logger.info('Waiting for transfer to start...')
    logger.info('Job status: {0:s}'.format(str(status)))
    while not status['operations'][0].get('done'):
      time.sleep(5)
      status = gcst_transfers.list(
          name='transferOperations', filter=filter_string).execute()
      logger.info('Waiting to finish...')
      logger.info(status)
    error = status['operations'][0].get('error', None)
    if error:
      raise errors.TransferExecutionError(
          'Could not execute transfer. Job output: {0:s}'.format(str(status)),
          __name__)
    counters = status['operations'][0].get('metadata', {}).get('counters', {})
    logger.info(
        'Transferred {0:s}/{1:s} files ({2:s}/{3:s} bytes).'.format(
            counters.get('objectsFoundFromSource', '0'),
            counters.get('objectsCopiedToSink', '0'),
            counters.get('bytesFoundFromSource', '0'),
            counters.get('bytesCopiedToSink', '0')))
    logger.info(
        'Skipped {0:s} files ({1:s} bytes).'.format(
            counters.get('objectsFromSourceSkippedBySync', '0'),
            counters.get('bytesFromSourceSkippedBySync', '0')))
    return status
