# Stormgen Design Notes

Stormgen is a tool that will be able to convert structured Markdown documentation into Storm node tuples that can be used with a Synapse Cortex's proxy methods to create or update nodes.

An example document can be found in `tests/data/stormgen-example.md` that demonstrates (almost) all of stormgen's expected features.

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

Stormgen does support 

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


# Appendix
Saving this code for now
```python
class Section:
    """All Markdown tokens between two headings of the same level.
    
    ``Section``s are organized into a list of ``Part``s. Each part
    is all content between two headings including the first heading.

    A "root section" is a ``Section`` that exists because there is no top level
    heading in the original Markdown document. This section cannot have a level
    because there is no heading, so ``level`` will equal 0.

    A root section is created when no ``heading`` is passed to the constructor.
    """

    def __init__(self, heading: marko.block.Heading | None = None) -> None:
        self.heading = heading
        self.cur = Part(self.heading)
        self.level = 0
        self.parts: list[Part] = [self.cur]

        self.root = True if heading is None else False
        """The root section holds all blocks that exists before any headings."""

        if not self.root:
            self.level = heading.level

    def add_part(self, heading: marko.block.Heading):
        # The first part will always be in the list.
        if self.cur not in self.parts:
            self.parts.append(self.cur)
        self.cur = Part(heading)

    def add_block(self, block: marko.block.BlockElement):
        self.cur.add_block(block)

def parse(self) -> list[Section]:
    section = Section()
    for child in self.ast.children:
        if isinstance(child, marko.block.Heading):
            if section.level <= child.level:
                self.sections.append(section)
                section = Section(heading=child)
            else:
                section.add_part(child)
        section.add_block(child)
    return
```
