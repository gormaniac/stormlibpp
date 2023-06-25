class PackedNode:
    """A "packed" storm:node Storm object that is in a Python runtime.

    It supports "unpacking" the node into this object, edits to the object, and
    repacking of the node to be sent back to Storm.

    This node can be created purely from Python code rather than a packed
    ``storm:node`` object. Use the ``__init__`` directly instead of ``unpack``.
    This allows the creation of a new node in Python that can be passed back to
    Storm.
    """

    raise NotImplementedError
