#
# Copyright (c) 2024 Joshua Watt
#
# SPDX-License-Identifier: MIT

import sys
import os
from pathlib import Path
from contextlib import contextmanager
from jinja2 import Environment, FileSystemLoader, TemplateRuntimeError
from rdflib.namespace import SH
from ..model import SHACL2CODE

THIS_DIR = Path(__file__).parent


class OutputFile(object):
    def __init__(self, path):
        self.path = path

    @contextmanager
    def open(self):
        if self.path == "-":
            yield sys.stdout
        else:
            with open(self.path, "w") as f:
                yield f


class BasicJinjaRender(object):
    """
    Common Jinja Template Renderer

    Renderers that only use a single Jinja file can derive from this class. The
    class should set the class member variable `TEMPLATE` to indicate which
    template file to use. For example:

        @language("my-lang")
        class MyRendered(BasicJinjaRenderer):
            HELP = "Generates my-lang bindings"
            TEMPLATE = "my-lang.j2"

    """

    def __init__(self, args, template):
        self.__output = args.output
        self.__template = template

    @classmethod
    def get_arguments(cls, parser):
        parser.add_argument(
            "--output",
            "-o",
            type=OutputFile,
            help="Output file or '-' for stdout",
            required=True,
        )

    def get_additional_render_args(self):
        return {}

    def get_extra_env(self):
        return {}

    def output(self, model):
        def abort_helper(msg):
            raise TemplateRuntimeError(msg)

        def get_all_derived(cls):
            nonlocal classes

            def _recurse(cls):
                result = set(cls.derived_ids)
                for r in cls.derived_ids:
                    result |= _recurse(classes.get(r))
                return result

            d = list(_recurse(cls))
            d.sort()
            return d

        class ObjectList(object):
            def __init__(self, objs):
                self.__objs = objs

            def __iter__(self):
                return iter(self.__objs)

            def get(self, _id):
                for o in self.__objs:
                    if o._id == _id:
                        return o
                raise KeyError(f"Object with ID {_id} not found")

        env = Environment(
            loader=FileSystemLoader([self.__template.parent, THIS_DIR.parent])
        )
        for k, v in self.get_extra_env().items():
            env.globals[k] = v
        env.globals["abort"] = abort_helper
        env.globals["get_all_derived"] = get_all_derived
        env.globals["SHACL2CODE"] = SHACL2CODE
        env.globals["SH"] = SH
        template = env.get_template(self.__template.name)

        classes = ObjectList(model.classes)
        enums = ObjectList(model.enums)

        render = template.render(
            disclaimer=f"This file was automatically generated by {os.path.basename(sys.argv[0])}. DO NOT MANUALLY MODIFY IT",
            enums=enums,
            classes=classes,
            context=model.context,
            **self.get_additional_render_args(),
        )

        with self.__output.open() as f:
            f.write(render)
            if not render[-1] == "\n":
                f.write("\n")
