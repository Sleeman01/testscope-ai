output "control_plane_public_ip" { value = aws_instance.control_plane.public_ip }
output "control_plane_private_ip" { value = aws_instance.control_plane.private_ip }
output "control_plane_id" { value = aws_instance.control_plane.id }
output "worker_public_ip" { value = aws_instance.worker.public_ip }
output "worker_id" { value = aws_instance.worker.id }
output "worker_iam_role_arn" { value = aws_iam_role.worker.arn }
output "ssh_private_key_path" { value = local_sensitive_file.ssh_private_key.filename }
