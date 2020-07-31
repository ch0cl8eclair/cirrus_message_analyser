import os
import sys
import pandas as pd

excel_file_to_process = r'C:\Users\klairb\Documents\rbi\keis-logged-issues.xlsx'

rule_format_str = """
(defrule {}
(source {}) (destination {}) (document-type {})
=>
(printout t \"Please visit: {}\" crlf))
"""



counter = 0


def main():
    do_pandas()


def has_muliple_types(given_type_str):
    return given_type_str and "/" in given_type_str


def types_str_to_list(given_type_str):
    return given_type_str.split('/ ')


def format_rule(row_dict):
    global counter
    rule_name = "keis_rule_{}".format(counter)
    counter = counter + 1
    source = row_dict['Sender'].lower()
    dest = row_dict['Recipient'].lower()
    doc_type = row_dict['Msg Type'].lower()
    url = row_dict['Action']
    if has_muliple_types(doc_type):
        types_list = types_str_to_list(doc_type)
        for current_type in types_list:
            print(rule_format_str.format(rule_name, source, dest, current_type, url))
    else:
        print(rule_format_str.format(rule_name, source, dest, doc_type, url))


def do_pandas():
    sheet_to_df_map = pd.read_excel(excel_file_to_process, sheet_name="Sheet1")
    # print(sheet_to_df_map)
    print(sheet_to_df_map.columns.ravel())
    for index, row in enumerate(sheet_to_df_map.to_dict(orient='record')):
        format_rule(row)


def read_single_sheet():
    sheet_to_df_map = pd.read_excel(excel_file_to_process, sheet_name=None)
    for sheet_name in sheet_to_df_map.keys():
        if sheet_name == "Sheet1":
            print("processing key sheet")
            headings_list = list(sheet_to_df_map[sheet_name].iloc[0])
            print(', '.join(headings_list))


# Excel file location: C:\Users\klairb\Documents\rbi\keis-logged-issues.xlsx
if __name__ == '__main__':
    main()

