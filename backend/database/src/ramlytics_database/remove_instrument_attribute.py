"""
remove_instrument_attribute.py
Remove one or more attributes from an instrument item (PK="INSTRUMENTS", SK="INSTRUMENT#{symbol}").

CLI: python -m ramlytics_database.remove_instrument_attribute AAPL attr1 [attr2 ...]
"""

from __future__ import annotations

import argparse
import os
from typing import Any, Iterable

import boto3
from botocore.exceptions import ClientError

KEY_ATTRIBUTES = {"PK", "SK"}


def remove_instrument_attributes(
    symbol: str,
    attributes: str | Iterable[str],
    table_name: str | None = None,
    region: str | None = None,
    table: Any = None,
) -> dict[str, Any]:
    """Remove attributes from the instrument item and return the updated item.

    Raises ValueError for empty input or key attributes, and LookupError if the
    instrument item does not exist.
    """
    symbol = (symbol or "").strip().upper()
    if not symbol:
        raise ValueError("symbol is required")
    names = [attributes] if isinstance(attributes, str) else list(attributes)
    names = list(dict.fromkeys(n.strip() for n in names if n and n.strip()))
    if not names:
        raise ValueError("at least one attribute is required")
    protected = KEY_ATTRIBUTES.intersection(names)
    if protected:
        raise ValueError(f"cannot remove key attributes: {sorted(protected)}")

    if table is None:
        table = boto3.resource(
            "dynamodb",
            region_name=region
            or os.environ.get("DEFAULT_AWS_REGION", os.environ.get("AWS_REGION", "us-east-1")),
        ).Table(table_name or os.environ.get("DYNAMODB_TABLE", "alex-financial-data"))

    # Placeholders avoid collisions with DynamoDB reserved words.
    placeholders = {f"#a{i}": n for i, n in enumerate(names)}
    try:
        response = table.update_item(
            Key={"PK": "INSTRUMENTS", "SK": f"INSTRUMENT#{symbol}"},
            UpdateExpression="REMOVE " + ", ".join(placeholders),
            ExpressionAttributeNames={"#pk": "PK", **placeholders},
            ConditionExpression="attribute_exists(#pk)",
            ReturnValues="ALL_NEW",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise LookupError(f"Instrument {symbol} not found") from exc
        raise
    return response.get("Attributes", {})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("symbol")
    parser.add_argument("attributes", nargs="+")
    parser.add_argument("--table")
    parser.add_argument("--region")
    args = parser.parse_args()
    item = remove_instrument_attributes(args.symbol, args.attributes, args.table, args.region)
    print(f"Updated {item.get('SK')}: remaining attributes {sorted(item)}")


if __name__ == "__main__":
    main()
