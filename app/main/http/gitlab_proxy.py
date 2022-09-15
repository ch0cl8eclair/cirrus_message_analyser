import gitlab

from main.config.configuration import ConfigSingleton
from main.config.constants import GITLAB_CONFIG_FILE, GITLAB_DEFAULT_ID, GITLAB, CREDENTIALS


# TODO update class to handle output as json parameter
class GitlabProxy:
    """All fetch functionality for Gitlab access"""

    def __init__(self):
        self.configuration = ConfigSingleton()
        config_file = self.configuration.get(CREDENTIALS).get(GITLAB).get(GITLAB_CONFIG_FILE)
        default_git_id = self.configuration.get(CREDENTIALS).get(GITLAB).get(GITLAB_DEFAULT_ID)
        self.git_interface = gitlab.Gitlab.from_config(default_git_id, [config_file])

    def __handle_options__(self, options, include_all=False):
        search_options = {}
        if include_all:
            search_options['all'] = True
        if options['all']:
            search_options['all'] = True
        return search_options

    def list_groups(self, options):
        search_options = self.__handle_options__(options, True)
        groups = self.git_interface.groups.list(**search_options)
        return groups

    def list_projects(self, options):
        search_options = self.__handle_options__(options)
        projects = self.git_interface.projects.list(**search_options)
        return projects

    # The search term here seems to be for simple text only, but it is faster to execute on the server
    def search_projects(self, search_term, options):
        search_options = self.__handle_options__(options)
        search_options["search"] = search_term
        projects = self.git_interface.projects.list(**search_options)
        return projects

    def list_projects_for_group(self, group_id, options):
        projects = None
        group = self.git_interface.groups.get(group_id)
        if group:
            search_options = self.__handle_options__(options)
            projects = group.projects.list(**search_options)
        return projects

    def search_group(self, search_pattern, options):
        search_options = self.__handle_options__(options, True)
        groups = self.git_interface.groups.list(**search_options)
        return [record for record in groups if search_pattern.match(record.name)]

    def search_project(self, search_pattern, options):
        search_options = self.__handle_options__(options)
        projects = self.git_interface.projects.list(**search_options)
        return [record for record in projects if search_pattern.match(record.name)]

    def list_branches_for_project(self, project_id, options):
        my_project = self.git_interface.projects.get(project_id)
        branches = my_project.branches.list()
        return branches

    def list_tags_for_project(self, project_id, options):
        my_project = self.git_interface.projects.get(project_id)
        repositories = my_project.repositories.list()
        repository = repositories.pop()
        tags = repository.tags.list()
        return tags

    def list_commits_for_project(self, project_id, options):
        my_project = self.git_interface.projects.get(project_id)
        # commits = my_project.commits.list(ref_name='my_branch')
        # commits = my_project.commits.list(since='2016-01-01T00:00:00Z')
        commits = my_project.commits.list()
        return commits