"""Work with storm:node objects in Python."""


from types import SimpleNamespace
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
    """Hold key/value items in a SimpleNamespace.

    Keys must be strings.

    Supports ``obj['item']`` (and ``obj['item'] = 'val'``) notation.

    When "getting" an item with ``__getitem__``, that doesn't exist in the
    container, ``None`` is returned instead of raising an exception.

    Calling ``dir`` on this object will only return names for items this object
    "holds" instead of all parts of this object.

    Supports checking if an item is "held" via the ``in`` operator.

    Supports iteration of items in the SimpleNamespace. Each iteration returns
    a tuple of the item name followed by the item value.

    Implements only magic methods, and all of them operate on the underlying
    SimpleNamespace.
    
    To convert this object to a ``dict`` of the items it holds,
    call ``vars`` on an instance.
    """

    def __init__(self, /, **kwargs) -> None:
        # TODO - Is SimpleNamespace really the best option for this?
        self.__ns = SimpleNamespace(**kwargs)
    
    def __contains__(self, __name: str) -> bool:
        return __name in dir(self)

    @property
    def __dict__(self):
        return self.__ns.__dict__

    def __dir__(self) -> list[str]:
        return [val for val in dir(self.__ns) if not val.startswith("_")]

    def __iter__(self) -> Any:
        for item in dir(self):
            yield (item, self[item])

    def __getitem__(self, __name: str) -> Any:
        return getattr(self.__ns, __name, None)

    def __repr__(self) -> str:
        return repr(self.__ns).replace("namespace", self.__class__.__name__)

    def __setitem__(self, __name: str, __value: str) -> None:
        setattr(self.__ns, __name, __value)


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
    def unpack(cls, packedtup: NodeTuple) -> 'StormNode':
        form, name = packedtup[0]
        vals = NodeVals(**packedtup[1])
        return cls(
            form,
            name,
            **vals
        )

    def pack(self) -> NodeTuple:
        return ((self.form, self.value), self.nodevals)

    # TODO - Support tag properties
    def addTag(self, tag, timestamps: tuple = (None, None)) -> None:
        if tag in self._tags and timestamps != (None, None) and self._tags[tag] != timestamps:
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
