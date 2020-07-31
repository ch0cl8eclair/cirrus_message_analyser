import csv
import json
from collections import defaultdict


def ctree():
    """ One of the python gems. Making possible to have dynamic tree structure.

    """
    return defaultdict(ctree)


def build_leaf(name, leaf):
    """ Recursive function to build desired custom tree structure

    """
    res = {"name": name}

    # add children node if the leaf actually has any children
    if len(leaf.keys()) > 0:
        res["children"] = [build_leaf(k, v) for k, v in leaf.items()]

    return res


def main():
    """ The main thread composed from two parts.

    First it's parsing the csv file and builds a tree hierarchy from it.
    Second it's recursively iterating over the tree and building custom
    json-like structure (via dict).

    And the last part is just printing the result.

    """
    tree = ctree()
    file_name = "c:/temp/kira-namespaces.txt"
    with open(file_name) as f:
        while True:
            line = f.readline().strip()
            if not line:
                break
            print("processing line: {}".format(line))
            columns_list = line.split('.')
            for col_index, column_value in enumerate(columns_list):
                if col_index == 0:
                    leaf = tree[column_value]
                else:
                    leaf = leaf[column_value]
    # print(tree)
    #
    # # building a custom tree structure
    # res = []
    # for name, leaf in tree.items():
    #     res.append(build_leaf(name, leaf))
    #
    # # printing results into the terminal
    # import json
    print(json.dumps(tree))


# so let's roll
main()