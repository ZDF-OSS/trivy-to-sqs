import json
import logging
import sys
import boto3
import base64
import gzip
import time
from botocore.exceptions import ClientError
from utils import get_cluster_name  # Import the get_cluster_name function
from enrich import enrich_payload  # Import the enrichment function

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize SQS client and cluster name globally
sqs = boto3.client('sqs', region_name='eu-central-1')
cluster_name = get_cluster_name()  # Get cluster name dynamically

# Load configuration, queue URL, and account ID globally to avoid multiple calls
config = None
queue_url = None
account_id = None  # Global variable for account ID


def load_config():
    """
    Load configuration from a local JSON file (config.json).
    This function is called once at the start.
    """
    global config
    if config is None:
        try:
            with open('config.json') as config_file:
                config = json.load(config_file)
        except Exception as e:
            logging.error(f"Failed to load configuration: {e}")
            sys.exit(1)
    return config


def get_sqs_queue_url():
    """
    Retrieve and cache the URL for the SQS queue, assuming there's only one queue.
    """
    global queue_url
    if queue_url is None:
        config = load_config()
        try:
            response = sqs.get_queue_url(QueueName=config['queue_name'], QueueOwnerAWSAccountId=config['account_id'])
            queue_url = response['QueueUrl']
        except ClientError as e:
            logging.error(f"Failed to get queue URL: {e}")
            sys.exit(1)
    return queue_url


def get_account_id():
    """
    Retrieve and cache the AWS account ID.
    """
    global account_id
    if account_id is None:
        try:
            account_id = boto3.client('sts').get_caller_identity().get('Account')
        except ClientError as e:
            logging.error(f"Failed to get AWS account ID: {e}")
            sys.exit(1)
    return account_id


def send_to_sqs(message_body):
    """
    Sends a compressed JSON message to an AWS SQS queue.
    """
    queue_url = get_sqs_queue_url()  # Use the cached queue URL

    try:
        # Serialize the message body to a JSON string
        message_json = json.dumps(message_body)
        original_size_kb = len(message_json.encode('utf-8')) / 1024
        logging.info(f"Original message size: {original_size_kb:.2f} KB")

        # Compress the JSON string using gzip
        compressed_bytes = gzip.compress(message_json.encode('utf-8'), compresslevel=9)
        compressed_base64 = base64.b64encode(compressed_bytes).decode('utf-8')
        compressed_size_kb = len(compressed_base64.encode('utf-8')) / 1024
        logging.info(f"Compressed message size: {compressed_size_kb:.2f} KB")

        # Ensure the compressed message size is within SQS limits
        if compressed_size_kb > 256:
            logging.error("Compressed message size exceeds SQS limit of 256 KB.")
            filename = f"failed_message_{int(time.time())}.json"
            with open(filename, 'w') as f:
                json.dump(message_body, f)
            logging.info(f"Message saved to file {filename}")
            sys.exit(1)

        # Send the message to SQS
        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=compressed_base64,
            MessageAttributes={
                'ContentEncoding': {'StringValue': 'gzip', 'DataType': 'String'},
                'ContentType': {'StringValue': 'application/json', 'DataType': 'String'}
            }
        )
        logging.info(f"Message sent to SQS queue, MessageId: {response['MessageId']}")
        return response
    except ClientError as e:
        logging.error(f"Failed to send message: {e}")
        filename = f"failed_message_{int(time.time())}.json"
        with open(filename, 'w') as f:
            json.dump(message_body, f)
        logging.info(f"Message saved to file {filename}")
        sys.exit(1)


def send_to_input_sqs(container_name, scan_payload):
    """
    Send scan result payload to the SQS queue.
    """
    # Load config and enrich payload once
    config = load_config()

    # Get account ID once
    account_id = get_account_id()

    # Enrich the payload with additional metadata
    enriched_payload = enrich_payload(scan_payload, account_id, cluster_name, container_name)

    # Send the enriched payload to SQS
    send_to_sqs(enriched_payload)
