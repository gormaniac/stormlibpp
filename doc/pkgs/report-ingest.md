# report-ingest

```{warning}
This will soon be replaced with a more robust Synapse Advanced Power-Up
```

A tool to download Threat Intel reports (or really any article) from the web, model them as `media:news` nodes, and optionally scrape any potential nodes from the downloaded text.

This tool is barebones, it passes all returned contents to the "$lib.scrape" API. Meaning all URLs on an HTML page will be parsed and created, like javascript, or navigation links to other parts of a website. Keep this in mind when you choose to scrape results, creating tagging or node pruning will be needed to ignore results.

This tool also does not save the contents of the HTML to the graph, if an Axon is available raw bytes are stored there.

All requests are made directly from the Cortex, without a proxy. DO NOT query untrustworthy infrastructure with this tool.

## Examples

```
// Create a new inet:url then pass it to slib.report.ingest without any options. Without options, this is almost useless, a media:news is created along with the response stored in the Axon.
[inet:url="https://example.com"] | slib.report.ingest 

// Scrape all possible nodes from the HTML response and yield them.
[inet:url="https://example.com"] | slib.report.ingest --scrape --yield

// Do the above but also create a -(refs)> edge from the media:news to all scraped nodes.
[inet:url="https://example.com"] | slib.report.ingest --scrape --refs --yield
```
