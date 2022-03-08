from botocore.client import Config
from botocore.exceptions import ClientError
from datetime import datetime
import boto3
import logging
import pandas as pd

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

# put deny policy for s3:GetObject
def delete_bucket(bucket):
    try:
        # delete bucket objects
        bucket_objects = s3resource.Bucket(bucket)
        response = bucket_objects.objects.all().delete()
        logger.info('Bucket: {}, Response: {}'.format(bucket, response))
        # delete bucket
        response = s3client.delete_bucket(Bucket=bucket)
        logger.info('Bucket: {}, Response: {}'.format(bucket, response))
    except ClientError as e:
        logger.info('Bucket: {}, Error: {}'.format(bucket, e))

# insert bucket names here
buckets = ['bucket-name']
for bucket in buckets:
    delete_bucket(bucket)