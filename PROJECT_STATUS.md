# CloudMart Project Status

**Audit date:** 2026-10-07
**Repository:** `https://github.com/SankarBJ/cloudmart-infra.git` (`main` @ `ef6c474`)
**Live region:** `ap-south-1`
**Live cluster:** `cloudmart-dev-eks`
**This document does not include secrets, passwords, kubeconfig contents, or AWS keys.**

No infrastructure was created, modified, or destroyed during this audit. `terraform destroy` was not run.

---

## Verification of the current working deployment

Live HTTP checks against the existing Classic Load Balancer succeeded:

| Check | Result |
| --- | --- |
| `GET /` (frontend) | HTTP 200 |
| `GET /api/health` | `{"service":"cloudmart-backend","status":"healthy"}` |
| `GET /api/products` | 4 products returned from PostgreSQL |

Kubernetes (`cloudmart` namespace):

| Resource | Status |
| --- | --- |
| `deployment/frontend` | 1/1 Running, image `cloudmart-frontend:latest` in ECR |
| `deployment/backend` | 1/1 Running, image `cloudmart-backend:latest` in ECR |
| `deployment/postgres` | 1/1 Running, `postgres:16-alpine` |
| `service/frontend` | `LoadBalancer` (Classic ELB, port 80) |
| `service/backend` | ClusterIP 5000 |
| `service/db` | ClusterIP 5432 |
| `secret/db-secret` | Present (values not exported) |
| `configmap/db-init` | Present |

Preserve this deployment. Do not rebuild it unless a replacement has been validated.

---

## A. CURRENT IMPLEMENTED FEATURES

### Application

- Static CloudMart UI (HTML/CSS/JS, not a React SPA) served by Nginx
- Nginx reverse-proxy of `/api/` to the backend
- Flask backend with `/api/health` and `/api/products`
- PostgreSQL schema and seed data in `app/database/init.sql`
- Dockerfiles for frontend and backend
- Local `app/docker-compose.yml` three-tier stack

### Infrastructure (live in AWS, represented in local Terraform state)

- VPC `10.0.0.0/16` with 2 public + 2 private subnets across `ap-south-1a` / `ap-south-1b`
- Internet Gateway, NAT Gateway (1 AZ), public/private route tables
- IAM baseline (EC2 role, instance profile, admin group, readonly policy)
- Milestone EC2 web server (`t2.micro`) still present
- EKS cluster `cloudmart-dev-eks` (Kubernetes 1.33) with 1 managed node (`t3.medium`) in private subnets
- ECR repositories: `cloudmart-frontend`, `cloudmart-backend`
- Classic ELB in front of the frontend Service

### Kubernetes

- Namespace `cloudmart`
- Backend Deployment/Service with DB credentials from `db-secret` and HTTP probes
- Postgres Deployment/Service with init ConfigMap and `emptyDir` data
- Frontend Deployment/Service (live, **not yet in Git**)

### Remote state (partial)

- Bootstrap module exists for S3 + DynamoDB locking
- `terraform/environments/dev/backend.tf` points at `cloudmart-tf-state-sankarb-vit` / `cloudmart-tf-lock`
- The **live** stack is `terraform/environments/dev-new` using **local** `terraform.tfstate`

---

## B. PARTIALLY IMPLEMENTED FEATURES

| Item | What exists | What is incomplete |
| --- | --- | --- |
| Terraform environments | `dev`, `dev-new`, empty `prod` | Split-brain: live EKS is only in `dev-new` local state; `dev` has S3 backend but no EKS; `prod` files are empty |
| EKS module | Local untracked `terraform/modules/eks` + uncommitted `module "eks"` in `dev-new/main.tf` | Not on `origin/main`; missing cluster logging, encryption, addons, public subnet tags for load balancers, EKS outputs on the env |
| Kubernetes manifests | `namespace.yaml`, `postgres.yaml`, `backend.yaml` (untracked) | Frontend Service/Deployment not in repo; no Helm; no resource requests/limits; no HPA/PDB; no Ingress |
| Secrets | K8s `db-secret` used correctly by backend/postgres | Compose still has a hardcoded password; no AWS Secrets Manager; secret not created from Git-safe workflow |
| PostgreSQL | Working in-cluster Postgres | Not RDS Multi-AZ; `emptyDir` (data lost on pod recreate) |
| IAM | EC2/EKS cluster+node roles | No GitHub OIDC; SSH SG `0.0.0.0/0`; no ALB controller IRSA |
| Remote state | Bootstrap module + `dev/backend.tf` | Live env not using remote state; local tfstate on disk |
| Frontend | Working Nginx UI | Not React; no TLS |

---

## C. MISSING FEATURES

Capstone items not present in the repo or cluster:

- Terraform modules: `rds`, `redis`, `s3` (app), `security`, `observability`, `ecr`
- Amazon RDS PostgreSQL Multi-AZ
- ElastiCache Redis
- AWS Secrets Manager
- Helm chart
- AWS Load Balancer Controller + ALB Ingress + ACM HTTPS
- Route 53 (no domain configured)
- GitHub Actions, SAST/SCA, Trivy, Checkov, Gitleaks, Semgrep
- GitHub OIDC federation
- ArgoCD / GitOps
- Prometheus, Grafana, Metrics Server, application `/metrics`
- Falco / runtime security
- Adaptive Multi-Signal Health Orchestrator (CRD + controller)
- Graduated remediation, cooldowns, decision logs
- Fault injection + evaluation harness (MTTR / false-positive)
- Automated tests (`tests/` empty/absent)
- Documentation (`README.md` absent from this clone; `docs/` absent)
- Architecture diagrams in-repo

---

## D. BROKEN / RISKY FEATURES

Not “down”, but structurally wrong or unsafe:

1. **Git vs live drift.** Working EKS module, provider, and k8s YAML are untracked. A clean clone cannot recreate the live cluster definition.
2. **Local Terraform state** for the live environment (`dev-new/terraform.tfstate`). Loss/corruption risk; locking is not in use for this env.
3. **`dev` vs `dev-new`.** Two environments share the same VPC CIDR / resource naming (`environment = "dev"`). Applying `dev` accidentally could conflict with live `dev-new` resources.
4. **Postgres on `emptyDir`.** Database is ephemeral.
5. **Health endpoint does not check the database.** `/api/health` always returns healthy.
6. **No exception handling** on `/api/products` (connection errors become 500s).
7. **EKS subnet tags** (`kubernetes.io/role/elb`, `kubernetes.io/cluster/...`) are missing — ALB/NLB discovery will be unreliable.
8. **Empty `prod` Terraform files** could confuse later applies.
9. **Classic ELB** from `Service type: LoadBalancer` (not ALB Ingress).
10. **kubectl JSONPath** on Windows PowerShell is awkward; operators/scripts should be POSIX or Python for demos.

---

## E. AWS RESOURCES REFERENCED / OBSERVED

| Resource | Name / note | In Terraform state (`dev-new`) | Cost category |
| --- | --- | --- | --- |
| VPC + subnets + IGW + NAT + EIP | environment tag `dev` | Yes | NAT = ongoing $$ |
| EKS control plane | `cloudmart-dev-eks` | Yes | $$ (hourly) |
| EKS node group | 1× `t3.medium` | Yes | $$ |
| EC2 | `t2.micro` Apache milestone box | Yes | $ (small; leftover) |
| ECR | `cloudmart-frontend`, `cloudmart-backend` | **No** (exist in AWS) | $ (storage) |
| Classic ELB | frontend Service | Created by Kubernetes, not Terraform | $ |
| S3/DynamoDB tfstate | named in `dev/backend.tf` | Bootstrap not in `dev-new` state | $ |
| RDS | none | — | — |
| ElastiCache | none | — | — |
| ALB (v2) | none | — | — |

Account ID appears in ECR image URIs in Kubernetes YAML (normal AWS convention; not a secret key).

---

## F. KUBERNETES RESOURCES

**Cluster:** `cloudmart-dev-eks`
**Node:** 1 Ready Amazon Linux 2023 node in `10.0.12.0/24`
**Addons observed:** `coredns`, `aws-node` (VPC CNI), `kube-proxy`
**Not installed:** metrics-server, AWS Load Balancer Controller, ArgoCD, Prometheus, Grafana, Falco

**Namespace `cloudmart`:** frontend, backend, postgres Deployments + Services, `db-secret`, `db-init` ConfigMap.

---

## G. SECURITY RISKS

| Risk | Severity | Notes |
| --- | --- | --- |
| Hardcoded DB password in `docker-compose.yml` | High for Git history | Local-only compose, still committed |
| EC2 SG SSH `0.0.0.0/0` | High | Milestone leftover |
| Local `terraform.tfstate` on disk | High | Can contain sensitive attributes; gitignored but present |
| Secrets only in K8s Secret | Medium | No rotation, no Secrets Manager, no External Secrets |
| No image/IaC/secret scanning in CI | Medium | No `.github/workflows` |
| No runtime security | Medium | No Falco |
| Public EKS API endpoint | Medium | `endpoint_public_access = true` (needed for laptop kubectl) |
| Classic ELB HTTP only | Medium | No TLS |
| Health check ignores DB | Low/Med | Orchestrator cannot trust `/api/health` as-is |
| IAM admin group with no users documented | Low | Unused surface |

No AWS access keys were found hardcoded in application/Terraform source.

---

## H. COST RISKS

**Currently burning (do not delete without approval):**

- EKS control plane
- 1× `t3.medium` node
- NAT Gateway + EIP
- Classic ELB
- leftover `t2.micro` EC2
- ECR storage (small)
- CloudWatch (default EKS/EC2)

**Do not create without explicit approval (approximate academic-project impact in ap-south-1):**

| Resource | Purpose | Cost category | Why required later |
| --- | --- | --- | --- |
| RDS PostgreSQL Multi-AZ | Production data tier | $$$ | Capstone data requirement |
| ElastiCache Redis | Cache / dependency latency signal | $$ | Orchestrator dependency signal |
| Extra NAT Gateway (2nd AZ) | HA NAT | $$ | True Multi-AZ egress HA |
| Additional EKS nodes | Prometheus/Grafana/Falco/operator | $$ | Observability + operator need RAM |
| ALB | HTTPS ingress | $ | Phase 5 |
| Secrets Manager | DB creds | $ | Phase 2/14 |

---

## I. EXACT IMPLEMENTATION PLAN

Work incrementally. Never `terraform destroy`. Stop before expensive applies.

### Recommended order

1. **Freeze Git source of truth** (this sprint): commit-ready k8s manifests including frontend; track EKS module; tighten `.gitignore`; add `PROJECT_STATUS.md`. No AWS changes.
2. **Phase 1 — Terraform completeness (code + plan only):** ECR module with *import* plan; EKS outputs; subnet tags; decide `dev` vs `dev-new`; remote state migration plan. `fmt` / `validate` / `plan`. **Ask before apply / state migration.**
3. **Phase 3 — Application hardening:** DB-aware health, metrics, structured logging, Redis client stub, no extra shop features.
4. **Phase 4 — Helm:** chart matching the live 3-tier app; probes, resources, PDB; secrets by reference.
5. **Phase 6 — CI + OIDC:** GitHub Actions build/test/scan; OIDC role (apply after approval). Push-to-ECR only after OIDC exists.
6. **Phase 10 foundation:** AdaptiveHealthPolicy CRD + operator (Go) with scoring, explainability, cooldowns; start with observe-only remediation.
7. **Phase 8/9 — Observability + Falco:** metrics-server, kube-prometheus-stack, Falco. **Warn: needs more node capacity.**
8. **Phase 7 — ArgoCD GitOps** after Helm values are the deployment API.
9. **Phase 5 — ALB/HTTPS** after ALB controller + optional ACM (ask before domain purchase).
10. **Phase 2 — RDS + ElastiCache** only after cost approval; do not cut over the working app until validated.
11. **Phase 11–13 — Remediation, fault injection, baseline comparison** with measured results only.
12. **Phase 14–17 — Scanning, tests, docs, cost/cleanup runbook.**

### Blockers requiring your approval

- Migrate `dev-new` state from local file to S3 + DynamoDB
- `terraform import` of existing ECR repos
- RDS Multi-AZ, ElastiCache, extra nodes, second NAT, ALB
- Domain / ACM certificate
- Removing leftover EC2 Apache instance (saves a little money; not required for the demo)

### Intentionally deferred until approval

RDS, ElastiCache, HTTPS/ACM, extra HA NAT, cluster size increase.

---

## Definition of Done (current check)

- [x] 3-tier application running on EKS (verified HTTP)
- [x] Multi-AZ VPC + NAT (single NAT)
- [x] EKS + node group (live)
- [x] ECR (live, not in Terraform)
- [x] In-cluster PostgreSQL (not RDS)
- [ ] Terraform fully in Git / remote state for live env
- [ ] Redis / ElastiCache
- [ ] Secrets Manager
- [ ] Helm
- [ ] ALB / HTTPS
- [ ] GitHub Actions + OIDC
- [ ] ArgoCD
- [ ] Prometheus / Grafana / app SLIs
- [ ] Falco
- [ ] AdaptiveHealthPolicy operator
- [ ] Fault injection + measured evaluation
- [ ] Tests + documentation

---

## Next step after this file

Highest-priority missing work that does **not** change AWS: capture the live frontend Kubernetes manifests into the repository, tighten ignore rules for state/secrets, and complete Terraform *code* so Git matches the running EKS stack. No apply.
