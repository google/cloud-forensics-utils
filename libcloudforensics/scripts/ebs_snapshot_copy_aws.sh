#!/bin/bash -x

set -o pipefail

snapshot=%s
bucket=%s

function ebsCopy {
	# params
	snapshot=$1
	bucket=$2

	# Get details about self
	region=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
	az=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)
	instance=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)

	# create the new volume
	volume=$(aws ec2 --region $region create-volume --availability-zone $az --snapshot-id $snapshot --tag-specification 'ResourceType=volume,Tags=[{Key=Name,Value=volumeToCopy}]' | jq -r .VolumeId)

	# wait for create to complete
	aws ec2 --region $region wait volume-available --volume-ids $volume

	# attach the new volume to self
	aws ec2 --region $region attach-volume --device xvdh --instance-id $instance --volume-id $volume

	# wait for the attachment
	aws ec2 --region $region wait volume-in-use --volume-ids $volume
	sleep 5 # let the kernel catch up

	# perform the dd to s3
	# TODO: improve this somehow to not require the double pass
	dd if=/dev/xvdh bs=256K | sha256sum | aws s3 cp - $bucket/$snapshot.sha256
	dd if=/dev/xvdh bs=256K | aws s3 cp - $bucket/$snapshot.bin

	# detach the volume
	aws ec2 --region $region detach-volume --volume-id $volume
	aws ec2 --region $region wait volume-available --volume-ids $volume

	# delete the volume
	aws ec2 --region $region delete-volume --volume-id $volume
}

yum install jq -y

ebsCopy $snapshot $bucket

poweroff
