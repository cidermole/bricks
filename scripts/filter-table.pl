#!/usr/bin/env perl
#
# This file is part of moses.  Its use is licensed under the GNU Lesser General
# Public License version 2.1 or, at your option, any later version.

# $Id$
# Given an input text prepare minimized phrase table.
# Stripped down from filter-model-given-input.pl to its bare necessities.

# original code by Philipp Koehn
# changes by Ondrej Bojar

use warnings;
use strict;

use FindBin qw($RealBin);
use Getopt::Long;

# consider phrases in input up to $MAX_LENGTH
# in other words, all phrase-tables will be truncated at least to 10 words per
# phrase.
my $MAX_LENGTH = 10;

my $SOURCE_FACTOR = "0";

# utilities
my $ZCAT = "gzip -cd";

# get optional parameters
my $min_score = undef;
my $max_phrase_len = undef;
my $source_factor = undef;

GetOptions(
    "MinScore=s" => \$min_score,
	"SourceFactor=s" => \$source_factor,
	"MaxPhraseLen=i" => \$max_phrase_len
) or exit(1);

# get command line parameters
my $input = shift;

if (!defined $input) {
  print STDERR "usage: filter-table.pl input.text < phrase-table > phrase-table.filtered\n";
  exit 1;
}

$MAX_LENGTH = $max_phrase_len if defined $max_phrase_len;

# decode min-score definitions
my %MIN_SCORE;
if ($min_score) {
  foreach (split(/ *, */,$min_score)) {
    my ($id,$score) = split(/ *: */);
    $MIN_SCORE{$id} = $score;
    print STDERR "score $id must be at least $score\n";
  }
}

my %CONSIDER_FACTORS;

# for now, only consider factor '0' unless configured otherwise
$source_factor = $SOURCE_FACTOR if !defined $source_factor;
$CONSIDER_FACTORS{$source_factor} = 1;

# Collect used phrases from input.txt

my %PHRASE_USED;
# get the phrase pairs appearing in the input text, up to the $MAX_LENGTH
open(INPUT,mk_open_string($input)) or die "Can't read $input";
while(my $line = <INPUT>) {
	chomp($line);
	my @WORD = split(/ +/,$line);
	for(my $i=0;$i<=$#WORD;$i++) {
		for(my $j=0;$j<$MAX_LENGTH && $j+$i<=$#WORD;$j++) {
			foreach (keys %CONSIDER_FACTORS) {
				my @FACTOR = split(/,/);
				my $phrase = "";
				for(my $k=$i;$k<=$i+$j;$k++) {
					my @WORD_FACTOR = split(/\|/,$WORD[$k]);
					for(my $f=0;$f<=$#FACTOR;$f++) {
						$phrase .= $WORD_FACTOR[$FACTOR[$f]]."|";
					}
					chop($phrase);
					$phrase .= " ";
				}
				chop($phrase);
				$PHRASE_USED{$_}{$phrase}++;
			}
		}
	}
}
close(INPUT);

my $factors = $source_factor;

# filter files
print STDERR "Filtering file...\n";
my ($used,$total) = (0,0);
while(my $entry = <STDIN>) {
  my ($foreign,$rest) = split(/ \|\|\| /,$entry,2);
  $foreign =~ s/ $//;
  if (defined($PHRASE_USED{$factors}{$foreign})) {
	  # handle min_score thresholds
	  if ($min_score) {
		 my @ITEM = split(/ *\|\|\| */,$rest);
		 if(scalar (@ITEM)>2) { # do not filter reordering table
		   my @SCORE = split(/ /,$ITEM[1]);
		   my $okay = 1;
		   foreach my $id (keys %MIN_SCORE) {
			 $okay = 0 if $SCORE[$id] < $MIN_SCORE{$id};
		   }
		   next unless $okay;
		 }
	  }
	  print $entry;
	  $used++;
  }
  $total++;
}

# functions
sub mk_open_string {
  my $file = shift;
  my $openstring;
  if ($file !~ /\.gz$/ && -e "$file.gz") {
    $openstring = "$ZCAT $file.gz |";
  } elsif ($file =~ /\.gz$/) {
    $openstring = "$ZCAT $file |";
  } else {
    $openstring = "< $file";
  }
  return $openstring;
}
