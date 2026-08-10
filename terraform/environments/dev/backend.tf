# State is local by default (Terraform's implicit backend when no `backend` block
# is configured) — same convention as `environments/shared`. This file is the reserved
# location for a `backend "s3"` block if remote state is adopted later; none is
# configured yet.
