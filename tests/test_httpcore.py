import synapse.tests.utils as s_test

import stormlibpp


class TestHttpCore(s_test.SynTest):
    async def test_login(self):
        async with self.getTestCore(conf={"https:port": 4443}) as core:
            await core.addUser("test", passwd="test")

            async with stormlibpp.HttpCortex(
                "https://127.0.0.1:4443", ssl_verify=False, usr="test", pwd="test"
            ) as hcore:
                assert hcore.sess.cookie_jar._cookies != {}

    async def test_callStorm(self):
        async with self.getTestCore(conf={"https:port": 4443}) as core:
            await core.addUser("test", passwd="test")

            async with stormlibpp.HttpCortex(
                "https://127.0.0.1:4443", ssl_verify=False, usr="test", pwd="test"
            ) as hcore:
                retn = await hcore.callStorm("return('test')")
                assert retn["result"] == "test"

    async def test_storm(self):
        async with self.getTestCore(conf={"https:port": 4443}) as core:
            await core.addUser("test", passwd="test")

            async with stormlibpp.HttpCortex(
                "https://127.0.0.1:4443", ssl_verify=False, usr="test", pwd="test"
            ) as hcore:
                msgs = []
                async for msg in hcore.storm("help"):
                    msgs.append(msg)
                self.stormHasNoWarnErr(msgs)
