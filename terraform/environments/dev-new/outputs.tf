output "instance_id" {
  value = module.compute.instance_id
}

output "public_ip" {
  value = module.compute.public_ip
}

output "private_ip" {
  value = module.compute.private_ip
}

output "security_group_id" {
  value = module.compute.security_group_id
}

output "vpc_id" {
  value = module.networking.vpc_id
}

output "private_subnet_ids" {
  value = [
    module.networking.private_subnet_1_id,
    module.networking.private_subnet_2_id
  ]
}

output "public_subnet_ids" {
  value = [
    module.networking.public_subnet_1_id,
    module.networking.public_subnet_2_id
  ]
}

output "nat_gateway_id" {
  value = module.networking.nat_gateway_id
}

output "eks_cluster_name" {
  value = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  value     = module.eks.cluster_endpoint
  sensitive = true
}

output "eks_node_group_name" {
  value = module.eks.node_group_name
}