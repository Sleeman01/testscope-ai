variable "instance_type" {
  type    = string
  default = "t3.large"
}
variable "public_subnet_id" { type = string }
variable "security_group_id" { type = string }
