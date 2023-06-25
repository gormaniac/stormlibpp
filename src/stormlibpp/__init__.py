"""The stormlibpp Python Package.

StormLib++ provides a number of Python objects to make life as a Synapse/Storm
developer easier.

It also exposes a few of Synapses submodles with the following name mappings::

    synapse.common -> s_common
    synapse.exc -> s_exc
    synapse.genpkg -> s_genpkg

"""

__version__ = "0.1.2"


import synapse.common as s_common
import synapse.exc as s_exc
import synapse.tools.genpkg as s_genpkg
import synapse.lib.parser as s_parser

from . import errors
from . import utils
from .stormpkg import StormPkg
from .telepath import (genDefaultTelepathRetn, TelepathRetn)
