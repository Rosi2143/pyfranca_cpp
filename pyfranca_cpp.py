#!/usr/bin/python3

# -*- coding: utf-8 -*-
# vim: tw = 0
# vim: set fileencoding = utf-8

"""
Generate stuff from Franca IDL based on templates
"""

import sys
import os
import time
from jinja2 import Environment, BaseLoader, TemplateNotFound
from itertools import *

# call, POpen, ...
from subprocess import *

# Instead of relying on installed pyfranca, assume it is stored in parallel
# with this project or inside the project dir:
sys.path.append(os.getcwd() + "/pyfranca")
sys.path.append(os.getcwd() + "/../pyfranca")

# Same for jinja2 if it's not installed
sys.path.append(os.getcwd() + "/jinja/src")
sys.path.append(os.getcwd() + "/../jinja/src")

from pyfranca import Processor, LexerException, ParserException, ProcessorException, ast
from pyfranca.ast import Array

# From jinja2 docs


class MyLoader(BaseLoader):
    """load the templates

    Args:
        BaseLoader (baseLoader): jinja baseLoader
    """

    def __init__(self, prioritydir, defaultdir, relpath):
        self.relpath = relpath
        self.prioritydir = prioritydir  # Use file from here, if it exists
        self.defaultdir = defaultdir    # else from here.

    def get_source(self, environment, template):
        path = self.get_file_location(template)

        if not os.path.exists(path):
            raise TemplateNotFound(template)

        mtime = os.path.getmtime(path)
        with open(path, encoding='utf-8') as in_file:
            source = in_file.read()
        return source, path, lambda: mtime == os.path.getmtime(path)

    def get_file_location(self, name):
        """get the location of the file, when the full name is given

        Args:
            name (string): full path to file

        Returns:
            string: directory of the given file
        """
        preferred = os.path.abspath(os.path.join(self.prioritydir, self.relpath, name))
        fallback = os.path.abspath(os.path.join(self.defaultdir, self.relpath, name))

        if os.path.exists(preferred):
            path = preferred
        else:
            path = fallback
        return path

# -------------------------------------------------------------------
# Setting up...
# Constants and other global values


RELATIVE_OUTPUT_DIR = 'src_gen'

# The starting directory (assumed to be == the script directory for now)
workingdir = os.getcwd()
basedir = os.path.dirname(os.path.realpath(__file__))
output_dir = workingdir + "/" + RELATIVE_OUTPUT_DIR


# Where to find templates
env = Environment(
    loader=MyLoader(workingdir,  # preferred/override location
                    basedir,      # fallback/default location
                    'templates')  # relative path
)

# ---------------------------------------------------------------


def log(*kwargs):
    """log to commandline
    """
    print(", ".join(kwargs))


def clang_format(file):
    """run clang-format for given file

    Args:
        file (filePath): file to check
    """
    call(['clang-format', '-i', file])


def boilerplate_from_file():
    """read the boilerplate file content into a string

    Returns:
        string: file content
    """
    path = env.loader.get_file_location('boilerplate.txt')
    return open(path, 'r', encoding="utf8").read()

# ---------------------------------------------------------------
# Type definitions generation
#
# There's a fair amount of code here simply because types need to be
# generated in the order they are referenced in the C/C++ program or there
# will be a compile error.  (The order is not guaranteed from the way the
# generation is set up, since it generates one type of object at a time -
# e.g. first all structs, then all unions, then all arrays, etc.)
#
# We also dedup since the same type might turn up more than once but must
# be output only once.
# ---------------------------------------------------------------

# Here we use a combination of a Set for existence, and an array for ordered
# storage. An OrderedDict / OrderedSet could be an alternative but swapping
# elements seemed messier there than in a plain array.


is_rendered = set()
rendered_types_ordered = []
reference_pairs = set()
rendered_types_index = {}


def a_reference_to_b(element_a, element_b):
    """Does a reference b?

    Args:
        a (_type_): any element
        b (_type_): any (other) element

    Returns:
        _type_: ??
    """
    return (element_a, element_b) in reference_pairs


def type_reference(element_a, element_b):
    """Used as a Set - the pair exists or not

    Args:
        a (_type_): any element
        b (_type_): any (other) element
    """
    reference_pairs.add((element_a, element_b))


def store_rendered_type(name, text):
    """
    Because of files including files (including files...) there can be
    rendered duplicates and we make sure to avoid that.

    Args:
        name (string): name of element
        text (string): already rendered text
    """
    if name not in is_rendered:
        is_rendered.add(name)
        rendered_types_ordered.append((name, text))


def reset_rendered_types():
    """Empty all data structures"""
    reference_pairs.clear()
    is_rendered.clear()
    rendered_types_ordered[:] = []
    rendered_types_index.clear()


def process_file(file):
    """
    Relative path includes seem to only work if we're in the right
    working directory also for the file:

    Args:
        file (filePath): path to FIDL file
    """

    dir_name = os.path.dirname(file)
    file_name = os.path.basename(file)
    os.chdir(dir_name)

    file = open(file_name, "r", encoding="utf8")
    file_content = file.read().replace('\r\n', '\n')  # Need to get rid of Windows linefeeds
    fidl_text = file_content.replace('^version', 'interfaceversion') \
        # FIXME, dirty fix of ^ escape character

    # dump_contents(f, s)
    process_fidl(file_name, fidl_text)
    os.chdir(workingdir)


def process_fidl(name, fidl_text):
    """process content of the FIDL file

    Args:
        name (string): file name
        fidl_text (string): content of FIDL file
    """
    processor = Processor()
    try:
        processor.import_string(name, fidl_text)
    except (LexerException, ParserException, ProcessorException) as exception:
        print(f"ERROR: {exception}")

    template = "interfaceheader.tpl"
    template_render_plain_file(processor, ['interfaces'], template, "i", ".h")

    template = "classheader.tpl"
    template_render_plain_file(processor, ['interfaces'], template, "", ".h")

    template = "class.tpl"
    template_render_plain_file(processor, ['interfaces'], template, "", ".cpp")

    render_typedef_file(processor, ['interfaces', 'typecollections'], ".types.h")


def clean(fidl_file):
    """Some needed cleanup (smarter templates might avoid this)

       TODO - maybe check that result is not empty before writing file
    Args:
        file (filePath): path to FIDL file
    """
    with open(fidl_file, 'r', encoding="utf8") as in_file:
        file_content = in_file.read()
        file_content = file_content.replace('){', ')\n{')
        file_content = file_content.replace(',)', ')')

    with open(fidl_file, 'w', encoding="utf8") as out_file:
        out_file.write(file_content)


def write_result_file(result, name, prefix, suffix):
    """write the generated content into a file
       location of the new file is the "workingdir"

    Args:
        result (string): generated file content
        name (string): base name of the file
        prefix (string): prefix to the filename (e.g. "I" for interface files)
        suffix (string): postfix of the filename (e.g. the ".hpp"/".cpp")
    """
    out_file = output_dir + "/" + prefix + name + suffix
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    with open(out_file, 'w', encoding="utf8") as out_file_ptr:
        out_file_ptr.write(result)
    # clean up result
    clang_format(out_file)
    clean(out_file)
    print(f"Wrote file: {out_file}")

# ----- Rendering helpers -----
# These functions take some of the logic out of the rendering templates which
# would otherwise be a little messy.


def is_array(parameter_name):
    """check if element is an array
       Arrays are complex types and can't be rendered like normal ones The AST
       requires us to extract the inner *referenced* type.name rather than usually
       simply the name of the type.

    Args:
        parameter_name (_type_): any type

    Returns:
        bool: True - element is an Array
    """
    return isinstance(parameter_name, ast.Array)


def is_reference(parameter_name):
    """check if element is a Reference
       References just refer to more detailed
       type information but are not a type themselves

    Args:
        parameter_name (_type_): any type

    Returns:
        bool: True - element is a Reference
    """
    return isinstance(parameter_name, ast.Reference)


def render_type(parameter_name, base_namespace=""):
    """function called from template to render type info

    Args:
        parameter_name (_type_): parameter name of a function
        base_namespace (str, optional): additional namespace used in template. Defaults to "".

    Returns:
        _type_: fully qualified type info
    """
    namespace = ""
    type_is_array = False
    if base_namespace != "":
        base_namespace = base_namespace + "::"
    type_to_render = parameter_name.type

    if is_array(type_to_render):
        type_to_render = parameter_name.type.type
        type_is_array = True

    if is_reference(type_to_render):
        namespace = f"{base_namespace}{type_to_render.reference.namespace.name}::"

    rendered_type = f"{namespace}{type_to_render.name}"

    if type_is_array:
        return f"std::vector<{rendered_type}>"

    return rendered_type

# Enumerators also require a bit of logic since they can have a value
# (equal sign) or not.


def render_enumerator(enum_object):
    """function called from template to render enum info

    Args:
        eo (enum): name of the enum

    Returns:
        string: generated info
    """
    if enum_object.value is not None:
        return f"{enum_object.name} = {enum_object.value.value},\n"

    return f"{enum_object.name},\n"


def template_render_complex_types(package, item, imports):
    """function called from template to render complex types

    Args:
        package (string): package the item is in
        item (string): item name
        imports (list): list of imports of given <package>

    Returns:
        string: generated info
    """
    result = ""

    timestamp = time.strftime("%Y-%m-%d, %H:%M:%d")

    # Store the type reference hierarchy
    for structure in item.structs.values():
        for fields in structure.fields.values():
            if is_array(fields.type):
                # The relevant reference is to the inner type (elements of array)
                type_reference(structure.name, fields.type.type.name)
            else:
                type_reference(structure.name, fields.type.name)

        tpl = env.get_template('struct.tpl')
        rendered_text = tpl.render(item=structure, render_type=render_type)
        store_rendered_type(structure.name, rendered_text)

    for unions in item.unions.values():
        for fields in unions.fields.values():
            if is_array(fields.type):
                # The relevant reference is to the inner type (elements of array)
                type_reference(unions.name, fields.type.type.name)
            else:
                type_reference(unions.name, fields.type.name)

        tpl = env.get_template('union.tpl')
        rendered_text = tpl.render(item=unions, render_type=render_type)
        store_rendered_type(unions.name, rendered_text)

    for enumerations in item.enumerations.values():
        for parameter_name in enumerations.enumerators.values():
            type_reference(enumerations.name, parameter_name.name)  # FIXME This is not needed...
        if enumerations.extends is not None:
            type_reference(enumerations.name, enumerations.extends)

        tpl = env.get_template('enumeration.tpl')
        rendered_text = tpl.render(item=enumerations, render_enumerator=render_enumerator)
        store_rendered_type(enumerations.name, rendered_text)

    for type_defs in item.typedefs.values():
        type_reference(type_defs.name, type_defs.type.name)

        tpl = env.get_template('typedef.tpl')
        rendered_text = tpl.render(item=type_defs, render_type=render_type)
        store_rendered_type(type_defs.name, rendered_text)

    for arrays in item.arrays.values():
        type_reference(arrays.name, arrays.type.name)

        tpl = env.get_template('array.tpl')
        rendered_text = tpl.render(item=arrays, render_type=render_type)
        store_rendered_type(arrays.name, rendered_text)

    for maps in item.maps.values():
        type_reference(maps.name, maps.key_type.name)
        type_reference(maps.name, maps.value_type.name)

        tpl = env.get_template('map.tpl')
        rendered_text = tpl.render(item=maps)
        store_rendered_type(maps.name, rendered_text)

    # Determine type rendering order
    sys.stdout.write("Reordering type definitions : ")
    prepare_swap_types()
    swap_occurred = True
    while swap_occurred:
        sys.stdout.write('.')
        swap_occurred = reorder_types()
    print("")

    # OK, now output rendered types in the right order
    for idx, rendered_text in enumerate(rendered_types_ordered):
        result += f"\n// Typedef #{idx} from {item.name} in package {package.name}\n"
        result += rendered_text[1]

    tpl = env.get_template('typesheader.tpl')
    fullresult = tpl.render(body=result, timestamp=timestamp,
                            boilerplate=boilerplate_from_file(),
                            imports=list(imports),
                            name=item.name)

    return fullresult


def prepare_swap_types():
    """Preparation: store the location of types
       in rendered_types_ordered for easy lookup

    """
    for index, rendered_item in enumerate(rendered_types_ordered):
        name = rendered_item[0]
        rendered_types_index[name] = index


def swap_them(item_1, item_2):
    """swap order of items to make sure
       referred types are mentioned first

    Args:
        a (_type_): any item
        b (_type_): any other item
    """

    # Get indices
    item_index_1 = rendered_types_index[item_1]
    item_index_2 = rendered_types_index[item_2]

    # Swap (typename, text) pair location in array
    item_tmp = rendered_types_ordered[item_index_1]
    rendered_types_ordered[item_index_1] = rendered_types_ordered[item_index_2]
    rendered_types_ordered[item_index_2] = item_tmp

    # Update indices
    rendered_types_index[item_1] = item_index_2
    rendered_types_index[item_2] = item_index_1


def b_is_defined_later_than_a(item_a, item_b):
    """helper for "swap_them"
       check if type_a is defined later
       then type_b

    Args:
        a (_type_): _description_
        b (_type_): _description_

    Returns:
        _type_: _description_
    """
    return rendered_types_index[item_a] < rendered_types_index[item_b]


def reorder_types():
    """
    What are we doing here?
    => If a complex type (e.g. struct) references another type, then the
    referenced type must be defined before it is used.   If it's defined
    after, we swap the location of the referencer and referencee.
    Repeat this process until no more swaps are necessary.

    WARNING: This is a solution with O(n^3) complexity!  Although it's still
    exponential it might be improved greatly by using another datastructure
    (with O(1) lookup), so that the inner loop deals ONLY with those types
    that are actually referenced by the first one.  But for the sizes we deal
    with, this seems to be fine for now.

    (Note it will also likely deadlock if a file has a circular dependency!
    Opportunity for improvement here...)

    Returns:
        _type_: ???
    """

    for rendered_item_1 in rendered_types_ordered:
        # We deal with the names of the types.  FIXME: A named tuple would be nice here.
        rendered_name_1 = rendered_item_1[0]
        for rendered_item_2 in rendered_types_ordered:
            rendered_name_2 = rendered_item_2[0]
            if a_reference_to_b(rendered_name_1, rendered_name_2) and \
                    b_is_defined_later_than_a(rendered_name_1, rendered_name_2):
                swap_them(rendered_name_1, rendered_name_2)
                return True

    # FIXME = notice and break circular dependency
    return False


def template_render_plain_file(processor, filterstr, template_file, prefix, suffix):
    """This is used for rendering source files that are not just a list of types.
       For example as class declarations (.h) and class method body defintion
       (.cpp)

    Args:
        processor (_type_): jinja processor (AST)
        filterstr (string): filter for type of file to be created
        template_file (filePath): template file to use for generation
        prefix (string): prefix for output filename
        suffix (string): postfix for output filename
    """
    tpl = env.get_template(template_file)
    timestamp = time.strftime("%Y-%m-%d, %H:%M:%d")

    result = ""
    for packages in processor.packages.values():
        # TODO Redo the imports --> #include connection
        imports = map(lambda parameter_name: parameter_name.namespace_reference, packages.imports)

        name = None
        if 'typecollections' in filterstr:
            for type_collection in packages.typecollections.values():
                name = type_collection.name
                rendered_text = tpl.render(item=type_collection,
                                           name=name,
                                           timestamp=timestamp,
                                           render_type=render_type,
                                           boilerplate="",
                                           imports=list(imports))
                result += rendered_text

        if 'interfaces' in filterstr:
            for interfaces in packages.interfaces.values():
                name = interfaces.name    # This takes priority for the chosen file name
                rendered_text = tpl.render(item=interfaces,
                                           name=name,
                                           timestamp=timestamp,
                                           render_type=render_type,
                                           boilerplate="",
                                           imports=list(imports))
                result += rendered_text

        if name is not None and len(result) != 0:
            write_result_file(boilerplate_from_file() + result, name, prefix, suffix)


def render_typedef_file(processor, filterstr, suffix):
    """This is used for headers that are expected to contain types.
       the order that types are defined is critical.

    Args:
        processor (_type_): jinja processor (AST)
        filterstr (string): filter for type of file to be created
        suffix (string): postfix for output filename
    """

    result = ""
    for packages in processor.packages.values():
        # TODO imports
        imports = map(lambda parameter_name: parameter_name.namespace_reference, packages.imports)

        # FIXME does not fully take into account what parts are imported
        # self.namespace    --  None for "import model"
        # self.package_reference
        # self.namespace_reference

        # Simple mapping.  For now it assumes all namespaces are unique and
        # not dependent on the path.  All type headers are generated into a
        # single directory and all are included without subdirectory
        # #include "namespacename.h"

        reset_rendered_types()
        if 'interfaces' in filterstr:
            for interfaces in packages.interfaces.values():
                result = template_render_complex_types(packages, interfaces, imports)
                if len(result) != 0:
                    write_result_file(result, interfaces.name, "", suffix)

        reset_rendered_types()
        if 'typecollections' in filterstr:
            for type_collections in packages.typecollections.values():
                result = template_render_complex_types(packages, type_collections, imports)
                if len(result) != 0:
                    write_result_file(result, type_collections.name, "", suffix)


def main():
    """main function

       FIDL_FILES must contain a list of files to be parsed.
    """
    for files in FIDL_FILES:
        log("-------------------------------------------------------")
        log(" ----- PROCESSING %s -----" % files)
        log("-------------------------------------------------------")
        process_file(files)


if __name__ == "__main__":
    main()
