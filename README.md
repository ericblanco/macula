# Macula

![Image of the eye](https://upload.wikimedia.org/wikipedia/commons/thumb/3/30/Blausen_0389_EyeAnatomy_02.png/500px-Blausen_0389_EyeAnatomy_02.png)
> Because the macula is yellow in colour it absorbs excess blue and ultraviolet light that enter the eye, and acts as a natural sunblock (analogous to sunglasses) for this area of the retina. The yellow color comes from its content of lutein and zeaxanthin, which are yellow xanthophyll carotenoids, derived from the diet. Zeaxanthin predominates at the macula, while lutein predominates elsewhere in the retina. There is some evidence that these carotenoids protect the pigmented region from some types of macular degeneration.

The Macula project will house all production code for the processing, deployment, and testing of ThreatStream indicators.  This project uses machine learning models to score IoC's based on a variety of features gathered through internal and external API queries.  

## Some History and Design Goals
This project was born out of Retina to solve a few limitations inherent in the configuration and fault tolerance strategies used historically.  Over time, the Retina repository has become cluttered with old experiments and data base models.  We have learned a lot from building Retina and it's come time to reconsider the design in order to improve model configuration, fault tolerance, and testability.
 
Fundamentally, Macula must replicate the same API functionality that Retina has supported historically.  In order to support the existing queue of bug reports though, we will need to improve the configuration and testability of the system.  The following design goals have come up through internal bug reports, customer complaints, and the need to test and iterate on future scoring models.

Aside from replication of existing Retina functionality, the initial goal will be to address the following JIRA tickets:
* OP-426: Retina: TTL feature for domains uses ttl from recursive NS, not authoritative NS
* OP-2526: Provide a flag in API to use/not use cache
* OP-2527: Retina API: Provide option to able to set custom feature set
* OP-2551: Add test cases for all feature gatherers
* OP-2677: Disabling retina features causes prediction error
* also log every API query so we know how hard we are hitting them.  maybe send it to graphite or something

Decoupled feature extraction from model configuration is key.  Each model must specify the features and formats that it is expecting, validating and correcting any inconsistencies due to unexpected feature values or missing data.  Models will accept feature lists in an intermediate json format conforming to a standard.  Models will then do further preprocessing to normalize and impute values, select important features, and score the feature vector.  Models will return the individual class scores for each indicator passed in.

Prior to a model being run over the feature list, each dependent API will be queried and an intermediate feature representation will be extracted.  The results for each API will be cached, but the caching strategy will be configurable on a per-API basis.  This will allow us to get higher resolution feature values for some API's which are cheap and lower resolution for others which may be costly or sensitive to high request rates.

The responses for each feature API will be logged if anything unusual is detected.  This will indicate when API's change so that we are alerted to change our parsing code.

The code should make it clear what features are extracted at each step without hard coding expected values.  Updates to the values returned by API's should be handled gracefully, but we should be notified immediately of any API updates to the shape of responses.

# Macula New Version
![Macula](./images/macula.png)
Macula was suffering from an increasing number of FP/FN and also lack of score transparency. To suppress the drawbacks we changed the Macula's design. Current Macula is not anymore an ML approach, it's now a combination of ML and Rule-based approaches. 
The changes that we made to improve macula accuracy are:
- Whitelist rule: We check the queried IoCs against a whitelist. If the IOC is in the whitelist,  Maclua scores the IOC as 0 (benign).
- Blacklist rule: We check the queried IoCs against a blacklist. If the IOC is on the blacklist,  Maclua scores the IOC as 100 (Malicious).
- Feed rule: Macula is maintaining a list of IOCs from the trusted opensource feeds, if one of these feeds report the IOC as malicious, Maclua increases its score. 
- Darklist rule: We check the queried IoCs against a Darklist. If the IOC is on the Darklist,  Maclua increases its score. 
- Domain-Pivoting: This only applies on the IPs. If an IP is recently hosting some domains, Macula scores top domains and returns the minumum score of these domains as the IP's score. If one of these top domains is in a whitelist, the final IP's score is zero.

To make Macula transparent, Macula extracts the contribution of each features, puts the contribution of features from the same categories to gether, and rescales them to show which feature categores have more contirbution in final score.
The feature categories are   
- Open Port Behaviours: censys,
- Passive DNS: farsight,
- Online Reputation and Internet Safety: wot, Bitdefender, majestic, neutrino,
- Whois: whoisxml,
- Geolocation: geo

# Training Process:
To be able to train on the big training set, we do the training phase in Databricks to have access to enough memory. The training phase has multiple steps between Databricks and Macula. We do the computations and data processing in Databricks and feature gathering and enrichment by Macula.
The below figure shows the training process. 
![training](./images/macula-traning.png)

### Step 1: Generating the training and testing data.
This part is done in Databrick.
Databricks noteboook:
Training st: https://anomali.cloud.databricks.com/#notebook/199639
Testing set: https://anomali.cloud.databricks.com/#notebook/199736/

### Step 2: Gathering and enriching features.
This part is done by Macula. Macula calls Telescope to collect the raw features and then enrich them.
- Command line: `python ml_eval.py -t /path/to/trainingset -f /path/to/save/raw-features -r /path/to/save/enriched-features`

### Step 3: Feature Selection.
This part is done in Databrick and drops the useless features.
- Databricks noteboook: 
https://anomali.cloud.databricks.com/#notebook/193554/


### Step 4: Model Training:
This part is done in Databrick.
- Databricks noteboook: https://anomali.cloud.databricks.com/#notebook/198037/

### Step 4: Loading the model:
- Macula picks up the new models from S3 frequently and archives them in S3.

# Training Automation:
We have automated the whole training process. This pipeline does the training job for us: https://ghe.anomali.com/ThreatStream/macula-automations

# Macula Pieces:
As we mentioned earlier, Macula relies on several lists. In this part, we point to the pipelines that generate these lists:
- Whitelist: this list is created by a pipeline in https://ghe.anomali.com/TS-Labs/whitelists_new. Variable `MACULA_WHITELIST_CRON_STR` in `setting.py` controls how frequently Macula loads the new whitelist.
- Blacklists and Darklist: this list is created by a pipeline in https://ghe.anomali.com/ThreatStream/DS-Blacklist. Variable `MACULA_IP_BLACKLIST_CRON_STR`, `MACULA_DM_BLACKLIST_CRON_STR`, and `MACULA_DARKLIST_CRON_STR` in `setting.py` control how frequently Macula loads the new IP blacklist, Domain blacklist, and Darklist, respectively.
- Feed list: this list is created by a pipeline in https://ghe.anomali.com/ThreatStream/macula-scraper. Variable `MACULA_FEEDS_CRON_STR`  controls how frequently Macula loads the new feed list.





## Architecture
macula.py - runs the main Macula server with endpoints:
- /api/score
  - hits telescope
  - for each indicator, pull out internal.type from dict results returned by telescope
  - separate into groups by internal.type and run through appropriate classifier
  - return flat dict of results in the shape:
```
        <ioc>: {
            benign: float 0-1,
            malicious: float 0-1,
            meta: {
                source: "",
                explanation: <explain results>,
                type: "ioc type",
                success: true,
                summary: <summary results>
            },
            rescaled: float 0-100 
            }
```


models.models.py includes generic modeling functionality for classifying network indicators

## S3 bucket and paths:
All the S3 paths are in `setting.py`. Make sure the paths in this file correspond with the paths in all the Databricks notebooks, and list pipelines.


## Installation

Macula's cache requires postgres 9.5+ since it uses `INSERT ... ON CONFLICT DO ...` (https://wiki.postgresql.org/wiki/What's_new_in_PostgreSQL_9.5#INSERT_..._ON_CONFLICT_DO_NOTHING.2FUPDATE_.28.22UPSERT.22.29).

```
# Tested on Ubuntu 14.04.4
./install.sh

# On OS X, you'll need to run
brew install gcc@5
to ensure xgboost installs correctly.
```
- Set up environment variable:

`virtualenv -p /usr/bin/python2.7 venv`

- Activate the env variable:

`source venv/bin/activate`

- Install requirements:

`pip install -r requirements.txt`

### Installation notes:
Python package `gglsbl` requires `sqlite3` on  your machine. Please follow these steps on your MacOS:
```
(venv) % brew install sqlite3
(venv) % echo 'export PATH="/usr/local/opt/sqlite/bin:$PATH"' >> ~/.zshrc
(venv) % export LDFLAGS="-L/usr/local/opt/sqlite/lib"
(venv) % export CPPFLAGS="-I/usr/local/opt/sqlite/include"
(venv) % pip install pysqlite
(venv) % pip install gglsbl==0.3 
```
### Configuration
    - Set the S3 bucket key and secret in `settings.py`

# Start the Macula server
python macula.py runserver

# Macula Parameters
- &useCache: enables the cache to retrieve the scores from the cache. The default is true.
- &useWhitelist: enables using the whitelist in scoring the IOCs. The default is true.
- &useBlacklist: enables using the blacklist in scoring the IOCs. The default is true.
- &domain_pivot: to determine the number of recent domains that we use in domain-pivot. The default is 5. If this parameter is set to 0, it disables the domain pivot process and IPs are scored by IP model.
- &useRule: enables using the rules in scoring the IOCs. The default is true.
- &summary: generates the subscores for each features category. The default is false. Enabling this slows down the scoring.
- &explain: generates the contribution of each feature for each. The default is false. Enabling this slows down the scoring.
- &explain_items: determines the number of features that we display in when `&explain=true`. The default is 10.

# Score batch of indicators using the Macula server
macula.threatstream.com/api/score?indicators=129.21.187.44,adobeflashmanager.online&useCache=true&summary=true

## Deployment
```
# Deploy new model to production
- production changes can be observed here: https://tswiki.atlassian.net/wiki/spaces/DATASCI/pages/116540077/Macula+testing+changelog
- both a telescope instance and a redis database are required to successfully deploy a working macula model, for more information see: https://tswiki.atlassian.net/wiki/spaces/DATASCI/pages/202277046/Anomali+Spark+workflow
```
