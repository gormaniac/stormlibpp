"""Methods related to using the synapse.tools.storm Storm CLI."""


import synapse.tools.storm as s_storm


async def start_storm_cli(core, outp, opts, onecmd=[]):
    async with await s_storm.StormCli.anit(core, outp=outp, opts=opts) as cli:
        if onecmd:
            await cli.runCmdLine(onecmd)
            return

        cli.colorsenabled = True
        cli.printf(s_storm.welcome)
        await cli.addSignalHandlers()
        await cli.runCmdLoop()
