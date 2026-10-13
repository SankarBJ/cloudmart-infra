variable "repository_names" {
  description = "ECR repository names to manage"
  type        = list(string)
}

variable "environment" {
  description = "Environment tag"
  type        = string
}

variable "image_tag_mutability" {
  description = "MUTABLE allows :latest (current CloudMart workflow)"
  type        = string
  default     = "MUTABLE"
}
