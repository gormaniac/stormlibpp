"""Tests for stormlibpp.node."""


import stormlibpp

import synapse.tests.utils as s_test
import synapse.lib.cell as s_cell
import synapse.lib.stormsvc as s_stormsvc


PACKED_NODE = (('it:app:yara:rule', '5d0292d99a7da59a3a119e193f140143'), {'iden': '57ce731580ed6976b608e87dfc7f2ece81790f2cb8cdaf958013c738b28cd56e', 'tags': {'test': (None, None), 'test.tag': (None, None)}, 'props': {'.created': 1687720565352, 'text': 'rule dummy { condition: true }', 'name': 'dummy', 'enabled': 1}, 'tagprops': {}, 'nodedata': {}})


TEST_STORM_CODE = """
$lib.print(test1)
$testsvc = $lib.service.get(test.storm.svc)
yield { [ inet:fqdn=google.com ] }
$lib.print(test)

$retn = $testsvc.testCall($node)
$lib.print($retn)
"""

stormlibpp.utils.chk_storm_syntax(TEST_STORM_CODE)

PKG_DEF = (
    {
        "name": "test.storm.svc",
        "version": (0, 0, 1),
        "synapse_minversion": [2, 135, 0],
        "commands": (
            {
                'name': f'test.storm.svc.cmd',
                'descr': "A test command",
                'storm': TEST_STORM_CODE,
            },
        ),
    }
)


class NodeTestCellApi(s_cell.CellApi, s_stormsvc.StormSvc):
    _storm_svc_name = "test.storm.svc"
    _storm_svc_vers = "0.0.1"
    _storm_svc_evts = "a64249b397e1dbbdfe073f5ac5eea50c"
    _storm_svc_pkgs = PKG_DEF

    async def testCall(self, node):
        return await self.cell.testCall(node)


class NodeTestCell(s_cell.Cell):
    cellapi = NodeTestCellApi

    async def testCall(self, node):
        storm_node = stormlibpp.node.StormNode.unpack(node)
        breakpoint()
        print(storm_node)
        return storm_node.pack()

class TestNode:

    def test_packing(self):
        node = stormlibpp.StormNode.unpack(PACKED_NODE)
        assert node.pack() == PACKED_NODE

    def test_add_tags(self):
        tags = ["#test.othertag", "#atag"]
        node = stormlibpp.StormNode.unpack(PACKED_NODE)
        node.addTags(tags)

        for tag in tags:
            assert tag in node.tags

        assert dir(node.tags) == [item[0] for item in iter(node.tags)]

    def test_add_props(self):
        props = {'prop': 'test', 'other': 'value'}
        node = stormlibpp.StormNode.unpack(PACKED_NODE)
        node.addProps(props)

        for prop in props:
            assert prop in node.props

        for propname, propval in node.props:
            if propname in props:
                assert props[propname] == propval

    def test_values(self):
        node = stormlibpp.StormNode.unpack(PACKED_NODE)

        assert node.form == PACKED_NODE[0][0]
        assert node.value == PACKED_NODE[0][1]
        assert node.nodevals == PACKED_NODE[1]
        assert node.iden == PACKED_NODE[1].get("iden", "")

# class TestNodeStorm(s_test.SynTest):
# 
#     async def test_svc_starts(self):
#         print("out")
#         async with self.getTestCore() as core:
#             core.conf['storm:log'] = True
#             core.stormlog = True
#             with self.getTestDir() as dirn:
#                 async with await NodeTestCell.anit(dirn, conf={}) as svc:
#                     svc.dmon.share('svc', svc)
#                     root = await svc.auth.getUserByName('root')
#                     await root.setPasswd('root')
#                     info = await svc.dmon.listen('tcp://127.0.0.1:0/')
#                     svc.dmon.test_addr = info
#                     host, port = info
#                     surl = f'tcp://root:root@127.0.0.1:{port}/svc'
#                     await self.runCoreNodes(core, f'service.add test.storm.svc {surl}')
# 
#                     msgs = await core.callStorm(TEST_STORM_CODE)
#                     breakpoint()
#                     print(msgs)
#                     self.stormHasNoErr(msgs)

