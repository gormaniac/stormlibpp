# Title

Free text under a heading allows for documentation.

## inet:ipv4
This is a group of inet:ipv4 nodes that are important enough to document.

### 1.2.3.4

Explain stuff about this specific inet:ipv4 here.

Comments directly under a primary property title may optionally be saved as `meta:notes` that get edged to this node.

Images linked in this section should be saved to Synapse and edged to this node too (a wishlist feature).

#### :dns:rev

To set values on properties, use a code block. Free text still serves as documentation.
```
example.com
```

#### :place
You can code block on one line for ease of use
```AU```

#### :loc="-27.4820,153.0136"
Or you can place the value directly in the heading.

### 1.1.1.1

Primary properties are the only required heading needed for a node.

## inet:fqdn

### example.com

This will be automatically created by our `inet:ipv4=1.2.3.4`'s `:rev:dns` example. But now we can add custom things to it.

#### Tags

Tags are also supported. They can have properties set on them just like nodes.

Notice the title for this section uses a capital letter and does not start with a colon or period. This is how node tags are differentiated from any node properties.

##### #test.tag

You still need to start tag titles with pound signs - as with all other titles, values are used as is.

###### :tlp
```green```

##### #test.time=(2023-02-01, 2023-04-05)

Since tag titles are also used as is, timestamps are supported.

## it:prod:soft

### (vscode, dev.ide)

Primary properties are used as is. So seed values as primary properties for guid nodes are supported, just like in Storm.

#### :names

Values for arrays can be markdown lists instead of code blocks with Storm lists within them:

- Visual Studio Code
- Code

#### Edges

You can document all the kinds of edges a particular node should have.

- `<(uses)-`
    - `ou:org`
    - `risk:threat`
    - `it:prod:soft`
- `-(uses)>`
    - `it:prod:soft`

#### -(uses)>

Or actually create the edge.

- `it:prod:soft=(electron, dev.framework)`
- `it:prod:soft=(textmate, dev.helper)`

## ou:org

### *

You can have GUIDS generated for you.

#### :name
```Example LLC```

But you'll probably want to give it a property that can be used to reference it.

### aaa4e5bd9b308ba8a12fdf6d8e1756b9

Of course you can always use an already generated GUID too.

### 90b8547258ec52e1ce58309de2af73d7 // (microsoft)

Using only GUIDs (or asterisks for GUID generation) in documentation can get confusing. But they're still valuable for reference. So annotating titles with comments is supported by always splitting titles on the last ` // ` and throwing away everything to the right before using the title value.

It is best practice, if applicable, to use the seed values of a GUID in a comment.

## it:dev:str

### A string with a comment // separator in it // and now an actual comment

Only the last comment separator is recognized. So titles with `//` are still supported. This example would produce the node `it:dev:str="A string with a comment // separator in it"`.

### A string with an escaped \\// comment separator in it

This example would produce the node `it:dev:str="A string with a comment // separator in it"`.
