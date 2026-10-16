"""Key-protected manual Service Bus test. GET previews; POST sends one fixture."""
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import azure.functions as func
from azure.identity import ManagedIdentityCredential
from azure.servicebus import ServiceBusClient, ServiceBusMessage, TransportType

from send_notification import NAMESPACE, TOPIC

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
CLIENT_ID = "7e2dcba0-2e52-4b1f-b715-f708b56a0211"


def response(data, status=200):
    return func.HttpResponse(json.dumps(data), status_code=status, mimetype="application/json")


@app.route(route="notification-test", methods=["GET", "POST"])
def notification_test(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "POST":
        try:
            options = req.get_json()
        except ValueError:
            return response({"error": 'Send requires JSON: {"send": true}'}, 400)
        if not isinstance(options, dict) or options.get("send") is not True:
            return response({"error": 'Send requires JSON: {"send": true}'}, 400)

    payload = json.loads((Path(__file__).parent / "in/test-notification.json").read_text())
    payload["context"]["eventTimestamp"] = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    message_id = str(uuid4())
    result = {"namespace": NAMESPACE, "topic": TOPIC, "messageId": message_id, "payload": payload}
    if req.method == "GET":
        return response({**result, "status": "preview", "note": "Nothing sent. POST generates a fresh timestamp and message ID."})

    try:
        with ManagedIdentityCredential(client_id=os.environ.get("SERVICE_BUS_MI_CLIENT_ID", CLIENT_ID)) as credential:
            with ServiceBusClient(NAMESPACE, credential, transport_type=TransportType.AmqpOverWebsocket,
                                  retry_total=0) as client:
                with client.get_topic_sender(topic_name=TOPIC) as sender:
                    sender.send_messages(ServiceBusMessage(json.dumps(payload), content_type="application/json",
                                                           message_id=message_id), timeout=30)
    except Exception as exc:
        logging.error("Notification send not confirmed: message_id=%s error_type=%s", message_id, type(exc).__name__)
        return response({**result, "status": "not_confirmed", "errorType": type(exc).__name__,
                         "note": "Check identity permissions and networking. Check message ID before retrying; delivery may be uncertain."}, 502)
    logging.info("Service Bus accepted notification message_id=%s topic=%s", message_id, TOPIC)
    return response({**result, "status": "accepted", "note": "Service Bus acceptance confirmed; Galaxy processing not verified."})
