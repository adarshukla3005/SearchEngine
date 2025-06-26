#!/bin/bash
# Install system dependencies for lxml
pip install --upgrade pip
pip install wheel
pip install lxml==4.6.3 --only-binary=lxml
echo "Installed lxml from binary wheel" 