# Manual send evidence — 2026-10-15

This folder preserves the deployment files from the local ZIP used for deployment
`10fe1549-2f60-4cc6-a9f6-64c4f07ad49a`. This is a historical reference, not the current
fixture or a new deployment. No new test message was sent when publishing this evidence.

## What sent the message

`deployment/function_app.py` is the HTTP-triggered Azure sender. It imports the
namespace and topic from `deployment/send_notification.py`, authenticates with
Galaxy managed identity client ID `7e2dcba0-2e52-4b1f-b715-f708b56a0211`, and sends
one message when POSTed `{ "send": true }`. `verify_deployment.py` at repository
root invoked that endpoint. The standalone CLI sender was not the process that
performed the successful cloud send.

`sent-payload.json` reconstructs the sent JSON from the deployment fixture plus
the recorded event timestamp; these values match the successful HTTP response.
`receipt.json` records the acceptance result. It is not a consumer acknowledgment.

- Namespace: `sb-qa-scus-5uhjokcqxur5g.servicebus.windows.net`
- Topic: `power-azureiot-alert` (NOT the legacy `sbtgalscusqa03` topic)
- Message ID: `8fe1fd68-b7c3-4333-8540-dcd077bad48b`
- Event timestamp: `2026-10-15T22:51:05.407Z`
- Content type: `application/json`
- Body: JSON text
- Custom application properties: none
- Subject, correlation ID, and session ID: not explicitly set
- TTL: not explicitly set; entity defaults apply

The original test used `telemetry.status = 1` with an Open alarm. The user later
clarified that 0 means open and 1 means closed. The current root fixture uses 0;
the historical deployment and sent payload intentionally retain 1. Asset/customer/
fleet identifiers are examples and have not been confirmed against Galaxy mappings.

## Receiving-team checks

1. Confirm the consumer reads a Service Bus subscription under this exact topic,
   not just the legacy topic; confirm that subscription existed when this test was sent.
2. Check subscription rules. Broker filters inspect system/application properties,
   not JSON body fields. If rules require messageType, businessUnitId or similar
   application properties, this sender currently does not set them.
3. Check the subscription's active and dead-letter counts, expiration/TTL settings,
   session requirements and forwarding destination. Inspect rather than consume
   messages during diagnosis.
4. Search consumer logs for the message ID and event timestamp. Check payload
   validation, unknown asset mappings and incident deduplication using the fixed
   alarm ID `dyn-dt35-001`.
5. If this older message cannot be traced, arrange a new test after the correct
   subscription and routing contract are confirmed.

Service Bus acceptance establishes successful publication; it does not establish
subscription matching, consumer receipt, or Galaxy incident creation.

References:
- https://learn.microsoft.com/en-us/azure/service-bus-messaging/topic-filters
- https://learn.microsoft.com/en-us/azure/service-bus-messaging/service-bus-queues-topics-subscriptions
