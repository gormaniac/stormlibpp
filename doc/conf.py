import os
import sys
sys.path.insert(0, os.path.abspath("../src"))

project = "stormlibpp"
copyright = "2023, John Gorman"
author = "John Gorman"

extensions = ["sphinx.ext.autodoc", "myst_parser", "notfound.extension", "sphinx.ext.githubpages"]

templates_path = ["_templates"]
exclude_patterns = []

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_title = "StormLib++ Docs"

notfound_no_urls_prefix = True

myst_enable_extensions = ["colon_fence"]

html_theme_options = {
    "analytics_id": "G-6G9XWTWCQG"
}
