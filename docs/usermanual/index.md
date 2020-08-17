# libcloudforensics capabilities

## GCP

### Disk snapshot

TODO

### GCS to persistent disk

TODO

### Analysis VM

TODO


## AWS

### Prerequisites

Your AWS credentials configuration (`~/.aws/credentials`) should look like this:

```text
# Access credentials to Account A
[src_profile]
aws_access_key_id = xxx
aws_secret_access_key = xxx

# Access credentials to Account B
[dst_profile]
aws_access_key_id = yyy
aws_secret_access_key = yyy

# Access credentials to the default account to use with AWS operations. Note that this can be the same account as one 
# of the accounts above. This is the account that will be used by libcloudforensics for AWSAccount objects that are not 
# instantiated with a particular profile.
[default]
aws_access_key_id = zzz
aws_secret_access_key = zzz
```

### Disk snapshot

Use case: you have a volume `vol1` in an AWS account (Account A, in zone `us-east-2b`) which you would like to make a copy 
of in a different account (Account B).

#### Using the library and the CLI

To make the copy, import the `forensics` package and use the `CreateVolumeCopy` method.

```python
from libcloudforensics.providers.aws import forensics

# Create a copy of the volume 'vol1' from one account to another 

copy = forensics.CreateVolumeCopy('us-east-2b',
                                  volume_id='vol1', 
                                  src_profile='src_profile', 
                                  dst_profile='analysis_profile')
```

The equivalent CLI command is:

```bash
# Create a copy of the volume 'vol1' from one account to another 
cloudforensics aws 'us-east-2b' copydisk --volume_id='vol1' --src_profile='src_profile' --dst_profile='dst_profile' 
```

If you want to make the copy in a different zone, just specify `dst_zone` in the above method.
You can also pass a dictionary of tags to add to the volume copy.

```python
from libcloudforensics.providers.aws import forensics

# Create a copy of the volume 'vol1' from one account to another, in a different zone

copy = forensics.CreateVolumeCopy('us-east-2b',
                                  dst_zone='us-west-2a',
                                  volume_id='vol1', 
                                  src_profile='src_profile', 
                                  dst_profile='analysis_profile',
                                  tags={'customTag': 'customValue'})
```

The equivalent CLI command is:

```bash
# Create a copy of the volume 'vol1' from one account to another, in a different zone
cloudforensics aws 'us-east-2b' copydisk --dst_zone='us-west-2a' --volume_id='vol1' --src_profile='src_profile' --dst_profile='dst_profile' --tags="{'customTag': 'customValue'}" 
```

Finally, you can opt to pass an `instance_id` parameter to the method instead of a `volume_id`.
If you do so, then the boot volume of the instance pointed to by `instance_id` will be copied.

```python
from libcloudforensics.providers.aws import forensics

# Create a copy of the boot volume of instance 'inst1' in the default account.

copy = forensics.CreateVolumeCopy('us-east-2b',
                                  instance_id='inst1')
```

The equivalent CLI command is:

```bash
# Create a copy of the boot volume of instance 'inst1' in the default account
cloudforensics aws 'us-east-2b' copydisk --instance_id='inst1'
```    

#### EBS encryption

Making copies of encrypted resources is a bit more involved. By default, encrypted Elastic Block Store (EBS) resources 
use the aws/ebs key that is associated with the AWS account. Snapshots that are encrypted with this key cannot be shared 
directly. Instead, you must first make a copy of the snapshot, and re-encrypt it with a Customer Managed Key (CMK). 
Both the CMK and the snapshot copy need to then be shared with the destination account.


To reduce key management hassle, libcloudforensics allows you to transfer encrypted EBS resources between accounts by 
generating a one-time use CMK. This key is deleted once the process completes. The process is depicted below:

![ebs-encryption](https://github.com/google/cloud-forensics-utils/blob/master/docs/source/images/ebs.png?raw=true)

All of the code snippets and command lines given in the [previous section](#using-the-library-and-the-cli) can be 
applied as-is, regardless of whether the target volume uses EBS encryption or not.

### Analysis VMs

Use case: you have a volume `vol1` in an AWS account (Account A, in zone `us-east-2b`) which you would like to make a copy 
of in a different account (Account B). Afterwards, you want to start an analysis VM in Account B, and attach the disk 
copy that you created to begin your investigation.

Your AWS credentials configuration should be similar to what is described [above](#aws).

Using the library, you can start an analysis VM as follows:

```python
from libcloudforensics.providers.aws import forensics

# Create a copy of the volume 'vol1' from one account to another 

copy = forensics.CreateVolumeCopy('us-east-2b',
                                  volume_id='vol1', 
                                  src_profile='src_profile', 
                                  dst_profile='dst_profile')

# Start an analysis VM 'vm-forensics' for investigation in the AWS account 
# dst_profile, and attach the copy created in the previous step.

analysis_vm, _ = forensics.StartAnalysisVm('vm-forensics',
                                           'us-east-2b', 
                                            50, 
                                            cpu_cores=4,
                                            attach_volumes=[(copy.volume_id, '/dev/sdf')], 
                                            dst_profile='dst_profile')
```

The equivalent CLI command is:

```bash
# Create a copy of the volume 'vol1' in the dst_account AWS account.
# In this scenario we consider that the final volume copy name is 'vol1-copy' for illustration purpose. 
cloudforensics aws 'us-east-2b' copydisk --volume_id='vol1' --src_profile='src_profile' --dst_profile='dst_profile' 

# Start an analysis VM 'vm-forensics' for investigation in the AWS account 
# dst_profile, and attach a volume to it.
cloudforensics aws 'us-east-2b' startvm 'vm-forensics' --boot_volume_size=50 --cpu_cores=4 --attach_volumes='vol1-copy' --dst_profile='dst_profile'
```

You're now ready to go! Log in your AWS account, find the instance (you can search it based on the name tag 
`vm-forensics`) and click on `Connect`.

``` important:: Pro tip: you can export an environment variable 'STARTUP_SCRIPT' that points to a custom bash script. 
This script will be shipped to the instance being created and executed during the first boot. You can do any kind of 
pre-processing you want in this script.
```

## Microsoft Azure

### Prerequisites

Your Azure credentials configuration (`~/.azure/credentials.json`) should look like this:

```text
{
  # Access credentials to Account A
  'src_profile': {
      'subscriptionId': xxx,
      'tenantId': xxx,
      'clientId': xxx,
      'clientSecret': xxx
  },
  # Access credentials to Account B
  'dst_profile': {
      'subscriptionId': yyy,
      'tenantId': yyy,
      'clientId': yyy,
      'clientSecret': yyy
  },
  ...
}
```

Alternatively, if you are working on only one account and do not require cross-account disk copies, you can define the 
following environment variables:

```text
$: export AZURE_SUBSCRIPTION_ID=xxx
$: export AZURE_CLIENT_ID=xxx
$: export AZURE_CLIENT_SECRET=xxx
$: export AZURE_TENANT_ID=xxx
```

### Disk snapshot

#### Scenario 1

You have a disk `disk1` in an Azure account, in `eastus` which you would like to make a copy 
of in the same account and in the same region.

#### Scenario 2

You have a disk `disk1` in an Azure account, in `eastus` which you would like to make a copy 
of in the same account but in a different region `westus`.

#### Scenario 3

You have a disk `disk1` in an Azure account (Account A) which you would like to make a copy 
of in a different account (Account B).

#### Using the library and the CLI

To make the copy, import the `forensics` package and use the `CreateDiskCopy` method.

```python
from libcloudforensics.providers.azure import forensics

# Scenario 1. Assumes credentials are configured through environment variables
copy = forensics.CreateDiskCopy('resource_group_name',
                                disk_name='disk1')
      
# Scenario 2. Assumes credentials are configured through environment variables                          
copy = forensics.CreateDiskCopy('resource_group_name',
                                disk_name='disk1',
                                region='westus')
                                
# Scenario 3. Assumes credentials are configured through profiles in ~/.azure/credentials.json
copy = forensics.CreateDiskCopy('resource_group_name',
                                disk_name='disk1',
                                src_profile='src_profile',
                                dst_profile='dst_profile')
```

The equivalent CLI command is:

```bash
# Scenario 1. Assumes credentials are configured through environment variables
cloudforensics az 'resource_group_name' copydisk --disk_name='disk1'

# Scenario 2. Assumes credentials are configured through environment variables 
cloudforensics az 'resource_group_name' copydisk --disk_name='disk1' --region='westus'

# Scenario 3. Assumes credentials are configured through profiles in ~/.azure/credentials.json
cloudforensics az 'resource_group_name' copydisk --disk_name='disk1' --src_profile='src_profile' --dst_profile='dst_profile' 
```

#### Cross-account / region sharing

The process for sharing resources across accounts/regions involves the creation (in the destination account/region) of a 
temporary storage account and container in which  the disk's snapshot is downloaded, prior to creating the disk copy 
from the storage account. To reduce user hassle, libcloudforensics takes care of all these steps. 
The process is depicted below:

![azure-cross-share](https://github.com/google/cloud-forensics-utils/blob/master/docs/source/images/sas.png?raw=true)

### Analysis VMs

Use case: you have a disk `disk1` in an Azure account (Account A) which you would like to make a copy 
of in a different account (Account B). Afterwards, you want to start an analysis VM in Account B, and attach the disk 
copy that you created to begin your investigation.

Your Azure credentials configuration should be similar to what is described [above](#microsoft-azure).

Using the library, you can start an analysis VM as follows:

```python
from libcloudforensics.providers.azure import forensics

# Create a copy of the disk 'disk1' from one account to another 

copy = forensics.CreateDiskCopy('resource_group_name',
                                disk_name='disk1', 
                                src_profile='src_profile', 
                                dst_profile='dst_profile')

# Start an analysis VM 'vm-forensics' for investigation in the Azure account 
# dst_profile, and attach the copy created in the previous step.

analysis_vm, _ = forensics.StartAnalysisVm('resource_group_name',
                                           'vm-forensics',
                                            50, 
                                            'ssh-rsa AAAbbbbFFFF...',
                                            cpu_cores=4,
                                            # In this scenario we consider that the final disk copy name is 'disk1-copy' for illustration purpose.
                                            attach_disks=['disk1-copy'],
                                            dst_profile='dst_profile')
```

The equivalent CLI command is:

```bash
# Create a copy of the disk 'disk1' in the dst_account Azure account.
# In this scenario we consider that the final disk copy name is 'disk1-copy' for illustration purpose. 
cloudforensics az 'resource_group_name' copydisk --disk_name='disk1' --src_profile='src_profile' --dst_profile='dst_profile'

# Start an analysis VM 'vm-forensics' for investigation in the Azure account 
# dst_profile, and attach a volume to it.
# A SSH key pair will be automatically generated and associated to the instance.
cloudforensics az 'resource_group_name' startvm 'vm-forensics' --disk_size=50 --cpu_cores=4 --attach_disks='disk1-copy' --dst_profile='dst_profile'
```

You're now ready to go! Log in your Azure account, find the instance's IP address and SSH to it.

``` important:: Pro tip: you can export an environment variable 'STARTUP_SCRIPT' that points to a custom bash script. 
This script will be shipped to the instance being created and executed during the first boot. You can do any kind of 
pre-processing you want in this script.
```