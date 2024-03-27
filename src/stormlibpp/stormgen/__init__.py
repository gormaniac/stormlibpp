"""stormgen helps analysts generate Synapse nodes from Markdown documentation.

TODO - Put a long docstring here so it gets include in docs
"""


from collections.abc import Callable

import marko

from .. import StormNode


DocNodeExtractor = Callable[["StormGenDoc", str, str, str], list["DocNode"]]
"""A method that extracts ``DocNodes`` from a ``StormGenDoc`` of a given type."""


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

    It contains a list of all ``DocPart`` objects in a document,
    in order of appearance.

    It also stores the raw AST parsed by `marko`_.

    .. _marko: https://pypi.org/project/marko/
    """

    def __init__(self, text: str) -> None:
        self.ast: list[marko.block.BlockElement] = marko.parse(text).children
        """All blocks in the input text, in top-to-bottom order of appearance."""
        self.parts: list[DocPart] = []
        """A list of all ``DocPart`` objects in the input text, in order of appearance.
        
        A ``DocPart`` is all blocks between two headings.
        """

    def parse(self) -> None:
        """Parse the input text into a list of blocks and a list of ``DocPart`` objects."""

        part = DocPart(heading=None)

        for child in self.ast:
            if isinstance(child, marko.block.Heading):
                self.parts.append(part)
                part = DocPart(heading=child)

            part.add_block(child)

        return


class DocNode:
    """A node defined in Markdown - as a grouping of ``DocPart`` objects."""

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
    """Extracts ``DocNode`` objects from a ``StormGenDoc``."""

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

        if doc_type not in self.types:
            raise ValueError(f"Unsupported type ({doc_type}) passed to DocExtractor!")

    def _extract_embedded(self):
        pass

    def _extract_forms(self):
        pass

    def _extract_full(self):
        pass

    def extract(self) -> list[DocNode]:
        """Get the ``DocNode`` objects from the input document."""

        match self.dtype:
            case "embedded":
                return self._extract_embedded()
            case "forms":
                return self._extract_forms()
            case "full":
                return self._extract_full()


class NodesConverter:
    """Convert ``DocNodes`` to ``StormNodes``."""

    def __init__(
        self,
        doc_nodes: list[DocNode],
        comments: bool = False,
    ) -> None:
        self.save_comments = comments
        self.doc_nodes = doc_nodes
        self.storm_nodes: list[StormNode] = []

    def convert(self) -> None:
        pass


def parse(text: str) -> StormGenDoc:
    """Parse a Markdown document into a ``StormGenDoc``.

    Parameters
    ----------
    text : str
        The Markdown document to parse.

    Returns
    -------
    StormGenDoc
        An object representing the parsed Markdown document.

        A ``StormGenDoc`` has an AST of all pieces of the document and list of
        ``DocPart`` objects. It can be passed to ``convert`` to make a list of
        ``StormNode`` objects that can be sent to Synapse.
    """

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
    extractor: DocNodeExtractor = extract,
) -> list[StormNode]:
    """Convert a parsed stormgen Markdown document to a list of Storm nodes.

    Parameters
    ----------
    doc : StormGenDoc
        The parsed Markdown document in a stormgen compatible format.
    comments : bool, optional
        Whether to create meta:note nodes to link select Markdown text to the
        created nodes, by default False.
    doc_type : {"full", "embedded", "forms"} str, optional
        The type of stormgen doc that is being converted, by default "full".
    nodes_header : str, optional
        The prefix for the header used to detect stormgen Markdown when processing
        an ``embedded`` doc, by default "Nodes".
    form : str, optional
        Optionally skip node form detection and treat all nodes defined in the doc
        as one form, by default "".
    extractor : DocNodeExtractor, optional
        A callable that can create a list of ``DocNode`` objects from an input
        ``StormGenDoc``, by default ``extract``.

    Returns
    -------
    list[StormNode]
        The Storm nodes created from the input ``StormGenDoc``.
    """

    cvertr = NodesConverter(
        extractor(doc, doc_type, nodes_header, form), comments=comments
    )
    cvertr.convert()
    return cvertr.storm_nodes
