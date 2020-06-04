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

## Operation

The code uses a Cirrus REST api to obtain the message details and performs analysis on the messages to save manual effort. Analysis algorithm can be configured per message classification.
The code uses your Cirrus credentials and assumes you have super user access as per a support user.

Unfortunately the API does not provide the ability to switch to super user so this is done by mimicking the user'sinteraction with the website using selenium. A chrome browser is opened, the user interactions performed and then the required tokens are obtained. The browser window closes after a short while.

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

### Logs
cirrus_analyser.log - Contains general log statements

cirrus-messages-summary.log - Contains message summary data only, these is the data you are most interested in for cirrus message details and summaries.

## Common issues

Sometimes the code will fail to find messages on cirrus. A common reason is that your sesion has expired, as the code caches certain session cookies. To clear these and force the code to obtain fresh details run:
```
python cmc.py clear-cache
```