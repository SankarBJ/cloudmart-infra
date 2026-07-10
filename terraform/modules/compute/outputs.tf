output "instance_id" {
  description = "EC2 Instance ID"
  value       = aws_instance.web.id
}

output "public_ip" {
  description = "EC2 Public IP"
  value       = aws_instance.web.public_ip
}

output "private_ip" {
  description = "EC2 Private IP"
  value       = aws_instance.web.private_ip
}

output "security_group_id" {
  description = "Security Group ID"
  value       = aws_security_group.ec2_sg.id
}