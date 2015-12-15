#!/bin/bash
set -e

#BUILD_OPTIONS=""
BUILD_TYPE="Release"

TMP=/tmp/build-moses.$$

# later, arg
AUTO_TARGET_DIR=/home/david/build/auto

MOSES_SRC_REPO=git@github.com:moses-smt/mosesdecoder.git
MOSES_CACHED_REPO=git@github.com:moses-smt/mosesdecoder.git
MOSES_REV=master
MOSES_BRANCH=master


# parse command line args
OPTIND=1
while getopts "h?s:r:b:a:t:" opt; do
    case "$opt" in
    s)
        # source repository
        MOSES_SRC_REPO="$OPTARG"
        ;;
    r)
        # revision
        MOSES_REV=$OPTARG
        ;;
    b)
        # branch
        MOSES_BRANCH=$OPTARG
        ;;
    a)
        # AUTO_TARGET_DIR
        AUTO_TARGET_DIR="$OPTARG"
        ;;
    t)
        # build type
        BUILD_TYPE=$OPTARG
        ;;

    h|\?)
        echo "usage: $0 [-s source-repo.git] [-r revision] [-b branch] [-a auto-target-dir] [-t Release|Debug|RelWithDebInfo]"
        exit 0
        ;;
    esac
done

shift $((OPTIND-1))

[ "$1" = "--" ] && shift


OPT_DIR=$AUTO_TARGET_DIR/opt
MOSES_CACHED_DIR=$AUTO_TARGET_DIR/cached-moses



function have_native_boost() {
    if [ -e /usr/include/boost/version.hpp ]; then
        boost_version=$(awk '/define BOOST_VERSION/ {print $3}' /usr/include/boost/version.hpp)
        if [ $boost_version -ge 105900 ]; then
            # if system has at least Boost 1.59, then don't bother using the other one.
            return 0
        fi
    fi
    return 1
}

function ensure_have_moses_cached() {
  if [ ! -e $MOSES_CACHED_DIR ]; then
      # maintain a recent moses git repo to avoid always having to pull the History of Time.
      git clone $MOSES_CACHED_REPO $MOSES_CACHED_DIR
  fi
}

function ensure_have_dependencies() {
  if [ ! -e $OPT_DIR ]; then
      # set up opt tools ...

      mkdir -p $OPT_DIR

      pushd $(dirname $OPT_DIR)
      # build stuff in ./build, install in ./opt
      if have_native_boost; then
          # all: xmlrpc cmph irstlm boost
          make -f $(dirname $0)/install-dependencies.gmake xmlrpc cmph irstlm
      else
          make -f $(dirname $0)/install-dependencies.gmake
      fi
      popd
  fi
}

function get_git_revision() {
    ensure_have_moses_cached
    mkdir -p $TMP
    git clone $MOSES_CACHED_DIR $TMP/moses.check
    pushd $TMP/moses.check

    git remote remove origin
    git remote add origin $MOSES_SRC_REPO
    git fetch
    git checkout $MOSES_BRANCH
    git checkout $MOSES_REV

    # first 7 characters of revision
    MOSES_REV=$(git log | awk '/^commit/ { print(substr($2, 0, 7)); exit; }')

    # didn't want to use "git describe --dirty" here, because it's so long.

    popd
    rm -rf $TMP
}


# backup stdout to fd=6
exec 6<&1
# redirect stdout to stderr (our stdout has a special meaning below)
exec 1>&2


#if [ "$MOSES_REV" == "$MOSES_BRANCH" -o "$MOSES_REV" == "HEAD" ]; then
#    # need to get the actual revision!
#    #MOSES_REV=$(get_git_revision)
#    get_git_revision
#fi

# always get git revision, this way we cannot fail to get it right.
get_git_revision


# pattern for directory name: moses.branch.rev.BuildType
# this ensures we build different configs separately
MOSES_TARGET_DIR=$AUTO_TARGET_DIR/moses.$MOSES_BRANCH.$MOSES_REV.$BUILD_TYPE
mkdir -p $MOSES_TARGET_DIR


if [ -e $MOSES_TARGET_DIR/bin/moses ]; then
    # there is already a build for this revision
    exit 0
fi

ensure_have_dependencies
ensure_have_moses_cached

# clean up if there was something left over
rm -rf "$MOSES_TARGET_DIR"

pushd $(dirname $MOSES_TARGET_DIR)

# quick clone of most data
git clone $MOSES_CACHED_DIR $(basename $MOSES_TARGET_DIR)
pushd $(basename $MOSES_TARGET_DIR)

git remote remove origin
git remote add origin $MOSES_SRC_REPO
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
#if [ -e ./compile.sh ]; then
#    # recent versions have a ./compile.sh
#    ./compile.sh $BUILD_OPTIONS
#else

# link=static? no?

if have_native_boost; then
    WITH_BOOST=""
else
    WITH_BOOST="--with-boost=./opt"
fi

set -e -o pipefail
./bjam --with-irstlm=./opt $WITH_BOOST --with-cmph=./opt --with-xmlrpc-c=./opt --with-mm --with-probing-pt -j$(getconf _NPROCESSORS_ONLN) $BUILD_OPTIONS

#fi

popd
popd


# Restore stdout
exec 1<&6  # restore stdout from fd=6

# our only stdout: the true path to moses binary
echo "$MOSES_TARGET_DIR/bin/moses"


# implicit return value
[ -e $MOSES_TARGET_DIR/bin/moses ]

