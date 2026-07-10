import os
import sys
sys.path.insert(0, os.path.abspath("../src"))

project = "stormlibpp"
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
html_theme_options = {
    "analytics_id": "G-6G9XWTWCQG",
    "accent_color": "teal",
    "color_mode": "auto",
    "nav_socials": [
        {
            "name": "GitHub",
            "url": "https://github.com/gormaniac/stormlibpp",
            "icon": "simple-icons:github",
        },
    ],
    "foot_socials": [
        {
            "name": "GitHub",
            "url": "https://github.com/gormaniac/stormlibpp",
            "icon": "simple-icons:github",
        },
    ]
}

html_static_path = ["_static"]
html_title = "StormLib++ Docs"

# notfound_urls_prefix = None
# notfound_context = {
#     "title": "Page Not Found",
#     "body": "This is not the page you're looking for."
# }

myst_enable_extensions = ["colon_fence"]

html_theme_options = {
    "analytics_id": "G-6G9XWTWCQG"
}
