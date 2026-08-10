# terraform/

## Apply order (real AWS resources — confirm account, region, and budget first)

1. `cd terraform/environments/shared && terraform init && terraform apply` — provisions the VPC and the two-node kubeadm cluster (control-plane + worker), including a generated SSH key pair (written to `testscope-k8s-keypair.pem` in this directory, gitignored — no pre-existing AWS key pair needed). Requires `-var="admin_cidr=<your-ip>/32"` (no default — your own public IP in CIDR form; SSH and the Kubernetes API are restricted to it). Note **both** `control_plane_public_ip` and `worker_public_ip` from the output — they're different IPs and both are needed, don't assume the control-plane's IP works for anything ingress-related. Run Task 28's cluster-convergence check (`kubectl get nodes` via SSH) before moving on to step 2.
2. **Point `dev.testscope.local` and `testscope.local` at the WORKER, not the control-plane.** Ingress runs with `hostNetwork: true` on the worker node specifically — the control-plane never serves application traffic (§9). Add `/etc/hosts` entries (or real DNS records, if you have a domain) mapping both hostnames to `worker_public_ip`. If you're only accessing the demo from your own machine, an `/etc/hosts` entry is enough:
   ```
   <worker_public_ip>  dev.testscope.local testscope.local
   ```
   The self-hosted CI runner (Task 37/38) also needs to resolve these — but since it lives *on* the control-plane EC2 instance, same-VPC, its `/etc/hosts` should point at `worker_private_ip` instead (skips the public internet round-trip; the security group already allows this over the shared cluster security group's self-referencing rule). Add this to the control-plane's `/etc/hosts` as part of runner registration (Task 37's manual setup step).
3. `cd terraform/environments/dev && terraform init && terraform apply` — provisions dev's S3 bucket, DynamoDB table, SQS queues, IAM policy, CloudWatch alarms. Requires `-var="alert_email=<your-email>"` (no default — the SNS topic subscription needs a real address to send the confirmation email to).
4. `cd terraform/environments/prod && terraform init && terraform apply` — same, for prod.
5. Copy each environment's `bucket_name`/`table_name`/`queue_url` outputs into the matching Kubernetes ConfigMap (`kubernetes/dev/configmap.yaml` / `kubernetes/prod/configmap.yaml`, Task 35) — this hand-off is manual by design (Terraform provisions AWS resources; it does not template Kubernetes manifests).
6. Tear-down order is the reverse: `prod` → `dev` → `shared` (`terraform destroy` in each), since `dev`/`prod` reference the shared worker instance role by name.

## Known account-specific constraints (found during Task 28, real and reproducible — not this project's own config)

The AWS account this was built and verified against has two IAM guardrail policies and one scheduled auto-stop Lambda. These aren't part of this Terraform config (they live at the account level) but will affect any real `apply` run against the same account:

- **`DenyLargeInstanceTypes`** — blocks `ec2:RunInstances` for anything above `{t2,t3,t4g}.{nano,micro,small,medium}`. `modules/ec2`'s `instance_type` default is therefore `t3.medium`, not a larger type — override via `-var="instance_type=..."` only if the target account's guardrails allow it.
- **`LimitVolumeSize`** — blocks any EBS volume over 30GB. Both instances' `root_block_device.volume_size` is `30`, not larger — same caveat.
- **A scheduled Lambda (`aws-learning-budget-keeper-function`, EventBridge cron `0 13,21 * * ? *` — 13:00 and 21:00 UTC daily in this account) stops all running EC2 instances** at those times regardless of how recently they launched. `shared`'s `apply` takes roughly 3–4 minutes wall-clock to reach a fully-converged cluster (control-plane + worker `Ready`, Calico/ingress-nginx/metrics-server all `Running`) — time any real `apply` to land with comfortable margin before the next stop window, not right up against it. A stopped-mid-bootstrap instance does **not** self-heal on restart: cloud-init's `runcmd` only runs once per instance-id, so a stop/start cycle leaves the kubeadm bootstrap permanently half-finished. If this happens, `terraform destroy` and re-`apply` fresh rather than trying to restart the existing instances.

If applying against a different AWS account, none of the above may apply — but if `apply` fails with an `UnauthorizedOperation`/explicit-deny error, decode it with `aws sts decode-authorization-message` before assuming it's a bug in this config; it may be an equivalent guardrail on the new account.

## Provider versions

`hashicorp/aws` is pinned to `~> 6.58` (added in Task 31) in each environment root's `required_providers` block — matches the version resolved and tested consistently across every `init` run during Phase 6. `random`/`tls`/`local` (declared in `environments/shared` only, where they're actually used) are pinned to `~> 3.6`/`~> 4.0`/`~> 2.5` respectively, per the plan's original text.

## `dev`/`prod` and `environments/shared`'s state — intentionally decoupled

`dev`/`prod`'s `iam` module attaches its policy to `environments/shared`'s worker IAM role **by a hardcoded name literal** (`testscope-k8s-worker-role`), not by reading `shared`'s state file via `terraform_remote_state`. This is deliberate (see `docs/2026-07-30-testscope-ai-design.md` §9): it keeps each environment's `apply`/`destroy` independent of the others' state being present/readable, at the cost of the role name being a convention both sides have to agree on rather than something Terraform enforces structurally. `data "terraform_remote_state" "shared"` is still declared in `dev`/`prod`'s `main.tf` (reserved for future use) but nothing currently reads its outputs.
