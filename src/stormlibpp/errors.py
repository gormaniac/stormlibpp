"""Errors for StormLib++."""


class StormPkgError(Exception):
    """An error in a StormPkg."""


class StormPkgNoProtoError(StormPkgError):
    """The proto Yaml file for a StormPkg does not exist."""


class StormPkgResolveError(StormPkgError):
    """The package proto's directory for a StormPkg could not be resolved."""


class StormPkgBadDefError(StormPkgError):
    """The package proto's directory for a StormPkg could not be resolved."""
