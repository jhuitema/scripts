"""Generate unit test stubs based on the AST of a module."""

# Import built-in modules
import argparse
import ast
import fnmatch
import pathlib
import sys


_TEMPLATES = {
    "func": {
        "file_name": "test_{func}.py",
        "contents": '''
"""Tests for the `{mod}.{func}` function."""

# Import third-party modules
import pytest

# Import local modules
from {mod} import {func}


def test_main_case(mocker):
    """Test the main case of `{func}`."""
    # Preparation
    
    # Execution
    result = {func}()
    
    # Verification
    assert result == ""

'''.lstrip(),
    },
    "async_func": {
        "file_name": "test_{func}.py",
        "contents": '''
"""Tests for the `{mod}.{func}` function."""

# Import third-party modules
import pytest

# Import local modules
from {mod} import {func}


async def test_main_case(mocker):
    """Test the main case of `{func}`."""
    # Preparation
    
    # Execution
    result = await {func}()
    
    # Verification
    assert result == ""

'''.lstrip(),
    },
    "meth": {
        "file_name": "test_{cls}_{meth}.py",
        "contents": '''
"""Tests for the `{mod}.{cls}.{meth}` method."""

# Import third-party modules
import pytest

# Import local modules
from {mod} import {cls}


def test_main_case(mocker):
    """Test the main case of `{cls}.{meth}`."""
    # Preparation
    obj = {cls}()

    # Execution
    result = obj.{meth}()

    # Verification
    assert result == ""

'''.lstrip(),
    },
    "async_meth": {
        "file_name": "test_{cls}_{meth}.py",
        "contents": '''
"""Tests for the `{mod}.{cls}.{meth}` method."""

# Import third-party modules
import pytest

# Import local modules
from {mod} import {cls}


async def test_main_case(mocker):
    """Test the main case of `{cls}.{meth}`."""
    # Preparation
    obj = {cls}()

    # Execution
    result = await obj.{meth}()

    # Verification
    assert result == ""

'''.lstrip(),
    },
}


def cli():
    args = parse_args()
    root_module_file = args.src_dir
    root_module_name = root_module_file.stem
    root_test_dir = args.test_dir

    for submodule_file in root_module_file.rglob("*.py"):
        if any(fnmatch.fnmatch(str(submodule_file), pattern) for pattern in args.ignore_submodules):
            continue

        test_dir = root_test_dir.joinpath(*submodule_file.parts[:-1]) / submodule_file.stem
        module_path = ".".join(submodule_file.with_suffix("").parts)
        if module_path.endswith(".__init__"):
            test_dir = root_test_dir.joinpath(*submodule_file.parts).parent
            module_path = module_path.rsplit(".", 1)[0]

        print()
        print(test_dir, module_path)
        for child_node in ast.iter_child_nodes(ast.parse(submodule_file.read_text())):
            print(child_node)

            if isinstance(child_node, ast.ClassDef):
                found_init = False
                format_args = {"mod": module_path, "cls": child_node.name}
                for cls_child_node in ast.iter_child_nodes(child_node):
                    if isinstance(cls_child_node, ast.FunctionDef):
                        meth_format_args = format_args.copy()
                        meth_format_args["meth"] = cls_child_node.name
                        create_test_file(test_dir, "meth", meth_format_args)

                    elif isinstance(cls_child_node, ast.AsyncFunctionDef):
                        meth_format_args = format_args.copy()
                        meth_format_args["meth"] = cls_child_node.name
                        create_test_file(test_dir, "async_meth", meth_format_args)

                    else:
                        continue

                    if cls_child_node.name == "__init__":
                        found_init = True

                if not found_init:
                    meth_format_args = format_args.copy()
                    meth_format_args["meth"] = "__init__"
                    create_test_file(test_dir, "meth", meth_format_args)

            elif isinstance(child_node, ast.FunctionDef):
                format_args = {"mod": module_path, "func": child_node.name}
                create_test_file(test_dir, "func", format_args)

            elif isinstance(child_node, ast.AsyncFunctionDef):
                format_args = {"mod": module_path, "func": child_node.name}
                create_test_file(test_dir, "async_func", format_args)

    return 0


def create_test_file(test_dir, ast_type, format_args):
    """Create the test file with the appropriate data."""
    test_file = test_dir / _TEMPLATES[ast_type]["file_name"].format(**format_args)
    if test_file.exists():
        print(f"Skipping as test file exists: {test_file}")
        return

    contents = _TEMPLATES[ast_type]["contents"].format(**format_args)
    print(f"Creating test file: {test_file}")
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text(contents)


def parse_args():
    parser = argparse.ArgumentParser(
        "create_unit_tests",
        description="Generate unit test stubs based on the AST of a module.",
    )
    parser.add_argument(
        "src_dir",
        type=pathlib.Path,
        help="The path to the module directory or file to create the tests for.",
    )
    parser.add_argument(
        "test_dir",
        type=pathlib.Path,
        help="The path to create the tests in.",
    )
    parser.add_argument(
        "--ignore-submodules",
        type=str,
        nargs="+",
        default=["*test*"],
        help="Patterns that match against files or directories to not create tests for.",
    )
    return parser.parse_args(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(cli())
