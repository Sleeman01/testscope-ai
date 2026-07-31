import json
from datetime import datetime, timezone
from decimal import Decimal
from aws import get_dynamodb_table, get_s3_client, get_s3_bucket_name

def _render_markdown(repository, issue_number, requirement, coverage_matrix, missing_tests, test_plan) -> str:
    lines = [f"# Coverage Report — {repository}#{issue_number}", "", f"## {requirement.get('feature_name', 'Untitled')}", ""]
    lines.append("## Coverage Matrix")
    for row in coverage_matrix:
        lines.append(f"- **{row['criterion_id']}**: {row['status']}")
    lines.append("")
    lines.append(f"## Missing Tests ({len(missing_tests)})")
    for m in missing_tests:
        lines.append(f"- {m.get('behavior', '')}")
    return "\n".join(lines)

def save_coverage_report(analysis_id, repository, issue_number, requirement, coverage_matrix,
                          missing_tests, test_plan, status, tool_call_trace) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    s3_key = f"{repository}/{issue_number}/{analysis_id}"
    payload = {
        "analysis_id": analysis_id, "repository": repository, "issue_number": issue_number,
        "requirement": requirement, "coverage_matrix": coverage_matrix,
        "missing_tests": missing_tests, "test_plan": test_plan, "status": status,
        "tool_call_trace": tool_call_trace, "created_at": now,
    }
    s3 = get_s3_client()
    bucket = get_s3_bucket_name()
    s3.put_object(Bucket=bucket, Key=f"{s3_key}.json", Body=json.dumps(payload).encode(), ContentType="application/json")
    md = _render_markdown(repository, issue_number, requirement, coverage_matrix, missing_tests, test_plan)
    s3.put_object(Bucket=bucket, Key=f"{s3_key}.md", Body=md.encode(), ContentType="text/markdown")

    covered = sum(1 for r in coverage_matrix if r["status"] == "Covered")
    total = len(coverage_matrix) or 1
    table = get_dynamodb_table()
    table.put_item(Item={
        "analysis_id": analysis_id, "repository": repository, "issue_number": issue_number,
        "repository_issue": f"{repository}#{issue_number}", "gsi2_pk": "ANALYSIS",
        "status": status, "created_at": now, "updated_at": now,
        "requirement_summary": requirement.get("feature_name", ""),
        "coverage_summary": {"percent_covered": Decimal(str(round(100 * covered / total, 1)))},
        "missing_tests_count": len(missing_tests),
        "s3_report_key": f"{s3_key}.json", "tool_call_trace": tool_call_trace,
    })
    return {"s3_report_key": f"{s3_key}.json", "dynamodb_status": "saved"}
