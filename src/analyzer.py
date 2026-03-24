def analyze(result):
    if "SUCCESS" in result:
        return "PASS"

    if "401" in result or "Unauthorized" in result:
        return "Invalid credentials (expected)"

    if "NullPointerException" in result:
        return "BUG: NullPointerException"

    return "CHECK"
