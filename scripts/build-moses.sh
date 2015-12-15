#!/bin/bash
set -e

#BUILD_OPTIONS=""
BUILD_TYPE="Release"

# later, arg
#MOSES_TARGET_DIR=/home/david/build/auto/moses.master
AUTO_TARGET_DIR=/home/david/build/auto

MOSES_REPO=git@github.com:moses-smt/mosesdecoder.git
MOSES_CACHED_REPO=git@github.com:moses-smt/mosesdecoder.git
MOSES_REV=master
MOSES_BRANCH=master

# pattern for directory name: moses.branch.rev.BuildType
# this ensures we build different configs separately
MOSES_TARGET_DIR=$AUTO_TARGET_DIR/moses.$MOSES_BRANCH.$MOSES_REV.$BUILD_TYPE

OPT_DIR=$MOSES_TARGET_DIR/../opt
MOSES_CACHED_DIR=$MOSES_TARGET_DIR/../cached-moses


# backup stdout to fd=6
exec 6<&1
# redirect stdout to stderr (our stdout has a special meaning below)
exec 1>&2


mkdir -p $MOSES_TARGET_DIR

if [ ! -e $OPT_DIR ]; then
    # set up opt tools ...
    
    mkdir -p $OPT_DIR
    
    pushd $(dirname $OPT_DIR)
    # build stuff in ./build, install in ./opt
    make -f $(dirname $0)/install-dependencies.gmake
    popd
fi

if [ -e $MOSES_TARGET_DIR/bin/moses ]; then
    # there is already a build for this revision
    exit 0
fi

if [ ! -e $MOSES_CACHED_DIR ]; then
    # maintain a recent moses git repo to avoid always having to pull the History of Time.
    git clone $MOSES_CACHED_REPO $MOSES_CACHED_DIR
fi

# make sure we don't go via $MOSES_TARGET_DIR that's not going to exist
MOSES_CACHED_DIR=$(readlink -f $MOSES_CACHED_DIR)

# clean up if there was something left over
rm -rf "$MOSES_TARGET_DIR"

pushd $(dirname $MOSES_TARGET_DIR)

# quick clone of most data
git clone $MOSES_CACHED_DIR $(basename $MOSES_TARGET_DIR)
pushd $(basename $MOSES_TARGET_DIR)

git remote remove origin
git remote add origin $MOSES_REPO
git fetch
git checkout $MOSES_BRANCH
git checkout $MOSES_REV


function have_option() {
    # try and make sure we don't exit because of set -e
    if grep -q "$1" Jamroot; then
        exit 0
    else
        exit 1
    fi
}

# shorthand BUILD_TYPE options like CMake: Release, Debug, RelWithDebInfo
case "$BUILD_TYPE" in
    Release)
        BUILD_OPTIONS="variant=release"
        ;;
        
    Debug)
        BUILD_OPTIONS="debug-symbols=on variant=debug"
        if have_option "with-address-sanitizer"; then
            BUILD_OPTIONS="$BUILD_OPTIONS --with-address-sanitizer"
        fi
        if have_option "debug-build"; then
            BUILD_OPTIONS="$BUILD_OPTIONS --debug-build"
        fi
        ;;
        
    RelWithDebInfo)
        BUILD_OPTIONS="debug-symbols=on variant=release"
        if have_option "with-profiler"; then
            BUILD_OPTIONS="$BUILD_OPTIONS --with-profiler"
        fi
        if have_option "debug-build"; then
            BUILD_OPTIONS="$BUILD_OPTIONS --debug-build"
        fi
        ;;

    *)
        echo $"valid build types: {Release|Debug|RelWithDebInfo}"
        exit 1 
esac




# build using additional build options
ln -s ../opt ./opt
if [ -e ./compile.sh ]; then
    # recent versions have a ./compile.sh
    ./compile.sh $BUILD_OPTIONS
else
    # untested.
    set -e -o pipefail
    ./bjam --with-irstlm=./opt --with-boost=./opt --with-cmph=./opt --with-xmlrpc-c=./opt --with-mm --with-probing-pt -j$(getconf _NPROCESSORS_ONLN) $BUILD_OPTIONS
fi

popd
popd


# Restore stdout
exec 1<&6  # restore stdout from fd=6

# our only stdout: the true path to moses binary
echo "$MOSES_TARGET_DIR/bin/moses"


# implicit return value
[ -e $MOSES_TARGET_DIR/bin/moses ]

