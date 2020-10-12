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
"""KMS functionality."""

import json
from typing import Optional, TYPE_CHECKING

from libcloudforensics import errors
from libcloudforensics.providers.aws.internal import common

if TYPE_CHECKING:
  # TYPE_CHECKING is always False at runtime, therefore it is safe to ignore
  # the following cyclic import, as it it only used for type hints
  from libcloudforensics.providers.aws.internal import account  # pylint: disable=cyclic-import


class KMS:
  """Class that represents AWS KMS services."""

  def __init__(self,
               aws_account: 'account.AWSAccount') -> None:
    """Initialize the AWS KMS client object.

    Args:
      aws_account (AWSAccount): An AWS account object.
    """
    self.aws_account = aws_account

  def CreateKMSKey(self) -> str:
    """Create a KMS key.

    Returns:
      str: The KMS key ID for the key that was created.

    Raises:
      ResourceCreationError: If the key could not be created.
    """

    client = self.aws_account.ClientApi(common.KMS_SERVICE)
    try:
      kms_key = client.create_key()
    except client.exceptions.ClientError as exception:
      raise errors.ResourceCreationError(
          'Could not create KMS key: {0!s}'.format(
              exception), __name__) from exception

    # The response contains the key ID
    key_id = kms_key['KeyMetadata']['KeyId']  # type: str
    return key_id

  def ShareKMSKeyWithAWSAccount(self,
                                kms_key_id: str,
                                aws_account_id: str) -> None:
    """Share a KMS key.

    Args:
      kms_key_id (str): The KMS key ID of the key to share.
      aws_account_id (str): The AWS Account ID to share the KMS key with.

    Raises:
      RuntimeError: If the key could not be shared.
    """

    share_policy = {
        'Sid': 'Allow use of the key',
        'Effect': 'Allow',
        'Principal': {
            'AWS': 'arn:aws:iam::{0:s}:root'.format(aws_account_id)
        },
        'Action': [
            # kms:*crypt and kms:ReEncrypt* are necessary to transfer
            # encrypted EBS resources across accounts.
            'kms:Encrypt',
            'kms:Decrypt',
            'kms:ReEncrypt*',
            # kms:CreateGrant is necessary to transfer encrypted EBS
            # resources across regions.
            'kms:CreateGrant'
        ],
        'Resource': '*'
    }
    client = self.aws_account.ClientApi(common.KMS_SERVICE)
    try:
      policy = json.loads(client.get_key_policy(
          KeyId=kms_key_id, PolicyName='default')['Policy'])
      policy['Statement'].append(share_policy)
      # Update the key policy so that it is shared with the AWS account.
      client.put_key_policy(
          KeyId=kms_key_id, PolicyName='default', Policy=json.dumps(policy))
    except client.exceptions.ClientError as exception:
      raise RuntimeError('Could not share KMS key {0:s}: {1:s}'.format(
          kms_key_id, str(exception))) from exception

  def DeleteKMSKey(self, kms_key_id: Optional[str] = None) -> None:
    """Delete a KMS key.

    Schedule the KMS key for deletion. By default, users have a 30 days
        window before the key gets deleted.

    Args:
      kms_key_id (str): The ID of the KMS key to delete.

    Raises:
      ResourceDeletionError: If the key could not be scheduled for deletion.
    """

    if not kms_key_id:
      return

    client = self.aws_account.ClientApi(common.KMS_SERVICE)
    try:
      client.schedule_key_deletion(KeyId=kms_key_id)
    except client.exceptions.ClientError as exception:
      raise errors.ResourceDeletionError(
          'Could not schedule the KMS key {0:s} for deletion {1!s}'.format(
              exception, kms_key_id), __name__) from exception
