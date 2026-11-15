"""Regression tests for Markdown node extraction and generation."""

from pathlib import Path
import json
from io import StringIO

import pytest
import synapse.exc as s_exc
import synapse.tests.utils as s_test

import stormlibpp.stormgen as stormgen


def test_embedded_regions_are_bounded_and_repeated():
    doc = stormgen.parse("""# Report
## Nodes
### inet:fqdn
#### first.example
## Narrative
### Not a form
#### Not a node
## Nodes
### inet:fqdn
#### second.example
""")
    nodes = stormgen.extract(doc, doc_type="embedded")
    assert [(node.form, node.valu) for node in nodes] == [
        ("inet:fqdn", "first.example"),
        ("inet:fqdn", "second.example"),
    ]


def test_embedded_fixed_form_and_shallower_boundary():
    doc = stormgen.parse("""# Report
### Nodes (inet:fqdn)
#### first.example
## Narrative
#### Not a node
### Nodes (inet:ipv4) // addresses
#### 1.2.3.4
""")
    assert [(node.form, node.valu) for node in stormgen.extract(doc, "embedded")] == [
        ("inet:fqdn", "first.example"), ("inet:ipv4", "1.2.3.4"),
    ]


def test_single_form_uses_top_level_nodes():
    doc = stormgen.parse("# first.example\n## :loc=us\n# second.example\n")
    nodes = stormgen.extract(doc, "forms", form="inet:fqdn")
    assert [node.valu for node in nodes] == ["first.example", "second.example"]
    assert [part.title for part in nodes[0].parts] == ["first.example", ":loc=us"]


def test_single_form_rejects_missing_form_and_preamble():
    with pytest.raises(ValueError, match="require a form"):
        stormgen.extract(stormgen.parse("# example.com"), "forms")
    with pytest.raises(ValueError, match="start with a node heading"):
        stormgen.extract(stormgen.parse("Preamble\n# example.com"), "forms", form="inet:fqdn")


def test_custom_form_level_and_scope_reset():
    doc = stormgen.parse("""# Report
#### inet:fqdn // domains
##### example.com
###### :loc=us
#### inet:ipv4
###### Not owned by example.com
## Narrative
##### Not a node
""")
    nodes = stormgen.extract(doc, form_level=4)
    assert [(node.form, node.valu) for node in nodes] == [("inet:fqdn", "example.com")]
    assert len(nodes[0].parts) == 2


def test_parse_is_repeatable_and_empty_documents_are_valid():
    doc = stormgen.parse("## inet:fqdn\n### example.com\n")
    before = len(doc.parts)
    doc.parse()
    assert len(doc.parts) == before
    assert stormgen.extract(stormgen.parse("")) == []


@pytest.mark.parametrize("level", [0, 6, "2"])
def test_invalid_form_level(level):
    with pytest.raises(ValueError, match="form_level"):
        stormgen.extract(stormgen.parse(""), form_level=level)


def extract_node(body, heading="example.com"):
    node = stormgen.extract(stormgen.parse(f"## inet:fqdn\n### {heading}\n{body}"))[0]
    node.extract()
    return node


@pytest.mark.parametrize(("body", "expected"), [
    ("#### :name\n```\nExample LLC\n```\n", "Example LLC"),
    ("#### :name\n```Example LLC```\n", "Example LLC"),
    ("#### :name\nDocumentation\n```Example LLC```\n", "Example LLC"),
    ("#### :name\n    Example LLC\n", "Example LLC"),
    ("#### :name=example\n", stormgen.StormExpression("example")),
    ("#### :name\n```storm\n$lib.str.format('{name}', name=example)\n```\n",
     stormgen.StormExpression("$lib.str.format('{name}', name=example)")),
    ("#### :names\n- Visual Studio Code\n- `Code`\n", ["Visual Studio Code", "Code"]),
    ("#### :name=ignored\nDocumentation\n```first```\n\n```\nchosen\n```\n", "chosen"),
    ("#### :name\n```\nfirst\n```\n\n```\nsecond\n```\n", "first"),
    ("#### :name\n```\nfirst\n\nsecond\n\n```\n", "first\n\nsecond\n"),
])
def test_property_values(body, expected):
    assert extract_node(body).props[0].val == expected


def test_properties_ignore_narrative_and_descendant_headings():
    node = extract_node("""Node narrative.
#### :name
Documentation is not a value.
```
chosen
```
##### :ignored=other
#### Notes
##### :ignored=again
#### .seen=(2020, 2021)
""")
    assert node.props == [
        stormgen.Prop(":name", "chosen"),
        stormgen.Prop(".seen", stormgen.StormExpression("(2020, 2021)")),
    ]
    assert node.comment == "Node narrative."


@pytest.mark.parametrize("body", [
    "#### :name\nOnly documentation.\n",
    "#### :name=\n",
    "#### :names\n- outer\n  - nested\n",
])
def test_invalid_property_values(body):
    with pytest.raises(ValueError, match="heading"):
        extract_node(body)


def test_inline_code_in_prose_is_not_a_value():
    with pytest.raises(ValueError, match="Missing value"):
        extract_node("#### :name\nDo not extract `this example` from prose.\n")


def test_tag_ownership_properties_and_last_entry():
    node = extract_node("""#### Tags
##### #test.first
###### :score=10
##### #test.last=(2020, 2021)
###### :label
```green```
#### Narrative
##### This is not a tag
###### :ignored=1
""")
    assert [tag.name for tag in node.tags] == ["test.first", "test.last"]
    assert node.tags[0].props == [stormgen.Prop(":score", stormgen.StormExpression("10"))]
    assert node.tags[1].interval == stormgen.StormExpression("(2020, 2021)")
    assert node.tags[1].props == [stormgen.Prop(":label", "green")]
    node.extract()
    assert len(node.tags) == 2
    assert len(node.tags[0].props) == 1


def test_edge_statements_ignore_documentation_and_preserve_equals():
    node = extract_node("""#### Edges
- `-(documents)>`
  - `inet:fqdn`
##### -(uses)>
- `inet:fqdn=target.example`
- `it:dev:str="contains=equals"`
##### <(seen)-
- `inet:ipv4=1.2.3.4`
#### Notes
##### Not an edge
""")
    assert [(edge.verb, edge.reverse) for edge in node.edges] == [("uses", False), ("seen", True)]
    assert node.edges[0].targets == [
        ("inet:fqdn", "target.example"), ("it:dev:str", '"contains=equals"'),
    ]
    assert node.edges[1].targets == [("inet:ipv4", "1.2.3.4")]


@pytest.mark.parametrize(("body", "message"), [
    ("#### Tags\n##### test.missing.hash\n", "Invalid tag"),
    ("#### Tags\n##### #test=\n", "Invalid tag"),
    ("#### Edges\n##### uses\n- inet:fqdn=example.com\n", "Invalid edge heading"),
    ("#### Edges\n##### -(uses)>\n", "Missing target list"),
    ("#### Edges\n##### -(uses)>\n- example.com\n", "Invalid edge target"),
])
def test_invalid_tag_and_edge_elements(body, message):
    with pytest.raises(ValueError, match=message):
        extract_node(body)


def test_nested_inline_headings():
    node = extract_node("#### **:name**\n```Example```\n", heading="**example**.com")
    assert node.valu == "example.com"
    assert node.props == [stormgen.Prop(":name", "Example")]


def test_canonical_example_extracts_all_elements():
    text = Path(__file__).with_name("data").joinpath("stormgen-example.md").read_text()
    nodes = stormgen.extract(stormgen.parse(text))
    for node in nodes:
        node.extract()
    assert len(nodes) == 9
    assert nodes[0].props[:2] == [
        stormgen.Prop(":dns:rev", "example.com"),
        stormgen.Prop(":place", "0123456789abcdef0123456789abcdef"),
    ]
    assert [tag.name for tag in nodes[2].tags] == ["test.tag", "test.time"]
    assert nodes[3].props == [stormgen.Prop(":names", ["Visual Studio Code", "Code"])]
    assert nodes[3].edges[0].targets == [
        ("it:prod:soft", "(electron, dev.framework)"),
        ("it:prod:soft", "(textmate, dev.helper)"),
    ]
    assert nodes[-2].valu == "A string with a comment // separator in it"
    assert nodes[-1].valu == "A string with an escaped // comment separator in it"


def test_literal_conversion_populates_packed_nodes():
    nodes = stormgen.convert(stormgen.parse("""## inet:fqdn
### example.com
#### :name
```Example LLC```
#### :aliases
- First alias
- Second alias
#### :score=(42)
#### .seen=(2020,2021)
#### Tags
##### #test
###### :confidence=(100)
"""))
    assert len(nodes) == 1
    assert nodes[0].value == "example.com"
    assert vars(nodes[0].props) == {
        "name": "Example LLC", "aliases": ("First alias", "Second alias"),
        "score": 42, ".seen": ("2020", "2021"),
    }
    assert vars(nodes[0].tags) == {"test": (None, None)}
    assert nodes[0].tagprops == {"test": {"confidence": 100}}


@pytest.mark.parametrize("body", [
    "## ou:org\n### *\n",
    "## ou:org\n### (example, seed)\n",
    "## ou:org\n### $lib.guid()\n",
    "## inet:fqdn\n### example.com\n#### :name=$lib.guid()\n",
    "## inet:fqdn\n### example.com\n#### Tags\n##### #test=$interval\n",
    "## inet:fqdn\n### example.com\n#### Edges\n##### -(uses)>\n- inet:fqdn=target.com\n",
])
def test_offline_conversion_rejects_runtime_operations(body):
    with pytest.raises(ValueError, match=r"require.*stormgen.apply"):
        stormgen.convert(stormgen.parse(body))


def test_offline_constant_lists_and_tag_intervals():
    doc = stormgen.parse("""## ou:org
### 0123456789abcdef0123456789abcdef
#### :names
```
(first, second)
```
#### Tags
##### #test=(2020,2021)
""")
    nodes = stormgen.convert(doc)
    assert nodes[0].value == "0123456789abcdef0123456789abcdef"
    assert nodes[0].props["names"] == ("first", "second")
    assert nodes[0].tags["test"] == (1577836800000, 1609459200000)


@pytest.mark.parametrize(("language", "value", "expected"), [
    ("", "([1, 2])", stormgen.StormExpression("([1, 2])")),
    ("text", "(first, second)", "(first, second)"),
    ("", "(ordinary text)", "(ordinary text)"),
    ("", "($lib.guid(), other)", "($lib.guid(), other)"),
])
def test_code_block_list_and_literal_disambiguation(language, value, expected):
    node = extract_node(f"#### :names\n```{language}\n{value}\n```\n")
    assert node.props[0].val == expected


def test_custom_extractor_retains_positional_contract():
    calls = []

    def extractor(doc, doc_type, nodes_header, form):
        calls.append((doc, doc_type, nodes_header, form))
        return []

    doc = stormgen.parse("")
    assert stormgen.convert(doc, doc_type="forms", nodes_header="Data", form="inet:fqdn", extractor=extractor) == []
    assert calls == [(doc, "forms", "Data", "inet:fqdn")]


def test_empty_node_and_repeated_property_extraction():
    empty = stormgen.DocNode("inet:fqdn", "empty.example")
    empty.extract()
    assert empty.props == empty.tags == empty.edges == []
    node = extract_node("#### :name\n```Example```\n")
    node.extract()
    assert node.props == [stormgen.Prop(":name", "Example")]


def test_custom_embedded_heading_and_form_fallback():
    doc = stormgen.parse("## Data\n### example.com\n## Narrative\n### Not a node\n")
    nodes = stormgen.extract(doc, "embedded", nodes_header="Data", form="inet:fqdn")
    assert [(node.form, node.valu) for node in nodes] == [("inet:fqdn", "example.com")]


def test_compiler_binds_literal_data_instead_of_interpolating_it():
    dangerous = 'quotes " and ] { $lib.exit() }'
    doc = stormgen.parse(f"## it:dev:str\n### ordinary text with spaces\n#### .source\n```\n{dangerous}\n```\n")
    program = stormgen.compile_storm(doc)
    assert dangerous not in program.text
    assert dangerous in program.vars["stormgen_data"]
    assert "ordinary text with spaces" in program.vars["stormgen_data"]


@pytest.mark.parametrize("value", ["$lib.guid(", '"unterminated', "(missing, close"])
def test_compiler_rejects_malformed_expressions(value):
    doc = stormgen.parse(f"## ou:org\n### {value}\n")
    with pytest.raises(ValueError, match="Invalid Storm"):
        stormgen.compile_storm(doc)


class TestStormgenApply(s_test.SynTest):
    async def test_apply_order_identity_properties_tags_and_edges(self):
        doc = stormgen.parse("""## ou:org
### (stormgen, seed)
#### :name
```Source organization```
#### Tags
##### #stormgen.test=(2020,2021)
###### :score=(10)
#### Edges
##### -(uses)>
- `inet:fqdn=target.example`
##### <(seen)-
- `inet:ipv4=1.2.3.4`
## inet:fqdn
### target.example
#### .seen=(2020,2021)
## ou:org
### *
#### :name=$lib.str.format('Generated {name}', name=organization)
""")
        async with self.getTestCore() as core:
            await core.addTagProp("score", ("int", {}), {})
            nodes = await stormgen.apply(doc, core)
            self.eq(3, len(nodes))
            self.eq("source organization", nodes[0].props["name"])
            self.eq((1577836800000, 1609459200000), nodes[0].tags["stormgen.test"])
            self.eq(10, nodes[0].tagprops["stormgen.test"]["score"])
            self.eq("target.example", nodes[1].value)
            self.eq((1577836800000, 1609459200000), nodes[1].props[".seen"])
            self.eq("generated organization", nodes[2].props["name"])
            source = (await core.nodes("ou:org:name='source organization'"))[0]
            target = (await core.nodes("inet:fqdn=target.example"))[0]
            incoming = (await core.nodes("inet:ipv4=1.2.3.4"))[0]
            self.eq([("uses", target.iden())], [edge async for edge in source.iterEdgesN1()])
            self.eq([("seen", source.iden())], [edge async for edge in incoming.iterEdgesN1()])
            again = await stormgen.apply(doc, core)
            self.eq(nodes[0].value, again[0].value)
            self.ne(nodes[2].value, again[2].value)

    async def test_empty_and_duplicate_definitions(self):
        async with self.getTestCore() as core:
            self.eq([], await stormgen.apply(stormgen.parse(""), core))
            doc = stormgen.parse("""## ou:org
### (stormgen, duplicate)
#### :name=first
### (stormgen, duplicate)
#### :name=second
""")
            nodes = await stormgen.apply(doc, core)
            self.eq(2, len(nodes))
            self.eq(nodes[0].value, nodes[1].value)
            self.eq("second", nodes[0].props["name"])
            self.eq("second", nodes[1].props["name"])

    async def test_http_shaped_results_bound_literals_and_options(self):
        async with self.getTestCore() as core:
            class HttpAdapter:
                async def callStorm(self, text, opts=None):
                    result = await core.callStorm(text, opts=opts)
                    return json.loads(json.dumps({"status": "ok", "result": result}))

            opts = {"vars": {"label": "caller-provided name"}}
            original = json.loads(json.dumps(opts))
            doc = stormgen.parse("""## ou:org
### (stormgen, http)
#### :name=$label
#### :names
- Quoted " text
- Literal ] { $lib.exit() }
#### Tags
##### #test=(2020,2021)
""")
            nodes = await stormgen.apply(doc, HttpAdapter(), opts=opts)
            self.eq(original, opts)
            self.eq("caller-provided name", nodes[0].props["name"])
            self.eq(('literal ] { $lib.exit() }', 'quoted " text'), nodes[0].props["names"])
            self.eq((1577836800000, 1609459200000), nodes[0].tags["test"])

    async def test_runtime_errors_and_invalid_responses(self):
        async with self.getTestCore() as core:
            doc = stormgen.parse("## inet:fqdn\n### example.com\n#### :not_a_property=invalid\n")
            with self.raises(s_exc.NoSuchProp):
                await stormgen.apply(doc, core)

        class ErrorAdapter:
            async def callStorm(self, text, opts=None):
                return {"status": "err", "code": "NoSuchProp", "mesg": "missing property"}

        with self.raises(ValueError):
            await stormgen.apply(stormgen.parse(""), ErrorAdapter())

    async def test_documentation_notes_are_optional_and_repeatable(self):
        doc = stormgen.parse("""## ou:org
### (stormgen, notes)
Direct documentation with **formatting** and "quotes".
#### :name
```Example organization```
#### Notes
This descendant narrative must not be in the note.
""")
        async with self.getTestCore() as core:
            await stormgen.apply(doc, core)
            self.eq([], await core.nodes("meta:note"))
            source = (await stormgen.apply(doc, core, comments=True))[0]
            notes = await core.nodes("meta:note")
            self.eq(1, len(notes))
            self.eq('Direct documentation with **formatting** and "quotes".', notes[0].get("text"))
            self.eq([("about", source.iden)], [edge async for edge in notes[0].iterEdgesN1()])
            await stormgen.apply(doc, core, comments=True)
            self.eq(1, len(await core.nodes("meta:note")))

    async def test_standalone_storm_preserves_literal_data(self):
        text = 'Quoted " text with \\backslash and caf\u00e9\nLiteral ] { $lib.exit() }'
        doc = stormgen.parse(f"## meta:note\n### *\n#### :text\n```\n{text}\n```\n")
        async with self.getTestCore() as core:
            program = stormgen.compile_storm(doc)
            packed = await core.callStorm(program.to_storm())
            self.eq(text, packed[0][1]["props"]["text"])

    async def test_escaped_heading_comment_separator_applies_as_literal(self):
        doc = stormgen.parse("## it:dev:str\n### Keep \\// this text\n")
        async with self.getTestCore() as core:
            nodes = await stormgen.apply(doc, core)
            self.eq("Keep // this text", nodes[0].value)
            packed = await core.callStorm(stormgen.compile_storm(doc).to_storm())
            self.eq("Keep // this text", packed[0][0][1])

    async def test_canonical_example_applies_to_cortex(self):
        text = Path(__file__).with_name("data").joinpath("stormgen-example.md").read_text()
        async with self.getTestCore() as core:
            await core.addTagProp("tlp", ("str", {}), {})
            nodes = await stormgen.apply(stormgen.parse(text), core)
            self.eq(9, len(nodes))
            self.eq("example.com", nodes[0].props["dns:rev"])
            self.eq("green", nodes[2].tagprops["test.tag"]["tlp"])

    async def test_source_dependent_edge_values_and_once_only_input(self):
        doc = stormgen.parse("""## it:dev:str
### source
#### Edges
##### -(uses)>
- `it:dev:str=$node.value()`
##### -(refs)>
- `ou:org=*`
""")
        async with self.getTestCore() as core:
            incoming = await core.nodes("[ inet:fqdn=one.example inet:fqdn=two.example ]")
            result = await stormgen.apply(doc, core, opts={"idens": [node.iden() for node in incoming]})
            self.eq(1, len(result))
            source = (await core.nodes("it:dev:str=source"))[0]
            edges = [edge async for edge in source.iterEdgesN1()]
            self.isin(("uses", source.iden()), edges)
            self.eq(2, len(edges))
            self.eq(1, len(await core.nodes("ou:org")))


@pytest.mark.parametrize("value", ["example.com", '"example.com"', "A literal with spaces"])
def test_offline_primary_literals(value):
    nodes = stormgen.convert(stormgen.parse(f"## it:dev:str\n### {value}\n"))
    assert nodes[0].value == value.strip('"')


def test_convert_custom_levels_and_no_partial_results():
    doc = stormgen.parse("#### inet:fqdn\n##### example.com\n")
    assert stormgen.convert(doc, form_level=4)[0].value == "example.com"
    converter = stormgen.NodesConverter(stormgen.extract(doc, form_level=4))
    converter.convert()
    converter.doc_nodes.append(stormgen.DocNode("ou:org", "*"))
    with pytest.raises(ValueError, match="require"):
        converter.convert()
    assert converter.storm_nodes == []


@pytest.mark.parametrize("operation", [stormgen.convert, stormgen.compile_storm])
def test_invalid_form_heading_cannot_be_compiled_or_converted(operation):
    doc = stormgen.parse("## not a form\n### example.com\n")
    with pytest.raises(ValueError, match="Invalid form"):
        operation(doc)


def test_cli_file_and_stdin(tmp_path, monkeypatch, capsys):
    from stormlibpp.stormgen.__main__ import main

    path = tmp_path / "nodes.md"
    path.write_text("# example.com\n", encoding="utf-8")
    assert main([str(path), "--doc-type", "forms", "--form", "inet:fqdn"]) == 0
    assert "$stormgen_data = $lib.json.load(" in capsys.readouterr().out
    monkeypatch.setattr("sys.stdin", StringIO("## inet:fqdn\n### example.com\n"))
    assert main(["-"]) == 0
    assert "inet:fqdn=example.com" in capsys.readouterr().out


@pytest.mark.parametrize("args", [["missing.md"], ["-", "--form-level", "0"], ["-", "--doc-type", "forms"]])
def test_cli_errors(args, monkeypatch, capsys):
    from stormlibpp.stormgen.__main__ import main

    monkeypatch.setattr("sys.stdin", StringIO(""))
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2
    assert "error:" in capsys.readouterr().err


@pytest.mark.parametrize(("heading", "expected"), [
    (r"Keep \// this text", "Keep // this text"),
    (r"Keep /\/ this text", "Keep // this text"),
    (r"Keep \\// this text", "Keep // this text"),
    (r"**Keep \// this text**", "Keep // this text"),
    (r"Keep \// this text // annotation", "Keep // this text"),
    (r"Keep \// first \// second // annotation", "Keep // first // second"),
    (r'"Keep \// this text"', "Keep // this text"),
    (r"Keep // earlier separator \// literal separator", "Keep"),
    (r"https:\/\/example.com", "https://example.com"),
])
def test_heading_comment_escapes_survive_markdown(heading, expected):
    doc = stormgen.parse(f"## it:dev:str\n### {heading}\n")
    source = f'"{expected}"' if heading.startswith('"') else expected
    assert stormgen.extract(doc)[0].valu == source
    assert stormgen.convert(doc)[0].value == expected


@pytest.mark.parametrize("text", [
    "Title\n=====\n",
    "inet:fqdn\n---\n### example.com\n",
    "## inet:fqdn\n### example.com\nProperty heading\n---\n",
])
def test_setext_headings_are_explicitly_rejected(text):
    with pytest.raises(ValueError, match="Setext.*#"):
        stormgen.parse(text)


@pytest.mark.parametrize(("source", "expected"), [
    ("($lib.true, $lib.false, $lib.null)", (True, False, None)),
    ("($lib.true, ($lib.false, $lib.null))", (True, (False, None))),
    ("([$lib.true, [$lib.false, $lib.null]])", (True, (False, None))),
    ('("$lib.true", $lib.true)', ("$lib.true", True)),
])
def test_nested_builtin_constants_in_code_blocks(source, expected):
    doc = stormgen.parse(
        f"## ou:org\n### 0123456789abcdef0123456789abcdef\n#### :values\n```\n{source}\n```\n"
    )
    node = stormgen.extract(doc)[0]
    node.extract()
    assert node.props[0].val == stormgen.StormExpression(source)
    assert stormgen.convert(doc)[0].props["values"] == expected


@pytest.mark.parametrize(("source", "expected"), [
    ("$lib.true", True), ("($lib.false)", False), (" $lib.null ", None),
])
def test_scalar_builtin_constants_use_ast_resolution(source, expected):
    assert stormgen.utils.constant_value(source) is expected


@pytest.mark.parametrize("source", ["($lib.guid(), $lib.true)", "($other.true, $lib.false)"])
def test_nested_runtime_values_are_not_resolved_offline(source):
    with pytest.raises(ValueError, match="Runtime Storm"):
        stormgen.utils.constant_value(source)