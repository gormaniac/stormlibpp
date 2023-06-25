"""The stormlibpp Python Package.

StormLib++ provides a number of Python objects to make life as a Synapse/Storm
developer easier.

StormLib++ provides several useful utility functions in ``utils``.

StormLib++ errors can be found in ``errors``. Each componenent of StormLib++
uses these errors their own way. Information our how they're used can be found
in those components.

``StormPkg`` is a helper class that represents a Storm package in memory. It
can read a package prototype from a default (or configured) location, convert
it to a package definition, optionally check the Storm code's syntax (enabled
by default), and store a Python dict containing the Storm package's definition.

``StormPkg`` also provides some helpful properties to describe the Storm
package's configuration (`cmds`, `mods`, `pkg_guid`, `pkg_name`, `pkg_ver`, `storm`).

There are also several submodules not directly imported by ``stormlibpp`` at
init. However, some classes/functions from these submodules are. The submodules
are briefly described below:

- ``telepath`` has methods and classes for working with Telepath endpoints.
  It currently contains mostly classes for describing standard Telepath API
  return values.

- ``stormpkg`` defines the ``StormPkg`` class.

"""

__version__ = "0.2.0"

from . import errors
from . import utils
from .stormpkg import StormPkg
from .telepath import (genDefaultTelepathRetn, TelepathRetn)
