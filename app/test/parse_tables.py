from os import listdir
from os.path import isfile, join
import re

CREATE_LINE_REGEX = re.compile(r'^.*CREATE\s+TABLE\s+\[(.+)\]\.\[(.+)\]')
COLUMN_LINE_REGEX = re.compile(r'^\s*\[(.+)\]\s+(\w+)\s+(.*)')
END_DECLARATION_REGEX = re.compile(r'^\s*\);\s*$')
CONSTRAINT_REGEX = re.compile(r'^\s*CONSTRAINT\s+\[.+\]\s+FOREIGN\s+KEY\s+\(\[(.+)\]\)\s+REFERENCES\s+\[(.+)\]\.\[(.+)\]\s+\(\[(.+)\]\)')


def detect_column_boundaries(lines):
    number_of_lines = len(lines)
    bit_lines = [list(map(lambda x: 0 if x == ' ' else 1, line)) for line in lines]
    char_count_list = [sum(x) for x in zip(*bit_lines)]
    # print(char_count_list)
    boundary_index = []

    ignoring_start_whitespace = True
    for index, value in enumerate(char_count_list):
        if ignoring_start_whitespace and value == 0:
            continue
        elif ignoring_start_whitespace and value != 0:
            ignoring_start_whitespace = False
        elif value == 0:
            if index < len(char_count_list) and char_count_list[index+1] == number_of_lines:
                boundary_index.append(index + 1)
                # print("Whitespace boundary: {}".format(index + 1))
    return boundary_index


def parse_field_name(given_string):
    match = re.match(r'^\[(.+)\]', given_string)
    if match:
        return match.group(1)
    return ""


def get_column_fields(column_lines, boundaries):
    first_marker = boundaries[0]
    second_marker = boundaries[1]
    for line in column_lines:
        print("  {} {}".format(parse_field_name(line[0:first_marker]), line[first_marker:second_marker].strip()))
        # line[second_marker:]


def format_constraints(constraints_list):
    for constraint in constraints_list:
        print("Ref: {}.{} > {}.{}".format(constraint[0], constraint[1], constraint[2], constraint[3]))


if __name__ == '__main__':
    table_directory = "C:\\repositories\\Krka.RebateManagement\\Krka.RebateManagement.Database\\dbo\\Tables"
    sql_files = [f for f in listdir(table_directory) if isfile(join(table_directory, f)) and f.endswith(".sql")]
    # print(sql_files)

    for filename in sql_files:
        # print(f"processing sql file: {filename}")
        print()
        with open(join(table_directory, filename)) as f:
            parsing_table = False
            column_lines = []
            constraints = []
            while True:
                line = f.readline().strip()
                if not line:
                    break
                # print("Parsing line: {}".format(line))
                line_parsed = False
                match_result = re.match(CREATE_LINE_REGEX, line)
                if match_result:
                    parsing_table = True
                    schema_name = match_result.group(1)
                    table_name = match_result.group(2)
                    line_parsed = True
                    # print("Parsed create table line with name: {}".format(table_name))
                elif parsing_table:
                    # print("Parsing table line: {}".format(line))
                    column_result = re.match(COLUMN_LINE_REGEX, line)
                    if column_result:
                        # print("Parsed column line: {}".format(line))
                        column_lines.append(line)
                        line_parsed = True
                    elif re.match(r'^\s*CONSTRAINT\s+', line):
                        constraint_match = re.match(CONSTRAINT_REGEX, line)
                        if constraint_match:
                            constraints.append([table_name, constraint_match.group(1), constraint_match.group(3), constraint_match.group(4)])

                    if not line_parsed:
                        end_declaration_match = re.match(END_DECLARATION_REGEX, line)
                        if end_declaration_match:
                            parsing_table = False
                            line_parsed = True
                elif not parsing_table:
                    print("Parsing post definition line: {}".format(line))
                    if not line.strip():
                        pass
                    elif "GO" in line:
                        pass
                    elif "CREATE" in line and "INDEX" in line:
                        pass
                    elif "ON" in line and line.endswith(";"):
                        pass
                    else:
                        print(">>> Unknown post declaration line: [{}}]".format(line))

            print("Table %s {" % table_name)
            # print("Parsed table: {}".format(table_name))
            # print("Constraints:")
            # print(constraints)
            # print("Column lines:")
            # print("\n".join(column_lines))
            boundary_index_list = detect_column_boundaries(column_lines)
            get_column_fields(column_lines, boundary_index_list)
            print("}")
            format_constraints(constraints)
    print("All done")
