import jpype


def test_connection(jdbc_url, props):
    try:
        DriverManager = jpype.JClass("java.sql.DriverManager")
        Properties = jpype.JClass("java.util.Properties")

        java_props = Properties()
        for k, v in props.items():
            java_props.setProperty(str(k), str(v))

        conn = DriverManager.getConnection(jdbc_url, java_props)

        stmt = conn.createStatement()
        stmt.execute("SELECT 1")
        conn.close()

        return "SUCCESS"

    except Exception as e:
        return str(e)
