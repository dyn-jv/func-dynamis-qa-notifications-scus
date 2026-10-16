import json
import unittest
from unittest.mock import patch

import azure.functions as func
import function_app as module


class TesterTests(unittest.TestCase):
    def request(self, method="GET", body=b""):
        return func.HttpRequest(method, "https://example/api/notification-test", body=body)

    @patch.object(module, "ManagedIdentityCredential")
    def test_preview_never_authenticates(self, credential):
        result = module.notification_test(self.request())
        data = json.loads(result.get_body())
        self.assertEqual(data["status"], "preview")
        self.assertEqual(data["payload"]["telemetry"]["status"], 0)
        credential.assert_not_called()

    @patch.object(module, "ManagedIdentityCredential")
    def test_invalid_posts_never_authenticate(self, credential):
        for body in [b"", b"{}", b'{"send": "true"}', b"[]"]:
            self.assertEqual(module.notification_test(self.request("POST", body)).status_code, 400)
        credential.assert_not_called()

    @patch.object(module, "ServiceBusClient")
    @patch.object(module, "ManagedIdentityCredential")
    def test_send_once_using_designated_identity(self, credential, client):
        result = module.notification_test(self.request("POST", b'{"send":true}'))
        self.assertEqual(json.loads(result.get_body())["status"], "accepted")
        credential.assert_called_once_with(client_id=module.CLIENT_ID)
        sender = client.return_value.__enter__.return_value.get_topic_sender.return_value.__enter__.return_value
        sender.send_messages.assert_called_once()

    @patch.object(module, "ManagedIdentityCredential", side_effect=RuntimeError("secret-detail"))
    def test_failure_is_not_reported_as_success_or_exposes_exception(self, credential):
        result = module.notification_test(self.request("POST", b'{"send":true}'))
        self.assertEqual(result.status_code, 502)
        self.assertNotIn(b"secret-detail", result.get_body())
        self.assertEqual(json.loads(result.get_body())["status"], "not_confirmed")


if __name__ == "__main__":
    unittest.main()
