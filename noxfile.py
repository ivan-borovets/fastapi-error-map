import nox

PYTHON_SUPPORT_VERSIONS = ("3.9", "3.10", "3.11", "3.12", "3.13", "3.14")


@nox.session(python=PYTHON_SUPPORT_VERSIONS)
@nox.parametrize("fastapi", ("0.100.0", "latest"))
def compatibility(session, fastapi):
    """
    Examples:
        run all versions python and fastapi
        nox

        run python and fastapi versions
        nox -s compatibility -p 3.14 -- fastapi=latest
    """
    session.run("uv", "sync", "--locked", "--group", "test", "--active", external=True)

    if fastapi == "latest":
        session.run("uv", "add", "fastapi", "--active", external=True)
    else:
        session.run("uv", "add", f"fastapi=={fastapi}", "--active", external=True)

    session.run("uv", "run", "--active", "make", "code.test", external=True)
