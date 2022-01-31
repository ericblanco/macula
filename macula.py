#!/usr/bin/env python
"""
Tornado app that will server the endpoints for Macula.  We'll fetch features using AsyncHTTPClients and feed the results through models.  Easy-peasy
"""
import settings
from models.manager import LoadModelFromS3, macula_model_scheduler
from tornado.ioloop import IOLoop
from tornado.web import RequestHandler, Application, url
from tornado import gen
from tornado import httpclient
from raven import Client
from pandas import DataFrame
from copy import deepcopy
from urlparse import urlparse
from utils.telescope_client import TelescopeClient
from utils.log_manager import LogsManager
from utils.tools import (
    TypeDetector, reformat_scores, type_identifier)
from utils.cache import get_cached_ioc_scores, get_uncached_ioc_scores, write_ioc_scores_to_cache
from utils.file_based_set import UploadFilesContainer
import momoko
import sys
import argparse
import logging
import re
import json
from settings import (
    ALL_WL_BUCKET, ALL_WL_CRON_STR, ALL_WL_DEST_PATH,
    ALL_WL_S3_PATH, ALL_WL_NAME, MACULA_S3_ACCESS_KEY,
    MACULA_DEBUG, MACULA_PORT, MACULA_DB_NAME, MACULA_DB_USER, MACULA_DB_PASSWORD,
    MACULA_DB_HOST, MACULA_DB_PORT, MACULA_SENTRY_URL, MACULA_S3_SECRET_KEY, MACULA_DOMAIN_PIVOT_TOP_NUM,GREY_LIST_NAME, GREY_LIST_BUCKET, GREY_LIST_S3_PATH, GREY_LIST_DEST_PATH,GREY_LIST_CRON_STR, MACULA_GREYLIST_ENABLE,
    MACULA_FEEDS_BUCKET, MACULA_FEEDS_S3_PATH, MACULA_FEEDS_DEST_PATH, MACULA_FEEDS_CRON_STR,MACULA_FEEDS_NAME,
    ENABLE_MACULA_DARKLIST_RULE, MACULA_DARKLIST_NAME, MACULA_DARKLIST_BUCKET, MACULA_DARKLIST_S3_PATH, MACULA_DARKLIST_DEST_PATH, MACULA_DARKLIST_CRON_STR
    )

 


logger = logging.getLogger(__name__)
logging_level = logging.DEBUG if MACULA_DEBUG else logging.INFO
logger.setLevel(logging_level)
typer = TypeDetector()
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging_level)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

sentry = Client(MACULA_SENTRY_URL)
upload_file_container = UploadFilesContainer()
log_manager = LogsManager()



from models.manager import score_mixed_indicators
from models.explainer import apply_thelist
class MaculaRequestHandler(RequestHandler):

    @property
    def db(self):
        return self.application.db

    @property
    def black_list(self):
        bl_obj = upload_file_container.get("ip_blacklist")
        return dict() if not bl_obj else bl_obj

    @property
    def grey_list(self):
        grey_obj = upload_file_container.get("grey_list")
        return dict() if not grey_obj else grey_obj
    
    @property
    def feeds_list(self):
        feeds_obj = upload_file_container.get(MACULA_FEEDS_NAME)
        return dict() if not feeds_obj else feeds_obj
    
    @property
    def dm_blklst(self):
        dm_blklst = upload_file_container.get("dm_blacklist")
        return dict() if not dm_blklst else dm_blklst
    @property
    def darklist(self):
        darklist = upload_file_container.get(MACULA_DARKLIST_NAME)
        return dict() if not darklist else darklist
    @property
    def all_whitelist(self):
        # load all wl domains into memory from remote resources
        all_whitelist = upload_file_container.get(ALL_WL_NAME)
        return dict() if not all_whitelist else all_whitelist


    def clean_reverse_dns_record(self, host):
        rDnsIpv4Tld = ".in-addr.arpa"
        if rDnsIpv4Tld in host:
            ipv4 = '.'.join(list(reversed(host.split(rDnsIpv4Tld)[0].split("."))))
            return ipv4
        else:
            # TO DO: Also do for IPV6
            return host


    def clean_ioc(self, host):
        host = host.lower().strip()
        # Get rid of everything after first slash
        url_to_host = re.sub(r'(?:http.?://)?([^/:]*).*', r'\1', host)
        # Get rid of invalid chars
        invalid_removed = re.sub(r'[^.a-zA-Z0-9\-]+', '',  url_to_host)
        # Get rid of trailing periods
        trailing_period_removed = re.sub(r'\.+$', '',  invalid_removed)
        # Extract IP from reverse dns host
        reverse_dns_record_cleaned = self.clean_reverse_dns_record(trailing_period_removed)

        return reverse_dns_record_cleaned

    def normalize_iocs(self, iocs):
        return [(ioc, self.clean_ioc(ioc)) for ioc in iocs]

    def remap_scores(self, scores, ioc_mapping):
        result = {}
        for original, normalized in ioc_mapping:
            result[original] = scores[normalized]
        return result

    def strip_explain_data(self, scores):
        if self.explain:
            for ioc, score in scores.iteritems():
                try:
                    del scores[ioc]['meta']['explanation']
                except Exception as e:
                    logger.warn('Error while processing IOC {}: {}'.format(ioc, e))
                    pass
        # Delete the summary for the cache
        if self.summary:
            for ioc, score in scores.iteritems():
                try:
                    del scores[ioc]['meta']['summary']
                except Exception as e:
                    logger.warn('Error while processing IOC {}: {}'.format(ioc, e))
                    pass
        return scores

    def score_iocs(self, enriched_df, explain=False, explain_items=10, domain_pivot=MACULA_DOMAIN_PIVOT_TOP_NUM, summary=False, rule=True):
        return score_mixed_indicators(enriched_df, explain, explain_items, domain_pivot, summary,rule)

    @gen.coroutine
    def get_enriched_data(self, iocs):
        telescope = TelescopeClient(None, self.use_cache)

        try:
            enriched_dict = yield telescope.batch_enrich(iocs)
        except httpclient.HTTPError as e:
            raise Exception("Telescope Client Returned HTTPError: '%s'" % str(e))

        raise gen.Return(DataFrame.from_dict(enriched_dict, orient='index'))

    @gen.coroutine
    def process_generic_iocs(self, iocs=list):

        # Don't pull cache records when using "explain" mode
        if self.explain or self.summary:
            self.use_cache = False

        allscores = {}
        cached_ioc_scores = {}

        # Whitelist Handling
        # Before normalisation, find iocs with whitelist match and assign static score to them.
        # WL score will NOT be added to cache, but it needs to be added to result for displaying.
        # Currently, only url type is checked for wl.


        # Check whitelists
        ioc_mapping = self.normalize_iocs(iocs)
        raw_iocs = [x[0] for x in ioc_mapping]
        normalized_iocs = [x[1] for x in ioc_mapping]

        wl_iocs = []
        non_wl_iocs = iocs
        wl_score = {}
        if self.use_whitelist and settings.MACULA_WL_ENABLE:
            wl_score = apply_thelist(normalized_iocs, ALL_WL_NAME)
            wl_iocs = [ioc for ioc in wl_score]
            normalized_iocs = [ioc for ioc in normalized_iocs if ioc not in wl_iocs]
            log_manager.integer_add(c_type=ALL_WL_NAME,
                                    total=len(normalized_iocs) + len(wl_iocs),
                                    in_whitelist=len(wl_iocs))
        if len(wl_iocs): logger.debug("Whitelisted iocs: {}".format(','.join(wl_iocs)))

        # Return early if no valid indicators were supplied
        if not normalized_iocs:
            result = self.remap_scores(wl_score, ioc_mapping)
            # append whitelist result - no ioc remapping needed
            raise gen.Return(result)

        allscores.update(wl_score)

        #Grey list handling
        normalized_iocs_grey, normalized_iocs_grey_score = [], {}
        if self.use_greylist and settings.MACULA_GREYLIST_ENABLE:
            normalized_iocs_grey, normalized_iocs = self.grey_list.check_in(normalized_iocs)
            normalized_iocs_grey_score = {ioc: 
            {
                'benign': settings.MACULA_GREYLIST_RETURN_VALUE['benign'],
                'malicious': settings.MACULA_GREYLIST_RETURN_VALUE['malicious'],
                'rescaled': settings.MACULA_GREYLIST_RETURN_VALUE['rescaled'],
                'meta': {
                    'type': '{}',
                    'success': True,
                    'source': 'grey_list',
                    'explanation': "{} is in our grey list.",
                    'summary':"{} is in the Greylist."
                }
            } for ioc in normalized_iocs_grey}
            
            ioc_types = {k:type_identifier(k) for k in normalized_iocs_grey}
            for k,v in normalized_iocs_grey_score.items():
                itype, message = ioc_types[k]
                #if unknown type
                if message != None:
                    normalized_iocs_grey_score[k] = {'meta':{
                            'type': itype,
                            'success': False,
                            'message': 'Invalid IOC'
                            }
                        }
                else:
                    normalized_iocs_grey_score[k]['meta']['type'] = itype
                    normalized_iocs_grey_score[k]['meta']['explanation'] = normalized_iocs_grey_score[k]['meta']['explanation'].format(itype)
                    normalized_iocs_grey_score[k]['meta']['summary'] = normalized_iocs_grey_score[k]['meta']['summary'].format(itype)
                    
            log_manager.integer_add(c_type="grey_list",
                                    total=len(normalized_iocs) + len(normalized_iocs_grey),
                                    in_greylist=len(normalized_iocs_grey),)


        # Blacklists Handling
        # BL score will NOT be added to cache, but need to be added to result for displaying.
        normalized_iocs_ip_bl, normalized_iocs_ip_bl_score = [], {}
        if self.use_blacklist and settings.MACULA_IP_BLACKLIST_ENABLE:
            normalized_iocs_ip_bl_score = apply_thelist(normalized_iocs,'ip_blacklist')
            normalized_iocs_ip_bl = [ioc for ioc in normalized_iocs_ip_bl_score]
            normalized_iocs = [ioc for ioc in normalized_iocs if ioc not in normalized_iocs_ip_bl_score]
            log_manager.integer_add(c_type="ip_blacklist",
                                    total=len(normalized_iocs) + len(normalized_iocs_ip_bl),
                                    in_blacklist=len(normalized_iocs_ip_bl))
        
        # check domain blacklist
        normalized_iocs_dm_bl, normalized_iocs_dm_bl_score = [], {}
        if self.use_blacklist and settings.MACULA_DM_BLACKLIST_ENABLE:
            normalized_iocs_dm_bl_score = apply_thelist(normalized_iocs, 'dm_blacklist')
            normalized_iocs_dm_bl = [ioc for ioc in normalized_iocs_dm_bl_score]
            normalized_iocs = [ioc for ioc in normalized_iocs if ioc not in normalized_iocs_dm_bl_score]
            log_manager.integer_add(c_type="dm_blklst",
                                    total=len(normalized_iocs) + len(normalized_iocs_dm_bl),
                                    in_blklst=len(normalized_iocs_dm_bl))

        # merge domain and ip blacklists & scores
        normalized_iocs_bl = normalized_iocs_ip_bl + normalized_iocs_dm_bl + normalized_iocs_grey
        normalized_iocs_bl_score = normalized_iocs_ip_bl_score
        normalized_iocs_bl_score.update(normalized_iocs_dm_bl_score)
        normalized_iocs_bl_score.update(normalized_iocs_grey_score)
        if len(normalized_iocs_bl): logger.debug("Blacklisted iocs: {}".format(','.join(normalized_iocs_bl)))

        # Return early if no valid indicators were supplied
        #score dict has already been updated by wl scores, now we need to update it with bl scores
        allscores.update(normalized_iocs_bl_score)
        if not normalized_iocs:
            result = self.remap_scores(allscores, ioc_mapping)
            # append whitelist result - no ioc remapping needed
            raise gen.Return(result)

        # check cache records only when use_cache is on & there are normalized_iocs to be scored
        if self.use_cache:
            cached_ioc_scores = yield get_cached_ioc_scores(all_iocs=normalized_iocs, db=self.db)
            # drop all failed items when retriving from existing cache, if rescore succeed, cache will be updated
            cached_ioc_scores = {k:v for k,v in cached_ioc_scores.items() if v.get('meta', {}).get('success', False)}
            log_manager.integer_add(c_type="cache_ioc", total=len(normalized_iocs), cached=len(cached_ioc_scores.keys()))
            if len(cached_ioc_scores): logger.debug(
                "Cache scored iocs: {}".format(','.join(list(cached_ioc_scores.keys()))))
            # Return early if every requested indicator was found in the cache
            if len(normalized_iocs) == len(cached_ioc_scores.keys()):
                cackedscores = self.augment_meta_and_rescale_scores(normalized_iocs, cached_ioc_scores)
                # append score from Blacklist
                allscores.update(cackedscores)
                result = self.remap_scores(allscores, ioc_mapping)
                # append result from Whitelist, no ioc remapping is needed
                raise gen.Return(result)
            else:
                # Determine iocs that don't have cached data
                uncached_ioc_scores = get_uncached_ioc_scores(all_iocs=normalized_iocs,
                                                              cached_ioc_scores=cached_ioc_scores)
                # Look up scores for iocs that don't have cached data
                enriched_df = yield self.get_enriched_data(uncached_ioc_scores)
        else:
            enriched_df = yield self.get_enriched_data(normalized_iocs)

        # Get final scores based on enrichments
        scores = {}
        if len(enriched_df.keys()) > 0:
            scores = self.score_iocs(enriched_df, self.explain, self.explain_items, self.domain_pivot, self.summary, self.rule)
        if len(scores): logger.debug(
            "ML scored iocs: {}".format(','.join(list(scores.keys()))))

        # Merge cached and uncached ioc scores
        if len(cached_ioc_scores) > 0:
            scores.update(cached_ioc_scores)

        # Augment ioc metadata and rescale
        scores = self.augment_meta_and_rescale_scores(normalized_iocs, scores)
        allscores.update(scores)
        # scores = applyoverride(scores,enriched_df,original)
        scores_to_cache = deepcopy(scores)

        # Strip explain data prior to caching
        if self.explain or self.summary:
            scores_to_cache = self.strip_explain_data(scores_to_cache)
        # drop all failed items before caching
        scores_to_cache = {k:v for k,v in scores_to_cache.items() if v.get('meta', {}).get('success', False)}

        # Always write to cache. Duplicates of existing records are ignored.
        # Using spawn_callback allows for 'fire and forget'
        IOLoop.current().spawn_callback(
            write_ioc_scores_to_cache,
            scores=scores_to_cache,
            already_cached_ioc_scores=cached_ioc_scores,
            db=self.db
        )

        result = self.remap_scores(allscores, ioc_mapping)
        raise gen.Return(result)

    def augment_meta_and_rescale_scores(self, iocs, scores):
        return reformat_scores(iocs=iocs, scores=scores)


class ScoreIPsHandler(MaculaRequestHandler):
    @gen.coroutine
    def get(self):
        """
        Must return results in the form:
        dummy_result = {
            "1.1.1.1": {
                "Benign": 0.0,
                "Malicious": 0.8
            }
        }
        """
        iocs  = self.get_argument('ips').split(',')
        self.explain = self.get_argument('explain', default='False')
        self.explain = True if self.explain.lower() in ['true', 't'] else False
        self.explain_items = self.get_argument('explain_items', default='10')
        self.explain_items = int(self.explain_items) if self.explain_items.isdigit() else 10
        self.use_cache = self.get_argument('useCache', default='True')
        self.use_cache = False if self.use_cache.lower() in ['false', 'f'] else True

        try:
            scores = yield self.process_generic_iocs(iocs)
            self.write(scores)
        except Exception, e:
            sentry.captureException()
            logger.exception('Error processing IOCs:{}'.format(self.get_argument('ips')))
            self.set_status(414)
            self.write({
                    "Error while processing IOC's": str(e)
                })

class ScoreDomainsHandler(MaculaRequestHandler):
    @gen.coroutine
    def get(self):
        """
        Must return results in the form:
        dummy_result = {
            "1.1.1.1": {
                "Benign": 0.0,
                "Malicious": 0.8
            }
        }
        """
        iocs = self.get_argument('domains').split(',')
        self.explain = self.get_argument('explain', default='False')
        self.explain = True if self.explain.lower() in ['true', 't'] else False
        self.explain_items = self.get_argument('explain_items', default='10')
        self.explain_items = int(self.explain_items) if self.explain_items.isdigit() else 10
        self.use_cache = self.get_argument('useCache', default='True')
        self.use_cache = False if self.use_cache.lower() in ['false', 'f'] else True

        try:
            scores = yield self.process_generic_iocs(iocs)
            self.write(scores)
        except Exception, e:
            sentry.captureException()
            logger.exception('Error processing IOCs:{}'.format(self.get_argument('domains')))
            self.set_status(414)
            self.write({
                    "Error while processing IOC's": str(e)
                })

class ScoreHandler(MaculaRequestHandler):
    @gen.coroutine
    def get(self):
        """
        Must return results in the form:
        dummy_result = {
            "1.1.1.1": {
                "Benign": 0.0,
                "Malicious": 0.8
            }
        }
        """
        iocs = self.get_argument('indicators').split(',')
        self.explain = self.get_argument('explain', default='False')
        self.explain = True if self.explain.lower() in ['true', 't'] else False
        self.explain_items = self.get_argument('explain_items', default='10')
        self.explain_items = int(self.explain_items) if self.explain_items.isdigit() else 10
        self.use_cache = self.get_argument('useCache', default='True')
        self.use_cache = False if self.use_cache.lower() in ['false', 'f'] else True
        # parameter to control if whitelist should be used for URL evaluation. Default to True
        self.use_whitelist = self.get_argument('useWhitelist', default='True')
        self.use_whitelist = False if self.use_whitelist.lower() in ['false', 'f'] else True
        self.use_blacklist = self.get_argument('useBlacklist', default='True')
        self.use_blacklist = False if self.use_blacklist.lower() in ['false', 'f'] else True
        self.domain_pivot = self.get_argument('domain_pivot', default=str(MACULA_DOMAIN_PIVOT_TOP_NUM))
        self.domain_pivot = int(self.domain_pivot) if self.domain_pivot.isdigit() else MACULA_DOMAIN_PIVOT_TOP_NUM
        self.use_greylist = self.get_argument('useGreylist', default='True')
        self.use_greylist = False if self.use_greylist.lower() in ['false', 'f'] else True
        self.summary = self.get_argument('summary', default='False')
        self.summary = True if self.summary.lower() in ['true', 't'] else False  
        self.rule = self.get_argument('useRule', default='True')
        self.rule = True if self.rule.lower() in ['true', 't'] else False  
        try:
            scores = yield self.process_generic_iocs(iocs)
            self.write(scores)
        except Exception, e:
            sentry.captureException()
            logger.exception('Error processing IOCs:{}'.format(self.get_argument('indicators')))
            self.set_status(414)
            self.write({
                    "Error while processing IOC's": str(e)
                })
    @gen.coroutine
    def post(self):
        """
        Must return results in the form:
        dummy_result = {
            "1.1.1.1": {
                "Benign": 0.0,
                "Malicious": 0.8
            }
        }
        """
        data = json.loads(self.request.body)

        iocs = data.get('indicators').split(',')
        self.explain = data.get('explain', False)
        self.explain_items = data.get('explain_items', 10)
        self.use_cache = data.get('useCache', True)
        # parameter to control if whitelist should be used for URL evaluation. Default to True
        self.use_whitelist = data.get('useWhitelist', True)
        self.use_blacklist = data.get('useBlacklist', True)
        self.domain_pivot = data.get('domain_pivot', MACULA_DOMAIN_PIVOT_TOP_NUM)
        self.use_greylist = data.get('useGreylist', True)
        self.summary = data.get('summary', False)
        self.rule = data.get('useRule', True)
        try:
            scores = yield self.process_generic_iocs(iocs)
            self.write(scores)
        except Exception, e:
            sentry.captureException()
            logger.exception('Error processing IOCs:{}'.format(data.get('indicators')))
            self.set_status(414)
            self.write({
                    "Error while processing IOC's": str(e)
                })


class ShipBuilderStatusHandler(MaculaRequestHandler):
    @gen.coroutine
    def get(self):
        self.write({'status': 'ok'})


def make_app(debug=False):
    app = Application([
            # Endpoints for scoring indicators based on features from Telescope enrichment
            url(r"/", ShipBuilderStatusHandler),
            url(r"/api/score", ScoreHandler),
            url(r"/api/score_ips", ScoreIPsHandler),
            url(r"/api/score_domains", ScoreDomainsHandler),

            # Actual use case for previous Features endpoint:
            #   "Why was this indicator scored like it was?"
            #   -> create a better response to this using the ML model
            #   -> More Like This functionality would be useful too

            ],
            debug=debug
        )
    return app


def start_static_check_list():
    """
    load static check list from external resource
    like: local, s3
    :return:
    """
    def load(name, **config):
        """
        try to get this obj,
        if not exist, load it,
        if still fail, return empty set
        :param name:
        :param config:
        :return:
        """
        obj = upload_file_container.get(name)
        if not obj:
            if config.get("load_type") == "s3":
                upload_file_container.load(load_type="s3",
                                           name=name,
                                           multi_entry=config.get("multi_entry",False),
                                           bucket=config.get("bucket"),
                                           s3_path=config.get("s3_path"),
                                           saved_path=config.get("saved_path"),
                                           secret_key=config.get("secret_key"),
                                           access_key=config.get("access_key"),
                                           cron_str=config.get("cron_str"))

            obj = upload_file_container.get(name)
            if not obj:
                upload_file_container.set(name, set())         
                
    load(name="domain_whitelist",
         load_type="s3",
         bucket=settings.MACULA_WHITELIST_BUCKET,
         s3_path=settings.MACULA_WHITELIST_S3_PATH,
         saved_path=settings.MACULA_WHITELIST_DEST_PATH,
         secret_key=settings.MACULA_S3_SECRET_KEY,
         access_key=settings.MACULA_S3_ACCESS_KEY,
         cron_str=settings.MACULA_WHITELIST_CRON_STR)

    load(name="ip_blacklist",
         load_type="s3",
         bucket=settings.MACULA_IP_BLACKLIST_BUCKET,
         s3_path=settings.MACULA_IP_BLACKLIST_S3_PATH,
         saved_path=settings.MACULA_IP_BLACKLIST_DEST_PATH,
         secret_key=settings.MACULA_S3_SECRET_KEY,
         access_key=settings.MACULA_S3_ACCESS_KEY,
         cron_str=settings.MACULA_IP_BLACKLIST_CRON_STR,)

    load(name="dm_blacklist",
        load_type="s3",
        bucket=settings.MACULA_DM_BLACKLIST_BUCKET,
        s3_path=settings.MACULA_DM_BLACKLIST_S3_PATH,
        saved_path=settings.MACULA_DM_BLACKLIST_DEST_PATH,
        secret_key=settings.MACULA_S3_SECRET_KEY,
        access_key=settings.MACULA_S3_ACCESS_KEY,
        cron_str=settings.MACULA_DM_BLACKLIST_CRON_STR,)

    load(name=ALL_WL_NAME,
         load_type="s3",
         bucket=ALL_WL_BUCKET,
         s3_path=ALL_WL_S3_PATH,
         saved_path=ALL_WL_DEST_PATH,
         secret_key=MACULA_S3_SECRET_KEY,
         access_key=MACULA_S3_ACCESS_KEY,
         cron_str=ALL_WL_CRON_STR, )

    load(name=MACULA_FEEDS_NAME,
         load_type="s3",
         bucket=MACULA_FEEDS_BUCKET,
         s3_path=MACULA_FEEDS_S3_PATH,
         saved_path=MACULA_FEEDS_DEST_PATH,
         secret_key=MACULA_S3_SECRET_KEY,
         access_key=MACULA_S3_ACCESS_KEY,
         cron_str=MACULA_FEEDS_CRON_STR, )    

    load(name=GREY_LIST_NAME,
         load_type="s3",
         bucket=GREY_LIST_BUCKET,
         s3_path=GREY_LIST_S3_PATH,
         saved_path=GREY_LIST_DEST_PATH,
         secret_key=MACULA_S3_SECRET_KEY,
         access_key=MACULA_S3_ACCESS_KEY,
         cron_str=GREY_LIST_CRON_STR, )

    load(name=MACULA_DARKLIST_NAME,
         load_type="s3",
         bucket=MACULA_DARKLIST_BUCKET,
         s3_path=MACULA_DARKLIST_S3_PATH,
         saved_path=MACULA_DARKLIST_DEST_PATH,
         secret_key=MACULA_S3_SECRET_KEY,
         access_key=MACULA_S3_ACCESS_KEY,
         cron_str=MACULA_DARKLIST_CRON_STR, )
def start_server(port, debug):
    #Load the models and schedule cron job to load them frequently
    LoadModelFromS3('ip')
    LoadModelFromS3('domain')
    macula_model_scheduler()
    start_static_check_list()
    app = make_app(debug)
    ioloop = IOLoop.instance()

    app.db = momoko.Pool(
        dsn='dbname={} user={} password={} host={} port={}'.format(
            MACULA_DB_NAME, MACULA_DB_USER, MACULA_DB_PASSWORD, MACULA_DB_HOST, MACULA_DB_PORT
        ),
        size=10,
        ioloop=ioloop,
    )

    # this is one way to run ioloop in sync
    future = app.db.connect()
    ioloop.add_future(future, lambda f: ioloop.stop())
    ioloop.start()

    app.listen(port)
    ioloop.start()
    return app

def parse_args(args):
    """
    Usage:
        Run the server:
            run.py runserver --config server-config.json

        Train a new model:
            run.py train input.csv new_model.model       # where input.csv has labeled header of 'value', 'label', (optional 'type' if --type not specified)
                                                            # and 'features' may be added to skip resolution with json feature dictionaries (output from 'run.py resolve')
        Resolve features without training:
            run.py resolve input.csv > output.csv   # where input.csv has labeled header of 'value', 'label'

    """

    def runserver(args):
        port = MACULA_PORT
        debug = MACULA_DEBUG
        start_server(port, debug)

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    parser_runserver = subparsers.add_parser('runserver', help='Run the Macula server.')
    parser_runserver.set_defaults(func=runserver)

    return parser.parse_args(args)

def process_cmdline(args):
    parser = parse_args(args)
    parser.func(parser)


if __name__ == '__main__':
    process_cmdline(sys.argv[1:])
