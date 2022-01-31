#!/bin/bash

set -e

if [ -z "$1" -o -z "$2" -o -z "$3" ]
then
	echo "Usage: $0 <training-set-input> <features-file-output> <model-file-output> <featurerank-file-log> <recenteval-file-output> <referenceeval-fileoutput>"
	exit 1
fi

TRAINING_SET="$1"
FEATURES_FILE="$2"
MODEL_FILE="$3"
FEATURERANK_FILE="$4"
RECENTEVAL_STATS="$5"
REFERENCEEVAL_STATS="$6"
S3_OUTPUT_PATH="s3://ts-labs/macula"

DIR=`dirname "$0"`
source "$DIR/env/bin/activate"
source "$DIR/macula.rc"

DAYSAGO=$(date --date="7 days ago" +%Y%m%d)
#alternative: ls -t /mnt/macula/training/domain-retina-training-* | head -n 2 | tail -n 1
DT=$(date +%Y%m%d)
EVAL_FILE=$(echo "$TRAINING_SET" | sed 's/'$DT'/'$DAYSAGO'/')
EVAL_FEATURES_FILE=$(echo "$FEATURES_FILE" | sed 's/'$DT'/'$DAYSAGO'/')

echo "[`date`] ml_eval_oob stats for recenteval . Output files:"
time python $DIR/oob_model_eval.py -c -o $EVAL_FILE -f $EVAL_FEATURES_FILE -m $MODEL_FILE -e $RECENTEVAL_STATS
RECENTEVAL_PERM=$(echo $RECENTEVAL_STATS | sed -r 's#-2[0-9]{7}##')
$DIR/utils/csvcombine.py -o $RECENTEVAL_PERM $RECENTEVAL_PERM $RECENTEVAL_STATS

echo "[`date`] ml_eval_oob stats for referenceeval . Output files:"
if [[ $MODEL_FILE == *"domain-"* ]]; then
    #time python $DIR/oob_model_eval.py -c -o /mnt/macula/reference/2016reference-training-domain.csv.gz -f /mnt/macula/reference/2016reference-features-domain.csv.gz -m $MODEL_FILE -e $REFERENCEEVAL_STATS
    time python $DIR/oob_model_eval.py -c -o /mnt/macula/reference/2016reference-training-domain.csv.gz -f /mnt/macula/reference/2016reference-features-domain.csv.gz -m $MODEL_FILE -e $REFERENCEEVAL_STATS
else
    time python $DIR/oob_model_eval.py -c -o /mnt/macula/reference/2016reference-training-ip.csv.gz -f /mnt/macula/reference/2016reference-features-ip.csv.gz -m $MODEL_FILE -e $REFERENCEEVAL_STATS
    #time python $DIR/oob_model_eval.py -c -o /mnt/macula/reference/2016reference-training-ip.csv.gz -f /mnt/macula/reference/2016reference-features-ip.csv.gz -m $MODEL_FILE -e $REFERENCEEVAL_STATS
fi
REFERENCEEVAL_PERM=$(echo $REFERENCEEVAL_STATS | sed -r 's#-2[0-9]{7}##')
$DIR/utils/csvcombine.py -o $REFERENCEEVAL_PERM $REFERENCEEVAL_PERM $REFERENCEEVAL_STATS

echo "[`date`] compressing $RECENTEVAL_PERM ..."
gzip "$RECENTEVAL_PERM"
echo "[`date`] compressing $REFERENCEEVAL_PERM ..."
gzip "$REFERENCEEVAL_PERM"

echo "[`date`] Pushing $RECENTEVAL_PERM.gz to S3 ..."
s3cmd put "$RECENTEVAL_PERM.gz" "$S3_OUTPUT_PATH/"
gunzip $RECENTEVAL_PERM.gz
echo "[`date`] Pushing $REFERENCEEVAL_PERM.gz to S3 ..."
s3cmd put "$REFERENCEEVAL_PERM.gz" "$S3_OUTPUT_PATH/"
gunzip $REFERENCEEVAL_PERM.gz
