resource "aws_sns_topic" "alerts" {
  name = "testscope-${var.env}-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_cloudwatch_metric_alarm" "dlq_not_empty" {
  alarm_name          = "testscope-${var.env}-dlq-not-empty"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Maximum"
  threshold           = 0
  dimensions          = { QueueName = "testscope-jobs-${var.env}-dlq" }
  alarm_actions       = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "queue_backlog_age" {
  alarm_name          = "testscope-${var.env}-queue-backlog-age"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ApproximateAgeOfOldestMessage"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Maximum"
  threshold           = 900  # 15 min backlog
  dimensions          = { QueueName = "testscope-jobs-${var.env}" }
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
