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
"""AWS IAM Functionality"""

import datetime
import json
import os
from typing import TYPE_CHECKING, Optional, Tuple
from libcloudforensics import errors
from libcloudforensics import logging_utils
from libcloudforensics.providers.aws.internal import common

if TYPE_CHECKING:
  # TYPE_CHECKING is always False at runtime, therefore it is safe to ignore
  # the following cyclic import, as it it only used for type hints
  from libcloudforensics.providers.aws.internal import account  # pylint: disable=cyclic-import

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)

IAM_POLICY_DIR = './iampolicies'

# Policy allowing an instance to image a volume
EBS_COPY_POLICY_DOC = 'ebs_copy_to_s3_policy.json'

# Policy doc to allow EC2 to assume the role. Necessary for instance profiles
EC2_ASSUME_ROLE_POLICY_DOC = 'ec2_assume_role_policy.json'

# Policy to deny all session tokens generated after a date
IAM_DENY_ALL_AFTER_TOKEN_ISSUE_DATE = 'revoke_old_sessions.json'


class IAM:
  """Class that represents AWS IAM services"""
  def __init__(self,
               aws_account: 'account.AWSAccount') -> None:
    """Initialize the AWS IAM client object.

    Args:
      aws_account (AWSAccount): An AWS account object.
    """
    self.aws_account = aws_account
    self.client = self.aws_account.ClientApi(common.IAM_SERVICE)

  def CheckInstanceProfileExists(self, profile_name: str) -> bool:
    """Check if an instance role exists.

    Args:
      profile_name (str): Instance profile name.

    Returns:
      bool: True if the Instance Profile exists, false otherwise.
    """

    try:
      self.client.get_instance_profile(InstanceProfileName=profile_name)
      return True
    except self.client.exceptions.NoSuchEntityException:
      return False

  def CreatePolicy(self, name: str, policy_doc: str) -> Tuple[str, bool]:
    """Creates an IAM policy using the name and policy doc passed in.
    If the policy exists already, return the Arn of the existing policy.

    Args:
      name (str): Name for the policy
      policy_doc (str): IAM Policy document as a json string.

    Returns:
      Tuple[str, bool]: A tuple containing:
        str: The policy Amazon Resource Name (ARN).
        bool: True if the policy was created, False if it existed already.

    Raises:
      ResourceNotFoundError: If the policy failed creation due to already
        existing, but then could not be found
    """
    logger.info('Creating IAM policy {0:s}'.format(name))
    try:
      policy = self.client.create_policy(
        PolicyName=name, PolicyDocument=policy_doc)
      return str(policy['Policy']['Arn']), True
    except self.client.exceptions.EntityAlreadyExistsException as exception:
      logger.info('Policy exists already, using existing')
      policies = self.client.list_policies(Scope='Local')

      while True:
        for policy in policies['Policies']:
          if policy['PolicyName'] == name:
            return str(policy['Arn']), False

        if not policies['IsTruncated']:
          # If we reached here it means the policy was deleted between the
          # creation failure and lookup
          # pylint: disable=line-too-long
          raise errors.ResourceNotFoundError('Could not locate policy with name {0:s} after creation failure due to EntityAlreadyExistsException'
          # pylint: enable=line-too-long
            .format(name), __name__) from exception

        policies = self.client.list_policies(
          Scope='Local', Marker=policies['Marker'])

  def DeletePolicy(self, arn: str) -> None:
    """Deletes the IAM policy with the given name.

    Args:
      name (str): The ARN of the policy to delete.
    """
    logger.info('Deleting IAM policy {0:s}'.format(arn))
    try:
      self.client.delete_policy(PolicyArn=arn)
    except self.client.exceptions.NoSuchEntityException:
      logger.info('IAM policy {0:s} did not exist'.format(arn))

  def CreateInstanceProfile(self, name: str) -> Tuple[str, bool]:
    """Create an EC2 instance Profile. If the profile exists already, returns
    the Arn of the existing.

    Args:
      name (str): The name of the instance profile.

    Returns:
      Tuple[str, bool]: A tuple containing:
        str: The instance profile Amazon Resource Name (ARN).
        bool: True if the instance profile was created, False if it existed
          already.

    Raises:
      ResourceNotFoundError: If the profile failed creation due to already
        existing, but then could not be found
    """
    logger.info('Creating IAM Instance Profile {0:s}'.format(name))
    try:
      profile = self.client.create_instance_profile(InstanceProfileName=name)
      return str(profile['InstanceProfile']['Arn']), True
    except self.client.exceptions.EntityAlreadyExistsException as exception:
      logger.info('Instance Profile exists already, using existing')
      profiles = self.client.list_instance_profiles()

      while True:
        for profile in profiles['InstanceProfiles']:
          if profile['InstanceProfileName'] == name:
            return str(profile['Arn']), False
        if not profiles['IsTruncated']:
          # If we reached here it means the profile was deleted between the
          # creation failure and lookup
          # pylint: disable=line-too-long
          raise errors.ResourceNotFoundError('Could not locate instance profile with name {0:s} after creation failure due to EntityAlreadyExistsException'
          # pylint: enable=line-too-long
            .format(name), __name__) from exception

        profiles = self.client.list_instance_profiles(Marker=profiles['Marker'])

  def DeleteInstanceProfile(self, profile_name: str) -> None:
    """Deletes an instance profile.

    Args:
      profile_name (str): The name of the instance profile to delete.
    """
    logger.info('Deleting instance profile {0:s}'.format(profile_name))
    try:
      self.client.delete_instance_profile(InstanceProfileName=profile_name)
    except self.client.exceptions.NoSuchEntityException:
      logger.info('IAM role {0:s} did not exist'.format(profile_name))

  def CreateRole(self, name: str, assume_role_policy_doc: str) \
    -> Tuple[str, bool]:
    """Create an AWS IAM role. If it exists, return the existing.

    Args;
      name (str): The name of the role.
      assume_role_policy_doc (str): Assume Role policy doc.

    Returns:
      Tuple[str, bool]: A tuple
        str: The Arn of the role.
        bool: True if the role was created, false if it existed already.

    Raises:
      ResourceNotFoundError: If the role failed creation due to already
        existing, but then could not be found
    """
    logger.info('Creating IAM Role {0:s}'.format(name))
    try:
      role = self.client.create_role(RoleName=name,
        AssumeRolePolicyDocument=assume_role_policy_doc)
      return str(role['Role']['Arn']), True
    except self.client.exceptions.EntityAlreadyExistsException as exception:
      logger.info('Role exists already, using existing')
      roles = self.client.list_roles()

      while True:
        for role in roles['Roles']:
          if role['RoleName'] == name:
            return str(role['Arn']), False
        if not roles['IsTruncated']:
          # If we reached here it means the role was deleted between the
          # creation failure and lookup
          # pylint: disable=line-too-long
          raise errors.ResourceNotFoundError('Could not locate role with name {0:s} after creation failure due to EntityAlreadyExistsException'
          # pylint: enable=line-too-long
            .format(name), __name__) from exception

        roles = self.client.list_roles(Marker=roles['Marker'])

  def DeleteRole(self, role_name: str) -> None:
    """Delete an IAM role.

    Args:
      role_name (str): The name of the role to delete.
    """
    logger.info('Deleting IAM role {0:s}'.format(role_name))
    try:
      self.client.delete_role(RoleName=role_name)
    except self.client.exceptions.NoSuchEntityException:
      logger.info('IAM role {0:s} did not exist'.format(role_name))

  def AttachPolicyToRole(self, policy_arn: str, role_name: str) -> None:
    """Attaches an IAM policy to an IAM role.

    Args:
      policy_arn (str): The Policy Arn.
      role_name (str): The Role Name.
    """
    logger.info('Attaching policy {0:s} to role {1:s}'
      .format(policy_arn, role_name))
    try:
      self.client.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
    except Exception as e:
      raise errors.ResourceNotFoundError(
        'Attaching policy {0:s} to role {1:s} failed'
        .format(policy_arn, role_name), __name__) from e

  def DetachPolicyFromRole(self, policy_arn: str, role_name :str) -> None:
    """Detach a policy from a role.

    Args:
      policy_arn (str): The Arn of the policy to remove.
      role_name (str): The name of the role.
    """
    logger.info('Detaching policy {0:s} from role {1:s}'
      .format(policy_arn, role_name))
    try:
      self.client.detach_role_policy(
        RoleName=role_name, PolicyArn=policy_arn)
    except self.client.exceptions.NoSuchEntityException:
      pass
      # It doesn't matter if this fails.

  def AttachInstanceProfileToRole(self,
    instance_profile_name: str,
    role_name: str) -> None:
    """Attach a role to an instance profile.

    Args:
      instance_profile_name: The name fo the instance profile.
      role_name: The role name.
    """
    logger.info('Attaching role {0:s} to instance profile {1:s}'
      .format(role_name, instance_profile_name))
    try:
      self.client.add_role_to_instance_profile(
        InstanceProfileName=instance_profile_name, RoleName=role_name)
    except self.client.exceptions.LimitExceededException:
      # pylint: disable=line-too-long
      logger.info('Instance profile {0:s} already has a role attached. Proceeding on assumption this is the correct attachment'
      # pylint: enable=line-too-long
        .format(instance_profile_name))

  def DetachInstanceProfileFromRole(self, role_name: str, profile_name: str) \
    -> None:
    """Detach a role from an instance profile.

    Args:
      role_name (str): The name of the role.
      profile_name (str): The name of the instance profile.
    """
    logger.info('Detaching role {0:s} from instance profile {1:s}'
      .format(role_name, profile_name))
    try:
      self.client.remove_role_from_instance_profile(
        InstanceProfileName=profile_name, RoleName=role_name)
    except self.client.exceptions.NoSuchEntityException:
      pass
      # It doesn't matter if this fails.

  def RevokeOldSessionsForRole(self, role_name: str) -> None:
    """Revoke old session tokens for a role.

    This is acheived by adding an inline policy to the role, Deny *:* on the
    condition of TokenIssueTime.

    Args:
      role_name (str): The role name to act on.
    """
    now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z")
    policy = json.loads(ReadPolicyDoc(IAM_DENY_ALL_AFTER_TOKEN_ISSUE_DATE))
    policy['Statement'][0]['Condition']['DateLessThan']['aws:TokenIssueTime']\
      = now
    policy = json.dumps(policy)

    try:
      self.client.put_role_policy(
        RoleName=role_name,
        PolicyName='RevokeOldSessions',
        PolicyDocument=policy
      )
    except self.client.exceptions.ClientError as exception:
      raise errors.ResourceNotFoundError(
        'Could not add inline policy to IAM role {0:s}: {1!s}'.format(
          role_name, exception), __name__) from exception

def ReadPolicyDoc(filename: str) -> str:
  """Read and return the IAM policy doc at filename.

  Args:
    filename (str): the name of the policy file in the iampolicies directory.

  Returns:
    str: The policy doc.

  Raises:
    OSError: If the policy file cannot be opened, read or closed.
  """

  try:
    policy_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), IAM_POLICY_DIR, filename)
    with open(policy_path) as policy_doc:
      return policy_doc.read()
  except OSError as exception:
    raise OSError(
        'Could not open/read/close the policy doc {0:s}: {1:s}'.format(
            policy_path, str(exception))) from exception
