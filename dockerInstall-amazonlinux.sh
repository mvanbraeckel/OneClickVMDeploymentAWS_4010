#!/bin/bash

# Install Docker on Amazon Linux AMI instance
# From: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/docker-basics.html
# AMI image ID: ??

sudo yum update -y
sudo yum install docker -y
sudo service docker start
