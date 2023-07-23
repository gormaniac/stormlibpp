"""Python objects for working with Synapse Telepath endpoints."""


from typing import Any, TypedDict


class TelepathRetn(TypedDict):
    """A standard return value from a Telepath API endpoint.

    Also typically returned by Cell methods that eventually
    get called by a Telepath endpoint method.

    Can be subclassed to override type of ``data``.

    Using this standard class to return values to Storm helps error handling in
    Storm code. Subclassing to set ``data``'s type also improves a Storm
    developer's understanding of the Python object available in Storm.

    A ``status`` of ``False`` means and error occurred. ``mesg`` must be set
    if ``status`` is ``False``. ``data`` may or may not be set.

    A ``status`` of ``True`` means everything worked well. In this case ``mesg``
    may be empty, but ``data`` must have a value.
    """

    status: bool
    mesg: str
    data: Any


class BoolRetn(TelepathRetn):
    """A TelepathRetn where ``data`` is a boolean value."""
    data: bool


class ListRetn(TelepathRetn):
    """A TelepathRetn where ``data`` is a list value."""
    data: list


class DictRetn(TelepathRetn):
    """A TelepathRetn where ``data`` is a dict value."""
    data: dict


class StrRetn(TelepathRetn):
    """A TelepathRetn where ``data`` is a str value."""
    data: str


def genDefaultTelepathRetn(obj=TelepathRetn, /, default_data=None) -> TelepathRetn:
    """Generate a default TelepathRetn return object, or the given subclass.

    Default values have a ``status`` of ``True``, an empty ``mesg``, and
    ``data`` is set to the ``default_data`` arg - which defaults to ``None``.
    """

    return obj(status=True, mesg="", data=default_data)
