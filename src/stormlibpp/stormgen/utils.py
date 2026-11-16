"""Generic helper functions unique to stormgen."""

import synapse.exc as s_exc
import synapse.lib.ast as s_ast
import synapse.lib.parser as s_parser


def constant_value(text: str):
    """Resolve only constant Storm values without executing a runtime."""
    try:
        value = s_parser.parseEval(text)
    except s_exc.BadSyntax as error:
        raise ValueError(f"Invalid Storm value {text!r}: {error}") from error
    return _constant_ast(value)


def _constant_ast(value):
    if isinstance(value, s_ast.Const):
        return value.valu
    if isinstance(value, s_ast.VarDeref) and len(value.kids) == 2:
        base, name = value.kids
        builtins = {"true": True, "false": False, "null": None}
        if (
            isinstance(base, s_ast.VarValue)
            and len(base.kids) == 1
            and isinstance(base.kids[0], s_ast.Const)
            and base.kids[0].valu == "lib"
            and isinstance(name, s_ast.Const)
            and name.valu in builtins
        ):
            return builtins[name.valu]
    if isinstance(value, (s_ast.List, s_ast.ExprList)):
        return tuple(_constant_ast(child) for child in value.kids)
    if isinstance(value, s_ast.DollarExpr) and len(value.kids) == 1:
        return _constant_ast(value.kids[0])
    raise ValueError("Runtime Storm expressions require stormgen.apply()")


def is_constant_list(text: str) -> bool:
    """Recognize constant Storm list syntax, not parenthesized ordinary text."""
    try:
        value = s_parser.parseEval(text)
        if isinstance(value, s_ast.DollarExpr) and len(value.kids) == 1:
            value = value.kids[0]
        if not isinstance(value, (s_ast.List, s_ast.ExprList)):
            return False
        _constant_ast(value)
    except (s_exc.BadSyntax, ValueError):
        return False
    return True


def heading_value(text: str):
    """Preserve explicit Storm values while allowing ordinary free-text headings."""
    try:
        value = s_parser.parseEval(text)
    except s_exc.BadSyntax as error:
        if text.startswith(("$", "(", "[", "{", "\"", "'")):
            raise ValueError(f"Invalid Storm value {text!r}: {error}") from error
        return text, False
    if value.astinfo.eoff < len(text.rstrip()):
        return text, False
    return text, True


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
    if text.endswith(" \\//"):
        text = text[:-3] + "//"
    return text
