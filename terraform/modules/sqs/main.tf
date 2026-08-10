resource "aws_sqs_queue" "dlq" {
  name = "testscope-jobs-${var.env}-dlq"
}

resource "aws_sqs_queue" "jobs" {
  name                       = "testscope-jobs-${var.env}"
  visibility_timeout_seconds = 660 # > worker's 600s graph timeout
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })
}
