#!/bin/bash

SCRIPT_DIR=$(dirname $(readlink -f "$0"))

HOSTS="$1"
shift

BRICKS_DIR=/home/dmadl/run-bricks/mmt
ABS_BRICKS_DIR=/fs/lofn0/dmadl/mmt/run-bricks/mmt
CONF_DIR=/fs/lofn0/dmadl/mmt/bricks/examples/mmt

# symlinked:
# ln -s /fs/lofn0/dmadl/mmt/run-bricks /home/dmadl/run-bricks

pushd $BRICKS_DIR >/dev/null
dir=$(date "+%Y-%m-%d_%H-%M-%S")
#echo $dir
mkdir $dir || exit 1
pushd $dir

. /fs/lofn0/dmadl/mmt/run-bricks/env.sh

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
  bricks.py experiment.cfg
  popd >/dev/null

  # submit job to host
  ssh $host "
    . /fs/lofn0/dmadl/mmt/run-bricks/env.sh
    cd $ABS_BRICKS_DIR/$dir/$experiment
    nice nohup $SCRIPT_DIR/run-job.sh $dir $experiment >> nohup.out 2>&1 &
  "
done

popd >/dev/null  # $dir
popd >/dev/null  # $BRICKS_DIR

if [ $# -gt 0 ]; then
  echo >&2 "warning: some jobs have not been assigned hosts:"
  echo >&2 "$@"
fi
