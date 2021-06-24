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

import os

from typing import TYPE_CHECKING, Optional
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

  def CreatePolicy(self, name: str, policy_doc: str) -> str:
    """Creates an IAM policy using the name and policy doc passed in.
    If the policy exists already, return the Arn of the existing policy.

    Args:
      name (str): Name for the policy
      policy_doc (str): IAM Policy document as a json string.

    Returns:
      str: Arn of the policy.

    Raises:
      ResourceNotFoundError: If the policy failed creation due to already
        existing, but then could not be found
    """
    logger.info("Creating IAM policy {0:s}".format(name))
    try:
      policy = self.client.create_policy(
        PolicyName=name, PolicyDocument=policy_doc)
      return str(policy['Policy']['Arn'])
    except self.client.exceptions.EntityAlreadyExistsException as exception:
      logger.info("Policy exists already, using existing")
      policies = self.client.list_policies(Scope='Local')

      while True:
        for policy in policies['Policies']:
          if policy['PolicyName'] == name:
            return str(policy['Arn'])

        if not policies['IsTruncated']:
          # If we reached here it means the policy was deleted between the
          # creation failure and lookup
          # pylint: disable=line-too-long
          raise errors.ResourceNotFoundError('Could not locate policy with name {0:s} after creation failure due to EntityAlreadyExistsException'
          # pylint: enable=line-too-long
            .format(name), __name__) from exception

        policies = self.client.list_policies(
          Scope='Local', Marker=policies['Marker'])

  def CreateInstanceProfile(self, name: str) -> str:
    """Create an EC2 instance Profile. If the profile exists already, returns
    the Arn of the existing.

    Args:
      name (str): The name of the instance profile.

    Returns:
      str: The Arn of the instance profile.

    Raises:
      ResourceNotFoundError: If the profile failed creation due to already
        existing, but then could not be found
    """
    try:
      logger.info("Creating IAM Instance Profile {0:s}".format(name))
      profile = self.client.create_instance_profile(InstanceProfileName=name)
      return str(profile['InstanceProfile']['Arn'])
    except self.client.exceptions.EntityAlreadyExistsException as exception:
      logger.info("Instance Profile exists already, using existing")
      profiles = self.client.list_instance_profiles()

      while True:
        for profile in profiles['InstanceProfiles']:
          if profile['InstanceProfileName'] == name:
            return str(profile['Arn'])
        if not profiles['IsTruncated']:
          # If we reached here it means the profile was deleted between the
          # creation failure and lookup
          # pylint: disable=line-too-long
          raise errors.ResourceNotFoundError('Could not locate instance profile with name {0:s} after creation failure due to EntityAlreadyExistsException'
          # pylint: enable=line-too-long
            .format(name), __name__) from exception

        profiles = self.client.list_instance_profiles(Marker=profiles['Marker'])

  def CreateRole(self, name: str, assume_role_policy_doc: str) -> str:
    """Create an AWS IAM role. If it exists, return the existing.

    Args;
      name (str): The name of the role.
      assume_role_policy_doc (str): Assume Role policy doc.

    Returns:
      str: The Arn of the role.

    Raises:
      ResourceNotFoundError: If the role failed creation due to already
        existing, but then could not be found
    """
    try:
      logger.info("Creating IAM Role {0:s}".format(name))
      role = self.client.create_role(RoleName=name,
        AssumeRolePolicyDocument=assume_role_policy_doc)
      return str(role['Role']['Arn'])
    except self.client.exceptions.EntityAlreadyExistsException as exception:
      logger.info("Role exists already, using existing")
      roles = self.client.list_roles()

      while True:
        for role in roles['Roles']:
          if role['RoleName'] == name:
            return str(role['Arn'])
        if not roles['IsTruncated']:
          # If we reached here it means the role was deleted between the
          # creation failure and lookup
          # pylint: disable=line-too-long
          raise errors.ResourceNotFoundError('Could not locate role with name {0:s} after creation failure due to EntityAlreadyExistsException'
          # pylint: enable=line-too-long
            .format(name), __name__) from exception

        roles = self.client.list_roles(Marker=roles['Marker'])

  def AttachPolicyToRole(self, policy_arn: str, role_name: str) -> None:
    """Attaches an IAM policy to an IAM role.

    Args:
      policy_arn (str): The Policy Arn.
      role_name (str): The Role Name.
    """
    logger.info("Attaching policy {0:s} to role {1:s}"
      .format(policy_arn, role_name))
    self.client.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)

  def AttachInstanceProfileToRole(self,
    instance_profile_name: str,
    role_name: str) -> None:
    """Attach a role to an instance profile.

    Args:
      instance_profile_name: The name fo the instance profile.
      role_name: The role name.
    """
    try:
      logger.info("Attaching role {0:s} to instance profile {1:s}"
        .format(role_name, instance_profile_name))
      self.client.add_role_to_instance_profile(
        InstanceProfileName=instance_profile_name, RoleName=role_name)
    except self.client.exceptions.LimitExceededException:
      # pylint: disable=line-too-long
      logger.info("Instance profile {0:s} already has a role attached. Proceeding on assumption this is the correct attachment"
      # pylint: enable=line-too-long
        .format(instance_profile_name))

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
