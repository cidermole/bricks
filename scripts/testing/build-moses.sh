#!/bin/bash

branch=master
rev=HEAD

BUILD_MOSES=/home/dmadl/mmt/bricks/scripts/build-moses.sh
BUILD_MOSES_OPTS="-b $branch -a /fs/saxnot0/dmadl/build/auto -g /home/dmadl/gcc-4.9.2"

# obtain the given / most recent revision number of the branch
gitrev=$($BUILD_MOSES $BUILD_MOSES_OPTS -r $rev -v)

# build the most recent revision in the staging directory
moses=$($BUILD_MOSES $BUILD_MOSES_OPTS -r $gitrev)

echo gitrev=$gitrev
echo moses=$moses
