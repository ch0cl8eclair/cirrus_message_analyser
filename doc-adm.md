# ADM based functionality
This tool supports working with ADM allowing the user to get key data on builds from a single interface.

## Configuration
- Ensure that you have ADM credentials
- Enter your credentials within the file: [resources/credentials.json](./app/resources/credentials.json) in the following format:
  ```json
  {
    "adm_package_manager": {
      "username": "me@proagrica.com",
      "password": "password123"
    }
  }
  ```

## Sample commands
List ADM configs
```
cmc.py adm configs
```
List ADM locations
```
cmc.py adm locations
```
List ADM versions
```
cmc.py adm versions
```
List ADM scripts
```
cmc.py adm scripts
```
List ADM artifacts
```
cmc.py adm artifacts
```
List ADM versions for a specific project (project filtering can be done for all ADM commands)
```
cmc.py adm versions --project ping
```
List ADM versions for a grouping of projects, in this case for customer kws, these are defined in the [configuration.json](./app/resources/configuration.json) file under the entry: "adm-projects"
```
cmc.py adm versions --group kws
```