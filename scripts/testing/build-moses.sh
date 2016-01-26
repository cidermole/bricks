#!/bin/bash
#
# Pass hostname as an argument to ssh build on that host.
# Must then be invoked with an absolute path.

if [ "$(hostname)" != "hopper" ]; then
  if [ $# -gt 0 ]; then
    build_host=$1
    ssh $build_host "$0"
    exit $?
  fi
  EXTRA="-g /home/dmadl/gcc-4.9.2"

else
  # don't bother rebuilding moses for testing
  gitrev=b0c208c
  # but if we wanted to, we have a recent system GCC here.
  EXTRA=""
fi



# obtain paths ($TEST_FRAMEWORK, ...)
. $(dirname $0)/env.sh

branch=master
rev=HEAD

BUILD_MOSES=$TEST_FRAMEWORK/bricks/scripts/build-moses.sh
#BUILD_MOSES_OPTS="-b $branch -a $TEST_FRAMEWORK/build -g /home/dmadl/gcc-4.9.2"
BUILD_MOSES_OPTS="-b $branch -a $TEST_FRAMEWORK/build $EXTRA"

have_moses=1
# obtain the given / most recent revision number of the branch
[ -z ${gitrev+x} ] && gitrev=$($BUILD_MOSES $BUILD_MOSES_OPTS -r $rev -v) && have_moses=$?

if [ $have_moses -ne 0 ]; then
  echo >&2 "Building moses revision $gitrev ..."
else
  echo >&2 "Using existing build of moses revision $gitrev in staging area."
fi

# build the most recent revision in the staging directory
moses=$($BUILD_MOSES $BUILD_MOSES_OPTS -r $gitrev)
rv=$?

echo gitrev=$gitrev
echo moses=$moses
# descriptor is a filename-ready summary of build source and options, e.g. moses.master.42b8b8.Release
echo descriptor=$(basename $(dirname $(dirname $moses)))

exit $rv
