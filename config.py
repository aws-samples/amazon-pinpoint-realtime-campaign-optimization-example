import os

###################################
# VPC Parameters
###################################

vpc_id = 'vpc-xxxxxxxxxxx'
subnet_ids = [
    'subnet-xxxxxxxxxxxxx',
    'subnet-xxxxxxxxxxxxx'
]

###################################
# Account Setup
###################################
ACCOUNT = "xxxxxxxxxxxxx"
REGION = "xxxxxxxxxx"
CDK_ENV = {"account": ACCOUNT, "region": REGION}

###################################
# Default Parameters  (Edit as Needed)
###################################
create_dms_service_role = True
dms_service_role_arn = ''
port = 3308
namespace = 'dev'