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
    # delete_list = ['DELETE', 'delete', 'Delete', 'DELETED', 'deleted', 'Deleted']
    # if the action is keep or deleted, edit the bucket name accordingly
    for i in range(len(bucket_action)):
        if bucket_action[i] in keep_list:
            bucket_names[i] = 'KEEP'
        # elif bucket_action[i] in delete_list:
        #     bucket_names[i] = 'DELETED'
        
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