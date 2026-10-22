"""Manually preview or send one JSON notification to Azure Service Bus."""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import uuid

NAMESPACE = "sb-qa-scus-5uhjokcqxur5g.servicebus.windows.net"
TOPIC = "power-azureiot-alert"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, default=Path(__file__).parent / "in/test-notification.json")
    parser.add_argument("--topic", choices=[TOPIC, "sbtgalscusqa03"], default=TOPIC)
    parser.add_argument("--auth", choices=["azure", "connection-string"], default="azure")
    parser.add_argument("--message-id", default=None, help="Optional ID for tracking a particular test")
    parser.add_argument("--refresh-timestamp", action="store_true", help="Set context.eventTimestamp to current UTC")
    parser.add_argument("--send", action="store_true", help="Send one message; otherwise only preview")
    args = parser.parse_args()
    try:
        payload = json.loads(args.payload.read_text(), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"Invalid JSON constant: {value}")))
        if not isinstance(payload, dict):
            raise ValueError("Payload must be a JSON object")
        if args.refresh_timestamp:
            if not isinstance(payload.get("context"), dict):
                raise ValueError("Timestamp refresh requires a context object")
            payload["context"]["eventTimestamp"] = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        body = json.dumps(payload, allow_nan=False)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    message_id = args.message_id or str(uuid.uuid4())
    print(f"Namespace: {NAMESPACE}\nTopic: {args.topic}\nMessage ID: {message_id}", flush=True)
    if not args.send:
        print(json.dumps(payload, indent=2))
        print("Preview only. Add --send to publish this notification.")
        return 0

    try:
        from azure.identity import DefaultAzureCredential
        from azure.servicebus import ServiceBusClient, ServiceBusMessage, TransportType
        import websocket  # Required by the SDK's synchronous WebSocket transport.
    except ImportError:
        print("No send attempted. Missing a required package (including websocket-client for WebSockets). "
              "Install dependencies: python3 -m pip install -r requirements.txt", file=sys.stderr)
        return 1

    try:
        with ExitStack() as stack:
            options = {"transport_type": TransportType.AmqpOverWebsocket, "retry_total": 0}
            if args.auth == "connection-string":
                connection = os.environ.get("SERVICE_BUS_CONNECTION_STRING")
                if not connection:
                    raise ValueError("Set SERVICE_BUS_CONNECTION_STRING in your environment")
                fields = dict(part.split("=", 1) for part in connection.split(";") if "=" in part)
                if fields.get("Endpoint", "").rstrip("/").lower() != f"sb://{NAMESPACE}":
                    raise ValueError("Connection string must target the configured QA namespace")
                if fields.get("EntityPath", args.topic) != args.topic:
                    raise ValueError("Connection string EntityPath does not match selected topic")
                client = ServiceBusClient.from_connection_string(connection, **options)
            else:
                credential = stack.enter_context(DefaultAzureCredential())
                client = ServiceBusClient(NAMESPACE, credential, **options)
            stack.enter_context(client)
            sender = stack.enter_context(client.get_topic_sender(topic_name=args.topic))
            message = ServiceBusMessage(body, content_type="application/json", message_id=message_id)
            sender.send_messages(message, timeout=30)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        # SDK exception details can contain connection information; do not print secrets.
        print(f"Send not confirmed ({type(exc).__name__}). Check authentication, send permission, and network access."
              " Delivery may be uncertain; check the message ID before retrying.", file=sys.stderr)
        return 1
    print("Service Bus accepted the message. Galaxy processing still needs verification.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
