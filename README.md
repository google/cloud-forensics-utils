# Cloud Forensics Utils

<p align="center">
  <img src="https://user-images.githubusercontent.com/25910997/81309523-533f6300-9083-11ea-975b-668f550e5a9e.png" width="300"/>
</p>

This repository contains some tools to be used by forensics teams to collect
evidence from cloud platforms. Currently, Google Cloud Platform, Microsoft Azure,
and Amazon Web Services are supported.

It consists of one module called `libcloudforensics` which implements functions
that can be desirable in the context of incident response in a cloud
environment, as well as a CLI wrapper tool for these functions.

Documentation can be found on the [ReadTheDocs page](https://libcloudforensics.readthedocs.io/en/latest/).

## Quick install

```
pip install libcloudforensics
```

## Running the CLI tool

A standalone tool called `cloudforensics` is created during installation.

```
$ cloudforensics --help
usage: cloudforensics [-h] {aws,az,gcp} ...

CLI tool for AWS and GCP.

positional arguments:
  {aws,az,gcp}
    aws         Tools for AWS
    az          Tools for Azure
    gcp         Tools for GCP

optional arguments:
  -h, --help    show this help message and exit
```

The implemented functions for each platform can also be listed. For example:

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
