# State is local by default (Terraform's implicit backend when no `backend` block
# is configured) — Tasks 30/31's `dev`/`prod` environments read this root's state via
# `terraform_remote_state` with `backend = "local"`, pointed at
# `../shared/terraform.tfstate`. This file is the reserved location for a `backend "s3"`
# block if remote state is adopted later; none is configured yet.
