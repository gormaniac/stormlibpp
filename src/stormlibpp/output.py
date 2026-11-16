# Copyright (c) 2024, John Gorman
# Licensed under the MIT License
#
# Portions of this file are derived from the Synapse project:
#   https://github.com/vertexproject/synapse
# Copyright (c) The Vertex Project
# Licensed under the Apache License, Version 2.0.
#
# Modified for use in the stormlibpp project.


"""Storm message printing code that was copied and modified from the Storm CLI.

Unfortunately, the Storm CLI code does not include the following code as easily
exportable methods for reuse in other code. The relevant code from the Storm CLI
from vertexproject/synapse has been modified to work in standalone methods.
"""

import io
import json
from typing import Any

import synapse.lib.node as s_node
import synapse.lib.output as s_output

from .errors import StormRaiseError


OUTP = s_output.stdout


def log_storm_msg(logfd: io.BufferedRandom, mesg: dict) -> None:
    """Write ``mesg`` to ``logfd`` after converting it to JSON bytes.

    Parameters
    ----------
    logfd : io.BufferedRandom
        The file descriptor to write the log message to.
    mesg : dict
        The Storm message to log.
    """
    if logfd is not None:
        byts = json.dumps(mesg).encode("utf8")
        logfd.write(byts + b"\n")


def print_node_prop(name: str, valu: Any) -> None:
    """Print a node property to the output stream.

    Adopted from ``synapse.tools.storm.StormCli._printNodeProp()`` and modified to
    be a standalone function.

    Used heavily in ``handle_msg()``.

    Parameters
    ----------
    name : str
        The property name to print.
    valu : Any
        The property value to print.
    """
    OUTP.printf(f"        {name} = {valu}")


def handle_err(mesg: tuple, storm_raise: bool = True) -> None:
    """Handle an error message streamed from Storm/a Cortex.

    Adopted from ``synapse.tools.storm.StormCli.handleErr()`` and modified to
    be a standalone function. The storm_raise parameter was added to allow the
    caller to control whether errors streamed from Storm should be raised in
    the Python runtime.

    Parameters
    ----------
    mesg : tuple
        The message tuple
    storm_raise : bool, optional
        Raises errors streamed from Storm in the Python runtime, by default True.

    Raises
    ------
    StormRaiseError
        The error streamed from Storm, only raised if ``storm_raise = True``.
    """
    err = mesg[1]
    if err[0] == "BadSyntax":
        pos = err[1].get("at", None)
        text = err[1].get("text", None)
        tlen = len(text)
        mesg = err[1].get("mesg", None)
        if pos is not None and text is not None and mesg is not None:
            text = text.replace("\n", " ")
            # Handle too-long text
            if tlen > 60:
                text = text[max(0, pos - 30) : pos + 30]
                if pos < tlen - 30:
                    text += "..."
                if pos > 30:
                    text = "..." + text
                    pos = 33

            OUTP.printf(text)
            OUTP.printf(f'{" " * pos}^')
            OUTP.printf(f"Syntax Error: {mesg}")
            return
    elif err[0] == "StormRaise" and storm_raise:
        errname = err[1].get("errname", "")
        if errname == "stormlibpp:exit":
            raise StormRaiseError(f"{errname}: {err[1].get('mesg', err[0])}")

    text = err[1].get("mesg", err[0])
    OUTP.printf(f"ERROR: {text}")


def handle_msg(
    mesg: tuple,
    hideprops: bool = False,
    hidetags: bool = False,
    print_skips: list[str] = [],
    print_fini: bool = True,
    logfd: io.BufferedRandom = None,
) -> None:
    """Process a message streamed from the Storm runtime for cli applications.

    Adopted from ``synapse.tools.storm.StormCli.storm()`` and modified to
    be a standalone function. Since the method is adopted from a class, the
    function params are adopted to provide similar control of processing behavior. 

    This is intended for cli applications, messages are printed directly to stdout.
    Though a a log file descriptor can be provided to also log messages to a file in
    JSON format. One could monkey-patch the ``stormlibpp.output.OUTP`` object to 
    redirect output to a different stream. Future versions may provide this
    functionality natively.

    Parameters
    ----------
    mesg : tuple
        The message tuple streamed from the Storm runtime.
    hideprops : bool, optional
        Whether to hide node properties, by default False.
    hidetags : bool, optional
        Whether to hide node tags, by default False.
    print_skips : list[str], optional
        List of message types to skip printing, by default [].
    print_fini : bool, optional
        Whether to print the final "stream finished" message, by default True.
    logfd : io.BufferedRandom, optional
        A log file descriptor to write messages in JSON format, by default None.
        Message types in print_skips are also not logged.
    """
    # TODO - Ensure this is still up to date with the latest Storm CLI code.
    mtyp = mesg[0]

    # Do nothing if we don't want to handle this message type
    if mtyp in print_skips:
        return

    if mtyp == "node":
        node = mesg[1]
        formname, formvalu = s_node.reprNdef(node)

        # I think cause we're not using the CLI's printf, a newline is being missed somewhere.
        # We'll force it before each node is printed.
        OUTP.printf(f"\n{formname}={formvalu}")

        if not hideprops:
            props = []
            extns = []
            univs = []

            for name in s_node.props(node).keys():
                if name.startswith("."):
                    univs.append(name)
                    continue

                if name.startswith("_"):
                    extns.append(name)
                    continue

                props.append(name)

            props.sort()
            extns.sort()
            univs.sort()

            for name in props:
                valu = s_node.reprProp(node, name)
                name = ":" + name
                print_node_prop(name, valu)

            for name in extns:
                valu = s_node.reprProp(node, name)
                name = ":" + name
                print_node_prop(name, valu)

            for name in univs:
                valu = s_node.reprProp(node, name)
                print_node_prop(name, valu)

        if not hidetags:
            for tag in sorted(s_node.tagsnice(node)):
                valu = s_node.reprTag(node, tag)
                tprops = s_node.reprTagProps(node, tag)
                printed = False
                if valu:
                    OUTP.printf(f"        #{tag} = {valu}")
                    printed = True

                if tprops:
                    for prop, pval in tprops:
                        OUTP.printf(f"        #{tag}:{prop} = {pval}")
                    printed = True

                if not printed:
                    OUTP.printf(f"        #{tag}")

    elif mtyp == "node:edits":
        edit = mesg[1]
        count = sum(len(e[2]) for e in edit.get("edits", ()))
        OUTP.printf("." * count, addnl=False)

    elif mtyp == "fini" and print_fini:
        took = mesg[1].get("took")
        took = max(took, 1)
        count = mesg[1].get("count")
        pers = float(count) / float(took / 1000)
        OUTP.printf("complete. %d nodes in %d ms (%d/sec)." % (count, took, pers))

    elif mtyp == "print":
        OUTP.printf(mesg[1].get("mesg"))

    elif mtyp == "warn":
        info = mesg[1]
        warn = info.pop("mesg", "")
        xtra = ", ".join([f"{k}={v}" for k, v in info.items()])
        if xtra:
            warn = " ".join([warn, xtra])
        OUTP.printf(f"WARNING: {warn}")

    elif mtyp == "err":
        handle_err(mesg)

    log_storm_msg(logfd, mesg)
