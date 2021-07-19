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
"""Library for incident response operations on AWS EC2.

Library to make forensic images of Amazon Elastic Block Store devices and create
analysis virtual machine to be used in incident response.
"""

from typing import Optional, TYPE_CHECKING
import boto3

from libcloudforensics.providers.aws.internal import ec2
from libcloudforensics.providers.aws.internal import ebs
from libcloudforensics.providers.aws.internal import iam
from libcloudforensics.providers.aws.internal import kms
from libcloudforensics.providers.aws.internal import s3

if TYPE_CHECKING:
  import botocore


class AWSAccount:
  """Class representing an AWS account.

  Attributes:
    default_availability_zone (str): Default zone within the region to create
        new resources in.
    default_region (str): The default region to create new resources in.
    aws_profile (str): The AWS profile defined in the AWS
        credentials file to use.
    session (boto3.session.Session): A boto3 session object.
    _ec2 (AWSEC2): An AWS EC2 client object.
    _ebs (AWSEBS): An AWS EBS client object.
    _kms (AWSKMS): An AWS KMS client object.
    _s3 (AWSS3): An AWS S3 client object.
  """

  def __init__(self,
               default_availability_zone: str,
               aws_profile: Optional[str] = None,
               aws_access_key_id: Optional[str] = None,
               aws_secret_access_key: Optional[str] = None,
               aws_session_token: Optional[str] = None) -> None:
    """Initialize the AWS account.

    Args:
      default_availability_zone (str): Default zone within the region to create
          new resources in.
      aws_profile (str): Optional. The AWS profile defined in the AWS
          credentials file to use.
      aws_access_key_id (str): Optional. If provided together with
          aws_secret_access_key and aws_session_token, authenticate to AWS
          using these parameters instead of the credential file.
      aws_secret_access_key (str): Optional. If provided together with
          aws_access_key_id and aws_session_token, authenticate to AWS
          using these parameters instead of the credential file.
      aws_session_token (str): Optional. If provided together with
          aws_access_key_id and aws_secret_access_key, authenticate to AWS
          using these parameters instead of the credential file.
    """

    self.default_availability_zone = default_availability_zone
    # The region is given by the zone minus the last letter
    # https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html#using-regions-availability-zones-describe # pylint: disable=line-too-long
    self.default_region = self.default_availability_zone[:-1]

    if aws_access_key_id and aws_secret_access_key and aws_session_token:
      self.session = boto3.session.Session(
          aws_access_key_id=aws_access_key_id,
          aws_secret_access_key=aws_secret_access_key,
          aws_session_token=aws_session_token)
    elif aws_profile:
      self.aws_profile = aws_profile
      self.session = boto3.session.Session(profile_name=self.aws_profile)
    else:
      self.session = boto3.session.Session()

    self._ec2 = None  # type: Optional[ec2.EC2]
    self._ebs = None  # type: Optional[ebs.EBS]
    self._kms = None  # type: Optional[kms.KMS]
    self._s3 = None  # type: Optional[s3.S3]
    self._iam = None # type: Optional[iam.IAM]

  @property
  def ec2(self) -> ec2.EC2:
    """Get an AWS ec2 object for the account.

    Returns:
      AWSEC2: Object that represents AWS EC2 services.
    """

    if self._ec2:
      return self._ec2
    self._ec2 = ec2.EC2(self)
    return self._ec2

  @property
  def ebs(self) -> ebs.EBS:
    """Get an AWS ebs object for the account.

    Returns:
      AWSEBS: Object that represents AWS EBS services.
    """

    if self._ebs:
      return self._ebs
    self._ebs = ebs.EBS(self)
    return self._ebs

  @property
  def kms(self) -> kms.KMS:
    """Get an AWS kms object for the account.

    Returns:
      AWSKMS: Object that represents AWS KMS services.
    """

    if self._kms:
      return self._kms
    self._kms = kms.KMS(self)
    return self._kms

  @property
  def s3(self) -> s3.S3:
    """Get an AWS S3 object for the account.

    Returns:
      AWSS3: Object that represents AWS S3 services.
    """

    if self._s3:
      return self._s3
    self._s3 = s3.S3(self)
    return self._s3

  @property
  def iam(self) -> iam.IAM:
    """Get an AWS IAM object for the account.

    Returns:
      AWSIAM: Object that represents AWS IAM services.
    """

    if self._iam:
      return self._iam
    self._iam = iam.IAM(self)
    return self._iam

  def ClientApi(self,
                service: str,
                region: Optional[str] = None) -> 'botocore.client.EC2':  # pylint: disable=no-member
    """Create an AWS client object.

    Args:
      service (str): The AWS service to use.
      region (str): Optional. The region in which to create new resources. If
          none provided, the default_region associated to the AWSAccount
          object will be used.
    Returns:
      botocore.client.EC2: An AWS EC2 client object.
    """

    if region:
      return self.session.client(service_name=service, region_name=region)
    return self.session.client(
        service_name=service, region_name=self.default_region)

  def ResourceApi(self,
                  service: str,
                  # The return type doesn't exist until Runtime, therefore we
                  # need to ignore the type hint
                  # pylint: disable=line-too-long
                  region: Optional[str] = None) -> 'boto3.resources.factory.ec2.ServiceResource':  # type: ignore
                  # pylint: enable=line-too-long
    """Create an AWS resource object.

    Args:
      service (str): The AWS service to use.
      region (str): Optional. The region in which to create new resources. If
          none provided, the default_region associated to the AWSAccount
          object will be used.

    Returns:
      boto3.resources.factory.ec2.ServiceResource: An AWS EC2 resource object.
    """

    if region:
      return self.session.resource(service_name=service, region_name=region)
    return self.session.resource(
        service_name=service, region_name=self.default_region)
