import os
import sys

from setuptools import Extension, setup

# Builds the futex-based extension on Linux only when explicitly enabled
# My tests show that it brings no practical performance value and is more brittle.
extensions = []

if sys.platform.startswith("linux") and os.environ.get("USE_FUTEX"):
    extensions.append(
        Extension(
            name="shm_rpc_bridge._internal.linux_futex",
            sources=["src/shm_rpc_bridge/_internal/linux_futex.c"],
            define_macros=[("_GNU_SOURCE", "1")],
            extra_compile_args=["-O3", "-std=c11", "-Wall", "-Wextra"],
        )
    )

# setuptools will read most configuration from pyproject.toml
setup(
    ext_modules=extensions,
)
