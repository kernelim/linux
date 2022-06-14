include Makefile.common
include Makefile.rhpkg

LANG=C

ifeq ("$(ZSTREAM)", "yes")
  __YSTREAM = no
  ifeq ("$(origin RHDISTGIT_BRANCH)", "command line")
    __ZSTREAM = branch
  else
    __ZSTREAM = yes
  endif
  BUILDOPTS += +kabidupchk
else
  __ZSTREAM = no
  ifeq ("$(EARLY_YSTREAM)", "yes")
    __YSTREAM = early
  else
    __YSTREAM = yes
  endif
endif

ifeq ("$(NO_CONFIGCHECKS)","1")
   PROCESS_CONFIGS_OPTS=
   PROCESS_CONFIGS_CHECK_OPTS=
   BUILDOPTS += -configchecks
else
   PROCESS_CONFIGS_CHECK_OPTS=-n -t -c
   PROCESS_CONFIGS_OPTS=-n -w -c
endif

BUILD_TARGET ?= --scratch $(BUILD_SCRATCH_TARGET)
FLAVOR =

RHGITURL?=$(shell $(GIT) config rhg.url || $(GIT) config remote.origin.url)
RHGITCOMMIT?=$(shell $(GIT) log -1 --pretty=format:%H)

# this section is needed in order to make O= to work
_OUTPUT := ..
ifeq ("$(origin O)", "command line")
  _OUTPUT := $(O)
  _EXTRA_ARGS := O=$(_OUTPUT)
endif

CURARCH := $(shell uname -m)
ARCHCONFIG := $(shell uname -m | sed -e s/x86_64/X86_64/ \
				     -e s/s390x/S390/ -e s/ppc.*/PPC/ )

KABIDW := $(REDHAT)/kabi-dwarf

include Makefile.cross

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
	@cd $(REDHAT)/configs; VERSION=$(KVERSION) ./generate_all_configs.sh "$(FLAVOR)" 1; \
	./process_configs.sh -z $(PACKAGE_NAME) $(KVERSION) "" $(FLAVOR)

dist-configs: dist-configs-prep
	@cd $(REDHAT)/configs; VERSION=$(KVERSION) ./generate_all_configs.sh "$(FLAVOR)" 1; \
	./process_configs.sh $(PROCESS_CONFIGS_OPTS) $(PACKAGE_NAME) $(KVERSION)

dist-fedora-configs: FLAVOR = fedora
dist-fedora-configs: dist-configs
fedora-configs: dist-fedora-configs

dist-rhel-configs: FLAVOR = rhel
dist-rhel-configs: dist-configs
rh-configs: dist-rhel-configs

dist-configs-check: dist-configs-prep
	cd $(REDHAT)/configs; ./process_configs.sh $(PROCESS_CONFIGS_CHECK_OPTS) $(PACKAGE_NAME)

dist-configs-prep: dist-clean-configs dist-buildreq-check
	cd $(REDHAT)/configs; ./build_configs.sh "partial" "$(ARCH_MACH)" "snip"
	cd $(REDHAT)/configs; ./build_configs.sh "$(PACKAGE_NAME)" "$(ARCH_MACH)" "$(FLAVOR)"

dist-configs-arch: ARCH_MACH = $(MACH)
dist-configs-arch: dist-configs

dist-clean-configs:
	cd $(REDHAT)/configs; rm -f kernel-*.config \
					kernel-*.config.orig \
					kernel-*.config.tmp

dist-clean-sources:
	@rm -f $(RPM)/SPECS/*
	@for i in $(SOURCES)/*; do \
		rm -f $$i; \
	done;

dist-clean-rpmdirs:
	@for i in $(RPM)/{BUILD,SRPMS,RPMS,SPECS}/*; do \
		rm -rf $$i; \
	done;

dist-clean-scripts:
	@rm -f dist-dump-variables.sh

dist-clean: dist-clean-sources dist-clean-configs dist-clean-rpmdirs dist-clean-scripts

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
	@if [ $(SINGLE_TARBALL) -eq 1 ]; then \
		scripts/create-tarball.sh $(GITID) $(TARBALL) linux-$(KVERSION)-$(PKGRELEASE); \
	else \
		scripts/create-tarball.sh $(MARKER) $(TARBALL) linux-$(TARFILE_RELEASE); \
	fi

.PHONY: $(KABI_TARBALL)
$(KABI_TARBALL):
	@(cd kabi && tar cjf $(SOURCES)/$(KABI_TARFILE) kabi-rhel$(RHEL_MAJOR)* kabi-current)

.PHONY: $(KABIDW_TARBALL)
$(KABIDW_TARBALL):
	@if [ ! -d $(KABIDW)/base ]; then \
		mkdir -p $(KABIDW)/base; \
	fi
	@(cd kabi-dwarf && tar cjf $(SOURCES)/$(KABIDW_TARFILE) base run_kabi-dw.sh)


dist-tarball: $(TARBALL)
	@echo "redhat/$(TARFILE)"

dist-kernelrelease:
	@echo $(PACKAGE_NAME)-$(KVERSION)-$(PKGRELEASE)

dist-kernelversion:
	@echo $(KVERSION)-$(PKGRELEASE)

dist-specfile: setup-source
	@echo $(SOURCES)/$(SPECFILE)

dist-git-version-check:
	@# genspec.sh uses pathspec magic that wasn't introduced until version 2.13
	@IFS=" ."; \
	set -- $$($(GIT) --version); \
	IFS=; \
	if [ "$$3" -lt 2 -o \( "$$3" -eq 2 -a "$$4" -lt 13 \) ]; then \
		echo "ERROR: You need git version 2.13 or newer to run some setup commands"; \
		exit 1; \
	fi

dist-buildreq-check: setup-source
	@PKGLIST="rpm-build $(rpmspec -q --buildrequires $(SOURCES)/$(SPECFILE) | cut -d ' ' -f 1)"; \
	MISSING=""; \
	for pkg in $$PKGLIST; do \
		rpm -q --whatprovides $$pkg >/dev/null || MISSING="$$MISSING $$pkg"; \
	done; \
	if [ -n "$$MISSING" ]; then \
		echo "Error: please install $$MISSING"; \
		exit 1; \
	fi

setup-source: dist-git-version-check dist-clean-sources
	@cp $(REDHAT)/$(SPECFILE).template $(SOURCES)/$(SPECFILE)
	@if [ ! -e  $(REDHAT)/$(CHANGELOG) ]; then \
		echo "Creating $(CHANGELOG) as copy of $(CHANGELOG_PREV)"; \
		cp $(REDHAT)/$(CHANGELOG_PREV) $(REDHAT)/$(CHANGELOG); \
	fi
	@cp $(REDHAT)/$(CHANGELOG) $(SOURCES)/$(CHANGELOG)
	@$(REDHAT)/genspec.sh $(SOURCES) $(SOURCES)/$(SPECFILE) $(SOURCES)/$(CHANGELOG) $(PKGRELEASE) $(RPMKVERSION) $(RPMKPATCHLEVEL) $(RPMKSUBLEVEL) $(SPECRELEASE) "$(BUILDOPTS)" $(MARKER) `cat $(REDHAT)/marker` $(SINGLE_TARBALL) $(TARFILE_RELEASE) $(SNAPSHOT) $(UPSTREAM_BRANCH) $(INCLUDE_FEDORA_FILES) $(INCLUDE_RHEL_FILES) $(RHEL_MAJOR) $(RHEL_MINOR) $(BUILDID)
	@cp $(SOURCES)/$(SPECFILE) $(SOURCES)/../SPECS/

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
	@cp cpupower.* \
		keys/rhel*.x509 \
		kabi/check-kabi \
		configs/$(PACKAGE_NAME)-*.config \
		configs/partial*.config \
		gating.yaml \
		rpminspect.yaml \
		update_scripts.sh \
		kvm_stat.logrotate \
		mod-denylist.sh \
		mod-internal.list \
		mod-sign.sh \
		configs/flavors \
		configs/generate_all_configs.sh \
		configs/merge.pl \
		configs/process_configs.sh \
		parallel_xz.sh \
		../Makefile.rhelver \
		README.rst \
		kernel-local \
		$(SOURCES)/
	@for KABIARCH in $(ARCH_LIST); do \
		cp kabi/Module.kabi_$$KABIARCH $(SOURCES)/; \
		cp kabi/Module.kabi_dup_$$KABIARCH $(SOURCES)/; \
	done
	@(cd kabi && tar cjf $(SOURCES)/$(KABI_TARFILE) kabi-rhel$(RHEL_MAJOR)* kabi-current)
	@if [ ! -d $(KABIDW)/base ]; then \
		mkdir -p $(KABIDW)/base; \
	fi
	@(cd kabi-dwarf && tar cjf $(SOURCES)/$(KABIDW_TARFILE) base run_kabi-dw.sh)

dist-sources: dist-kabi dist-kabi-dup sources-rh

dist-test-patch: generate-testpatch-tmp
	@mv $(TESTPATCH).tmp $(TESTPATCH);

do-rpmbuild: dist-sources
	$(RPMBUILD) --define "_sourcedir $(SOURCES)" --define "_builddir $(RPM)/BUILD" --define "_srcrpmdir $(RPM)/SRPMS" --define "_rpmdir $(RPM)/RPMS" --define "_specdir $(RPM)/SPECS" --define "dist $(DIST)" $(RPMBUILDOPTS) $(RPM)/SOURCES/$(PACKAGE_NAME).spec

dist-all-rpms: RPMBUILDOPTS=--target $(MACH) -ba
dist-all-rpms: dist-sources do-rpmbuild

dist-srpm: RPMBUILDOPTS=--nodeps -bs
dist-srpm: dist-sources do-rpmbuild

dist-srpm-gcov: BUILDID=".gcov"
dist-srpm-gcov: BUILDOPTS+="+gcov"
dist-srpm-gcov: dist-srpm

dist-rpms: RPMBUILDOPTS=--target $(MACH) -bb
dist-rpms: dist-sources do-rpmbuild

dist-kernel-%: dist-sources
	RPMBUILDOPTS="--target $(MACH) --with $* -bb" make do-rpmbuild

dist-prep: RPMBUILDOPTS=--nodeps --target noarch -bp
dist-prep: dist-sources do-rpmbuild

dist-perf: RPMBUILDOPTS=--without up --without smp --without zfcpdump --without debug --without doc --without headers --without  --without doc --without debuginfo --target $(MACH) -bb
dist-perf: dist-sources do-rpmbuild

dist-rpm-baseonly: RPMBUILDOPTS=--target $(MACH) --without debug --without debuginfo --without vdso_install --without bpftool --without perf --without tools -bb
dist-rpm-baseonly: dist-sources do-rpmbuild

# unless you know what you're doing, you don't want to use the next four ones
dist-release-finish: setup-source
	@cp $(SOURCES)/$(CHANGELOG) $(REDHAT)/$(CHANGELOG)
	@$(GIT) add $(REDHAT)/$(CHANGELOG)
	@$(GIT) add $(REDHAT)/marker
	@$(GIT) commit -s ../Makefile.rhelver $(REDHAT)/marker $(REDHAT)/$(CHANGELOG) $(PACKAGE_NAME).spec.template -m "[redhat] $(PACKAGE_NAME)-$(STAMP_VERSION)-$(PREBUILD)$(BUILD)$(SOURCE_DIST)$(BUILDID)"
dist-release-changed: setup-source
	@cp $(SOURCES)/$(CHANGELOG) $(REDHAT)/$(CHANGELOG)
	@echo $(MARKER) > $(REDHAT)/marker
	@# if neither changelog nor marker was updated, skip bumping a release
	@$(GIT) update-index -q --really-refresh
	@if $(GIT) diff-index --quiet HEAD; then \
		echo "Nothing changed, skipping updates"; \
	else \
		$(GIT) checkout -- $(REDHAT)/$(CHANGELOG); \
		$(REDHAT)/scripts/new_release.sh $(REDHAT) $(__YSTREAM) $(__ZSTREAM) $(BUMP_RELEASE); \
		$(MAKE) dist-release-finish; \
	fi
dist-release: dist-clean-sources
	@$(MAKE) dist-release-changed
dist-release-tag:
	@$(GIT) tag -a -m "$(PACKAGE_NAME)-$(STAMP_VERSION)-$(PKGRELEASE)" $(PACKAGE_NAME)-$(STAMP_VERSION)-$(PKGRELEASE)

git-tree-check:
	@if test -n "$(DIST_PUSH)" && test -z "$(shell $(GIT) remote get-url gitlab 2>/dev/null)"; then \
		echo -e "Please run 'git remote add gitlab <url>' to enable git-push.\n"; \
		exit 1; \
	fi
	@$(GIT) diff-index --quiet HEAD || \
		{ echo -e "Dirty tree, please clean before merging.\n"; exit 1; }

DIST_BRANCH ?= "os-build"
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

.PHONY: dist-brew dist-koji
dist-brew : BUILD_FLAGS ?= $(BREW_FLAGS) $(TEST_FLAGS)
dist-koji : BUILD_FLAGS ?= $(KOJI_FLAGS) $(TEST_FLAGS)
distg-brew: BUILD_FLAGS ?= $(BREW_FLAGS) $(TEST_FLAGS)
distg-koji: BUILD_FLAGS ?= $(KOJI_FLAGS) $(TEST_FLAGS)

dist-brew dist-koji: dist-%: dist-srpm
	$* $(BUILD_PROFILE) build $(BUILD_FLAGS) $(BUILD_TARGET) $(SRPMS)/$(PACKAGE_NAME)-$(KVERSION)-$(PKGRELEASE)$(SRPM_DIST).src.rpm $(OUTPUT_FILE)

distg-brew distg-koji: distg-%:
	$* $(BUILD_PROFILE) build $(BUILD_FLAGS) $(BUILD_TARGET) "$(RHGITURL)?redhat/koji#$(RHGITCOMMIT)"

.PHONY: $(REDHAT)/rpm/SOURCES/$(PACKAGE_NAME).spec
$(REDHAT)/rpm/SOURCES/$(PACKAGE_NAME).spec:
	@echo "dist-sources"
	@$(MAKE) dist-sources

dist-git-test: export RH_DIST_GIT_TEST="1"
dist-git-test: dist-git

dist-git: dist-srpm $(KABI_TARBALL) $(KABIDW_TARBALL)
ifeq ("$(RHDISTGIT_BRANCH)", "")
 $(error RHDISTGIT_BRANCH unset)
endif
	@if [ "$(DISTRO)" == "centos" ]; then \
	if [ -z "$(GL_DISTGIT_USER)" ]; then \
		echo "Error: please provide your gitlab username with GL_DISTGIT_USER"; \
		exit 1; \
	fi; \
	fi
	$(REDHAT)/scripts/rh-dist-git.sh "$(RHDISTGIT_BRANCH)" "$(RHDISTGIT_CACHE)" "$(RHDISTGIT_TMP)" "$(RHDISTGIT)" "$(TARBALL)" "$(KABI_TARBALL)" "$(KABIDW_TARBALL)" "$(PACKAGE_NAME)" "$(RPMVERSION)-$(PKGRELEASE)" "$(REDHAT)/$(CHANGELOG)" "$(RHEL_MAJOR)" "$(RHPKG_BIN)" "$(SRPMS)/$(PACKAGE_NAME)-$(KVERSION)-$(PKGRELEASE)$(SRPM_DIST).src.rpm"

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

.EXPORT_ALL_VARIABLES:
.PHONY: dist-dump-variables
dist-dump-variables:
	grep -h "^[ 	]*[a-zA-Z_][a-zA-Z_0-9]*[ 	]*[:?]*=" $(REDHAT)/Makefile.common $(REDHAT)/Makefile $(TOPDIR)/Makefile.rhelver | sed -e 's/[ 	]*\([a-zA-Z_][a-zA-Z_0-9]*\).*/echo "\1=$$\1"/' | sort | uniq > dist-dump-variables.sh
	chmod +x $(REDHAT)/dist-dump-variables.sh
	@$(REDHAT)/dist-dump-variables.sh

dist-self-test:
	@if test -x /usr/bin/bats; then \
		bats $(REDHAT)/self-test/*.bats ; \
	else \
		echo "dist-self-test: The bats package is not installed" ; \
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
	@echo  '  dist-buildreq-check - Checks for presence of packages required for build'
	@echo  '  dist-get-latest - Returns the latest "known good" kernel from brew. This'
	@echo  '                    should not be confused with the latest top-of-tree'
	@echo  '                    development tag.'
	@echo  '  dist-os-version - Displays the current Red Hat Enterprise Linux versioni'
	@echo  '                    target used by the current branch/tree.'
	@echo  '  dist-self-test  - Runs self-tests from the redhat/self-test directory'
	@echo  ''
