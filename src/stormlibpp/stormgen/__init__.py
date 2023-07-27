"""stormgen helps analysts generate Synapse nodes from Markdown documentation.

TODO - Put a long docstring here so it gets include in docs
"""


import marko


from .. import StormNode


class Part:
    """An element is all blocks between any two headings."""

    def __init__(self, heading: marko.block.Heading) -> None:
        self.heading = heading
        self.blocks: list[marko.block.BlockElement] = []
        self.children = []

    def add_block(self, block: marko.block.BlockElement):
        self.blocks.append(block)


class Section:
    """All Markdown tokens between two headings of the same level.
    
    ``Section``s are organized into a list of ``Part``s. Each part
    is all content between two headings including the first heading.

    A "root section" is a ``Section`` that exists because there is no top level
    heading in the original Markdown document. This section cannot have a level
    because there is no heading, so ``level`` will equal 0.

    A root section is created when no ``heading`` is passed to the constructor.
    """

    def __init__(self, heading: marko.block.Heading | None = None) -> None:
        self.heading = heading
        self.cur = Part(self.heading)
        self.level = 0
        self.parts: list[Part] = [self.cur]

        self.root = True if heading is None else False
        """The root section holds all blocks that exists before any headings."""

        if not self.root:
            self.level = heading.level

    def add_part(self, heading: marko.block.Heading):
        # The first part will always be in the list.
        if self.cur not in self.parts:
            self.parts.append(self.cur)
        self.cur = Part(heading)

    def add_block(self, block: marko.block.BlockElement):
        self.cur.add_block(block)

class StormGenDoc:
    """A Markdown document that is ready for processing with stormgen.

    It contains a list of all ``Section``s in a document, in order of appearance.

    It also stores the raw AST parsed by marko_.

    _marko: https://pypi.org/project/marko/
    """

    def __init__(self, text: str) -> None:
        self.ast = marko.parse(text)
        self.parts = []

    def parse(self) -> list[Section]:
        part = Part(heading=None)
        for child in self.ast.children:
            if isinstance(child, marko.block.Heading):
                self.parts.append(part)
                part = Part(heading=child)
            part.add_block(child)
        return


class StormGenElement:
    """Processable pieces of a StormGenDoc."""


def parse(text: str) -> StormGenDoc:
    doc = StormGenDoc(text)
    doc.parse()
    return doc


def extract(doc: StormGenDoc) -> list[StormGenElement]:
    pass


def convert(doc: StormGenDoc) -> list[StormNode]:
    pass
