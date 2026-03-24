import subprocess
import json

# 1Password system/meta fields that should never be used as JDBC credentials
_SKIP_LABELS = {
    "notesplain", "notes", "username", "account", "account[email]",
    "totp", "tags", "title", "url", "website",
}


def fetch_credentials(item_name):
    result = subprocess.run(
        ["op", "item", "get", item_name, "--format", "json"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"1Password CLI error: {result.stderr.strip()}")

    data = json.loads(result.stdout)

    creds = {}

    # Try parsing JDBC connection string from notes field first
    for field in data.get("fields", []):
        label = field.get("label", "")
        value = field.get("value", "")
        if label == "notesPlain" and value and "jdbc:" in value:
            creds = parse_jdbc_connection_string(value)
            return creds

    # Fallback: use labeled fields, skipping system/meta fields
    for field in data.get("fields", []):
        label = field.get("label", "")
        value = field.get("value", "")
        if label and value and label.lower() not in _SKIP_LABELS:
            creds[label] = value

    return creds


def parse_jdbc_connection_string(jdbc_str):
    """Parse a JDBC connection string into a dict of key=value pairs."""
    creds = {}
    # Remove the jdbc:driver: prefix
    parts = jdbc_str.strip().split(":", 2)
    if len(parts) >= 3:
        params_str = parts[2]
    else:
        params_str = jdbc_str

    for param in params_str.split(";"):
        param = param.strip()
        if "=" in param:
            key, value = param.split("=", 1)
            key = key.strip()
            if key and key not in ("AuthScheme",):
                creds[key] = value.strip()

    return creds
