#!/bin/bash
#
# ran in a directory which has an experiment.cfg
# ran in env which has redo in PATH

dir="$1"
experiment="$2"

host=$(hostname)

# original working dir (on NFS)
ODIR=$(pwd)

# local host working dir
TMP_BRICKS_DIR=/fs/${host}0/dmadl/run-bricks-wd
WDIR=$TMP_BRICKS_DIR/$dir/$experiment

# copy and run elsewhere.
mkdir -p $(dirname $WDIR)
cp -r --preserve=links $ODIR $WDIR
pushd $WDIR >/dev/null

# run the Experiment.
redo &

pid=$!
echo $pid | tee $WDIR/redo.pid > $ODIR/redo.pid

# process group id (can use kill -TERM -pgid # with negative pgid)
pgid=$(sed -n '$s/.*) [^ ]* [^ ]* \([^ ]*\).*/\1/p' < /proc/$pid/stat)
echo $pgid | tee $WDIR/redo.pgid > $ODIR/redo.pgid

# wait for Experiment to actually finish.
wait $pid

popd >/dev/null  # $WDIR

cd ..
# backup old link structure
mv "$experiment" "${experiment}.bak"
# copy back results
cp -r --preserve=links $WDIR $ODIR || exit 1
cp "${experiment}.bak/nohup.out" "$experiment"
rm -rf "${experiment}.bak"
rm -rf "$WDIR"
rmdir $(dirname $WDIR)  # remove $dir (the timestamped dir)
