"""Various helper functions to manipulate marko Markdown objects."""


import marko.block
import marko.element
import marko.inline
import marko.md_renderer


def text_from_element(element: marko.element.Element) -> str:
    """Extract text recursively, including nested inline formatting."""
    if isinstance(element, marko.inline.LineBreak):
        return "\n"
    children = getattr(element, "children", [])
    if isinstance(children, str):
        return children
    return "".join(text_from_element(child) for child in children)


def _heading_leaves(element: marko.element.Element):
    children = getattr(element, "children", [])
    if isinstance(children, str):
        yield children, isinstance(element, marko.inline.Literal) and children == "/"
    else:
        for child in children:
            yield from _heading_leaves(child)


def title_from_heading(heading: marko.block.Heading) -> str:
    """Get the title string from a Heading block.

    Parameters
    ----------
    heading : marko.block.Heading
        The heading to extract a title from.

    Returns
    -------
    str
        The Heading's title.
    """
    leaves = list(_heading_leaves(heading))
    title = "".join(text for text, escaped in leaves)
    escaped_separators = set()
    offset = 0
    for text, escaped in leaves:
        if escaped:
            if offset > 0 and title[offset - 1:offset + 3] == " // ":
                escaped_separators.add(offset)
            elif offset > 1 and title[offset - 2:offset + 2] == " // ":
                escaped_separators.add(offset - 1)
        offset += len(text)
    for offset in sorted(escaped_separators, reverse=True):
        title = title[:offset] + "\\" + title[offset:]
    return title


def doc_from_blocks(blocks: list[marko.element.Element]) -> marko.block.Document:
    """Create a new Document element from a list of other elements.

    Parameters
    ----------
    blocks : list[marko.element.Element]
        The ``Element`` objects to convert to a new Document.

    Returns
    -------
    marko.block.Document
        The new Document element object.
    """
    doc = marko.block.Document()
    doc.children.extend(blocks)
    return doc


def doc_from_parts(parts: list) -> marko.block.Document:
    """Create a new Document element from a list of DocPart objects.

    Parameters
    ----------
    parts : list[DocPart]
        The ``DocPart`` objects to convert to a new Document.

    Returns
    -------
    marko.block.Document
        The new Document element object.
    """
    doc = marko.block.Document()
    for part in parts:
        doc.children.extend(part.blocks)
    return doc


def md_from_blocks(blocks: list[marko.element.Element]) -> str:
    """Convert a list of Element objects to convert to a Markdown string.

    Parameters
    ----------
    parts : list[marko.element.Element]
        The ``Element`` objects to convert to Markdown.

    Returns
    -------
    str
        The rendered Markdown.
    """
    return marko.md_renderer.MarkdownRenderer().render(doc_from_blocks(blocks))


def md_from_parts(parts: list) -> str:
    """Convert a list of DocPart objects to convert to a Markdown string.

    Parameters
    ----------
    parts : list[DocPart]
        The ``DocPart`` objects to convert to Markdown.

    Returns
    -------
    str
        The rendered Markdown.
    """
    return marko.md_renderer.MarkdownRenderer().render(doc_from_parts(parts))
