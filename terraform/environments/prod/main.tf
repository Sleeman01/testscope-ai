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
  env    = "prod"
}
module "dynamodb" {
  source = "../../modules/dynamodb"
  env    = "prod"
}
module "sqs" {
  source = "../../modules/sqs"
  env    = "prod"
}

module "iam" {
  source             = "../../modules/iam"
  env                = "prod"
  instance_role_name = "testscope-k8s-worker-role"
  bucket_arn         = module.s3.bucket_arn
  table_arn          = module.dynamodb.table_arn
  queue_arn          = module.sqs.queue_arn
  dlq_arn            = module.sqs.dlq_arn
}

module "monitoring" {
  source      = "../../modules/monitoring"
  env         = "prod"
  alert_email = var.alert_email
}

output "bucket_name" { value = module.s3.bucket_name }
output "table_name" { value = module.dynamodb.table_name }
output "queue_url" { value = module.sqs.queue_url }
# Task 42: same dlq_url fix as environments/dev/main.tf -- see that file's comment.
output "dlq_url" { value = module.sqs.dlq_url }
