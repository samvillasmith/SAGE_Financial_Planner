variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "sagemaker_endpoint_name" {
  description = "Name of the SageMaker endpoint from Part 2"
  type        = string
}

variable "aurora_cluster_arn" {
  description = "ARN of the Aurora cluster from Part 5"
  type        = string
}

variable "aurora_secret_arn" {
  description = "ARN of the Aurora secrets from Part 5"
  type        = string
}

variable "aurora_database" {
  description = "Name of the Aurora database"
  type        = string
  default     = "sage"
}