# Cloud Forensics Utils

<p align="center">
  <img src="https://user-images.githubusercontent.com/25910997/81309523-533f6300-9083-11ea-975b-668f550e5a9e.png" width="300"/>
</p>

This repository contains some tools to be used by forensics teams to collect
evidence from cloud platforms. Currently, Google Cloud Platform, Microsoft Azure,
and Amazon Web Services are supported.

It consists in one module called `libcloudforensics` which implements functions
that can be desirable in the context of incident response in a cloud
environment.

A standalone called `cloudforensics` to call these methods from the command line
is created during installation

## Quick install

```
pip install libcloudforensics
```
