# EC2 related outputs have been removed

output "sqs_queue_url" {
  description = "The URL of the SQS queue for S3 notifications"
  value       = aws_sqs_queue.s3_notifications.url
}

output "sqs_queue_arn" {
  description = "The ARN of the SQS queue for S3 notifications"
  value       = aws_sqs_queue.s3_notifications.arn
}

output "s3_config_bucket" {
  description = "The name of the S3 bucket used for ESF configuration"
  value       = aws_s3_bucket.esf_config.bucket
}

output "lambda_function_name" {
  description = "The name of the ESF Lambda function"
  value       = aws_lambda_function.esf.function_name
}

output "lambda_function_arn" {
  description = "The ARN of the ESF Lambda function"
  value       = aws_lambda_function.esf.arn
}

output "esf_continuing_queue_url" {
  description = "The URL of the ESF continuing queue"
  value       = aws_sqs_queue.esf_continuing_queue.url
}

output "esf_replay_queue_url" {
  description = "The URL of the ESF replay queue"
  value       = aws_sqs_queue.esf_replay_queue.url
}