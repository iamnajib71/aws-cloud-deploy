# ADR 002: GitHub OIDC instead of stored AWS keys

Status: accepted for implementation; live trust validation pending.

Delivery needs AWS access for a short workflow lifetime. Long-lived user keys would need storage, rotation and revocation. GitHub OIDC provides an auditable short-lived session without repository AWS access keys.

Trust uses exact audience/repository/environment subjects, separate plan/dev/prod roles and protected production approval. Runtime and delivery roles are separate. Environment branch restrictions are required because the OIDC environment subject contains no branch name.

Consequences: the owner must run the first bootstrap and configure GitHub environment protection. Trusted PR Terraform can access the read-only plan role and dev state. Forks receive no cloud plan credentials. Scope limitations are recorded in `docs/security.md`.
