from __future__ import annotations

import contextlib
import subprocess as sp
import tempfile
import textwrap
from pathlib import Path

import pytest
from kraken.core.project import Project
from kraken.testing import kraken_execute

from kraken.std.docker import build_docker_image
from kraken.std.generic.render_file import render_file


@pytest.mark.parametrize("backend", ["kaniko"])
def test__secrets_can_be_accessed_at_build_time_and_are_not_present_in_the_final_image(
    kraken_project: Project,
    backend: str,
) -> None:
    """Tests that secret file mounts work as expected, i.e. they can be read from `/run/secrets` and they
    do not make it into the final image."""

    secret_name = "MY_SECRET"
    secret_path = f"/run/secrets/{secret_name}"

    dockerfile_content = textwrap.dedent(
        f"""
        FROM alpine:latest
        RUN cat {secret_path}
        """
    )

    image_tag = "kraken-integration-tests/test-secrets:latest"

    with tempfile.TemporaryDirectory() as tempdir, contextlib.ExitStack() as exit_stack:
        kraken_project.directory = Path(tempdir)

        dockerfile = render_file(
            project=kraken_project,
            file=kraken_project.build_directory / "Dockerfile",
            content=dockerfile_content,
        )

        build_docker_image(
            name="buildDocker",
            dockerfile=dockerfile.file,
            secrets={secret_name: "Hello, World!"},
            cache=False,
            tags=[image_tag],
            load=True,
            backend=backend,
        )

        kraken_execute(kraken_project.context, ":buildDocker")

        exit_stack.callback(lambda: sp.check_call(["docker", "rmi", image_tag]))

        command = ["sh", "-c", f"find {secret_path} 2>/dev/null || true"]
        output = sp.check_output(["docker", "run", "--rm", image_tag] + command).decode().strip()
        assert output == ""
