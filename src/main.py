import argparse
import jpype
from driver_inspector import start_jvm, discover_driver_class, get_auth_schemes
from credential_fetcher import fetch_credentials
from test_case_generator import generate_cases_with_ai
from executor import test_connection
from analyzer import analyze
from report import print_report, export_excel_report


def build_jdbc_url(driver, scheme, creds):
    base = f"jdbc:{driver}:AuthScheme={scheme};"
    for k, v in creds.items():
        base += f"{k}={v};"
    return base


# OAuth-specific fields that should NOT be used with non-OAuth schemes
OAUTH_FIELDS = {
    "initiateoauth", "oauthclientid", "oauthclientsecret",
    "oauthaccesstoken", "oauthrefreshtoken", "oauthsettingslocation",
    "oauthcallbackurl", "oauthverifier", "oauthexpiresin",
    "oauthgranttype", "oauthtokenurl", "oauthauthorizationurl",
}

# Basic-auth-specific fields that should NOT be used with OAuth schemes
BASIC_FIELDS = {
    "apitoken", "apikey", "password", "user", "username",
}

# Infrastructure/proxy fields — never include in auth test mutations
INFRA_FIELDS = {
    "proxyserver", "proxyport", "proxyuser", "proxypassword", "proxyauthscheme",
    "proxyssltype", "sslservercert", "sslclientcert", "sslclientcertpassword",
    "sslclientcertsubject", "sslclientcerttype", "firewalltype", "firewallserver",
    "firewallport", "firewalluser", "firewallpassword", "logfile", "verbosity",
    "logmodules", "maxlogfilesize", "maxlogfilecount", "location", "other",
}


def filter_creds_for_scheme(creds, scheme):
    """Return only the credentials relevant to the given auth scheme."""
    scheme_lower = scheme.lower()
    filtered = {}

    for key, value in creds.items():
        key_lower = key.lower()

        # Always exclude infrastructure/proxy fields
        if key_lower in INFRA_FIELDS:
            continue

        if "oauth" in scheme_lower:
            # OAuth scheme: exclude basic-only fields
            if key_lower not in BASIC_FIELDS:
                filtered[key] = value
        else:
            # Non-OAuth scheme (Basic, etc.): exclude OAuth fields
            if key_lower not in OAUTH_FIELDS:
                filtered[key] = value

    return filtered


def main():
    parser = argparse.ArgumentParser(description="CData Auth Testing Framework")
    parser.add_argument("--driver", required=True, help="Driver name (e.g. shopify)")
    parser.add_argument("--creds", help="1Password item name for credentials")
    parser.add_argument("--limit", type=int, default=25, help="Max test cases per scheme")
    args = parser.parse_args()

    driver = args.driver.lower()
    jar_path = rf"C:\Program Files\CData\CData JDBC Driver for {driver.capitalize()} 2025\lib\cdata.jdbc.{driver}.jar"

    print(f"[*] Starting JVM with {jar_path}...")
    start_jvm(jar_path)

    driver_class_name = discover_driver_class()
    print(f"[+] Auto-discovered driver class: {driver_class_name}")
    driver_class = jpype.JClass(driver_class_name)

    print("[*] Discovering auth schemes...")
    schemes = get_auth_schemes(driver_class)
    print(f"[+] Found schemes: {schemes}")

    results = []

    creds_item = args.creds or f"{driver}_creds"
    base_creds = fetch_credentials(creds_item)
    print(f"[+] Loaded credentials from 1Password item: {creds_item}")
    print(f"[+] Credential keys: {list(base_creds.keys())}")

    for scheme in schemes:
        print(f"\n[*] Testing scheme: {scheme}")

        creds = filter_creds_for_scheme(base_creds, scheme)
        print(f"    Filtered keys for {scheme}: {list(creds.keys())}")
        cases = generate_cases_with_ai(creds, scheme, driver, limit=args.limit)

        for i, case in enumerate(cases, 1):
            jdbc_url = build_jdbc_url(driver, scheme, case["creds"])
            result = test_connection(jdbc_url, {})
            analysis = analyze(result)

            error_msg = "" if result == "SUCCESS" else result
            comment = ""
            if analysis == "PASS" and case["label"] != "Valid credentials (baseline)":
                comment = "Driver accepted mutated input — verify if expected"
            elif "BUG" in analysis:
                comment = "Potential bug — needs investigation"

            results.append({
                "scheme": scheme,
                "test_case": case["label"],
                "connection_string": jdbc_url,
                "pass_fail": "PASS" if analysis == "PASS" else "FAIL",
                "error_message": error_msg,
                "analysis": analysis,
                "comment": comment,
            })

            print(f"  [{i}/{len(cases)}] {analysis}")

    print_report(results)
    export_excel_report(results, driver)


if __name__ == "__main__":
    main()
