# ADR 001: Lambda container behind an HTTP API

Status: accepted for implementation; live cost validation pending.

A portfolio API has little traffic and no need for a continuously running worker. Lambda container images reuse a container build without paying for idle tasks. HTTP API supplies HTTPS without an always-on load balancer. DynamoDB avoids a continuously running database.

Fargate is useful for long-running processes but adds task runtime charges. EKS adds a paid control plane and worker capacity that the target budget cannot justify. Neither variant is included in this initial scope.

Consequences: cold starts, Lambda quotas and short request lifetimes apply. In-memory metrics are per execution environment. A future Fargate comparison must use a separate root/workspace, explicit time limit and teardown instructions.
