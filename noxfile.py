import nox


@nox.session(python=None)
@nox.parametrize("fastapi", ["0.100.0", "latest"])
def compatibility(session, fastapi):
    if fastapi == "latest":
        session.run("uv", "pip", "install", "fastapi", external=True)
    else:
        session.run("uv", "pip", "install", f"fastapi=={fastapi}", external=True)

    session.run("uv", "pip", "install", "-e", ".[test]", external=True)
    session.run("make", "code.test", external=True)
