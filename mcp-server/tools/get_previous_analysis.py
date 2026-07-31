from boto3.dynamodb.conditions import Key
from aws import get_dynamodb_table

def get_previous_analysis(repository: str, issue_number: int) -> dict:
    table = get_dynamodb_table()
    response = table.query(
        IndexName="repository_issue-index",
        KeyConditionExpression=Key("repository_issue").eq(f"{repository}#{issue_number}"),
        ScanIndexForward=False,
    )
    analyses = [{
        "analysis_id": item["analysis_id"], "created_at": item["created_at"],
        "status": item["status"], "coverage_summary": item.get("coverage_summary"),
        "s3_report_key": item.get("s3_report_key"),
    } for item in response["Items"]]
    return {"analyses": analyses}
