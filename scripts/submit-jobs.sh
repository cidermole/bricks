#!/bin/bash

#BRICKS=/mnt/lofn0/dmadl/mmt/bricks
BRICKS=/mnt/saxnot0/dmadl/mmt/bricks

#SCRIPT_DIR=$(dirname $(readlink -f "$0"))  # not cross-host
SCRIPT_DIR=$BRICKS/scripts

# capitalize first letter
setup=$(hostname | sed 's/[^ _-]*/\u&/g').cfg

if [ "${1::1}" == "-" ]; then
  option="$1"
  shift

  if [ "$option" == "--setup" ]; then
    setup="$1"
    shift
  fi
fi

HOSTS="$1"
shift

# must be cluster-accessible
#ABS_BRICKS_DIR=/mnt/lofn0/dmadl/mmt/run-bricks/mmt
ABS_BRICKS_DIR=/mnt/saxnot0/dmadl/mmt/run-bricks/mmt
CONF_DIR=$BRICKS/examples/mmt

# symlinked:
# ln -s /fs/lofn0/dmadl/mmt/run-bricks /home/dmadl/run-bricks

pushd $ABS_BRICKS_DIR >/dev/null
dir=$(date "+%Y-%m-%d_%H-%M-%S")
#echo $dir
mkdir $dir || exit 1
pushd $dir

. $ABS_BRICKS_DIR/env.sh  # load bricks.py and redo into PATH

for host in $HOSTS; do
  if [ $# -eq 0 ]; then
    echo >&2 "note: more hosts than jobs."
    break
  fi

  experiment="$1"
  shift

  if [ ! -e $CONF_DIR/$experiment.cfg ]; then
    echo >&2 "error: no mmt experiment $experiment.cfg exists."
    continue
  fi

  # debug print job scheduling
  echo "$experiment @ $host"

  # set up folder
  mkdir -p $experiment && pushd $experiment >/dev/null
  target=$(pwd)
  pushd $CONF_DIR >/dev/null
  for part in *.cfg; do
    ln -sf $CONF_DIR/$part $target/$part
  done
  popd >/dev/null
  ln -sf $CONF_DIR/$experiment.cfg experiment.cfg
  # just make sure we can parse config. Actually run in run-job.sh for proper path setup
  bricks.py --setup $setup experiment.cfg
  popd >/dev/null

  # submit job to host
  ssh $host "
    . $ABS_BRICKS_DIR/env.sh  # load bricks.py and redo into PATH
    cd $ABS_BRICKS_DIR/$dir/$experiment
    nice nohup $SCRIPT_DIR/run-job.sh $dir $experiment $setup >> nohup.out 2>&1 &
  "
done

popd >/dev/null  # $dir
popd >/dev/null  # $BRICKS_DIR

if [ $# -gt 0 ]; then
  echo >&2 "warning: some jobs have not been assigned hosts:"
  echo >&2 "$@"
fi
