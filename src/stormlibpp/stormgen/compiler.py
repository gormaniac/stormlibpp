"""Compile structured Markdown nodes into an ordered Storm program."""

from dataclasses import dataclass
from typing import Any
import json
import re

import synapse.exc as s_exc
import synapse.lib.parser as s_parser

from . import DocNode, StormExpression, utils


@dataclass
class StormProgram:
    """Storm source and literal variables to pass together to a Cortex."""

    text: str
    vars: dict[str, Any]

    def to_storm(self) -> str:
        """Return standalone Storm with literal data loaded from a JSON string."""
        data = json.dumps(self.vars["stormgen_data"], ensure_ascii=False, allow_nan=False)
        quoted = json.dumps(data, ensure_ascii=False)
        return f"$stormgen_data = $lib.json.load({quoted})\n{self.text}\n"


class StormCompiler:
    """Bind literal data separately from explicit Storm expressions."""

    def __init__(self) -> None:
        self.data: list[Any] = []

    def value(self, value) -> str:
        if isinstance(value, StormExpression):
            try:
                s_parser.parseEval(value.text)
            except s_exc.BadSyntax as error:
                raise ValueError(f"Invalid Storm expression {value.text!r}: {error}") from error
            return value.text
        index = len(self.data)
        self.data.append(value)
        return f"$stormgen_data.{index}"

    def primary(self, text: str) -> str:
        value, expression = utils.heading_value(text)
        return self.value(StormExpression(value) if expression else value)

    def compile(self, nodes: list[DocNode], comments: bool = False) -> StormProgram:
        self.data.clear()
        lines = ["$stormgen_nodes = ([])", "spin |"]
        for node in nodes:
            if node.parts:
                node.extract()
            try:
                if not re.fullmatch(r"[a-z_][a-z0-9_:]*", node.form):
                    raise ValueError(f"Invalid form heading {node.form!r}")
                edits = [f"{node.form}={self.primary(node.valu)}"]
                edits.extend(f"{prop.key}={self.value(prop.val)}" for prop in node.props)
                for tag in node.tags:
                    expression = f"+#{tag.name}"
                    if tag.interval is not None:
                        expression += f"={self.value(tag.interval)}"
                    edits.append(expression)
                    edits.extend(
                        f"+#{tag.name}:{prop.key.removeprefix(':')}={self.value(prop.val)}"
                        for prop in tag.props
                    )
                lines.append("[\n" + "\n".join(edits) + "\n]")
                for edge in node.edges:
                    operator = f"<({edge.verb})+" if edge.reverse else f"+({edge.verb})>"
                    for form, value in edge.targets:
                        primary = self.primary(value)
                        if primary != "*":
                            lines.append(f"$stormgen_target = {primary}")
                            primary = "$stormgen_target"
                        lines.append(f"[ {operator} {{ [ {form}={primary} ] }} ]")
                if comments and node.comment:
                    value = self.value(node.comment)
                    lines.append("$stormgen_source = $node.ndef()")
                    lines.append(
                        f"[ <(about)+ {{ [ meta:note=(stormgen.note, $stormgen_source, {value}) :text={value} ] }} ]"
                    )
                lines.extend(["$stormgen_nodes.append($node)", "spin |"])
            except ValueError as error:
                raise ValueError(f"Cannot compile {node!r}: {error}") from error
        lines.extend([
            "$stormgen_results = ([])",
            "for $stormgen_node in $stormgen_nodes { $stormgen_results.append($stormgen_node.pack()) }",
            "return($stormgen_results)",
        ])
        text = "\n".join(lines)
        try:
            s_parser.parseQuery(text)
        except s_exc.BadSyntax as error:
            raise ValueError(f"Invalid generated Storm: {error}") from error
        return StormProgram(text, {"stormgen_data": list(self.data)})