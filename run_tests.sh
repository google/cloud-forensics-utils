#!/bin/bash
echo "Running GCP unit tests...."
python -m tests.unittest.gcp_test
echo "Running AWS unit tests...."
python -m tests.unittest.aws_test
