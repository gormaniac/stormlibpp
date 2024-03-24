"""A wrapper of ``synapse.tools.feed`` that feeds data to a Cortex over HTTP instead of Telepath."""


import asyncio
import sys

import synapse.tools.feed as s_feed

from ._args import TOKEN_PARSER, USER_PARSER, VERIFY_PARSER
from .output import OUTP
from .utils import add_parser_parents
from .utils import (
    add_parser_parents,
    get_cortex_creds,
    get_cortex_obj,
    get_cortex_token,
)


def get_args(argv: list[str]):
    parser = s_feed.makeargparser()
    parser.prog = "stormlibpp.hfeed"
    parser.description = __doc__

    parents =  [TOKEN_PARSER, USER_PARSER, VERIFY_PARSER]
    parser = add_parser_parents(parser, parents)

    return parser.parse_args(argv)


async def main():
    args = get_args(sys.argv[1:])

    if args.token and not args.test:
        token = get_cortex_token(prompt=True)
        username = password = ""
        if not token:
            return "Token wasn't set!"
    elif not args.test:
        username, password = get_cortex_creds(args.user)
        token = ""
        if not username or not password:
            return "Username/password wasn't set!"
    else:
        token = username = password = ""

    # TODO - Support telepath too?
    core_obj = await get_cortex_obj(
        cortex=args.cortex,
        local=args.test,
        http=True,
        ssl_verify=not args.no_verify,
        username=username,
        password=password,
        token=token,
    )

    async with core_obj() as core:

        await s_feed.addFeedData(
            core,
            OUTP,
            args.format,
            args.debug,
            chunksize=args.chunksize,
            offset=args.offset,
            viewiden=args.view,
            *args.files
        )


if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main()))