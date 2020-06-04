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
from libcloudforensics.providers.aws.internal import common


class AWSCloudTrail:
  """Class representing an AWS CloudTrail service.

  Attributes:
    aws_account (AWSAccount): The AWS account to use.
  """

  def __init__(self, aws_account):
    """Initialize an AWS CloudTrail client.

    Args:
      aws_account (AWSAccount): The AWS account to use.
    """

    self.aws_account = aws_account

  def LookupEvents(self,
                   qfilter=(),
                   starttime=None,
                   endtime=None):
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
      list(dict): A list of events.
    """

    events = []

    client = self.aws_account.ClientApi(common.CLOUDTRAIL_SERVICE)

    params = {}
    if qfilter:
      k, v = qfilter.split(',')
      qfilter = [{'AttributeKey': k, 'AttributeValue': v}]
      params = {'LookupAttributes': qfilter}
    if starttime:
      params['StartTime'] = starttime
    if endtime:
      params['EndTime'] = endtime

    responses = common.ExecuteRequest(client, 'lookup_events', params)
    for response in responses:
      for entry in response['Events']:
        events.append(entry)
    return events
