#
# Deprecated variables
#
# This section is intentionally left at the top of the Makefile so it won't be ignored.
#
ifdef BUILD_SCRATCH_TARGET
  # deprecated in 5.19.0
  $(warning WARNING: BUILD_SCRATCH_TARGET will be deprecated in a later release, use BUILD_TARGET instead.)
  BUILD_TARGET:=$(BUILD_SCRATCH_TARGET)
endif

include Makefile.variables

# This deprecation message must come after GIT is set in Makefile.variables.
ifneq ($(GIT),git)
  # deprecated in 5.20.0
  $(warning WARNING: GIT($(GIT)) will be deprecated in a later release.)
endif

# These entries are 'duplicates' of variables specified in Makefile.variables
# that are used in the SPEC file.  Specifying these with a SPEC prefix indicates
# that the value is passed through to the spec file.
SPECRELEASED_KERNEL=$(RELEASED_KERNEL)
SPECINCLUDE_FEDORA_FILES=$(INCLUDE_FEDORA_FILES)
SPECINCLUDE_RHEL_FILES=$(INCLUDE_RHEL_FILES)

ifneq (,$(findstring n,$(firstword -$(MAKEFLAGS))))
  # Do not set RHTEST on the command line. Use the make command built-in options
  # -n, --just-print, --dry-run, --recon on the command line.
  RHTEST=1
endif

LANG=C

ifndef RHSELFTESTDATA
  TOPDIR:=$(shell $(GIT) rev-parse --show-toplevel)
else
  # change TOPDIR to be relative
  TOPDIR:=..
  # RHEL_RELEASE may be updated which will cause a difference with the BUILD variable
  RHEL_RELEASE:=6
  BUILD:=$(RHEL_RELEASE)
endif

REDHAT:=$(TOPDIR)/redhat
include $(TOPDIR)/Makefile.rhelver

ifndef RHDISTDATADIR
  RHDISTDATADIR=${REDHAT}/self-test/data
endif

RPMBUILD:=$(shell if [ -x "/usr/bin/rpmbuild" ]; then echo rpmbuild; \
                  else echo rpm; fi)

MACH:=$(shell uname -m)
SPECKVERSION:=$(shell $(GIT) show $(HEAD):Makefile | sed -ne '/^VERSION\ =\ /{s///;p;q}')
SPECKPATCHLEVEL:=$(shell $(GIT) show $(HEAD):Makefile | sed -ne '/^PATCHLEVEL\ =\ /{s///;p;q}')
SPECKSUBLEVEL:=$(shell $(GIT) show $(HEAD):Makefile | sed -ne '/^SUBLEVEL\ =\ /{s///;p;q}')
SPECKEXTRAVERSION:=$(shell $(GIT) show $(HEAD):Makefile | sed -ne '/^EXTRAVERSION\ =\ /{s///;p;q}')
GITID:= $(shell $(GIT) log --max-count=1 --pretty=format:%H $(HEAD))
ifndef RHSELFTESTDATA
  BUILD:=$(RHEL_RELEASE)
endif
FLAVOR=
CURARCH := $(shell uname -m)
ARCHCONFIG := $(shell uname -m | sed -e s/x86_64/X86_64/ \
				     -e s/s390x/S390/ -e s/ppc.*/PPC/ )

# rpm information
SPECFILE:=$(PACKAGE_NAME).spec
RPM:=$(REDHAT)/rpm
SRPMS:=$(RPM)/SRPMS
SOURCES:=$(RPM)/SOURCES
TESTPATCH:=$(REDHAT)/linux-kernel-test.patch
SPECCHANGELOG:=$(PACKAGE_NAME).changelog-$(RHEL_MAJOR).$(RHEL_MINOR)
CHANGELOG_PREV:=$(PACKAGE_NAME).changelog-$(RHEL_MAJOR).$(shell expr $(RHEL_MINOR) - 1)
ARCH_LIST=aarch64 ppc64le s390x x86_64

ifndef DISTRO
  ifneq ($(findstring .fc,$(DIST)),)
    DISTRO := fedora
  else
    DISTRO := rhel
  endif
endif

ifndef RHJOBS
  RHJOBS=$(shell j=$$(echo $(MAKEFLAGS) | grep -Eo "(^|[ ])-j[0-9]*" | xargs ); \
	  if [ -z "$${j}" ]; then \
	  	echo "1"; \
	  else \
	  	j=$$(echo "$${j}" | tr -d "\-j"); \
	  	[ -z "$${j}" ] && nproc || echo $${j}; \
	  fi)
endif

LOCVERFILE:=../localversion
# create an empty localversion file if you don't want a local buildid
ifneq ($(wildcard $(LOCVERFILE)),)
  DISTLOCALVERSION:=$(shell cat $(LOCVERFILE))
  $(info DISTLOCALVERSION is "$(DISTLOCALVERSION)". Update '$(shell dirname $(REDHAT))/localversion' to change.)
else
  ifeq ($(origin BUILDID),undefined)
    ifeq ($(DISTLOCALVERSION),)
      DISTLOCALVERSION:=.test
    endif
  else
    # Do NOT drop the ability to use BUILDID! Keep backwards compatibility to be
    # able to build all RHEL kernels the same way.
    DISTLOCALVERSION:=$(BUILDID)
  endif
  $(info DISTLOCALVERSION is "$(DISTLOCALVERSION)".)
endif

# options for process_configs.sh script
ifdef NO_CONFIGCHECKS
   PROCESS_CONFIGS_OPTS=
   PROCESS_CONFIGS_CHECK_OPTS=
   BUILDOPTS += -configchecks
else
   PROCESS_CONFIGS_CHECK_OPTS=-n -t -c
   PROCESS_CONFIGS_OPTS=-n -w -c
endif

# this section is needed in order to make O= to work
_OUTPUT := ..
ifeq ("$(origin O)", "command line")
  _OUTPUT := $(O)
  _EXTRA_ARGS := O=$(_OUTPUT)
endif

# MARKER is the upstream git tag which we base off of for exporting patches.
# MARKER (and UPSTREAM_TARBALL_NAME) must use SPECKVERSION, SPECKPATCHLEVEL,
# SPECKEXTRAVERSION, and SPECKSUBLEVEL from the top-level kernel makefile as
# opposed to any adjusted version for snapshotting.
ifneq ($(SPECKEXTRAVERSION),)
  UPSTREAMBUILD:=0$(shell echo $(SPECKEXTRAVERSION) | sed -e s/-/./).
  UPSTREAM_TARBALL_NAME:=$(SPECKVERSION).$(SPECKPATCHLEVEL)$(SPECKEXTRAVERSION)
else
  ifeq ($(SPECKSUBLEVEL),0)
    UPSTREAM_TARBALL_NAME:=$(SPECKVERSION).$(SPECKPATCHLEVEL)
  else
    # MARKER (and UPSTREAM_TARBALL_NAME) must use SPECKVERSION,
    # SPECKPATCHLEVEL, and SPECKSUBLEVEL from the top-level kernel makefile as
    # opposed to any adjusted version for snapshotting.  IOW, these variables are
    # *NOT* equivalent to the SPECVERSION variable.
    UPSTREAM_TARBALL_NAME:=$(SPECKVERSION).$(SPECKPATCHLEVEL).$(SPECKSUBLEVEL)
  endif
  UPSTREAMBUILD:=
endif
MARKER:=v$(UPSTREAM_TARBALL_NAME)

# If VERSION_ON_UPSTREAM is set, the versioning of the rpm package is based
# on a branch tracking upstream. This allows for generating rpms
# based on untagged releases.
ifndef VERSION_ON_UPSTREAM
  ifeq ("$(DISTRO)", "fedora")
    VERSION_ON_UPSTREAM:=1
  else
    VERSION_ON_UPSTREAM:=0
  endif
endif

UPSTREAM:=$(shell $(GIT) rev-parse -q --verify origin/$(UPSTREAM_BRANCH) || \
            $(GIT) rev-parse -q --verify $(UPSTREAM_BRANCH))

ifeq ($(VERSION_ON_UPSTREAM),1)
  # UPSTREAM_BRANCH is expected to track mainline.
  ifeq ($(UPSTREAM),)
      $(error "Missing an $(UPSTREAM_BRANCH) branch")
  endif
  MERGE_BASE:=$(shell $(GIT) merge-base $(HEAD) $(UPSTREAM))
  _TAG:=$(shell $(GIT) describe $(MERGE_BASE))
  # a snapshot off of a tagged git is of the form [tag]-[cnt]-g[hash]
  SNAPSHOT:=$(shell echo $(_TAG) | grep -c '\-g')

  ifeq ($(SNAPSHOT),1)
    # The base for generating tags is the snapshot commit
    MARKER:=$(shell echo $(_TAG) | awk -F "-g" '{ print $$2 }')
    # The merge window is weird because the actual versioning hasn't
    # been updated but we still need something that works for
    # packaging. Fix this by bumping the patch level and marking
    # this as rc0
    ifeq ($(SPECKEXTRAVERSION),)
      UPSTREAMBUILD:=0.rc0.
      SPECKPATCHLEVEL:=$(shell expr $(SPECKPATCHLEVEL) + 1)
    endif
    ifndef UPSTREAMBUILD_GIT_ONLY
      ifneq ($(filter $(MAKECMDGOALS),dist-git-test dist-git),)
        UPSTREAMBUILD_GIT_ONLY:=0
      else
        UPSTREAMBUILD_GIT_ONLY:=1
      endif
    endif
    ifeq ($(UPSTREAMBUILD_GIT_ONLY),1)
      UPSTREAMBUILD:=$(UPSTREAMBUILD)$(MARKER).
    else
      # Obtain the date that HEAD was committed (not the snapshot commit).
      HEAD_DATE:=$(shell $(GIT) show -s --format=%cd --date=format:%Y%m%d $(HEAD))
      UPSTREAMBUILD:=$(UPSTREAMBUILD)$(HEAD_DATE)git$(MARKER).
    endif
    UPSTREAM_TARBALL_NAME:=$(patsubst v%,%,$(_TAG))
  endif
else
  SNAPSHOT:=0
  ifneq ($(ADD_COMMITID_TO_VERSION),)
    _EXACT_TAG:=$(shell $(GIT) describe --exact-match 2>/dev/null)
    ifeq ($(_EXACT_TAG),)
      _TAG:=$(shell $(GIT) describe 2>/dev/null)
      ifneq ($(_TAG),)
        _BUILDCOMMIT:=$(shell echo $(_TAG) | awk -F- '{ printf(".%s", $$(NF)) }' | cut -c 1-6)
        BUILD:=$(BUILD)$(_BUILDCOMMIT)
      endif
    endif
  endif
endif

# This section contains the variables that represent the kernel rpm's NVR.
# The NVR looks like, for example, kernel-5.17.0-0.rc8.551acdc3c3d2.124.test.fc35.
# This string can be deconstructed as
#
# $(PACKAGE_NAME)-$(SPECKVERSION).$(SPECKPATCHLEVEL).$(SPECKSUBLEVEL)-$(UPSTREAMBUILD)$(BUILD)$(DISTLOCALVERSION)$(DIST)
#
# This can be evaluated as
#
# $(PACKAGE_NAME)-$(SPECKVERSION).$(SPECKPATCHLEVEL).$(SPECKSUBLEVEL)-$(SPECBUILD)          $(DIST)
# $(PACKAGE_NAME)-$(SPECVERSION)                                     -$(SPECBUILD)          $(DIST)
# $(PACKAGE_NAME)-$(BASEVERSION)                                                            $(DIST)
# $(RELEASETAG)                                                                             $(DIST)
#
SPECBUILD:=$(UPSTREAMBUILD)$(BUILD)$(DISTLOCALVERSION)
SPECVERSION:=$(SPECKVERSION).$(SPECKPATCHLEVEL).$(SPECKSUBLEVEL)
BASEVERSION:=$(SPECVERSION)-$(SPECBUILD)
RELEASETAG:=$(PACKAGE_NAME)-$(BASEVERSION)
SRPM:=$(SRPMS)/$(RELEASETAG)$(DIST).src.rpm

#
# This conditional statement is where fedora, centos, and other (aka RHEL)
# specific values should be set.
#
ifeq ("$(DISTRO)", "fedora")
  RHDISTGIT_BRANCH:=rawhide
  ifndef BUILD_TARGET
    BUILD_TARGET:=rawhide
  endif
  # The Fedora tarfile name is based on an upstream tag as users may
  # replace the tarball from one with upstream, rebuild, and then deploy
  # without changing anything else in the specfile.
  SPECTARFILE_RELEASE:=$(UPSTREAM_TARBALL_NAME)
  SPECKABIVERSION:=$(SPECVERSION)
  DISTRELEASETAG:=$(RELEASETAG)
  DISTBASEVERSION:=$(BASEVERSION)
else ifeq ("$(DISTRO)", "centos")
  RHDISTGIT_BRANCH:=c$(RHEL_MAJOR)s
  ifndef BUILD_PROFILE
    BUILD_PROFILE:= -p stream
  endif
  ifndef BUILD_TARGET
    BUILD_TARGET:=c$(RHEL_MAJOR)s-candidate
  endif
  SPECTARFILE_RELEASE:=$(BASEVERSION)$(DIST)
  SPECKABIVERSION:=$(BASEVERSION)$(DIST)
  DISTRELEASETAG:=$(RELEASETAG)$(DIST)
  DISTBASEVERSION:=$(BASEVERSION)$(DIST)
  PATCHLIST_URL:=none
else
  RHDISTGIT_BRANCH:=rhel-$(RHEL_MAJOR).$(RHEL_MINOR).0
  ifndef BUILD_TARGET
    ifeq ("$(DIST)", ".eln")
      BUILD_TARGET:=eln
    else
      # This value is used by the dist[g]-targets.  Changing this value has significant
      # consequences for all of RHEL kernel engineering.
      BUILD_TARGET:=rhel-$(RHEL_MAJOR).$(RHEL_MINOR).0-test-pesign
    endif
  endif
  ifeq ("$(DIST)", ".eln)
    DISTRELEASETAG:=$(RELEASETAG)
    DISTBASEVERSION:=$(BASEVERSION)
    SPECTARFILE_RELEASE:=$(BASEVERSION)
    SPECKABIVERSION:=$(BASEVERSION)
  else
    DISTRELEASETAG:=$(RELEASETAG)$(DIST)
    DISTBASEVERSION:=$(BASEVERSION)$(DIST)
    SPECTARFILE_RELEASE:=$(BASEVERSION)$(DIST)
    SPECKABIVERSION:=$(BASEVERSION)$(DIST)
  endif
  PATCHLIST_URL:=none
endif

TARFILE:=linux-$(SPECTARFILE_RELEASE).tar.xz
TARBALL:=$(REDHAT)/$(TARFILE)

KABI_TARBALL:=$(SOURCES)/kernel-abi-stablelists-$(SPECKABIVERSION).tar.bz2
KABIDW := $(REDHAT)/kabi-dwarf
KABIDW_TARBALL:=$(SOURCES)/kernel-kabi-dw-$(SPECKABIVERSION).tar.bz2

# Taken from tools/lib/bpf/Makefile
BPFTOOLVERSION:=$(shell \
	grep -oE '^LIBBPF_([0-9.]+)' $(TOPDIR)/tools/lib/bpf/libbpf.map | \
	sort -rV | head -n1 | cut -d'_' -f2 | \
	awk -F. -v OFS=. '{$$1 += 6 ; print}')

include Makefile.rhpkg

ifeq ("$(ZSTREAM)", "yes")
  YSTREAM_FLAG = no
  ifeq ("$(origin RHDISTGIT_BRANCH)", "command line")
    ZSTREAM_FLAG = branch
  else
    ZSTREAM_FLAG = yes
  endif
  BUILDOPTS += +kabidupchk
else
  ZSTREAM_FLAG = no
  ifeq ("$(EARLY_YSTREAM)", "yes")
    YSTREAM_FLAG = early
  else
    YSTREAM_FLAG = yes
  endif
endif

include Makefile.cross

#
# Targets
#
# Do not place variable declarations below this line.  Variables are exported
# to scripts called in the targets below and do not need to be passed on the
# command-line.
#

default: dist-help

dist-python-check:
	@if [ ! -x /usr/bin/python3 ]; then \
		echo "ERROR: Python 3 is needed." ; \
		exit 1; \
	fi

dist-kabi: dist-python-check
	@for KABIARCH in $(ARCH_LIST); do \
		$(REDHAT)/kabi/show-kabi -k $(REDHAT)/kabi/kabi-module/ -m \
			-a $$KABIARCH -r $(RHEL_MAJOR).$(RHEL_MINOR) > $(REDHAT)/kabi/Module.kabi_$$KABIARCH;\
		for i in {0..$(RHEL_MINOR)}; do \
			mkdir -p $(REDHAT)/kabi/kabi-rhel$(RHEL_MAJOR)$$i/;\
			$(REDHAT)/kabi/show-kabi -k $(REDHAT)/kabi/kabi-module/ -s -a $$KABIARCH \
			-r $(RHEL_MAJOR).$$i > $(REDHAT)/kabi/kabi-rhel$(RHEL_MAJOR)$$i/kabi_stablelist_$$KABIARCH;\
		done;\
	done;
	@(cd $(REDHAT)/kabi/ && ln -Tsf kabi-rhel$(RHEL_MAJOR)$(RHEL_MINOR) kabi-current)

dist-kabi-dup: dist-python-check
	@for KABIARCH in $(ARCH_LIST); do \
		touch $(REDHAT)/kabi/Module.kabi_dup_$$KABIARCH;\
		if [ -d $(REDHAT)/kabi/kabi-dup-module/kabi_$$KABIARCH ]; then \
			$(REDHAT)/kabi/show-kabi -k $(REDHAT)/kabi/kabi-dup-module/ -m \
				-a $$KABIARCH -r $(RHEL_MAJOR).$(RHEL_MINOR) > \
				$(REDHAT)/kabi/Module.kabi_dup_$$KABIARCH;\
		fi \
	done;

dist-assert-tree-clean:
ifeq ($(FORCE),)
	@if ! git diff-index --quiet --cached HEAD -- &> /dev/null; then \
		echo "ERROR: staged changes found. Please clean the git tree."; >&2 \
		git status; \
		exit 1; \
	fi
	@if ! git diff-files --quiet &> /dev/null; then \
		echo "ERROR: unstaged changes found. Please clean the git tree." >&2; \
		git status; \
		exit 1; \
	fi
	@if [ $$(git ls-files --exclude-standard --others | wc -l) -gt 0 ]; then \
		echo "ERROR: untracked files found. Please clean the git tree." >&2; \
		git status; \
		exit 1; \
	fi
endif

KABI_SUPPORTED_ARCHS ?= $(patsubst kabi_%,%,$(notdir $(wildcard kabi/kabi-module/*)))
export KABI_CROSS_COMPILE_PREFIX ?= /usr/bin/
export KABI_CROSS_COMPILE_SUFFIX ?= -linux-gnu-
KABI_CROSS_COMPILE = $(patsubst %,$(KABI_CROSS_COMPILE_PREFIX)%$(KABI_CROSS_COMPILE_SUFFIX),$(filter-out $(CURARCH),$(KABI_SUPPORTED_ARCHS)))

ifeq ($(ARCH),$(CURARCH))
dist-assert-cross-tools: # no dependencies when we're building for native arch
else
dist-assert-cross-tools: $(patsubst %,%gcc,$(KABI_CROSS_COMPILE))
endif

$(KABI_CROSS_COMPILE_PREFIX)%$(KABI_CROSS_COMPILE_SUFFIX)gcc:
	@echo "ERROR: couldn't find cross compilation toolchain (looking for: $@)" >&2
	@echo "       override KABI_CROSS_COMPILE_PREFIX to set path (currently $(KABI_CROSS_COMPILE_PREFIX))" >&2
	@echo "       override KABI_CROSS_COMPILE_SUFFIX to set suffix (currently $(KABI_CROSS_COMPILE_SUFFIX))" >&2
	@exit 1


ifeq ($(ARCH),)
dist-kabi-index: ARCH=$(CURARCH)
endif
dist-kabi-index:
	: > $(REDHAT)/kabi/kabi-module/kabi_$(ARCH)/.index.json
	for sym in $$(find $(REDHAT)/kabi/kabi-module/kabi_$(ARCH)/ -type f -not -name "*.*" \
	                  -exec basename {} \;); do \
		$(REDHAT)/kabi/symtypes index \
			$(REDHAT)/kabi/kabi-module/kabi_$(ARCH)/.$$(basename $$sym) \
			-o $(REDHAT)/kabi/kabi-module/kabi_$(ARCH)/.index.json || : ; \
	done

ifeq ($(ARCH),)
dist-kabi-image-%: ARCH=$(CURARCH)
endif
dist-kabi-image-%: NODE = $(patsubst dist-kabi-image-%,%,$@)
dist-kabi-image-%: dist-kabi-index
	$(REDHAT)/kabi/symtypes image -s $(NODE) -t $(REDHAT)/kabi/kabi-module/kabi_$(ARCH)/.index.json

ifeq ($(ARCH),)
dist-kabi-preimage-%: ARCH=$(CURARCH)
endif
dist-kabi-preimage-%: NODE = $(patsubst dist-kabi-preimage-%,%,$@)
dist-kabi-preimage-%: dist-kabi-index
	@node="$(NODE)"; \
	if [ "${node:1:1}" = "#" ]; then \
		$(REDHAT)/kabi/symtypes preimage -s '$(NODE)' -t $(REDHAT)/kabi/kabi-module/kabi_$(ARCH)/.index.json; \
	else \
		for prefix in {E,e,s,t,u}; do \
		$(REDHAT)/kabi/symtypes preimage -S -s "$$prefix#$(NODE)" -t $(REDHAT)/kabi/kabi-module/kabi_$(ARCH)/.index.json || :; \
		done; \
	fi

dist-symtype-diff: KABI_TOOL = $(REDHAT)/kabi/diff-kabi
dist-symtype-diff: dist-assert-cross-tools dist-assert-tree-clean dist-configs dist-symtype-shared

dist-kabi-update: KABI_TOOL = $(REDHAT)/kabi/update-kabi
dist-kabi-update: dist-assert-cross-tools dist-assert-tree-clean dist-configs dist-symtype-shared

dist-symtype-shared:
	@declare -a _ARGS; \
	declare -a _ARCHS; \
	for symbol in $${SYMBOL:-}; do \
		_ARGS=("$${_ARGS[@]}" -s "$$symbol"); \
	done; \
	if [ -n "$${SRC:-}" ]; then \
		_ARGS=("$${_ARGS[@]}" $$SRC); \
	fi; \
	if [ -n "$${ARCH:-}" ]; then \
		$(KABI_TOOL) -a $(ARCH) $${_ARGS[@]}; \
	else \
		cnt=1; \
		for arch in $(KABI_SUPPORTED_ARCHS); do \
			$(KABI_TOOL) -a $$arch $${_ARGS[@]} || : ; \
			let cnt++; \
		done; \
	fi

dist-check-kabi: dist-kabi
	@if [ ! -e $(_OUTPUT)/Module.symvers ]; then \
		echo "ERROR: You must compile the kernel and modules first";\
		exit 1;\
	fi
	@$(REDHAT)/kabi/check-kabi -k $(REDHAT)/kabi/Module.kabi_$(MACH) \
	 -s $(_OUTPUT)/Module.symvers

dist-check-kabi-dup: dist-kabi-dup
	@if [ ! -e $(_OUTPUT)/Module.symvers ]; then \
		echo "ERROR: You must compile the kernel and modules first";\
		exit 1;\
	fi
	@$(REDHAT)/kabi/check-kabi -k $(REDHAT)/kabi/Module.kabi_dup_$(MACH) \
	-s $(_OUTPUT)/Module.symvers

dist-kabi-dw-base: dist-kabi
	@echo "Generating baseline dataset for KABI DWARF-based comparison..."
	@echo "**** GENERATING DWARF-based kABI baseline dataset ****"
	@$(KABIDW)/run_kabi-dw.sh generate \
		$(REDHAT)/kabi/kabi-current/kabi_stablelist_$(CURARCH) \
		$(_OUTPUT) $(KABIDW)/base/$(CURARCH)/

dist-kabi-dw-check: dist-kabi
	@if [ ! -d $(KABIDW)/base/$(CURARCH) ]; then \
		echo "**** ERROR: ****"; \
		echo "Comparison base not found in $(KABIDW)/base/$(CURARCH)."; \
		echo "Please run \"make dist-kabi-dw-base\" first!"; \
		exit 1; \
	fi
	@echo "**** GENERATING DWARF-based kABI dataset ****"
	@$(KABIDW)/run_kabi-dw.sh generate \
		$(REDHAT)/kabi/kabi-current/kabi_stablelist_$(CURARCH) \
		$(_OUTPUT) $(KABIDW)/base/$(CURARCH).tmp/
	@echo "**** KABI DWARF-based comparison report ****"
	@$(KABIDW)/run_kabi-dw.sh compare \
		$(KABIDW)/base/$(CURARCH) $(KABIDW)/base/$(CURARCH).tmp || :
	@echo "**** End of KABI DWARF-based comparison report ****"
	@rm -rf $(KABIDW)/base/$(CURARCH).tmp

dist-configs-commit: dist-configs-prep
	+@cd $(REDHAT)/configs; ./generate_all_configs.sh 1;\
	./process_configs.sh -z "$(SPECVERSION)" "$(FLAVOR)"

dist-configs: dist-configs-prep
	+@cd $(REDHAT)/configs; ./generate_all_configs.sh 1;\
	./process_configs.sh $(PROCESS_CONFIGS_OPTS) "$(SPECVERSION)" ""

dist-fedora-configs: FLAVOR = fedora
dist-fedora-configs: dist-configs
fedora-configs: dist-fedora-configs

dist-rhel-configs: FLAVOR = rhel
dist-rhel-configs: dist-configs
rh-configs: dist-rhel-configs

dist-configs-check: dist-configs-prep
	+cd $(REDHAT)/configs; ./process_configs.sh $(PROCESS_CONFIGS_CHECK_OPTS) "" ""

dist-configs-prep: dist-clean-configs
	+cd $(REDHAT)/configs; ./build_configs.sh "partial" "snip"
	+cd $(REDHAT)/configs; ./build_configs.sh "$(PACKAGE_NAME)" "$(FLAVOR)"

dist-configs-arch: ARCH_MACH = $(MACH)
dist-configs-arch: dist-configs

dist-clean-configs:
	@cd $(REDHAT)/configs; rm -f kernel-*.config kernel-*.config.orig kernel-*.config.tmp

dist-clean-sources:
	@rm -f $(RPM)/SPECS/*
	@for i in $(SOURCES)/*; do \
		rm -f $$i; \
	done;

dist-clean-rpmdirs:
	@for i in $(RPM)/{BUILD,SRPMS,RPMS,SPECS}/*; do \
		rm -rf $$i; \
	done;

dist-clean: dist-clean-sources dist-clean-configs dist-clean-rpmdirs
	@rm -f $(REDHAT)/linux-*.tar.xz

dist-stub-key:
	@echo "Copying pre-generated keys";
	@echo "*** THIS IS NOT RECOMMENDED ***";
	@echo "To be safe, keys should be created once for every build";
	@echo "Use this option only for development builds";
	@cp keys/stub_key.x509 $(_OUTPUT)/;
	@cp keys/stub_key.priv $(_OUTPUT)/;

# force tarball to be regenerated if HEAD changes
.PHONY:	$(TARBALL)
$(TARBALL):
	@scripts/create-tarball.sh

.PHONY: $(KABI_TARBALL)
$(KABI_TARBALL):
	@(cd kabi && tar cjf $(KABI_TARBALL) kabi-rhel$(RHEL_MAJOR)* kabi-current)

.PHONY: $(KABIDW_TARBALL)
$(KABIDW_TARBALL):
	@if [ ! -d $(KABIDW)/base ]; then \
		mkdir -p $(KABIDW)/base; \
	fi
	@(cd kabi-dwarf && tar cjf $(KABIDW_TARBALL) base run_kabi-dw.sh)

dist-git-version-check:
	@# genspec.sh uses pathspec magic that wasn't introduced until version 2.13
	@IFS=" ."; \
	set -- $$($(GIT) --version); \
	IFS=; \
	if [ "$$3" -lt 2 -o \( "$$3" -eq 2 -a "$$4" -lt 13 \) ]; then \
		echo "ERROR: You need git version 2.13 or newer to run some setup commands"; \
		exit 1; \
	fi

dist-get-buildreqs: setup-source
	@PKGLIST="rpm-build $$(rpmspec -q --buildrequires $(SOURCES)/$(SPECFILE) | cut -d ' ' -f 1)"; \
	MISSING=""; \
	for pkg in $$PKGLIST; do \
		rpm -q --whatprovides $$pkg >/dev/null || MISSING="$$MISSING $$pkg"; \
	done; \
	if [ -n "$$MISSING" ]; then \
		echo " Missing dependencies: $$MISSING"; \
		if  echo "$$MISSING" | grep -q system-sb-certs ; then \
			echo "system-sb-certs can be installed from a RHEL or Centos-Stream CodeReady Linux Builder (CRB) repository."; \
		fi; \
	else \
		echo "PASS: All build dependencies found."; \
	fi

_setup-source: dist-git-version-check
	@cp $(REDHAT)/$(SPECFILE).template $(SOURCES)/$(SPECFILE)
	@if [ ! -e  $(REDHAT)/$(SPECCHANGELOG) ]; then \
		echo "Creating $(SPECCHANGELOG) as copy of $(CHANGELOG_PREV)"; \
		cp $(REDHAT)/$(CHANGELOG_PREV) $(REDHAT)/$(SPECCHANGELOG); \
	fi
	@if [ -z "$(RHSELFTESTDATA)" ]; then \
		cp $(REDHAT)/$(SPECCHANGELOG) $(SOURCES)/$(SPECCHANGELOG); \
	else \
		echo "Mon Mar 28 2022 Fedora Kernel Team <kernel-team@fedoraproject.org> [$(BASEVERSION)]" > $(SOURCES)/$(SPECCHANGELOG); \
	fi
	@if [ -z "$(PATCHLIST_URL)" ]; then \
		echo "Error: PATCHLIST_URL must be set (to 'none' or any URL)"; \
		exit 1; \
	fi
	@$(REDHAT)/genspec.sh
	@cp $(SOURCES)/$(SPECFILE) $(SOURCES)/../SPECS/

setup-source: dist-clean-sources _setup-source

generate-testpatch-tmp:
	@$(GIT) diff --no-renames HEAD ":(exclude,top).get_maintainer.conf" \
		":(exclude,top).gitattributes" \
		":(exclude,top).gitignore" \
		":(exclude,top)makefile" \
		":(exclude,top)Makefile.rhelver" \
		":(exclude,top)redhat" > $(TESTPATCH).tmp

sources-rh: $(TARBALL) generate-testpatch-tmp setup-source dist-configs-check
	@cp -l $(TARBALL) $(SOURCES)/ || cp $(TARBALL) $(SOURCES)/
	@touch $(TESTPATCH)
	@diff $(TESTPATCH).tmp $(TESTPATCH) > /dev/null || \
		echo "WARNING: There are uncommitted changes in your tree or the changes are not in sync with linux-kernel-test.patch.  Either commit the changes or run 'make dist-test-patch'"
	@rm $(TESTPATCH).tmp
	@cp $(TESTPATCH) $(SOURCES)/linux-kernel-test.patch
	@cat configs/flavors | while read flavor; do echo "Copying sources for $${flavor}"; [ -e $${flavor}_files ] && cp $${flavor}_files/* $(SOURCES); done
	@sed -e "s/%%SPECKVERSION%%/$(SPECKVERSION)/" \
		-e "s/%%SPECKPATCHLEVEL%%/$(SPECKPATCHLEVEL)/" \
		rpminspect.yaml > $(SOURCES)/rpminspect.yaml
	@cp cpupower.* \
		keys/rhel*.x509 \
		keys/nvidia*.x509 \
		kabi/check-kabi \
		configs/$(PACKAGE_NAME)-*.config \
		configs/partial*.config \
		gating.yaml \
		update_scripts.sh \
		kvm_stat.logrotate \
		mod-denylist.sh \
		mod-internal.list \
		mod-partner.list \
		mod-kvm.list \
		mod-sign.sh \
		configs/flavors \
		configs/generate_all_configs.sh \
		configs/merge.pl \
		configs/process_configs.sh \
		parallel_xz.sh \
		../Makefile.rhelver \
		README.rst \
		kernel-local \
		dracut-virt.conf \
		$(SOURCES)/
	@for KABIARCH in $(ARCH_LIST); do \
		cp kabi/Module.kabi_$$KABIARCH $(SOURCES)/; \
		cp kabi/Module.kabi_dup_$$KABIARCH $(SOURCES)/; \
	done
	@(cd kabi && tar cjf $(KABI_TARBALL) kabi-rhel$(RHEL_MAJOR)* kabi-current)
	@if [ ! -d $(KABIDW)/base ]; then \
		mkdir -p $(KABIDW)/base; \
	fi
	@(cd kabi-dwarf && tar cjf $(KABIDW_TARBALL) base run_kabi-dw.sh)

dist-sources: dist-kabi dist-kabi-dup sources-rh

dist-test-patch: generate-testpatch-tmp
	@mv $(TESTPATCH).tmp $(TESTPATCH);

do-rpmbuild: dist-sources
	$(RPMBUILD) --define "_sourcedir $(SOURCES)" --define "_builddir $(RPM)/BUILD" --define "_srcrpmdir $(RPM)/SRPMS" --define "_rpmdir $(RPM)/RPMS" --define "_specdir $(RPM)/SPECS" --define "dist $(DIST)" $(RPMBUILDOPTS) $(RPM)/SOURCES/$(SPECFILE)

dist-all-rpms: RPMBUILDOPTS=--target $(MACH) -ba
dist-all-rpms: dist-sources do-rpmbuild

dist-srpm: RPMBUILDOPTS=--nodeps -bs
dist-srpm: dist-sources do-rpmbuild

dist-srpm-gcov: DISTLOCALVERSION=.gcov
dist-srpm-gcov: BUILDOPTS+=+gcov
dist-srpm-gcov: dist-srpm

dist-rpms: RPMBUILDOPTS=--target $(MACH) -bb
dist-rpms: dist-sources do-rpmbuild

dist-kernel-%: dist-sources
	RPMBUILDOPTS="--target $(MACH) --with $* -bb" make do-rpmbuild

dist-prep: RPMBUILDOPTS=--nodeps --target noarch -bp
dist-prep: dist-sources do-rpmbuild

dist-perf: RPMBUILDOPTS=--without up --without smp --without zfcpdump --without debug --without doc --without headers --without doc --without debuginfo --target $(MACH) -bb
dist-perf: dist-sources do-rpmbuild

dist-rpm-baseonly: RPMBUILDOPTS=--target $(MACH) --without debug --without debuginfo --without vdso_install --without bpftool --without perf --without tools -bb
dist-rpm-baseonly: dist-sources do-rpmbuild

# unless you know what you're doing, you don't want to use the next four ones
dist-release-finish: setup-source
	@cp $(SOURCES)/$(SPECCHANGELOG) $(REDHAT)/$(SPECCHANGELOG)
	@echo $(MARKER) > $(REDHAT)/marker
	@$(GIT) add $(REDHAT)/$(SPECCHANGELOG)
	@$(GIT) add $(REDHAT)/marker
	@$(GIT) commit -s ../Makefile.rhelver $(REDHAT)/marker $(REDHAT)/$(SPECCHANGELOG) $(SPECFILE).template -m "[redhat] $(DISTRELEASETAG)"
dist-release-changed:
	@CLOGF="$$(mktemp)"; \
	trap 'rm -f "$$CLOGF"' SIGHUP SIGINT SIGTERM EXIT; \
	$(REDHAT)/genlog.sh "$$CLOGF"; \
	if [ "$(MARKER)" == "$$(cat $(REDHAT)/marker)" ] && \
	   [ "$$(wc -l $$CLOGF | cut -d ' ' -f 1)" -le 3 ]; then \
		echo "Nothing changed, skipping updates"; \
	else \
		$(REDHAT)/scripts/new_release.sh; \
		$(MAKE) dist-release-finish; \
	fi

dist-release: dist-clean-sources
	@$(MAKE) dist-release-changed

dist-release-tag:
	@$(GIT) tag -a -m "$(DISTRELEASETAG)" $(DISTRELEASETAG)

git-tree-check:
	@if test -n "$(DIST_PUSH)" && test -z "$(shell $(GIT) remote get-url gitlab 2>/dev/null)"; then \
		echo -e "Please run 'git remote add gitlab <url>' to enable git-push.\n"; \
		exit 1; \
	fi
	@$(GIT) diff-index --quiet HEAD || \
		{ echo -e "Dirty tree, please clean before merging.\n"; exit 1; }

dist-merge-upstream: git-tree-check
	@if test "$(shell $(GIT) branch --show-current)" != "$(DIST_BRANCH)"; then \
		echo -e "Please checkout $(DIST_BRANCH) branch before merging.\n"; \
		exit 1; \
		fi;

	@# If TAG is empty, script defaults to master:HEAD
	@$(GIT) checkout $(DIST_BRANCH)
	@cd ..; $(REDHAT)/scripts/ci/ark-update-configs.sh $(TAG)

dist-merge-upstream-push: export DIST_PUSH="1"
dist-merge-upstream-push: dist-merge-upstream

dist-fedora-release: git-tree-check

	@# If TAG is empty, script defaults to master:HEAD
	@cd ..; $(REDHAT)/scripts/ci/ark-create-release.sh $(TAG) || \
		(echo "Unable to create release tag"; exit 1)

dist-fedora-release-push: export DIST_PUSH="1"
dist-fedora-release-push: dist-fedora-release

dist-vr-check:
	@# builds may include a s390x+zfcpdump arch build.  UTS_RELEASE can only have a
	@# version-release string with max 64 chars.  The version-release for s390x+zfcpdump
	@# is 29 characters, leaving a maximum of 35 characters for SPECBUILD.
	@if [ $$(echo -n $(SPECBUILD) | wc -c) -gt 35 ]; then \
		echo "SPECBUILD ($(SPECBUILD)) is too long.  Use a shorter localversion (currently $(DISTLOCALVERSION))"; \
		exit 1; \
	fi

dist-brew: DIST=.el9
dist-brew: DISTRO=rhel
dist-brew dist-koji: dist-%: dist-vr-check dist-srpm
	$* $(BUILD_PROFILE) build $(BUILD_FLAGS) --scratch $(BUILD_TARGET) $(SRPMS)/$(RELEASETAG)$(DIST).src.rpm $(OUTPUT_FILE)

distg-brew: DIST=.el9
distg-brew: DISTRO=rhel
distg-brew distg-koji: distg-%: dist-vr-check
	$* $(BUILD_PROFILE) build $(BUILD_FLAGS) --scratch $(BUILD_TARGET) "$(RHGITURL)?redhat/koji#$(RHGITCOMMIT)"

.PHONY: $(REDHAT)/rpm/SOURCES/$(SPECFILE)
$(REDHAT)/rpm/SOURCES/$(SPECFILE):
	@echo "dist-sources"
	@$(MAKE) dist-sources

dist-git-test: export RH_DIST_GIT_TEST="1"
dist-git-test: dist-git

dist-git: dist-srpm $(KABI_TARBALL) $(KABIDW_TARBALL)
ifeq ("$(RHDISTGIT_BRANCH)", "")
 $(error RHDISTGIT_BRANCH unset)
endif
	$(REDHAT)/scripts/rh-dist-git.sh

dist-rtg: dist-release
	@$(MAKE) dist-release-tag
	@$(MAKE) dist-git

# RH_LATEST returns the value of the latest "known good" kernel from brew.
# This should not be confused with the latest top-of-tree development tag.
dist-get-latest:
	$(eval RH_LATEST:=$(shell brew latest-pkg --quiet rhel-${RHEL_MAJOR}.${RHEL_MINOR}.0-candidate kernel | awk ' { print $$1 } '))
	@echo "The latest kernel package tag is ${RH_LATEST}."

dist-os-version:
	@echo "OSVERSION: $(RHEL_MAJOR).$(RHEL_MINOR)"

dist-dump-variables:
	$(eval VARS:=$(sort $(shell cat Makefile.variables | sed '/^#/d; /^$$/d; s/[ ]*[?:]=.*//')))
	@$(foreach V,$(sort $(.VARIABLES)), $(if $(filter-out environment default automatic, $(origin $V)),$(info $V=$($V) ),$(if $(filter $(VARS),$(V)),$(info $V=$($V)))))

dist-self-test:
	@if test -x /usr/bin/bats; then \
		RHEL_MAJOR=$(RHEL_MAJOR) RHEL_MINOR=$(RHEL_MINOR) bats $(REDHAT)/self-test/*.bats ; \
	else \
		echo "dist-self-test: The bats package is not installed" ; \
	fi

dist-self-test-data:
	./self-test/data/create-data.sh

dist-check-licenses:
	@if test -x /usr/bin/bats; then \
		bats $(REDHAT)/self-test/1007-spdx-licenses.bats ; \
	else \
		echo "dist-check-licenses: The bats package is not installed" ; \
	fi

dist-help:
	@echo  'Cleaning targets:'
	@echo  '  dist-clean          - Clean redhat/configs/ and redhat/rpm/ directories.'
	@echo  ''
	@echo  'Building targets:'
	@echo  '  dist-srpm           - Create a source RPM.'
	@echo  '  dist-all-rpms       - Create a source RPM and build binary RPMs locally.'
	@echo  '  dist-brew           - Create a source RPM and call brew to build binary RPMs.'
	@echo  '  distg-brew          - Build RPMs using a remote git repo.'
	@echo  '                        [Configuration needed.]'
	@echo  '  dist-cross-all-rpms - Build RPMs for all supported archs using a cross'
	@echo  '                        compiler.'
	@echo  ''
	@echo  'Configuration targets:'
	@echo  '  dist-configs        - Create RHEL config files in redhat/config/.'
	@echo  ''
	@echo  'For detailed description and full list of targets, run `make dist-full-help`.'
	@echo  ''

dist-full-help:
	@echo  'Cleaning targets:'
	@echo  '  dist-clean            - Do dist-clean-sources, dist-clean-configs, &'
	@echo  '                          dist-clean-rpmdirs.'
	@echo  '  dist-clean-sources    - Clean the redhat/rpm/SOURCES/ directory.'
	@echo  '  dist-clean-configs    - Clean the redhat/configs/ directory.'
	@echo  '  dist-clean-rpmdirs    - Clean the redhat/rpm/{BUILD,SRPMS,RPMS,SPECS}/'
	@echo  '                          directories.'
	@echo  ''
	@echo  'Building targets:'
	@echo  ' All RPM/SRPM files will be put under the redhat/rpm/ directory.'
	@echo  ''
	@echo  '  dist-srpm       - Create a source RPM and put it into the redhat/rpm/SRPMS/'
	@echo  '                    directory.  See the dist-brew target for available options.'
	@echo  '  dist-srpm-gcov  - Create a source RPM with gcov enabled and put it into the'
	@echo  '                    redhat/rpm/SRPMS/ directory.'
	@echo  '  dist-brew       - Create a kernel SRPM and then call brew to build the'
	@echo  '                    created SRPM.  Add BUILDOPTS="+<opt> -<opt> [...]" to'
	@echo  '                    enable/disable build options.'
	@echo  '                    Available <opt>s and their default values:' \
		$$(sed -n -e 's/^%define with_\([^ \t]*\).*\?_without_.*/+\1/p' \
		          -e 's/^%define with_\([^ \t]*\).*\?_with_.*/-\1/p' kernel.spec.template | \
		grep -v 'only$$') | fmt -80
	@echo  '  dist-koji       - Create a kernel SRPM and then call koji to build the'
	@echo  '                    created SRPM.  See the dist-brew target for available'
	@echo  '                    options.'
	@echo  '  distg-brew      - Pass HEAD of the current git branch to brew to build an'
	@echo  '                    RPM set.  Do not forget to push to the remote repository'
	@echo  '                    first.  Preceed make command by RHGITCOMMIT=<commitID>'
	@echo  '                    specify commit ID to use.'
	@echo  '                    To set the remote repo, invoke:'
	@echo  '                         git config rhg.url git://<repo_path>'
	@echo  '  distg-koji      - Pass HEAD of the current git branch to koji to build an'
	@echo  '                    RPM set.  Do not forget to push to the remote repository'
	@echo  '                    first.  See the distg-brew target for options and'
	@echo  '                    configuration.'
	@echo  '  dist-rpms       - Create the binary RPMS for the kernel.'
	@echo  '                    See the dist-brew target for available options.'
	@echo  '  dist-rpm-baseonly  - Create the binary RPMS for the kernel and modules'
	@echo  '                       (no userspace tools or debuginfo).'
	@echo  '  dist-kernel-<type> - Create  binary RPMS for a particular kernel type.'
	@echo  '                       Available <type>s:'\
		$$(sed -n 's/^%define with_\([^ ]*only\).*/\1/p' kernel.spec.template)

	@echo  '  dist-all-rpms   - Create the binary RPMS and the SRPM for the kernel.'
	@echo  '                    See the dist-brew target for available options.'
	@echo  '  dist-prep       - Setup the redhat/rpm/BUILD/ directory with the kernel'
	@echo  '                    source.  See the dist-brew target for available options.'
	@echo  '  dist-test-patch - Create a diff against HEAD and put it in'
	@echo  '                    linux-kernel-test.patch.  This patch will'
	@echo  '                    be added to the kernel build.'
	@echo  '  dist-stub-key   - Use pre generated keys to speed local test builds.'
	@echo  '  dist-cross-download     - [x86_64 only] download cross compiler rpms.'
	@echo  '  dist-cross-all-builds   - [x86_64 only] execute "rpmbuild -bc" for all'
	@echo  '                            supported archs using RHEL cross compiler.'
	@echo  '  dist-cross-<arch>-build - [x86_64 only] execute "rpmbuild -bc" for specified'
	@echo  '                            <arch> using RHEL cross compiler.'
	@echo  '                            Supported <arch>s: x86_64'\
		$$(sed -n 's/.*--target \([^ ]*\).*/\1/p' Makefile.cross | sort -u)
	@echo  '  dist-cross-all-rpms     - [x86_64 only] execute rpm builds for all supported'
	@echo  '                            archs using RHEL cross compiler.'
	@echo  '  dist-cross-<arch>-rpms  - [x86_64 only] execute rpm builds for specified'
	@echo  '                            <arch> using RHEL cross compiler.'
	@echo  '                            See dist-cross-<arch>-build for the supported archs.'
	@echo  '  dist-rhel-configs       - build ELN configs'
	@echo  '  dist-fedora-configs     - build Fedora configs'

	@echo  ''
	@echo  'kABI targets:'
	@echo  '  dist-kabi           - Create kABI stablelist files in redhat/kabi/kabi-rhel*/'
	@echo  '                        and merge kABI checksums into redhat/kabi/Module.kabi_*.'
	@echo  '  dist-kabi-dup       - Merge kABI checksums for Driver Update Program (DUP)'
	@echo  '                        into redhat/kabi/Module.kabi_dup_*.'
	@echo  '  dist-check-kabi     - Check for changes in kABI stablelisted symbols.'
	@echo  '                        Requires a pre-compiled tree: run `make dist-configs`,'
	@echo  '                        copy the relevant config file from redhat/configs/ to'
	@echo  '                       .config, and run `make`.'
	@echo  '  dist-check-kabi-dup - Like dist-check-kabi but uses a DUP kABI stablelist.'
	@echo  '  dist-kabi-dw-base   - Generate the base dataset for kABI DWARF-based check.'
	@echo  '  dist-kabi-dw-check  - Run DWARF-based kABI comparison of current binaries'
	@echo  '                        with the base dataset.'
	@echo  '  dist-kabi-update    - Update kabi stablelist checksums.'
	@echo  '  dist-symtype-diff   - Diff kabi stablelist and current kernel.'

	@echo  ''
	@echo  'Configuration targets:'
	@echo  '  dist-configs  - Creates config files for RHEL $(RHEL_MAJOR) architectures,'
	@echo  '                  cleans them by running make nonint_oldconfig, and copies'
	@echo  '                  them to redhat/configs/ directory. This is the target to use'
	@echo  '                  for a config!  Copy the config file you want from the'
	@echo  '                  redhat/configs/ directory to .config'
	@echo  '  dist-configs-arch  - Same as dist-configs but for single architecture only.'

	@echo  ''
	@echo  'Misc targets:'
	@echo  '  dist-get-buildreqs - returns list of packages listed as build requirements'
	@echo  '                       for this kernel'
	@echo  '  dist-get-latest - Returns the latest "known good" kernel from brew. This'
	@echo  '                    should not be confused with the latest top-of-tree'
	@echo  '                    development tag.'
	@echo  '  dist-os-version - Displays the current Red Hat Enterprise Linux versioni'
	@echo  '                    target used by the current branch/tree.'
	@echo  '  dist-self-test  - Runs self-tests from the redhat/self-test directory'
	@echo  '  dist-check-licenses - Runs license selftest checking SPDX-License-Identifier:'
	@echo  '                        tags in all source files against `License:` field in the'
	@echo  '                        specfile template.'
	@echo  ''

export
