# StormLib++'s own pytest plugin fails any test that uses a deprecated Synapse API, and the
# run for deprecations logged outside of a test. See stormlibpp/testing/__init__.py.
pytest_plugins = ["stormlibpp.testing"]
