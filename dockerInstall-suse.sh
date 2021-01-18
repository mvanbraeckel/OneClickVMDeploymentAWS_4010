#!/bin/bash

# Install Docker on SUSE Linux Enterprise Server 15 SP2 instance
# From: https://documentation.suse.com/sles/15-SP1/html/SLES-all/cha-docker-installation.html
# AMI image ID: ami-0a782e324655d1cc0

sudo zypper install docker -y
sudo service docker start
