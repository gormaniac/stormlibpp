import stormlibpp.stormgen

fd = open("../tests/data/stormgen-example.md", "r")
text = fd.read()
fd.close()

sdoc = stormlibpp.stormgen.StormGenDoc(text)
sdoc.parse()
extractor = stormlibpp.stormgen.DocExtractor(sdoc)
nodes = extractor.extract()
for node in nodes:
    node.extract()
    print(node, node.parts)

n = nodes[0]
n.props
