output "cluster_id" {
  description = "EKS cluster ID"
  value       = aws_eks_cluster.main.id
}

output "cluster_name" {
  description = "EKS cluster name"
  value       = aws_eks_cluster.main.name
}

output "cluster_endpoint" {
  description = "EKS Kubernetes API endpoint"
  value       = aws_eks_cluster.main.endpoint
}

output "cluster_arn" {
  description = "EKS cluster ARN"
  value       = aws_eks_cluster.main.arn
}

output "cluster_role_arn" {
  description = "EKS cluster IAM role ARN"
  value       = aws_iam_role.cluster.arn
}

output "node_role_arn" {
  description = "EKS node IAM role ARN"
  value       = aws_iam_role.node.arn
}

output "node_group_name" {
  description = "EKS managed node group name"
  value       = aws_eks_node_group.main.node_group_name
}
