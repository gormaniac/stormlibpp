# Stormgen Design Notes

Stormgen converts structured Markdown documentation into packed node data or compiled Storm that can create and update nodes, tags and edges in a Synapse Cortex.

An example document can be found in `tests/data/stormgen-example.md` that demonstrates (almost) all of stormgen's expected features.

## Implementation status

Markdown extraction, constant-safe node conversion, Storm compilation, asynchronous application, optional documentation notes and the compiler CLI are implemented. Images, attachments, report publication and review tooling remain outside this implementation.

Extraction is available offline:

```python
from stormlibpp import stormgen

doc = stormgen.parse(markdown_text)
nodes = stormgen.extract(doc)
for node in nodes:
    node.extract()
    print(node.form, node.valu, node.props, node.tags, node.edges)
```

The entry modes retain their existing API names:

- `full` (default): form headings at `form_level` (default 2), with node headings immediately below.
- `forms`: a required `form` argument and level-1 node headings; non-heading preamble content is rejected.
- `embedded`: every bounded `Nodes` region, including `Nodes (form)` regions. `nodes_header` customizes the heading name. Regions end at the next heading of the same or shallower level. A supplied `form` is the fallback for a plain nodes heading.

`form_level=4` supports non-default form levels in full-document mode through `extract`, `convert`, `compile_storm` and `apply`. Extracted nodes preserve source order and own only their headings and descendants within their form or embedded region. Repeated `parse()` and node `extract()` calls do not accumulate duplicates.

Structural headings must use ATX syntax (`#`, `##`, etc.). Setext headings underlined with `=` or `-` are explicitly rejected with `ValueError`, rather than silently ignored.

Heading comments start at the last unescaped ` // ` separator. Escape a literal separator as `\//`; the existing doubled-backslash spelling `\\//` is also supported. Escapes survive inline Markdown formatting, and the resulting literal separator is not reinterpreted as a Storm comment during conversion or compilation.

Property values use the first direct fenced or indented code block, otherwise a flat Markdown list, otherwise a standalone inline-code line, otherwise an assignment in the property heading. Inline code inside prose is ignored. A code block's structural final newline is removed; internal newlines are retained. The one-line backtick examples in the fixture are inline code spans, not fenced blocks, and are explicitly supported even when they follow prose without a blank line.

Unlabelled code blocks and inline-code values remain literal text, except that constant Storm-list syntax in code blocks is recognized, including `(first, second)`, `([1, 2])` and `($lib.true, $lib.false, $lib.null)`. Builtin boolean/null constants resolve recursively inside nested constant lists without executing a runtime; quoted builtin names remain strings. A `text` fence forces literal interpretation. Markdown lists contain literal strings. Inline assignments and code fences labelled `storm` produce `StormExpression` objects containing unevaluated source; use a `storm` fence for runtime expressions, including lists containing runtime values. Primary headings and edge target values also remain source text. Extraction never evaluates Storm or validates values against a live Synapse model.

Tags expose `name`, optional `interval`, and `props`. Edge statements expose `verb`, `reverse` and ordered `(form, value)` targets. Lists directly under `Edges` remain documentation, not statements. Missing values and malformed structural tag/edge/list definitions raise `ValueError` with the relevant heading or target. Unknown node sections and descendants below property headings are ignored.

### Conversion, compilation and application

`convert(doc)` returns offline `StormNode` objects for literal and constant values. Property-name colons and tag-name hashes are removed in packed data; universal-property dots are retained. Array values become tuples, and constant tag intervals are normalized to milliseconds. Other values are not normalized against a model. Constants are resolved through Synapse's expression AST without executing arbitrary code. Bare numbers retain Storm's semantics: `42` is text, while `(42)` is numeric. Generated or composite primary values, runtime expressions, edges and `comments=True` require `apply` and raise a capability error during offline conversion rather than being silently omitted. Existing positional arguments and the custom extractor hook are preserved; a custom extractor must accept the `form_level` keyword when a non-default level is requested.

```python
literal_doc = stormgen.parse("## inet:fqdn\n### example.com\n")
packed_nodes = [node.pack() for node in stormgen.convert(literal_doc)]

program = stormgen.compile_storm(doc)
result = await cortex.callStorm(program.text, opts={"vars": program.vars})

nodes = await stormgen.apply(doc, cortex, comments=True, opts={"vars": {"label": "example"}})
```

`compile_storm` returns a `StormProgram` with `text` and `vars`; these must be passed together. `program.to_storm()` returns standalone source containing its literal data. Literal Markdown values are bound as data, not interpolated into executable source. Primary values use Storm value syntax when valid, with ordinary free-text headings safely bound as literal text. Malformed explicit expressions and malformed form headings are rejected before submission.

`apply` accepts a caller-provided object implementing `callStorm`, including a Cortex, Telepath proxy or `HttpCortex`. It preserves caller options without modifying them, handles HTTP response envelopes and restores packed tuple representations. Names beginning with `stormgen_` are reserved for generated variables. Runtime expressions may refer to caller variables. Edge-target expressions are evaluated in the source node's context before entering the target subquery; wildcard edge targets generate fresh nodes.

Definitions execute in document order, once per definition even if the caller supplies input node idens. GUID seeds and explicit identities resolve through Synapse; wildcard GUIDs are generated once for each applicable definition and reused for its edits and edges. Edge target definitions may create nodes that later definitions update. The returned list preserves definition order and contains final normalized source-node states, including repeated identities. Explicit updates do not remove unspecified properties, tags or edges. Syntax/structural errors are detected before execution where possible; model, permission and runtime failures propagate. Application is not guaranteed atomic, so a failure may leave earlier edits applied.

With `comments=True`, direct narrative under each node heading becomes a `meta:note` with an outgoing `about` edge to that source node. Headings, code blocks and descendant documentation are excluded. A note identity is seeded from the source ndef and rendered narrative, so reapplying identical documentation does not create duplicate notes. Changed narrative creates a new note; old notes are not automatically deleted. The default `comments=False` creates no notes.

**Trust boundary:** documents containing Storm expressions are executable input. Only compile/apply trusted documents under appropriately scoped Cortex permissions; syntax validation is not a sandbox.

### Compiler CLI

The CLI prints standalone Storm to standard output and never connects to a Cortex:

```sh
python -m stormlibpp.stormgen tests/data/stormgen-example.md
python -m stormlibpp.stormgen nodes.md --doc-type forms --form inet:fqdn
python -m stormlibpp.stormgen - --doc-type embedded --nodes-header Nodes --comments
```

Options include `--doc-type`, `--form`, `--form-level`, `--nodes-header` and `--comments`. A file argument of `-` reads standard input. Input and compilation errors produce a nonzero exit status.

The canonical example uses the custom string tag property `tlp`, which must already be defined in the target Cortex. The integration test registers it explicitly. Example GUIDs and data are illustrative; wildcard nodes and newly introduced edge targets are intentional.

The regression suite is `tests/test_stormgen.py`; run `python -m pytest tests/test_stormgen.py -q` in the project environment. It covers extraction, typed constants, compilation, in-memory Cortex application, both edge directions, source-dependent targets, GUID generation/seeds, HTTP-shaped responses, option preservation, notes, literal-data safety, Unicode, errors and the CLI. The canonical example is tested both for extraction and live application. Verification uses Marko 2.2.5 and Synapse 2.257.0; older supported dependency versions have not been certified by these runs. The manual scripts read the same fixture and do not execute during test collection.

## Use case

Stormgen exists so that Synapse analysts don't have to do the double work of both documenting their data model and creating the nodes, which often contain elements of the same documentation. This allows users to document the expected usage, explain any rules or restrictions, warn others of gotchas, and even provide examples for any part of their Synapse data model without storing them in the model itself. All while also including the contents of the node inline with the documentation, in some cases letting the node contents themselves do the heavy lifting of documenting the model. This provides an easy avenue to train other analysts on new model designs, or give new analysts a model reference document to help them explore a particular Synapse instance's data model without querying it.

This type of documentation is most helpful for static (or at least less volatile) information that often has to be included in a Synapse instance for analysts to get the most value from it. This includes things like the  `*:taxonomy` forms, organization specific `syn:tag`s, custom forms, and commonly used `geo:*`/`ou:*`/`ps:*`/`pol:*`/`risk:*`/`transport:*` forms. Stormgen facilitates the bulk creation of these nodes as well, reducing work time for analysts/engineers trying to quickly populate a Synapse instance with supporting data.

Stormgen is also useful to document the abstract concepts (e.g. threat groups, malware families, attack campaigns) that typically need several nodes of different forms to describe it. Consumers of Synapse data expect things like this to be in one place. Analysts also typically want to document such things in one place. It is burdensome on the analyst to document things as queries, expecially when documenting complex relationships all related to one thing, long form text is more natural. Analysts that write reports on technical concepts can also benefit from long form expression of nodes embedded within the report itself.

Several case studies are below:

-----

Let's take threat groups (clusters) as an example, our example group is called `tc123`. A user with little to no Synapse experience that wants to learn about `tc123` shouldn't have to know the query `risk:threat:name=tc123`. And know that to pivot to all techniques used by this threat group they should add `-(uses)> ou:technique` to the original query. They expect to search a documentation page for the term  `tc123` and find everything they need to know. Users can then use this documentation to pivot to Synapse to learn more.

Analysts that are new to this particular threat group will also want to know all of the other "documentation-like" nodes that are related to the `risk:threat`. Like the group's `ou:org` or `ps:contact`.

The analyst that creates `risk:threat:name=tc123` will want a way to document all things related to this group in one place. Without stormgen, they would need to write (and execute) multiple queries to create nodes that have many properties, some of which are meant to be long form text. This could lead to errors, frustration, and lots of copy pasta for the analyst - eating up valuable time.

-----

An analyst wants to publish a report on a recent incident. The analyst needs to include indicators in Synapse to accompany the report, and tag them appropriately. The analyst will also need to create a `risk:attack` node, and all the various nodes necessary to fill out a `risk:atack`'s properties, to describe the incident. And internal processes dictate the creation of several additional nodes to document the incident response process. Suddenly, the short task of "write a few paragraphs to document this investigation" becomes incredibly complex.

The analyst should be able to write all of the above in a single document, with as little context switching as possible. Tooling or processes can remove the node definitions upon publication of the report if needed (or not if the audience would benefit 😉).

The analyst should not have to switch from natural language to query language in order to do the above.

The analyst should be able to include screenshots, or external references, without having to also ensure these are added to Synapse and properly edged to the relevant indicators. The analyst should also have a mechanism to include the long form report text in the model.

-----

An analyst team is trying to implement a review process before publishing new indicators or creating new abstract concepts. The team is using OSS Synapse and has no tooling or process in place to utilize splices merged from other views. The team needs a way to diff the past definition of a node and the proposed change. And also control the application of the change prior to approval. Even with good splice tooling, this can be a challenge for large edits.

Instead of writing complex Storm to handle this, the team can use stormgen paired with any version control system to gatekeep the deployment of new/updated nodes. This helpful for the more static or abstract values that should exist in Synapse, or the values that have significant enough importance to both be documented and have an impact if changed.

-----

To pair the last two examples... A junior analyst is writing an intelligence report that documents research uncovering a new threat group and the campaign they've carried out over the past few months. A senior analyst must review this report before it is published as well as ensure the modeling to support the report is accurate.

Doing this in two separate tasks is burdensome and duplicates efforts. It also decouples narrative from evidence, which can make understanding of analysis more difficult.

The junior analyst should be able to write this report and the data modeling in one document, push it to branch in a shared "intel reports" VCS repo, and open a PR to request review from others. The senior analyst can then review the PR, propose any changes, and approve the PR once done.

A CI/CD system can be used to enforce (or flag violations of) modeling requirements for certain forms, aiding the reviewing analyst. The CI/CD tooling can also be used to automatically build the nodes from the report once approved/merged and write them to Synapse. It could even publish the report to a website, or to another system for further review by other teams pre-publishing.

If the junior analyst needs to publish an edit to their report, including a retraction of an erroneous identification of a certain malware family (which would involve changing the node definitions too). The analyst can use this same PR process and the reviewing analyst will be able to easily diff the original report with the updates using existing VCS tooling.

-----

## Parsing design

Stormgen operates on nested headings to understand what values belong to which node. Stormgen must be able to parse a markdown document and understand what is the definition for a node and what isn't. Stormgen must be able to understand what form a given node needs to be without the user telling stormgen within each node definition.

This design proposes 3 different ways to gain an entrypoint into the markdown definition of nodes:

1. Treat the whole document as if it contains nodes of any type, with each node definition nested under a parent heading that describes the node's form (a "form heading").
    - Each form heading will be determined by a configurable "form heading level," by default 2, where any additional heading one level under the form heading is treated as  a node ("node heading"). Additional headings under a node heading will describe that particular node's properties or tags (as defined in "parsing a node").
    - This is the format that the example document uses.
    - Changing the default form heading level allows for placing form headers in different places throughout the document. This example uses a form heading level of 4:
    ```
    # Title
    ## Subtitle
    ### Sub-subtitle
    #### inet:ipv4
    .....
    ## Subtitle #2
    #### inet:fqdn
    .....
    ```
2. Treat the whole document as if it contains node headings of one form, which will be reported at runtime. Any level 1 headings in the document will be treated as node headings. Extra headings will not be ignored, this is a node only document, everything must be a valid node.
3. Read everything under a configurable "nodes heading" within a greater markdown document and treat it as a separate document parsed according to the rules of option 1.
    - This allows for embeddable nodes definitions.
    - When a "nodes heading" is defined at a certain markdown heading level, every heading level under the nodes heading will be parsed until a heading of the same level of the nodes heading is reached. This allows for continuing the document under the embedded nodes heading, like so:
    ```
    # Report title
    Lots of contents...
    ## Subtitle
    More contents...
    ### Nodes
    #### inet:ipv4
    ##### 1.2.3.4
    ## Another subtitle
    Different contents...
    ### Nodes
    #### inet:fqdn
    ##### example.com
    ## Appendix
    ### References
    Links to other content...
    ### Nodes (ou:org)
    A special nodes heading that defines the form of all nodes under it.
    #### ("A fake example org") // with comments
    ```

Once stormgen knows how to find markdown definitions of nodes, it extracts all of them and creates node definitions ("ndefs") for each one. Ndefs will eventually be created in Synapse in the top-bottom order that they appear in the markdown document. Unfortunately this means that if one node depends on another, it must be placed after the markdown definition of the node it depends on.

### Heading rules

Any free text under a heading must be treated as documentation content and not contents of the thing that the header defines. Contents of the actual thing a header defines must be included in a Markdown code block under that heading or as an additional heading.

Headings that are eventually used as Storm values should be treated as is. So headings don't need code blocks underneath them to define a value. Instead they may define the value within the heading as a full Storm expression (`#### :text="example"`, `##### #test.tag.with.timestamps=(2123-04-05, 2468-10-12)`). This means that node headings will be passed directly as the nodes primary property in the ndef that storm gen produces.

Headings should support comments so that those headings that would be GUIDs can be annotated with a human readable values that don't interfere with node generation.

### Node parsing

The rules for node parsing can be applied to anything that is considered an "element" by stormgen (tags are also considered elements).

Nodes should be parsed based on the following rules:

1. The value in the title of the node heading is used as the node's primary property. It is used as is when creating the node's ndef.
2. Any heading one level under the node that starts with a colon or period will be considered a "property heading."
    - Any additional heading under these property headings will be ignored.
    - The first code block that is a child of this heading and not another will be used as the property's value.
        - Properties that need to be arrays may be a markdown list instead.
        - However, using a Storm list as the value in a code block is also valid.
    - If a code block is missing under a property heading, and an equals sign is in the property title, the whole value of the title is used as is for the property.
3. Any other heading will be ignored by stormgen unless it matches any of stormgen's reserved headings. Currently:
    - `Tags`
    - `Edges`
4. The headings under `Tags` are treated as elements just like nodes are, so they are parsed with the same rules.
    - Tag headings must include the pound sign as if it was used in Storm.
5. The headings under `Edges` are parsed as "edge statements" while a list under `Edges` is treated as "edge documentation" - the parsing rules for edges are as follows:
    - "edge statements" are parsed like elements, except the value must be a list of full node expressions (`<form>=<valu>`). The heading is the type of edge to make between the source node and every single node in the list under the heading.
    - "edge documentation" is ignored when parsing a node. It is intended for analysts to describe the *expected* edges one can find on that particular node.

## Definitions

- `node heading`: A markdown heading that desribes the start of a single node definition. The value of this heading is used as the primary property for the node that is being defined.
- `form heading`: A markdown heading that defines the Synapse form to use for all node definitions that are one level below this heading.
- `nodes document`: A markdown document that stormgen parses to look for node definitions. This may be a subset of another document.
- `nodes heading`: A special heading used to tell stormgen that all headings below this one until the next heading of the same level is reached will be treated as a single nodes document and should be parsed for node definitions. A nodes heading can also be a forms heading if it defines a single form within parentheses next to the configured nodes heading value.
- `property heading`: A heading that defines a property in an element.
- `element`: A piece of a `nodes document` that can be parsed according to the node parsing rules (or perhaps that can be parsed into Synapse data? not sure if we want to make "edge statments" elements also or treat them totally differently).
- `tags heading`: The tag elements that are defined for a given source node.
- `edges heading`: A reserved heading (`Edges`) under a source node that can define multiple edge statements and/or a single edge documentation list.
- `edge statement`: A special heading+list pair that will be turned into edges of one type (the value of the heading) between the node being defined and the form/valu pairs in the list.
- `edge documentation`: An arbitrary list under an edges heading that documents the possible edges types that the source node may use.
- `source node`: The node being defined in the current context.
