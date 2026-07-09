output "vpc_id" {
  value = module.networking.vpc_id
}

output "public_subnet_1_id" {
  value = module.networking.public_subnet_1_id
}

output "public_subnet_2_id" {
  value = module.networking.public_subnet_2_id
}

output "iam_role_name" {
  value = module.iam_baseline.iam_role_name
}

output "instance_profile_name" {
  value = module.iam_baseline.instance_profile_name
}