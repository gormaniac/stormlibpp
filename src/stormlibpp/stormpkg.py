"""Python objects for working with Storm Packages."""


import json
import os
import sys

import synapse.common as s_common
import synapse.exc as s_exc
import synapse.tools.genpkg as s_genpkg

from . import errors
from . import utils


class StormPkg:
    """A Python representation of a Storm package, proto and definition.

    This class must be subclassed - this is how default proto dir loading is supported.

    By default, the subclasses expect a Storm package proto to be stored in a
    ``pkgproto`` directory that is within the same directory as the ``__init__.py``
    of the module the object is defined within. This can be changed. But, if
    it isn't, this means you must setup your package proto files to be built with
    your Python module.

    By default, subclasses look for a Yaml package proto file with a basename
    equal to the lowercase version of the subclass' name. Subclasses must
    override the ``proto_name`` class property to change this behavior.

    This object is ready to use on init - access the ``pkgdef`` prop for
    the full Storm package definition loaded from the definied package proto.
    The ``pkgdef`` property is also returned by this object's ``asdict`` method.

    It takes the following steps on start up:

    - Resolves the path of the package proto based on ``proto_name`` and
      ``proto_dir``.

    - Loads the package proto using ``synapse.tools.genpkg.tryLoadPkgProto``.

    - Converts the returned object to a ``dict`` using ``json.dumps`` and
      ``json.loads``.

        - This is necessary because ``tryLoadPkgProto`` returns a "tuplified"
          object (the return of ``synapse.common.tuplify``). Which can return
          immutable objects that ``synapse.cortex.Cortex.addStormPkg`` expects
          to be mutable. So a ``StormSvc._storm_svc_pkgs`` works best when it
          is set to a ``dict``.

    - Sets the loaded package definition's ``build`` key to a ``dict``
      containing the time using ``synapse.common.now``.

    - Stores the package definition ``dict`` in the ``pkdef`` property.

    - If ``check_syntax`` is True, all Storm code that is loaded in the ``pkdef``
      is passed to Synapse's Storm parser to check for Storm syntax errors.
      Any errors are raised as a ``StormPkgSyntaxError`` exception.

    Parameters
    ----------
    check_syntax : bool, optional
        Whether to check the syntax of this package's loaded Storm code.
        By default True.
    proto_dir : str | None, optional
        The fully resolved directory that the package proto is in. A value
        of ``None`` tells ``StormPkg`` to resolve this path automatically based
        on the rules defined elsewhere in this docstring. By default None.

    Properties
    ----------
    default_name : str
        The Yaml basename used if ``proto_name`` is empty (not set).
        Set to the value of ``self.__class__.__name__.lower()``.
    pkgdef : dict
        The loaded Storm package definition.
    proto_dir : str
        The directory that the Storm package's proto is in. This is
        the ``proto_dir`` argument if it is passed. Otherwise, the dir
        is resolved by looking at the ``self.__class__.__module__`` name
        at init, finding the object this resolves to in ``sys.modules``,
        and reading the module's ``__file__``. Then joining this file's
        dir name with the value ``pkgproto``.
    proto_name : str
        A class property containing the name of the Storm package's proto
        Yaml file (without extension). Subclasses may override this class
        property to set a custom proto Yaml file basename. If they don't,
        this property is automatically set to the value of ``self.default_name``.

    Raises
    ------
    StormPkgBadDefError
        If the package proto either has an invalid schema or bad value.
    StormPkgNoProtoError
        If the proto Yaml file cannot be loaded. This can happen if the file name
        will not match ``self.default_name`` but ``proto_name`` is not set.
    StormPkgResolveError
        If the default package proto dir cannot be resolved. This can be the case
        if a `StormPkg` is created and doesn't expect to use the default proto dir
        but a custom ``proto_dir`` is not passed.
    StormPkgSyntaxError
        If ``check_syntax`` is True and the Storm code in this package has syntax errors.
    RuntimeError
        If this class is instantiated directly and not subclassed.
    """

    proto_name: str | None = None
    """The basename of this Storm package's Yaml proto file."""

    def __init__(
        self,
        check_syntax: bool = True,
        proto_dir: str | None = None,
    ) -> None:
        if StormPkg not in self.__class__.__bases__:
            raise RuntimeError("StormPkg must be subclassed.")

        self.default_name = self.__class__.__name__.lower()
        if not self.proto_name:
            self.proto_name = self.default_name

        if proto_dir:
            self.proto_dir = proto_dir
        else:
            try:
                resolved_path = sys.modules[self.__class__.__module__].__file__
            except AttributeError as err:
                raise errors.StormPkgResolveError(
                    "Unable to automatically resolve the package proto's directory. "
                    "Try passing proto_dir."
                ) from err

            self.proto_dir = utils.absjoin(
                os.path.dirname(resolved_path),
                # TODO - Make this configurable
                "pkgproto",
            )

        self.proto = os.path.join(
            self.proto_dir,
            f"{self.proto_name}.yaml",
        )

        self.pkgdef = self._load_proto()
        """A Python dict containing the full Storm package definition."""

        if check_syntax:
            self.check_syntax()

    def _load_proto(self) -> dict:
        """Load the package proto and convert it to a package definition."""

        try:
            pkgdef = json.loads(
                json.dumps(s_genpkg.tryLoadPkgProto(self.proto, readonly=True))
            )
        except s_exc.NoSuchFile as err:
            raise errors.StormPkgNoProtoError(
                "One of the package`'s proto files do not exist. "
                "Try passing proto_name and/or proto_dir. "
                "May also indicate a missing .storm file."
            ) from err
        except (
            s_exc.BadArg,
            s_exc.BadPkgDef,
            s_exc.SchemaViolation,
        ) as err:
            raise errors.StormPkgBadDefError(
                "The specified package proto was invalid."
            ) from err

        pkgdef["build"] = {"time": s_common.now()}

        return pkgdef

    def asdict(self):
        """Return this objects full Storm package definition as a Python dict.

        Pointer to ``self.pkgdef``.
        """

        return self.pkgdef

    def check_syntax(self) -> None:
        """Check the Storm syntax of this package's loaded Storm code.

        Raises
        ------
        StormPkgSyntaxError
            If the syntax of a any Storm code is invalid. We fail the whole
            package because one bad Storm file will cause loading failures on
            the Cortex for all other files too.
        """

        for stormname, code in self.storm().items():
            try:
                utils.chk_storm_syntax(code)
            except errors.StormSyntaxError as err:
                raise errors.StormPkgSyntaxError(
                    f"{stormname} from {self.proto_name}.yaml has a Storm "
                    f"syntax error: {err}"
                ) from err

    def cmds(self) -> list[dict]:
        """The full definitions of the commands this package defines."""

        return self.pkgdef.get("commands", [])

    def mods(self) -> list[dict]:
        """The full definitions of the modules this package defines."""

        return self.pkgdef.get("modules", [])

    def storm(self) -> dict[str, str]:
        """The Storm code this package defines.

        Iterates over the dicts from ``cmds()`` + ``mods()`` to map all names
        to the Storm code each dict defines in the ``storm`` key.

        Returns
        -------
        dict[str, str]
            Keys are the module/command name and values are the Storm code.
        """

        storm = {}
        for item in self.cmds() + self.mods():
            if "name" in item and "storm" in item:
                storm[item["name"]] = item["storm"]
        return storm

    @property
    def cmdnames(self) -> list[str]:
        """The names of the commands this package defines, if any."""

        return [cmd.get("name") for cmd in self.cmds() if "name" in cmd]

    @property
    def modnames(self) -> list[str]:
        """The names of the modules this package defines, if any."""

        return [mod.get("name") for mod in self.mods() if "name" in mod]

    @property
    def pkg_guid(self) -> str | None:
        """The package's guid, None if not set."""

        return self.pkgdef.get("guid")

    @property
    def pkg_name(self) -> str | None:
        """The package's name, None if not set."""

        return self.pkgdef.get("name")

    @property
    def pkg_ver(self) -> str | None:
        """The package's version, None if not set."""

        return self.pkgdef.get("version")
