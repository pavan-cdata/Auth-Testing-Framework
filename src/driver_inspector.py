import jpype
import jpype.imports


def start_jvm(jar_path):
    if not jpype.isJVMStarted():
        jpype.startJVM(classpath=[jar_path])


def discover_driver_class():
    """Auto-discover the JDBC Driver class from the loaded JAR via ServiceLoader."""
    ServiceLoader = jpype.JClass("java.util.ServiceLoader")
    DriverInterface = jpype.JClass("java.sql.Driver")
    for driver in ServiceLoader.load(DriverInterface):
        return str(driver.getClass().getName())
    raise RuntimeError("No JDBC Driver found in JAR via ServiceLoader")


def get_auth_schemes(driver_class):
    driver = driver_class()
    props = driver.getPropertyInfo("", None)

    for p in props:
        if str(p.name).lower() == "authscheme":
            return [str(c) for c in p.choices]

    return []
