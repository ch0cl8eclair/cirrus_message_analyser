# cirrus_message_analyser

Support desk message analysis script that interfaces with Cirrus to analyse problem messages and classify them

## Installation

Following the following steps to get your system up and running
1. Install python (latest v3 or at least v3.7)
```
visit https://www.python.org/downloads/
```
2. Install the python package installer tool 
```
visit https://pip.pypa.io/en/stable/installing/
```
3. Checkout this repository, the master branch should be stable
```
git clone https://gitlab.agb.rbxd.ds/klairb/cirrus_message_analyser.git
```
4. Now install the required modules the code requires to run:
```
pip install -r ./app/requirements.txt
```
5. Install the chrome webdriver for your chrome browser version.
```
Use the script if you use WSL or cygwin (this will install the latest stable version, which probably matches your current installed chrome version):
. ./app/update-driver.sh

OR

Open chrome, select menu -> help -> about google chrome and read the version number eg 83.0.4103
Visit https://chromedriver.chromium.org/downloads and download the corresponding version file
Unzip the file to the app/driver folder and give it a unique name eg chromedriver83_win32. There needs to be an executable within the folder with the default name: chromedriver
Update the config to point to this folder name either via the app/resources/configuration.json with variable name: chrome-driver-folder or set an environment variable with the name: CHROME-DRIVER-FOLDER
```

## Operation

The code uses a Cirrus REST api to obtain the message details and performs analysis on the messages to save manual effort. Analysis algorithm can be configured per message classification.
The code uses your Cirrus credentials and assumes you have super user access as per a support user.

Unfortunately the API does not provide the ability to switch to super user so this is done by mimicking the user's interaction with the website using selenium. A chrome browser is opened, the user interactions performed and then the required tokens are obtained. The browser window closes after a short while.

### Output formats
The tool permits output as JSON, CSV and Tabular display.

### Environment variables
You can set your Cirrus credentials either in the credentials.json file or in the following environment variables: CIRRUS_USERNAME, CIRRUS_PASSWORD.

## Configuration

Set your username and password into the following file:
```
app\resources\credentials.json
```

Define rules to process categories of messages such as the search parameters and the algorithms they should analysed with.
```
app\resources\rules.json
```

## Usage

Here are some sample queries:

Query Cirrus using the YARA_MOVEMENTS_BASIC rule (which has the search parameters defined) and for messages in the last day (now - 24 hours)
```
cmc.py list messages --rule YARA_MOVEMENTS_BASIC --time 1d
```
Query Cirrus using the SYNGENTA_1 rule and for messages over the last two days and output data in csv format (default)
```
cmc.py list messages --rule SYNGENTA_1 --time 2d --output csv
```
Query Cirrus using the YARA_MOVEMENTS_BASIC rule and for messages in the last 3 days and output data in tabular form
```
cmc.py list messages --rule YARA_MOVEMENTS_COMPLEX --time 3d --output table
```
Query Cirrus for a message's payloads, you must supply the message unique id
```
cmc.py list message-payloads --uid 324324-23434-3423423
```
Query Cirrus for a message's events
```
cmc.py list message-events --uid 324324-23434-3423423
```
Query Cirrus for a message's metadata
```
cmc.py list message-metadata --uid 324324-23434-3423424
```
Query Cirrus for for a transformation using the source, destination and type defined in the rule
```
cmc.py list message-transforms --rule YARA_MOVEMENTS_BASIC
```
Analyse the messages defined by the rule YARA_MOVEMENTS_BASIC and that were processed yesterday
```
cmc.py analyse --rule YARA_MOVEMENTS_BASIC --time yesterday
```
Run analysis but limit the processing to the first message only. this saves on unwanted processing
```
cmc.py analyse --rule YARA_MOVEMENTS_BASIC --time yesterday --limit 1
```
Detail a single message, useful to gain initial insights, the command will also fetch matching logs from the ELK log server that match the message and message timeframe from the payload data
```
cmc.py detail --uid <message unique id> --output table
```
Obtain webpack for ICE Dashboard listed msg (it will zip up the logs, note the date format is a copy & paste from the dashboard)
```
cmc.py webpack --uid 324324-23434-3423424 --start-date "2020-11-23 13:13:40 GMT"
```
Obtain webpack for Cirrus listed msg (note the different ISO date format)
```
cmc.py webpack --uid 324324-23434-3423424 --start-date 2020-05-17T10:30:08.877Z --end-date 2020-05-17T10:31:18.312Z
```

List the configured rules
```
cmc.py list rules
```
Clear the caches
```
cmc.py clear-cache
```

Note that you can use durations such as: today, yesterday, 1d, 10h. Where specifying hours or days, we set the start point to now minus the supplied quantity and the end point the the current time. Therefore today and 1d are not the same, as today is the time since midnight, where as 1d is the time since 24 hours prior.

You can of course specify the start and end dates in the same format that Cirrus supports:
```
cmc.py list messages --rule YARA_MOVEMENTS_BASIC --start-date 2020-05-17T10:30:00 --end-date 2020-05-17T10:30:08.877Z
```
### ADM interface and usage
There is an ADM interface to fetch information for builds from this tool, [please click here](./doc-adm.md) for details

### Gitlab interface and usage
There is an Git interface to fetch information on repositories from this tool, [please click here](./doc-git.md) for details

### Logs
cirrus_analyser.log - Contains general log statements

cirrus-messages-summary.log - Contains message summary data only, these is the data you are most interested in for cirrus message details and summaries.

## Common issues

Sometimes the code will fail to find messages on cirrus. A common reason is that your session has expired, as the code caches certain session cookies. To clear these and force the code to obtain fresh details run:
```
python cmc.py clear-cache
```

Selenium requires an exact match with your Chrome browser version (with regards to obtaining super user access). Should your chrome version be updated by a security patch then the functionality will break.
```
See step five on installation to fix this.

OR

from git bash and the root project folder run:
  make update-driver

This will download and unzip the latest driver, all you have to do is update the folder name within the config file.
```

## Upgrading
To upgrade to version 2 from version 1:

- git pull to get the latest version
- install the new elasticsearch package using pip or disable elasticsearch feature by turning off the config switch: ```enable_elasticsearch_query``` within ```resource/configuration.json```
- Upgrade you credentials file to now have credentials to both Cirrus and Elasticsearch (this will be you standard operations network credentials)

To upgrade to version 3 from version 2:

- git pull to get the latest version
- install the new required python-dateutil package via pip
- Check the chrome browser version and chrome driver versions as per install instructions
- ice dashboard functionality is enabled by default but to disable it alter the ```enable_ice_login``` flag  within ```resource/configuration.json```
- Upgrade you credentials file to now have credentials for Cirrus, Elasticsearch and ICE

To upgrade to version 4 from version 3:

- git pull to get the latest version
- install the new required gitlab package via pip
- Check the chrome browser version and chrome driver versions as per install instructions
- Upgrade you credentials file to now have credentials for GitLab

