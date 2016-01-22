#!/bin/bash

branch=master
rev=HEAD

TEST_FRAMEWORK=/home/shared/mmt/testing

BUILD_MOSES=$TEST_FRAMEWORK/bricks/scripts/build-moses.sh
BUILD_MOSES_OPTS="-b $branch -a $TEST_FRAMEWORK/build -g /home/dmadl/gcc-4.9.2"

# obtain the given / most recent revision number of the branch
gitrev=$($BUILD_MOSES $BUILD_MOSES_OPTS -r $rev -v)

# build the most recent revision in the staging directory
moses=$($BUILD_MOSES $BUILD_MOSES_OPTS -r $gitrev)
rv=$?

echo gitrev=$gitrev
echo moses=$moses

exit $rv
