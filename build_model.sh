#!/bin/bash

set -e

if [ -z "$1" -o -z "$2" -o -z "$3" ]
then
	echo "Usage: $0 <training-set-input> <features-file-output> <model-file-output> <featurerank-file-log>"
	exit 1
fi

TRAINING_SET="$1"
FEATURES_FILE="$2"
MODEL_FILE="$3"
FEATURERANK_FILE="$4"
S3_OUTPUT_PATH="s3://ts-labs/macula"

DIR=`dirname "$0"`
source "$DIR/env/bin/activate"
#source "$DIR/macula.rc"

echo "[`date`] Running ml_eval on training set ($TRAINING_SET) to fetch features ($FEATURES_FILE) and build model ($MODEL_FILE) logging featurank to ($FEATURERANK_FILE)"
time python "$DIR/ml_eval.py" --training-file="$TRAINING_SET" \
    --features-file="$FEATURES_FILE" \
    --save-model="$MODEL_FILE" \
    --dump-featurerank-file="$FEATURERANK_FILE" \
    --use-cache 
    #--skip-eval will do this automatically unless foldseval is specified

echo "[`date`] ml_eval finished. Output files:"
/bin/ls -l "$FEATURES_FILE" "$MODEL_FILE"

echo "[`date`] compressing $FEATURES_FILE ..."
gzip "$FEATURES_FILE"
echo "[`date`] compressing $FEATURERANK_FILE ..."
gzip "$FEATURERANK_FILE"

echo "[`date`] Pushing $FEATURES_FILE.gz to S3 ..."
s3cmd put "$FEATURES_FILE.gz" "$S3_OUTPUT_PATH/"
echo "[`date`] Pushing $MODEL_FILE to S3 ..."
s3cmd put "$MODEL_FILE" "$S3_OUTPUT_PATH/"
echo "[`date`] Pushing $FEATURERANK_FILE.gz to S3 ..."
s3cmd put "$FEATURERANK_FILE.gz" "$S3_OUTPUT_PATH/"

