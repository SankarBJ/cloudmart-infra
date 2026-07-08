variable "bucket_name" {
  description = "Terraform state bucket name"
  type        = string
}

variable "dynamodb_table" {
  description = "Terraform lock table name"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}