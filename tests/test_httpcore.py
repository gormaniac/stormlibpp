import os
import sys

import synapse.tests.utils as s_test

import stormlibpp


class TestHttpCore(s_test.SynTest):
    async def test_login(self):
        async with self.getTestCore(conf={"https:port": 4443}) as core:
            await core.addUser("test", passwd="test")

            async with stormlibpp.HttpCortex(
                "https://127.0.0.1:4443", ssl_verify=False, usr="test", pwd="test"
            ) as hcore:
                return

    async def test_storm(self):
        async with self.getTestCore(conf={"https:port": 4443}) as core:
            await core.addUser("test", passwd="test")

            async with stormlibpp.HttpCortex(
                "https://127.0.0.1:4443", ssl_verify=False, usr="test", pwd="test"
            ) as hcore:
                msgs = []
                async for msg in hcore.storm("help"):
                    msgs.append(msg)
                print(msgs)
                self.stormHasNoWarnErr(msgs)
