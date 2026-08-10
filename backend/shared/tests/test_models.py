import json
from pathlib import Path

from models import AnalysisRecord

FIXTURE = Path(__file__).parent / "fixtures" / "sample_analysis_record.json"

def test_analysis_record_parses_the_shared_fixture():
    data = json.loads(FIXTURE.read_text())
    record = AnalysisRecord.model_validate(data)
    assert record.analysis_id == data["analysis_id"]
    assert record.status == "completed"
