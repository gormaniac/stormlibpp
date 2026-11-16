import os

import synapse.tests.utils as s_test

from ... import DIRNAME

class UtilsTest(s_test.StormPkgTest):

    pkgprotos = (os.path.join(DIRNAME, 'src/pkgs/utils/utils.yaml'),)

    async def test_getUserOrSystemOpt(self):

        async with self.getTestCore() as core:

            # Test that we can get a user config option
            resp = await core.callStorm('''
                $lib.user.vars.set("slib:utils:testopt", "uservalue")
                $lib.globals.set("slib:utils:testopt", "systemvalue")
                $val = $lib.import(slib.utils).getUserOrSystemOpt("slib:utils:testopt")
                return($val)
            ''')
            self.assertEqual(resp, 'uservalue')

            # Test that we can get a system config option if no user option is set
            resp = await core.callStorm('''
                $lib.user.vars.pop("slib:utils:testopt")
                $val = $lib.import(slib.utils).getUserOrSystemOpt("slib:utils:testopt")
                return($val)
            ''')
            self.assertEqual(resp, 'systemvalue')

            resp = await core.callStorm('''
                $lib.globals.pop("slib:utils:testopt")
                $val = $lib.import(slib.utils).getUserOrSystemOpt("slib:utils:testopt")
                return($val)
            ''')
            self.assertEqual(resp, 'null')
