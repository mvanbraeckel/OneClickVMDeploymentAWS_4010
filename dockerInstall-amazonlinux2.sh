#!/bin/bash

# Install Docker on Amazon Linux 2 AMI instance
# From: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/docker-basics.html
# AMI image ID: ami-0947d2ba12ee1ff75

sudo yum update -y
sudo amazon-linux-extras install docker -y
sudo service docker start
