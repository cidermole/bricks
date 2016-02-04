#!/bin/bash
#
# One-time copy of select EMS experiment data.
#
# Very specific to the particular MMT baseline experiments with
# 5 tuning runs per direction and two directions per lang pair.
#
# Copies into model_dir()/moses.${id}.ini
#
# Use --dry-run switch to avoid copying data files (passed through to
# moses-ini-copy-setup.py)
#
# Author: David Madl <git@abanbytes.eu>

# obtain paths ($TEST_FRAMEWORK, ...)
. $(dirname $0)/env.sh

EMS_RUNS_BASE=/home/bhaddow/experiments/mmt
# ems runs: http://data.statmt.org/restricted/mmt/experiment/
# aggregate reports: see http://data.statmt.org/restricted/mmt/benchmarks/

function model_dir() {
  echo ${TEST_FRAMEWORK}/models/${setup}/${src_lang}-${trg_lang}
  # note: dependency in run-tradeoff-tests.sh
}

moses_ini_copy_setup=$TEST_FRAMEWORK/bricks/scripts/moses-ini-copy-setup.py
moses_ini_change_table=$TEST_FRAMEWORK/bricks/scripts/moses-ini-change-table.py

####

# Obtain EMS parameter value from full key name.
#
function _ems_param() {
  awk 'BEGIN { FS="= " } /'$1'/ { print $2 }' $_ems_parameter
}

# Parse EMS parameters list for languages and file locations.
#
# General interface: xyz_test_setup <setup-name> <setup-id>
#
#                  (language pair)  (input and ref sents)
# Sets variables: src_lang trg_lang test_src test_ref     moses_ini
#
function ems_get_test_setup() {
  local setup_name=$1
  local id=$2

  local base=$EMS_RUNS_BASE/$setup_name

  # used by _ems_param()
  _ems_parameter=$base/steps/$id/parameter.$id

  src_lang=$(_ems_param GENERAL:input-extension)
  trg_lang=$(_ems_param GENERAL:output-extension)

  # get name of the first (only) testset
  local _ems_testset=$(perl -n -e'/EVALUATION:(.*):/ && print "$1\n"' $_ems_parameter | head -n 1)

  test_src=$base/evaluation/${_ems_testset}.input.tok.$id
  test_ref=$base/evaluation/${_ems_testset}.reference.tok.$id

  moses_ini=$base/tuning/moses.tuned.ini.$id
}

####


# Grab all experiment data from the listed EMS setups in $EMS_RUNS_BASE
#
# These setups have 5 tuning runs per language pair,
# (1-5) and (6-10) for reverse language pair.
#
# Hence we are copying two models for two directions each.

setups="
big-bench-fr-en
wmt-bench-ru-en
wmt-bench-fi-en
wmt-bench-de-en
wmt-bench-cs-en
"


for setup in $setups; do
  # the main copying work: two directions each
  for id in 1 6; do
    ems_get_test_setup $setup $id
    md=$(model_dir)
    mkdir -p $md

    #####
    # Copy models and adapt moses.ini
    $moses_ini_copy_setup -f $moses_ini $md -o $md/moses.${id}.ini "$@"

    # Alternative phrase tables, compact LR
    for ptname in PhraseDictionaryCompact ProbingPT; do
      $moses_ini_change_table -t $ptname -l -f $moses_ini $md -o $md/moses.${id}.${ptname}.ini "$@"
    done
    #####

    # Copy test corpus
    mkdir -p $md/corpus
    cp $test_src $md/corpus/test.src
    cp $test_ref $md/corpus/test.ref
  done

  # copy remaining moses.ini files (weights) using --no-overwrite-data
  for id in $(seq 1 10); do
    # note that 5 setups each go into different model_dir()
    ems_get_test_setup $setup $id
    md=$(model_dir)

    #####
    # Adapt moses.ini, but do not copy data again, using --no-overwrite-data
    $moses_ini_copy_setup -f $moses_ini $md -o $md/moses.${id}.ini --no-overwrite-data "$@"

    # Alternative phrase tables, compact LR
    for ptname in PhraseDictionaryCompact ProbingPT; do
      $moses_ini_change_table -t $ptname -l -f $moses_ini $md -o $md/moses.${id}.${ptname}.ini --no-overwrite-data "$@"
    done
    #####
  done
done
