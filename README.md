# CloudMart — Cloud-Native E-Commerce Platform

A production-grade, secure, multi-tier cloud e-commerce and logistics platform built with Python Flask, PostgreSQL, Nginx, Docker, Kubernetes (AWS EKS), and Terraform.

## Key Features
- **Amazon-Style Storefront & Catalog**: Parameterized search, department filters, and dynamic price/rating sorting.
- **High-Performance Shopping Cart**: Client-side cart manager with server-side price and stock validation.
- **Authentication & Customer Isolation**: Salted bcrypt password hashing and HMAC-SHA256 JWT tokens.
- **Concurrency-Safe Checkout**: Atomic PostgreSQL transactions with `SELECT ... FOR UPDATE` row locks and idempotency protection.
- **Warehouse Tracking & Delivery OTP**: 5-stage logistics tracking, automated SMS alerts, and doorstep 6-digit OTP verification.

## Quickstart (Local Development)
1. Start the complete stack:
   cd app
   docker compose up -d --build
2. Access the applications:
   - Storefront UI: http://localhost:8080
   - Health Check: http://localhost:8080/health
   - Products API: http://localhost:8080/api/products

## Automated Test Verification
Run the 8-stage integration test suite:
   python tests/verify_all.py

## Kubernetes & Cloud Deployment
- **Persistent Storage**: AWS EBS gp3 10Gi PersistentVolumeClaim in `k8s/postgres.yaml`.
- **AWS ALB Ingress**: Internet-facing load balancer routing in `k8s/ingress.yaml`.
- **Infrastructure as Code**: Modular Terraform modules in `terraform/modules/` for VPC, EKS, IAM, and ECR.
