output "queue_url" { value = aws_sqs_queue.jobs.id }
output "queue_arn" { value = aws_sqs_queue.jobs.arn }
output "dlq_arn" { value = aws_sqs_queue.dlq.arn }
