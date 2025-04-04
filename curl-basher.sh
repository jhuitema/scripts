#!/bin/bash

usage() {
  echo "Usage: $1 <concurrency> <iterations> <url>"
  echo ""
  echo "Example: $1 4 100 http://127.0.0.1:8080"
  echo ""
  echo "         Will run 4 concurrent curl requests"
  echo "         100 times against 127.0.0.1:8080"
  echo ""
  exit 1
}

[ $# -gt 2 ] || usage $0

TMP=/tmp/loadtest.$$.tmp

CONCURRENCY=$1
ITERATIONS=$2
URL=$3
QUERY=$4

runtest() {
  CONCURRENCY=$1
  ITERATIONS=$2
  URL=$3
  QUERY=$4
  echo "QUERY: $QUERY"
  declare -a PIDS=()
  for (( j = 1; j <= $CONCURRENCY; j++ ))
  do
    ( 
      for (( i = 1; i <= $ITERATIONS; i++ ))
      do
        curl -o /dev/null $URL -H "content-type:application/json" --data "{\"query\":\"$QUERY\"}" 2>/dev/null ;
        if [ $? != 0 ]; then
          echo "ERROR"
        fi
        if [ $j == 1 ]; then
          echo -n "."
        fi
      done
    ) &
    PIDS[${j}]=$!
  done
  for PID in ${PIDS[*]}; do
    wait $PID
  done
  echo ""
}

time ( runtest $CONCURRENCY $ITERATIONS $URL $QUERY ) 2>$TMP
REQS=`expr $ITERATIONS \* $CONCURRENCY` 
TIMESTR=`awk '$1=="real"{print $2}' $TMP`
MINS=`echo "$TIMESTR" |cut -dm -f1`
SECS=`echo "$TIMESTR" |cut -dm -f2 |cut -ds -f1`
TOTSECS=`awk "BEGIN {x=($MINS*60)+$SECS; print x}"`
RPS=`awk "BEGIN {x=$REQS/$TOTSECS; print x}"`
echo "$REQS requests completed in $TIMESTR = $RPS requests/second"
rm $TMP
