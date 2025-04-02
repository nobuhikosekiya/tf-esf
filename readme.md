# S3 to Elasticsearch with Elastic Serverless Forwarder

This Terraform project sets up the necessary AWS infrastructure to collect logs from an S3 bucket using SQS notifications and forwards them to Elasticsearch using the Elastic Serverless Forwarder (ESF).

## Architecture

```
┌─────────────┐    Notification     ┌───────────┐    EventSource    ┌───────────────────┐
│  Existing   │──────────────────▶  │           │◀─────────────────┤                   │
│  S3 Bucket  │                     │  SQS Queue│                  │  Elastic Serverless│
│  (Logs)     │                     │           │                  │  Forwarder (Lambda)│
└─────────────┘                     └───────────┘                  └───────────────────┘
      │                                                                      │
      │                                                                      │
      │                 S3 Object Access                                     │
      └─────────────────────────────────────────────────────────────────────┘
                                                                             │
                                                                             │
                                                                             ▼
                                                             ┌─────────────────────────┐
                                                             │                         │
                                                             │     Elasticsearch       │
                                                             │                         │
                                                             └─────────────────────────┘
```

## Components

- **Existing S3 Bucket**: Stores the logs that need to be processed
- **SQS Queue**: Receives notifications when new files are added to the S3 bucket
- **Lambda Function**: Runs the Elastic Serverless Forwarder to collect logs from S3 via SQS and forward them to Elasticsearch
- **IAM Roles and Policies**: Provides necessary permissions to access AWS resources

## Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform installed (version >= 1.0.0)
- An Elasticsearch deployment with an API key for authentication

## Usage

1. Clone this repository
2. Create a `terraform.tfvars` file based on the provided example
3. Initialize Terraform:
   ```
   terraform init
   ```
4. Apply the Terraform configuration:
   ```
   terraform apply
   ```
5. After resources are created, you can run the test script:
   ```
   python test_s3_logging.py --region <aws-region> --s3-bucket <s3-bucket-name> --sqs-queue-url <sqs-queue-url>
   ```

## Configuration

The key configurations needed in your `terraform.tfvars` file are:

- `elasticsearch_url`: The URL to your Elasticsearch deployment
- `elasticsearch_api_key`: An API key with permissions to write to Elasticsearch
- `esf_release_version`: The version of the Elastic Serverless Forwarder to use (default: "lambda-v1.9.0")

See the `terraform.tfvars.example` file for all available configuration options.

## Testing

The included test script (`test_s3_logging.py`) generates random log files, uploads them to the S3 bucket, and verifies that SQS messages are generated. This helps confirm that the infrastructure is working correctly.

## AWS Permissions

The following permissions are required for the Lambda function to access AWS resources:
- `sqs:DeleteMessage`
- `sqs:GetQueueAttributes`
- `sqs:ReceiveMessage`
- `sqs:ChangeMessageVisibility`
- `s3:GetObject`
- `s3:ListBucket`
- `logs:CreateLogGroup`
- `logs:CreateLogStream`
- `logs:PutLogEvents`

## Cleanup

To destroy all created resources:

```
terraform destroy
```

Note: The ESF configuration S3 bucket is created with `force_destroy = true` to allow clean destruction even if it contains objects. The main logs bucket is not managed by this Terraform configuration.