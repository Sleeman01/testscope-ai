output "queue_url" { value = aws_sqs_queue.jobs.id }
output "queue_arn" { value = aws_sqs_queue.jobs.arn }
output "dlq_arn" { value = aws_sqs_queue.dlq.arn }
# Task 42: added alongside dlq_arn (not a new resource -- aws_sqs_queue.dlq already
# exists, this just exposes its .id too, same pattern queue_url already uses for the main
# queue). Needed because dlq_arn alone can't satisfy Task 42's own Step 1 command
# ("aws sqs send-message --queue-url ...") -- that flag requires an actual queue URL
# (https://sqs.<region>.amazonaws.com/<account>/<name>), not an ARN
# (arn:aws:sqs:<region>:<account>:<name>); the two are different formats and AWS CLI
# rejects an ARN there.
output "dlq_url" { value = aws_sqs_queue.dlq.id }
