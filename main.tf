locals {
  config_bucket_name  = "${var.prefix}-esf-config"
  logs_bucket_name    = "${var.s3_bucket_prefix}-${random_string.bucket_suffix.result}"
  dependencies_url    = "http://esf-dependencies.s3.amazonaws.com"
  dependencies_file   = "${var.esf_release_version}.zip"
  lambda_name         = "${var.prefix}-esf-lambda"
  sqs_queue_arn       = aws_sqs_queue.s3_notifications.arn
  logs_bucket_arn     = aws_s3_bucket.logs_bucket.arn
}

# Random string for unique bucket naming
resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}

# Create an S3 bucket for logs
resource "aws_s3_bucket" "logs_bucket" {
  bucket        = local.logs_bucket_name
  force_destroy = true
}

# Create an S3 bucket for ESF configuration
resource "aws_s3_bucket" "esf_config" {
  bucket        = local.config_bucket_name
  force_destroy = true
}

# Create SQS queue for S3 notifications
resource "aws_sqs_queue" "s3_notifications" {
  name                      = var.sqs_queue_name
  visibility_timeout_seconds = 300
  message_retention_seconds = 345600 # 4 days
  sqs_managed_sse_enabled   = true
}

# Create SQS queue policy to allow S3 to send messages
resource "aws_sqs_queue_policy" "s3_notifications" {
  queue_url = aws_sqs_queue.s3_notifications.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
        Action = "sqs:SendMessage"
        Resource = aws_sqs_queue.s3_notifications.arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = local.logs_bucket_arn
          }
        }
      }
    ]
  })
}

# Configure S3 bucket to send notifications to SQS
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.logs_bucket.id

  queue {
    queue_arn = aws_sqs_queue.s3_notifications.arn
    events    = ["s3:ObjectCreated:*"]
  }

  depends_on = [aws_sqs_queue_policy.s3_notifications]
}

# ESF Lambda Configuration

# SQS for ESF continuing queue and replay queue
resource "aws_sqs_queue" "esf_continuing_queue_dlq" {
  name                       = "${local.lambda_name}-continuing-queue-dlq"
  delay_seconds              = 0
  sqs_managed_sse_enabled    = true
  visibility_timeout_seconds = 910
}

resource "aws_sqs_queue_redrive_allow_policy" "esf_continuing_queue_dlq" {
  queue_url = aws_sqs_queue.esf_continuing_queue_dlq.url

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue",
    sourceQueueArns   = [aws_sqs_queue.esf_continuing_queue.arn]
  })
}

resource "aws_sqs_queue" "esf_continuing_queue" {
  name                       = "${local.lambda_name}-continuing-queue"
  delay_seconds              = 0
  sqs_managed_sse_enabled    = true
  visibility_timeout_seconds = 910
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.esf_continuing_queue_dlq.arn
    maxReceiveCount     = 3
  })
}

resource "aws_sqs_queue" "esf_replay_queue_dlq" {
  name                       = "${local.lambda_name}-replay-queue-dlq"
  delay_seconds              = 0
  sqs_managed_sse_enabled    = true
  visibility_timeout_seconds = 910
}

resource "aws_sqs_queue_redrive_allow_policy" "esf_replay_queue_dlq" {
  queue_url = aws_sqs_queue.esf_replay_queue_dlq.url

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue",
    sourceQueueArns   = [aws_sqs_queue.esf_replay_queue.arn]
  })
}

resource "aws_sqs_queue" "esf_replay_queue" {
  name                       = "${local.lambda_name}-replay-queue"
  delay_seconds              = 0
  sqs_managed_sse_enabled    = true
  visibility_timeout_seconds = 910
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.esf_replay_queue_dlq.arn
    maxReceiveCount     = 3
  })
}

# Download ESF dependencies
resource "terraform_data" "curl_dependencies_zip" {
  provisioner "local-exec" {
    command = "curl -L -O ${local.dependencies_url}/${local.dependencies_file}"
  }
}

# Upload ESF config to S3
resource "aws_s3_object" "config_file" {
  bucket  = aws_s3_bucket.esf_config.bucket
  key     = "config.yaml"
  content = yamlencode({
    inputs = [
      {
        id   = aws_sqs_queue.s3_notifications.arn
        type = "s3-sqs"
        outputs = [
          {
            type = "elasticsearch"
            args = merge(
              {
                elasticsearch_url  = var.elasticsearch_url
                es_datastream_name = var.elasticsearch_datastream
              },
              var.elasticsearch_api_key != null ? { api_key = var.elasticsearch_api_key } : {},
              var.elasticsearch_username != null && var.elasticsearch_password != null ? {
                username = var.elasticsearch_username
                password = var.elasticsearch_password
              } : {}
            )
          }
        ]
      }
    ]
  })
}

# Upload ESF dependencies to S3
resource "aws_s3_object" "dependencies_file" {
  bucket = aws_s3_bucket.esf_config.bucket
  key    = local.dependencies_file
  source = local.dependencies_file

  depends_on = [terraform_data.curl_dependencies_zip]
}

# IAM role for ESF Lambda
resource "aws_iam_role" "esf_lambda" {
  name = "${local.lambda_name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM policy for ESF Lambda
resource "aws_iam_policy" "esf_lambda" {
  name        = "${local.lambda_name}-policy"
  description = "IAM policy for ESF Lambda"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = [
          "${aws_s3_bucket.esf_config.arn}/config.yaml",
          "${aws_s3_bucket.esf_config.arn}/${local.dependencies_file}",
          "${local.logs_bucket_arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = [
          local.logs_bucket_arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:ChangeMessageVisibility"
        ]
        Resource = [
          aws_sqs_queue.s3_notifications.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = [
          aws_sqs_queue.esf_continuing_queue.arn,
          aws_sqs_queue.esf_replay_queue.arn
        ]
      }
    ]
  })
}

# Attach ESF Lambda policy to role
resource "aws_iam_role_policy_attachment" "esf_lambda" {
  role       = aws_iam_role.esf_lambda.name
  policy_arn = aws_iam_policy.esf_lambda.arn
}

# Create ESF Lambda function
resource "aws_lambda_function" "esf" {
  function_name = local.lambda_name
  role          = aws_iam_role.esf_lambda.arn
  handler       = "main_aws.lambda_handler"
  runtime       = "python3.9"
  timeout       = 300
  memory_size   = 512

  s3_bucket = aws_s3_bucket.esf_config.bucket
  s3_key    = local.dependencies_file

  environment {
    variables = {
      S3_CONFIG_FILE  = "s3://${aws_s3_bucket.esf_config.bucket}/config.yaml"
      SQS_CONTINUE_URL = aws_sqs_queue.esf_continuing_queue.url
      SQS_REPLAY_URL   = aws_sqs_queue.esf_replay_queue.url
      LOG_LEVEL        = var.lambda_log_level
    }
  }

  depends_on = [
    aws_s3_object.dependencies_file,
    aws_s3_object.config_file
  ]
}

# Create Lambda event source mapping for SQS
resource "aws_lambda_event_source_mapping" "esf_s3_sqs" {
  event_source_arn = aws_sqs_queue.s3_notifications.arn
  function_name    = aws_lambda_function.esf.arn
  batch_size       = 10
  enabled          = true

  depends_on = [
    aws_lambda_function.esf,
    aws_s3_object.config_file
  ]
}

# Create Lambda event source mapping for continuing queue
resource "aws_lambda_event_source_mapping" "esf_continuing_queue" {
  event_source_arn = aws_sqs_queue.esf_continuing_queue.arn
  function_name    = aws_lambda_function.esf.arn
  batch_size       = 10
  enabled          = true

  depends_on = [
    aws_lambda_function.esf
  ]
}