"""The stormlibpp Python Package.

StormLib++ provides a number of Python objects to make life as a Synapse/Storm
developer easier.

StormLib++ has several useful utility functions in ``utils``.

StormLib++ errors can be found in ``errors``. Each componenent of StormLib++
uses these errors their own way. Information our how they're used can be found
in those components.

``StormPkg`` is a helper class that represents a Storm package in memory. It
can read a package prototype from a default (or configured) location, convert
it to a package definition, optionally check the Storm code's syntax (enabled
by default), and store a Python dict containing the Storm package's definition.

``StormPkg`` also provides some helpful properties to describe the Storm
package's configuration (`cmds`, `mods`, `pkg_guid`, `pkg_name`, `pkg_ver`, `storm`).

The ``telepath`` module has methods and classes for working with Telepath endpoints.
It currently contains mostly classes for describing standard Telepath API
return values.

``StormNode`` is a class giving users access to a Python API that can interface
with a Storm Node that is sent to a Python runtime either through Telepath RPC
or as a return message from an HTTP API call. It allows for unpacking of node
tuples into objects as well as repacking for use in Cortex methods. Edits to the
object can be made and later reflected when repacking the node.

The ``node`` module also contains some Python typing primitives for Storm Nodes.

``HttpCortex`` is a fake ``synapse.cortex.Cortex`` object that communicates over
HTTP instead of Telepath. This object can be passed around in place of a ``Cortex``
to support non-standard deployments that are unable use Telepath. Currently, it
only supports the ``storm`` and ``callStorm`` methods.

``hstorm`` is a submodule designed to be run as a CLI script. It starts a Storm
CLI that uses an ``HttpCortex`` object rather than a ``synapse.cortex.Cortex``.
This script uses the same ``synapse.tools.storm.StormCli`` object that the official
CLI relies on to handle IO and the command loop. So everything should feel
familiar to those used to Synapse's builtin tools.

``tmpcortex`` is another CLI script that allows users to start a throwaway Cortex
that can be used for testing other tools. It creates a user (``test``) with password
(``test``) and starts the HTTP API over port ``4443``. Future versions of this
script will support custom Cortex configuration.
"""

__version__ = "0.8.4"

# TODO - Do we want to change this to only import submods, or do we even need that?
from . import errors
from . import utils
from .httpcore import HttpCortex
from .node import StormNode
from .stormpkg import StormPkg
from .telepath import genDefaultTelepathRetn, TelepathRetn
