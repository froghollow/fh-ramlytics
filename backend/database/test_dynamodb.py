from decimal import Decimal

from ramlytics_database import DynamoDBClient
db = DynamoDBClient()

def test_user_record_is_mapped_to_single_table_shape():
    record = {
        "clerk_user_id": "user_123",
        "display_name": "Test User",
        "years_until_retirement": 25,
        "target_retirement_income": "100000.00",
        "asset_class_targets": '{"equity":70,"fixed_income":30}',
        "region_targets": '{"north_america":50,"international":50}',
        "created_at": "2026-05-22 13:17:35.091994",
        "updated_at": "2026-05-22 13:17:35.091994",
    }
    item = db.put_user(record)

    assert item["PK"] == "USER#user_123"
    assert item["SK"] == "PROFILE"
    assert item["record_type"] == "user"
    assert item["target_retirement_income"] == Decimal("100000.00")
    assert item["asset_class_targets"]["equity"] == Decimal("70")
    assert item["region_targets"]["north_america"] == Decimal("50")


def test_account_record_is_lookupable_by_generic_id():
    record = {
        "id": "account-123",
        "clerk_user_id": "user_123",
        "account_name": "Roth IRA",
        "created_at": "2026-05-22 13:17:35.091994",
        "updated_at": "2026-05-22 13:17:35.091994",
    }

    item = db.put_account(record)

    assert item["GSI4PK"] == "ID#account-123"
    assert item["GSI4SK"] == "ACCOUNT"


def test_job_record_is_mapped_to_status_index_shape():
    record = {
        "id": "job-123",
        "clerk_user_id": "user_123",
        "job_type": "portfolio_analysis",
        "status": "completed",
        "request_payload": '{"analysis_type": "test"}',
        "created_at": "2026-05-23 16:11:36.123102",
        "updated_at": "2026-05-23 16:12:03.767080",
    }

    item = db.put_job(record)

    assert item["PK"] == "USER#user_123"
    assert item["SK"] == "JOB#2026-05-23 16:11:36.123102#job-123"
    assert item["GSI3PK"] == "USER#user_123#STATUS#completed"
    assert item["request_payload"]["analysis_type"] == "test"


1