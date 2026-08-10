data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

resource "aws_iam_role" "worker" {
  name = "testscope-k8s-worker-role"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Action = "sts:AssumeRole", Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" } }]
  })
}

resource "aws_iam_instance_profile" "worker" {
  name = "testscope-k8s-worker-profile"
  role = aws_iam_role.worker.name
}

# Generated entirely by Terraform — no "create a key pair in the console first" step.
resource "tls_private_key" "ssh" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "cluster" {
  key_name   = "testscope-k8s-keypair"
  public_key = tls_private_key.ssh.public_key_openssh
}

resource "local_sensitive_file" "ssh_private_key" {
  content         = tls_private_key.ssh.private_key_pem
  filename        = "${path.root}/testscope-k8s-keypair.pem"
  file_permission = "0600"
}

# kubeadm bootstrap token, format [a-z0-9]{6}.[a-z0-9]{16} — generated once so both
# instances' cloud-init can agree on it without an out-of-band handoff step.
resource "random_string" "kubeadm_token_id" {
  length  = 6
  special = false
  upper   = false
}

resource "random_string" "kubeadm_token_secret" {
  length  = 16
  special = false
  upper   = false
}

locals {
  kubeadm_token = "${random_string.kubeadm_token_id.result}.${random_string.kubeadm_token_secret.result}"
}

resource "aws_instance" "control_plane" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  subnet_id              = var.public_subnet_id
  vpc_security_group_ids = [var.security_group_id]
  key_name               = aws_key_pair.cluster.key_name
  user_data = templatefile("${path.module}/cloud-init-control-plane.yaml.tpl", {
    kubeadm_token = local.kubeadm_token
  })

  # 30, not the plan's original 40 — this AWS account has an explicit IAM deny policy
  # ("LimitVolumeSize") blocking any EBS volume over 30GB. Confirmed live via a failed
  # apply + `aws sts decode-authorization-message`, user-approved deviation.
  root_block_device { volume_size = 30 }
  tags = { Name = "testscope-k8s-control-plane" }
}

resource "aws_instance" "worker" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  subnet_id              = var.public_subnet_id
  vpc_security_group_ids = [var.security_group_id]
  iam_instance_profile   = aws_iam_instance_profile.worker.name
  key_name               = aws_key_pair.cluster.key_name
  user_data = templatefile("${path.module}/cloud-init-worker.yaml.tpl", {
    kubeadm_token            = local.kubeadm_token
    control_plane_private_ip = aws_instance.control_plane.private_ip
  })

  # 30, not the plan's original 40 — this AWS account has an explicit IAM deny policy
  # ("LimitVolumeSize") blocking any EBS volume over 30GB. Confirmed live via a failed
  # apply + `aws sts decode-authorization-message`, user-approved deviation.
  root_block_device { volume_size = 30 }
  tags = { Name = "testscope-k8s-worker" }
}
