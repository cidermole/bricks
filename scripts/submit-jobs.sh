#!/bin/bash

SCRIPT_DIR=$(dirname $(readlink -f "$0"))

HOSTS="$1"
shift

pushd ~/mmt/run-bricks/mmt >/dev/null
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

  if [ ! -e /fs/lofn0/dmadl/mmt/bricks/examples/mmt/$experiment.cfg ]; then
    echo >&2 "error: no mmt experiment $experiment.cfg exists."
    continue
  fi

  # debug print job scheduling
  echo "$experiment @ $host"

  # set up folder
  mkdir -p $experiment && pushd $experiment >/dev/null
  target=$(pwd)
  pushd /fs/lofn0/dmadl/mmt/bricks/examples/mmt >/dev/null
  for part in *.cfg; do
    ln -sf /fs/lofn0/dmadl/mmt/bricks/examples/mmt/$part $target/$part
  done
  popd >/dev/null
  ln -sf /fs/lofn0/dmadl/mmt/bricks/examples/mmt/$experiment.cfg experiment.cfg
  bricks.py experiment.cfg
  popd >/dev/null

  # submit job to host
  ssh $host "
    . /fs/lofn0/dmadl/mmt/run-bricks/env.sh
    cd /fs/lofn0/dmadl/mmt/run-bricks/mmt/$dir/$experiment
    nice nohup $SCRIPT_DIR/run-job.sh $dir $experiment >> nohup.out 2>&1 &
  "
done

popd >/dev/null  # $dir
popd >/dev/null  # run-bricks/mmt

if [ $# -gt 0 ]; then
  echo >&2 "warning: some jobs have not been assigned hosts:"
  echo >&2 "$@"
fi
