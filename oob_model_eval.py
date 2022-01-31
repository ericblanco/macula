import numpy as np
import pandas as pd
import csv
import json
import gc
from collections import OrderedDict

from tornado import gen, ioloop

import os
import sys
import getopt
import logging
from datetime import datetime

from models.telescope_model import TelescopeClassifier
import ml_eval

#to enable verbose debugging just set level=logging.DEBUG
logging.basicConfig(level=logging.CRITICAL, format='%(asctime)s - %(levelname)s - %(message)s')

def eval_model_oob(train, target, model_file, title="", oob_eval_file=None):  
    """
    Compute OOB metrics for the given model and save to oob_eval_file
    """

    translate = {'Benign': 0, 'Malicious': 1,'benign':0, 'malicious': 1}
    target = np.array([translate[name] for name in target])

    print 'Loading model ..........'
    clf = TelescopeClassifier.load(model_file)
    print 'Classifying ..........'
    predictions = clf.predict(train)
    predictions = np.array([translate[name] for name in predictions])
    expected = target


    print 'Generating report ........'
    original = sys.stdout
    if oob_eval_file:
        print('Saving report to file ...... {}'.format(oob_eval_file))
        sys.stdout = open(oob_eval_file, 'w')
    
    ml_eval.print_report(title, expected, predictions)
    sys.stdout = original

def csv_row_to_feature_vector(rec):
    for col in rec.keys():
        if col not in ['value', 'label', 'ioc_type', 'source']:
            rec[col] = json.loads(rec[col])
    dictRow = {rec['value']: rec}
    return dictRow


def load_training_from_csv(filename):
    csv.field_size_limit(sys.maxsize)
    labelsDict = {}
    count = 0
    errCount = 0
    rows = OrderedDict()
    values = set()

    with open(filename, 'r') as inf:
        reader = csv.DictReader(inf)
        for rec in reader:
            if rec['value'] in values:
                continue
            fVector = False    
            try:
                # Features maybe malformed
                fVector = csv_row_to_feature_vector(rec)
            except Exception, e:
                errCount += 1
                print "Unable to load features for {}, with error - {}".format(rec['value'], e)    

            if fVector:    
                values.add(rec['value'])
                rows.update(fVector)
                labelsDict.update({rec['value']:rec['label']})
                count += 1
                if count % 100 == 0:
                    print 'loaded {} records so far (gc: {})'.format(count, gc.collect())

        features = pd.DataFrame.from_dict(rows, orient='index')
        labels = [labelsDict[ioc] for ioc in features.index]

        return features, labels

@gen.coroutine
def main(argv):
    def usage():
        print '========================================================================================'
        print 'Usage:  python {} [-c] -o <oobFile> -m <modelFile> -f <oobFeaturesFile> [-e <oobEvalFile.csv>]'.format(sys.argv[0])
        print '========================================================================================'
        print('Flags:')
        print("    -c, --use-cache                    - use cache file")
        print("    -o, --oob-file                     - Out-of-bag test csv file")
        print("    -f, --oob-features-file            - OOB features csv file")
        print("    -m, --model-file                   - model to test file")
        print("    -e, --oob-eval-file                - write OOB test metrics tp specified csv file")
        print("    -h, --help                         - Print help menu")
        sys.exit(2)

    use_cache = False
    oobFile = None
    oobFeaturesFile = None
    oobEvalFile = None
    oobModelFile = None
    try:
        opts, args = getopt.getopt(argv, "ch:o:f:m:e:",\
        ['help', 'use-cache', 'oob-file=', 'oob-features-file=' 'model-file=','oob-eval-file='])
    except getopt.GetoptError:
        usage()

    def checkFileExist(path):
        if not os.path.exists(path):
            print("{} does not exist!".format(path))
            usage()

    for opt, arg in opts:
        if opt in ("-h", '--help'):
            usage()
        elif opt in ("-f", '--oob-features-file'):
            oobFeaturesFile = arg
        elif opt in ("-c", '--use-cache'):
            use_cache = True
        elif opt in ("-o", '--oob-file'):
            oobFile = arg
            checkFileExist(oobFile)
        elif opt in ("-m", '--model-file'):
            oobModelFile = arg
            checkFileExist(oobModelFile)
        elif opt in ("-e", '--oob-eval-file'):
            # NOTE: OOB stands for Out of Bag and this file should be a holdout data set the model has never seen before
            oobEvalFile = arg
        else:
            print("Wrong usage!!!!!!!")
            usage()

    
    print '=================================================================='
    print 'Running OOB Model Evaluation'
    print '=================================================================='
    print 'Settings: oobFile={}, modelFile={}, oobFeaturesFile={}, oobEvalFile={}, use_cache={}'.format(oobFile, oobModelFile, oobFeaturesFile, oobEvalFile, use_cache)

    # Gather features for OOB file
    if not os.path.exists(oobFeaturesFile):
        print 'Gathering Features. This may take a while..........'
        yield ml_eval.gather_features_to_csv(oobFile, oobFeaturesFile, use_cache)

    # Load training,target data from csv    
    print 'Loading training, target from csv data ............'
    train, target = load_training_from_csv(oobFeaturesFile)

    # Evaluate model
    print 'Evaluating model ............'
    runtitle="{}-{}".format(oobEvalFile,datetime.now().strftime('%Y%m%d'))
    eval_model_oob(train, target, model_file= oobModelFile, title=runtitle, oob_eval_file=oobEvalFile)


if __name__ == "__main__":
    ioloop.IOLoop.instance().run_sync(lambda: main(sys.argv[1:]))
