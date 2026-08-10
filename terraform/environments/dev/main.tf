terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.58" }
  }
}
provider "aws" { region = var.aws_region }

data "terraform_remote_state" "shared" {
  backend = "local" # or "s3" with a real backend config — see backend.tf
  config  = { path = "../shared/terraform.tfstate" }
}

module "s3" {
  source = "../../modules/s3"
  env    = "dev"
}
module "dynamodb" {
  source = "../../modules/dynamodb"
  env    = "dev"
}
module "sqs" {
  source = "../../modules/sqs"
  env    = "dev"
}

module "iam" {
  source             = "../../modules/iam"
  env                = "dev"
  instance_role_name = "testscope-k8s-worker-role"
  bucket_arn         = module.s3.bucket_arn
  table_arn          = module.dynamodb.table_arn
  queue_arn          = module.sqs.queue_arn
  dlq_arn            = module.sqs.dlq_arn
}

module "monitoring" {
  source      = "../../modules/monitoring"
  env         = "dev"
  alert_email = var.alert_email
}

output "bucket_name" { value = module.s3.bucket_name }
output "table_name" { value = module.dynamodb.table_name }
output "queue_url" { value = module.sqs.queue_url }
# Task 42: plan.md's own literal snippet is `output "dlq_url" { value = module.sqs.dlq_arn }`
# -- confirmed a real bug, not applied as written: the sqs module never exposed a dlq_url
# output (only dlq_arn), and Task 42's own Step 1 command feeds this value to
# `aws sqs send-message --queue-url`, which requires a queue URL, not an ARN. Added a real
# dlq_url output to terraform/modules/sqs/outputs.tf (aws_sqs_queue.dlq.id, same pattern
# queue_url already uses) and reference that here instead.
output "dlq_url" { value = module.sqs.dlq_url }
