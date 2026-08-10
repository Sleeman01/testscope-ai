resource "aws_iam_role_policy" "env_access" {
  name = "testscope-${var.env}-access"
  role = var.instance_role_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject"], Resource = "${var.bucket_arn}/*" },
      { Effect = "Allow", Action = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:Query"],
      Resource = [var.table_arn, "${var.table_arn}/index/*"] },
      { Effect = "Allow", Action = ["sqs:SendMessage", "sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"],
      Resource = [var.queue_arn, var.dlq_arn] },
      { Effect = "Allow", Action = ["cloudwatch:PutMetricData", "logs:CreateLogStream", "logs:PutLogEvents"], Resource = "*" },
    ]
  })
}
