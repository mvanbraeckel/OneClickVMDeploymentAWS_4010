#!/usr/bin/env python

'''
@author : Mitchell Van Braeckel
@id : 1002297
@date : 10/29/2020
@version : python 3.8-32 / python 3.8.5
@course : CIS*4010 Cloud Computing
@brief : A2 Part 1: AWS EC2 - One-Click Deployment of VMs and Containers ; monitor.py

@note :
    Description: after launch.py (one-click deployment), demonstrates everything was successful and is correct
        (ie. monitors VM Instances, ideally with a nice style)
        - display info about all instances
        - this info must be selected and designed how to be displayed

        - will terminate if bad argument(s) are detected

        - optional 'watch' argument "-w" or "-watch" or "watch"
        --> if this is present as the first argument after 'monitor.py', runs the program infinitely using a sleep timer (thus "watching")
        --> Before printing and displaying info, give a message to user saying they can stop and exit the program using 'Ctrl+c' (or 'Command+c' on Mac)
        --> After, it continues to the output table every N seconds until its manually terminated by user

        - optional argument refresh_rate_seconds (integer)
        --> to use this argument, it must be used with the -w/-watch/watch optional argument
        --> by giving an integer, the user can change the number of seconds the program sleeps before refreshing the monitoring display info
        --> by default, it refreshes every 10 seconds

        - optional 'flush' argument "-f" or "-flush" or "flush"
        --> to use this argument, it must be used with the previous two optional arguments
        --> Before printing and displaying info, clear everything first (thus "flushing")
        --> After printing and displaying info, give a message to user saying they can stop and exit the program using 'Ctrl+c' (or 'Command+c' on Mac)
          - Notice this message is printed after the table output instead of before, in contrast to 'watch' flag

        - Using this script in its simplest form `py monitor.py` will output a table of display information related to monitoring VM instances
          - Simply run the script again whenever you want an update
          - Alternatively, turn on the 'watch' version and let it update automatically in a terminal
          - Notice, that a further optional argument allows you to change the default 10 second refresh rate
          - Further notice, that the next optional argument after allows you to run an output 'flushing' version that refreshes
'''

############################################# IMPORTS #############################################

# IMPORTS - 'pip install <import-package>'
import boto3
import csv
import os
import sys
import time

############################################ CONSTANTS ############################################

USAGE_STATEMENT = "Usage: py monitor.py <-w,-watch,watch|optional> <refresh_rate_seconds|optional,int> <-f,-flush-flush|optional>"

############################## STATE VARIABLES, INITIALIZATION, MAIN ##############################

def main():
    #globals
    global ec2_client
    global ec2_resource

    # ========== ARGUMENTS ==========

    # Declare optional argument default values
    watch_flag = False
    refresh_rate_seconds = 10
    flush_flag = False

    # Collect command line arguments when executing this python script
    argc = len(sys.argv)
    bad_usage_flag = False

    # Check args
    if argc >= 2:
        if sys.argv[1] == None or sys.argv[1] == "" or sys.argv[1] != "-w" and sys.argv[1] != "-watch" and sys.argv[1] != "watch":
            bad_usage_flag = True
            print("Error: Given watch flag '" + sys.argv[1] + "' is invalid - must be set as '-w' or '-watch' or 'watch'.")
        else:
            watch_flag = True
    if argc >= 3:
        if not sys.argv[2].isdigit():
            bad_usage_flag = True
            print("Error: Given refresh rate '" + sys.argv[2] + "' is not an integer.")
        elif len(sys.argv[2]) < 1 or len(sys.argv[2]) > 10:
            bad_usage_flag = True
            print("Error: Refresh rate must be between 1 and 10 seconds (inclusive)!")
        else:
            refresh_rate_seconds = int(sys.argv[2])
    if argc >= 4:
        if sys.argv[3] == None or sys.argv[3] == "" or sys.argv[3] != "-f" and sys.argv[3] != "-flush" and sys.argv[3] != "flush":
            bad_usage_flag = True
            print("Error: Given flush flag '" + sys.argv[3] + "' is invalid - must be set as '-w' or '-flush' or 'flush'.")
        else:
            flush_flag = True
    if argc > 4:
        bad_usage_flag = True
        print("Error: Too many arguments.")
    
    # Exit with usage statement if flag has been triggered for any reason
    if bad_usage_flag:
        sys.exit(USAGE_STATEMENT)

    # ========== AWS EC2 ==========
    ec2_client = boto3.client("ec2")
    ec2_resource = boto3.resource("ec2")

    # Validate AWS EC2 credentials (by testing if 'describe_instances()' works)
    try:
        ec2_client.describe_instances()
    except Exception as e:
        print("Error: Invalid or expired credentials (or insufficient permissions to call 'describe_instances()')")
        sys.exit(f"[ERROR] {e}")

    # ========== MONITOR VM INSTANCES ==========
     
    # Infinitely display monitor info (clearing last display first), every N seconds (default 10), until user manually stops (with keyboard interrupt)
    if watch_flag:
        try:
            # Give user msg saying how to quit if flush flag is not set
            if not flush_flag:
                print("--Please use command keyboard interrupt 'Ctrl+c' or ('Command+c' for Mac) to stop monitoring and exit the program--\n")
                
            while True:
                # Get monitor output table of display info
                output = get_monitor_output_table()

                # Flush existing stdout monitor display info (via 'clear') if flush flag is set, then print output table
                if flush_flag:
                    os.system(f"clear")
                print(output)
                
                # Give user msg saying how to quit if flush flag is set, then sleep N seconds before displaying monitor info again
                if flush_flag:
                    print("--Please use command keyboard interrupt 'Ctrl+c' or ('Command+c' for Mac) to stop monitoring and exit the program--\n")
                time.sleep(refresh_rate_seconds)

        except KeyboardInterrupt:
            # Catch user manual termination and give nice ALERT saying they closed it 
            sys.exit("ALERT: User manually stopped monitoring the VM instances, thus terminating the program.")
    
    else:
        # Get monitor output table of display info
        output = get_monitor_output_table()
        # try:
        #     output = get_monitor_output_table()
        # except Exception as e:
        #     sys.exit(f"[ERROR] While constructing monitor output table for display info of VM instances: {e}")
        
        # Print output table
        print(output)

############################################ FUNCTIONS ############################################

# Returns the monitor output table of display info
def get_monitor_output_table():
    # Get all instances
    instances = list(ec2_resource.instances.all())
    length = len(instances)

    # Col lists hold all column info individually
    template_list = ["TEMPLATE NAME"]
    instance_list = ["INSTANCE NAME"]
    state_list = ["STATE"]
    instance_id_list = ["INSTANCE ID"]
    image_id_list = ["IMAGE ID"]
    public_ip_list = ["PUBLIC IPV4"]
    type_list = ["INSTANCE TYPE"]
    sec_group_list = ["SECURITY GROUP"]

    # Skip if no instances exist
    if length > 0:
        # Get necessary info from all instances, storing in its col list
        try:
            for inst in instances:
                # Reload each instance before getting info
                inst.reload()

                # Get template and instance name
                template_name = "NULL"
                instance_name = "NULL"
                tags = inst.tags
                for tag in tags:
                    if tag['Key'] == 'TemplateName':
                        template_name = tag['Value']
                    elif tag['Key'] == 'InstanceName':
                        instance_name = tag['Value']
                template_list.append(str_return_empty_for_none(template_name))
                instance_list.append(str_return_empty_for_none(instance_name))

                # Get status state, instance ID, image ID, public ipv4 (already know max length)
                state_list.append(str_return_empty_for_none(inst.state['Name'].upper()))
                instance_id_list.append(str_return_empty_for_none(inst.id))
                image_id_list.append(str_return_empty_for_none(inst.image_id))
                public_ip_list.append(str_return_empty_for_none(inst.public_ip_address))

                # Get instance type, security group name (turn it into comma-separated list, strip extra tailing comma)
                type_list.append(str_return_empty_for_none(inst.instance_type))
                sec_groups = ""
                for sec_group in inst.security_groups:
                    sec_groups += f"{sec_group['GroupName']},"
                sec_group_list.append(str_return_empty_for_none(sec_groups.strip(',')))

        except Exception as e:
            sys.exit(f"[ERROR] While gathering info from VM instances: {e}")
    
    # Determine all col widths (include col header), some we already know max, others we calculate
    template_max = 0
    instance_max = 0
    state_max = len("SHUTTING-DOWN") #13
    instance_id_max = len("i-0d57e622c8f32a7ae") #19
    image_id_max = len("ami-0dba2cb6798deb6d8") #21
    public_ip_max = len("255.255.255.255") #15
    type_max = 0
    sec_group_max = 0

    # Challenge max lengths (+1 for table headers)
    for i in range(length+1):
        template_max = max(template_max, len(template_list[i]))
        instance_max = max(instance_max, len(instance_list[i]))
        type_max = max(type_max, len(type_list[i]))
        sec_group_max = max(sec_group_max, len(sec_group_list[i]))

    # Construct monitor output table
    ## old Table headers: TEMPLATE NAME, INSTANCE NAME, STATE, INSTANCE ID, IMAGE ID, PUBLIC IPV4, INSTANCE TYPE, SECURITY GROUP
    # Table headers: TEMPLATE NAME, IMAGE ID, INSTANCE NAME, INSTANCE ID, STATE, PUBLIC IPV4, INSTANCE TYPE, SECURITY GROUP
    output = ""
    for i in range(length+1):
        ## bad old table calculated version
        ## output += f"{template_list[i].ljust(template_max)}   {instance_list[i].ljust(instance_max)}   {state_list[i].ljust(state_max)}   {instance_id_list[i].ljust(instance_id_max)}   "
        ## output += f"{image_id_list[i].ljust(image_id_max)}   {public_ip_list[i].ljust(public_ip_max)}   {type_list[i].ljust(type_max)}   {sec_group_list[i].ljust(sec_group_max)}\n"
        
        # Hardcoded approximate version
        # output += f"{template_list[i].ljust(25)}{image_id_list[i].ljust(25)}{instance_list[i].ljust(20)}{instance_id_list[i].ljust(25)}"
        # output += f"{state_list[i].ljust(15)}{public_ip_list[i].ljust(18)}{type_list[i].ljust(15)}{sec_group_list[i].ljust(20)}\n"

        # Calculated version
        output += f"{template_list[i].ljust(template_max+3)}{image_id_list[i].ljust(image_id_max+3)}{instance_list[i].ljust(instance_max+3)}{instance_id_list[i].ljust(instance_id_max+3)}"
        output += f"{state_list[i].ljust(state_max+3)}{public_ip_list[i].ljust(public_ip_max+3)}{type_list[i].ljust(type_max+3)}{sec_group_list[i].ljust(sec_group_max+3)}\n"

    return output

############################################# HELPERS #############################################

# Returns an empty string if string given is None
def str_return_empty_for_none(str_check):
    if str_check == None:
        return ""
    else:
        return str(str_check)

###################################################################################################

main()
