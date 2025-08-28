import contextlib
import os
import warnings


def ENV_BOOL(env_name, default):
    val = os.environ.get(env_name, default)

    if not val:
        return default

    if val == "True" or val:
        return True

    if val == "False" or not val:
        return False

    warnings.warn("Variable %s is not boolean. It is %s", env_name, val)


def ENV_STR(env_name, default):
    val = os.environ.get(env_name, default)

    if not val:
        return default

    return val


def ENV_INT(env_name, default):
    val = os.environ.get(env_name, default)

    if not val:
        return default

    return int(val)


def print_finmars():
    text = """
███████╗    ██╗    ███╗   ██╗    ███╗   ███╗     █████╗     ██████╗     ███████╗
██╔════╝    ██║    ████╗  ██║    ████╗ ████║    ██╔══██╗    ██╔══██╗    ██╔════╝
█████╗      ██║    ██╔██╗ ██║    ██╔████╔██║    ███████║    ██████╔╝    ███████╗
██╔══╝      ██║    ██║╚██╗██║    ██║╚██╔╝██║    ██╔══██║    ██╔══██╗    ╚════██║
██║         ██║    ██║ ╚████║    ██║ ╚═╝ ██║    ██║  ██║    ██║  ██║    ███████║
╚═╝         ╚═╝    ╚═╝  ╚═══╝    ╚═╝     ╚═╝    ╚═╝  ╚═╝    ╚═╝  ╚═╝    ╚══════╝
    """

    print(text)


def filter_sentry_events(event, hint):
    with contextlib.suppress(Exception):
        frames = event["exception"]["values"][0]["stacktrace"]["frames"]
        for i, frame in enumerate(frames):
            if frame["function"] == "execute_workflow_step" and len(frames) > i + 1:
                #  do not report exceptions raised in custom modules
                return None
    return event
