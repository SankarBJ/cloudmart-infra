#####################################
# IAM Group
#####################################

resource "aws_iam_group" "admins" {
  name = "${var.environment}-cloudmart-admins"
}

#####################################
# Read Only Policy
#####################################

resource "aws_iam_policy" "readonly" {

  name        = "${var.environment}-readonly-policy"

  description = "Read only policy for CloudMart"

  policy = jsonencode({

    Version = "2012-10-17"

    Statement = [

      {

        Effect = "Allow"

        Action = [

          "ec2:Describe*",
          "s3:List*",
          "s3:Get*"

        ]

        Resource = "*"

      }

    ]

  })

}

#####################################
# EC2 IAM Role
#####################################

resource "aws_iam_role" "ec2_role" {

  name = "${var.environment}-ec2-role"

  assume_role_policy = jsonencode({

    Version = "2012-10-17"

    Statement = [

      {

        Effect = "Allow"

        Principal = {

          Service = "ec2.amazonaws.com"

        }

        Action = "sts:AssumeRole"

      }

    ]

  })

}

#####################################
# Attach Policy
#####################################

resource "aws_iam_role_policy_attachment" "readonly_attach" {

  role       = aws_iam_role.ec2_role.name

  policy_arn = aws_iam_policy.readonly.arn

}

#####################################
# Instance Profile
#####################################

resource "aws_iam_instance_profile" "instance_profile" {

  name = "${var.environment}-instance-profile"

  role = aws_iam_role.ec2_role.name

}