# Default is t3.medium, not the plan's original t3.large — this AWS account has an
# explicit IAM deny policy ("DenyLargeInstanceTypes") blocking ec2:RunInstances for
# anything above {t2,t3,t4g}.{nano,micro,small,medium}. Confirmed live via a failed
# apply + `aws sts decode-authorization-message`, user-approved deviation.
variable "instance_type" {
  type    = string
  default = "t3.medium"
}
variable "public_subnet_id" { type = string }
variable "security_group_id" { type = string }
