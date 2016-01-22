#!/bin/bash
#
# Build a clean moses revision in a staging area $AUTO_BUILD_DIR.
#
# Dependencies are built a single time for the staging area.
#
# Then, the specified source revision is cleanly checked out and built
# from scratch, except if the exact configuration has already been
# built before.

# TODO: rename 'auto' -> 'staging'

set -e

#BUILD_OPTIONS=""
BUILD_TYPE="Release"

TMP=/tmp/build-moses.$$

# later, arg
AUTO_BUILD_DIR=/home/david/build/auto

MOSES_SRC_REPO=git@github.com:moses-smt/mosesdecoder.git
MOSES_CACHED_REPO=git@github.com:moses-smt/mosesdecoder.git
MOSES_REV=HEAD
MOSES_BRANCH=master

# to speed up the build: pass -m moses, or -m moses2
MOSES_BIN_TARGET=""

TOOLSET_GCC=""
BJAM_TOOLSET=""

MODE=""

# parse command line args
OPTIND=1
while getopts "h?s:r:b:a:t:m:q?g:v?" opt; do
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
        # AUTO_BUILD_DIR
        AUTO_BUILD_DIR="$OPTARG"
        ;;
    t)
        # build type
        BUILD_TYPE=$OPTARG
        ;;

    m)
        # moses binary target
        MOSES_BIN_TARGET=$OPTARG
        ;;

    q)
        # quick check if anything needs to be built.
        # returns 0 if everything is up-to-date (no work necessary).
        MODE="check"
        ;;
    v)
        # like q), quick check, but instead of outputting moses path on success,
        # always outputs the most recent git revision.
        # returns 0 if everything is up-to-date (no work necessary).
        MODE="revision"
        ;;

    g)
        # absolute GCC (GNU Compiler Collection) install folder of the format "/opt/gcc-4.9.2"
        TOOLSET_GCC="$OPTARG"
        ;;

    h|\?)
        echo "usage: $0 [-s source-repo.git] [-r revision] [-b branch] [-a auto-target-dir] [-t Release|Debug|RelWithDebInfo]"
        exit 0
        ;;
    esac
done

shift $((OPTIND-1))

[ "$1" = "--" ] && shift


if [ "$MOSES_BIN_TARGET" == "" ]; then
    MOSES_BIN_TARGET_OUT="moses"
else
    MOSES_BIN_TARGET_OUT="$MOSES_BIN_TARGET"
fi


OPT_DIR=$AUTO_BUILD_DIR/opt
MOSES_CACHED_DIR=$AUTO_BUILD_DIR/cached-moses



if [ "$TOOLSET_GCC" != "" ]; then
    # this PATH affects both the bjam build of moses below, and the build of dependencies like boost itself
    # (in the install-dependencies.gmake file).
    export PATH=$TOOLSET_GCC/bin:$PATH
    BJAM_TOOLSET="toolset=$(basename $TOOLSET_GCC)"
fi



function have_native_boost() {
    if [ -e /usr/include/boost/version.hpp ]; then
        boost_version=$(gawk '/define BOOST_VERSION/ {print $3}' /usr/include/boost/version.hpp)
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

  # ensure it is kept up-to-date (avoid re-downloads)
  pushd $MOSES_CACHED_DIR >/dev/null
  git fetch >/dev/null 2>&1
  git pull origin master >/dev/null 2>&1
  popd >/dev/null
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

function git_replace_remote_and_pull() {
  git remote rm origin
  git remote add origin $MOSES_SRC_REPO
  git fetch >/dev/null 2>&1
  git checkout $MOSES_BRANCH
  # we have to explicitly pull the correct branch (old git???) - generic git pull leaves us outdated
  git pull origin $MOSES_BRANCH >/dev/null 2>&1
  git checkout $MOSES_REV >/dev/null 2>&1
}

function get_git_revision() {
    ensure_have_moses_cached

    # start in subshell, which goes to /dev/null
    # we are not interested in any noise here.

    # the weird contraption is to get $MOSES_REV out of the subshell

    MOSES_REV=$( ( \
    mkdir -p $TMP
    git clone $MOSES_CACHED_DIR $TMP/moses.check
    pushd $TMP/moses.check

    git_replace_remote_and_pull

    # first 7 characters of revision
    MOSES_REV=$(git log | gawk '/^commit/ { print(substr($2, 0, 7)); exit; }')

    # didn't want to use "git describe --dirty" here, because it's so long.

    popd
    rm -rf $TMP

    echo >&3 $MOSES_REV
    ) 3>&1 >/dev/null 2>&1 )
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
MOSES_TARGET_DIR=$AUTO_BUILD_DIR/moses.$MOSES_BRANCH.$MOSES_REV.$BUILD_TYPE
mkdir -p $MOSES_TARGET_DIR


# note set -e, so we cannot just run test and set have_build=$?
if [ -e $MOSES_TARGET_DIR/bin/$MOSES_BIN_TARGET_OUT ]; then
  have_build=0
else
  have_build=1
fi


if [ "$MODE" == "revision" ]; then
    # Restore stdout
    exec 1<&6  # restore stdout from fd=6

    # just print the revision, return status indicates whether we have a build
    echo $MOSES_REV
    exit $have_build
fi


if [ $have_build -eq 0 ]; then
    echo >&2 "There is already a build for this revision $MOSES_REV"

    # Restore stdout
    exec 1<&6  # restore stdout from fd=6

    # our only stdout: the true path to moses binary
    echo $MOSES_TARGET_DIR/bin/$MOSES_BIN_TARGET_OUT
    exit 0
fi

if [ "$MODE" == "check" ]; then
    echo >&2 "Need to build this revision $MOSES_REV"
    exit 1
fi

ensure_have_dependencies
ensure_have_moses_cached

# clean up if there was something left over
rm -rf "$MOSES_TARGET_DIR"

pushd $(dirname $MOSES_TARGET_DIR)

# quick clone of most data
git clone $MOSES_CACHED_DIR $(basename $MOSES_TARGET_DIR)
pushd $(basename $MOSES_TARGET_DIR)

git_replace_remote_and_pull


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



if [ "$MOSES_BIN_TARGET" != "" ]; then
    case "$MOSES_BIN_TARGET" in
        moses)
            BUILD_OPTIONS="$BUILD_OPTIONS moses-cmd//moses"
            ;;

        moses2)
            BUILD_OPTIONS="$BUILD_OPTIONS contrib/other-builds/moses2//moses2"
            ;;

        *)
            echo $"valid MOSES_BIN_TARGET types: {moses|moses2}"
            exit 1
    esac
fi



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


# libstdc++ hack: include ../lib in rpath, so a libstdc++ can be shipped
# with moses for older distributions. This path is relative from wherever
# moses is executed from.
# see https://enchildfone.wordpress.com/2010/03/23/a-description-of-rpath-origin-ld_library_path-and-portable-linux-binaries/

if [ "$TOOLSET_GCC" != "" ]; then
  # patch a line that has stayed constant at least since Moses 3.0
  sed -i 's#external-lib z ;#external-lib z ;\nrequirements += <linkflags>-Wl,-rpath=XORIGIN/../lib ;#g' Jamroot
fi



set -e -o pipefail
./bjam --with-irstlm=./opt $WITH_BOOST --with-cmph=./opt --with-xmlrpc-c=./opt --with-mm --with-probing-pt -j$(getconf _NPROCESSORS_ONLN) $BJAM_TOOLSET $BUILD_OPTIONS


if [ "$MOSES_BIN_TARGET" != "" ]; then
    # find the binary, and put it into bin/
    # we actually find the first, but that should be the only one and hence recent
    moses_bin_target=$(find . -name "$MOSES_BIN_TARGET" -type f | grep '/bin/' | head -n 1)
    cp $moses_bin_target bin/

    # remember binary name
    moses_bin_target=bin/$(basename $moses_bin_target)
else
    # guess binary name
    moses_bin_target=bin/moses
fi

if [ "$TOOLSET_GCC" != "" ]; then
## ...
  # change XORIGIN to the magic variable
  $(dirname $0)/chrpath -r '$ORIGIN/../lib' $moses_bin_target
  # copy the used lib
  cp $TOOLSET_GCC/lib64/libstdc++.so.6 lib/
fi

#fi

popd
popd


# Restore stdout
exec 1<&6  # restore stdout from fd=6

# our only stdout: the true path to moses binary
echo "$MOSES_TARGET_DIR/bin/$MOSES_BIN_TARGET_OUT"


# implicit return value
[ -e $MOSES_TARGET_DIR/bin/$MOSES_BIN_TARGET_OUT ]

