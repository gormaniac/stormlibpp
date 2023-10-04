"""Start a temporary Synapse Cortex for testing purposes."""


import asyncio
import contextlib
import sys
from typing import Iterable

import synapse.common as s_common
import synapse.cortex as s_cortex


MAIN_HELP = """
Start a temporary local Cortex.
The HTTP API is enabled on port 4443.
A user is created with the creds test:test.
"""


@contextlib.asynccontextmanager
async def getTempCortexWithArgs(
    mods: Iterable | None = None,
    conf: dict | None = None,
    user: str = "test",
    password: str = "test",
    print_dir: bool = True,
):
    with s_common.getTempDir() as dirn:
        async with await s_cortex.Cortex.anit(dirn, conf=conf) as core:
            if print_dir:
                print(f"Started a temporary Cortex from {dirn}")
            if mods:
                for mod in mods:
                    await core.loadCoreModule(mod)

            await core.addUser(user, passwd=password)

            async with core.getLocalProxy() as prox:
                yield prox


async def main():
    if "-h" in sys.argv or "--help" in sys.argv:
        print(MAIN_HELP)
        sys.exit()

    async with getTempCortexWithArgs(conf={"https:port": 4443}) as proxy:
        try:
            while True:
                pass
        except Exception as err:
            raise err


if __name__ == "__main__":
    asyncio.run(main())
