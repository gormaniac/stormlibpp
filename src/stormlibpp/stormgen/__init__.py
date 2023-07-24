"""stormgen helps analysts generate Synapse nodes from Markdown documentation.

TODO - Put a long docstring here so it gets include in docs
"""


import marko


from .. import StormNode


class Element:
    """An element is a unit of processable information found in a StormGenDoc.

    Multiple elements may be in a Section. Elements may contain child Elements.
    Elements are broken up by Markdown headings.
    """


class Section:
    """All Markdown tokens between two headings of the same level."""


class StormGenDoc:
    """A Markdown document that is ready for processing with stormgen.

    It contains a list of all ``Section``s in a document, in order of appearance.

    It also stores the raw AST parsed by marko_.

    _marko: https://pypi.org/project/marko/
    """

    def __init__(self, text: str) -> None:
        self.ast = marko.parse(text)
        self.sections = self.get_sections(self.ast)
        self.elements = self.get_elements()
        self.node_elements = self.get_node_elements()

    def get_sections(self) -> list[Section]:
        pass

    def get_elements(self) -> list[Element]:
        pass

    # TODO - Do we really need this?
    def get_node_elements(self) -> list[Element]:
        pass


def parse(text: str) -> StormGenDoc:
    return StormGenDoc(text)

def convert(doc: StormGenDoc) -> list[StormNode]:
    pass

def export(nodes: list[StormNode]):
    pass
