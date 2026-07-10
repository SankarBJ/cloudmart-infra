########################################
# Security Group
########################################

resource "aws_security_group" "ec2_sg" {
  name        = "${var.environment}-ec2-sg"
  description = "Security group for CloudMart EC2"
  vpc_id      = var.vpc_id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.environment}-ec2-sg"
    Environment = var.environment
    Project     = "CloudMart"
  }
}

########################################
# EC2 Instance
########################################

resource "aws_instance" "web" {
  ami                         = var.ami_id
  instance_type               = var.instance_type
  subnet_id                   = var.subnet_id
  iam_instance_profile        = var.instance_profile_name
  associate_public_ip_address = true

  vpc_security_group_ids = [
    aws_security_group.ec2_sg.id
  ]

  user_data_replace_on_change = true

  user_data = <<-EOF
#!/bin/bash

export DEBIAN_FRONTEND=noninteractive

apt-get update -y
apt-get install -y apache2

systemctl enable apache2
systemctl start apache2

cat > /var/www/html/index.html <<HTML
<!DOCTYPE html>
<html>
<head>
    <title>CloudMart</title>
</head>
<body style="font-family: Arial; text-align:center; margin-top:100px;">
    <h1>🚀 CloudMart Infrastructure</h1>
    <h2>Milestone 5 Completed Successfully!</h2>
    <p>Provisioned automatically using Terraform</p>
    <p>Ubuntu 24.04 + Apache2 + Terraform</p>
</body>
</html>
HTML

systemctl restart apache2
EOF

  tags = {
    Name        = "${var.environment}-cloudmart-ec2"
    Environment = var.environment
    Project     = "CloudMart"
  }
}