variable "aws_region" {
  description = "AWS Region"
  type        = string
  default     = "ap-northeast-1"
}

variable "aws_profile" {
  description = "AWS Profile to use for credentials"
  type        = string
  default     = "default"
}

variable "prefix" {
  description = "Prefix for all resources"
  type        = string
}

# EC2 related variables have been removed

# variable "s3_bucket_prefix" {
#   description = "Prefix for S3 bucket name that will store logs"
#   type        = string
# }

variable "s3_bucket_prefix" {
  description = "Prefix for S3 bucket name that will store logs"
  type        = string
}

# variable "existing_s3_bucket_name" {
#   description = "Name of the existing S3 bucket that stores logs to be collected"
#   type        = string
# }

variable "sqs_queue_name" {
  description = "Name of the SQS queue that will receive S3 notifications"
  type        = string
}

variable "lambda_log_level" {
  description = "Log level for the ESF Lambda function"
  type        = string
  default     = "INFO"
}

variable "default_tags" {
  description = "Default tags to apply to all resources"
  type        = map(string)
  default     = {
    Environment = "dev"
    Terraform   = "true"
  }
}

variable "esf_release_version" {
  description = "ESF release version to use"
  type        = string
  default     = "lambda-v1.9.0"
}

variable "elasticsearch_url" {
  description = "URL of the Elasticsearch instance"
  type        = string
}

variable "elasticsearch_api_key" {
  description = "API key for Elasticsearch authentication"
  type        = string
  sensitive   = true
  default     = null
}

variable "elasticsearch_username" {
  description = "Username for Elasticsearch authentication"
  type        = string
  default     = null
}

variable "elasticsearch_password" {
  description = "Password for Elasticsearch authentication"
  type        = string
  sensitive   = true
  default     = null
}

variable "elasticsearch_datastream" {
  description = "Name of the Elasticsearch datastream"
  type        = string
  default     = "logs-aws.s3-default"
}