#! /bin/sh

# to make resetting aws creds a little easier (copy-paste values here)
aws_access_key_id=LOL
aws_secret_access_key=XD
aws_session_token=FwoGZXIvYXdzEBoaDHX+NZKnCBTHJoK8EiLEAR4EykdivBgXXyxHahYJnFh7ZAP5sKv1TXwXmpexg88qFmxs8B3BSB98mVzbXJonTIrIfhIWtGflI1dJKuoVwlCyqBWzABm1QFKnPg3JXgtAE61i46yW3uj9VTRAtdKi1HEjFrFS3zcVhHLAzdybg8xlHKI0GuNx/PHFMDmJ1VaBdOJIl2RaiIDk5SgN5t4pdfyxdZ3aIKdF4vFfLIoDGbg0IaCmjGZNPt8SZyDAJ2QrQC0YRPC0SlL0f6fzcODuyIhLVocos4Dx/AUyLThXCK37qIpcD3vkI/h41j58BXFzcjLnp5k+jVzigldh78NZEwKcqcPsrE/AIg==

# in order: set aws credentials config for key, secret, session token
aws configure set aws_access_key_id $aws_access_key_id
aws configure set aws_secret_access_key $aws_secret_access_key
aws configure set aws_session_token $aws_session_token
# shouldn't need to change the region
#aws configure set region us-east-1
