from invoke import task


@task
def cog(ctx):
    """Run cog -r readme.md using the cogapp API."""

    ctx.run("cog -r readme.md")
