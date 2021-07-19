#!/bin/bash -x

set -o pipefail

snapshot={0:s}
bucket={1:s}

# This script gets used by python's string.format, so following curly braces need to be doubled

function ebsCopy {{
	# params
	snapshot=$1
	bucket=$2

	# Get details about self
	region=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
	az=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)
	instance=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)

	# create the new volume
	volume=$(aws ec2 --region $region create-volume --availability-zone $az --snapshot-id $snapshot --tag-specification 'ResourceType=volume,Tags=[{{Key=Name,Value=volumeToCopy}}]' | jq -r .VolumeId)

	# wait for create to complete
	aws ec2 --region $region wait volume-available --volume-ids $volume

	# attach the new volume to self
	aws ec2 --region $region attach-volume --device xvdh --instance-id $instance --volume-id $volume

	# wait for the attachment
	aws ec2 --region $region wait volume-in-use --volume-ids $volume
	sleep 5 # let the kernel catch up

	# perform the dd to s3
	dc3dd if=/dev/xvdh hash=sha512 hash=sha256 hash=md5 log=/tmp/log.txt hlog=/tmp/hlog.txt mlog=/tmp/mlog.txt | aws s3 cp - $bucket/$snapshot/image.bin
	aws s3 cp /tmp/log.txt $bucket/$snapshot/
	aws s3 cp /tmp/hlog.txt $bucket/$snapshot/
	aws s3 cp /tmp/mlog.txt $bucket/$snapshot/

	# detach the volume
	aws ec2 --region $region detach-volume --volume-id $volume
	aws ec2 --region $region wait volume-available --volume-ids $volume

	# delete the volume
	aws ec2 --region $region delete-volume --volume-id $volume
}}

amazon-linux-extras install epel -y
yum install jq dc3dd -y

ebsCopy $snapshot $bucket

poweroff
