import json
import re
import logging
from logging.config import fileConfig

from main.cli.cli_parser import LIST, SEARCH
from main.config.configuration import ConfigSingleton, LOGGING_CONFIG_FILE
from main.config.constants import FUNCTION, PROJECT, GROUP, OPTIONS, DataType, OUTPUT, TABLE, ENTITY, PROJECTS, GROUPS, \
    VERBOSE, BRANCHES, TAGS, COMMITS, PARAMETERS
from main.formatter.formatter import Formatter, DynamicFormatter
from main.http.gitlab_proxy import GitlabProxy

from main.utils.utils import error_and_exit

fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('main')


class GitLabCommandProcessor:
    """Main class that takes cli arguments and actions them by communicating with GitLab"""

    def __init__(self):
        self.configuration = ConfigSingleton()
        self.formatter = DynamicFormatter()
        self.git_proxy = GitlabProxy()

    def action_cli_request(self, cli_dict):
        """Take the cli arguments, validate them further and action them"""
        # Determine behaviour based on supplied arguments
        function_to_call = cli_dict.get(FUNCTION, None)
        entity_to_list = cli_dict.get(ENTITY, None)
        project = cli_dict.get(PROJECT, None)
        parameters = cli_dict.get(PARAMETERS, None)
        group = cli_dict.get(GROUP, None)
        options = cli_dict.get(OPTIONS)
        # forcing output to table intitially. Git does support json.
        options[OUTPUT] = TABLE

        if not entity_to_list:
            error_and_exit("Please specific an entity to find for GIT eg projects")


        logger.info("Received CLI request to list git: {}".format(entity_to_list))
        logger.debug("CLI command is: {}".format(str(cli_dict)))
        if function_to_call == LIST:
            if entity_to_list == PROJECTS:
                if group:
                    result = self.git_proxy.list_projects_for_group(group, options)
                    data_type = DataType.git_projects
                else:
                    result = self.git_proxy.list_projects(options)
                    data_type = DataType.git_projects
                reformated_data = flatten_project_list(result, options)

            elif entity_to_list == GROUPS:
                result = self.git_proxy.list_groups(options)
                data_type = DataType.git_groups
                reformated_data = flatten_group_list(result, options)

            elif entity_to_list == BRANCHES:
                assert_that_project_id_given(project)
                result = self.git_proxy.list_branches_for_project(project, options)
                attrs = vars(result[0])
                print(', '.join("%s: %s" % item for item in attrs.items()))
                data_type = DataType.git_branches
                reformated_data = flatten_branch_list(result, options)

            elif entity_to_list == TAGS:
                assert_that_project_id_given(project)
                result = self.git_proxy.list_tags_for_project(project, options)
                data_type = DataType.git_tags
                reformated_data = flatten_tag_list(result, options)

            elif entity_to_list == COMMITS:
                assert_that_project_id_given(project)
                result = self.git_proxy.list_commits_for_project(project, options)
                data_type = DataType.git_commits
                reformated_data = flatten_commit_list(result, options)

            else:
                error_and_exit(f"Unknown command passed for GIT list: {entity_to_list}")

        elif function_to_call == SEARCH:
            # This is the search string/regex
            if not parameters:
                error_and_exit("GIT search requires the search text/regex to be passed in (within single quotes)")
            p = re.compile(chomp_quotes(parameters))

            if entity_to_list == PROJECTS:
                if group:
                    result = self.git_proxy.list_projects_for_group(group, options)
                else:
                    result = self.git_proxy.list_projects(options)
                data_type = DataType.git_projects
                reformated_data = flatten_project_list(filter_projects_by_name(result, p), options)

            elif entity_to_list == GROUPS:
                result = self.git_proxy.list_groups(options)
                data_type = DataType.git_groups
                # now filter and explode out data fields
                reformated_data = flatten_group_list(filter_groups_by_name(result, p), options)

            elif entity_to_list == BRANCHES:
                assert_that_project_id_given(project)
                result = self.git_proxy.list_branches_for_project(project, options)
                data_type = DataType.git_branches
                # now filter
                reformated_data = flatten_group_list(filter_branches_by_name(result, p), options)

            elif entity_to_list == TAGS:
                assert_that_project_id_given(project)
                result = self.git_proxy.list_tags_for_project(project, options)
                data_type = DataType.git_tags
                # now filter
                reformated_data = flatten_group_list(filter_tags_by_name(result, p), options)

            elif entity_to_list == COMMITS:
                assert_that_project_id_given(project)
                result = self.git_proxy.list_commits_for_project(project, options)
                data_type = DataType.git_commits
                # now filter
                reformated_data = flatten_group_list(filter_commits_by_name(result, p), options)
            else:
                error_and_exit(f"Unknown command passed for GIT search: {entity_to_list}")
        else:
            error_and_exit(f"Unknown command passed for GIT: {entity_to_list}")

        self.formatter.format(data_type, reformated_data, options)


def chomp_quotes(search_string):
    if search_string and search_string[0] == r"'" and search_string[-1] == r"'":
        return search_string[1:-1]
    return search_string


def assert_that_project_id_given(project):
    if not project:
        error_and_exit(f"The given GIT command requires the project id to be passed in eg --project 15")


def filter_groups_by_name(groups, search_pattern):
    return [single_group for single_group in groups if search_pattern.match(single_group.name)]


def filter_projects_by_name(projects, search_pattern):
    return [single_project for single_project in projects if search_pattern.match(single_project.name)]


def filter_branches_by_name(branches, search_pattern):
    return [item for item in branches if search_pattern.match(item.name)]


def filter_tags_by_name(tags, search_pattern):
    return [item for item in tags if search_pattern.match(item.name)]


def filter_commits_by_name(commits, search_pattern):
    return [item for item in commits if search_pattern.match(item.name)]


def escape_description(description):
    return repr(description)


def convert_group_to_list(group, options):
    if options[VERBOSE]:
        return [group.id, group.name, group.path, group.visibility, escape_description(group.description)]
    return [group.id, group.name]


def convert_project_to_list(project, options):
    if options[VERBOSE]:
        return [project.id, project.name, project.visibility, escape_description(project.description), project.archived]
    return [project.id, project.name]


def convert_branch_to_list(branch, options):
    if options[VERBOSE]:
        return [branch.name, branch.merged, branch.protected, branch.developers_can_push, branch.developers_can_merge, branch.can_push, branch.default, branch.web_url]
    return [branch.name]


def convert_tag_to_list(tag, options):
    if options[VERBOSE]:
        return [tag.name, tag.path, tag.location]
    return [tag.name]


def convert_commit_to_list(commit, options):
    if options[VERBOSE]:
        return [commit.id, commit.created_at, commit.parent_ids, commit.title, commit.message, commit.author_name, commit.author_email, commit.authored_date, commit.committer_name, commit.committer_email, commit.committed_date, commit.web_url]
    return [commit.id, commit.title]


def flatten_group_list(groups, options):
    return [convert_group_to_list(single_group, options) for single_group in groups]


def flatten_project_list(projects, options):
    return [convert_project_to_list(single_project, options) for single_project in projects]


def flatten_branch_list(branches, options):
    return [convert_branch_to_list(single_branch, options) for single_branch in branches]


def flatten_tag_list(tags, options):
    return [convert_tag_to_list(single_tag, options) for single_tag in tags]


def flatten_commit_list(commits, options):
    return [convert_commit_to_list(single_commit, options) for single_commit in commits]
