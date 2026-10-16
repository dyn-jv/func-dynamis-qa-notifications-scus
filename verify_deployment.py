"""Check the deployed tester; optionally send once. Function keys stay in memory."""
import argparse
import json
import subprocess
import urllib.error
import urllib.request

SUBSCRIPTION = "835baf64-0f24-4ca2-8e65-5bcfdbb98978"
APP = "func-dynamis-qa-notifications-scus"
GROUP = "DynamisPS"


def az_json(arguments):
    result = subprocess.run(["az", *arguments, "--subscription", SUBSCRIPTION,
                             "--resource-group", GROUP, "--name", APP, "-o", "json"],
                            capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("Azure CLI lookup failed; verify your login and Function App access.")
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--send", action="store_true")
    args = parser.parse_args()
    app = az_json(["functionapp", "show"])
    host = app.get("defaultHostName") or app["properties"]["defaultHostName"]
    url = f"https://{host}/api/notification-test"
    # An unauthenticated call must never run the function.
    try:
        urllib.request.urlopen(url, timeout=60)
    except urllib.error.HTTPError as exc:
        if exc.code not in (401, 403):
            raise RuntimeError(f"Unexpected unauthenticated HTTP status: {exc.code}") from None
        print(f"Unauthenticated request rejected: HTTP {exc.code}")
    else:
        raise RuntimeError("Endpoint did not reject an unauthenticated request")

    keys = az_json(["functionapp", "function", "keys", "list", "--function-name", "notification_test"])
    key = keys.get("default") or next(iter(keys.values()), None)
    if not isinstance(key, str):
        raise RuntimeError("No function-specific key available")
    headers = {"x-functions-key": key, "Content-Type": "application/json"}
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as reply:
        preview = json.load(reply)
    if preview.get("status") != "preview":
        raise RuntimeError("Preview did not return the expected response")
    print(json.dumps(preview, indent=2))
    if args.send:
        request = urllib.request.Request(url, data=b'{"send":true}', headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=120) as reply:
                result = json.load(reply)
        except urllib.error.HTTPError as exc:
            print(exc.read().decode())
            raise SystemExit("Test send failed; no automatic retry performed.")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
