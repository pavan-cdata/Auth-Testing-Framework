import jpype
import jpype.imports


def start_jvm(jar_path):
    if not jpype.isJVMStarted():
        jpype.startJVM(classpath=[jar_path])


def get_auth_schemes(driver_class):
    driver = driver_class()
    props = driver.getPropertyInfo("", None)

    for p in props:
        if str(p.name).lower() == "authscheme":
            return [str(c) for c in p.choices]

    return []
