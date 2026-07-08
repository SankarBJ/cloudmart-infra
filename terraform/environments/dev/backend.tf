terraform {
  backend "s3" {
    bucket         = "cloudmart-tf-state-sankarb-vit"
    key            = "dev/terraform.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "cloudmart-tf-lock"
    encrypt        = true
  }
}