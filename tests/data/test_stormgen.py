"""Optional manual inspection of the canonical Stormgen fixture."""

from pathlib import Path

import stormlibpp.stormgen as stormgen


def main():
    doc = stormgen.parse(Path(__file__).with_name("stormgen-example.md").read_text())
    for node in stormgen.extract(doc):
        node.extract()
        print(node, node.props, node.tags, node.edges)


if __name__ == "__main__":
    main()
