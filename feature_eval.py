import numpy as np
import pandas as pd
import csv
import json
import gc

from tornado import gen, ioloop

import os
import sys
import getopt
import logging
from datetime import datetime

from matplotlib import pyplot as plt

def generateCharts(featureEvalFile, title=''):
    df = pd.read_csv(featureEvalFile)
    # Remove all 0 importance features
    df = df[(df['importance'] > 0)]
    
    featureSourcesImpMap = {}
    for index,row in df.iterrows():
        source = row['name'].split('.')[0]
        if source in featureSourcesImpMap:
            featureSourcesImpMap[source] += row['importance']
        else:
            featureSourcesImpMap[source] = row['importance']
    
    labels = featureSourcesImpMap.keys()
    values = featureSourcesImpMap.values()
    plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=140)
    plt.axis('equal')
    plt.tight_layout()
    plt.show()


@gen.coroutine
def main(argv):
    def usage():
        print '========================================================================================'
        print 'Usage:  python {} -f <featureEvalFile.csv>'.format(sys.argv[0])
        print '========================================================================================'
        print('Flags:')
        print("    -f, --feature-eval-file            - Feature Eval File")
        print("    -h, --help                         - Print help menu")
        sys.exit(2)

    featureEvalFile = None    

    try:
        opts, args = getopt.getopt(argv, "h:f:",\
        ['help', 'feature-eval-file='])
    except getopt.GetoptError:
        usage() 

    def checkFileExist(path):
        if not os.path.exists(path):
            print("{} does not exist!".format(path))
            usage()

    for opt, arg in opts:
        if opt in ("-h", '--help'):
            usage()
        elif opt in ("-f", '--feature-eval-file'):
            featureEvalFile = arg
        else:
            print("Wrong usage!!!!!!!")
            usage()

    
    generateCharts(featureEvalFile)

if __name__ == "__main__":
    ioloop.IOLoop.instance().run_sync(lambda: main(sys.argv[1:]))
