# ADR 003: Private versioned S3 state with dual locking

Status: accepted for implementation.

Local state would make CI and owner recovery disagree about deployed resources. Use a private, TLS-only, SSE-S3-encrypted and versioned bucket with distinct state/bootstrap/dev/prod keys. Keep email, account information and state out of source control.

Workload backends use S3 lock files plus the requested DynamoDB lock table. DynamoDB locking is deprecated upstream; retaining S3 locking provides a migration path. Pin the Terraform minor version and reassess before upgrading. Bootstrap uses only S3 locking so it can destroy the shared table safely.

The owner creates the state bucket with initially local state, then migrates its own state to the same bucket. `make destroy` removes workloads and bootstrap but retains the bucket and its controls. Retained versions aid recovery but may incur storage cost; strict zero requires a separate, deliberate owner cleanup.

Reference: [HashiCorp S3 backend and locking](https://developer.hashicorp.com/terraform/language/backend/s3).
