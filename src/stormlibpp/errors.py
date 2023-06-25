"""Errors for StormLib++."""


class StormSyntaxError(Exception):
    """There was a syntax error in Storm code."""


class StormPkgError(Exception):
    """An error in a StormPkg."""


class StormPkgNoProtoError(StormPkgError):
    """The proto Yaml file for a StormPkg does not exist."""


class StormPkgResolveError(StormPkgError):
    """The package proto's directory for a StormPkg could not be resolved."""


class StormPkgBadDefError(StormPkgError):
    """The package proto's directory for a StormPkg could not be resolved."""

class StormPkgSyntaxError(StormPkgError, StormSyntaxError):
    """The Storm code defined in a StormPkg has a syntax error."""
