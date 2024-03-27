"""Generic helper functions unique to stormgen."""


def strip_comment(text: str) -> str:
    """Strip a comment from a node DocPart's title.

    Also converts escaped comments separators to regular double slashes.

    Parameters
    ----------
    text : str
        The text to strip a comment from.

    Returns
    -------
    str
        The stripped, and converted text.
    """

    sep = " // "
    esc = " \\// "
    if sep in text:
        text = " // ".join(text.split(" // ")[:-1]).strip()
    if esc in text:
        text = text.replace(esc, sep)
    return text
