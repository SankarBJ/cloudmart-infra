variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
}

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.33"
}

variable "vpc_id" {
  description = "VPC ID for the EKS cluster"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for EKS"
  type        = list(string)
}

variable "node_instance_types" {
  description = "EC2 instance types for EKS managed nodes"
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_desired_size" {
  description = "Desired number of EKS nodes"
  type        = number
  default     = 1
}

variable "node_min_size" {
  description = "Minimum number of EKS nodes"
  type        = number
  default     = 1
}

variable "node_max_size" {
  description = "Maximum number of EKS nodes"
  type        = number
  default     = 2
}
