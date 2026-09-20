"""
dynamodb_client.py
DynamoDB client for the Alex single-table design.
This module provides a small wrapper around a single DynamoDB table, with methods for common operations 
such as creating, reading, updating, and deleting items. 
It also includes methods for querying and scanning the table, as well as batch operations and transactions.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Iterable, Optional
from uuid import uuid4

import boto3
from boto3.dynamodb.conditions import Attr, Key
from boto3.dynamodb.table import BatchWriter

from ramlytics_yfinance import yf_search


class DynamoDBClient:
    """Small wrapper around a single Alex DynamoDB table.

    Items use the key layout created by ``setup_dynamodb.py``. DynamoDB does
    not support SQL-style arbitrary updates or joins, so callers provide key
    values and update expressions explicitly.
    """

    def __init__(
        self,
        table_name: str | None = None,
        region: str | None = None,
        endpoint_url: str | None = None,
    ):
        self.table_name = table_name or os.environ.get(
            "DYNAMODB_TABLE", "alex-financial-data"
        )
        self.region = region or os.environ.get(
            "DEFAULT_AWS_REGION", os.environ.get("AWS_REGION", "us-east-1")
        )
        self.resource = boto3.resource(
            "dynamodb", region_name=self.region, endpoint_url=endpoint_url
        )
        self.table = self.resource.Table(self.table_name)

    @staticmethod
    def now() -> str:
        """Return a sortable UTC timestamp for created/updated fields."""
        return datetime.now(timezone.utc).isoformat(timespec="microseconds")

    @staticmethod
    def _clean_item(item: dict[str, Any]) -> dict[str, Any]:
        """Remove None values because DynamoDB does not accept them by default."""
        return {key: value for key, value in item.items() if value is not None}

    @classmethod
    def _to_decimal(cls, value: Any) -> Any:
        """Recursively convert floats to Decimal, since boto3 rejects native floats."""
        if isinstance(value, float):
            return Decimal(str(value))
        if isinstance(value, dict):
            return {key: cls._to_decimal(val) for key, val in value.items()}
        if isinstance(value, list):
            return [cls._to_decimal(val) for val in value]
        return value

    def put(self, item: dict[str, Any], condition_expression: Any = None) -> dict:
        """Create or replace an item."""
        kwargs: dict[str, Any] = {"Item": self._to_decimal(self._clean_item(item))}
        if condition_expression is not None:
            kwargs["ConditionExpression"] = condition_expression
        return self.table.put_item(**kwargs)

    def get(self, partition_key: str, sort_key: str) -> Optional[dict[str, Any]]:
        """Get one item by its primary key."""
        response = self.table.get_item(Key={"PK": partition_key, "SK": sort_key})
        return response.get("Item")

    def delete(self, partition_key: str, sort_key: str) -> dict:
        """Delete one item by its primary key."""
        return self.table.delete_item(Key={"PK": partition_key, "SK": sort_key})

    def update(
        self,
        partition_key: str,
        sort_key: str,
        update_expression: str,
        expression_attribute_values: dict[str, Any] | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        condition_expression: Any = None,
    ) -> dict[str, Any]:
        """Update an item using a DynamoDB UpdateExpression."""
        kwargs: dict[str, Any] = {
            "Key": {"PK": partition_key, "SK": sort_key},
            "UpdateExpression": update_expression,
            "ReturnValues": "ALL_NEW",
        }
        if expression_attribute_values:
            kwargs["ExpressionAttributeValues"] = self._to_decimal(expression_attribute_values)
        if expression_attribute_names:
            kwargs["ExpressionAttributeNames"] = expression_attribute_names
        if condition_expression is not None:
            kwargs["ConditionExpression"] = condition_expression
        return self.table.update_item(**kwargs)

    def update_attributes(
        self,
        partition_key: str,
        sort_key: str,
        attributes: dict[str, Any],
    ) -> dict[str, Any]:
        """Set arbitrary attributes on an item, skipping None values."""
        attributes = {key: value for key, value in attributes.items() if value is not None}
        if not attributes:
            return {}
        attributes["updated_at"] = self.now()
        names = {f"#{key}": key for key in attributes}
        values = {f":{key}": value for key, value in attributes.items()}
        set_expression = "SET " + ", ".join(f"#{key} = :{key}" for key in attributes)
        return self.update(partition_key, sort_key, set_expression, values, names)

    def query(
        self,
        partition_key: str,
        sort_key_begins_with: str | None = None,
        index_name: str | None = None,
        scan_forward: bool = True,
        limit: int | None = None,
        exclusive_start_key: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Query a partition and return ``Items`` plus pagination metadata."""
        partition_attribute = "PK" if index_name is None else f"{index_name}PK"
        sort_attribute = "SK" if index_name is None else f"{index_name}SK"
        key_condition = Key(partition_attribute).eq(partition_key)
        if sort_key_begins_with is not None:
            key_condition = key_condition & Key(sort_attribute).begins_with(
                sort_key_begins_with
            )

        kwargs: dict[str, Any] = {
            "KeyConditionExpression": key_condition,
            "ScanIndexForward": scan_forward,
        }
        if index_name:
            kwargs["IndexName"] = index_name
        if limit is not None:
            kwargs["Limit"] = limit
        if exclusive_start_key:
            kwargs["ExclusiveStartKey"] = exclusive_start_key
        return self.table.query(**kwargs)

    def query_all(
        self,
        partition_key: str,
        sort_key_begins_with: str | None = None,
        index_name: str | None = None,
        scan_forward: bool = True,
    ) -> list[dict[str, Any]]:
        """Query all pages for a partition."""
        items: list[dict[str, Any]] = []
        start_key = None
        while True:
            response = self.query(
                partition_key,
                sort_key_begins_with,
                index_name,
                scan_forward,
                exclusive_start_key=start_key,
            )
            items.extend(response.get("Items", []))
            start_key = response.get("LastEvaluatedKey")
            if not start_key:
                return items

    def batch_put(self, items: Iterable[dict[str, Any]]) -> None:
        """Write items in batches using boto3 retry handling."""
        with self.table.batch_writer() as batch:  # type BatchWriter
            for item in items:
                batch.put_item(Item=self._clean_item(item))

    def batch_delete(self, keys: Iterable[dict[str, str]]) -> None:
        """Delete primary-key pairs in batches."""
        with self.table.batch_writer() as batch:  # type BatchWriter
            for key in keys:
                batch.delete_item(Key=key)

    def get_by_generic_id(self, entity_id: str) -> Optional[dict[str, Any]]:
        """Look up an account, position, or job by its id alone via GSI4."""
        response = self.query(f"ID#{entity_id}", index_name="GSI4", limit=1)
        items = response.get("Items", [])
        return items[0] if items else None

    def scan_all(self, record_type: str | None = None) -> list[dict[str, Any]]:
        """Scan the whole table, optionally filtered by ``record_type``. Expensive - use sparingly."""
        items: list[dict[str, Any]] = []
        kwargs: dict[str, Any] = {}
        if record_type is not None:
            kwargs["FilterExpression"] = Attr("record_type").eq(record_type)
        start_key = None
        while True:
            if start_key:
                kwargs["ExclusiveStartKey"] = start_key
            response = self.table.scan(**kwargs)
            items.extend(response.get("Items", []))
            start_key = response.get("LastEvaluatedKey")
            if not start_key:
                return items

    def transact_write(self, actions: list[dict[str, Any]]) -> dict:
        """Execute a DynamoDB transaction using low-level item actions.

        Each action should be a boto3 ``TransactWriteItems`` action, such as
        ``{"Put": {"TableName": ..., "Item": ...}}``.
        """
        client = self.resource.meta.client
        return client.transact_write_items(TransactItems=actions)

    def put_user(self, clerk_user_id: str, **attributes: Any) -> dict:
        timestamp = self.now()
        item = {
            "PK": f"USER#{clerk_user_id}",
            "SK": "PROFILE",
            "record_type": "user",
            "clerk_user_id": clerk_user_id,
            "created_at": attributes.pop("created_at", timestamp),
            "updated_at": timestamp,
            **attributes,
        }
        return self.put(item)

    def get_user(self, clerk_user_id: str) -> Optional[dict[str, Any]]:
        return self.get(f"USER#{clerk_user_id}", "PROFILE")

    '''def list_users(self) -> Optional[list[dict[str, Any]]]:
        return self.query_all("USER#", "PROFILE")'''

    def list_accounts(self, clerk_user_id: str) -> list[dict[str, Any]]:
        return self.query_all(f"USER#{clerk_user_id}", "ACCOUNT#")

    def get_account(self, clerk_user_id: str, account_id: str) -> Optional[dict[str, Any]]:
        return self.get(f"USER#{clerk_user_id}", f"ACCOUNT#{account_id}")

    def put_account(self, clerk_user_id: str, account_id: str | None = None, **attributes: Any) -> str:
        account_id = account_id or str(uuid4())
        timestamp = self.now()
        item = {
            "PK": f"USER#{clerk_user_id}",
            "SK": f"ACCOUNT#{account_id}",
            "GSI1PK": f"USER#{clerk_user_id}",
            "GSI1SK": f"ACCOUNT#{timestamp}#{account_id}",
            "GSI4PK": f"ID#{account_id}",
            "GSI4SK": "ACCOUNT",
            "record_type": "account",
            "account_id": account_id,
            "clerk_user_id": clerk_user_id,
            "created_at": timestamp,
            "updated_at": timestamp,
            **attributes,
        }
        self.put(item)
        return account_id

    def list_positions(self, account_id: str) -> list[dict[str, Any]]:
        return self.query_all(f"ACCOUNT#{account_id}", "POSITION#")

    def get_position(self, account_id: str, symbol: str) -> Optional[dict[str, Any]]:
        return self.get(f"ACCOUNT#{account_id}", f"POSITION#{symbol}")

    def put_position(
        self,
        clerk_user_id: str,
        account_id: str,
        symbol: str,
        quantity: Decimal | int | float | str,
        **attributes: Any,
    ) -> dict:
        timestamp = self.now()
        existing = self.get_position(account_id, symbol)
        position_id = attributes.pop("position_id", None) or (
            existing.get("position_id") if existing else None
        ) or str(uuid4())
        item = {
            "PK": f"ACCOUNT#{account_id}",
            "SK": f"POSITION#{symbol}",
            "GSI1PK": f"USER#{clerk_user_id}",
            "GSI1SK": f"POSITION#{account_id}#{symbol}",
            "GSI2PK": f"INSTRUMENT#{symbol}",
            "GSI2SK": f"ACCOUNT#{account_id}",
            "GSI4PK": f"ID#{position_id}",
            "GSI4SK": "POSITION",
            "record_type": "position",
            "position_id": position_id,
            "id": position_id,
            "clerk_user_id": clerk_user_id,
            "account_id": account_id,
            "symbol": symbol,
            "quantity": Decimal(str(quantity)),
            "as_of_date": attributes.pop("as_of_date", date.today().isoformat()),
            "created_at": (existing or {}).get("created_at", timestamp),
            "updated_at": timestamp,
            **attributes,
        }
        self.put(item)
        return item

    def list_instruments(self) -> list[dict[str, Any]]:
        return self.query_all("INSTRUMENTS", "INSTRUMENT#")

    def get_instrument(self, symbol: str) -> Optional[dict[str, Any]]:
        return self.get("INSTRUMENTS", f"INSTRUMENT#{symbol}")

    def put_instrument(self, symbol: str, **attributes: Any) -> dict:
        timestamp = self.now()
        item = {
            "PK": "INSTRUMENTS",
            "SK": f"INSTRUMENT#{symbol}",
            "GSI2PK": f"INSTRUMENT#{symbol}",
            "GSI2SK": "REFERENCE",
            "record_type": "instrument",
            "symbol": symbol,
            "created_at": attributes.pop("created_at", timestamp),
            "updated_at": timestamp,
            **attributes,
        }
        quote = yf_search(symbol)  # Look up the instrument on Yahoo Finance
        if not item.get("name") or "User Added" in item.get("name"):
            item["name"] = quote.get("longname")
        if not item.get("instrument_type"):
            item["instrument_type"] = quote.get("quoteType").lower()
        if quote.get("sector") and not item.get("sector"):
            item["sector"] = quote.get("sector")
        if quote.get("industry") and not item.get("industry"):
            item["industry"] = quote.get("industry")
        if quote.get("current_price"):
            item["current_price"] = quote.get("current_price")

        return self.put(item)

    def get_job(self, clerk_user_id: str, job_id: str, created_at: str) -> Optional[dict[str, Any]]:
        return self.get(f"USER#{clerk_user_id}", f"JOB#{created_at}#{job_id}")

    def put_job(
        self,
        clerk_user_id: str,
        job_type: str,
        job_id: str | None = None,
        status: str = "pending",
        created_at: str | None = None,
        **attributes: Any,
    ) -> tuple[str, str]:
        job_id = job_id or str(uuid4())
        created_at = created_at or self.now()
        item = {
            "PK": f"USER#{clerk_user_id}",
            "SK": f"JOB#{created_at}#{job_id}",
            "GSI1PK": f"USER#{clerk_user_id}",
            "GSI1SK": f"JOB#{created_at}#{job_id}",
            "GSI3PK": f"USER#{clerk_user_id}#STATUS#{status}",
            "GSI3SK": f"{created_at}#{job_id}",
            "GSI4PK": f"ID#{job_id}",
            "GSI4SK": "JOB",
            "record_type": "job",
            "job_id": job_id,
            "clerk_user_id": clerk_user_id,
            "job_type": job_type,
            "status": status,
            "created_at": created_at,
            "updated_at": self.now(),
            **attributes,
        }
        self.put(item)
        return job_id, created_at

    def update_job_status(
        self,
        clerk_user_id: str,
        job_id: str,
        created_at: str,
        status: str,
        **attributes: Any,
    ) -> dict[str, Any]:
        """Update status and keep the status GSI key synchronized."""
        values = {
            ":status": status,
            ":status_pk": f"USER#{clerk_user_id}#STATUS#{status}",
            ":updated_at": self.now(),
            **{f":{key}": value for key, value in attributes.items()},
        }
        names = {f"#{key}": key for key in attributes}
        set_parts = [
            "#status = :status",
            "GSI3PK = :status_pk",
            "updated_at = :updated_at",
        ]
        set_parts.extend(f"#{key} = :{key}" for key in attributes)
        return self.update(
            f"USER#{clerk_user_id}",
            f"JOB#{created_at}#{job_id}",
            "SET " + ", ".join(set_parts),
            values,
            {"#status": "status", **names},
        )

    def list_jobs(self, clerk_user_id: str, status: str | None = None) -> list[dict[str, Any]]:
        if status:
            return self.query_all(
                f"USER#{clerk_user_id}#STATUS#{status}", index_name="GSI3", scan_forward=False
            )
        return self.query_all(f"USER#{clerk_user_id}", "JOB#", scan_forward=False)


__all__ = ["DynamoDBClient"]
