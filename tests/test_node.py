"""Tests for stormlibpp.node."""


import stormlibpp


PACKED_NODE = (('it:app:yara:rule', '5d0292d99a7da59a3a119e193f140143'), {'iden': '57ce731580ed6976b608e87dfc7f2ece81790f2cb8cdaf958013c738b28cd56e', 'tags': {'test': (None, None), 'test.tag': (None, None)}, 'props': {'.created': 1687720565352, 'text': 'rule dummy { condition: true }', 'name': 'dummy', 'enabled': 1}, 'tagprops': {}, 'nodedata': {}})


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
