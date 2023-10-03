"""Errors for StormLib++."""


import synapse.exc as s_exc


class StormSyntaxError(Exception):
    """There was a syntax error in Storm code."""


class StormRaiseError(Exception):
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


class HttpCortexError(Exception):
    """An error occurred in HttpCortex."""


class HttpCortexLoginError(HttpCortexError):
    """Unable to login to Synapse with HttpCortex."""


class HttpCortexNotImplementedError(s_exc.SynErr, NotImplementedError):
    """Raised when HttpCortex doesn't implement a method.

    Wraps ``synapse.exc.SynErr`` so this can be caught by builtin Synapse tools.
    """


class HttpCortexJsonError(HttpCortexError):
    """Unable to parse JSON response from Synapse with HttpCortex."""
