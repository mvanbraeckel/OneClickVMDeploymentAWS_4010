#
# As root, add the new user identity
#
uName=$1
public=$2
#
# As root, modify the ownership, group, and permissions for the keys
# 
echo "sudo cp /tmp/"$public" /home/"$uName"/.ssh/authorized_keys"
echo "sudo chown "$uName" /home/"$uName"/.ssh/authorized_keys"
echo "sudo chgrp "$uName" /home/"$uName"/.ssh/authorized_keys"
echo "sudo chmod 600 /home/"$uName"/.ssh/authorized_keys"
echo "sudo usermod -aG wheel "$uName
echo "exit"
