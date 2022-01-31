#!/usr/bin/env python

from tornado.ioloop import IOLoop
from tornado.web import RequestHandler, Application, url
from tornado import queues
from tornado import gen, httpclient
from tornado.options import options
import json
import time
from datetime import timedelta
import unicodecsv as csv

from pandas import DataFrame, read_table, Series, concat
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.cross_validation import train_test_split, StratifiedShuffleSplit

from models.telescope_model import TelescopeClassifier
from models.manager import score_mixed_indicators
from utils.tools import batch, unwrap_dataframe, validate_indicator
from utils.telescope_client import TelescopeClient

import logging
import sys
import argparse
import pickle

root = logging.getLogger()
root.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
root.addHandler(ch)


def make_training_set_filename(prefix):
    return '{pre}-training.csv'.format(pre=prefix)

def make_evaluation_set_filename(prefix):
    return '{pre}-evaluation.csv'.format(pre=prefix)



@gen.coroutine
def enrich_iocs(iocs):
    telescope = TelescopeClient()
    enriched_dict = yield telescope.batch_enrich(iocs)

    enriched_df = DataFrame.from_dict(enriched_dict, orient='index')
    enriched_df = concat([enriched_df, iocs], axis=1)

    # Strip out any nulls caused by Telescope returning different indicators
    #   This happens because the training set may have malformed indicators
    enriched_df = enriched_df[enriched_df.value.notnull()]
    enriched_df = enriched_df[enriched_df.internal.notnull()]

    raise gen.Return(enriched_df)


@gen.coroutine
def enrich_and_split(values, labels, split_percentage):
    enriched_df = yield enrich_iocs(values)
    enriched_df = concat([enriched_df, labels], axis=1)
    enriched_df = enriched_df[enriched_df.label.notnull()]

    # Note: There appears to be a bug in StratifiedShuffleSplit that 
    #   does not correctly set test_size when train_size is set alone
    train_index, eval_index = next(iter(StratifiedShuffleSplit(enriched_df.label, 
                                            n_iter=1, #train_size=split_percentage, 
                                            test_size=1-split_percentage, random_state=1)))

    training_df = enriched_df.ix[train_index]
    evaluation_df = enriched_df.ix[eval_index]

    raise gen.Return((training_df, evaluation_df))


@gen.coroutine
def enrich_features_from_csv(input_csv_fn, output_fn_prefix, split_percentage):
    """
    Drops duplicates and requires that the input has 'value' and 'label' in the header.
    Additionally, the cardinality of labels must be > 1
    """
    df = read_table(input_csv_fn, sep=',')
    df.drop_duplicates(subset='value', inplace=True)

    df.index = df.value
    df = df[df.value.apply(validate_indicator)]

    iocs = df.value
    labels = df.label

    training_df, evaluation_df = yield enrich_and_split(iocs, labels, split_percentage)

    training_csv_fn = make_training_set_filename(output_fn_prefix)
    training_df = training_df.applymap(json.dumps)
    training_df.to_csv(training_csv_fn, index=False)
    root.info('Writing Training CSV Out To File: ' + training_csv_fn)

    evaluation_csv_fn = make_evaluation_set_filename(output_fn_prefix)
    evaluation_df = evaluation_df.applymap(json.dumps)
    evaluation_df.to_csv(evaluation_csv_fn, index=False)
    root.info('Writing Evaluation CSV Out To File: ' + evaluation_csv_fn)


def train_model_from_csv(input_csv_fn, output_model_fn):
    """
    train classifier based on 'label' column of csv
    """
    df = read_table(input_csv_fn, sep=',')
    df.drop_duplicates(subset='value', inplace=True)
    df.index = df.value
    iocs = df.value

    # Why are there NaN's in this file?
    df = df.dropna()

    for cname in df.columns:
        if cname not in ['value', 'label']:
            try:
                df[cname] = df[cname].apply(json.loads)
            except Exception, e:
                print "Error loading JSON String from Column '%s'" % cname
                print "Column: ", df[cname]
                raise e

    model = TelescopeClassifier()
    model.train(df, df.label)

    model.save(output_model_fn)


@gen.coroutine
def score_iocs_from_csv(input_csv_fn, scored_csv_fn):
    df = read_table(input_csv_fn, sep=',')
    df.drop_duplicates(subset='value', inplace=True)

    df.index = df.value
    df = df[df.value.apply(validate_indicator)]

    iocs = df.value

    enriched_df = yield enrich_iocs(iocs)

    scores = score_mixed_indicators(enriched_df)

    scored_df = DataFrame.from_dict(scores, orient='index')
    # scored_df.index = features_for_type.index
    scored_df.index.name = 'value'

    scored_df['label'] = scored_df.Malicious.apply(lambda x: 'Benign' if x < .5 else 'Malicious')

    scored_df.to_csv(scored_csv_fn)
    root.info('Writing Scored CSV Out To File: ' + scored_csv_fn)


def enrich_features(input_csv_fn, output_fn_prefix, split_percentage):
    """
    Call Telescope with list of indicators in batches of XXX and return results dict
    """
    IOLoop.current().run_sync(lambda: enrich_features_from_csv(input_csv_fn, output_fn_prefix, split_percentage))


def score_iocs(input_csv_fn, output_fn_prefix):
    """
    Call Telescope with list of indicators in batches of XXX and return results dict
    """
    IOLoop.current().run_sync(lambda: score_iocs_from_csv(input_csv_fn, output_fn_prefix))


def parse_args(args):
    """
    Usage:
        Enrich features without training:
            training.py enrich input.csv > output.csv   # where input.csv has labeled header of 'value', 'label'

        Train a new model:
            training.py train input.csv new_model.model       
            # where input.csv has labeled header of 'value', 'label', (optional 'type' if --type not specified)
            # and 'features' may be added to skip resolution with json feature dictionaries (output from 'run.py enrich')

    """

    def enrich(args):
        input_csv_fn = args.input
        output_fn_prefix = args.output
        split_percentage = args.split
        enrich_features(input_csv_fn, output_fn_prefix, split_percentage)

    def train(args):
        input_csv_fn = args.input
        output_model_fn = args.model_fn
        train_model_from_csv(input_csv_fn, output_model_fn)

    def score(args):
        input_csv_fn = args.input
        output_fn_prefix = args.output
        score_iocs(input_csv_fn, output_fn_prefix)

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    parser_enrich = subparsers.add_parser('enrich', help="Enrich IOC's with Telescope")
    parser_enrich.add_argument('input', type=str, 
                    help="Labeled CSV file expected with a header specifying 'value' and 'label'.")
    parser_enrich.add_argument('-s', '--split', dest='split', type=float, default=0.75,
                    help="Optional flag to split output into training and evaluation set.")
    parser_enrich.add_argument('output', type=str, help="Output filename prefix.")
    parser_enrich.set_defaults(func=enrich)

    parser_train = subparsers.add_parser('train', help='Train a new Macula model.')
    parser_train.add_argument('input', type=str, 
                    help="Labeled CSV file expected with a header specifying 'value' and 'label'.")
    parser_train.add_argument('model_fn', type=str, 
                    help="Filename for the new, pickled model file.")
    parser_train.set_defaults(func=train)

    parser_enrich = subparsers.add_parser('score', help="Score IOC's with Telescope Classifier")
    parser_enrich.add_argument('input', type=str, 
                    help="Labeled CSV file expected with a header specifying 'value'.")
    parser_enrich.add_argument('output', type=str, help="Output filename.")
    parser_enrich.set_defaults(func=score)
    
    return parser.parse_args(args)
    

def process_cmdline(args):
    parser = parse_args(args)
    parser.func(parser)


if __name__=="__main__":
    process_cmdline(sys.argv[1:])
