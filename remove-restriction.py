from operator import index
from botocore.client import Config
from botocore.exceptions import ClientError
from datetime import datetime
import botocore
import boto3
import logging
import pandas as pd
import json

# Setup Logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)  # or any level you want

# OnScreen Log Output
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)  # or any other level
logger.addHandler(ch)

# Log File Output
timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
fh = logging.FileHandler('aws-s3-search-{}.log'.format(timestamp))
fh.setLevel(logging.INFO)  # or any level you want
logger.addHandler(fh)

# Boto3 Timeout Config
config = Config(connect_timeout=10, retries={'max_attempts': 5})

# Objects S3 Instances
s3client = boto3.client('s3', config=config)
s3resource = boto3.resource('s3', config=config)

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

bucket_names = ['']
for bucket in bucket_names:
    remove_restriction(bucket)