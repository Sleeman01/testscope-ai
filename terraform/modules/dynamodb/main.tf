resource "aws_dynamodb_table" "analyses" {
  name         = "testscope-analyses-${var.env}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "analysis_id"

  attribute {
    name = "analysis_id"
    type = "S"
  }
  attribute {
    name = "repository_issue"
    type = "S"
  }
  attribute {
    name = "created_at"
    type = "S"
  }
  attribute {
    name = "gsi2_pk"
    type = "S"
  }

  global_secondary_index {
    name            = "repository_issue-index"
    hash_key        = "repository_issue"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "recent-index"
    hash_key        = "gsi2_pk"
    range_key       = "created_at"
    projection_type = "ALL"
  }
}
