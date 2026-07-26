import os
import sys
sys.path.insert(0, os.path.abspath("../src"))

project = "StormLib++"
copyright = "2023, John Gorman"
author = "John Gorman"

extensions = [
    "sphinx.ext.autodoc",
    "myst_parser",
#     "notfound.extension"
]

templates_path = ["_templates"]
exclude_patterns = []

html_theme = "shibuya"
html_static_path = ["_static"]
html_title = "StormLib++ Docs"

# notfound_urls_prefix = None
# notfound_context = {
#     "title": "Page Not Found",
#     "body": "This is not the page you're looking for."
# }

myst_enable_extensions = ["colon_fence"]

html_baseurl = 'https://docs.gormo.co/stormlibpp/'

html_theme_options = {
    "accent_color": "teal",
    "color_mode": "auto",
    "nav_socials": [
        {
            "name": "GitHub",
            "url": "https://github.com/gormaniac/stormlibpp",
            "icon": "simple-icons:github",
        },
        {
            "name": "PyPI",
            "url": "https://pypi.org/project/stormlibpp/",
            "icon": "simple-icons:pypi",
        },
    ],
    "foot_socials": [
        {
            "name": "GitHub",
            "url": "https://github.com/gormaniac/stormlibpp",
            "icon": "simple-icons:github",
        },
        {
            "name": "PyPI",
            "url": "https://pypi.org/project/stormlibpp/",
            "icon": "simple-icons:pypi",
        },
    ]
}
