"""Python objects for working with Storm Packages."""


import json
import os
import sys

from . import errors
from . import s_common, s_exc, s_genpkg
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
    pkgdef : dict
        The loaded Storm package definition.
    proto_dir : str
        The directory that the Storm package's proto is in. This is
        the ``proto_dir`` argument if it is passed. Otherwise, the dir
        is resolved by looking at the ``self.__class__.__module__`` name
        at init, finding the object this resolves to in ``sys.modules``,
        and reading the module's ``__file__``. Then joining this file's
        dir name with the value ``pkgproto``.
    proto_name : str | None
        A class property containing the name of the Storm package's proto
        Yaml file (without extension). Subclasses may override this class
        property to set a custom proto Yaml file basename. If they don't,
        this property is automatically set to the value of
        ``self.__class__.__name__.lower()``.

    Raises
    ------
    StormPkgBadDefError
        If the package proto either has an invalid schema or bad value.
    StormPkgNoProtoError
        If the proto Yaml file cannot be loaded. This can happen if the file name
        will not match ``name``/``pkg_name`` but ``proto_name`` is not passed.
    StormPkgResolveError
        If the default package proto dir cannot be resolved. This can be the case
        if a `StormPkg` is created and doesn't expect to use the default proto dir
        but a custom ``proto_dir`` is not passed.
    RuntimeError
        If this class is instantiated directly and not subclassed.
    """

    proto_name: str | None = None

    def __init__(
        self,
        check_syntax: bool = True,
        proto_dir: str | None = None,
    ) -> None:
        if StormPkg not in self.__class__.__bases__:
            raise RuntimeError("StormPkg must be subclassed.")

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
                "pkgproto",
            )

        if not self.proto_name:
            self.proto_name = self.__class__.__name__.lower()

        self.proto = os.path.join(self.proto_dir, f"{self.proto_name}.yaml",)

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

    def _search_def(self, primkey: str, seckey: str) -> list[str]:
        """Search the modules or commands of the pkgdef for a secondary key."""

        vals = []
        for val in self.pkgdef.get(primkey, []):
            if seckey in val:
                vals.append(val[seckey])
        return vals

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

    def cmds(self) -> list[str]:
        """The commands this package defines."""

        return self._search_def("commands", "name")

    def mods(self) -> list[str]:
        """The modules this package defines."""

        return self._search_def("modules", "name")

    def storm(self) -> dict[str, str]:
        """The Storm code this package defines.
        
        Returns
        -------
        dict[str, str]
            Keys are the module/command name and values are the Storm code.
        """

        storm = {}
        for mod in self.pkgdef.get("modules", []):
            if "name" in mod and "storm" in mod:
                storm[mod["name"]] = mod["storm"]
        for cmd in self.pkgdef.get("commands", []):
            if "name" in cmd and "storm" in cmd:
                storm[cmd["name"]] = cmd["storm"]
        return storm
