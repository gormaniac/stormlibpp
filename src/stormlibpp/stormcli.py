# Copyright (c) 2024, John Gorman
# Licensed under the MIT License
#
# Portions of this file are derived from the Synapse project:
#   https://github.com/vertexproject/synapse
# Copyright (c) The Vertex Project
# Licensed under the Apache License, Version 2.0.
#
# Modified for use in the stormlibpp project.


"""Methods related to using the synapse.tools.storm Storm CLI."""


import synapse.tools.storm as s_storm


async def start_storm_cli(core, outp, opts, onecmd=[]):
    """Start a ``synapse.tools.storm.StormCli`` but with a configurable Cortex.

    Adopted from ``synapse.tools.storm.StormCli.main()`` and modified to
    be a standalone function.

    This allows us to support HttpCortex based CLIs. Also gives us a convenient way to
    start a Storm CLI programmatically.

    Parameters
    ----------
    core : synapse.cortex.Cortex
        The Cortex object to use for the Storm CLI. This can be a local Cortex, 
        a Telepath proxy to a Cortex, an HttpCortex object, or any Cortex subclass.
    outp : file-like object
        The output stream for the Storm CLI.
    opts : dict
        A dictionary of options to configure the Storm CLI.
        See the Synapse documentation on Storm Opts. StormLib++ code uses this to set
        the ``view`` option for the Storm CLI rather than making it a separate param.
    onecmd : list, optional
        A Storm command to run and exit, by default [].
    """

    async with await s_storm.StormCli.anit(core, outp=outp, opts=opts) as cli:

        if onecmd:
            await cli.runCmdLine(onecmd)
            return

        completer = s_storm.StormCompleter(cli)
        cli.completer = completer
        await completer.load()

        cli.colorsenabled = True
        cli.printf(s_storm.welcome)
        await cli.addSignalHandlers()
        await cli.runCmdLoop()
