"""stormgen helps analysts generate Synapse nodes from Markdown documentation.

TODO - Put a long docstring here so it gets include in docs
"""


import marko


from .. import StormNode


class DocPart:
    """A DocPart is all blocks between any two headings, including the 1st heading."""

    def __init__(self, heading: marko.block.Heading | None) -> None:
        self.blocks: list[marko.block.BlockElement] = []
        self.heading = heading
        self.level = 0

        if self.heading is not None:
            self.level = self.heading.level

    def add_block(self, block: marko.block.BlockElement):
        self.blocks.append(block)


class StormGenDoc:
    """A Markdown document that is ready for processing with stormgen.

    It contains a list of all ``Section``s in a document, in order of appearance.

    It also stores the raw AST parsed by marko_.

    _marko: https://pypi.org/project/marko/
    """

    def __init__(self, text: str) -> None:
        self.ast: list[marko.block.BlockElement] = marko.parse(text).children
        """All blocks in the input text, in top-to-bottom order of appearance."""
        self.parts: list[DocPart] = []
        """A list of all ``DocPart``s in the input text, in order of appearance.
        
        A ``DocPart`` is all blocks between two headers.
        """

    def parse(self) -> None:
        """Parse the input text into a list of blocks and a list of ``DocPart``s."""

        part = DocPart(heading=None)

        for child in self.ast:
            if isinstance(child, marko.block.Heading):
                self.parts.append(part)
                part = DocPart(heading=child)

            part.add_block(child)

        return


class DocNode:
    """A node defined in Markdown - as a grouping of ``DocPart``s."""

    def __init__(self, parts: list[DocPart], form: str) -> None:
        self.parts = parts
        self.form = form
        self.valu: str = ""
        self.props: list[DocPart] = []
        self.tags: list[DocPart] = []
        self.edges: list[DocPart] = []

        self.extract()

    def extract(self):
        """Extract all parts of a DocNode from the input parts."""
        pass


class DocExtractor:
    """Extracts ``DocNode``s from a ``StormGenDoc``."""

    types = (
        "embedded",
        "forms",
        "full",
    )

    def __init__(
        self,
        doc: StormGenDoc,
        /,
        doc_type: str = "full",
        form: str = "",
        nodes_header: str = "Nodes",
    ) -> None:
        self.doc = doc
        self.dtype = doc_type
        self.form = form
        self.nheader = nodes_header

    def _extract_embedded(self):
        pass

    def _extract_forms(self):
        pass

    def _extract_full(self):
        pass

    def extract(self) -> list[DocNode]:
        """Get the ``DocNode``s from the input document."""

        match self.dtype:
            case "embedded":
                return self._extract_embedded()
            case "forms":
                return self._extract_forms()
            case "full":
                return self._extract_full()


class NodesConverter:
    """Convert ``DocNode``s to ``StormNode``s."""

    def __init__(self, doc_nodes: list[DocNode], comments: bool = False,) -> None:
        self.save_comments = comments
        self.doc_nodes = doc_nodes
        self.storm_nodes: list[StormNode] = []
    
    def convert(self) -> None:
        pass


def parse(text: str) -> StormGenDoc:
    doc = StormGenDoc(text)
    doc.parse()
    return doc


def extract(
    doc: StormGenDoc,
    doc_type: str = "full",
    nodes_header: str = "Nodes",
    form: str = "",
) -> list[DocNode]:
    return DocExtractor(
        doc,
        doc_type=doc_type,
        nodes_header=nodes_header,
        form=form,
    ).extract()


def convert(
    doc: StormGenDoc,
    comments: bool = False,
    doc_type: str = "full",
    nodes_header: str = "Nodes",
    form: str = "",
) -> list[StormNode]:
    cvertr = NodesConverter(
        extract(doc, doc_type, nodes_header, form), comments=comments
    )
    cvertr.convert()
    return cvertr.storm_nodes
