"""stormgen helps analysts generate Synapse nodes from Markdown documentation.

TODO - Put a long docstring here so it gets include in docs
"""

from collections.abc import Callable

import marko

from .. import StormNode
from . import md
from . import utils


DocNodeExtractor = Callable[["StormGenDoc", str, str, str], list["DocNode"]]
"""A method that extracts ``DocNodes`` from a ``StormGenDoc`` of a given type."""


class DocPart:
    """A DocPart is all blocks between any two headings, including the 1st heading."""

    def __init__(self, heading: marko.block.Heading | None) -> None:
        self.blocks: list[marko.block.BlockElement] = []
        self.heading = heading
        self.title = ""
        self.level = 0

        if self.heading is not None:
            self.level = self.heading.level
            self.title = md.title_from_heading(self.heading)
            self.stripped_title = utils.strip_comment(self.title)

    def __repr__(self) -> str:
        return f"<DocPart: {self.title}>"

    def add_block(self, block: marko.block.BlockElement):
        self.blocks.append(block)

    def markdown(self):
        return md.md_from_parts([self])


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

        # Catch the last part
        if part not in self.parts:
            self.parts.append(part)


class DocNodeSection:
    """A collection of DocParts that are part of a DocNode, like a node prop or tag."""

    def __init__(self) -> None:
        self.parts: list[DocPart] = []

    def add_part(self, part: DocPart) -> None:
        self.parts.append(part)


class DocNode:
    """A node defined in Markdown - as a grouping of ``DocPart`` objects."""

    def __init__(self, form: str, valu: str) -> None:
        self.form = form
        self.valu = valu
        self.parts: list[DocPart] = []
        self.props: list[DocNodeSection] = []
        self.tags: list[DocNodeSection] = []
        self.edges: list[DocNodeSection] = []
        self.comment: str = ""

        self.extract()

    def __repr__(self) -> str:
        return f"<DocNode: {self.form}={self.valu}>"

    def add_part(self, part: DocPart) -> None:
        self.parts.append(part)

    def extract(self):
        """Extract all parts of a DocNode from the input parts."""

        comment_blocks = [block for block in self.parts[0].blocks[1:]]
        self.comment = md.md_from_blocks(comment_blocks)

        # nlevel = self.parts[0].level

        # section: DocNodeSection | None = None

        # # TODO - This code is wrong
        # for part in self.parts[1:]:
        #     if part.level == nlevel + 1:
        #         section = DocNodeSection()
        #         if part.stripped_title not in ("Edges", "Tags"):
        #             self.props.append(section)
        #             section.add_part(part)
        #         elif part.stripped_title == "Edges":
        #             self.edges.append(section)
        #         elif part.stripped_title == "Tags":
        #             self.tags.append(section)
        #     if part.level > nlevel + 1:
        #         section.add_part(part)


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
        form_level: str = 2,
    ) -> None:
        self.doc = doc
        self.dtype = doc_type
        self.form = form
        self.nheader = nodes_header
        self.flevel = form_level
        self.nlevel = self.flevel + 1

        if doc_type not in self.types:
            raise ValueError(f"Unsupported type ({doc_type}) passed to DocExtractor!")

    def _extract_embedded(self):
        for index in range(len(self.doc.parts)):
            part = self.doc.parts[index]

            if part.title == self.nheader:
                self.flevel = part.level + 1
                self.nlevel = self.flevel + 1
                return self._extract(self.doc.parts[index:])

        return []

    def _extract_forms(self):
        return self._extract(self.doc.parts, form=self.form)

    def _extract_full(self):
        return self._extract(self.doc.parts)

    def _extract(self, parts: list[DocPart], form=""):
        nodes: list[DocNode] = []
        node: DocNode | None = None
        cur_form = form

        for part in parts:

            if part.level == self.flevel:
                if not form:
                    cur_form = part.title

            if part.level == self.nlevel:
                if node is not None:
                    nodes.append(node)
                node = DocNode(cur_form, part.stripped_title)
                node.add_part(part)

            if part.level > self.nlevel:
                node.add_part(part)

        # Catch the last node
        if isinstance(node, DocNode) and node not in nodes:
            nodes.append(node)

        return nodes

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