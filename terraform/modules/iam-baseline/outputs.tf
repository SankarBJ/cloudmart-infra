output "iam_role_name" {

  value = aws_iam_role.ec2_role.name

}

output "instance_profile_name" {

  value = aws_iam_instance_profile.instance_profile.name

}