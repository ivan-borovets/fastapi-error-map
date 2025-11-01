import nox


@nox.session(python=None)
@nox.parametrize("fastapi", ["0.100.0", "latest"])
def compatibility(session, fastapi):
    session.run("uv", "sync", "--locked", "--group", "test", "--active", external=True)

    if fastapi == "latest":
        session.run("uv", "add", "fastapi", "--active", external=True)
    else:
        session.run("uv", "add", f"fastapi=={fastapi}", "--active", external=True)

    session.run("uv", "run", "--active", "make", "code.test", external=True)
