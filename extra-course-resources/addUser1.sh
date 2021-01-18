#
# As root, add the new user identity
#
uName=$1
public=$2
echo "sudo adduser "$uName

# As the new user, set up your ssh keys
echo "sudo su - "$uName
echo "mkdir .ssh"
echo "chmod 700 .ssh"
echo "touch .ssh/authorized_keys"
echo "exit"
echo "exit"
