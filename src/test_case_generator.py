import json
import os
import httpx
from groq import Groq


def _get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY environment variable not set")
    http_client = httpx.Client(verify=False)
    return Groq(api_key=api_key, http_client=http_client)


def generate_cases_with_ai(valid_creds, scheme, driver, limit=25):
    """Ask Groq AI to generate intelligent, scheme-aware test cases."""
    client = _get_groq_client()

    cred_keys = list(valid_creds.keys())

    prompt = f"""You are a QA engineer testing JDBC authentication for the CData {driver.capitalize()} driver.

Auth Scheme: {scheme}
Available credential fields: {json.dumps(cred_keys)}

Generate exactly {limit} test cases for this auth scheme. Each test case should modify the credentials to test a specific scenario.

Rules:
- Test case 1 MUST be "Valid credentials (baseline)" with ALL fields unchanged.
- For each field, create meaningful test mutations:
  - Missing a required field (remove it entirely)
  - Invalid value for a field (e.g. wrong format, expired token, bad URL)
  - Empty string value for a field
- Think about what each field actually means for {scheme} auth:
  - For OAuth: OAuthClientId and OAuthClientSecret are critical, InitiateOAuth controls the flow
  - For Basic: credentials like APIKey or password are critical
  - CompanyDomain should be a valid URL
  - Schema is typically a data source identifier
- Add edge cases specific to {scheme}:
  - For OAuth: test with InitiateOAuth=OFF, test with swapped client ID/secret
  - For Basic: test with special characters in credentials
- Do NOT include any proxy, SSL, firewall, or logging fields in mutations.
- Each test case must have a clear, descriptive label explaining what is being tested.

Return ONLY valid JSON array. Each element must be:
{{"label": "descriptive test case name", "mutations": {{"field_name": "new_value_or_null"}}}}

Use null to indicate the field should be removed entirely.
Use "" (empty string) for empty value tests.
Return raw JSON only, no markdown, no explanation."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=4000,
    )

    raw = response.choices[0].message.content.strip()

    # Clean markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    try:
        ai_cases = json.loads(raw)
    except json.JSONDecodeError:
        print("[!] Groq returned invalid JSON, falling back to basic generator")
        return _fallback_generate(valid_creds, limit)

    cases = []
    for tc in ai_cases[:limit]:
        label = tc.get("label", "Unknown test case")
        mutations = tc.get("mutations", {})

        creds = valid_creds.copy()
        for field, value in mutations.items():
            if value is None:
                creds.pop(field, None)
            else:
                creds[field] = value

        cases.append({"label": label, "creds": creds})

    return cases


def _fallback_generate(valid_creds, limit=25):
    """Simple fallback if Groq is unavailable."""
    cases = []

    cases.append({"label": "Valid credentials (baseline)", "creds": valid_creds.copy()})

    for key in valid_creds:
        case = valid_creds.copy()
        case.pop(key)
        cases.append({"label": f"Missing field: {key}", "creds": case})

    for key in valid_creds:
        case = valid_creds.copy()
        case[key] = "invalid"
        cases.append({"label": f"Invalid value for: {key}", "creds": case})

    for key in valid_creds:
        case = valid_creds.copy()
        case[key] = ""
        cases.append({"label": f"Empty value for: {key}", "creds": case})

    return cases[:limit]
