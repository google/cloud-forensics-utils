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
"""Log functionality."""
from typing import TYPE_CHECKING, Dict, List, Optional, Any

from libcloudforensics.providers.aws.internal import common

if TYPE_CHECKING:
  # TYPE_CHECKING is always False at runtime, therefore it is safe to ignore
  # the following cyclic import, as it it only used for type hints
  from libcloudforensics.providers.aws.internal import account  # pylint: disable=cyclic-import
  from datetime import datetime


class AWSCloudTrail:
  """Class representing an AWS CloudTrail service.

  Attributes:
    aws_account (AWSAccount): The AWS account to use.
  """

  def __init__(self, aws_account: 'account.AWSAccount') -> None:
    """Initialize an AWS CloudTrail client.

    Args:
      aws_account (AWSAccount): The AWS account to use.
    """

    self.aws_account = aws_account

  def LookupEvents(
      self,
      qfilter: Optional[str] = None,
      starttime: Optional['datetime'] = None,
      endtime: Optional['datetime'] = None) -> List[Dict[str, Any]]:
    """Lookup events in the CloudTrail logs of this account.

    Example usage:
      # pylint: disable=line-too-long
      # qfilter = 'key,value'
      # starttime = datetime(2020,5,5,17,33,00)
      # LookupEvents(qfilter=qfilter, starttime=starttime)
      # Check documentation for qfilter details
      # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudtrail.html#CloudTrail.Client.lookup_events

    Args:
      qfilter (string): Optional. Filter for the query including 1 key and value.
      starttime (datetime): Optional. Start datetime to add to query filter.
      endtime (datetime): Optional. End datetime to add to query filter.

    Returns:
      List[Dict]: A list of events. E.g. [{'EventId': 'id', ...},
          {'EventId': ...}]
    """

    events = []

    client = self.aws_account.ClientApi(common.CLOUDTRAIL_SERVICE)

    params = {}  # type: Dict[str, Any]
    if qfilter:
      k, v = qfilter.split(',')
      filters = [{'AttributeKey': k, 'AttributeValue': v}]
      params = {'LookupAttributes': filters}
    if starttime:
      params['StartTime'] = starttime
    if endtime:
      params['EndTime'] = endtime

    responses = common.ExecuteRequest(client, 'lookup_events', params)
    for response in responses:
      for entry in response['Events']:
        events.append(entry)
    return events
