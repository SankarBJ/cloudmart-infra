module "networking" {
  source = "../../modules/networking"

  environment = "dev"

  vpc_cidr              = "10.0.0.0/16"
  public_subnet_1_cidr  = "10.0.1.0/24"
  public_subnet_2_cidr  = "10.0.2.0/24"
  private_subnet_1_cidr = "10.0.11.0/24"
  private_subnet_2_cidr = "10.0.12.0/24"

  availability_zone_1 = "ap-south-1a"
  availability_zone_2 = "ap-south-1b"
}

module "iam_baseline" {
  source = "../../modules/iam-baseline"

  environment = "dev"
}

module "compute" {
  source = "../../modules/compute"

  environment = "dev"

  vpc_id                = module.networking.vpc_id
  subnet_id             = module.networking.public_subnet_1_id
  instance_profile_name = module.iam_baseline.instance_profile_name

  instance_type = "t2.micro"
  ami_id        = "ami-0f58b397bc5c1f2e8"
}