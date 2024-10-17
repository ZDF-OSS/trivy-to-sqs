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

# Initialize SQS client
sqs = boto3.client('sqs')

cluster_name = get_cluster_name()  # Get cluster name dynamically


def load_config():
    """
    Load configuration from a local JSON file (config.json).
    """
    try:
        with open('config.json') as config_file:
            config = json.load(config_file)
            return config
    except Exception as e:
        logging.error(f"Failed to load configuration: {e}")
        sys.exit(1)


def send_to_sqs(queue_name, account_id, message_body):
    """
    Sends a compressed JSON message to an AWS SQS queue.
    """
    try:
        # Get the URL for the SQS queue
        response = sqs.get_queue_url(QueueName=queue_name, QueueOwnerAWSAccountId=account_id)
        queue_url = response['QueueUrl']
    except ClientError as e:
        logging.error(f"Failed to get queue URL for {queue_name}: {e}")
        sys.exit(1)

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

        if compressed_size_kb > 256:
            logging.error("Compressed message size exceeds SQS limit of 256 KB.")
            filename = f"failed_message_{int(time.time())}.json"
            with open(filename, 'w') as f:
                json.dump(message_body, f)
            logging.info(f"Message saved to file {filename}")
            sys.exit(1)

        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=compressed_base64,
            MessageAttributes={
                'ContentEncoding': {'StringValue': 'gzip', 'DataType': 'String'},
                'ContentType': {'StringValue': 'application/json', 'DataType': 'String'}
            }
        )
        logging.info(f"Message sent to SQS queue {queue_name}, MessageId: {response['MessageId']}")
        return response
    except ClientError as e:
        logging.error(f"Failed to send message to {queue_name}: {e}")
        filename = f"failed_message_{int(time.time())}.json"
        with open(filename, 'w') as f:
            json.dump(message_body, f)
        logging.info(f"Message saved to file {filename}")
        sys.exit(1)


def send_to_input_sqs(container_name, scan_payload, account=None):
    """
    Send scan result payload to the SQS queue.
    """

    config = load_config()
    account_id = account if account else boto3.client('sts').get_caller_identity().get('Account')

    # Enrich the payload with additional metadata
    enriched_payload = enrich_payload(scan_payload, account_id, cluster_name, container_name)

    # Send the enriched payload to SQS
    send_to_sqs(config['queue_name'], config['account_id'], enriched_payload)
