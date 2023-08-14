"""Start a temporary Synapse Cortex for testing purposes."""


import asyncio
import contextlib

import synapse.common as s_common
import synapse.cortex as s_cortex


@contextlib.asynccontextmanager
async def getTempCortexWithArgs(mods = None, conf = None, user="test", password="test"):

    with s_common.getTempDir() as dirn:

        async with await s_cortex.Cortex.anit(dirn, conf=conf) as core:
            if mods:
                for mod in mods:
                    await core.loadCoreModule(mod)

            await core.addUser(user, passwd=password)

            async with core.getLocalProxy() as prox:
                yield prox


async def main():
    async with getTempCortexWithArgs(conf={"https:port": 4443}) as proxy:
        try:
            while True:
                pass
        except Exception as err:
            raise err


if __name__ == "__main__":
    asyncio.run(main())
