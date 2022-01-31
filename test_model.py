from __future__ import division
import requests
import json
from batcher import Batcher
import sys
import os
import pandas as pd
import math, random
import sys
import time


MACULA_HOST = os.getenv('MACULA_HOST', 'https://macula.threatstream.com')

def _bulk_score(iocs, explain, useCache):
    url = '{}/api/score?indicators={}&useCache={}'.format(MACULA_HOST, ','.join(iocs), useCache)
    if explain:
        url += '&explain=true'
    #print >> sys.stderr, url
    failures = 0
    success = False
    while failures < 5:
        try:
            r = requests.get(url)
            print >> sys.stderr, r.status_code
            res = r.json()
            success = True
        except:
            e = sys.exc_info()[0]
            print >> sys.stderr, "Error processing batch: '%s'" % str(e)
            print >> sys.stderr, "Retrying ...............(failures={})".format(failures+1)
            # Exponential Backoff with a random offset to prevent clashes in a multi-threaded case.
            timeToSleep = math.pow(2, failures) + random.random()
            time.sleep(timeToSleep)
            failures += 1
            continue
        break

    if not success:
        print >> sys.stderr, "Batch Failed for iocs: {}. Skipping .....".format(iocs)
        return {}
    else:    
        return res

def bulk_score(iocs, explain, useCache):
    scores = {}
    for batch in Batcher(iocs, 50):
        batchScores = _bulk_score(list(batch), explain, useCache)
        scores.update(batchScores)

    return scores    

# Maps for score and label with the IOC as the key
def evaluate_scores(scoreMap, labelMap):
    correctCount = 0
    totalCount = 0
    for ioc in labelMap:
        label = labelMap[ioc].lower()
        scoreObj = scoreMap[ioc]

        if scoreObj: # scoreObj may not be present due to a batch failure
            totalCount += 1
            if 'rescaled' in scoreObj:
                rescaledScore = scoreObj['rescaled']

                if label == 'benign' and rescaledScore <= 15:
                    correctCount += 1
                elif label == 'malicious' and rescaledScore > 15:
                    correctCount += 1

    accuracy = correctCount / totalCount
    print 'Accuracy: {}'.format(accuracy)

if __name__ == '__main__':
    explain = False
    useCache = False
    if '-e' in sys.argv:
        sys.argv.remove('-e')
        explain = True
    if '-c' in sys.argv:
        sys.argv.remove('-c')
        useCache = True 

    csvFilePath = sys.argv[1]
    colnames = ['value', 'label', 'ioc_type', 'source']
    df = pd.read_csv(csvFilePath, names = colnames, header=0)
    # Does the first 1000 iocs.....
    df = df[:1000]
    iocs = df['value'].tolist()
    scores = bulk_score([x.strip() for x in iocs], explain=explain, useCache=useCache)
    labelMap  = {}
    for index, row in df.iterrows():
        labelMap[row['value'].strip()] = row['label'].strip()

    evaluate_scores(scores, labelMap)    
