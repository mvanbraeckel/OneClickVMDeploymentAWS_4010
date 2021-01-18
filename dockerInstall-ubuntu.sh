#!/bin/bash

# Install Docker on Ubuntu Server 20.04 LTS, Ubuntu Server 18.04 LTS, or Ubuntu Server 16.04 LTS instance
# From: https://docs.docker.com/engine/install/ubuntu/
# AMI image ID: ami-0dba2cb6798deb6d8, ami-0817d428a6fb68645, ami-0f82752aa17ff8f5d

sudo apt update -y
sudo apt-get update -y
sudo apt-get install apt-transport-https ca-certificates curl gnupg-agent software-properties-common -y
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
#sudo apt-key fingerprint 0EBFCD88
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"

sudo apt-get update -y
sudo apt-get install docker-ce docker-ce-cli containerd.io -y
