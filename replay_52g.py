"""Read-only historical 52G opening replay; never publishes notifications."""
import argparse
import csv
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parent
CLUSTER = "https://dynamisps.centralus.kusto.windows.net"
DATABASE = "Turbine_Hub_Data_2023"
FIELDS = ["unit", "timestamp", "previous_timestamp", "breaker", "previous_breaker",
          "nggsel", "previous_nggsel", "gap_seconds", "classification", "reason"]


def utc_time(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Times must include Z or a UTC offset")
    return parsed.astimezone(timezone.utc)


def detector_query():
    return (ROOT / "queries/detect_52g.kql").read_text()


def historical_query():
    return "declare query_parameters(Start:datetime, End:datetime);\n" + detector_query() + '''
DT35_MAIN
| where timestamp >= Start and timestamp < End
| project timestamp, UNIT_NUM, Breaker=['52G'], Speed=NGGSEL
| invoke Detect52G()
'''


def execute(client, database, query, properties=None):
    result = client.execute_query(database, query, properties)
    if result.get_exceptions():
        raise RuntimeError("ADX returned partial results or query errors; no successful report was written")
    if len(result.primary_results) != 1:
        raise RuntimeError("Unexpected ADX result shape")
    records = []
    for row in result.primary_results[0]:
        data = row["Data"]
        records.append((row["Kind"], json.loads(data) if isinstance(data, str) else data))
    return records


def reports(records):
    output = {"events": [], "quality": [], "summary": []}
    for kind, data in records:
        key = {"event": "events", "quality": "quality", "summary": "summary"}.get(kind)
        if key is None or not isinstance(data, dict):
            raise ValueError("Unexpected detector output")
        output[key].append(data)
    for values in output.values():
        values.sort(key=lambda row: (row.get("unit", ""), str(row.get("timestamp", ""))))
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=utc_time)
    parser.add_argument("--end", type=utc_time)
    parser.add_argument("--cluster", default=CLUSTER)
    parser.add_argument("--database", default=DATABASE)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "out")
    parser.add_argument("--print-query", action="store_true", help="Print KQL without connecting")
    args = parser.parse_args()
    if args.print_query:
        print(historical_query())
        return 0
    if bool(args.start) != bool(args.end):
        parser.error("Provide both --start and --end, or neither")
    end = args.end or datetime.now(timezone.utc)
    start = args.start or end - timedelta(hours=24)
    if start >= end:
        parser.error("--start must precede --end")
    try:
        from azure.kusto.data import KustoClient, KustoConnectionStringBuilder, ClientRequestProperties
        properties = ClientRequestProperties()
        properties.set_parameter("Start", start.isoformat())
        properties.set_parameter("End", end.isoformat())
        properties.set_option("deferpartialqueryfailures", False)
        with KustoClient(KustoConnectionStringBuilder.with_az_cli_authentication(args.cluster)) as client:
            output = reports(execute(client, args.database, historical_query(), properties))
        output["metadata"] = {"cluster": args.cluster, "database": args.database, "table": "DT35_MAIN",
                              "start": start.isoformat(), "end": end.isoformat(),
                              "rule": "52G 1->0; previous NGGSEL >= 7000; gap <= 5 seconds",
                              "baseline": "first reading within window", "status": "complete"}
        args.output_dir.mkdir(parents=True, exist_ok=True)
        stem = args.output_dir / ("replay-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8])
        stem.with_suffix(".json").write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
        with stem.with_suffix(".csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(output["events"])
        print(f"Window: {start.isoformat()} to {end.isoformat()} (end exclusive)")
        for row in output["summary"]:
            print(json.dumps(row))
        print(f"{len(output['events'])} opening candidates; {len(output['quality'])} quality issues")
        print(f"Reports: {stem}.json and {stem}.csv")
        return 0
    except Exception as exc:
        print(f"Replay failed ({type(exc).__name__}): {exc}", file=sys.stderr)
        print("Check Azure CLI login, ADX database Viewer access, endpoint and network connectivity. No notifications were sent.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
