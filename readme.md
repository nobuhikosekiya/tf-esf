# S3 to Elasticsearch with Elastic Serverless Forwarder

This Terraform project sets up AWS infrastructure to collect logs from an S3 bucket using SQS notifications and forwards them to Elasticsearch using the Elastic Serverless Forwarder (ESF).

## Architecture

```
┌─────────────┐    Notification     ┌───────────┐    EventSource    ┌───────────────────┐
│  New S3     │──────────────────▶  │           │◀─────────────────┤                   │
│  Bucket     │                     │  SQS Queue│                  │  Elastic Serverless│
│  (Logs)     │                     │           │                  │  Forwarder (Lambda)│
└─────────────┘                     └───────────┘                  └───────────────────┘
      │                                                                      │
      │                 S3 Object Access                                     │
      │   ┌─────────────────────────────────────────────────────────────────┘
      │   │                                                                  │
      ▼   ▼                                                                  ▼
┌─────────────────────────┐                                 ┌─────────────────────────┐
│   S3 Bucket Structure   │                                 │                         │
│                         │                                 │     Elasticsearch       │
│ /json-logs/            │                                 │                         │
│ /plain-logs/           │                                 └─────────────────────────┘
│ /ndjson-logs/          │
│ /csv-logs/             │
└─────────────────────────┘
```

## Components

- **S3 Bucket**: Automatically created to store logs with organized folder structure
- **SQS Queue**: Receives notifications when new files are added to the S3 bucket
- **Lambda Function**: Runs the Elastic Serverless Forwarder to process logs and forward to Elasticsearch
- **IAM Roles and Policies**: Provides necessary permissions to access AWS resources

## Supported Data Types

This setup supports multiple log formats with organized storage:

### 📁 **Folder Structure**
- `/json-logs/` - JSON formatted application logs
- `/plain-logs/` - Plain text logs (Apache/Nginx style)
- `/ndjson-logs/` - Newline-delimited JSON logs
- `/csv-logs/` - CSV formatted metrics and data

### 📋 **Data Format Examples**

**JSON Logs** (`/json-logs/`)
```json
{
  "@timestamp": "2025-01-15T10:30:00Z",
  "level": "INFO",
  "message": "User authentication successful",
  "user_id": "user123"
}
```

**Plain Text Logs** (`/plain-logs/`)
```
192.168.1.100 - - [15/Jan/2025:10:30:00 +0000] "GET /api/users HTTP/1.1" 200 1234
```

**NDJSON Logs** (`/ndjson-logs/`)
```
{"@timestamp": "2025-01-15T10:30:00Z", "level": "INFO", "service": "api-gateway"}
{"@timestamp": "2025-01-15T10:30:01Z", "level": "WARN", "service": "user-service"}
```

**CSV Logs** (`/csv-logs/`)
```csv
timestamp,level,service,message,user_id,response_time_ms
2025-01-15 10:30:00,INFO,web-server,Request completed,user123,150
```

## Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform installed (version >= 1.0.0)
- An Elasticsearch deployment with an API key for authentication

## Usage

### 1. Configure

Create a `terraform.tfvars` file:

```hcl
aws_region = "ap-northeast-1"
aws_profile = "default"
prefix = "myproject"

s3_bucket_prefix = "my-logs-bucket"
sqs_queue_name = "s3-notifications-queue"

elasticsearch_url = "https://your-elasticsearch-instance.example.com:9243"
elasticsearch_api_key = "your_api_key"
elasticsearch_datastream = "logs-aws.s3-default"

default_tags = {
  Environment = "production"
  Project     = "log-collection"
}
```

### 2. Deploy

```bash
terraform init
terraform plan
terraform apply
```

### 3. Test

```bash
pip install -r requirements.txt

python test_s3_logging.py \
  --region ap-northeast-1 \
  --s3-bucket $(terraform output -raw logs_s3_bucket_name) \
  --lambda-function $(terraform output -raw lambda_function_name) \
  --elasticsearch-url "https://your-elasticsearch.com:9243" \
  --elasticsearch-api-key "your-api-key"
```

**Expected Result**: The test will upload sample files to S3, wait for processing, and verify that data appears in Elasticsearch within 120 seconds.

## Configuration Variables

### Required
| Variable | Description |
|----------|-------------|
| `prefix` | Prefix for all resource names |
| `s3_bucket_prefix` | Prefix for S3 bucket name |
| `elasticsearch_url` | Your Elasticsearch endpoint |
| `elasticsearch_api_key` | API key for Elasticsearch |

### Optional
| Variable | Default | Description |
|----------|---------|-------------|
| `aws_region` | `"ap-northeast-1"` | AWS region for deployment |
| `aws_profile` | `"default"` | AWS profile to use |
| `sqs_queue_name` | Required | Name for SQS notification queue |
| `lambda_log_level` | `"INFO"` | Log level for Lambda function |
| `elasticsearch_datastream` | `"logs-aws.s3-default"` | Target datastream name |

## AWS Permissions

The Lambda function requires these permissions:
- `s3:GetObject`, `s3:ListBucket`
- `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:GetQueueAttributes`, `sqs:ChangeMessageVisibility`
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

## Troubleshooting

### Common Issues

**Permission Errors**
```bash
aws sts get-caller-identity  # Check AWS credentials
export AWS_PROFILE=your-profile-name
```

**Lambda Function Errors**
```bash
aws logs filter-log-events --log-group-name "/aws/lambda/your-function-name"
```

**Elasticsearch Connection**
```bash
curl -H "Authorization: ApiKey your-api-key" "https://your-elasticsearch-url/_cluster/health"
```

## Cleanup

```bash
terraform destroy
```

Both S3 buckets are created with `force_destroy = true` for easy cleanup.