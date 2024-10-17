# EKS Trivy Scan Results to SQS

This project provides a Python script that scans EKS workloads using [Trivy](https://github.com/aquasecurity/trivy), retrieves vulnerabilities from container images, and sends them as JSON messages to an AWS SQS queue. The script allows configuration of the SQS queue name, target AWS account, and other settings via a local configuration file.

## Features

- Scans EKS workloads for vulnerabilities using Trivy.
- Filters unique images from Kubernetes pods.
- Sends scan results as messages to an AWS SQS queue.
- Configurable queue name and AWS account ID via `config.json`.
- Payload enrichment with cluster, container, and account details.
- Modular code structure for easy extension and maintenance.

## Prerequisites

- Python 3.x
- [Trivy](https://github.com/aquasecurity/trivy) installed and accessible in your system’s PATH.
- AWS credentials with sufficient permissions to access SQS and assume IAM roles.
- `boto3` and `kubernetes` libraries installed (`pip install boto3 kubernetes`).

## Setup

### 1. **Clone the repository**:
   ```bash
   git clone https://github.com/ZDF-OSS/eks-trivy-sqs.git
   cd eks-trivy-sqs
   ```

### 2. **Install required dependencies**:
   Install Python dependencies listed in the `requirements.txt` file:
   ```bash
   pip install -r requirements.txt
   ```

### 3. **Create a local configuration file**:
   Create a `config.json` file in the root directory of the project. This file will be ignored by Git using `.gitignore`.

   Example `config.json`:
   ```json
   {
       "queue_name": "your-sqs-queue-name",
       "account_id": "123456789012",
       "cluster_name": "your-cluster-name"
   }
   ```

### 4. **Trivy Setup**:
   Ensure that [Trivy](https://github.com/aquasecurity/trivy) is installed and added to your system’s PATH. You can verify Trivy installation by running:
   ```bash
   trivy --version
   ```

### 5. **AWS Configuration**:
   Ensure that your AWS credentials are set up, either through environment variables, an AWS credentials file, or an instance profile (if running on EC2).

## Configuration

The configuration file (`config.json`) allows you to specify:
- `queue_name`: The name of the SQS queue where scan results will be sent.
- `account_id`: The AWS account ID owning the SQS queue.
- `cluster_name`: The name of your EKS cluster.

### Example `config.json`:

```json
{
    "queue_name": "my-sqs-queue",
    "account_id": "123456789012",
    "cluster_name": "my-cluster"
}
```

### Notes:
- **`queue_name`**: The SQS queue name must exist in your AWS account.
- **`account_id`**: Ensure that you have the necessary permissions in this AWS account.
- **`cluster_name`**: The name of the EKS cluster that will be scanned for workloads.

## Usage

### 1. **Run the script**:
   After configuring the `config.json` file, run the script to scan the EKS workloads and send the results to the specified SQS queue.

   ```bash
   python main.py
   ```

### 2. **Output**:
   The script will log scan results and provide summaries for each scanned image. It will send individual vulnerabilities as messages to the SQS queue.

   Example:
   ```bash
   Summary for image: nginx:latest: Total: 5, High: 2, Critical: 1, Medium: 1, Low: 1
   Message sent to SQS queue my-sqs-queue, MessageId: <message-id>
   ```

## Customization

The script can be extended by modifying the enrichment function (`enrich_payload` in `enrich.py`) to add more fields or modify existing ones in the scan payload.

### `enrich.py` Example:
```python
def enrich_payload(scan_payload, account_id, cluster_name, container_name):
    enriched_payload = scan_payload.copy()
    enriched_payload.update({
        "DocumentType": "DOCKER_IMAGE",
        "AccountId": account_id,
        "HostSystemName": cluster_name,
        "HostSystemType": "EKS",
        "SystemName": container_name,
        "DocumentVersion": 1
    })
    return enriched_payload
```

## Logging and Error Handling

The script uses logging to output detailed information, including errors during scanning or message delivery. Failed messages that exceed the SQS size limit are saved as JSON files for later inspection.

- Log files are saved in the format `scan_log_<timestamp>.log` in the project root directory.
- In case of SQS message size issues, the message is saved to a file in the format `failed_message_<timestamp>.json`.

## Troubleshooting

### 1. **Trivy Not Found**:
   If Trivy is not installed or not found in the system’s PATH, you will see the following error:
   ```bash
   Trivy is not installed or not found in PATH. Please install Trivy to proceed.
   ```
   Make sure Trivy is correctly installed and available in your environment.

### 2. **AWS Permission Issues**:
   If your AWS credentials are missing or insufficient, you will encounter AWS ClientError messages. Ensure that your IAM roles and permissions are configured properly.

## Contributing

Feel free to open issues or submit pull requests if you have any improvements or suggestions.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
