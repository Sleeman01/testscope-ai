terraform {
  required_version = ">= 1.5"
  required_providers {
    aws    = { source = "hashicorp/aws", version = "~> 6.58" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
    tls    = { source = "hashicorp/tls", version = "~> 4.0" }
    local  = { source = "hashicorp/local", version = "~> 2.5" }
  }
}
provider "aws" { region = var.aws_region }

module "networking" {
  source     = "../../modules/networking"
  aws_region = var.aws_region
  admin_cidr = var.admin_cidr
}

module "ec2" {
  source            = "../../modules/ec2"
  public_subnet_id  = module.networking.public_subnet_id
  security_group_id = module.networking.security_group_id
}

output "control_plane_public_ip" { value = module.ec2.control_plane_public_ip }
output "worker_public_ip" { value = module.ec2.worker_public_ip }
output "worker_iam_role_arn" { value = module.ec2.worker_iam_role_arn }
output "ssh_private_key_path" { value = module.ec2.ssh_private_key_path }
