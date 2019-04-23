import os
import logging
from itertools import chain
from dataclasses import dataclass
from typing import Sequence, Callable

from .process import Process


class ScriptError(Exception):
    pass


@dataclass
class Ludus:
    path: str
    script_dirname: str = "scripts"
    instance_dirname: str = "instances"
    archetype_dirname: str = "archetypes"
    codebase_dirname: str = "codebase"
    _logger: logging.Logger = None

    @property
    def script_dir(self):
        return os.path.join(self.path, self.script_dirname)

    @property
    def instance_dir(self):
        return os.path.join(self.path, self.instance_dirname)

    @property
    def archetype_dir(self):
        return os.path.join(self.path, self.archetype_dirname)

    @property
    def codebase_dir(self):
        return os.path.join(self.path, self.codebase_dirname)

    def create_process(self, command, *args, **kwargs) -> Process:
        def form_kwargs(key: str, value):
            if value is None:
                return []
            if isinstance(value, bool):
                if not value:
                    return []
                return [f"--{key}"]
            if isinstance(value, str):
                return [f"--{key}", value]
            if isinstance(value, Sequence):
                return list(chain(*(form_kwargs(key, v) for v in value)))
            return [f"--{key}", str(value)]

        kwargs = list(chain(*(form_kwargs(k.replace("_", "-"), v)
                              for k, v in kwargs.items())))
        return Process(
            args=[command] + list(args) + kwargs,
            cwd=self.path,
            inherit_env=True,
            aux_paths=[self.script_dir, "/home/kani/.conda3/envs/apollo/bin"]
        )

    def _create_instance(self, archetype,
                         instance=None, overwrite=False, force=False
                         ) -> Process:
        return self.create_process(
            "instance-create",
            *list(filter(None, (archetype, instance))),
            overwrite=overwrite,
            force=force,
            instances_dir=self.instance_dir
        )

    def _run_instance(self, instance, *commands, verbose=False, dry_run=False):
        return self.create_process(
            "instance-run",
            instance, *commands,
            verbose=verbose,
            dry_run=dry_run,
            instances_dir=self.instance_dir,
            codebase=self.codebase_dir
        )

    def _clear_instance(self, instance):
        return self.create_process(
            "instance-clear",
            instance,
            yes=True,
            instances_dir=self.instance_dir
        )

    def _set_config(self, instance, config, key, value):
        if value is None:
            value_type = "null"
        elif isinstance(value, int):
            value_type = "int"
        elif isinstance(value, float):
            value_type = "float"
        elif isinstance(value, str):
            value_type = "str"
        else:
            raise TypeError(f"unsupported value type: {value}")
        return self.create_process(
            "config-set",
            instance, config, key, str(value),
            type=value_type,
            write_back=True,
            instances_dir=self.instance_dir,
        )

    def _get_config(self, instance, config, *keys):
        return self.create_process(
            "config-get",
            instance, config, *keys,
            instances_dir=self.instance_dir
        )

    @staticmethod
    def throw_script_error(name, rc, msg: bytes):
        raise ScriptError(f"instance-create failed; "
                          f"return code: {rc}, "
                          f"error message: {msg.decode()}")

    def create_instance(self, archetype,
                        instance=None, overwrite=False, force=False):
        process = self._create_instance(
            archetype,
            instance=instance,
            overwrite=overwrite,
            force=force
        )
        ret = process.run_sync()
        if ret != 0:
            self.throw_script_error("instance-create",
                                    ret, process.read_error())

    def run_instance(self, instance, *commands,
                     verbose=False, dry_run=False, proc_fn: Callable = None):
        process = self._run_instance(
            instance, *commands,
            verbose=verbose, dry_run=dry_run
        )
        process.open()
        if proc_fn is not None:
            proc_fn(process)
        ret = process.wait()
        if ret != 0:
            self.throw_script_error("instance-run",
                                    ret, process.read_error())

    def clear_instance(self, instance):
        process = self._clear_instance(instance)
        ret = process.run_sync()
        if ret != 0:
            self.throw_script_error("instance-clear",
                                    ret, process.read_error())

    def set_config(self, instance, config, key, value):
        process = self._set_config(instance, config, key, value)
        ret = process.run_sync()
        if ret != 0:
            self.throw_script_error("config-set",
                                    ret, process.read_error())

    def get_config(self, instance, config, *keys) -> Sequence[str]:
        process = self._get_config(instance, config, *keys)
        ret = process.run_sync()
        if ret != 0:
            self.throw_script_error("config-get",
                                    ret, process.read_error())
        return [l.rstrip("\n") for l in process.read_str().splitlines()]
