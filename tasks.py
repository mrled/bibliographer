from invoke import task


@task
def cog(ctx):
    """Run cog -r readme.md using the cogapp API."""

    ctx.run("cog -r readme.md")


@task
def mypy(ctx):
    """Run mypy on the src directory."""

    ctx.run("mypy src")


@task
def release(ctx, version=None, primary="main"):
    """Update the version in pyproject.toml, tag the release, and push the tag.

    Set the version to the specified version or increment the patch version by 1.

    Only allow the release to happen on the primary branch.
    """

    # Fail if there are uncommitted changes
    ctx.run("git diff --exit-code")

    # Fail if not on the primary branch
    branch = ctx.run("git branch --show-current", hide=True).stdout.strip()
    if branch != primary:
        raise Exception(f"Not on the primary branch '{primary}'")

    # Update the version in pyproject.toml
    with open("pyproject.toml") as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if line.startswith("version"):
            if version:
                lines[i] = f'version = "{version}"\n'
            else:
                version = line.split("=")[1].strip().strip('"')
                version = version.split(".")
                version[-1] = str(int(version[-1]) + 1)
                version = ".".join(version)
                lines[i] = f'version = "{version}"\n'
            break
    with open("pyproject.toml", "w") as f:
        f.writelines(lines)

    # Commit the change
    ctx.run(f"git add pyproject.toml")
    ctx.run(f'git commit -m "Update version to {version}"')

    # Tag the release
    ctx.run(f"git tag -a v{version} -m 'Version {version}'")

    # Push the tag and primary branch
    ctx.run(f"git push origin {primary} v{version}")
