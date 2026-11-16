# Cost target and actual-cost evidence

**Actual monthly cost: pending. No Cost Explorer screenshot has been captured.** The owner must record the reporting period, region, usage, gross service cost, credits and net billed cost. A partially elapsed month is month-to-date, not an actual full monthly cost.

The verified dev preview ran in `ap-southeast-2` on the new AWS Free experience with finite credits. No billing-plan upgrade was performed. This proves deployment, not permanent free hosting. Only dev was deployed; prod was not deployed. The owner requested full cleanup after verification. The workload destroy passed, and the state bucket and all versions were also deleted after private current-state backups. [Teardown evidence](evidence/teardown.json) records resource checks; it does not establish a final invoice amount. See the [live evidence](evidence.md).

The running target is below about US$2/month for very light demo traffic **when the account has enough applicable free allowance**. AWS eligibility and credits vary by account creation date and other account usage. Verify them in Billing before deploying. Without dashboard free allowance, this design can exceed the target even with no traffic: run it for a short recorded demo, then destroy it.

## Planning assumptions (estimates, not observed usage)

| Input | Assumption / cost implication |
|---|---|
| Region | The live preview uses `ap-southeast-2`; check the selected project's regional prices. |
| Traffic | At most 1,000 requests per environment per month for planning. A public endpoint does not enforce this limit. |
| Lambda | At 128 MiB and assumed average 100 ms, 2,000 requests use 25 GB-seconds; expected within eligible free allowance. Cold starts increase actual duration. |
| ECR | Keep total stored compressed image layers around 1 GB or less. At the illustrative US$0.10/GB-month rate, that is around US$0.10/month before credits. Immutable tags accumulate; inspect stored bytes and remove old unused images or destroy after demos. |
| DynamoDB | On-demand request/storage charges and point-in-time recovery depend on actual data. Small synthetic items and TTL reduce retained volume; on-demand requests are not the provisioned-capacity free offer. |
| CloudWatch | Each environment has a dashboard with 3 metrics and 2 alarms. The rate alarm evaluates 2 underlying metrics, so account for metric-based alarm pricing. Existing account use can exhaust free dashboards/alarms/log allowance. |
| Logs | Application and API access logs retain 3 days. Retention limits storage, not ingestion charges under abuse. |
| State | S3 requests, current/old versions and dual lock requests can incur small charges. Old state versions expire after 30 days. Retained state remains after teardown. |
| SNS / Budgets | Notifications are infrequent; check current email delivery and budgets pricing. Budget emails trigger at actual spend thresholds of US$1 and US$5, with reporting delay. |

These are inputs for an estimate, not a guarantee. There is no NAT gateway, EKS, load balancer, dedicated customer-managed key or always-on container. Both demo environments should be destroyed when unused.

## Guardrails and failure limits

Provider default tags set Project, Environment, Owner and ManagedBy on taggable resources. Relationships such as IAM inline policies and API routes do not support tags. The account-wide budget includes charges that cannot be attributed by those tags. State storage is deliberately included in that guard.

API throttling reduces burst exposure; Lambda uses shared concurrency by default because small quotas may not support a reservation. Sustained public traffic can still exceed US$2. AWS Budgets alerts **do not stop resources**. Neither an email alert nor TTL is a cost cap. Remove the endpoint and destroy the stack if usage is unexpected.

`make destroy` removes the application, bootstrap, images, logs, dashboards and budget; it retains the state bucket and its state data. A non-empty retained bucket prevents an unconditional $0-footprint claim. See [teardown verification](runbook.md#destroy-and-verify) for strict-zero owner cleanup.

## Owner screenshot checklist

- Cost Explorer service breakdown, reporting period and currency visible; note whether costs are amortised or unblended.
- Include credits/refunds separately so they do not disguise gross usage.
- Redact account IDs, account names, email, account-bearing resource URLs and private data.
- Save the actual screenshot under `docs/evidence/` and link it here. Include a second billing check after teardown and the reporting delay.
- Mark zero usage, missing data or credits honestly. Do not substitute an estimate or a blank console for actual spend evidence.

Pricing references, checked during implementation: [Lambda](https://aws.amazon.com/lambda/pricing/), [API Gateway](https://aws.amazon.com/api-gateway/pricing/), [ECR](https://aws.amazon.com/ecr/pricing/), [CloudWatch](https://aws.amazon.com/cloudwatch/pricing/), [DynamoDB](https://aws.amazon.com/dynamodb/pricing/on-demand/), [S3](https://aws.amazon.com/s3/pricing/), [Budgets](https://aws.amazon.com/aws-cost-management/aws-budgets/pricing/). Recheck the account-specific prices before applying.
