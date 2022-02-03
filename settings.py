import os
import re

TELESCOPE_CLIENT_REQUEST_TIMEOUT = int(os.getenv('TELESCOPE_CLIENT_REQUEST_TIMEOUT', 60*60*24))
TELESCOPE_CLIENT_CONNECT_TIMEOUT = int(os.getenv('TELESCOPE_CLIENT_CONNECT_TIMEOUT', 60*60*24))
TELESCOPE_CLIENT_MAX_CLIENTS = int(os.getenv('TELESCOPE_CLIENT_MAX_CLIENTS', 15))

TELESCOPE_URL = os.getenv('TELESCOPE_URL', "https://telescope.threatstream.com")
#TELESCOPE_URL = os.getenv('TELESCOPE_URL', "https://stg1-optic-telescope.threatstream.com")
#TELESCOPE_URL = os.getenv('TELESCOPE_URL', "https://ext-telescope.threatstream.com")
#TELESCOPE_URL = os.getenv('TELESCOPE_URL', "https://stg1-optic-telescope.threatstream.com")
#TELESCOPE_URL = os.getenv('TELESCOPE_URL', "http://datasci-mltest01.threatstream.com:8080")

#KONG_API_KEY = "c9e2addc277f4bcf9f809aa501e44f88"
KONG_API_KEY = "" 

# --- log ---
MACULA_DEBUG = os.getenv('MACULA_DEBUG', False)
MACULA_LOG_INTERVAL = int(os.getenv("MACULA_LOG_INTERVAL", 1)) * 60  # unit is millsecond

# NOTE: this must be "PORT" for shipbuilder
MACULA_PORT = int(os.getenv('PORT', '8080'))


BASEDIR = os.getcwd()
DGA_MODEL = os.getenv('DGA_MODEL', '{}/data/dga/mit_hyb_74fam_ep3.model'.format(BASEDIR))

MACULA_DB_NAME = os.getenv('MACULA_DB_NAME', None)
MACULA_DB_USER = os.getenv('MACULA_DB_USER', None)
MACULA_DB_PASSWORD = os.getenv('MACULA_DB_PASSWORD', None)
MACULA_DB_HOST = os.getenv('MACULA_DB_HOST', None)
MACULA_DB_PORT = int(os.getenv('MACULA_DB_PORT', 5432))

MACULA_SENTRY_URL = os.getenv('MACULA_SENTRY_URL', None)

MACULA_CACHE_INTERVAL_IN_DAYS = int(os.getenv('MACULA_CACHE_INTERVAL_IN_DAYS', 1))

# on-demand feature
MACULA_DOMAIN_PIVOT_TOP_NUM = os.getenv('MACULA_DOMAIN_PIVOT_TOP_NUM', 5)
MACULA_DOMAIN_PIVOT_BATCH_SIZE = os.getenv('MACULA_DOMAIN_PIVOT_BATCH_SIZE', 50)
MACULA_DOMAIN_PIVOT_TIME_RANGE = int(os.getenv('MACULA_DOMAIN_PIVOT_TIME_RANGE', 90)) * 24 * 60 * 60  # days

# folder
MACULA_RESOURCE = os.path.join(BASEDIR, "resources")

# load file option
MACULA_UPLOADFILE_SUPPORT_MODE = ["s3"]

# s3
MACULA_S3_ACCESS_KEY = os.getenv('MACULA_S3_ACCESS_KEY', None)
MACULA_S3_SECRET_KEY = os.getenv('MACULA_S3_SECRET_KEY', None)

# anamoli rule
ANOMALI_RULE_FILE = os.getenv('ANOMALi_RULE_FILE', None)
ANOMALI_RULE_FILE_PATH = os.path.join(BASEDIR, MACULA_ANOMALY_RULE_FILE)
ANOMALI_RULE_S3_PATH = os.getenv('GREY_LIST_S3_PATH', 'greylist/domain/domain_greylist.csv')
ANOMALI_RULE_URL = os.getenv('TELESCOPE_URL' + '/api/v1/anomali_rule.json')
ANOMALI_RULE_RETURN_VALUE ={
    "anomali_rules": {
      "dm_blacklist": [],
      "greylist": [{
        "detail": "{\"virustotal\": {\"engines\": [\"CINS Army\"]}}",
        "first_seen": "2022-01-24T00:00",
        "id": 111340169,
        "ip": "128.1.40.181/32",
        "last_seen": "2022-01-24T00:00",
        "list_type": "greylist",
        "times_seen": 4
      }


# # ip blacklist
# #MACULA_IP_BLACKLIST_ENABLE = int(os.getenv("MACULA_IP_BLACKLIST_ENABLE", 1))
# MACULA_IP_BLACKLIST_BUCKET = os.getenv('MACULA_IP_BLACKLIST_BUCKET', 'ts-labs')
# MACULA_IP_BLACKLIST_S3_PATH = os.getenv('MACULA_IP_BLACKLIST_S3_PATH', 'ipblklst/ipblklst/ip_global_blacklist_detail.csv')
# MACULA_IP_BLACKLIST_DEST_PATH = os.path.join(MACULA_RESOURCE, 'ipblklst_macula.csv')
# MACULA_IP_BLACKLIST_CRON_STR = os.getenv('MACULA_IP_BLACKLIST_CRON_STR', '0 7,19 * * *')
# MACULA_IP_BLACKLIST_RETURN_VALUE = (0,1,100)

# # domain blacklist, update once per month
# MACULA_DM_BLACKLIST_ENABLE = int(os.getenv("MACULA_DM_BLACKLIST_ENABLE", 1))
# MACULA_DM_BLACKLIST_BUCKET = os.getenv('MACULA_DM_BLACKLIST_BUCKET', 'ts-labs')
# MACULA_DM_BLACKLIST_S3_PATH = os.getenv('MACULA_DM_BLACKLIST_S3_PATH', 'dmblklst/dmblklst/dm_global_blacklist_detail.csv')
# MACULA_DM_BLACKLIST_DEST_PATH = os.path.join(MACULA_RESOURCE, 'dmblklst_macula.csv')
# MACULA_DM_BLACKLIST_CRON_STR = os.getenv('MACULA_DM_BLACKLIST_CRON_STR', '0 7,19 * * *')
# MACULA_DM_BLACKLIST_RETURN_VALUE = (0,1.0,100)


# whitelist top domains
# MACULA_WHITELIST_BUCKET = os.getenv('MACULA_WHITELIST_BUCKET', 'ts-labs')
# MACULA_WHITELIST_S3_PATH = os.getenv('MACULA_WHITELIST_S3_PATH', 'whitelist/domain_pivot/top_25000_domains.csv')
# MACULA_WHITELIST_DEST_PATH = os.path.join(MACULA_RESOURCE, 'domain_whitelist.csv')
# MACULA_WHITELIST_CRON_STR = os.getenv('MACULA_WHITELIST_CRON_STR', '0 6,18 * * *')


# # Feeds for Macula rule 
# ENABLE_MACULA_FEEDS_RULE = int(os.getenv('ENABLE_MACULA_FEEDS_RULE', 1))
# MACULA_FEEDS_NAME = "feed_list"
# MACULA_FEEDS_BUCKET = os.getenv('MACULA_FEEDS_BUCKET', 'ts-labs')
# MACULA_FEEDS_S3_PATH = os.getenv('MACULA_FEEDS_S3_PATH', 'feeds-rule/feeds-rule.csv')
# MACULA_FEEDS_DEST_PATH = os.path.join(MACULA_RESOURCE, 'feeds-rule.csv')
# MACULA_FEEDS_CRON_STR = os.getenv('MACULA_FEEDS_CRON_STR', '0 6,18 * * *')

#Macula darklist
ENABLE_MACULA_DARKLIST_RULE = int(os.getenv('ENABLE_MACULA_FEEDS_RULE', 1))
MACULA_DARKLIST_NAME = "dark_list"
MACULA_DARKLIST_BUCKET = os.getenv('MACULA_DARK_BUCKET', 'ts-labs')
MACULA_DARKLIST_S3_PATH = os.getenv('MACULA_DARK_S3_PATH', 'greylists/global_greylist_detail.csv')
MACULA_DARKLIST_DEST_PATH = os.path.join(MACULA_RESOURCE, 'greylist.csv')
MACULA_DARKLIST_CRON_STR = os.getenv('MACULA_DARKLIST_CRON_STR', '0 6,18 * * *')


# models info
# TO DO: update these to s3 paths once models are built regularly
# MODEL_NAME = 'macula-model-{}.mll'
# S3_MODELS_PATH = 'tmp/macula/{}/latest/'#"macula-model/{}/latest/"
# S3_ARCHIVE_PATH = 'tmp/macula/{}/archive/'#"macula-model/{}/archive/"
# AUXILIARY_FILES = ["trainingset-{}.csv.gz", "transformed-{}.jsonl", 'raw-features-{}.jsonl', MODEL_NAME]
# DATE_FORMAT = '%Y-%m-%d'
# MACULA_MODEL_BUCKET = os.getenv('MACULA_MODEL_BUCKET', 'ts-labs')
# MACULA_DOMAIN_MODEL_CRON_STR = os.getenv('MACULA_DOMAIN_MODEL_CRON_STR', '30 15 * * 1,4')
# MACULA_IP_MODEL_CRON_STR = os.getenv('MACULA_IP_MODEL_CRON_STR', '30 15 * * 1,4')
# VERIFY = False
# ARCHIVE = int(os.getenv('MACULA_MODEL_ARCHIVE', 0))

# for bitdefender rule
ENABLE_BITDEFENDER_RULE = int(os.getenv('ENABLE_BITDEFENDER_RULE', 1))
BITDEFENDER_AFTERMIN = float(os.getenv('BITDEFENDER_AFTERMIN', 0.4))


# Grey list info 
MACULA_GREYLIST_ENABLE = int(os.getenv("MACULA_GREYLIST_ENABLE", 1))
GREY_LIST_NAME = "grey_list"
GREY_LIST_BUCKET = os.getenv('GREY_LIST_BUCKET', 'ts-ds')
GREY_LIST_S3_PATH = os.getenv('GREY_LIST_S3_PATH', 'greylist/domain/domain_greylist.csv')
GREY_LIST_DEST_PATH = os.path.join(MACULA_RESOURCE, 'grey_list.csv')
GREY_LIST_CRON_STR = os.getenv('GREY_LIST_CRON_STR', '0 6,18 * * *')
MACULA_GREYLIST_RETURN_VALUE = {
    'benign': 0.9,
    'malicious': 0.1,
    'rescaled': 10,
}


#Whitelist
ALL_WL_NAME = "all_whitelist"
MACULA_WL_ENABLE = int(os.getenv("MACULA_WL_ENABLE", 1))
ALL_WL_BUCKET = os.getenv('ALL_WL_DOMAINS_BUCKET', 'ts-labs')
ALL_WL_S3_PATH = os.getenv('ALL_WL_DOMAINS_S3_PATH', 'all_macula_wl.csv')
ALL_WL_DEST_PATH = os.path.join(MACULA_RESOURCE, 'all_macula_wl.csv')
ALL_WL_CRON_STR = os.getenv('ALL_WL_DOMAINS_CRON_STR', '0 6,18 * * *')
MACULA_WL_RETURN_VALUE =  {
    'benign': 1.0,
    'malicious': 0.0,
    'rescaled': 0.0,
    'meta': {
        'type': 'url',
        'success': True,
        "source": "whitelist",
        'explanation': "URL matches whitelist."
    }
}

# Regex for URL extraction
_USER_INFO_RE = r'(?:[-a-z0-9._~%!$&\'()*+,;=:]+@)?'

_HOSTNAME_RE = (
    r'[a-z0-9]'                 # Start with an ALPHA or DIGIT
    r'(?:'                      # Start of subgroup
    r'[-a-z0-9_]{0,61}'             # 0 to 61 chars of ALPHA or DIGIT or HYPHEN or UNDERSCORE
    r'[a-z0-9]'                     # Ends with ALPHA or DIGIT
    r')?'                       # End of subgroup, zero or one of previous subgroup
)
_DOMAIN_RE = (
    r'(?:'                      # Start of subgroup
    r'\.'                           # Starts with a dot
    r'(?![-_])'                     # Can't start with a HYPHEN or UNDERSCORE
    r'[-a-z0-9_]{1,63}'             # 1 to 63 char of ALPHA or DIGIT or HYPHEN or UNDERSCORE
    r'(?<![-_])'                    # Can't end with a HYPHEN or UNDERSCORE
    r')*'                       # End of subgroup, any number of previous subgroups
)
_TLD_RE = (
    r'\.'                       # Starts with a dot
    r'(?!-)'                    # Can't start with a dash
    r'(?:'                      # Start of subgroup
    r'[-a-z]{2,63}'                 # 2 to 63 chars of ALPHA or HYPHEN
    r'|xn--[a-z0-9]{1,59}'          # Or punycode label
    r')'                        # End of subgroup
    r'(?<!-)'                   # Can't end with a dash
    r'\.?'                      # May have a trailing dot
)
_IPV4_RE = (
    r'(?:25[0-5]|2[0-4]\d|[0-1]?\d?\d)'     # Digit between 0-255
    r'(?:'                                  # Start of subgroup
    r'\.'                                       # Starts with a dot
    r'(?:25[0-5]|2[0-4]\d|[0-1]?\d?\d)'         # Digit between 0-255
    r'){3}'                                 # End of subgroup, exactly 3 of previous subgroup
)
_IPV6_RE = r'\[[a-f0-9:.]+\]'  # ipv6 regex, simplified as validated later with django.utils.ipv6.is_valid_ipv6_address

VALID_URL_PATTERN = re.compile(
    r'^' + _USER_INFO_RE + r''                              # Start and optional userinfo
    r'(?:'                                                  # Start of subgroup
    r'(?:' + _HOSTNAME_RE + _DOMAIN_RE + _TLD_RE + r')'     # host
    r'|localhost|' + _IPV4_RE + r'|' + _IPV6_RE + r''       # localhost or ipv4 or ipv6
    r')'                                                    # End of subgroup
    r'(?::\d+)?'                                            # optional port
    r'$', re.IGNORECASE                                     # End of line and ignore case
)

URI_SCHEMES = set([
    'aaa',
    'aaas',
    'about',
    'acap',
    'acct',
    'adiumxtra',
    'afp',
    'afs',
    'aim',
    'apt',
    'attachment',
    'aw',
    'barion',
    'beshare',
    'bitcoin',
    'bolo',
    'callto',
    'cap',
    'chrome',
    'chrome-extension',
    'cid',
    'coap',
    'coaps',
    'com-eventbrite-attendee',
    'content',
    'crid',
    'cvs',
    'data',
    'dav',
    'dict',
    'dlna-playcontainer',
    'dlna-playsingle',
    'dns',
    'dtn',
    'dvb',
    'ed2k',
    'facetime',
    'feed',
    'feedready',
    'file',
    'finger',
    'fish',
    'ftp',
    'geo',
    'gg',
    'git',
    'gizmoproject',
    'go',
    'gopher',
    'gtalk',
    'h323',
    'ham',
    'hcp',
    'http',
    'https',
    'iax',
    'icap',
    'icon',
    'im',
    'imap',
    'info',
    'ipn',
    'ipp',
    'irc',
    'irc6',
    'ircs',
    'iris',
    'iris.beep',
    'iris.lwz',
    'iris.xpc',
    'iris.xpcs',
    'itms',
    'jabber',
    'jar',
    'jms',
    'keyparc',
    'lastfm',
    'ldap',
    'ldaps',
    'magnet',
    'mailto',
    'maps',
    'market',
    'message',
    'mid',
    'mms',
    'ms-help',
    'ms-settings-power',
    'msnim',
    'msrp',
    'msrps',
    'mtqp',
    'mumble',
    'mupdate',
    'mvn',
    'news',
    'nfs',
    'ni',
    'nih',
    'nntp',
    'notes',
    'oid',
    'opaquelocktoken',
    'palm',
    'paparazzi',
    'pkcs11',
    'platform',
    'pop',
    'pres',
    'proxy',
    'psyc',
    'query',
    'reload',
    'res',
    'resource',
    'rmi',
    'rsync',
    'rtmfp',
    'rtmp',
    'rtsp',
    'rtsps',
    'rtspu',
    'secondlife',
    'service',
    'session',
    'sftp',
    'sgn',
    'shttp',
    'sieve',
    'sip',
    'sips',
    'skype',
    'smb',
    'sms',
    'smtp',
    'snmp',
    'soap.beep',
    'soap.beeps',
    'soldat',
    'spotify',
    'ssh',
    'steam',
    'stun',
    'stuns',
    'submit',
    'svn',
    'tag',
    'teamspeak',
    'tel',
    'teliaeid',
    'telnet',
    'tftp',
    'things',
    'thismessage',
    'tip',
    'tn3270',
    'turn',
    'turns',
    'tv',
    'udp',
    'unreal',
    'urn',
    'ut2004',
    'vemmi',
    'ventrilo',
    'view-source',
    'webcal',
    'ws',
    'wss',
    'wtai',
    'wyciwyg',
    'xcon',
    'xcon-userid',
    'xfire',
    'xmlrpc.beep',
    'xmlrpc.beeps',
    'xmpp',
    'xri',
    'ymsgr',
    'z39.50r',
    'z39.50s',
])
# end of regex
