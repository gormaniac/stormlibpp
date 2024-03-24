"""Work with storm:node objects in Python."""


from typing import Any, TypedDict


NodeForm = str
"""A valid syn:form value."""


class NodeVals(TypedDict):
    """The items a Node can have in the second part of packed NodeTuple."""

    iden: str
    nodedata: dict[str, Any]
    props: dict[str, Any]
    tags: dict[str, Any]
    tagprops: dict[str, Any]


NodeDef = tuple[NodeForm, str]
"""A nodes definition, the node's form and primary value."""

NodeTuple = tuple[NodeDef, NodeVals]
"""A packed node, this is what get's sent from Storm to a Telepath endpoint.

Or what get's returned from a Cortex's Python APIs.
"""


class ItemContainer:
    """Hold key/value items in dict-like container.

    Acts almost identically to a dict except::
        
        - Missing items simply return None, not raise an error.
        - Iterating over an ``ItemContainer`` returns key/value pairs instead
          of just the key.
        - Keys must be strings.
            - Although technically non-string keys could be used, it messes
              up instantiation.
        - The object's ``repr`` is the current classname and all items in the
          container as if the object was being instantiated - a la ``SimpleNamespace``.
          Meaning, subclasses get automatic repr support.

    All default methods of a ``dict`` are supported, they are actually directly
    returned from the underlying ``dict`` thanks to ``__getattr__`` magic. Meaning
    calling these methods operate on the items this container.

    Supports ``obj['item']`` (and ``obj['item'] = 'val'``) notation.

    When "getting" an item with ``__getitem__``, that doesn't exist in the
    container, ``None`` is returned instead of raising an exception.

    Calling ``dir`` on this object will only return names for items this object
    "holds" instead of all parts of this object.

    Supports checking if an item is "held" via the ``in`` operator.

    Supports iteration of items in the underlying ``dict``. Each iteration returns
    a tuple of the item name followed by the item value.

    Implements only magic methods, and all of them operate on the underlying
    SimpleNamespace.

    To convert this object to a ``dict`` of the items it holds,
    call ``vars`` on an instance.

    Parameters
    ----------
    All keyword args passed at instantiation are added to the container as initial
    values. These are not required and no args passed just creates an empty container.
    """

    def __init__(self, /, **kwargs) -> None:
        self.__ns = dict(**kwargs)

    def __contains__(self, __name: str) -> bool:
        return __name in self.__ns

    def __delitem__(self, __name: str) -> None:
        if __name in self:
            del self.__ns[__name]

    @property
    def __dict__(self):
        return self.__ns

    def __iter__(self) -> Any:
        for item in self.__ns:
            yield (item, self[item])

    def __getattr__(self, __name):
        try:
            return getattr(self.__ns, __name)
        # Rewrite the attribute error to use the current class's name.
        except AttributeError:
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{__name}'"
            )

    def __getitem__(self, __name: str) -> Any:
        return self.__ns.get(__name, None)

    def __repr__(self) -> str:
        orig = f"{self.__class__.__name__}("
        ret = orig
        for key, val in self:
            ret += f"{key}={val}, "
        if ret != orig:
            ret = f"{ret[:-2]})"
        else:
            ret = f"{ret})"
        return ret

    def __setitem__(self, __name: str, __value: Any) -> None:
        self.__ns[__name] = __value


class Props(ItemContainer):
    """Properties of a StormNode."""


class Tags(ItemContainer):
    """Tags of a StormNode."""


class StormNode:
    """A storm:node Storm object that is in a Python runtime.

    It supports "unpacking" the node into this object, edits to the object, and
    repacking of the node to be sent back to Storm.

    This node can be created purely from Python code rather than a packed
    ``storm:node`` object. Use ``__init__`` directly instead of ``unpack``.
    This allows the creation of a new node in Python that can be passed back to
    Storm.

    The intent is to represent an object that can be read from and written back
    to a Cortex. It isn't meant to provide the same API that a ``storm:node``
    has in Storm.
    """

    def __init__(
        self,
        form: NodeForm,
        value: Any,
        /,
        iden: str = "",
        tags: dict = {},
        props: dict = {},
        nodedata: dict = {},
        tagprops: dict = {},
        **kwargs,
    ) -> None:
        self._form = form
        self._value = value

        self._tags = Tags(**tags)
        self._props = Props(**props)

        self.iden = iden
        # TODO - Should these also become ItemContainers?
        self.nodedata = nodedata
        self.tagprops = tagprops

        # Not really sure if this is needed, but saving it for now.
        self._xtras = kwargs

    @property
    def form(self) -> str:
        """The form of this StormNode."""

        return self._form

    @property
    def value(self) -> str:
        """The value of this StormNode."""

        return self._value

    @property
    def tags(self):
        """The tags of this StormNode."""

        return self._tags

    @property
    def props(self):
        """The properties of this StormNode."""

        return self._props

    @property
    def nodevals(self):
        """The NodeVals dict this Node would have in a NodeTuple."""

        return NodeVals(
            iden=self.iden,
            tagprops=self.tagprops,
            nodedata=self.nodedata,
            props=vars(self.props),
            tags=vars(self.tags),
        )

    @classmethod
    def unpack(cls, packedtup: NodeTuple) -> "StormNode":
        form, name = packedtup[0]
        vals = NodeVals(**packedtup[1])
        return cls(form, name, **vals)

    def pack(self) -> NodeTuple:
        return ((self.form, self.value), self.nodevals)

    # TODO - Support tag properties
    def addTag(self, tag, timestamps: tuple = (None, None)) -> None:
        if (
            tag in self._tags
            and timestamps != (None, None)
            and self._tags[tag] != timestamps
        ):
            self._tags[tag] = timestamps
        elif tag not in self._tags:
            self._tags[tag] = timestamps

    def addTags(self, tags, timestamps: tuple = (None, None)) -> None:
        for tag in tags:
            self.addTag(tag, timestamps=timestamps)

    def addProp(self, propname: str, propval: Any) -> None:
        self._props[propname] = propval

    def addProps(self, props: dict[str, Any]) -> None:
        for propname, propval in props.items():
            self._props[propname] = propval
