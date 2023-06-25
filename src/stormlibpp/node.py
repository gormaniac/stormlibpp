"""Work with storm:node objects in Python."""


from typing import Any, Self, TypedDict


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


class StormNode:
    """A "packed" storm:node Storm object that is in a Python runtime.

    It supports "unpacking" the node into this object, edits to the object, and
    repacking of the node to be sent back to Storm.

    This node can be created purely from Python code rather than a packed
    ``storm:node`` object. Use the ``__init__`` directly instead of ``unpack``.
    This allows the creation of a new node in Python that can be passed back to
    Storm.
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

        self._tags = tags
        self._props = props

        self.iden = iden
        self.nodedata = nodedata
        self.tagprops = tagprops

        # Not really sure if this is needed, but saving it for now.
        self._xtras = kwargs

    @property
    def form(self) -> str:
        """The form of this Node."""

        return self._form

    @property
    def value(self) -> str:
        """The value of this Node."""

        return self._value

    @property
    def tags(self):
        """The tags of this Node."""

        return self._tags

    @property
    def props(self):
        """The properties of this Node."""

        return self._props

    @property
    def nodevals(self):
        """The NodeVals dict this Node would have in a NodeTuple."""

        return NodeVals(
            iden=self.iden,
            tagprops=self.tagprops,
            nodedata=self.nodedata,
            props=self.props,
            tags=self.tags,
        )

    @classmethod
    def unpack(cls, packedtup: NodeTuple) -> Self:
        form, name = packedtup[0]
        vals = NodeVals(**packedtup[1])
        return cls(
            form,
            name,
            **vals
        )

    def pack(self) -> NodeTuple:
        return ((self.form, self.value), self.nodevals)

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

    def addProps(self, props: dict) -> None:
        for propname, propval in props.items():
            self._props[propname] = propval
