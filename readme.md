# Installation and Virtual Environment Setup

- Before installing the necessary packages, make sure you have Python 3.6 or later, and pip3.

- Clone this repository to your local machine.

To isolate the necessary packages, create a Python virtual environment.

- Install virtualenv:
    ```
    pip3 install virtualenv
    ```

- Create a virtual environment and activate it:
    ```
    virtualenv [name of your new virtual environment]
    ```
    ```
    source [name of your virtualenv]/bin/activate
    ```

- Then, install the latest Boto3, botocore and pandas release via pip3:

    ```
    pip3 install boto3 botocore pandas
    ```

- You can alternatively run the following command:

    ```
    pip3 install -r requirements.txt
    ```

- To deactivate the virtual environment, run:

    ```
    deactivate
    ```

# AWS CLI Configuration

- If you have the AWS CLI installed, then you can use the aws configure command to configure your credentials file:

    ```
    aws configure
    ```

- It will prompt you for your AWS access key ID and secret access key.

    ```
    aws_access_key_id = YOUR_ACCESS_KEY
    aws_secret_access_key = YOUR_SECRET_KEY
    ```

By default, its location is ~/.aws/credentials.

# Intro

- The idea of this script is to restrict owners access to their bucket's objects. 

- It's not for the sake of restriction only, but for getting an idea of possible issues that deleting these **apparently** unused buckets may bring.

- **This is a step to be taken before actually deleting unused buckets**.

- So, the script reads a CSV file with information about the buckets, loads the bucket names from a column in a variable, and from this info restricts access to the collected buckets' objects. 

- It also has an undo feature that removes the restriction if necessary. The CSV file was created in a previous step and contains all the buckets in the account that haven't been used in a long time.

# The script

**put-restriction.py**

It is the main script that inserts the restriction policy in the buckets.

```
from operator import index
from botocore.client import Config
from botocore.exceptions import ClientError
from datetime import datetime
import botocore
import boto3
import logging
import pandas as pd
import json

# logging setup
logger = logging.getLogger()
logger.setLevel(logging.INFO)  # or any level you want

# on-screen log output
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)  # or any other level
logger.addHandler(ch)

# log file output
timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
fh = logging.FileHandler('aws-s3-search-{}.log'.format(timestamp))
fh.setLevel(logging.INFO)  # or any level you want
logger.addHandler(fh)

# boto3 timeout config
config = Config(connect_timeout=10, retries={'max_attempts': 5})

# s3 client objects setup
s3client = boto3.client('s3', config=config)
s3resource = boto3.resource('s3', config=config)

# collects and filters bucket names and actions from csv file
def collect_bucket_names():
    file_name = 'bucket-data.csv'
    col = ['Name', 'Action']
    bucket_info = pd.read_csv(file_name, usecols=col)
    bucket_names = bucket_info['Name'].tolist()
    bucket_action = bucket_info['Action'].tolist()
    keep_list = ['KEEP', 'keep', 'Keep']
    delete_list = ['DELETE', 'delete', 'Delete', 'DELETED', 'deleted', 'Deleted']
    # if the action is keep or deleted, edit the bucket name accordingly
    for i in range(len(bucket_action)):
        if bucket_action[i] in keep_list:
            bucket_names[i] = 'KEEP'
        elif bucket_action[i] in delete_list:
            bucket_names[i] = 'DELETED'
    # trim the bucket names to remove spaces
    bucket_names = [x.strip() for x in bucket_names]
    logger.info(bucket_names)

    return bucket_names

# calls the restrict_bucket_access function IF the bucket is responsive
def check_bucket_exists(buckets):
    for bucket in buckets:
        try:
            response = s3client.head_bucket(Bucket=bucket)
            if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                restrict_bucket_access(bucket)
        except ClientError as e:
            logger.info('Bucket: {}, Error: {}'.format(bucket, e))

# put deny policy for s3:GetObject
def restrict_bucket_access(bucket):
    bucket_policy_template = {
    'Version': '2012-10-17',
    'Statement': [{
        'Sid': 'RestrictGetObject',
        'Effect': 'Deny',
        'Principal': '*',
        'Action': ['s3:GetObject'],
        'Resource': f'arn:aws:s3:::{bucket}/*'
    }]
}
    try:
        # get policy before removal and logs it
        response = s3client.get_bucket_policy(Bucket=bucket)
        bucket_policy = json.loads(response['Policy'])
        logger.info('Bucket: {}, Policy Before Restriction: {}'.format(bucket, bucket_policy))
        
        # adds restriction policy and logs the policy after restriction
        bucket_policy['Statement'].insert(0, bucket_policy_template['Statement'][0])
        bucket_policy = json.dumps(bucket_policy)
        response_put = s3client.put_bucket_policy(Bucket=bucket, Policy=bucket_policy)
        response = s3client.get_bucket_policy(Bucket=bucket)
        bucket_policy = json.loads(response['Policy'])
        logger.info('Bucket: {}, Policy After Restriction: {}'.format(bucket, bucket_policy))
    except ClientError as e:
        logger.info('Bucket: {}, Error: {}'.format(bucket, e))

buckets = collect_bucket_names()
logger.info('\n')
check_bucket_exists(buckets)
```

**remove-restriction.py**

This script removes the restriction of a single bucket or a group of buckets if necessary

```
# Delete Bucket Policy
def remove_restriction(bucket):
    try:
        # get policy before removal and logs it
        response = s3client.get_bucket_policy(Bucket=bucket)
        bucket_policy = json.loads(response['Policy'])
        logger.info('Bucket: {}, Policy Before Removal: {}'.format(bucket, bucket_policy))

        # removes restriction policy and logs the policy after removal
        bucket_policy['Statement'].remove(bucket_policy['Statement'][0])
        bucket_policy = json.dumps(bucket_policy)
        response_put = s3client.put_bucket_policy(Bucket=bucket, Policy=bucket_policy)
        response = s3client.get_bucket_policy(Bucket=bucket)
        bucket_policy = json.loads(response['Policy'])
        logger.info('Bucket: {}, Policy After Removal: {}'.format(bucket, bucket_policy))
    except ClientError as e:
        logger.info('Bucket: {}, Error: {}'.format(bucket, e))

bucket_names = ['bucket-names']
for bucket in bucket_names:
    remove_restriction(bucket)
```

**logs folder**

It contains the log files created by the script during the testing phase.

**tests folder**

Contains **restriction-test**, used to test adding the restriction policy to the buckets, and **remove-restriction-test**, used to test removing the restriction policy from the buckets.
