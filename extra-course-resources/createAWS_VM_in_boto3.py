#
# Example code to create an EC2 instance
#
import boto3

#
# Connect to the ec2 resource
# To run this example on your system: you might not be able to use the CA zone - use
# a the zone that your account is in.
#
ec2 = boto3.resource("ec2","us-east-1")

#
# Launch one Amazon Linux AMI 2018.03.0 (HVM), SSD Volume Type
# To run this example on your system: you must create a KeyName (not use the one here)
# For information about keys see: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html
#
instance = ec2.create_instances(
   ImageId="ami-0dba2cb6798deb6d8", #vm image - Ubuntu Server 20.04 LTS (HVM), SSD Volume Type - ami-0dba2cb6798deb6d8 (64-bit x86) / ami-0ea142bd244023692 (64-bit Arm)
   MinCount=1,
   MaxCount=1,
   InstanceType="t2.micro",
   KeyName="4010-1"
)[0]

'''
template name - JASON - set a tag on the instance - 'TemplateName'
ami image id - ImageId="ami-..." 
instance type - InstanceType="t2.micro"
root volume size (GiB) - in BlockDeviceMappings list, each dict obj, 'Ebs' dict obj - 'VolumeSize': 123
                     JASON   - if 'default', no BlockDeviceMappings list included in request 
sec group name - SecurityGroups list (the sec group name as a string item)
zone / region - in Placement dict obj - 'AvailabilityZone': "us-east-1a"

template name - duplicate
instance name - JASON - set a tag on the instance - 'InstanceName'
ssh key pair name - KeyName="cis-4010-all-a2"
container pack name - 

container pack name - duplicate
container - 
location - 
start script - 
'''

'''
response = client.run_instances(
    BlockDeviceMappings=[
        {
            'DeviceName': '/dev/xvda',
            'Ebs': {
                'DeleteOnTermination': True,
                'VolumeSize': 8,
                'VolumeType': 'gp2'
            },
        },
    ],
    ImageId='ami-6cd6f714',
    InstanceType='t3.micro',
    MaxCount=1,
    MinCount=1,
    Monitoring={
        'Enabled': False
    },
    SecurityGroupIds=[
        'sg-1f39854x',
    ],
)
'''

#
# Wait for the instance to be created...
# This code is using a routine that waits on the instance to be running
# and then reloads information about the instance
#
instance.wait_until_running()
instance.reload()

#
# show_instances will list all of your VMs of a given status
#
def show_instances(status):
   instances = ec2.instances.filter(
      Filters=[{"Name": "instance-state-name","Values": [status]}])
   for inst in instances:
      print(inst.id, inst.instance_type, inst.image_id, inst.public_ip_address)

#
# List all of your running EC2 instances - you should see the new VM
#
show_instances("running")


