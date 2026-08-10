resource "aws_s3_bucket" "reports" {
  bucket = "testscope-reports-${var.env}"
}

resource "aws_s3_bucket_lifecycle_configuration" "reports" {
  bucket = aws_s3_bucket.reports.id
  rule {
    id     = "expire-old-reports"
    status = "Enabled"
    expiration { days = 180 }
  }
}
