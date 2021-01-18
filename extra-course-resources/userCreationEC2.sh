#! /bin/sh
#
# Set up a new user on a AWS EC2 instance
#
# Arguments: vm_address pemFileName newUserName KeyFileName 
# Example: sh userCreationEC2.sh 15.223.115.38 gbads-summer2020.pem deb deb_rsa
#
# Check that there are 4 arguments on the commandline
#
number=$#
if [[ $number -ne 4 ]]
then
   echo "Usage: userCreationEC2.sh EC2_address pemFile newUserName privateKeyName"
   exit
fi
# Capture the commandline arguments
vmAddr=$1
pem=$2
uName=$3
private=$4
public=$private.pub
echo $vmAddr $pem $uName $public $private
#
ec2User="ec2-user@"$vmAddr
newUser=$uName"@"$vmAddr
echo $ec2User $newUser
#
# create keys
#
ssh-keygen -t rsa -f $private -P ""
#
echo "Copying public key "$public"..."
echo "scp -i "$pem" "$public" "$ec2User":/tmp"
scp -i $pem $public $ec2User:/tmp
ls -l $private*
#
# Login as root to the VM
# As root, add the new user identity
# As the new user, set up your ssh keys
#
echo "Adding user - part 1..."
sh addUser1.sh $uName $public > newUserInstructions1.txt
ssh -i $pem $ec2User < newUserInstructions1.txt
#
echo "Adding user - part 2..."
sh addUser2.sh $uName $public > newUserInstructions2.txt
ssh -i $pem $ec2User < newUserInstructions2.txt
#

# From your host machine, verify that the new user account works
# and set a new password on the machine
echo "ssh -i "$private" "$newUser
ssh -i $private $newUser

