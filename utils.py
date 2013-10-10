"""
A collection of utility functions.
"""

import codecs


def readResultFile(filename):
    """
    Read Turker result file.

    The input file format is as following:

        entry 1 field 1
        entry 1 field n

        entry 2 field 1
        entry 2 field n

    Returns:
    --------
    [[field 1, field n], [field 1, field n]]

    Reads a file containing groups of fields (one field per line) separated by
    empty lines, into an array of arrays of fields.
    """
    file_ = codecs.open(filename, "r", "utf-8")
    entries = []
    fields = []
    for line in [l.strip() for l in file_.readlines()]:
        if line != "":
            fields.append(line)
        else:
            entries.append(fields)
            fields = []
    file_.close()
    return entries


def readFile(filename):
    return [line.strip() for line in codecs.open(filename, "r", "utf-8").readlines()]


def write(List, key_index, filename):
    """
    Sort a list of tuples by the tuple value at <key_index> and write it to <filename>.
    """
    file_ = codecs.open(filename, "w", "utf-8")
    Dict = {}
    for Tuple in List:
        for element in Tuple:
            lines = []
            if element != Tuple[key_index]:
                lines.append(element)
        Dict.setdefault(Tuple[key_index], []).append("\n".join(lines))
    elements = []
    for key in sorted(Dict.keys()):
        elements.append(key+"\n\n".join(Dict[key]))

    file_.write("\n\n".join(elements))
    file_.close()


def indent(elem, level=0):
    """
    Indents the child Elements of an XML element to make it more pretty.
    """
    i = "\n" + level * "    "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "    "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i








