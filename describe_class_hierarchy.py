"""Print the class inheritance hierarchy for a module's classes.

Note: The module needs to be available in the python session.

```bash
python describe_class_hierarchy.py importlib
```

"""

import argparse
import ast
import fnmatch
import importlib
import logging
import json
import pathlib
import sys

try:
    import yaml
except ImportError:
    yaml = None

_LOGGER = logging.getLogger(pathlib.Path(__file__).stem)


def _get_node_name(node) -> str:
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Call):
        args = [_get_node_name(arg_node) for arg_node in node.args]
        kwargs = [_get_node_name(kwarg_node) for kwarg_node in node.keywords]
        return f"{node.func.id}({', '.join(args + kwargs)})"
    elif isinstance(node, ast.keyword):
        return f"{node.arg}={_get_node_name(node.value)}"
    elif isinstance(node, ast.Starred):
        return f"*{_get_node_name(node.value)}"
    elif isinstance(node, ast.Attribute):
        return f"{_get_node_name(node.value)}.{node.attr}"
    else:
        raise ValueError(f"Unknown ast node '{str(type(node))}' detected: {node}")


def _get_local_object(module_obj, object_name):
    if module_obj:
        try:
            return module_obj.__dict__[object_name]
        except KeyError:
            # This probably means it is a global type like `object`
            print(f"Couldn't get {object_name} from {module_obj.__name__}")
            return locals()[object_name]
    return None


def find_class_children(
    classes: dict, module_file: pathlib.Path, module_path: str
) -> dict[str, set]:
    """For each class defined in the given module find the ancestor.

    Args:
        module_file:  The module file to get the classes of.

    Returns:
        Dictionary of all class relationships with the keys as the base
        classes and the values as a set of the sub classes. The class
        will always be described with the full import path.

    """
    _LOGGER.debug(f"=== Parsing {module_path} ===")
    module_obj = None
    # If the module isn't importable then we will have to make do with
    # whatever name the object was imported under
    try:
        module_obj = importlib.import_module(module_path)
    except ImportError:
        _LOGGER.debug(f"Couldn't import {module_path}")
        return {}

    for child_node in ast.iter_child_nodes(ast.parse(module_file.read_text())):
        if isinstance(child_node, ast.ClassDef):
            class_obj = _get_local_object(module_obj, child_node.name)
            _recursive_create_dict_hierarchy(
                classes,
                [
                    f"{base_cls.__module__}.{base_cls.__name__}"
                    for base_cls in reversed(class_obj.__mro__)
                ],
            )

    return classes


def _recursive_create_dict_hierarchy(dict_, levels):
    """Add a value to a dictionary at an unknown depth."""
    if levels:
        current_level = levels.pop(0)
        dict_.setdefault(current_level, {})
        dict_[current_level].update(
            _recursive_create_dict_hierarchy(dict_[current_level], levels)
        )
    return dict_


def _recursive_sort_dict(dict_):
    """Sort all keys within a dictionary."""
    if not isinstance(dict_, dict):
        return dict_
    new_dict = {key: _recursive_sort_dict(dict_[key]) for key in sorted(dict_)}
    return new_dict


def parse_args():
    parser = argparse.ArgumentParser(
        "describe_class_hierarchy",
        description="Describe the hierarchy for all classes found in the given module.",
    )
    parser.add_argument(
        "module",
        help="The module to describe the classes of.",
    )
    parser.add_argument(
        "--ignore-submodules",
        type=str,
        nargs="+",
        default=["*test*"],
        help="Patterns that match against submodules to not describe.",
    )
    parser.add_argument(
        "--as-json",
        action="store_true",
        default=False,
        help="Whether to output the hierarchy in a human-readable way.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Whether to output debug logging.",
    )
    return parser.parse_args(sys.argv[1:])


def cli():
    args = parse_args()
    if args.debug:
        logging.basicConfig(
            format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
            level=logging.DEBUG,
        )

    module_name: str = args.module
    module_obj = importlib.import_module(module_name)
    root_module_file = pathlib.Path(module_obj.__file__)
    if root_module_file.stem == "__init__":
        module_files = root_module_file.parent.rglob("*.py")
    else:
        module_files = [root_module_file]

    all_classes = {}
    for module_file in module_files:
        if any(
            fnmatch.fnmatch(str(module_file), pattern)
            for pattern in args.ignore_submodules
        ):
            continue
        py_module_path = ".".join(
            module_file.relative_to(root_module_file.parent.parent)
            .with_suffix("")
            .parts
        )
        if py_module_path.endswith(".__init__"):
            py_module_path = py_module_path.rsplit(".", 1)[0]
        find_class_children(all_classes, module_file, py_module_path)

    class_hierarchy = _recursive_sort_dict(all_classes)

    if yaml and not args.as_json:
        output = yaml.dump(class_hierarchy, default_flow_style=False, indent=2)
        # We only want the indentation not the dict structure
        print(output.replace(" {}", "").replace(":", ""))
    else:
        print(json.dumps(class_hierarchy, indent=2))


if __name__ == "__main__":
    sys.exit(cli())
