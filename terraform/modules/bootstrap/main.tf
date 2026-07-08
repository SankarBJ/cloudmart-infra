#################################################
# S3 Bucket for Terraform Remote State
#################################################

resource "aws_s3_bucket" "terraform_state" {
  bucket = var.bucket_name

  tags = {
    Name        = "Terraform State"
    Environment = var.environment
    Project     = "CloudMart"
  }
}

#################################################
# Enable Versioning
#################################################

resource "aws_s3_bucket_versioning" "terraform_state" {

  bucket = aws_s3_bucket.terraform_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

#################################################
# Server Side Encryption
#################################################

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {

  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

#################################################
# DynamoDB Table for State Locking
#################################################

resource "aws_dynamodb_table" "terraform_lock" {

  name         = var.dynamodb_table
  billing_mode = "PAY_PER_REQUEST"

  hash_key = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Name        = "Terraform Lock Table"
    Environment = var.environment
    Project     = "CloudMart"
  }
}