#!/bin/bash
#
# Set up the testing framework on the cluster. Includes paths
# specific to the machine setup on our cluster.
#
# Author: David Madl <git@abanbytes.eu>
#
# If this has ../dmadl/.. paths, those should be moved to a common
# area.

# obtain paths ($TEST_FRAMEWORK, ...)
. $(dirname $0)/env.sh

# could later make config.sh here, to source with . ./config.sh
# aka env.sh, with common paths.

# commonly accessible framework dir linking to all the goodies
# (symlinks from here point to the various cluster locations)
mkdir -p $TEST_FRAMEWORK
pushd $TEST_FRAMEWORK

# scripts to run experiments
# for now: (TODO: move to github)
ln -sf /fs/lofn0/dmadl/mmt/bricks bricks

# experiment model staging area
# TODO: ln -sf /fs/crom0/mmt/testing/models models
ln -sf /fs/lofn0/mmt/testing/models models

# experiment working directory
ln -sf /fs/lofn0/mmt/testing/wd wd

# moses build staging area
ln -sf /fs/saxnot0/dmadl/build/auto build


# /home/shared/mmt/testing/bricks
# /home/shared/mmt/testing/models
# /home/shared/mmt/testing/wd
# /home/shared/mmt/testing/build


#umask 0027
#newgrp mmt


# ...

# one-time copy of select EMS experiment data
$(dirname $0)/copy-mmt-baseline-models.sh

popd
