"""Various helper functions to manipulate marko Markdown objects."""


import marko.block
import marko.element
import marko.inline
import marko.md_renderer


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
    title = ""
    for item in heading.children:
        title += item.children
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
