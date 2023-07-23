import os
import sys
sys.path.insert(0, os.path.abspath("../src"))

project = "stormlibpp"
copyright = "2023, John Gorman"
author = "John Gorman"

# TODO - Figure out how to control autodoc's order of things and default names
extensions = ["sphinx.ext.autodoc", "sphinx.ext.githubpages"]

templates_path = ["_templates"]
exclude_patterns = []

html_theme = "sphinx_rtd_theme"
html_static_path = []
