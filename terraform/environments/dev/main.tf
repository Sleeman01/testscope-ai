terraform { required_version = ">= 1.5" }
provider "aws" { region = var.aws_region }

data "terraform_remote_state" "shared" {
  backend = "local"  # or "s3" with a real backend config — see backend.tf
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
  source              = "../../modules/iam"
  env                 = "dev"
  instance_role_name  = "testscope-k8s-worker-role"
  bucket_arn          = module.s3.bucket_arn
  table_arn           = module.dynamodb.table_arn
  queue_arn           = module.sqs.queue_arn
  dlq_arn             = module.sqs.dlq_arn
}

module "monitoring" {
  source      = "../../modules/monitoring"
  env         = "dev"
  alert_email = var.alert_email
}

output "bucket_name" { value = module.s3.bucket_name }
output "table_name" { value = module.dynamodb.table_name }
output "queue_url" { value = module.sqs.queue_url }
