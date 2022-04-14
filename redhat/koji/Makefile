######################################################################
#This Makefile is here for the sole purpose of building an SRPM
#within the brew/koji build environment
#
#When Brew launches a build with a commit on the end of the brew uri,
#it runs the BuildSRPMFromSCM task first, which clones the requested
#git tree, resets to the requested commit, cd's to the directory, and runs
#'make sources'.  That make target is responsible for creating an SRPM
#that the next brew task will then build.
#
#Other targets in this makefile
#
#notes: Responsible for pulling any note branches down from the origin
#
#buildid: This sets the BUILDID varible, which allows a brew scratch build
#	  To have a unique buildid as set by the developer.
#	  set it with - git notes --ref buildid -m ".buildid" HEAD
######################################################################

include ../Makefile.common

notes:
	git fetch --force origin refs/notes/*:refs/notes/*

buildid: notes
	$(eval BUILDID := $(shell git notes --ref buildid show HEAD || echo .test))

sources: buildid 
	echo $(BUILDID) > ../../localversion
	$(MAKE) -C ../ dist-sources
	mv -f ../rpm/SOURCES/* .
	rm -f ./$(PACKAGE_NAME).spec
	mv ../rpm/SPECS/$(PACKAGE_NAME).spec .

test:	buildid
	echo $(BUILDID)

PHONY = sources
