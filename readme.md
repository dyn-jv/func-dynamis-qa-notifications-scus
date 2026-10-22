For the exact original cloud test sender, payload and acceptance evidence, see
[October 15 manual test](docs/manual-test-2026-10-15/README.md).

# Historical 52G replay

The current milestone is **read-only historical validation**, not live alerts.
Across all units in `DT35_MAIN`, **52G 1 = closed; 0 = open**. An opening is
`1 → 0`, qualified when the immediately preceding closed reading has
`NGGSEL >= 7000` and the samples are at most five seconds apart. Current-row
NGGSEL does not gate the opening. No temperature or megawatt filter is applied.

```sh
source .venv/bin/activate
python3 -m pip install -r requirements.txt
az login
python3 replay_52g.py
python3 replay_52g.py --start 2026-10-01T00:00:00Z --end 2026-10-02T00:00:00Z
```

The default window is the last 24 hours. Explicit dates require time zones;
start is inclusive and end is exclusive. The first reading within the window
is each unit's baseline. No pre-window state or persistent checkpoint is used.
The runner uses your Azure CLI identity, which needs ADX database Viewer access.
Override `--cluster` and `--database` if needed. The query endpoint was inferred from the ingestion endpoint and verified
by successful read-only queries on 2026-10-16.

Reports are written to unique `out/replay-*.json` and `.csv` paths. CSV contains
all opening candidates with previous/current readings, gap, classification and
reason. JSON additionally includes per-unit counts, quality records and source
settings. Empty results are valid. Truncated or partial queries fail rather than
produce a successful report. JSON timestamps are UTC.

Gaps greater than five seconds and missing/nonfinite previous NGGSEL classify an
opening as uncertain. Values below 7000 classify it as not running. Identical
rows on the four selected columns collapse. Conflicting values at a unit/time
or invalid breaker readings break continuity; the next valid sample establishes
a fresh baseline. All units, including those with no openings, have summaries.
Rows with null timestamps cannot be assigned to a historical window and are
excluded by the time predicate. Rows without a unit are reported as quality issues.

`queries/detect_52g.kql` contains the shared KQL detector. To obtain a complete
query for ADX, run `python3 replay_52g.py --print-query`; in the ADX editor supply
Start/End query parameter defaults (or replace the declaration with UTC `let`
constants). All transition logic runs in ADX, avoiding a raw telemetry download.

Validation:

```sh
python3 -m unittest discover -s tests -v
python3 tests/validate_kql.py
```

The second command runs the actual shared query on synthetic inline data in ADX;
it is read-only and requires cluster access. Inspect source readings around real
qualified/not-running/uncertain results before considering live scheduling.

No automated sends, new HTTP routes or cloud configuration changes are part of
this milestone. The bundled manual tester fixture now represents open as 0;
the original annotated example and historical send receipt are preserved. The
already-deployed tester is unchanged until an explicit future deployment.
Galaxy processing and real asset mappings remain unconfirmed.

---

# Manual notification test

## Deployed Function tester

`function_app.py` exposes `/api/notification-test` with function-key authorization:

- GET previews the bundled notification without sending.
- POST with `{"send": true}` sends one message to `power-azureiot-alert` and returns
  the exact sent payload and message ID. Each POST generates a fresh timestamp
  and ID; its body is the bundled fixture, not a caller-supplied notification.

It explicitly uses the assigned Galaxy identity client ID
`7e2dcba0-2e52-4b1f-b715-f708b56a0211`. Override with the optional app setting
`SERVICE_BUS_MI_CLIENT_ID`. Storage and monitoring identities are unaffected.

The Azure host is `func-dynamis-qa-notifications-scus` in `DynamisPS`, subscription
`835baf64-0f24-4ca2-8e65-5bcfdbb98978`. Inspection found Flex Consumption with
Python 3.14; local tests ran on Python 3.12. Deployment uses a remote build.

After logging into Azure CLI, preview and verify authentication:

```sh
python3 verify_deployment.py
```

To preview and send one test notification:

```sh
python3 verify_deployment.py --send
```

This helper reads a function-specific key through Azure CLI and keeps it in memory.
HTTP callers must supply the function key using `x-functions-key`. The deployed
endpoint uses shared-key authorization, not individual Entra user sign-in.

Local verification: `.venv/bin/python -m unittest discover -s tests -v`.

Deployment ZIP contains only `function_app.py`, `send_notification.py`, `host.json`,
`requirements.txt`, and `in/test-notification.json` at their project-relative paths.

```sh
az functionapp deployment source config-zip \
  --subscription 835baf64-0f24-4ca2-8e65-5bcfdbb98978 \
  --resource-group DynamisPS --name func-dynamis-qa-notifications-scus \
  --src out/notification-tester.zip --build-remote true
```

Send one predefined JSON notification to the QA Service Bus namespace
`sb-qa-scus-5uhjokcqxur5g`, topic `power-azureiot-alert`.
Telemetry integration is a later milestone.

## Payload

`in/example-notification.json` is the original annotated reference.
`in/test-notification.json` is valid JSON derived from it: comments removed,
sensor set to `52G`, status set to `0` (open), title typo corrected, and the
truncated Base64 example replaced with an encoded test object. Other example
identifiers are retained; they are not verified Galaxy asset mappings.
The receiving team's schema and routing requirements still need confirmation.

## Preview locally

Python 3.10+ is required. Preview needs no packages or Azure access:

```sh
python3 send_notification.py --refresh-timestamp
```

## Authenticate and send

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
az login
.venv/bin/python send_notification.py --refresh-timestamp --send
```

Azure CLI is installed separately. DefaultAzureCredential uses supported local
Azure credentials, including Azure CLI login. Your identity needs **Azure Service
Bus Data Sender** on this topic or its namespace; subscription access alone does
not establish send permission. The subscription ID and resource group from the
email are management information, not authentication credentials.

Alternatively, obtain a connection string with Send permission through your
team's approved secret-sharing channel, set `SERVICE_BUS_CONNECTION_STRING` in
the local environment, and use:

```sh
.venv/bin/python send_notification.py --auth connection-string --refresh-timestamp --send
```

Do not put connection strings in source files. The script does not load `.env`.
It uses AMQP over WebSockets (port 443). No resources or subscriptions are created.

The email also offers the existing Galaxy flow for testing. To explicitly select it:

```sh
.venv/bin/python send_notification.py --topic sbtgalscusqa03 --refresh-timestamp --send
```

That flow may create a Galaxy incident. The default remains `power-azureiot-alert`.

## Verify the result

Record the printed message ID, topic, event timestamp, and payload alarm ID.
Successful sending means Service Bus accepted the message. Have the receiving
team confirm receipt and, where wired up, Galaxy incident creation using those
identifiers. Ask whether the new topic has a consumer subscription and whether
any filter properties or session ID are required. This sender sets content type
and message ID, with no custom routing properties.

Each invocation generates a new message ID; `--message-id` can set it explicitly.
Automatic SDK retries are disabled for this manual test. A failed acknowledgment
does not prove non-delivery. Reusing an ID only prevents duplicates if the topic
has duplicate detection configured within its detection window.

## Next milestones

1. Confirm authentication and acceptance of one manual message.
2. Validate historical replay across all DT35_MAIN units.
3. Confirm downstream processing and real asset mappings before live scheduling.
4. Add persisted state and delivery recovery before automated notifications.

References: [Python Service Bus SDK](https://learn.microsoft.com/en-us/python/api/overview/azure/servicebus-readme),
[Service Bus roles](https://learn.microsoft.com/en-us/azure/service-bus-messaging/service-bus-python-how-to-use-queues).
