"""Load every StormLib++ Storm package into a Cortex.

A package only gets loaded (and its Storm parsed) by a test that names it, and the
package build doesn't parse Storm, so a package with no tests can ship with syntax
errors. This loads every package under src/pkgs, including ones added later.
"""

import os

import synapse.tests.utils as s_test
import synapse.tools.storm.pkg.gen as s_genpkg

from .. import DIRNAME

PKGS_DIR = os.path.join(DIRNAME, "src/pkgs")


def pkgProtos(pkgsdir: str = PKGS_DIR) -> list[str]:
    """Return the package proto of every package directory in pkgsdir.

    Follows the convention scripts/pkgs/build.sh uses: src/pkgs/<name>/<name>.yaml.
    """
    return sorted(
        os.path.join(pkgsdir, name, f"{name}.yaml")
        for name in os.listdir(pkgsdir)
        if os.path.isdir(os.path.join(pkgsdir, name)) and not name.startswith((".", "_"))
    )


async def loadPkgs(core, protos: list[str]) -> list[str]:
    """Load each package proto into core, and return an error for each one that fails."""
    errs = []
    for proto in protos:
        name = os.path.relpath(proto, DIRNAME)
        try:
            pkgdef = s_genpkg.loadPkgProto(proto, no_docs=True, readonly=True)
            await core.addStormPkg(pkgdef)
        except Exception as e:
            errs.append(f"{name}: {e!r}")
    return errs


class AllPkgsTest(s_test.SynTest):
    """Every Storm package loads."""

    async def test_all_pkgs_load(self):
        """Every package under src/pkgs loads, which validates all of its Storm."""

        protos = pkgProtos()
        self.ge(len(protos), 6)

        async with self.getTestCore() as core:
            errs = await loadPkgs(core, protos)
            self.eq([], errs)
