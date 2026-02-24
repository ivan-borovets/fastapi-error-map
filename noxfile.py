import nox


@nox.session(python=None)
@nox.parametrize("fastapi", ["0.100.0", "latest"])
def compatibility(session, fastapi):
    session.run("uv", "sync", "--locked", "--group", "test", "--active", external=True)

    if fastapi == "latest":
        session.run("uv", "pip", "install", "--upgrade", "fastapi", external=True)
    else:
        session.run("uv", "pip", "install", f"fastapi=={fastapi}", external=True)

    session.run("uv", "run", "--no-sync", "--active", "make", "test", external=True)
