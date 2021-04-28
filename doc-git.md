# ADM based functionality
This tool supports working with Gitlab allowing the user to get key data on project repositories from a single interface.

## Configuration
- Ensure that you have GitLab credentials
- Create a git config file in your home directory eg `C:/Users/klairb/.python-gitlab.cfg`
- The file should contents should look like:
  ```
  [global]
  default = agb
  ssl_verify = False
  timeout = 5

  [agb]
  url = https://gitlab.agb.rbxd.ds/
  private_token = xxxxxxxxxxxxyyyyyyyzzzzz
  api_version = 4
  ```
- Now the token detailed in the file above must be generated, to do this follow the steps:
  - Login to Gitlab
  - click on your user profile (top right) and select settings
  - navigate to Access token via the left page menu
  - create a new token with the following grants: `api, read_user, read_api, read_repository, read_registry`
  - Paste the token into the file you created above.
- Enter your credentials within the file: [resources/credentials.json](./app/resources/credentials.json) in the following format:
  ```json
  {
    "gitlab": {
      "gitlab_config_file": "C:/Users/klairb/.python-gitlab.cfg",
      "gitlab_id": "agb"
    }
  }
  ```

## Sample commands
List Groups
```
cmc.py git list groups
```
List Projects
```
cmc.py git list projects
```
List Projects for a given group
```
cmc.py git list projects --group 27
```
List Branches for a Project
```
cmc.py git list branches --project 15
```
List Tags for a Project
```
cmc.py git list tags --project 15
```
List Commits for a Project
```
cmc.py git list commits --project 15
```
Search for Groups matching regex or string
```
cmc.py git search groups '^[pP].*'
```
Search for Projects matching regex or string
```
cmc.py git search projects 'warehouse.*'
```

## Common issues
The Git api doesn't always return back all available entries, in such cases you need to specify return all via the `-a` flag

List all Projects
```
cmc.py git -a list projects
```

All of the GIT commands have two levels of detail. By default the tool displays a limited set of fields. If you wish to view all the fields then specify the verbose flag via the `-v` flag

List Project tags with all fields
```
cmc.py git -v list tags --project 15
```
