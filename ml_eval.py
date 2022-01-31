from sklearn import cross_validation, metrics
import numpy as np
import matplotlib

matplotlib.use('Agg')
import pandas as pd
import csv
import json

from utils.telescope_client import TelescopeClient
from tornado import gen, ioloop
from tornado import httpclient

import time
import os
import sys
import getopt
import gc
import logging
from batcher import Batcher
import settings
from models.telescope_model import TelescopeFeatureTransform
from sklearn.feature_extraction import DictVectorizer

entropy = lambda p: -np.sum(p * np.log2(p)) if not 0 in p else 0
transformer = TelescopeFeatureTransform()

# to enable verbose debugging just set level=logging.DEBUG
logging.basicConfig(level=logging.CRITICAL, format='%(asctime)s - %(levelname)s - %(message)s')


# from http://nbviewer.ipython.org/github/fonnesbeck/Bios366/blob/master/notebooks/Section6_5-Decision-Trees.ipynb

def csv_row_to_feature_vector(rec, features_to_remove=None):
    if not features_to_remove:
        features_to_remove = []

    for col in rec.keys():
        if col not in ['value', 'label', 'ioc_type', 'source']:
            rec[col] = json.loads(rec[col])
        for name in features_to_remove:
            if name in col:
                del rec[col]
    # similulates that this record was returned from telescope
    df = pd.DataFrame.from_dict({rec['value']: rec}, orient='index')
    # note this feature vec does not contain these: 'value', 'label', 'ioc_type', 'source'
    # since it has been run through the feature transformer
    return transformer.transform(df)[0]


def transform_and_dump_features(filename, transformedfile, features_to_remove=None, fail_on_error=False):
    '''
    Transform the telescope features and dump them in the file
    '''
    csv.field_size_limit(sys.maxsize)
    rows = []
    labels = []
    count = 0
    errCount = 0
    values = set()
    wfile = open(transformedfile, 'w')
    with open(filename, 'r') as inf:
        reader = csv.DictReader(inf)
        for rec in reader:
            if rec['value'] in values:
                continue
            fVector = False
            if fail_on_error:
                fVector = csv_row_to_feature_vector(rec, features_to_remove)
            else:
                try:
                    # Features maybe malformed
                    fVector = csv_row_to_feature_vector(rec, features_to_remove)
                except Exception, e:
                    errCount += 1
                    print "Unable to load features for {}, with error - {}".format(rec['value'], e)

            if fVector:
                fVector['value'] = rec['value']
                fVector['label'] = rec['label']
                values.add(rec['value'])
                rows.append(fVector)
                labels.append(rec['label'])
                count += 1
                if count % 100 == 0:
                    print 'loaded {} records so far (gc: {})'.format(count, gc.collect())
                json.dump(fVector, wfile)
                wfile.write('\n')
                wfile.flush()
    wfile.close()
    return


def load_training_from_csv(filename, features_to_remove=None, fail_on_error=False):
    csv.field_size_limit(sys.maxsize)
    rows = []
    labels = []
    count = 0
    errCount = 0
    values = set()

    with open(filename, 'r') as inf:
        reader = csv.DictReader(inf)
        for rec in reader:
            if rec['value'] in values:
                continue
            fVector = False
            if fail_on_error:
                fVector = csv_row_to_feature_vector(rec, features_to_remove)
            else:
                try:
                    # Features maybe malformed
                    fVector = csv_row_to_feature_vector(rec, features_to_remove)
                except Exception, e:
                    errCount += 1
                    print "Unable to load features for {}, with error - {}".format(rec['value'], e)

            if fVector:
                values.add(rec['value'])
                rows.append(fVector)
                labels.append(rec['label'])
                count += 1
                if count % 100 == 0:
                    print 'loaded {} records so far (gc: {})'.format(count, gc.collect())

        print 'records failed: {}'.format(errCount)
        initial_time = time.time()
        dv = DictVectorizer().fit(rows)
        matrix = dv.transform(rows)
        features = pd.SparseDataFrame(
            [pd.SparseSeries(matrix[i].toarray().ravel()) for i in np.arange(matrix.shape[0])])
        print("Featurization took -------------------------------------------------> {}".format(
            time.time() - initial_time))
        return features, labels, dv


@gen.coroutine
def gather_features_to_csv(ips_file, path_to_store, use_cache=False):
    # fieldnames = ['value', 'label', 'ioc_type', 'source']
    # dataframe = pd.read_csv(ips_file, names=fieldnames, header=0)  # returns a dataframe
    dataframe = pd.read_csv(ips_file)  # returns a dataframe
    ips = list(dataframe['value'].values)
    if os.path.exists(path_to_store):
        os.remove(path_to_store)
    # Make sure to have telescope up and running locally or point to the staging url
    telescope = TelescopeClient(telescope_url=settings.TELESCOPE_URL, use_cache=use_cache)

    print "Before batch enrich"
    batchSize = 50
    batchFailures = 0
    failedIOCs = []
    columns = None
    for batch in Batcher(ips, batchSize):
        print "IOCs processed={}, batchFailures={}".format((batch.index - batchFailures) * batchSize, batchFailures)
        print "Enriching Batch ........"
        failures = 0
        success = False
        while failures < 5:
            try:
                enriched_dict = yield telescope.batch_enrich(list(batch))
                success = True
            except httpclient.HTTPError as e:
                failures += 1
                print "Telescope Client Returned HTTPError: '%s'" % str(e)
                print "retrying ......... (failures={})".format(failures)
                time.sleep(5)  # delays for 5 seconds
                continue
            break
        if not success:
            failedIOCs += list(batch)
            batchFailures += 1
        else:
            # Build DataFrame from telescope returned dictionary
            telescopeDf = pd.DataFrame.from_dict(enriched_dict, orient='index')
            # Store an ordered list of ips to map enrichments to ip,labels later
            orderedIps = list(telescopeDf.index)
            telescopeDf['value'] = orderedIps
            relevantDf = dataframe.loc[dataframe['value'].isin(list(batch))]
            csvDf = relevantDf.merge(telescopeDf, how='inner', on='value')

            for col in telescopeDf.columns:
                if col not in ['value', 'label', 'ioc_type', 'source']:
                    csvDf[col] = csvDf[col].apply(lambda s: json.dumps(s))

            if columns is None:
                columns = csvDf.columns

            if set(csvDf.columns) != set(columns):
                print 'WARNING: output columns ({}) diff from columns in record ({})'.format(csvDf.columns, columns)

            print "Converting to csv....."
            if not os.path.isfile(path_to_store):
                csvDf.to_csv(path_to_store, index=False, encoding='utf-8', columns=columns)
            else:  # else it exists so append without writing the header
                csvDf.to_csv(path_to_store, index=False, encoding='utf-8', columns=columns, mode='a', header=False)
    print 'Finished gathering features. batchFailures={}, failedIOCs={}'.format(batchFailures, failedIOCs)


@gen.coroutine
def main(argv):
    def usage():
        print '========================================================================================'
        print 'Usage: python {} [-c] -f <featuresFile> -t <trainingFile> -r <transformedfile> '.format(sys.argv[0])
        print '========================================================================================'
        print('Flags:')
        print(
            "    -f, --features-file <featuresFile> - Features file collected from telescope.  If this file does not exist, it will be created")
        print("    -t, --training-file <trainingFile> - Training set file (generated from Ophtmologist)")
        # print("    -S, --skip-eval                    - Do not output per-fold model stats")
        print("    -T, --testing-file <testinfile[,testingfile]  - testing file(s) comma seperated to test model on")
        print("    -r, --transformedfile              - File to write the transformed Telescope features")
        print("    -c, --use_cache        - The cache is enable if this is set'")
        print("    -h, --help                         - Print help menu")
        sys.exit(2)

    trainingFile = None
    featuresFile = None
    # changed default behavior to skip per-fold eval, if desired use -e and specify file to log this
    transfromedFile = None
    use_cache = False

    try:
        opts, args = getopt.getopt(argv, "hct:f:T:r:", \
                                   ['help', 'use_cache', 'training-file=', 'features-file=', 'testing-file=',
                                    'transformedfile='])
    except getopt.GetoptError:
        usage()

    for opt, arg in opts:
        if opt in ("-h", '--help'):
            usage()
        elif opt in ("-t", '--training-file'):
            trainingFile = arg
        elif opt in ("-f", '--features-file'):
            featuresFile = arg
        elif opt in ("-r", '--transformedfile'):
            transfromedFile = arg
        elif opt in ("-c", '--use_cache'):
            use_cache = True
        else:
            print("Input file doesn't exist!!")
            usage()

    if None in (trainingFile, featuresFile,):
        print("Missing command line option")
        usage()

    print '=================================================================='
    print 'Running Evaluation on Data'
    print '=================================================================='
    print 'Settings: trainingFile={}, featuresFile={} transformedfile={}'.format(trainingFile, featuresFile,
                                                                                 transfromedFile)

    print 'Gathering Features. This may take a while..........'
    yield gather_features_to_csv(trainingFile, featuresFile, use_cache)

    # Input file needs to be a labeled CSV with two columns 'ips' and 'label'
    features_to_remove = []

    'We collect the feature and exit. This part is only for calling Telescope and transforming the Telescope enrichments to the features'
    transform_and_dump_features(featuresFile, transfromedFile, features_to_remove, fail_on_error=False)


if __name__ == "__main__":
    ioloop.IOLoop.instance().run_sync(lambda: main(sys.argv[1:]))
