# Getting started

## Installing from pypi

As easy as:

```
$ pip install libcloudforensics
```

and you're done!

## Using the CLI

A standalone tool called `cloudforensics` is created during installation.

```
$ cloudforensics --help
usage: cloudforensics [-h] {aws,az,gcp} ...

CLI tool for AWS, Azure and GCP.

positional arguments:
  {aws,az,gcp}
    aws         Tools for AWS
    az          Tools for Azure
    gcp         Tools for GCP

optional arguments:
  -h, --help    show this help message and exit
```

The implemented functions for each platform can be listed. For example:

```
$ cloudforensics gcp -h
usage: cloudforensics gcp [-h] project {listinstances,listdisks,copydisk,startvm,querylogs,listlogs,listservices,creatediskgcs,bucketacls,objectmetadata,listobjects} ...

positional arguments:
  project               GCP project ID.
  {listinstances,listdisks,copydisk,startvm,querylogs,listlogs,listservices,creatediskgcs,bucketacls,objectmetadata,listobjects}
    listinstances       List GCE instances in GCP project.
    listdisks           List GCE disks in GCP project.
    copydisk            Create a GCP disk copy.
    startvm             Start a forensic analysis VM.
    querylogs           Query GCP logs.
    listlogs            List GCP logs for a project.
    listservices        List active services for a project.
    creatediskgcs       Creates GCE persistent disk from image in GCS.
    bucketacls          List ACLs of a GCS bucket.
    objectmetadata      List the details of an object in a GCS bucket.
    listobjects         List the objects in a GCS bucket.

optional arguments:
  -h, --help            show this help message and exit
```
