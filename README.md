# OneClickVMDeploymentAWS_4010
One-Click Deployment of VMs and Containers + Monitoring + Write-up (Cloud Computing course A2)

# Info

- Name: Mitchell Van Braeckel
- Student ID: 1002297
- Course: CIS*4010 Cloud Computing
- Assignment: 2
- Brief: One-Click Deployment of VMs and Containers + Monitoring + Write-up
- Due: (Extended) Fri Nov 6, 2020

## General

- All Python modules required (`pip install <import-package>`) besides AWS stuff (like its CLI)
  - import boto3
  - import csv
  - import os
  - import paramiko
  - import sys
  - import time

- Extra VM Instances and Containers are showed in the `template.csv`, `instances.csv`, and `container.csv` besides the required ones
  - Extra VM Instances:
    - UbuntuServer18.04LTS,ami-0817d428a6fb68645
    - UbuntuServer16.04LTS,ami-0f82752aa17ff8f5d
  - Extra Containers:
    - hellocloud, from Docker hub/dastacey, without a start script
      - NOTICE: the 'dastacey' part (the entire part after 'Docker hub/') is parsed and used as the repoName for docker command (eg. `docker pull repoName/containerName)`)
      - note: location 'Dockerfile/' is not supported
    - golang, from Docker hub, with `startScript-gogadget.sh`

- Generally, I error check a lot, so most things won't break the program
  - You can search in any file for the following error messages `"Error` or `"ERROR` or `[ERROR]` to finderror messages I made
    - `"Error` standard I caught it starting
    - `"ERROR` exit type error message
    - `[ERROR]` is the `print_error` template starting

- DISCLAIMER: I received an extension to Fri Nov 6 2020 11:59:59 PM
  - Please email me at `mvanbrae@uoguelph.ca` if there are any issues with my submission (deadline, code, comments, understanding, how to run, etc.)

- TL;DR
  - I documented how to run each program, but did not document what each program does not do because it does everything that is required
  - Although I say to assume perfect input, setup, preconditions, formatting, etc., I do error check a decent amount and should catch pretty much everything
    - of course, it still needs the CSVs, PEMs, bash scripts, etc., to actually function though
  - Go to the usage part for each python script and also take a look at the general section just after it
  - I recommend to skip the preconditions (of `launch.py` especially) since there are a lot of assumptions and notes
    - Can come back to it later if there are issues, otherwise feel free to give it all a read now
    - Pretty sure I jotted down ALL my thoughts as I developed, but may have left some out of this README
  - Important points being skipped are:
    - Essentially, I exit if preconditions fail (giving best error messages possible, trying to describe specific things as appropriate) - but if other things fail, I try to keep going (eg. so other instances and container stuff can happen even if the first one fails while SSH'd etc.)
    - End of part 1.a precondition 1 - covers most validation cases, specifically with regards to initial verification using info from CSVs, where it exits if not valid
    - CSV templates perfect formatting as expected, etc.
      - All CSVs require a header row, but ignore its contents
      - Template Name uniqueness, Instance Name uniqueness (within respective CSVs)
      - TemplateName format expectation - where I force descriptive names that are used to determine distro and user (applies to SSH and Docker install)
      - container location format expectation - applies to repoLocation/containerName vs containerName for Docker stuff
      - sshkey.pem on local VS sshkey (without .pem) on AWS
    - files are expected to be same local dir as the python script being run
    - I use the same security group name and associated PEM for everything, so to test another, it would need to be properly created
    - which specific things are validated (may have missed adding some anyways)
      - don't worry, these should be caught as errors when things are invalid (or at least the exceptions are caught if I didn't explicitly validate)
    - SSH will fail after 10 tries that are 5 seconds apart (usually succeeds in first 1-3 attempts)
      - installs docker, pulls image, runs docker or start script (if one present in CSV row)
        - ie. I use "docker run" if there's no bash start script, otherwise I put that script on instance and run it
      - logs for what is going through the SSH on the instance are still displayed to user
      - doing multiple things in one instance for multiple containers don't interfere with one another
    - all files must have proper line endings (eg. bash scripts should be LF)

## Part 1.a) - One-Click Deployment of VMs and Container

### Running `launch.py`

Usage: `py launch.py`

- Just run the script and sit back and enjoy the logs it outputs as everything deploys automatically :)
- See General 1.a) and the following Preconditions 1-4 for notes and assumptions about this script
  - Also, `launch.py` has many comments including a file header comment (which doesn't have anything that useful this time)

### General 1.a)

- assume proper AWS credentials already made, key, secret key, session token, region, etc. (similar to A1 Part 2 DynamoDB)
- assume that errors for preconditions are significant and handle strictly, typically by terminating the program
  - in other words, the user would investigate the issues with preconditions based on the output and fix things before trying `launch.py` again
- assume that for the duration of this program, there are no other instances in any state
  - NOTE: I try to ignore any instances that may already exist in some state when this program is run
- assume an instance is only related to one security group (the one from when it was created)
- assume that I can use the keyword identifier from the properly formatted and descriptive template name to get a keyword identifier that I can use to determine the user and determine what bash script the instance needs to install Docker on that distro
  - these Docker installation scripts have naming convention `dockerInstall-keyword.sh` and are located in local dir same as python script
- note that when you SSH and use docker commands in an instance, you will most likely need to use `sudo` in front of docker commands, when testing (below are example commands):
  - `docker images`
  - `docker container ls -a`
  - `docker run hello-world`
  - `docker run hellocloud`
  - `docker run gogadget`
- note: I have scripts for SUSE and Red Hat, but not properly confirmed/tested because I used other Ubuntu 18.04 and 16.04 versions as "extra" VM instances
- note: I have code for Dockerfile as location, but not properly confirmed/tested, so I error out and say unsupported
- note: Typically, if any validations or verifications of preconditions fail, the program is terminated

### Precondition 1: Deployment Description Files

- assume all 3 CSV files have been properly filled out and formatted without human error or syntax error (proper spacing/symbols, number of columns, header row is first row, etc.)
  - expects the 3 CSV files: `template.csv`, `instances.csv`, `container.csv` ; all on local dir, same as python script
  - for all CSV files, assume first line/row are column headers and ignore it
  - what the header columns are don't matter, as long as they are in the proper order and have the correct number of columns

  - assume that template names are all unique within `template.csv`
    - expect the template names to use standard characters, no spaces, and no special characters (typical of most things, although we won't be checking for this)
    - expect template names to be descriptive in terms of what image is being used
      - eg. AmazonLinux2, UbuntuServer20.04LTS
    - assume template name format to at the bare minimum include an identifier such as: `"amazonlinux2", "amazonlinux", "centos", "debian", "fedora", "rhel", "suse", "ubuntu", "redhat"`, etc. to identify the AMI image ID (and not multiple of these keywords)
      - we will parse this, and use it to determine the user (alternatively, hardcoded user for each AMI image ID), such as "ec2-user", "ubuntu", etc. as appropriate
      - program will terminate if it fails to find a user this way because it means the template name has an incorrect format
  - assume that availability zone / region is valid and will always be a region accessible by the user (however, if it ends with a letter instead of a digit, it is an availability zone, but we won't account for this)

  - assume that instance names are all unique within `instances.csv`
  - assume that ssh key pair names must have a `.pem` extension

  - assume if container is `hello-world` and location is `Docker hub/dastacey` the command will be `docker pull dastacey/hello-world` and it has access to it
    - otherwise the command will just be `docker pull hello-world` for plain location `Docker hub`
  - NOT SUPPORTED: assume if the container is `hello-world` and the location is `Docker file` or `Docker file/` or `Docker file/.`, the "Dockerfile" is implicitly in the same directory as the python script
    - whereas assume if the location is `Docker file/location` it is either the exact path to the file or the path to the dir of the file (not supported, but note: there is some code for it, but not activated because not applicable)
  - always pull the docker image for each row in `container.csv`, but only docker run if there is no start script present in the row (if there is, use the start script instead)

  - assume that all template names, instance names, and container package names have been set up properly and exist at least once in the appropriate files
    - eg. for every template name in `template.csv`, it exists at least once in `instances.csv`, and vice versa
    - eg. similarly, for every container package name, for `instances.csv` vs `container.csv`, and vice versa
  - assume all files must have proper line endings (eg. bash scripts should be LF)

- validate the following based on the 3 CSV file contents (catch and terminate when these are broken):
  - all template names contain exactly one of the given identifiers: `"amazonlinux2", "amazonlinux", "centos", "debian", "fedora", "rhel", "suse", "ubuntu", "redhat"`
    - exception: `amazonlinux2` can exist instead of `amazonlinux2` (former is checked first and has priority)
    - use this to determine the user (and catch and terminate if none are found), respective to above: `"ec2-user", "ec2-user", "centos", "admin", "ec2-user", "ec2-user", "ec2-user", "ubuntu", "ec2-user"`
      - note: commonly, this will be `ec2-user` or `root`
  - CSV, PEM, SH files all exist in local dir same as python script and with proper .extension
    - Note: `.pem` is required in `instances.csv`, but is trimmed in the AWS EC2 public version
    - Note: start script isn't required, but if it is filled, it must be valid
  - all AMI image IDs exist on AWS EC2
  - all security group names exist on AWS EC2
  - all ssh key-pair public copy exist on AWS EC2

### Precondition 2: Start Scripts

- assume that a start script will be constructed in a similar manner to example, `batchScriptMode.sh`:

```bash
docker run -ti --rm r-base bash
```

- note that start scripts I made have naming convention `startScript-containerName.sh` and are located in local dir same as python script
- assume all files must have proper line endings (eg. bash scripts should be LF)

### Precondition 3: SSH Key Creation

- assume precondition 3, where all ssh keys are already created on AWS EC2 publicly and a local `sshkeyname.pem` version has been downloaded in the same dir as python script
  - expect the public ssh key on AWS EC2 to not have an extension (or at least not reference it that way), whereas expect the local dir version that has been downloaded will have the `.pem` extension
  - ** assume ssh key pair name (`.pem`) cannot contain '.' in the file name (besides for the extension `.pem`), catch this error and end program if this occurs
  - assume ssh key pair name will contain '`.pem`' in the CSV
  - assume the related public key that AWS stores is guaranteed to exist given that there exists a private key (`.pem`) locally
    - must exist in both locations, otherwise it will terminate
  - assume that the local PEM file will have proper `chmod 600` permissions
- note that I use security group "cis4010-all" and its `cis4010-all-a2.pem` for all my instances, although others can be used if setup properly
  - note that security group used has all traffic open as requested
- related to ssh, fail to connect to instance via ssh 10 times with 5 second delay, we give up and skip this one
  - I output lots of logs especially for SSH related things
  - Once connected, will try to continue on despite errors (so we can get thru program and see if there are others that work properly after this instance/container)

### Precondition 4: Docker Info

- assume all docker locations follow format "Docker hub" or "Docker hub/repo" and pull the image from there
  - assume we have proper access to all locations and all the containers are valid and exist (eg. pull from public repo)
- assume bash start scripts somehow create and/or run the container in that entry (without interfering with other things)

## Part 1.b) : Monitoring VM Instances

### Running `monitor.py`

Usage: `Usage: py monitor.py <-w,-watch,watch|optional> <refresh_rate_seconds|optional,int> <-f,-flush-flush|optional>`

- If you run the script, it looks at all the existing VM instances (note: not just running ones) and displays relevant info in a table format that the user can easily monitor

  - optional 'watch' argument "-w" or "-watch" or "watch"
    - if this is present as the first argument after 'monitor.py', runs the program infinitely using a sleep timer (thus "watching")
    - Before printing and displaying info, give a message to user saying they can stop and exit the program using 'Ctrl+c' (or 'Command+c' on Mac)
    - After, it continues to the output table every N seconds until its manually terminated by user

  - optional argument refresh_rate_seconds (integer)
    - to use this argument, it must be used with the -w/-watch/watch optional argument
    - by giving an integer, the user can change the number of seconds the program sleeps before refreshing the monitoring display info
    - by default, it refreshes every 10 seconds

  - optional 'flush' argument "-f" or "-flush" or "flush"
    - to use this argument, it must be used with the previous two optional arguments
    - Before printing and displaying info, clear everything first (thus "flushing")
    - After printing and displaying info, give a message to user saying they can stop and exit the program using 'Ctrl+c' (or 'Command+c' on Mac)
    - Notice this message is printed after the table output instead of before, in contrast to 'watch' flag

  - Using this script in its simplest form `py monitor.py` will output a table of display information related to monitoring VM instances
    - Simply run the script again whenever you want an update
    - Alternatively, turn on the 'watch' version and let it update automatically in a terminal
    - Notice, that a further optional argument allows you to change the default 10 second refresh rate
    - Further notice, that the next optional argument after allows you to run an output 'flushing' version that refreshes
  
- See General 1.b) and the following Precondition 1 for notes and assumptions about this script
  - Also, `launch.py` has many comments including a file header comment (which the above information is from)

### General 1.b)

- All notes and assumptions match that of `launch.py`, unless stated otherwise
  - Of course generic things like, assume proper AWS credentials already made, key, secret key, session token, region, etc. (similar to A1 Part 2 DynamoDB), as well as things relating to content like assuming all the CSV files will be properly created and formatted, etc.
- will terminate if bad argument(s) are detected
- Table headers (using these headers, I format a table to be displayed):
  - `TEMPLATE NAME, IMAGE ID, INSTANCE NAME, INSTANCE ID, STATE, PUBLIC IPV4, INSTANCE TYPE, SECURITY GROUP`
  - note: left out DNS, KeyName, and Size because I didn't think they were very important
    - DNS covered by IP
    - KeyName covered by security group
    - Size doesn't really matter
- This will monitor and display all VM instances (besides just running ones)

### Precondition 1: Instances Running

- assume that there is at least one instance running when this program is run
  - otherwise, it will only print the table column headers
- assume that the user is able to use keyboard interrupt "Ctrl+c" (or "Command+c" on Mac) to terminate the 'watch' version of monitoring

## Part 2 - Alternative Existing AWS Services to EC2

"For the tasks that you were asked to do in Part 1, suggest what existing AWS services could be used to do the similar tasks and compare the capabilities and easy of use for your programs and the AWS services."

- please see `Part2.pdf` for my written answer with the following format (2 pages: cover, answer body):
  - header info
  - title
  - question
    - A2 description part 2 question
    - A2 guide info grading scheme description
  - answer (on the next page, word count of next page) - the following describes the paragraphs of the answer on next page
    - suggesting alternative existing AWS services for first chunk
    - comparing to A2 programs regarding capabilities and ease of use (separated by blank line from above chunk)

## Grading Scheme                                    /35 marks

**`launch.py`:**                                     /22 marks

- successfully instantiates the required VM's   (12 marks)
- successfully loads the containers             (6  marks)
- extra VM's or containers demonstrated         (4  marks)

**`monitor.py`:**                                    /6  marks

- successfully monitors the VMs                 (4  marks)
- style of the monitor                          (2  marks)

**Gitlab:**                                          /4  marks

- README file                                   (3  marks)
  - documentation of how to run each program and what that program does and does not do
- Template files                                (1  mark )

**Part 2:**                                          /3  marks

- "The answer to the question posed in Part 2 should appear in a file in your A2 repo and should be named Part2.txt or Part2.pdf depending on its format.  This will be graded outside of your Zoom grading session.  It should not be any larger than 500 words."
