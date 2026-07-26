import os

import synapse.tests.utils as s_test

from ... import DIRNAME

class IpInfoTest(s_test.StormPkgTest):

    assetdir = os.path.join(DIRNAME, 'tests/pkgs/testassets')
    pkgprotos = (
        os.path.join(DIRNAME, 'src/pkgs/ipinfo/ipinfo.yaml'),
        os.path.join(DIRNAME, 'src/pkgs/utils/utils.yaml'),
    )

    # TODO - build tests for the commands/mocked queries

    async def test_ipinfo_lib_ingestIpInfo_4_full(self):

        async with self.getTestCore() as core:

            example_ip4_full = {
                "ip": "8.8.8.8",
                "asn": "AS15169",
                "as_name": "Google LLC",
                "as_domain": "google.com",
                "country_code": "US",
                "country": "United States",
                "continent_code": "NA",
                "continent": "North America"
            }

            msgs = await core.stormlist(
                '''yield $lib.import(slib.ipinfo.lib).ingestIpInfo($data, $query)''',
                {'vars': {'data': example_ip4_full, 'query': '8.8.8.8'}}
            )

            assert len([m[1] for m in msgs if m[0] == 'node']) == 1
            node = [m[1] for m in msgs if m[0] == 'node'][0]
            assert node[0][0] == 'inet:ipv4'
            assert node[1]['props']['asn'] == 15169

            asnNode = await core.getNodeByNdef(('inet:asn', '15169'))
            assert asnNode is not None
            assert isinstance(asnNode.props['owner'], str)

            orgNode = await core.getNodeByNdef(('ou:org', asnNode.props['owner']))
            assert orgNode is not None
            assert orgNode.props['name'] == "google llc"


    async def test_ipinfo_lib_ingestIpInfo_6_full(self):

        async with self.getTestCore() as core:

            example_ip6_full = {
                "ip": "2001:4860:4860::8888",
                "asn": "AS15169",
                "as_name": "Google LLC",
                "as_domain": "google.com",
                "country_code": "US",
                "country": "United States",
                "continent_code": "NA",
                "continent": "North America"
            }

            msgs = await core.stormlist(
                '''yield $lib.import(slib.ipinfo.lib).ingestIpInfo($data, $query)''',
                {'vars': {'data': example_ip6_full, 'query': '2001:4860:4860::8888'}}
            )

            assert len([m[1] for m in msgs if m[0] == 'node']) == 1
            node = [m[1] for m in msgs if m[0] == 'node'][0]
            assert node[0][0] == 'inet:ipv6'
            assert node[1]['props']['asn'] == 15169

            asnNode = await core.getNodeByNdef(('inet:asn', '15169'))
            assert asnNode is not None
            assert isinstance(asnNode.props['owner'], str)

            orgNode = await core.getNodeByNdef(('ou:org', asnNode.props['owner']))
            assert orgNode is not None
            assert orgNode.props['name'] == "google llc"


    async def test_ipinfo_lib_ingestIpInfo_4_partial(self):

        async with self.getTestCore() as core:

            example_ip4_partial = {
                "ip": "8.8.8.8",
                "asn": "AS15169",
                "as_name": "",
                "as_domain": "",
                "country_code": "US",
                "country": "United States",
                "continent_code": "NA",
                "continent": "North America"
            }

            msgs = await core.stormlist(
                '''yield $lib.import(slib.ipinfo.lib).ingestIpInfo($data, $query)''',
                {'vars': {'data': example_ip4_partial, 'query': '8.8.8.8'}}
            )

            assert len([m[1] for m in msgs if m[0] == 'node']) == 1
            node = [m[1] for m in msgs if m[0] == 'node'][0]
            assert node[0][0] == 'inet:ipv4'
            assert node[1]['props']['asn'] == 15169

            asnNode = await core.getNodeByNdef(('inet:asn', '15169'))
            assert asnNode is not None
            assert isinstance(asnNode.props['owner'], str)

            orgNode = await core.getNodeByNdef(('ou:org', asnNode.props['owner']))
            assert orgNode is not None
            assert orgNode.props.get('name') == ""