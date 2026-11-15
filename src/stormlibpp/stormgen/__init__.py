"""Extract, convert, compile and apply Synapse nodes from Markdown documentation."""

from collections.abc import Callable
from typing import Any
from dataclasses import dataclass
import re

import marko
import synapse.common as s_common
import synapse.datamodel as s_datamodel

from .. import StormNode
from ..utils import startswith
from . import md
from . import utils


DocNodeExtractor = Callable[["StormGenDoc", str, str, str], list["DocNode"]]
"""A method that extracts ``DocNodes`` from a ``StormGenDoc`` of a given type."""


@dataclass
class Prop:
    """A node property."""

    key: str
    val: Any


@dataclass(frozen=True)
class StormExpression:
    """Unevaluated Storm source, kept distinct from literal Markdown text."""

    text: str


class DocPart:
    """A DocPart is all blocks between any two headings, including the 1st heading."""

    def __init__(self, heading: marko.block.Heading | None) -> None:
        self.blocks: list[marko.block.BlockElement] = []
        self.heading = heading
        self.title = ""
        self.stripped_title = ""
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

    def resolve_val(self):
        for block in self.blocks:
            if isinstance(block, (marko.block.FencedCode, marko.block.CodeBlock)):
                text = md.text_from_element(block)
                if text.endswith("\n"):
                    text = text[:-1]
                language = getattr(block, "lang", "")
                if language == "storm" or (not language and utils.is_constant_list(text)):
                    return StormExpression(text)
                return text
        for block in self.blocks:
            if isinstance(block, marko.block.List):
                return self.list_values(block)
        for block in self.blocks:
            if isinstance(block, marko.block.Paragraph):
                line = []
                for child in [*block.children, None]:
                    if child is None or isinstance(child, marko.inline.LineBreak):
                        if len(line) == 1 and isinstance(line[0], marko.inline.CodeSpan):
                            return md.text_from_element(line[0])
                        line = []
                    elif not isinstance(child, marko.inline.RawText) or child.children.strip():
                        line.append(child)
        if "=" in self.stripped_title:
            value = self.stripped_title.split("=", 1)[1].strip()
            if value:
                return StormExpression(value)
        raise ValueError(f"Missing value under heading {self.title!r}")

    def list_values(self, block: marko.block.List) -> list[str]:
        values = []
        for item in block.children:
            paragraphs = [child for child in item.children if isinstance(child, marko.block.Paragraph)]
            if len(paragraphs) != 1 or any(
                not isinstance(child, (marko.block.Paragraph, marko.block.BlankLine))
                for child in item.children
            ):
                raise ValueError(f"Expected a flat list under heading {self.title!r}")
            value = md.text_from_element(paragraphs[0]).strip()
            if not value:
                raise ValueError(f"Empty list item under heading {self.title!r}")
            values.append(value)
        return values


class DocSection:
    """A grouping of related DocPart objects."""

    def __init__(self) -> None:
        self.parts: list[DocPart] = []

    def add_part(self, part: DocPart) -> None:
        self.parts.append(part)


class PropParts(DocSection):
    """DocPart objects that include properties.

    Tags and Nodes can have properties.
    """

    def __init__(self) -> None:
        super().__init__()
        self.props: list[Prop] = []

    def add_prop(self, prop: Prop) -> None:
        self.props.append(prop)

    def extract_props(self, prop_level: int = 3):
        self.props.clear()
        for part in self.parts:
            if part.level == prop_level and startswith(part.stripped_title, [".", ":"]):
                self.add_prop(
                    Prop(
                        key=part.stripped_title.split("=", 1)[0],
                        val=part.resolve_val(),
                    )
                )


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

        self.parts.clear()
        part = DocPart(heading=None)

        for child in self.ast:
            if isinstance(child, marko.block.SetextHeading):
                raise ValueError("Unsupported Setext heading; use ATX headings starting with #")
            if isinstance(child, marko.block.Heading):
                self.parts.append(part)
                part = DocPart(heading=child)

            part.add_block(child)

        # Catch the last part
        if part not in self.parts:
            self.parts.append(part)


class DocNodeSection(PropParts):
    """A collection of DocParts that are part of a DocNode, like a node prop or tag."""

    types = (
        "edge",
        "tag",
        "prop",
    )

    def __init__(self, _type: str) -> None:
        super().__init__()

        if _type in self.types:
            self.type = _type
        else:
            raise ValueError(f"Invalid type ({_type}) passed to DocNodeSection!")


class DocTag(DocNodeSection):
    """A tag name, optional Storm interval and tag properties."""

    def __init__(self, part: DocPart) -> None:
        super().__init__("tag")
        name, separator, interval = part.stripped_title.partition("=")
        if not re.fullmatch(r"#[\w.-]+", name) or (separator and not interval.strip()):
            raise ValueError(f"Invalid tag heading {part.title!r}")
        self.name = name[1:]
        self.interval = StormExpression(interval.strip()) if separator else None
        self.add_part(part)


class DocEdge(DocNodeSection):
    """A directed edge statement and its ordered form/value targets."""

    def __init__(self, part: DocPart) -> None:
        super().__init__("edge")
        match = re.fullmatch(r"(?:-\(([^()\s]+)\)>|<\(([^()\s]+)\)-)", part.stripped_title)
        if match is None:
            raise ValueError(f"Invalid edge heading {part.title!r}")
        self.verb = match.group(1) or match.group(2)
        self.reverse = match.group(2) is not None
        self.add_part(part)
        block = next((block for block in part.blocks if isinstance(block, marko.block.List)), None)
        if block is None:
            raise ValueError(f"Missing target list under edge {part.title!r}")
        self.targets: list[tuple[str, str]] = []
        for value in part.list_values(block):
            form, separator, primary = value.partition("=")
            if not re.fullmatch(r"[a-z_][a-z0-9_:]*", form) or not separator or not primary.strip():
                raise ValueError(f"Invalid edge target {value!r} under {part.title!r}")
            self.targets.append((form, primary.strip()))


class DocNode(PropParts):
    """A node defined in Markdown - as a grouping of ``DocPart`` objects."""

    def __init__(self, form: str, valu: str) -> None:
        super().__init__()
        self.form = form
        self.valu = valu
        self.tags: list[DocTag] = []
        self.edges: list[DocEdge] = []
        self.comment: str = ""

    def __repr__(self) -> str:
        return f"<DocNode: {self.form}={self.valu}>"

    def extract(self):
        """Extract all parts of a DocNode from the input parts."""

        self.tags.clear()
        self.edges.clear()
        if not self.parts:
            self.props.clear()
            self.comment = ""
            return
        self.comment = md.md_from_blocks([
            block for block in self.parts[0].blocks
            if not isinstance(block, (marko.block.Heading, marko.block.FencedCode, marko.block.CodeBlock))
        ]).strip()
        nlevel = self.parts[0].level
        self.extract_props(prop_level=nlevel + 1)
        section: DocNodeSection | None = None
        parent_section = ""
        for part in self.parts[1:]:
            if part.level == nlevel + 1:
                parent_section = part.stripped_title if part.stripped_title in ("Edges", "Tags") else ""
                section = None
            elif part.level == nlevel + 2:
                section = None
                if parent_section == "Tags":
                    tag = DocTag(part)
                    self.tags.append(tag)
                    section = tag
                elif parent_section == "Edges":
                    edge = DocEdge(part)
                    self.edges.append(edge)
                    section = edge
            elif part.level > nlevel + 2 and section is not None:
                section.add_part(part)
        for tag in self.tags:
            tag.extract_props(prop_level=tag.parts[0].level + 1)


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
        form_level: int = 2,
    ) -> None:
        self.doc = doc
        self.dtype = doc_type
        self.form = form
        self.nheader = nodes_header
        self.flevel = form_level

        if doc_type not in self.types:
            raise ValueError(f"Unsupported type ({doc_type}) passed to DocExtractor!")
        if not isinstance(form_level, int) or not 1 <= form_level <= 5:
            raise ValueError("form_level must be an integer between 1 and 5")
        self.nlevel = self.flevel + 1
        if doc_type == "forms" and not form:
            raise ValueError("Single-form documents require a form")

    def _extract_embedded(self):
        nodes = []
        index = 0
        pattern = re.compile(re.escape(self.nheader) + r"(?:\s+\(([^()]+)\))?")
        while index < len(self.doc.parts):
            part = self.doc.parts[index]
            match = pattern.fullmatch(part.stripped_title) if part.level else None
            if match is None:
                index += 1
                continue
            end = index + 1
            while end < len(self.doc.parts) and self.doc.parts[end].level > part.level:
                end += 1
            form = match.group(1) or self.form
            nodes.extend(self._extract(
                self.doc.parts[index + 1:end],
                form=form,
                form_level=part.level if form else part.level + 1,
                node_level=part.level + 1 if form else part.level + 2,
            ))
            index = end
        return nodes

    def _extract_forms(self):
        root = self.doc.parts[0] if self.doc.parts else None
        if root is not None and root.level == 0 and any(
            not isinstance(block, marko.block.BlankLine) for block in root.blocks
        ):
            raise ValueError("Single-form documents must start with a node heading")
        return self._extract(self.doc.parts, form=self.form, form_level=0, node_level=1)

    def _extract_full(self):
        return self._extract(self.doc.parts)

    def _extract(self, parts: list[DocPart], form="", form_level=None, node_level=None):
        nodes: list[DocNode] = []
        node: DocNode | None = None
        cur_form = form
        form_level = self.flevel if form_level is None else form_level
        node_level = self.nlevel if node_level is None else node_level

        for part in parts:
            if part.level < node_level:
                node = None
                if not form:
                    cur_form = part.stripped_title if part.level == form_level else ""
                continue
            if part.level == node_level and cur_form:
                node = DocNode(cur_form, part.stripped_title)
                node.add_part(part)
                nodes.append(node)
            elif part.level > node_level and node is not None:
                node.add_part(part)
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
        self.storm_nodes = []
        if self.save_comments:
            raise ValueError("Documentation notes require stormgen.apply()")
        nodes = []
        for node in self.doc_nodes:
            if not re.fullmatch(r"[a-z_][a-z0-9_:]*", node.form):
                raise ValueError(f"Invalid form heading {node.form!r}")
            if node.parts:
                node.extract()
            if node.edges:
                raise ValueError(f"Edges on {node!r} require stormgen.apply()")
            text, expression = utils.heading_value(node.valu)
            value = utils.constant_value(text) if expression else text
            if value == "*" or isinstance(value, tuple):
                raise ValueError(f"Generated or composite primary values on {node!r} require stormgen.apply()")
            props = {
                prop.key.removeprefix(":"): self._value(prop.val)
                for prop in node.props
            }
            tags = {}
            tagprops = {}
            for tag in node.tags:
                interval = (None, None)
                if tag.interval is not None:
                    interval_value = utils.constant_value(tag.interval.text)
                    interval = s_datamodel.Model().type("ival").norm(interval_value)[0]
                tags[tag.name] = interval
                tagprops[tag.name] = {
                    prop.key.removeprefix(":"): self._value(prop.val)
                    for prop in tag.props
                }
            nodes.append(StormNode(node.form, value, props=props, tags=tags, tagprops=tagprops))
        self.storm_nodes = nodes

    @staticmethod
    def _value(value):
        if isinstance(value, StormExpression):
            return utils.constant_value(value.text)
        if isinstance(value, list):
            return tuple(value)
        return value


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
    *,
    form_level: int = 2,
) -> list[DocNode]:
    return DocExtractor(
        doc,
        doc_type=doc_type,
        nodes_header=nodes_header,
        form=form,
        form_level=form_level,
    ).extract()


def convert(
    doc: StormGenDoc,
    comments: bool = False,
    doc_type: str = "full",
    nodes_header: str = "Nodes",
    form: str = "",
    extractor: DocNodeExtractor = extract,
    *,
    form_level: int = 2,
) -> list[StormNode]:
    """Convert a parsed stormgen Markdown document to a list of Storm nodes.

    Parameters
    ----------
    doc : StormGenDoc
        The parsed Markdown document in a stormgen compatible format.
    comments : bool, optional
            Documentation notes require ``apply``; True raises a capability error.
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
    form_level : int, optional
        The form-heading level for full documents, by default 2.

    Notes
    -----
    This offline API resolves constant values, not model normalization or runtime
    expressions. Generated/composite primary values and edges require ``apply``.

    Returns
    -------
    list[StormNode]
        The Storm nodes created from the input ``StormGenDoc``.
    """

    kwargs = {"form_level": form_level} if form_level != 2 else {}
    cvertr = NodesConverter(extractor(doc, doc_type, nodes_header, form, **kwargs), comments=comments)
    cvertr.convert()
    return cvertr.storm_nodes


def compile_storm(
    doc: StormGenDoc,
    doc_type: str = "full",
    nodes_header: str = "Nodes",
    form: str = "",
    *,
    form_level: int = 2,
    comments: bool = False,
):
    """Compile a trusted document to Storm source and separately bound literal data."""
    from .compiler import StormCompiler

    nodes = extract(doc, doc_type, nodes_header, form, form_level=form_level)
    return StormCompiler().compile(nodes, comments=comments)


async def apply(
    doc: StormGenDoc,
    cortex,
    doc_type: str = "full",
    nodes_header: str = "Nodes",
    form: str = "",
    *,
    form_level: int = 2,
    comments: bool = False,
    opts: dict | None = None,
) -> list[StormNode]:
    """Apply a trusted document through callStorm and return normalized source nodes.

    Runtime errors propagate. Application is ordered, not guaranteed atomic.
    """
    program = compile_storm(doc, doc_type, nodes_header, form, form_level=form_level, comments=comments)
    options = dict(opts or {})
    options["vars"] = {**options.get("vars", {}), **program.vars}
    result = await cortex.callStorm(program.text, opts=options)
    if isinstance(result, dict):
        if result.get("status") != "ok":
            raise ValueError(f"Stormgen application failed: {result}")
        result = result.get("result")
    if not isinstance(result, (tuple, list)):
        raise ValueError(f"Expected packed nodes from Stormgen application, got {result!r}")
    return [StormNode.unpack(packed) for packed in s_common.tuplify(result)]
