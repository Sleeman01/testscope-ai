variable "aws_region" { type = string }
variable "admin_cidr" {
  type        = string
  description = "Your IP in CIDR form, e.g. 203.0.113.4/32"
}
