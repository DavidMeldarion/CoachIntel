from __future__ import annotations
from typing import Iterable, Dict
import csv
from io import StringIO

CSV_COLUMNS = [
    "id",
    "created_at",
    "status",
    "first_name",
    "last_name",
    "email",
    "phone",
    "tags",
    "source",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "last_contacted_at",
]

def rows_to_csv(rows: Iterable[Dict]) -> str:
    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    for r in rows:
        # ensure tags are joined as semicolon list
        r = dict(r)
        tags = r.get("tags")
        if isinstance(tags, (list, tuple)):
            r["tags"] = ";".join(tags)
        writer.writerow({k: r.get(k, "") if r.get(k) is not None else "" for k in CSV_COLUMNS})
    return buf.getvalue()
