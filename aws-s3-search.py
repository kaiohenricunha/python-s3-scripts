from botocore.client import Config
from botocore.exceptions import ClientError
from datetime import datetime
import botocore
import boto3
import logging

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
buckets = s3client.list_buckets()['Buckets']

public_buckets = []
public_acl_indicator = ['http://acs.amazonaws.com/groups/global/AllUsers','http://acs.amazonaws.com/groups/global/AuthenticatedUsers']
permissions_to_check = ['READ', 'WRITE', 'FULL_CONTROL', 'WRITE_ACP']

def check_bucket_access_block():
    for bucket in buckets:
        try:
            response = s3client.get_public_access_block(Bucket=bucket['Name'])
            for key, value in response['PublicAccessBlockConfiguration'].items():
                logger.info('Bucket: {}, {}: {}'.format(bucket['Name'], key, value))
                # if not response['PublicAccessBlockConfiguration']['BlockPublicAcls'] and not response['PublicAccessBlockConfiguration']['BlockPublicPolicy'] and bucket['Name'] not in public_buckets:
                #     logger.info('Bucket: {} blocks are set to False'.format(bucket['Name']))
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchPublicAccessBlockConfiguration':
                logger.info("Bucket: {} has no Public Access Block Configuration".format(bucket['Name']))
            else:
                logger.info("unexpected error: %s" % (e.response))

def check_bucket_status():
    try:
        for bucket in buckets:
            response = s3client.get_bucket_policy_status(Bucket=bucket['Name'])['PolicyStatus']['IsPublic']
            logger.info('Bucket Name: {}, Public: {}'.format(bucket['Name'], response))
            if response == True and bucket['Name'] not in public_buckets:
                public_buckets.append(bucket['Name'])
    except botocore.exceptions.ClientError as e:
        logger.info("unexpected error: %s" % (e.response))

def check_bucket_acl():
    for bucket in buckets:
        try:
            response = s3client.get_bucket_acl(Bucket=bucket['Name'])
            logger.info('Bucket: {}, ACL: {}'.format(bucket['Name'], response['Grants']))
            # get_bucket_size(bucket['Name'])
            for grant in response['Grants']:
                for (key, value) in grant.items():
                    if key == 'Permission' and any(permission in value for permission in permissions_to_check):
                        for (grantee_key, grantee_value) in grant['Grantee'].items():
                            if 'URI' in grantee_key and grant['Grantee']['URI'] in public_acl_indicator:
                                if bucket['Name'] not in public_buckets:
                                    public_buckets.append(bucket['Name'])
            if get_bucket_size(bucket['Name']) > 0: # If the bucket has any object, it calls the function to check the object ACL
                check_object_acl(bucket['Name'])
                logger.info(" ")
            else:
                logger.info("")
        except botocore.exceptions.ClientError as e:
            logger.info("unexpected error: %s" % (e.response))

def check_object_acl(bucket_name):
    try:
        s3bucket = s3resource.Bucket(bucket_name)
        for key in s3bucket.objects.all():
            response = s3client.get_object_acl(Bucket=bucket_name, Key=key.key)
            logger.info('Object: {}, ACL: {}'.format(key.key, response['Grants']))
            for grant in response['Grants']:
                for (key, value) in grant.items():
                    if key == 'Permission' and any(permission in value for permission in permissions_to_check):
                        for (grantee_key, grantee_value) in grant['Grantee'].items():
                            if 'URI' in grantee_key and grant['Grantee']['URI'] in public_acl_indicator:
                                if bucket_name not in public_buckets:
                                    public_buckets.append(bucket_name)
    except botocore.exceptions.ClientError as error:
        logger.info("{}, BucketName: {}".format(error, bucket_name))
        logger.info(" ")
        pass

def get_bucket_size(bucket_name):
    try:
        count = 0
        s3bucket = s3resource.Bucket(bucket_name)
        for key in s3bucket.objects.all():
            count += 1
        logger.info("Total Objects Count: {}".format(count))
        return count
    except botocore.exceptions.ClientError as error:
        logger.info("{}, BucketName: {}".format(error, bucket_name))
        logger.info(" ")
        pass

check_bucket_access_block()
logger.info('\n')
check_bucket_status()
logger.info('\n')
logger.info('\n')
check_bucket_acl()
logger.info('\n')
logger.info('Public Buckets: {}'.format(public_buckets))
