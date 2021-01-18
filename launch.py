#!/usr/bin/env python

'''
@author : Mitchell Van Braeckel
@id : 1002297
@date : 10/29/2020
@version : python 3.8-32 / python 3.8.5
@course : CIS*4010 Cloud Computing
@brief : A2 Part 1: AWS EC2 - One-Click Deployment of VMs and Containers ; launch.py

@note :
    Description: uses all the pre-condition info to start creating VMs and configuring them
        (ie. instantiates VMs and loads containers)
        - must report status of what is happening and report errors if they occur
        - use AWS credentials for auth purposes

        - on VMs, can also load multiple Docker images and start some of them

        Pre-conditions:
        1) deployment description files
        - template.csv -- ignore header column row of:
            Template Name,Amazon Machine Image (AMI)/Azure Image Name,Instance Type / Azure Size,Root Volume Size (GiB),Security Group Name / Azure Inbound Ports,Zone / Region
        - instances.csv -- ignore header column row of:
            Template Name,Instance/VM Name,ssh key / Azure Key pair name,Container Package Name
        - container.csv -- ignore header column row of:
            Container Package Name,Container,Location,Start script
        
        2) example of a start script
        - docker run -ti --rm r-base bash

        3) create ssh keys

        4) populate own Docker Hub account w/ container or create som containers and put them on your own machine

    Improvements:
    - better error checking for CSV contents instead of assuming lots of things are good (general checking and validation checking with AWS)
    - eg. availability zone/region validation existence and accessibility, finding legal zone based off region, etc.
    - optimize order of things so long processes happen concurrently and we check success later, or with 'monitor.py' instead
    - within the template>instance>container triple for loop, set a flag for ssh/sftp and docker install only happens first time
'''

############################################# IMPORTS #############################################

# IMPORTS - 'pip install <import-package>'
import boto3
import csv
import os
import paramiko
import sys
import time

############################################ CONSTANTS ############################################

USAGE_STATEMENT = "Usage: py launch.py"
CSV_TEMPLATE_FILENAME = "template.csv"
CSV_INSTANCES_FILENAME = "instances.csv"
CSV_CONTAINER_FILENAME = "container.csv"

USER_DICT = {
    "amazonlinux2": "ec2-user",
    "amazonlinux": "ec2-user",
    "centos": "centos",
    "debian": "admin",
    "fedora": "ec2-user",
    "rhel": "ec2-user",
    "suse": "ec2-user",
    "ubuntu": "ubuntu",
    "redhat": "ec2-user"
}

DOCKER_INSTALL_SCRIPT_DICT = {
    "amazonlinux2": "dockerInstall-amazonlinux2.sh",
    "amazonlinux": "dockerInstall-amazonlinux.sh",
    "ubuntu": "dockerInstall-ubuntu.sh",
    "redhat": "dockerInstall-redhat.sh",
    "suse": "dockerInstall-suse.sh"
}

############################## STATE VARIABLES, INITIALIZATION, MAIN ##############################

def main():
    #globals
    global template_csv_content
    global instances_csv_content
    global container_csv_content
    global ec2_client
    global ec2_resource
    global template_user_keyword
    global instance_user_keyword
    global template_user_list
    global instance_user_list

    template_csv_content = []
    instances_csv_content = []
    container_csv_content = []
    template_user_keyword = []
    instance_user_keyword = []
    template_user_list = []
    instance_user_list = []

    # NOTE: no args

    # ---------- Validating local files ----------
    try:
        validate_and_load_local_files()
        print("")
    except Exception as e:
        sys.exit(f"[ERROR] While validating and loading local files: {e}")

    # ========== AWS EC2 ==========
    ec2_client = boto3.client("ec2")
    ec2_resource = boto3.resource("ec2")

    # Validate AWS EC2 credentials (by testing if 'describe_instances()' works)
    try:
        ec2_client.describe_instances()
    except Exception as e:
        print("Error: Invalid or expired credentials (or insufficient permissions to call 'describe_instances()')")
        sys.exit(f"[ERROR] {e}")

    # ---------- Verifying CSV content in AWS ----------
    try:
        verify_csv_content_in_aws()
        print("")
    except Exception as e:
        sys.exit(f"[ERROR] While validating content from CSV files in AWS EC2: {e}")

    # ---------- Creating Instances ----------
    print("--Creating instances...")

    # Create each instance from 'instances.csv'(using the related info about the template name from 'template.csv')
    # where, each instance you make you need to wait until its running (and reload after its running before using it)
    
    # Track all created instances
    new_instances = []
    try:
        new_instances = create_instances_from_template()
    except Exception as e:
        sys.exit(f"[ERROR] While creating instances: {e}")
    print("...Instance creation complete--\n")

    print(f"-respective users for each instance item: {instance_user_list}\n")

    # Wait for all new instances to be running, then reload before printing logs
    print("--Waiting for all new instance(s) to be running... please wait...")
    print("-Template&InstanceName - StatusCode=StatusState : InstanceID ImageID, Public IP - DNS | InstanceType, SecurityGroup, KeyName")
    try:
        for inst in new_instances:
            inst.wait_until_running()
            inst.reload()
            print(f"-{inst.tags[0]['Value']} {inst.tags[1]['Value']} - {inst.state['Code']}={inst.state['Name'].upper()} :", \
                f"{inst.id} {inst.image_id}, {inst.public_ip_address} - {inst.public_dns_name} | {inst.instance_type}, {inst.security_groups[0]['GroupName']}, {inst.key_name}")
    except Exception as e:
        sys.exit(f"[ERROR] While waiting for instances: {e}")
    print("...All new instance(s) are running--\n")


    # ---------- Containers + Docker images/container start scripts ----------

    # For each instance that was created because of a template, pull images and create containers based on start script
    #   location=Docker hub -> docker pull containerName
    #   location=Docker hub/repo -> docker pull repo/containerName
    # if start script present, ssh and run it (to start a container)
    #   --NOTE: ssh may fail even if instance is running, so try a few times with a timer in between before moving on
    #           eg. don't spend more than 1min, try again after every 5 seconds
    # -- otherwise just pull the image only, then do docker run

    # Pull each image for all instances (using the container package name in 'instances.csv' and 'container.csv')
    #   where you pull based on the location or build an image from a docker file
    #       (we can assume the filenameLocation is provided explicitly with relative path from the local dir of the python script,
    #       or it is implicit because it uses name 'Dockerfile' and they only provide directory location of it)
    #       (Docker hub=pull containerName
    #       Docker hub/repo=pull repo/containerName
    #       Docker file=build -t containerName -f .
    #       Dockerfile/filenameLocation=build -t containerName -f ./filenameLocation)
    #   and ssh into the instance to run a startup script if present (otherwise just do docker run)

    print("--Pulling images and starting containers on each instance... please wait...")
    try:
        # Instances Format: template name, instance name, ssh key pair name (w/o .pem), container pack name
        # Container Format: container pack name, container, location, start script
        inst_list_index = 0 #track instances (template name matches instance template name)
        for template_row in template_csv_content:
            for instance_row in instances_csv_content:
                # Skip if  the template names of template and instance don't match
                if template_row[0] != instance_row[0]:
                    continue
                for container_row in container_csv_content:
                    # Check for matching container package names
                    if instance_row[3] == container_row[0]:
                        # Log container pack name matches with instance name and other container info
                        print(f"\n--match = {instance_row[1]}: '{container_row[0]}' - {container_row[1]}, {container_row[2]}, {container_row[3]}")
                        new_instances[inst_list_index].reload() #reload instance just in case

                        # Attempt retry SSH connection until it connects (or 10 failures occur so we skip)
                        ssh_client = paramiko.SSHClient()
                        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                        ssh_connection = ssh_connect_with_retry(
                            ssh_client,
                            instance_user_list[inst_list_index],
                            new_instances[inst_list_index].public_ip_address,
                            f"{instance_row[2]}.pem"
                        )

                        # Run commands on the instance if SSH succeeds, otherwise do nothing (already gave err msg w/ retries)
                        if ssh_connection:
                            sftp_client_open_flag = False
                            # Determine Docker image location
                            location_command = determine_location_command(container_row)
                            repo_container_name = determine_location_command(container_row, False)
                            print(f"-->command=sudo {location_command}")
                        
                            try:
                                # Determine related Docker install script using user template keyword (and validate file, but manually check string exists)
                                docker_install_script = DOCKER_INSTALL_SCRIPT_DICT[instance_user_keyword[inst_list_index]]
                                print(f"~opening SFTP and uploading '{docker_install_script}'...")
                                if not is_valid_bash_script(docker_install_script) or docker_install_script == None or docker_install_script == "":
                                    print(f"Error: Skipping due to invalid docker install script detection - {docker_install_script}")
                                    continue #skip if invalid bash script

                                # Open SFTP for SSH, put update+Docker install script onto instance, then run it (and tag instance with successful key-value pair: DockerInstalled, True),
                                sftp_client = ssh_client.open_sftp()
                                sftp_client_open_flag = True
                                sftp_client.sshclient = ssh_client #keep copy here for safety measure

                                sftp_client.put(docker_install_script, docker_install_script)

                                print(f"~executing 'sudo sh ./{docker_install_script}'... please wait...")
                                stdin, stdout, stderr = ssh_client.exec_command(f"sudo sh ./{docker_install_script}")
                                stdout.channel.recv_exit_status()

                                new_instances[inst_list_index].create_tags(
                                    Tags = [
                                        {
                                            'Key': 'DockerInstalled',
                                            'Value': 'True'
                                        }
                                    ]
                                )

                                # Then check 'docker images' to show it worked
                                print(f"~verifying Docker installation success via 'sudo docker images'")
                                stdin, stdout, stderr = ssh_client.exec_command("sudo docker images")
                                stdout.channel.recv_exit_status()
                                ssh_cmd_stdout_stderr_print("docker images", stdout.read().decode('UTF-8'), stderr.read().decode('UTF-8'))

                                # Create Docker image,
                                print(f"~executing 'sudo {location_command}'... please wait...")
                                stdin, stdout, stderr = ssh_client.exec_command(f"sudo {location_command}")
                                stdout.channel.recv_exit_status()

                                # Then check 'docker images' to show it worked
                                print(f"~verifying image success via 'sudo docker images'")
                                stdin, stdout, stderr = ssh_client.exec_command("sudo docker images")
                                stdout.channel.recv_exit_status()
                                ssh_cmd_stdout_stderr_print("docker images", stdout.read().decode('UTF-8'), stderr.read().decode('UTF-8'))
                                
                                # Run start script (if present), otherwise do 'docker run',
                                if container_row[3] != None and container_row[3] != "":
                                    # NOTE: already validated start scripts as locally existing bash scripts during CSV load
                                    print(f"~start script present, uploading '{container_row[3]}' using open SFTP...")
                                    sftp_client.put(container_row[3], container_row[3])

                                    print(f"~start script present, executing 'sudo sh ./{container_row[3]}'... please wait...")
                                    stdin, stdout, stderr = ssh_client.exec_command(f"sudo sh ./{container_row[3]}")
                                    stdout.channel.recv_exit_status()
                                    ssh_cmd_stdout_stderr_print("start script", stdout.read().decode('UTF-8'), stderr.read().decode('UTF-8'))

                                else:
                                    print(f"~executing 'sudo docker run {repo_container_name}'")
                                    stdin, stdout, stderr = ssh_client.exec_command(f"sudo docker run {repo_container_name}")
                                    stdout.channel.recv_exit_status()
                                    ssh_cmd_stdout_stderr_print("docker run", stdout.read().decode('UTF-8'), stderr.read().decode('UTF-8'))

                                # Then check 'docker images' and 'docker containers' to show it worked
                                # NOTE: maybe don't show these and leave it to 'monitor.py' to prove ?
                                print(f"~verifying container creation success via 'sudo docker images' and 'sudo docker container ls -a'")
                                stdin, stdout, stderr = ssh_client.exec_command("sudo docker images")
                                stdout.channel.recv_exit_status()
                                ssh_cmd_stdout_stderr_print("docker images", stdout.read().decode('UTF-8'), stderr.read().decode('UTF-8'))
                                
                                stdin, stdout, stderr = ssh_client.exec_command("sudo docker container ls -a")
                                stdout.channel.recv_exit_status()
                                ssh_cmd_stdout_stderr_print("docker containers", stdout.read().decode('UTF-8'), stderr.read().decode('UTF-8'))

                            except Exception as e:
                                print(f"Error: Failure to SSH, SFTP, and/or run commands on {new_instances[inst_list_index].public_ip_address}: {e}")
                            finally:
                                if sftp_client_open_flag:
                                    sftp_client.close()
                                ssh_client.close()
                # Accumulate instance tracker
                inst_list_index += 1
    except Exception as e:
        sys.exit(f"[ERROR] While pulling images and creating containers: {e}")
    print("...All container(s) are most likely running ...please run 'py monitor.py' for more details--")

############################################ FUNCTIONS ############################################

# Returns true if all CSV filenames exist locally and are valid, false otherwise
def validate_csv_files():
    valid_flag = True
    invalid_csv_list = []
    # Check if each CSV file exists locally, if it meets filename requirements
    # Each CSV filename must be at least 5 chars long and have a '.csv' extension
    if len(CSV_TEMPLATE_FILENAME) > 4 and CSV_TEMPLATE_FILENAME.endswith(".csv"):
        if not os.path.isfile(CSV_TEMPLATE_FILENAME):
            valid_flag = False
            invalid_csv_list.append(CSV_TEMPLATE_FILENAME)
            print(f"Error: Invalid CSV file name '{CSV_TEMPLATE_FILENAME}' - file does not exist.")
    else:
        valid_flag = False
        invalid_csv_list.append(CSV_TEMPLATE_FILENAME)
        print(f"Error: Invalid CSV file name '{CSV_TEMPLATE_FILENAME}' - filename must end with '.csv'.")
    
    if len(CSV_INSTANCES_FILENAME) > 4 and CSV_INSTANCES_FILENAME.endswith(".csv"):
        if not os.path.isfile(CSV_INSTANCES_FILENAME):
            valid_flag = False
            invalid_csv_list.append(CSV_INSTANCES_FILENAME)
            print(f"Error: Invalid CSV file name '{CSV_INSTANCES_FILENAME}' - file does not exist.")
    else:
        valid_flag = False
        invalid_csv_list.append(CSV_INSTANCES_FILENAME)
        print(f"Error: Invalid CSV file name '{CSV_INSTANCES_FILENAME}' - filename must end with '.csv'.")

    if len(CSV_CONTAINER_FILENAME) > 4 and CSV_CONTAINER_FILENAME.endswith(".csv"):
        if not os.path.isfile(CSV_CONTAINER_FILENAME):
            valid_flag = False
            invalid_csv_list.append(CSV_CONTAINER_FILENAME)
            print(f"Error: Invalid CSV file name '{CSV_CONTAINER_FILENAME}' - file does not exist.")
    else:
        valid_flag = False
        invalid_csv_list.append(CSV_CONTAINER_FILENAME)
        print(f"Error: Invalid CSV file name '{CSV_CONTAINER_FILENAME}' - filename must end with '.csv'.")
    
    # Output all invalid CSV filenames before leaving
    if not valid_flag:
        print(f"ERROR: Invalid CSV file names were detected - {invalid_csv_list}")
    
    return valid_flag

# Loads CSV and returns the 2D array of its contents
def load_csv_file(csv_filename):
    # Open the CSV file and read its contents, skipping header column row
    with open(csv_filename, "r", newline='') as csv_file:
        csv_content = list(csv.reader(csv_file, delimiter=','))
        csv_content.pop(0)
    csv_file.close()

    return csv_content

# Checks that all ssh key pair name exists locally, and is valid after trimming ".pem" extension (must not contain '.')
# Returns true if all pem key names exist locally and are valid, false otherwise
# NOTE: fixes permissions of PEM files to 'chmod 600'
def validate_and_trim_ssh_pem_local():
    # Bring in globals to modify
    global instances_csv_content

    valid_flag = True
    invalid_keys = []
    for row in instances_csv_content:
        # Must be at least 5 chars long and have a '.pem' extension
        if len(row[2]) > 4 and row[2].endswith(".pem"):
            # Check if it exists locally, then remove '.pem' extension
            if not os.path.isfile(row[2]):
                valid_flag = False
                invalid_keys.append(row[2])
                print(f"Error: Invalid ssh key pair name '{row[2]}' - file does not exist locally.")
            os.system(f"chmod 600 {row[2]}") #perms for PEM file
            row[2] = row[2][0:len(row[2])-4] #modifies global here
        else:
            valid_flag = False
            invalid_keys.append(row[2])
            print(f"Error: Invalid ssh key pair name '{row[2]}' - filename must end with '.pem'.")
    
    # Output all invalid ssh key pem filenames before leaving
    if not valid_flag:
        print(f"ERROR: Invalid ssh key pair names were detected - {invalid_keys}")

    return valid_flag

# Returns true if all start scripts exist locally, false otherwise
# Note: the start script is optional and can be empty in the CSV row
# NOTE: fixes permissions of SH files to 'chmod +x'
def validate_start_scripts():
    valid_flag = True
    invalid_scripts = []
    # Check that each start script is a valid bash script, track invalid ones
    for row in container_csv_content:
        if not is_valid_bash_script(row[3]):
            valid_flag = False
            invalid_scripts.append(row[3])
    
    # Output all invalid start scripts before leaving
    if not valid_flag:
        print(f"ERROR: Invalid start script names were detected - {invalid_scripts}")
    return valid_flag
        

# Returns true if all AMI image IDs in the template CSV exist
def verify_amis_exist():
    # Get list of AMIs from template
    template_ami_list = []
    unique_image_ids = 0
    for row in template_csv_content:
        # Track #of unique image IDs in the template AMI list
        if row[1] not in template_ami_list:
            unique_image_ids += 1
            template_ami_list.append(row[1])

    # Get all public AMIs, filtering by the unique image IDs being verified
    images = ec2_client.describe_images(
        ExecutableUsers=['all'],
        Filters=[
            {
                'Name': 'image-id',
                'Values': template_ami_list
            }
        ]
    )['Images']

    # Check if an AMI image exists for every unique image ID given
    print(f"-{len(images)} AMI image IDs were found for {unique_image_ids} unique")
    return len(images) == unique_image_ids

# Returns true if all security group names in the template CSV exist
def verify_sec_groups_exist():
    # Get list of sec group names from template
    template_sec_group_names = []
    unique_names = 0
    for row in template_csv_content:
        # Track #of unique names of the template security groups
        if row[4] not in template_sec_group_names:
            unique_names += 1
            template_sec_group_names.append(row[4])

    # Get security groups, filtering by the unique security group names being verified
    sec_groups = ec2_client.describe_security_groups(
        Filters=[
            {
                'Name': 'group-name',
                'Values': template_sec_group_names
            }
        ]
    )['SecurityGroups']

    # Check if a security group exists for every unique sec group name given
    print(f"-{len(sec_groups)} security group names were found for {unique_names} unique")
    return len(sec_groups) == unique_names

# Returns true if all ssh key pair name (w/o '.pem') exists on AWS EC2
# NOTE: used after validate_and_trim_ssh_pem_local()
def verify_public_ssh_pem():
    # Get list of ssh key '.pem' files w/o extension
    ssh_pem_list = []
    unique_keys = 0
    for row in instances_csv_content:
        # Track #of unique names of the template security groups
        if row[2] not in ssh_pem_list:
            unique_keys += 1
            ssh_pem_list.append(row[2])

    # Get key pairs from AWS EC2, filtering by the unique ssh key '.pem' names being verified
    key_pairs = ec2_client.describe_key_pairs(
        Filters=[
            {
                'Name': 'key-name',
                'Values': ssh_pem_list
            }
        ]
    )['KeyPairs']

    # Check if a public key-pair exists for every unique local ssh key '.pem' filename given
    print(f"-{len(key_pairs)} SSH key pair names were found for {unique_keys} unique")
    return len(key_pairs) == unique_keys


# Returns the BlockDeviceMappings structure of a create_instances() request based on the given 'default' or numerical root size of the template
def determine_block_device_mappings(template_row):
    block_device_mappings = []
    if template_row[3].lower() != "default":
        block_device_mappings = [
            {
                'DeviceName': f"{ec2_resource.Image(template_row[1]).root_device_name}",
                'Ebs': {
                    'DeleteOnTermination': True,
                    'VolumeSize': int(template_row[3]),
                }
            },
        ]
    return block_device_mappings

# Returns an availability zone if what's given is an availability region
def determine_availability_zone(availability):
    # Check the last letter of the availability: letter=zone, digit=region so get a zone (via adding 'a' on the end)
    if availability[-1].isalpha():
        return availability
    elif availability[-1].isdigit():
        return f"{availability}a"
    else:
        sys.exit(f"ERROR: Terminating program - invalid availability zone/region detected: '{availability}'")

# Returns the command used to get the image from docker specified location or file
# where you pull based on the location or build an image from a docker file
#   (we can assume the filenameLocation is provided explicitly with relative path from the local dir of the python script,
#   or it is implicit because it uses name 'Dockerfile' and they only provide directory location of it)
#   (Docker hub=pull containerName
#   Docker hub/repo=pull repo/containerName
#   Dockerfile=build -t containerName . -f .
#   Dockerfile/filenameLocation=build -t containerName . -f ./filenameLocation)
# NOTE: Dockerfile version not supported right now, would also need to check if said file exists
# NOTE: if command set to False, returns the repo/containerName only instead of full docker pull repo/containerName
def determine_location_command(container_row, command=True):
    first_slash_index = 10
    # Get everything after '/', as long as '/' and something else exists after (default to nothing), terminate if nothing
    split_location = container_row[2].split('/')
    if container_row[2] == None or container_row[2] == "" or len(split_location) < 1:
        sys.exit(f"ERROR: Terminating program - invalid docker image location detected for '{container_row[1]}': '{container_row[2]}'")
    else:
        extra_command = ""
        if len(split_location) > 1 and split_location[1] != None and split_location[1] != "":
            first_slash_index = container_row[2].find('/')
            extra_command = container_row[2][first_slash_index+1:] + '/'

    # Check for pull image vs build image from dockerfile
    if "docker hub" == container_row[2][:first_slash_index].lower():
        if command:
            return f"docker pull {extra_command}{container_row[1]}"
        else:
            return f"{extra_command}{container_row[1]}"
    elif "dockerfile" == container_row[2][:first_slash_index].lower():
        sys.exit(f"ERROR: Terminating program - feature for dockerfile location not supported - invalid docker image location detected for '{container_row[1]}': '{container_row[2]}'")
        return f"docker build -t {container_row[1]} -f ./{extra_command}"
    else:
        sys.exit(f"ERROR: Terminating program - invalid docker image location detected for '{container_row[1]}': '{container_row[2]}'")

# Recursive SSH retry logic that gives up after designated number of retries
#   Needs paramiko ssh client, user & public IP address, PEM, #of current retries (interval and limit default to 5,10 respectively)
# NOTE: sometimes fails to SSH into a running instance right after creation, so retry a few times
def ssh_connect_with_retry(ssh_client, user, ip_address, pem_file, retries=0, retry_interval=5, retry_limit=10):
    # Base case to stop when limit is exceeded
    if retries > retry_limit:
        print(f"-SSH connection failed to {ip_address} {retry_limit} times, skipping failure")
        return False
    
    # Get the private SSH key PEM, then try to connect using SSH client
    private_key = paramiko.RSAKey.from_private_key_file(pem_file)
    try:
        # Accumulate #of connection attempts
        retries += 1
        print(f"-Attempting to SSH into the instance: {ip_address}")
        ssh_client.connect(hostname=ip_address, username=user, pkey=private_key)
        return True
    except Exception as e:
        # Output exception, sleep for a bit, then retry 
        print(f"-SSH exception: {e}")
        time.sleep(retry_interval)
        print(f"-Retrying SSH connection {retries} to {ip_address}")
        return ssh_connect_with_retry(ssh_client, user, ip_address, pem_file, retries, retry_interval, retry_limit)

############################################# HELPERS #############################################

# Returns true if the filename is a bash script (or empty string), otherwise false
# NOTE: fixes permissions of SH files to 'chmod +x'
def is_valid_bash_script(filename):
    valid_flag = True
    # Must be at least 4 chars long and have a '.sh' extension
    if filename != None and filename != "":
        if len(filename) > 3 and filename.endswith(".sh"):
            # Check that the file exists locally
            if not os.path.isfile(filename):
                valid_flag = False
                print(f"Error: Invalid bash script '{filename}' - file does not exist locally.")
            os.system(f"chmod +x {filename}") #perms for bash script file
        else:
            valid_flag = False
            print(f"Error: Invalid bash script '{filename}' - filename must end with '.sh'.")
    return valid_flag

# Prints the output (and errors if present) of a command on the SSH
def ssh_cmd_stdout_stderr_print(descr, stdout, stderr):
    print(f"->{descr} output=\n{stdout}")
    if stderr != None and stderr != "":
        print(f"\n->{descr} errors=\n{stderr}")


# Helper function that validates local files: CSV, PEM, SH; and loads CSV content if valid
def validate_and_load_local_files():
    # Bring in globals to modify
    global template_csv_content
    global instances_csv_content
    global container_csv_content
    global template_user_keyword
    global template_user_list

    # Loads and parses the 3 CSV files
    print("--Validating and loading local CSV files...")
    try:
        # Check if each file exists before loading CSV contents, display err msg as appropriate
        if validate_csv_files():
            # Modifies globals for CSV content load from file
            template_csv_content = load_csv_file(CSV_TEMPLATE_FILENAME)
            instances_csv_content = load_csv_file(CSV_INSTANCES_FILENAME)
            container_csv_content = load_csv_file(CSV_CONTAINER_FILENAME)

            # Check if template names contain a keyword identifier
            template_name_valid_flag = True
            invalid_template_names = []
            for row in template_csv_content:
                # Determine user for the given template name (which was based on the AMI image ID)
                match_found_flag = False
                for key, value in USER_DICT.items():
                    # Check if keyword is in template name
                    if key in row[0].lower():
                        # For the match, add the user value to the list (and store keyword), then stop looking because found match
                        match_found_flag = True
                        template_user_keyword.append(key)
                        template_user_list.append(value)
                        break
                # Track bad template names
                if not match_found_flag:
                    template_name_valid_flag = False
                    invalid_template_names.append(row[0])

            # Output all invalid CSV filenames before leaving
            if not template_name_valid_flag:
                print(f"ERROR: Invalid template names were detected in '{CSV_TEMPLATE_FILENAME}' - {invalid_template_names}")
                sys.exit("Error: Terminating program - not all given template names are valid.")
        else:
            sys.exit()
    except Exception as e:
        sys.exit(f"[ERROR] While loading deployment description files: {e}")
    print("...Local CSV files validated and loaded successfully--")

    # Display loaded CSV content from each file
    for row in template_csv_content:
        print(f"-template item: {row[0]}, {row[1]}, {row[2]}, {row[3]}, {row[4]}, {row[5]}")
    #print(template_csv_content)
    print(f"-respective users for each template item: {template_user_list}")
    for row in instances_csv_content:
        print(f"-instances item: {row[0]}, {row[1]}, {row[2]}, {row[3]}")
    #print(instances_csv_content)
    for row in container_csv_content:
        print(f"-container item: {row[0]}, {row[1]}, {row[2]}, {row[3]}")
    #print(container_csv_content)

    ## Below covered by assumptions:
    ## Validate template name relates to at least 1 instance, and vice versa
    ## Validate instance name relates to at least 1 container pack name, and vice versa
    ## Validate instance template names are unique within template, and instance name unique within instances
    ## Maybe consider more validation for info from 'container.csv'

    # Validate ssh key pair names exists and trim ".pem" extension (local dir) && that all start scripts exist on local dir
    # Note: exit if any are invalid or do not exist
    print("--Validating local files referenced in CSVs...")
    if not validate_and_trim_ssh_pem_local() or not validate_start_scripts():
        sys.exit()
    print("...Local files referenced in CSVs validated successfully--")

# Helper function that verifies CSV content is valid in AWS EC2: AMIs, sec groups, key-pairs
def verify_csv_content_in_aws():
    # Verify AMIs exist
    print("--Verifying AMI image IDs exist...")
    try:
        if not verify_amis_exist():
            sys.exit("ERROR: Terminating program - not all given AMI Image IDs exist.")
    except Exception as e:
        sys.exit(f"[ERROR] While verifying all AMI image IDs exist: {e}")
    print("...AMI image IDs verified successfully--")

    # Verify security group names exist
    print("--Verifying security group names exist...")
    try:
        if not verify_sec_groups_exist():
            sys.exit("ERROR: Terminating program - not all given security group names exist.")
    except Exception as e:
        sys.exit(f"[ERROR] While verifying all security group names exist: {e}")
    print("...Security group names verified successfully--")

    # Verify ssh key pair (.pem) exists (on AWS EC2, note: exclude '.pem')
    print("--Verifying public ssh key pair names exist on AWS EC2...")
    try:
        if not verify_public_ssh_pem():
            sys.exit("ERROR: Terminating program - not all given public ssh key-pair names exist on AWS EC2.")
    except Exception as e:
        sys.exit(f"[ERROR] While verifying all ssh key-pair names exist on AWS EC2: {e}")
    print("...Public ssh key pair names verified successfully--")


# Helper function that creates returns a list of instances for tracking using the info from template and instances CSVs
def create_instances_from_template():
    # Bring in globals to modify
    global instance_user_keyword
    global instance_user_list

    new_instances = []
    # Template Format: template name, ami image ID, instance type, root volume size (GiB), sec group name, (availability) zone
    # Instance Format: template name, instance name, ssh key pair name (w/o .pem), container pack name
    template_index = 0
    for template_row in template_csv_content:
        for instance_row in instances_csv_content:
            # Check for matching template names
            if template_row[0] == instance_row[0]:
                # Log template name matches with image ID and instance name
                print(f"--match '{template_row[0]}': {template_row[1]} - {instance_row[1]}")

                # Track instance users and keywords
                instance_user_keyword.append(template_user_keyword[template_index])
                instance_user_list.append(template_user_list[template_index])

                # Create an instance using instance info + template commmon info, and track it
                #   -Determine BlockDeviceMappings via root volume size: do nothing if it says default, otherwise create proper structure for request
                #   -Determine availability zone if an availability region was given
                new_instances.append(ec2_resource.create_instances(
                    BlockDeviceMappings=determine_block_device_mappings(template_row),
                    ImageId=template_row[1],
                    InstanceType=template_row[2],
                    KeyName=instance_row[2],
                    MaxCount=1,
                    MinCount=1,
                    Placement={
                        'AvailabilityZone': determine_availability_zone(template_row[5])
                    },
                    SecurityGroups=[
                        template_row[4]
                    ],
                    TagSpecifications=[
                        {
                            'ResourceType': 'instance',
                            'Tags': [
                                {
                                    'Key': 'TemplateName',
                                    'Value': template_row[0]
                                },
                                {
                                    'Key': 'InstanceName',
                                    'Value': instance_row[1]
                                }
                            ]
                        },
                    ]
                )[0])
        template_index += 1
    return new_instances

###################################################################################################

# main()

try:
    main()
except Exception as e:
    print("Error: error occurred, terminating program immediately as precaution.")
    sys.exit(f"[ERROR] {e}")
