terraform {
  required_version = ">= 1.5"
  required_providers {
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
