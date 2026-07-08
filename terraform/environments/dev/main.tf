module "bootstrap" {
  source = "../../modules/bootstrap"

  bucket_name    = "cloudmart-tf-state-sankarb-vit"
  dynamodb_table = "cloudmart-tf-lock"

  environment = "dev"
}
module "networking" {
  source = "../../modules/networking"

  vpc_cidr    = "10.0.0.0/16"
  environment = "dev"

  public_subnet_1_cidr = "10.0.1.0/24"
  public_subnet_2_cidr = "10.0.2.0/24"

  private_subnet_1_cidr = "10.0.11.0/24"
  private_subnet_2_cidr = "10.0.12.0/24"

  availability_zone_1 = "ap-south-1a"
  availability_zone_2 = "ap-south-1b"
}