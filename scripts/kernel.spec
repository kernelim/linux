# All Global changes to build and install go here.
# Per the below section about __spec_install_pre, any rpm
# environment changes that affect %%install need to go
# here before the %%install macro is pre-built.

# Include Fedora files
%global include_fedora 0
# Include RHEL files
%global include_rhel 1

# Disable LTO in userspace packages.
%global _lto_cflags %{nil}

# Option to enable compiling with clang instead of gcc.
%bcond_with toolchain_clang

%if %{with toolchain_clang}
%global toolchain clang
%endif

# Compile the kernel with LTO (only supported when building with clang).
%bcond_with clang_lto

%if %{with clang_lto} && %{without toolchain_clang}
{error:clang_lto requires --with toolchain_clang}
%endif

# Cross compile on copr for arm
# See https://bugzilla.redhat.com/1879599
%if 0%{?_with_cross_arm:1}
%global _target_cpu armv7hl
%global _arch arm
%global _build_arch arm
%global _with_cross    1
%endif

# The kernel's %%install section is special
# Normally the %%install section starts by cleaning up the BUILD_ROOT
# like so:
#
# %%__spec_install_pre %%{___build_pre}\
#     [ "$RPM_BUILD_ROOT" != "/" ] && rm -rf "${RPM_BUILD_ROOT}"\
#     mkdir -p `dirname "$RPM_BUILD_ROOT"`\
#     mkdir "$RPM_BUILD_ROOT"\
# %%{nil}
#
# But because of kernel variants, the %%build section, specifically
# BuildKernel(), moves each variant to its final destination as the
# variant is built.  This violates the expectation of the %%install
# section.  As a result we snapshot the current env variables and
# purposely leave out the removal section.  All global wide changes
# should be added above this line otherwise the %%install section
# will not see them.
%global __spec_install_pre %{___build_pre}

# At the time of this writing (2019-03), RHEL8 packages use w2.xzdio
# compression for rpms (xz, level 2).
# Kernel has several large (hundreds of mbytes) rpms, they take ~5 mins
# to compress by single-threaded xz. Switch to threaded compression,
# and from level 2 to 3 to keep compressed sizes close to "w2" results.
#
# NB: if default compression in /usr/lib/rpm/redhat/macros ever changes,
# this one might need tweaking (e.g. if default changes to w3.xzdio,
# change below to w4T.xzdio):
#
# This is disabled on i686 as it triggers oom errors

%ifnarch i686
%define _binary_payload w3T.xzdio
%endif

Summary:               The Linux kernel

# Set debugbuildsenabled to 1 to build separate base and debug kernels
#  (on supported architectures). The kernel-debug-* subpackages will
#  contain the debug kernel.
# Set debugbuildsenabled to 0 to not build a separate debug kernel, but
#  to build the base kernel using the debug configuration. (Specifying
#  the --with-release option overrides this setting.)
%define debugbuildsenabled 1

%if 0%{?fedora}
%define secure_boot_arch x86_64
%else
%define secure_boot_arch x86_64 aarch64 s390x ppc64le
%endif

# Signing for secure boot authentication
%ifarch %{secure_boot_arch}
%global signkernel 1
%else
%global signkernel 0
%endif

# Sign modules on all arches
%global signmodules 1

# Compress modules only for architectures that build modules
%ifarch noarch
%global zipmodules 0
%else
%global zipmodules 1
%endif

%if %{zipmodules}
%global zipsed -e 's/\.ko$/\.ko.xz/'
# for parallel xz processes, replace with 1 to go back to single process
%global zcpu `nproc --all`
%endif

# define buildid .local


%if 0%{?fedora}
%define primary_target fedora
%else
%define primary_target rhel
%endif

# The kernel tarball/base version
%define kversion 5.14

%define rpmversion 5.14.0
%define pkgrelease 70.17.1.el9_0

# This is needed to do merge window version magic
%define patchlevel 14

# allow pkg_release to have configurable %%{?dist} tag
%define specrelease 70.17.1%{?buildid}%{?dist}

%define pkg_release %{specrelease}

# libexec dir is not used by the linker, so the shared object there
# should not be exported to RPM provides
%global __provides_exclude_from ^%{_libexecdir}/kselftests

%define _with_kabidupchk 1
# The following build options are enabled by default, but may become disabled
# by later architecture-specific checks. These can also be disabled by using
# --without <opt> in the rpmbuild command, or by forcing these values to 0.
#
# standard kernel
%define with_up        %{?_without_up:        0} %{?!_without_up:        1}
# kernel PAE (only valid for ARM (lpae))
%define with_pae       %{?_without_pae:       0} %{?!_without_pae:       1}
# kernel-debug
%define with_debug     %{?_without_debug:     0} %{?!_without_debug:     1}
# kernel-zfcpdump (s390 specific kernel for zfcpdump)
%define with_zfcpdump  %{?_without_zfcpdump:  0} %{?!_without_zfcpdump:  1}
# kernel-doc
%define with_doc       %{?_without_doc:       0} %{?!_without_doc:       1}
# kernel-headers
%define with_headers   %{?_without_headers:   0} %{?!_without_headers:   1}
%define with_cross_headers   %{?_without_cross_headers:   0} %{?!_without_cross_headers:   1}
# perf
%define with_perf      %{?_without_perf:      0} %{?!_without_perf:      1}
# tools
%define with_tools     %{?_without_tools:     0} %{?!_without_tools:     1}
# bpf tool
%define with_bpftool   %{?_without_bpftool:   0} %{?!_without_bpftool:   1}
# kernel-debuginfo
%define with_debuginfo %{?_without_debuginfo: 0} %{?!_without_debuginfo: 1}
# kernel-abi-stablelists
%define with_kernel_abi_stablelists %{?_without_kernel_abi_stablelists: 0} %{?!_without_kernel_abi_stablelists: 1}
# internal samples and selftests
%define with_selftests %{?_without_selftests: 0} %{?!_without_selftests: 1}
#
# Additional options for user-friendly one-off kernel building:
#
# Only build the base kernel (--with baseonly):
%define with_baseonly  %{?_with_baseonly:     1} %{?!_with_baseonly:     0}
# Only build the pae kernel (--with paeonly):
%define with_paeonly   %{?_with_paeonly:      1} %{?!_with_paeonly:      0}
# Only build the debug kernel (--with dbgonly):
%define with_dbgonly   %{?_with_dbgonly:      1} %{?!_with_dbgonly:      0}
# Control whether we perform a compat. check against published ABI.
%define with_kabichk   %{?_without_kabichk:   0} %{?!_without_kabichk:   1}
# Temporarily disable kabi checks until RC.
%define with_kabichk 0
# Control whether we perform a compat. check against DUP ABI.
%define with_kabidupchk %{?_with_kabidupchk:  1} %{?!_with_kabidupchk:   0}
#
# Control whether to run an extensive DWARF based kABI check.
# Note that this option needs to have baseline setup in SOURCE300.
%define with_kabidwchk %{?_without_kabidwchk: 0} %{?!_without_kabidwchk: 1}
%define with_kabidw_base %{?_with_kabidw_base: 1} %{?!_with_kabidw_base: 0}
#
# Control whether to install the vdso directories.
%define with_vdso_install %{?_without_vdso_install: 0} %{?!_without_vdso_install: 1}
#
# should we do C=1 builds with sparse
%define with_sparse    %{?_with_sparse:       1} %{?!_with_sparse:       0}
#
# Cross compile requested?
%define with_cross    %{?_with_cross:         1} %{?!_with_cross:        0}
#
# build a release kernel on rawhide
%define with_release   %{?_with_release:      1} %{?!_with_release:      0}

# verbose build, i.e. no silent rules and V=1
%define with_verbose %{?_with_verbose:        1} %{?!_with_verbose:      0}

#
# check for mismatched config options
%define with_configchecks %{?_without_configchecks:        0} %{?!_without_configchecks:        1}

#
# gcov support
%define with_gcov %{?_with_gcov:1}%{?!_with_gcov:0}

#
# ipa_clone support
%define with_ipaclones %{?_without_ipaclones: 0} %{?!_without_ipaclones: 1}

# Want to build a vanilla kernel build without any non-upstream patches?
%define with_vanilla %{?_with_vanilla: 1} %{?!_with_vanilla: 0}

%if 0%{?fedora}
# Kernel headers are being split out into a separate package
%define with_headers 0
%define with_cross_headers 0
# no ipa_clone for now
%define with_ipaclones 0
# no stablelist
%define with_kernel_abi_stablelists 0
# Fedora builds these separately
%define with_perf 0
%define with_tools 0
%define with_bpftool 0
# selftests turns on bpftool
%define with_selftests 0
%endif

%if %{with_verbose}
%define make_opts V=1
%else
%define make_opts -s
%endif

%if %{with toolchain_clang}
%global clang_make_opts HOSTCC=clang CC=clang
%if %{with clang_lto}
%global clang_make_opts %{clang_make_opts} LD=ld.lld HOSTLD=ld.lld AR=llvm-ar NM=llvm-nm HOSTAR=llvm-ar HOSTNM=llvm-nm LLVM_IAS=1
%endif
%global make_opts %{make_opts} %{clang_make_opts}
# clang does not support the -fdump-ipa-clones option
%global with_ipaclones 0
%endif

# turn off debug kernel and kabichk for gcov builds
%if %{with_gcov}
%define with_debug 0
%define with_kabichk 0
%define with_kabidupchk 0
%define with_kabidwchk 0
%define with_kabidw_base 0
%define with_kernel_abi_stablelists 0
%endif

# turn off kABI DWARF-based check if we're generating the base dataset
%if %{with_kabidw_base}
%define with_kabidwchk 0
%endif

# kpatch_kcflags are extra compiler flags applied to base kernel
# -fdump-ipa-clones is enabled only for base kernels on selected arches
%if %{with_ipaclones}
%ifarch x86_64 ppc64le
%define kpatch_kcflags -fdump-ipa-clones
%else
%define with_ipaclones 0
%endif
%endif

%define make_target bzImage
%define image_install_path boot

%define KVERREL %{version}-%{release}.%{_target_cpu}
%define KVERREL_RE %(echo %KVERREL | sed 's/+/[+]/g')
%define hdrarch %_target_cpu
%define asmarch %_target_cpu

%if 0%{!?nopatches:1}
%define nopatches 0
%endif

%if %{with_vanilla}
%define nopatches 1
%endif

%if %{with_release}
%define debugbuildsenabled 1
%endif

%if !%{with_debuginfo}
%define _enable_debug_packages 0
%endif
%define debuginfodir /usr/lib/debug
# Needed because we override almost everything involving build-ids
# and debuginfo generation. Currently we rely on the old alldebug setting.
%global _build_id_links alldebug

# kernel PAE is only built on ARMv7
%ifnarch armv7hl
%define with_pae 0
%endif

# if requested, only build base kernel
%if %{with_baseonly}
%define with_pae 0
%define with_debug 0
%define with_vdso_install 0
%define with_perf 0
%define with_tools 0
%define with_bpftool 0
%define with_kernel_abi_stablelists 0
%define with_selftests 0
%define with_cross 0
%define with_cross_headers 0
%define with_ipaclones 0
%endif

# if requested, only build pae kernel
%if %{with_paeonly}
%define with_up 0
%define with_debug 0
%endif

# if requested, only build debug kernel
%if %{with_dbgonly}
%define with_up 0
%define with_vdso_install 0
%define with_perf 0
%define with_tools 0
%define with_bpftool 0
%define with_kernel_abi_stablelists 0
%define with_selftests 0
%define with_cross 0
%define with_cross_headers 0
%define with_ipaclones 0
%endif

# turn off kABI DUP check and DWARF-based check if kABI check is disabled
%if !%{with_kabichk}
%define with_kabidupchk 0
%define with_kabidwchk 0
%endif

%if %{with_vdso_install}
%define use_vdso 1
%endif

# selftests require bpftool to be built
%if %{with_selftests}
%define with_bpftool 1
%endif

%ifnarch noarch
%define with_kernel_abi_stablelists 0
%endif

# Overrides for generic default options

# only package docs noarch
%ifnarch noarch
%define with_doc 0
%define doc_build_fail true
%endif

%if 0%{?fedora}
# don't do debug builds on anything but i686 and x86_64
%ifnarch i686 x86_64
%define with_debug 0
%endif
%endif

# don't build noarch kernels or headers (duh)
%ifarch noarch
%define with_up 0
%define with_headers 0
%define with_cross_headers 0
%define with_tools 0
%define with_perf 0
%define with_bpftool 0
%define with_selftests 0
%define with_debug 0
%define all_arch_configs kernel-%{version}-*.config
%endif

# sparse blows up on ppc
%ifnarch ppc64le
%define with_sparse 0
%endif

# zfcpdump mechanism is s390 only
%ifnarch s390x
%define with_zfcpdump 0
%endif

%if 0%{?fedora}
# This is not for Fedora
%define with_zfcpdump 0
%endif

# Per-arch tweaks

%ifarch i686
%define asmarch x86
%define hdrarch i386
%define all_arch_configs kernel-%{version}-i?86*.config
%define kernel_image arch/x86/boot/bzImage
%endif

%ifarch x86_64
%define asmarch x86
%define all_arch_configs kernel-%{version}-x86_64*.config
%define kernel_image arch/x86/boot/bzImage
%endif

%ifarch ppc64le
%define asmarch powerpc
%define hdrarch powerpc
%define make_target vmlinux
%define kernel_image vmlinux
%define kernel_image_elf 1
%define use_vdso 0
%define all_arch_configs kernel-%{version}-ppc64le*.config
%endif

%ifarch s390x
%define asmarch s390
%define hdrarch s390
%define all_arch_configs kernel-%{version}-s390x.config
%define kernel_image arch/s390/boot/bzImage
%define vmlinux_decompressor arch/s390/boot/compressed/vmlinux
%endif

%ifarch %{arm}
%define all_arch_configs kernel-%{version}-arm*.config
%define skip_nonpae_vdso 1
%define asmarch arm
%define hdrarch arm
%define make_target bzImage
%define kernel_image arch/arm/boot/zImage
# http://lists.infradead.org/pipermail/linux-arm-kernel/2012-March/091404.html
%define kernel_mflags KALLSYMS_EXTRA_PASS=1
# we only build headers/perf/tools on the base arm arches
# just like we used to only build them on i386 for x86
%ifnarch armv7hl
%define with_headers 0
%define with_cross_headers 0
%endif
# These currently don't compile on armv7
%define with_selftests 0
%endif

%ifarch aarch64
%define all_arch_configs kernel-%{version}-aarch64*.config
%define asmarch arm64
%define hdrarch arm64
%define make_target Image.gz
%define kernel_image arch/arm64/boot/Image.gz
%endif

# Should make listnewconfig fail if there's config options
# printed out?
%if %{nopatches}
%define with_configchecks 0
%endif

# To temporarily exclude an architecture from being built, add it to
# %%nobuildarches. Do _NOT_ use the ExclusiveArch: line, because if we
# don't build kernel-headers then the new build system will no longer let
# us use the previous build of that package -- it'll just be completely AWOL.
# Which is a BadThing(tm).

# We only build kernel-headers on the following...
%if 0%{?fedora}
%define nobuildarches i386
%else
%define nobuildarches i386 i686 %{arm}
%endif

%ifarch %nobuildarches
# disable BuildKernel commands
%define with_up 0
%define with_debug 0
%define with_pae 0
%define with_zfcpdump 0

%define with_debuginfo 0
%define with_perf 0
%define with_tools 0
%define with_bpftool 0
%define with_selftests 0
%define _enable_debug_packages 0
%endif

# Architectures we build tools/cpupower on
%if 0%{?fedora}
%define cpupowerarchs %{ix86} x86_64 ppc64le %{arm} aarch64
%else
%define cpupowerarchs i686 x86_64 ppc64le aarch64
%endif

%if 0%{?use_vdso}

%if 0%{?skip_nonpae_vdso}
%define _use_vdso 0
%else
%define _use_vdso 1
%endif

%else
%define _use_vdso 0
%endif

# If build of debug packages is disabled, we need to know if we want to create
# meta debug packages or not, after we define with_debug for all specific cases
# above. So this must be at the end here, after all cases of with_debug or not.
%define with_debug_meta 0
%if !%{debugbuildsenabled}
%if %{with_debug}
%define with_debug_meta 1
%endif
%define with_debug 0
%endif


#
# Packages that need to be installed before the kernel is, because the %%post
# scripts use them.
#
%define kernel_prereq  coreutils, systemd >= 203-2, /usr/bin/kernel-install
%define initrd_prereq  dracut >= 027


Name:                  kernel
License:               GPLv2 and Redistributable, no modification permitted
URL:                   https://www.kernel.org/
Version:               %{rpmversion}
Release:               %{pkg_release}
# DO NOT CHANGE THE 'ExclusiveArch' LINE TO TEMPORARILY EXCLUDE AN ARCHITECTURE BUILD.
# SET %%nobuildarches (ABOVE) INSTEAD
%if 0%{?fedora}
ExclusiveArch:         x86_64 s390x %{arm} aarch64 ppc64le
%else
ExclusiveArch:         noarch i386 i686 x86_64 s390x %{arm} aarch64 ppc64le
%endif
ExclusiveOS:           Linux
%ifnarch %{nobuildarches}
Requires:              kernel-core-uname-r = %{KVERREL}
Requires:              kernel-modules-uname-r = %{KVERREL}
%endif


#
# List the packages used during the kernel build
#
BuildRequires:         kmod, patch, bash, coreutils, tar, git-core, which
BuildRequires:         bzip2, xz, findutils, gzip, m4, perl-interpreter, perl-Carp, perl-devel, perl-generators, make, diffutils, gawk
BuildRequires:         gcc, binutils, redhat-rpm-config, hmaccalc, bison, flex, gcc-c++
BuildRequires:         net-tools, hostname, bc, elfutils-devel
BuildRequires:         dwarves
BuildRequires:         python3-devel
BuildRequires:         gcc-plugin-devel
# glibc-static is required for a consistent build environment (specifically
# CONFIG_CC_CAN_LINK_STATIC=y).
BuildRequires:         glibc-static
BuildRequires:         kernel-rpm-macros >= 185-9
%ifnarch %{nobuildarches} noarch
BuildRequires:         bpftool
%endif
%if %{with_headers}
BuildRequires:         rsync
%endif
%if %{with_doc}
BuildRequires:         xmlto, asciidoc, python3-sphinx, python3-sphinx_rtd_theme
%endif
%if %{with_sparse}
BuildRequires:         sparse
%endif
%if %{with_perf}
BuildRequires:         zlib-devel binutils-devel newt-devel perl(ExtUtils::Embed) bison flex xz-devel
BuildRequires:         audit-libs-devel
BuildRequires:         java-devel
BuildRequires:         libbpf-devel
BuildRequires:         libbabeltrace-devel
BuildRequires:         libtraceevent-devel
%ifnarch %{arm} s390x
BuildRequires:         numactl-devel
%endif
%ifarch aarch64
BuildRequires:         opencsd-devel >= 1.0.0
%endif
%endif
%if %{with_tools}
BuildRequires:         gettext ncurses-devel
BuildRequires:         libcap-devel libcap-ng-devel
%ifnarch s390x
BuildRequires:         pciutils-devel
%endif
%endif
%if %{with_tools} || %{signmodules} || %{signkernel}
BuildRequires:         openssl-devel
%endif
%if %{with_bpftool}
BuildRequires:         python3-docutils
BuildRequires:         zlib-devel binutils-devel
%endif
%if %{with_selftests}
BuildRequires:         clang llvm fuse-devel
%ifnarch %{arm}
BuildRequires:         numactl-devel
%endif
BuildRequires:         libcap-devel libcap-ng-devel rsync libmnl-devel
%endif
BuildConflicts:        rhbuildsys(DiskFree) < 500Mb
%if %{with_debuginfo}
BuildRequires:         rpm-build, elfutils
BuildConflicts:        rpm < 4.13.0.1-19
BuildConflicts:        dwarves < 1.13
# Most of these should be enabled after more investigation
%undefine _include_minidebuginfo
%undefine _find_debuginfo_dwz_opts
%undefine _unique_build_ids
%undefine _unique_debug_names
%undefine _unique_debug_srcs
%undefine _debugsource_packages
%undefine _debuginfo_subpackages
%global _find_debuginfo_opts -r
%global _missing_build_ids_terminate_build 1
%global _no_recompute_build_ids 1
%endif
%if %{with_kabidwchk} || %{with_kabidw_base}
BuildRequires:         kabi-dw
%endif

%if %{signkernel}%{signmodules}
BuildRequires:         openssl
%if %{signkernel}
BuildRequires:         system-sb-certs
%ifarch x86_64 aarch64
BuildRequires:         nss-tools
BuildRequires:         pesign >= 0.10-4
%endif
%endif
%endif

%if %{with_cross}
BuildRequires:         binutils-%{_build_arch}-linux-gnu, gcc-%{_build_arch}-linux-gnu
%define cross_opts CROSS_COMPILE=%{_build_arch}-linux-gnu-
%define __strip %{_build_arch}-linux-gnu-strip
%endif

# These below are required to build man pages
%if %{with_perf}
BuildRequires:         xmlto
%endif
%if %{with_perf} || %{with_tools}
BuildRequires:         asciidoc
%endif

%if %{with toolchain_clang}
BuildRequires:         clang
%endif

%if %{with clang_lto}
BuildRequires:         llvm
BuildRequires:         lld
%endif

# Because this is the kernel, it's hard to get a single upstream URL
# to represent the base without needing to do a bunch of patching. This
# tarball is generated from a src-git tree. If you want to see the
# exact git commit you can run
#
# xzcat -qq ${TARBALL} | git get-tar-commit-id
Source0:               linux-5.14.0-70.17.1.el9_0.tar.xz

Source1:               Makefile.rhelver

%if %{signkernel}

# Name of the packaged file containing signing key
%ifarch ppc64le
%define signing_key_filename kernel-signing-ppc.cer
%endif
%ifarch s390x
%define signing_key_filename kernel-signing-s390.cer
%endif

%define secureboot_ca_0 %{_datadir}/pki/sb-certs/secureboot-ca-%{_arch}.cer
%define secureboot_key_0 %{_datadir}/pki/sb-certs/secureboot-kernel-%{_arch}.cer

%ifarch x86_64 aarch64
%define pesign_name_0 rockybootsigningcert
%endif
%ifarch s390x
%define pesign_name_0 rockybootsigningcert
%endif
%ifarch ppc64le
%define pesign_name_0 rockybootsigningcert
%endif

# signkernel
%endif

Source20:              mod-denylist.sh
Source21:              mod-sign.sh
Source22:              parallel_xz.sh

%define modsign_cmd %{SOURCE21}

%if 0%{?include_rhel}
Source23:              x509.genkey

Source24:              kernel-aarch64-rhel.config
Source25:              kernel-aarch64-debug-rhel.config
Source26:              mod-extra.list.rhel

Source27:              kernel-ppc64le-rhel.config
Source28:              kernel-ppc64le-debug-rhel.config
Source29:              kernel-s390x-rhel.config
Source30:              kernel-s390x-debug-rhel.config
Source31:              kernel-s390x-zfcpdump-rhel.config
Source32:              kernel-x86_64-rhel.config
Source33:              kernel-x86_64-debug-rhel.config

Source34:              filter-x86_64.sh.rhel
Source35:              filter-armv7hl.sh.rhel
Source36:              filter-i686.sh.rhel
Source37:              filter-aarch64.sh.rhel
Source38:              filter-ppc64le.sh.rhel
Source39:              filter-s390x.sh.rhel
Source40:              filter-modules.sh.rhel
%endif

%if 0%{?include_fedora}
Source50:              x509.genkey.fedora
Source51:              mod-extra.list.fedora

Source52:              kernel-aarch64-fedora.config
Source53:              kernel-aarch64-debug-fedora.config
Source54:              kernel-armv7hl-fedora.config
Source55:              kernel-armv7hl-debug-fedora.config
Source56:              kernel-armv7hl-lpae-fedora.config
Source57:              kernel-armv7hl-lpae-debug-fedora.config
Source58:              kernel-i686-fedora.config
Source59:              kernel-i686-debug-fedora.config
Source60:              kernel-ppc64le-fedora.config
Source61:              kernel-ppc64le-debug-fedora.config
Source62:              kernel-s390x-fedora.config
Source63:              kernel-s390x-debug-fedora.config
Source64:              kernel-x86_64-fedora.config
Source65:              kernel-x86_64-debug-fedora.config

Source67:              filter-x86_64.sh.fedora
Source68:              filter-armv7hl.sh.fedora
Source69:              filter-i686.sh.fedora
Source70:              filter-aarch64.sh.fedora
Source71:              filter-ppc64le.sh.fedora
Source72:              filter-s390x.sh.fedora
Source73:              filter-modules.sh.fedora
%endif

Source75:              partial-kgcov-snip.config
Source80:              generate_all_configs.sh
Source81:              process_configs.sh

Source82:              update_scripts.sh

Source84:              mod-internal.list

Source200:             check-kabi

Source201:             Module.kabi_aarch64
Source202:             Module.kabi_ppc64le
Source203:             Module.kabi_s390x
Source204:             Module.kabi_x86_64

Source210:             Module.kabi_dup_aarch64
Source211:             Module.kabi_dup_ppc64le
Source212:             Module.kabi_dup_s390x
Source213:             Module.kabi_dup_x86_64

Source300:             kernel-abi-stablelists-%{rpmversion}-%{pkgrelease}.tar.bz2
Source301:             kernel-kabi-dw-%{rpmversion}-%{pkgrelease}.tar.bz2

# Sources for kernel-tools
Source2000:            cpupower.service
Source2001:            cpupower.config
Source2002:            kvm_stat.logrotate

# Some people enjoy building customized kernels from the dist-git in Fedora and
# use this to override configuration options. One day they may all use the
# source tree, but in the mean time we carry this to support the legacy workflow
Source3000:            merge.pl
Source3001:            kernel-local

Source4000:            README.rst
Source4001:            rpminspect.yaml
Source4002:            gating.yaml

## Rocky driver and kpatch certs
Source90000:           rockydup1.x509
Source90001:           rockykpatch1.x509

## Patches needed for building this package

%if !%{nopatches}

Patch1:                patch-%{rpmversion}-redhat.patch
%endif

# empty final patch to facilitate testing of kernel patches
Patch999999:           linux-kernel-test.patch

# END OF PATCH DEFINITIONS

%description
The kernel meta package

#
# This macro does requires, provides, conflicts, obsoletes for a kernel package.
#	%%kernel_reqprovconf <subpackage>
# It uses any kernel_<subpackage>_conflicts and kernel_<subpackage>_obsoletes
# macros defined above.
#
%define kernel_reqprovconf \
Provides:              kernel = %{rpmversion}-%{pkg_release}\
Provides:              kernel-%{_target_cpu} = %{rpmversion}-%{pkg_release}%{?1:+%{1}}\
Provides:              kernel-drm-nouveau = 16\
Provides:              kernel-uname-r = %{KVERREL}%{?1:+%{1}}\
Requires(pre): %{kernel_prereq}\
Requires(pre): %{initrd_prereq}\
Requires(pre): ((linux-firmware >= 20150904-56.git6ebf5d57) if linux-firmware)\
Recommends:            linux-firmware\
Requires(preun): systemd >= 200\
Conflicts:             xfsprogs < 4.3.0-1\
Conflicts:             xorg-x11-drv-vmmouse < 13.0.99\
%{expand:%%{?kernel%{?1:_%{1}}_conflicts:Conflicts: %%{kernel%{?1:_%{1}}_conflicts}}}\
%{expand:%%{?kernel%{?1:_%{1}}_obsoletes:Obsoletes: %%{kernel%{?1:_%{1}}_obsoletes}}}\
%{expand:%%{?kernel%{?1:_%{1}}_provides:Provides: %%{kernel%{?1:_%{1}}_provides}}}\
# We can't let RPM do the dependencies automatic because it'll then pick up\
# a correct but undesirable perl dependency from the module headers which\
# isn't required for the kernel proper to function\
AutoReq:               no\
AutoProv:              yes\
%{nil}


%package doc
Summary:               Various documentation bits found in the kernel source
Group:                 Documentation
%description doc
This package contains documentation files from the kernel
source. Various bits of information about the Linux kernel and the
device drivers shipped with it are documented in these files.

You'll want to install this package if you need a reference to the
options that can be passed to Linux kernel modules at load time.


%package headers
Summary:               Header files for the Linux kernel for use by glibc
Obsoletes:             glibc-kernheaders < 3.0-46
Provides:              glibc-kernheaders = 3.0-46
%description headers
Kernel-headers includes the C header files that specify the interface
between the Linux kernel and userspace libraries and programs.  The
header files define structures and constants that are needed for
building most standard programs and are also needed for rebuilding the
glibc package.

%package cross-headers
Summary:               Header files for the Linux kernel for use by cross-glibc
%description cross-headers
Kernel-cross-headers includes the C header files that specify the interface
between the Linux kernel and userspace libraries and programs.  The
header files define structures and constants that are needed for
building most standard programs and are also needed for rebuilding the
cross-glibc package.


%package debuginfo-common-%{_target_cpu}
Summary:               Kernel source files used by %{name}-debuginfo packages
Provides:              installonlypkg(kernel)
%description debuginfo-common-%{_target_cpu}
This package is required by %{name}-debuginfo subpackages.
It provides the kernel source files common to all builds.

%if %{with_perf}
%package -n perf
Summary:               Performance monitoring for the Linux kernel
Requires:              bzip2
License:               GPLv2
%description -n perf
This package contains the perf tool, which enables performance monitoring
of the Linux kernel.

%package -n perf-debuginfo
Summary:               Debug information for package perf
Requires:              %{name}-debuginfo-common-%{_target_cpu} = %{version}-%{release}
AutoReqProv:           no
%description -n perf-debuginfo
This package provides debug information for the perf package.

# Note that this pattern only works right to match the .build-id
# symlinks because of the trailing nonmatching alternation and
# the leading .*, because of find-debuginfo.sh's buggy handling
# of matching the pattern against the symlinks file.
%{expand:%%global _find_debuginfo_opts %{?_find_debuginfo_opts} -p '.*%%{_bindir}/perf(\.debug)?|.*%%{_libexecdir}/perf-core/.*|.*%%{_libdir}/libperf-jvmti.so(\.debug)?|XXX' -o perf-debuginfo.list}

%package -n python3-perf
Summary:               Python bindings for apps which will manipulate perf events
%description -n python3-perf
The python3-perf package contains a module that permits applications
written in the Python programming language to use the interface
to manipulate perf events.

%package -n python3-perf-debuginfo
Summary:               Debug information for package perf python bindings
Requires:              %{name}-debuginfo-common-%{_target_cpu} = %{version}-%{release}
AutoReqProv:           no
%description -n python3-perf-debuginfo
This package provides debug information for the perf python bindings.

# the python_sitearch macro should already be defined from above
%{expand:%%global _find_debuginfo_opts %{?_find_debuginfo_opts} -p '.*%%{python3_sitearch}/perf.*so(\.debug)?|XXX' -o python3-perf-debuginfo.list}

# with_perf
%endif

%if %{with_tools}
%package -n kernel-tools
Summary:               Assortment of tools for the Linux kernel
License:               GPLv2
%ifarch %{cpupowerarchs}
Provides:              cpupowerutils = 1:009-0.6.p1
Obsoletes:             cpupowerutils < 1:009-0.6.p1
Provides:              cpufreq-utils = 1:009-0.6.p1
Provides:              cpufrequtils = 1:009-0.6.p1
Obsoletes:             cpufreq-utils < 1:009-0.6.p1
Obsoletes:             cpufrequtils < 1:009-0.6.p1
Obsoletes:             cpuspeed < 1:1.5-16
Requires:              kernel-tools-libs = %{version}-%{release}
%endif
%define __requires_exclude ^%{_bindir}/python
%description -n kernel-tools
This package contains the tools/ directory from the kernel source
and the supporting documentation.

%package -n kernel-tools-libs
Summary:               Libraries for the kernels-tools
License:               GPLv2
%description -n kernel-tools-libs
This package contains the libraries built from the tools/ directory
from the kernel source.

%package -n kernel-tools-libs-devel
Summary:               Assortment of tools for the Linux kernel
License:               GPLv2
Requires:              kernel-tools = %{version}-%{release}
%ifarch %{cpupowerarchs}
Provides:              cpupowerutils-devel = 1:009-0.6.p1
Obsoletes:             cpupowerutils-devel < 1:009-0.6.p1
%endif
Requires:              kernel-tools-libs = %{version}-%{release}
Provides:              kernel-tools-devel
%description -n kernel-tools-libs-devel
This package contains the development files for the tools/ directory from
the kernel source.

%package -n kernel-tools-debuginfo
Summary:               Debug information for package kernel-tools
Requires:              %{name}-debuginfo-common-%{_target_cpu} = %{version}-%{release}
AutoReqProv:           no
%description -n kernel-tools-debuginfo
This package provides debug information for package kernel-tools.

# Note that this pattern only works right to match the .build-id
# symlinks because of the trailing nonmatching alternation and
# the leading .*, because of find-debuginfo.sh's buggy handling
# of matching the pattern against the symlinks file.
%{expand:%%global _find_debuginfo_opts %{?_find_debuginfo_opts} -p '.*%%{_bindir}/centrino-decode(\.debug)?|.*%%{_bindir}/powernow-k8-decode(\.debug)?|.*%%{_bindir}/cpupower(\.debug)?|.*%%{_libdir}/libcpupower.*|.*%%{_bindir}/turbostat(\.debug)?|.*%%{_bindir}/x86_energy_perf_policy(\.debug)?|.*%%{_bindir}/tmon(\.debug)?|.*%%{_bindir}/lsgpio(\.debug)?|.*%%{_bindir}/gpio-hammer(\.debug)?|.*%%{_bindir}/gpio-event-mon(\.debug)?|.*%%{_bindir}/gpio-watch(\.debug)?|.*%%{_bindir}/iio_event_monitor(\.debug)?|.*%%{_bindir}/iio_generic_buffer(\.debug)?|.*%%{_bindir}/lsiio(\.debug)?|.*%%{_bindir}/intel-speed-select(\.debug)?|.*%%{_bindir}/page_owner_sort(\.debug)?|.*%%{_bindir}/slabinfo(\.debug)?|XXX' -o kernel-tools-debuginfo.list}

# with_tools
%endif

%if %{with_bpftool}

%package -n bpftool
Summary:               Inspection and simple manipulation of eBPF programs and maps
License:               GPLv2
%description -n bpftool
This package contains the bpftool, which allows inspection and simple
manipulation of eBPF programs and maps.

%package -n bpftool-debuginfo
Summary:               Debug information for package bpftool
Group:                 Development/Debug
Requires:              %{name}-debuginfo-common-%{_target_cpu} = %{version}-%{release}
AutoReqProv:           no
%description -n bpftool-debuginfo
This package provides debug information for the bpftool package.

%{expand:%%global _find_debuginfo_opts %{?_find_debuginfo_opts} -p '.*%%{_sbindir}/bpftool(\.debug)?|XXX' -o bpftool-debuginfo.list}

# with_bpftool
%endif

%if %{with_selftests}

%package selftests-internal
Summary:               Kernel samples and selftests
License:               GPLv2
Requires:              binutils, bpftool, iproute-tc, nmap-ncat, python3, fuse-libs
%description selftests-internal
Kernel sample programs and selftests.

# Note that this pattern only works right to match the .build-id
# symlinks because of the trailing nonmatching alternation and
# the leading .*, because of find-debuginfo.sh's buggy handling
# of matching the pattern against the symlinks file.
%{expand:%%global _find_debuginfo_opts %{?_find_debuginfo_opts} -p '.*%%{_libexecdir}/(ksamples|kselftests)/.*|XXX' -o selftests-debuginfo.list}

# with_selftests
%endif

%if %{with_gcov}
%package gcov
Summary:               gcov graph and source files for coverage data collection.
%description gcov
kernel-gcov includes the gcov graph and source files for gcov coverage collection.
%endif

%package -n kernel-abi-stablelists
Summary:               The Rocky Linux kernel ABI symbol stablelists
AutoReqProv:           no
%description -n kernel-abi-stablelists
The kABI package contains information pertaining to the Rocky
Linux kernel ABI, including lists of kernel symbols that are needed by
external Linux kernel modules, and a yum plugin to aid enforcement.

%if %{with_kabidw_base}
%package kernel-kabidw-base-internal
Summary:               The baseline dataset for kABI verification using DWARF data
Group:                 System Environment/Kernel
AutoReqProv:           no
%description kernel-kabidw-base-internal
The package contains data describing the current ABI of the Rocky
Linux kernel, suitable for the kabi-dw tool.
%endif

#
# This macro creates a kernel-<subpackage>-debuginfo package.
#	%%kernel_debuginfo_package <subpackage>
#
# Explanation of the find_debuginfo_opts: We build multiple kernels (debug
# pae etc.) so the regex filters those kernels appropriately. We also
# have to package several binaries as part of kernel-devel but getting
# unique build-ids is tricky for these userspace binaries. We don't really
# care about debugging those so we just filter those out and remove it.
%define kernel_debuginfo_package() \
%package %{?1:%{1}-}debuginfo\
Summary:               Debug information for package %{name}%{?1:-%{1}}\
Requires:              %{name}-debuginfo-common-%{_target_cpu} = %{version}-%{release}\
Provides:              %{name}%{?1:-%{1}}-debuginfo-%{_target_cpu} = %{version}-%{release}\
Provides:              installonlypkg(kernel)\
AutoReqProv:           no\
%description %{?1:%{1}-}debuginfo\
This package provides debug information for package %{name}%{?1:-%{1}}.\
This is required to use SystemTap with %{name}%{?1:-%{1}}-%{KVERREL}.\
%{expand:%%global _find_debuginfo_opts %{?_find_debuginfo_opts} -p '.*\/usr\/src\/kernels/.*|XXX' -o ignored-debuginfo.list -p '/.*/%%{KVERREL_RE}%{?1:[+]%{1}}/.*|/.*%%{KVERREL_RE}%{?1:\+%{1}}(\.debug)?' -o debuginfo%{?1}.list}\
%{nil}

#
# This macro creates a kernel-<subpackage>-devel package.
#	%%kernel_devel_package [-m] <subpackage> <pretty-name>
#
%define kernel_devel_package(m) \
%package %{?1:%{1}-}devel\
Summary:               Development package for building kernel modules to match the %{?2:%{2} }kernel\
Provides:              kernel%{?1:-%{1}}-devel-%{_target_cpu} = %{version}-%{release}\
Provides:              kernel-devel-%{_target_cpu} = %{version}-%{release}%{?1:+%{1}}\
Provides:              kernel-devel-uname-r = %{KVERREL}%{?1:+%{1}}\
Provides:              installonlypkg(kernel)\
AutoReqProv:           no\
Requires(pre): findutils\
Requires:              findutils\
Requires:              perl-interpreter\
Requires:              openssl-devel\
Requires:              elfutils-libelf-devel\
Requires:              bison\
Requires:              flex\
Requires:              make\
Requires:              gcc\
%if %{-m:1}%{!-m:0}\
Requires:              kernel-devel-uname-r = %{KVERREL}\
%endif\
%description %{?1:%{1}-}devel\
This package provides kernel headers and makefiles sufficient to build modules\
against the %{?2:%{2} }kernel package.\
%{nil}

#
# This macro creates an empty kernel-<subpackage>-devel-matched package that
# requires both the core and devel packages locked on the same version.
#	%%kernel_devel_matched_package [-m] <subpackage> <pretty-name>
#
%define kernel_devel_matched_package(m) \
%package %{?1:%{1}-}devel-matched\
Summary:               Meta package to install matching core and devel packages for a given %{?2:%{2} }kernel\
Requires:              kernel%{?1:-%{1}}-devel = %{version}-%{release}\
Requires:              kernel%{?1:-%{1}}-core = %{version}-%{release}\
%description %{?1:%{1}-}devel-matched\
This meta package is used to install matching core and devel packages for a given %{?2:%{2} }kernel.\
%{nil}

#
# kernel-<variant>-ipaclones-internal package
#
%define kernel_ipaclones_package() \
%package %{?1:%{1}-}ipaclones-internal\
Summary:               *.ipa-clones files generated by -fdump-ipa-clones for kernel%{?1:-%{1}}\
Group:                 System Environment/Kernel\
AutoReqProv:           no\
%description %{?1:%{1}-}ipaclones-internal\
This package provides *.ipa-clones files.\
%{nil}

#
# This macro creates a kernel-<subpackage>-modules-internal package.
#	%%kernel_modules_internal_package <subpackage> <pretty-name>
#
%define kernel_modules_internal_package() \
%package %{?1:%{1}-}modules-internal\
Summary:               Extra kernel modules to match the %{?2:%{2} }kernel\
Group:                 System Environment/Kernel\
Provides:              kernel%{?1:-%{1}}-modules-internal-%{_target_cpu} = %{version}-%{release}\
Provides:              kernel%{?1:-%{1}}-modules-internal-%{_target_cpu} = %{version}-%{release}%{?1:+%{1}}\
Provides:              kernel%{?1:-%{1}}-modules-internal = %{version}-%{release}%{?1:+%{1}}\
Provides:              installonlypkg(kernel-module)\
Provides:              kernel%{?1:-%{1}}-modules-internal-uname-r = %{KVERREL}%{?1:+%{1}}\
Requires:              kernel-uname-r = %{KVERREL}%{?1:+%{1}}\
Requires:              kernel%{?1:-%{1}}-modules-uname-r = %{KVERREL}%{?1:+%{1}}\
AutoReq:               no\
AutoProv:              yes\
%description %{?1:%{1}-}modules-internal\
This package provides kernel modules for the %{?2:%{2} }kernel package for Rocky internal usage.\
%{nil}

#
# This macro creates a kernel-<subpackage>-modules-extra package.
#	%%kernel_modules_extra_package [-m] <subpackage> <pretty-name>
#
%define kernel_modules_extra_package(m) \
%package %{?1:%{1}-}modules-extra\
Summary:               Extra kernel modules to match the %{?2:%{2} }kernel\
Provides:              kernel%{?1:-%{1}}-modules-extra-%{_target_cpu} = %{version}-%{release}\
Provides:              kernel%{?1:-%{1}}-modules-extra-%{_target_cpu} = %{version}-%{release}%{?1:+%{1}}\
Provides:              kernel%{?1:-%{1}}-modules-extra = %{version}-%{release}%{?1:+%{1}}\
Provides:              installonlypkg(kernel-module)\
Provides:              kernel%{?1:-%{1}}-modules-extra-uname-r = %{KVERREL}%{?1:+%{1}}\
Requires:              kernel-uname-r = %{KVERREL}%{?1:+%{1}}\
Requires:              kernel%{?1:-%{1}}-modules-uname-r = %{KVERREL}%{?1:+%{1}}\
%if %{-m:1}%{!-m:0}\
Requires:              kernel-modules-extra-uname-r = %{KVERREL}\
%endif\
AutoReq:               no\
AutoProv:              yes\
%description %{?1:%{1}-}modules-extra\
This package provides less commonly used kernel modules for the %{?2:%{2} }kernel package.\
%{nil}

#
# This macro creates a kernel-<subpackage>-modules package.
#	%%kernel_modules_package [-m] <subpackage> <pretty-name>
#
%define kernel_modules_package(m) \
%package %{?1:%{1}-}modules\
Summary:               kernel modules to match the %{?2:%{2}-}core kernel\
Provides:              kernel%{?1:-%{1}}-modules-%{_target_cpu} = %{version}-%{release}\
Provides:              kernel-modules-%{_target_cpu} = %{version}-%{release}%{?1:+%{1}}\
Provides:              kernel-modules = %{version}-%{release}%{?1:+%{1}}\
Provides:              installonlypkg(kernel-module)\
Provides:              kernel%{?1:-%{1}}-modules-uname-r = %{KVERREL}%{?1:+%{1}}\
Requires:              kernel-uname-r = %{KVERREL}%{?1:+%{1}}\
%if %{-m:1}%{!-m:0}\
Requires:              kernel-modules-uname-r = %{KVERREL}\
%endif\
AutoReq:               no\
AutoProv:              yes\
%description %{?1:%{1}-}modules\
This package provides commonly used kernel modules for the %{?2:%{2}-}core kernel package.\
%{nil}

#
# this macro creates a kernel-<subpackage> meta package.
#	%%kernel_meta_package <subpackage>
#
%define kernel_meta_package() \
%package %{1}\
summary:               kernel meta-package for the %{1} kernel\
Requires:              kernel-%{1}-core-uname-r = %{KVERREL}+%{1}\
Requires:              kernel-%{1}-modules-uname-r = %{KVERREL}+%{1}\
Provides:              installonlypkg(kernel)\
%description %{1}\
The meta-package for the %{1} kernel\
%{nil}

#
# This macro creates a kernel-<subpackage> and its -devel and -debuginfo too.
#	%%define variant_summary The Linux kernel compiled for <configuration>
#	%%kernel_variant_package [-n <pretty-name>] [-m] <subpackage>
#
%define kernel_variant_package(n:m) \
%package %{?1:%{1}-}core\
Summary:               %{variant_summary}\
Provides:              kernel-%{?1:%{1}-}core-uname-r = %{KVERREL}%{?1:+%{1}}\
Provides:              installonlypkg(kernel)\
%if %{-m:1}%{!-m:0}\
Requires:              kernel-core-uname-r = %{KVERREL}\
%endif\
%{expand:%%kernel_reqprovconf}\
%if %{?1:1} %{!?1:0} \
%{expand:%%kernel_meta_package %{?1:%{1}}}\
%endif\
%{expand:%%kernel_devel_package %{?1:%{1}} %{!?{-n}:%{1}}%{?{-n}:%{-n*}} %{-m:%{-m}}}\
%{expand:%%kernel_devel_matched_package %{?1:%{1}} %{!?{-n}:%{1}}%{?{-n}:%{-n*}} %{-m:%{-m}}}\
%{expand:%%kernel_modules_package %{?1:%{1}} %{!?{-n}:%{1}}%{?{-n}:%{-n*}} %{-m:%{-m}}}\
%{expand:%%kernel_modules_extra_package %{?1:%{1}} %{!?{-n}:%{1}}%{?{-n}:%{-n*}} %{-m:%{-m}}}\
%if %{-m:0}%{!-m:1}\
%{expand:%%kernel_modules_internal_package %{?1:%{1}} %{!?{-n}:%{1}}%{?{-n}:%{-n*}}}\
%{expand:%%kernel_debuginfo_package %{?1:%{1}}}\
%endif\
%{nil}

# Now, each variant package.

%if %{with_pae}
%define variant_summary The Linux kernel compiled for Cortex-A15
%kernel_variant_package lpae
%description lpae-core
This package includes a version of the Linux kernel with support for
Cortex-A15 devices with LPAE and HW virtualisation support
%endif

%if %{with_zfcpdump}
%define variant_summary The Linux kernel compiled for zfcpdump usage
%kernel_variant_package zfcpdump
%description zfcpdump-core
The kernel package contains the Linux kernel (vmlinuz) for use by the
zfcpdump infrastructure.
# with_zfcpdump
%endif

%define variant_summary The Linux kernel compiled with extra debugging enabled
%if !%{debugbuildsenabled}
%kernel_variant_package -m debug
%else
%kernel_variant_package debug
%endif
%description debug-core
The kernel package contains the Linux kernel (vmlinuz), the core of any
Linux operating system.  The kernel handles the basic functions
of the operating system:  memory allocation, process allocation, device
input and output, etc.

This variant of the kernel has numerous debugging options enabled.
It should only be installed when trying to gather additional information
on kernel bugs, as some of these options impact performance noticably.

# And finally the main -core package

%define variant_summary The Linux kernel
%kernel_variant_package
%description core
The kernel package contains the Linux kernel (vmlinuz), the core of any
Linux operating system.  The kernel handles the basic functions
of the operating system: memory allocation, process allocation, device
input and output, etc.

%if %{with_ipaclones}
%kernel_ipaclones_package
%endif

%prep
# do a few sanity-checks for --with *only builds
%if %{with_baseonly}
%if !%{with_up}
echo "Cannot build --with baseonly, up build is disabled"
exit 1
%endif
%endif

# more sanity checking; do it quietly
if [ "%{patches}" != "%%{patches}" ] ; then
  for patch in %{patches} ; do
    if [ ! -f $patch ] ; then
      echo "ERROR: Patch  ${patch##/*/}  listed in specfile but is missing"
      exit 1
    fi
  done
fi 2>/dev/null

patch_command='patch -p1 -F1 -s'
ApplyPatch()
{
  local patch=$1
  shift
  if [ ! -f $RPM_SOURCE_DIR/$patch ]; then
    exit 1
  fi
  if ! grep -E "^Patch[0-9]+: $patch\$" %{_specdir}/${RPM_PACKAGE_NAME}.spec ; then
    if [ "${patch:0:8}" != "patch-5." ] ; then
      echo "ERROR: Patch  $patch  not listed as a source patch in specfile"
      exit 1
    fi
  fi 2>/dev/null
  case "$patch" in
  *.bz2) bunzip2 < "$RPM_SOURCE_DIR/$patch" | $patch_command ${1+"$@"} ;;
  *.gz)  gunzip  < "$RPM_SOURCE_DIR/$patch" | $patch_command ${1+"$@"} ;;
  *.xz)  unxz    < "$RPM_SOURCE_DIR/$patch" | $patch_command ${1+"$@"} ;;
  *) $patch_command ${1+"$@"} < "$RPM_SOURCE_DIR/$patch" ;;
  esac
}

# don't apply patch if it's empty
ApplyOptionalPatch()
{
  local patch=$1
  shift
  if [ ! -f $RPM_SOURCE_DIR/$patch ]; then
    exit 1
  fi
  local C=$(wc -l $RPM_SOURCE_DIR/$patch | awk '{print $1}')
  if [ "$C" -gt 9 ]; then
    ApplyPatch $patch ${1+"$@"}
  fi
}

%setup -q -n kernel-5.14.0-70.17.1.el9_0 -c
mv linux-5.14.0-70.17.1.el9_0 linux-%{KVERREL}

cd linux-%{KVERREL}
cp -a %{SOURCE1} .

%if !%{nopatches}

ApplyOptionalPatch patch-%{rpmversion}-redhat.patch
%endif

ApplyOptionalPatch linux-kernel-test.patch

# END OF PATCH APPLICATIONS

# Any further pre-build tree manipulations happen here.

chmod +x scripts/checkpatch.pl
mv COPYING COPYING-%{version}-%{release}

# This Prevents scripts/setlocalversion from mucking with our version numbers.
touch .scmversion

# Mangle /usr/bin/python shebangs to /usr/bin/python3
# Mangle all Python shebangs to be Python 3 explicitly
# -p preserves timestamps
# -n prevents creating ~backup files
# -i specifies the interpreter for the shebang
# This fixes errors such as
# *** ERROR: ambiguous python shebang in /usr/bin/kvm_stat: #!/usr/bin/python. Change it to python3 (or python2) explicitly.
# We patch all sources below for which we got a report/error.
pathfix.py -i "%{__python3} %{py3_shbang_opts}" -p -n \
	tools/kvm/kvm_stat/kvm_stat \
	scripts/show_delta \
	scripts/diffconfig \
	scripts/bloat-o-meter \
	scripts/jobserver-exec \
	tools \
	Documentation \
	scripts/clang-tools

# only deal with configs if we are going to build for the arch
%ifnarch %nobuildarches

if [ -L configs ]; then
	rm -f configs
fi
mkdir configs
cd configs

# Drop some necessary files from the source dir into the buildroot
cp $RPM_SOURCE_DIR/kernel-*.config .
cp %{SOURCE80} .
# merge.pl
cp %{SOURCE3000} .
# kernel-local
cp %{SOURCE3001} .
VERSION=%{version} ./generate_all_configs.sh %{primary_target} %{debugbuildsenabled}

# Merge in any user-provided local config option changes
%ifnarch %nobuildarches
for i in %{all_arch_configs}
do
  mv $i $i.tmp
  ./merge.pl %{SOURCE3001} $i.tmp > $i
%if %{with_gcov}
  echo "Merging with gcov options"
  cat %{SOURCE75}
  mv $i $i.tmp
  ./merge.pl %{SOURCE75} $i.tmp > $i
%endif
  rm $i.tmp
done
%endif

%if %{with clang_lto}
for i in *aarch64*.config *x86_64*.config; do
  sed -i 's/# CONFIG_LTO_CLANG_THIN is not set/CONFIG_LTO_CLANG_THIN=y/' $i
  sed -i 's/CONFIG_LTO_NONE=y/# CONFIG_LTO_NONE is not set/' $i
done
%endif

# Add DUP and kpatch certificates to system trusted keys for RHEL
%if 0%{?rhel}
%if %{signkernel}%{signmodules}
openssl x509 -inform der -in %{SOURCE90000} -out rockydup1.pem
openssl x509 -inform der -in %{SOURCE90001} -out rockykpatch1.pem
cat rockydup1.pem rockykpatch1.pem > ../certs/rocky.pem
%if %{signkernel}
%ifarch s390x ppc64le
openssl x509 -inform der -in %{secureboot_ca_0} -out secureboot.pem
cat secureboot.pem >> ../certs/rocky.pem
%endif
%endif
for i in *.config; do
  sed -i 's@CONFIG_SYSTEM_TRUSTED_KEYS=""@CONFIG_SYSTEM_TRUSTED_KEYS="certs/rocky.pem"@' $i
done
%endif
%endif

cp %{SOURCE81} .
OPTS=""
%if %{with_configchecks}
	OPTS="$OPTS -w -n -c"
%endif
%if %{with clang_lto}
for opt in %{clang_make_opts}; do
  OPTS="$OPTS -m $opt"
done
%endif
./process_configs.sh $OPTS kernel %{rpmversion}

cp %{SOURCE82} .
RPM_SOURCE_DIR=$RPM_SOURCE_DIR ./update_scripts.sh %{primary_target}

# end of kernel config
%endif

cd ..
# # End of Configs stuff

# get rid of unwanted files resulting from patch fuzz
find . \( -name "*.orig" -o -name "*~" \) -delete >/dev/null

# remove unnecessary SCM files
find . -name .gitignore -delete >/dev/null

cd ..

###
### build
###
%build

%if %{with_sparse}
%define sparse_mflags	C=1
%endif

cp_vmlinux()
{
  eu-strip --remove-comment -o "$2" "$1"
}

# Note we need to disable these flags for cross builds because the flags
# from redhat-rpm-config assume that host == target so target arch
# flags cause issues with the host compiler.
%if !%{with_cross}
%define build_hostcflags  %{?build_cflags}
%define build_hostldflags %{?build_ldflags}
%endif

%define make %{__make} %{?cross_opts} %{?make_opts} HOSTCFLAGS="%{?build_hostcflags}" HOSTLDFLAGS="%{?build_hostldflags}"

InitBuildVars() {
    # Initialize the kernel .config file and create some variables that are
    # needed for the actual build process.

    Variant=$1

    # Pick the right kernel config file
    Config=kernel-%{version}-%{_target_cpu}${Variant:+-${Variant}}.config
    DevelDir=/usr/src/kernels/%{KVERREL}${Variant:++${Variant}}

    KernelVer=%{version}-%{release}.%{_target_cpu}${Variant:++${Variant}}

    # make sure EXTRAVERSION says what we want it to say
    # Trim the release if this is a CI build, since KERNELVERSION is limited to 64 characters
    ShortRel=$(perl -e "print \"%{release}\" =~ s/\.pr\.[0-9A-Fa-f]{32}//r")
    perl -p -i -e "s/^EXTRAVERSION.*/EXTRAVERSION = -${ShortRel}.%{_target_cpu}${Variant:++${Variant}}/" Makefile

    # if pre-rc1 devel kernel, must fix up PATCHLEVEL for our versioning scheme
    # if we are post rc1 this should match anyway so this won't matter
    perl -p -i -e 's/^PATCHLEVEL.*/PATCHLEVEL = %{patchlevel}/' Makefile

    %{make} %{?_smp_mflags} mrproper
    cp configs/$Config .config

    %if %{signkernel}%{signmodules}
    cp $RPM_SOURCE_DIR/x509.genkey certs/.
    %endif

    Arch=`head -1 .config | cut -b 3-`
    echo USING ARCH=$Arch

    KCFLAGS="%{?kcflags}"

    # add kpatch flags for base kernel
    if [ "$Variant" == "" ]; then
        KCFLAGS="$KCFLAGS %{?kpatch_kcflags}"
    fi
}

BuildKernel() {
    MakeTarget=$1
    KernelImage=$2
    DoVDSO=$3
    Variant=$4
    InstallName=${5:-vmlinuz}

    DoModules=1
    if [ "$Variant" = "zfcpdump" ]; then
	    DoModules=0
    fi

    # When the bootable image is just the ELF kernel, strip it.
    # We already copy the unstripped file into the debuginfo package.
    if [ "$KernelImage" = vmlinux ]; then
      CopyKernel=cp_vmlinux
    else
      CopyKernel=cp
    fi

    InitBuildVars $Variant

    echo BUILDING A KERNEL FOR ${Variant} %{_target_cpu}...

    %{make} ARCH=$Arch olddefconfig >/dev/null

    # This ensures build-ids are unique to allow parallel debuginfo
    perl -p -i -e "s/^CONFIG_BUILD_SALT.*/CONFIG_BUILD_SALT=\"%{KVERREL}\"/" .config
    %{make} ARCH=$Arch KCFLAGS="$KCFLAGS" WITH_GCOV="%{?with_gcov}" %{?_smp_mflags} $MakeTarget %{?sparse_mflags} %{?kernel_mflags}
    if [ $DoModules -eq 1 ]; then
	%{make} ARCH=$Arch KCFLAGS="$KCFLAGS" WITH_GCOV="%{?with_gcov}" %{?_smp_mflags} modules %{?sparse_mflags} || exit 1
    fi

    mkdir -p $RPM_BUILD_ROOT/%{image_install_path}
    mkdir -p $RPM_BUILD_ROOT/lib/modules/$KernelVer
    mkdir -p $RPM_BUILD_ROOT/lib/modules/$KernelVer/systemtap
%if %{with_debuginfo}
    mkdir -p $RPM_BUILD_ROOT%{debuginfodir}/%{image_install_path}
%endif

%ifarch %{arm} aarch64
    %{make} ARCH=$Arch dtbs INSTALL_DTBS_PATH=$RPM_BUILD_ROOT/%{image_install_path}/dtb-$KernelVer
    %{make} ARCH=$Arch dtbs_install INSTALL_DTBS_PATH=$RPM_BUILD_ROOT/%{image_install_path}/dtb-$KernelVer
    cp -r $RPM_BUILD_ROOT/%{image_install_path}/dtb-$KernelVer $RPM_BUILD_ROOT/lib/modules/$KernelVer/dtb
    find arch/$Arch/boot/dts -name '*.dtb' -type f -delete
%endif

    # Start installing the results
    install -m 644 .config $RPM_BUILD_ROOT/boot/config-$KernelVer
    install -m 644 .config $RPM_BUILD_ROOT/lib/modules/$KernelVer/config
    install -m 644 System.map $RPM_BUILD_ROOT/boot/System.map-$KernelVer
    install -m 644 System.map $RPM_BUILD_ROOT/lib/modules/$KernelVer/System.map

    # We estimate the size of the initramfs because rpm needs to take this size
    # into consideration when performing disk space calculations. (See bz #530778)
    dd if=/dev/zero of=$RPM_BUILD_ROOT/boot/initramfs-$KernelVer.img bs=1M count=20

    if [ -f arch/$Arch/boot/zImage.stub ]; then
      cp arch/$Arch/boot/zImage.stub $RPM_BUILD_ROOT/%{image_install_path}/zImage.stub-$KernelVer || :
      cp arch/$Arch/boot/zImage.stub $RPM_BUILD_ROOT/lib/modules/$KernelVer/zImage.stub-$KernelVer || :
    fi

    %if %{signkernel}
    if [ "$KernelImage" = vmlinux ]; then
        # We can't strip and sign $KernelImage in place, because
        # we need to preserve original vmlinux for debuginfo.
        # Use a copy for signing.
        $CopyKernel $KernelImage $KernelImage.tosign
        KernelImage=$KernelImage.tosign
        CopyKernel=cp
    fi

    # Sign the image if we're using EFI
    # aarch64 kernels are gziped EFI images
    KernelExtension=${KernelImage##*.}
    if [ "$KernelExtension" == "gz" ]; then
        SignImage=${KernelImage%.*}
    else
        SignImage=$KernelImage
    fi

    %ifarch x86_64 aarch64
    %pesign -s -i $SignImage -o vmlinuz.signed -a %{secureboot_ca_0} -c %{secureboot_key_0} -n %{pesign_name_0}
    %endif
    %ifarch s390x ppc64le
    if [ -x /usr/bin/rpm-sign ]; then
	rpm-sign --key "%{pesign_name_0}" --lkmsign $SignImage --output vmlinuz.signed
    elif [ "$DoModules" == "1" -a "%{signmodules}" == "1" ]; then
	chmod +x scripts/sign-file
	./scripts/sign-file -p sha256 certs/signing_key.pem certs/signing_key.x509 $SignImage vmlinuz.signed
    else
	mv $SignImage vmlinuz.signed
    fi
    %endif

    if [ ! -s vmlinuz.signed ]; then
        echo "pesigning failed"
        exit 1
    fi
    mv vmlinuz.signed $SignImage
    if [ "$KernelExtension" == "gz" ]; then
        gzip -f9 $SignImage
    fi
    # signkernel
    %endif

    $CopyKernel $KernelImage \
                $RPM_BUILD_ROOT/%{image_install_path}/$InstallName-$KernelVer
    chmod 755 $RPM_BUILD_ROOT/%{image_install_path}/$InstallName-$KernelVer
    cp $RPM_BUILD_ROOT/%{image_install_path}/$InstallName-$KernelVer $RPM_BUILD_ROOT/lib/modules/$KernelVer/$InstallName

    # hmac sign the kernel for FIPS
    echo "Creating hmac file: $RPM_BUILD_ROOT/%{image_install_path}/.vmlinuz-$KernelVer.hmac"
    ls -l $RPM_BUILD_ROOT/%{image_install_path}/$InstallName-$KernelVer
    sha512hmac $RPM_BUILD_ROOT/%{image_install_path}/$InstallName-$KernelVer | sed -e "s,$RPM_BUILD_ROOT,," > $RPM_BUILD_ROOT/%{image_install_path}/.vmlinuz-$KernelVer.hmac;
    cp $RPM_BUILD_ROOT/%{image_install_path}/.vmlinuz-$KernelVer.hmac $RPM_BUILD_ROOT/lib/modules/$KernelVer/.vmlinuz.hmac

    if [ $DoModules -eq 1 ]; then
	# Override $(mod-fw) because we don't want it to install any firmware
	# we'll get it from the linux-firmware package and we don't want conflicts
	%{make} %{?_smp_mflags} ARCH=$Arch INSTALL_MOD_PATH=$RPM_BUILD_ROOT %{?_smp_mflags} modules_install KERNELRELEASE=$KernelVer mod-fw=
    fi

%if %{with_gcov}
    # install gcov-needed files to $BUILDROOT/$BUILD/...:
    #   gcov_info->filename is absolute path
    #   gcno references to sources can use absolute paths (e.g. in out-of-tree builds)
    #   sysfs symlink targets (set up at compile time) use absolute paths to BUILD dir
    find . \( -name '*.gcno' -o -name '*.[chS]' \) -exec install -D '{}' "$RPM_BUILD_ROOT/$(pwd)/{}" \;
%endif

    # add an a noop %%defattr statement 'cause rpm doesn't like empty file list files
    echo '%%defattr(-,-,-)' > ../kernel${Variant:+-${Variant}}-ldsoconf.list
    if [ $DoVDSO -ne 0 ]; then
        %{make} ARCH=$Arch INSTALL_MOD_PATH=$RPM_BUILD_ROOT vdso_install KERNELRELEASE=$KernelVer
        if [ -s ldconfig-kernel.conf ]; then
             install -D -m 444 ldconfig-kernel.conf \
                $RPM_BUILD_ROOT/etc/ld.so.conf.d/kernel-$KernelVer.conf
	     echo /etc/ld.so.conf.d/kernel-$KernelVer.conf >> ../kernel${Variant:+-${Variant}}-ldsoconf.list
        fi

        rm -rf $RPM_BUILD_ROOT/lib/modules/$KernelVer/vdso/.build-id
    fi

    # And save the headers/makefiles etc for building modules against
    #
    # This all looks scary, but the end result is supposed to be:
    # * all arch relevant include/ files
    # * all Makefile/Kconfig files
    # * all script/ files

    rm -f $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    rm -f $RPM_BUILD_ROOT/lib/modules/$KernelVer/source
    mkdir -p $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    (cd $RPM_BUILD_ROOT/lib/modules/$KernelVer ; ln -s build source)
    # dirs for additional modules per module-init-tools, kbuild/modules.txt
    mkdir -p $RPM_BUILD_ROOT/lib/modules/$KernelVer/updates
    mkdir -p $RPM_BUILD_ROOT/lib/modules/$KernelVer/weak-updates
    # CONFIG_KERNEL_HEADER_TEST generates some extra files in the process of
    # testing so just delete
    find . -name *.h.s -delete
    # first copy everything
    cp --parents `find  -type f -name "Makefile*" -o -name "Kconfig*"` $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    if [ ! -e Module.symvers ]; then
        touch Module.symvers
    fi
    cp Module.symvers $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp System.map $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    if [ -s Module.markers ]; then
      cp Module.markers $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    fi

    # create the kABI metadata for use in packaging
    # NOTENOTE: the name symvers is used by the rpm backend
    # NOTENOTE: to discover and run the /usr/lib/rpm/fileattrs/kabi.attr
    # NOTENOTE: script which dynamically adds exported kernel symbol
    # NOTENOTE: checksums to the rpm metadata provides list.
    # NOTENOTE: if you change the symvers name, update the backend too
    echo "**** GENERATING kernel ABI metadata ****"
    gzip -c9 < Module.symvers > $RPM_BUILD_ROOT/boot/symvers-$KernelVer.gz
    cp $RPM_BUILD_ROOT/boot/symvers-$KernelVer.gz $RPM_BUILD_ROOT/lib/modules/$KernelVer/symvers.gz

%if %{with_kabichk}
    echo "**** kABI checking is enabled in kernel SPEC file. ****"
    chmod 0755 $RPM_SOURCE_DIR/check-kabi
    if [ -e $RPM_SOURCE_DIR/Module.kabi_%{_target_cpu}$Variant ]; then
        cp $RPM_SOURCE_DIR/Module.kabi_%{_target_cpu}$Variant $RPM_BUILD_ROOT/Module.kabi
        $RPM_SOURCE_DIR/check-kabi -k $RPM_BUILD_ROOT/Module.kabi -s Module.symvers || exit 1
        # for now, don't keep it around.
        rm $RPM_BUILD_ROOT/Module.kabi
    else
        echo "**** NOTE: Cannot find reference Module.kabi file. ****"
    fi
%endif

%if %{with_kabidupchk}
    echo "**** kABI DUP checking is enabled in kernel SPEC file. ****"
    if [ -e $RPM_SOURCE_DIR/Module.kabi_dup_%{_target_cpu}$Variant ]; then
        cp $RPM_SOURCE_DIR/Module.kabi_dup_%{_target_cpu}$Variant $RPM_BUILD_ROOT/Module.kabi
        $RPM_SOURCE_DIR/check-kabi -k $RPM_BUILD_ROOT/Module.kabi -s Module.symvers || exit 1
        # for now, don't keep it around.
        rm $RPM_BUILD_ROOT/Module.kabi
    else
        echo "**** NOTE: Cannot find DUP reference Module.kabi file. ****"
    fi
%endif

%if %{with_kabidw_base}
    # Don't build kabi base for debug kernels
    if [ "$Variant" != "zfcpdump" -a "$Variant" != "debug" ]; then
        mkdir -p $RPM_BUILD_ROOT/kabi-dwarf
        tar xjvf %{SOURCE301} -C $RPM_BUILD_ROOT/kabi-dwarf

        mkdir -p $RPM_BUILD_ROOT/kabi-dwarf/stablelists
        tar xjvf %{SOURCE300} -C $RPM_BUILD_ROOT/kabi-dwarf/stablelists

        echo "**** GENERATING DWARF-based kABI baseline dataset ****"
        chmod 0755 $RPM_BUILD_ROOT/kabi-dwarf/run_kabi-dw.sh
        $RPM_BUILD_ROOT/kabi-dwarf/run_kabi-dw.sh generate \
            "$RPM_BUILD_ROOT/kabi-dwarf/stablelists/kabi-current/kabi_stablelist_%{_target_cpu}" \
            "$(pwd)" \
            "$RPM_BUILD_ROOT/kabidw-base/%{_target_cpu}${Variant:+.${Variant}}" || :

        rm -rf $RPM_BUILD_ROOT/kabi-dwarf
    fi
%endif

%if %{with_kabidwchk}
    if [ "$Variant" != "zfcpdump" ]; then
        mkdir -p $RPM_BUILD_ROOT/kabi-dwarf
        tar xjvf %{SOURCE301} -C $RPM_BUILD_ROOT/kabi-dwarf
        if [ -d "$RPM_BUILD_ROOT/kabi-dwarf/base/%{_target_cpu}${Variant:+.${Variant}}" ]; then
            mkdir -p $RPM_BUILD_ROOT/kabi-dwarf/stablelists
            tar xjvf %{SOURCE300} -C $RPM_BUILD_ROOT/kabi-dwarf/stablelists

            echo "**** GENERATING DWARF-based kABI dataset ****"
            chmod 0755 $RPM_BUILD_ROOT/kabi-dwarf/run_kabi-dw.sh
            $RPM_BUILD_ROOT/kabi-dwarf/run_kabi-dw.sh generate \
                "$RPM_BUILD_ROOT/kabi-dwarf/stablelists/kabi-current/kabi_stablelist_%{_target_cpu}" \
                "$(pwd)" \
                "$RPM_BUILD_ROOT/kabi-dwarf/base/%{_target_cpu}${Variant:+.${Variant}}.tmp" || :

            echo "**** kABI DWARF-based comparison report ****"
            $RPM_BUILD_ROOT/kabi-dwarf/run_kabi-dw.sh compare \
                "$RPM_BUILD_ROOT/kabi-dwarf/base/%{_target_cpu}${Variant:+.${Variant}}" \
                "$RPM_BUILD_ROOT/kabi-dwarf/base/%{_target_cpu}${Variant:+.${Variant}}.tmp" || :
            echo "**** End of kABI DWARF-based comparison report ****"
        else
            echo "**** Baseline dataset for kABI DWARF-BASED comparison report not found ****"
        fi

        rm -rf $RPM_BUILD_ROOT/kabi-dwarf
    fi
%endif

    # then drop all but the needed Makefiles/Kconfig files
    rm -rf $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/scripts
    rm -rf $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/include
    cp .config $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp -a scripts $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    rm -rf $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/scripts/tracing
    rm -f $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/scripts/spdxcheck.py

    # Files for 'make scripts' to succeed with kernel-devel.
    mkdir -p $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/security/selinux/include
    cp -a --parents security/selinux/include/classmap.h $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp -a --parents security/selinux/include/initial_sid_to_string.h $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    mkdir -p $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/tools/include/tools
    cp -a --parents tools/include/tools/be_byteshift.h $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp -a --parents tools/include/tools/le_byteshift.h $RPM_BUILD_ROOT/lib/modules/$KernelVer/build

    # Files for 'make prepare' to succeed with kernel-devel.
    cp -a --parents tools/include/linux/compiler* $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp -a --parents tools/include/linux/types.h $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp -a --parents tools/build/Build.include $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp --parents tools/build/Build $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp --parents tools/build/fixdep.c $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp --parents tools/objtool/sync-check.sh $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp -a --parents tools/bpf/resolve_btfids $RPM_BUILD_ROOT/lib/modules/$KernelVer/build

    cp --parents security/selinux/include/policycap_names.h $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp --parents security/selinux/include/policycap.h $RPM_BUILD_ROOT/lib/modules/$KernelVer/build

    cp -a --parents tools/include/asm-generic $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp -a --parents tools/include/linux $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp -a --parents tools/include/uapi/asm $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp -a --parents tools/include/uapi/asm-generic $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp -a --parents tools/include/uapi/linux $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp -a --parents tools/include/vdso $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp --parents tools/scripts/utilities.mak $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp -a --parents tools/lib/subcmd $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp --parents tools/lib/*.c $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp --parents tools/objtool/*.[ch] $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp --parents tools/objtool/Build $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp --parents tools/objtool/include/objtool/*.h $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp -a --parents tools/lib/bpf $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp --parents tools/lib/bpf/Build $RPM_BUILD_ROOT/lib/modules/$KernelVer/build

    if [ -f tools/objtool/objtool ]; then
      cp -a tools/objtool/objtool $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/tools/objtool/ || :
    fi
    if [ -f tools/objtool/fixdep ]; then
      cp -a tools/objtool/fixdep $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/tools/objtool/ || :
    fi
    if [ -d arch/$Arch/scripts ]; then
      cp -a arch/$Arch/scripts $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/arch/%{_arch} || :
    fi
    if [ -f arch/$Arch/*lds ]; then
      cp -a arch/$Arch/*lds $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/arch/%{_arch}/ || :
    fi
    if [ -f arch/%{asmarch}/kernel/module.lds ]; then
      cp -a --parents arch/%{asmarch}/kernel/module.lds $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/
    fi
    find $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/scripts \( -iname "*.o" -o -iname "*.cmd" \) -exec rm -f {} +
%ifarch ppc64le
    cp -a --parents arch/powerpc/lib/crtsavres.[So] $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/
%endif
    if [ -d arch/%{asmarch}/include ]; then
      cp -a --parents arch/%{asmarch}/include $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/
    fi
%ifarch aarch64
    # arch/arm64/include/asm/xen references arch/arm
    cp -a --parents arch/arm/include/asm/xen $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/
    # arch/arm64/include/asm/opcodes.h references arch/arm
    cp -a --parents arch/arm/include/asm/opcodes.h $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/
%endif
    # include the machine specific headers for ARM variants, if available.
%ifarch %{arm}
    if [ -d arch/%{asmarch}/mach-${Variant}/include ]; then
      cp -a --parents arch/%{asmarch}/mach-${Variant}/include $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/
    fi
    # include a few files for 'make prepare'
    cp -a --parents arch/arm/tools/gen-mach-types $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/
    cp -a --parents arch/arm/tools/mach-types $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/

%endif
    cp -a include $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/include
%ifarch i686 x86_64
    # files for 'make prepare' to succeed with kernel-devel
    cp -a --parents arch/x86/entry/syscalls/syscall_32.tbl $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/
    cp -a --parents arch/x86/entry/syscalls/syscall_64.tbl $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/
    cp -a --parents arch/x86/tools/relocs_32.c $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/
    cp -a --parents arch/x86/tools/relocs_64.c $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/
    cp -a --parents arch/x86/tools/relocs.c $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/
    cp -a --parents arch/x86/tools/relocs_common.c $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/
    cp -a --parents arch/x86/tools/relocs.h $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/
    cp -a --parents arch/x86/purgatory/purgatory.c $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/
    cp -a --parents arch/x86/purgatory/stack.S $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/
    cp -a --parents arch/x86/purgatory/setup-x86_64.S $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/
    cp -a --parents arch/x86/purgatory/entry64.S $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/
    cp -a --parents arch/x86/boot/string.h $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/
    cp -a --parents arch/x86/boot/string.c $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/
    cp -a --parents arch/x86/boot/ctype.h $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/

    cp -a --parents scripts/syscalltbl.sh $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/
    cp -a --parents scripts/syscallhdr.sh $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/

    cp -a --parents tools/arch/x86/include/asm $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp -a --parents tools/arch/x86/include/uapi/asm $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp -a --parents tools/objtool/arch/x86/lib $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp -a --parents tools/arch/x86/lib/ $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp -a --parents tools/arch/x86/tools/gen-insn-attr-x86.awk $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp -a --parents tools/objtool/arch/x86/ $RPM_BUILD_ROOT/lib/modules/$KernelVer/build

%endif
    # Clean up intermediate tools files
    find $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/tools \( -iname "*.o" -o -iname "*.cmd" \) -exec rm -f {} +

    # Make sure the Makefile and version.h have a matching timestamp so that
    # external modules can be built
    touch -r $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/Makefile $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/include/generated/uapi/linux/version.h

    # Copy .config to include/config/auto.conf so "make prepare" is unnecessary.
    cp $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/.config $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/include/config/auto.conf

%if %{with_debuginfo}
    eu-readelf -n vmlinux | grep "Build ID" | awk '{print $NF}' > vmlinux.id
    cp vmlinux.id $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/vmlinux.id

    #
    # save the vmlinux file for kernel debugging into the kernel-debuginfo rpm
    #
    mkdir -p $RPM_BUILD_ROOT%{debuginfodir}/lib/modules/$KernelVer
    cp vmlinux $RPM_BUILD_ROOT%{debuginfodir}/lib/modules/$KernelVer
    if [ -n "%{vmlinux_decompressor}" ]; then
	    eu-readelf -n  %{vmlinux_decompressor} | grep "Build ID" | awk '{print $NF}' > vmlinux.decompressor.id
	    # Without build-id the build will fail. But for s390 the build-id
	    # wasn't added before 5.11. In case it is missing prefer not
	    # packaging the debuginfo over a build failure.
	    if [ -s vmlinux.decompressor.id ]; then
		    cp vmlinux.decompressor.id $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/vmlinux.decompressor.id
		    cp %{vmlinux_decompressor} $RPM_BUILD_ROOT%{debuginfodir}/lib/modules/$KernelVer/vmlinux.decompressor
	    fi
    fi
%endif

    find $RPM_BUILD_ROOT/lib/modules/$KernelVer -name "*.ko" -type f >modnames

    # mark modules executable so that strip-to-file can strip them
    xargs --no-run-if-empty chmod u+x < modnames

    # Generate a list of modules for block and networking.

    grep -F /drivers/ modnames | xargs --no-run-if-empty nm -upA |
    sed -n 's,^.*/\([^/]*\.ko\):  *U \(.*\)$,\1 \2,p' > drivers.undef

    collect_modules_list()
    {
      sed -r -n -e "s/^([^ ]+) \\.?($2)\$/\\1/p" drivers.undef |
        LC_ALL=C sort -u > $RPM_BUILD_ROOT/lib/modules/$KernelVer/modules.$1
      if [ ! -z "$3" ]; then
        sed -r -e "/^($3)\$/d" -i $RPM_BUILD_ROOT/lib/modules/$KernelVer/modules.$1
      fi
    }

    collect_modules_list networking \
      'register_netdev|ieee80211_register_hw|usbnet_probe|phy_driver_register|rt(l_|2x00)(pci|usb)_probe|register_netdevice'
    collect_modules_list block \
      'ata_scsi_ioctl|scsi_add_host|scsi_add_host_with_dma|blk_alloc_queue|blk_init_queue|register_mtd_blktrans|scsi_esp_register|scsi_register_device_handler|blk_queue_physical_block_size' 'pktcdvd.ko|dm-mod.ko'
    collect_modules_list drm \
      'drm_open|drm_init'
    collect_modules_list modesetting \
      'drm_crtc_init'

    # detect missing or incorrect license tags
    ( find $RPM_BUILD_ROOT/lib/modules/$KernelVer -name '*.ko' | xargs /sbin/modinfo -l | \
        grep -E -v 'GPL( v2)?$|Dual BSD/GPL$|Dual MPL/GPL$|GPL and additional rights$' ) && exit 1

    remove_depmod_files()
    {
        # remove files that will be auto generated by depmod at rpm -i time
        pushd $RPM_BUILD_ROOT/lib/modules/$KernelVer/
            rm -f modules.{alias,alias.bin,builtin.alias.bin,builtin.bin} \
                  modules.{dep,dep.bin,devname,softdep,symbols,symbols.bin}
        popd
    }

    remove_depmod_files

    # Identify modules in the kernel-modules-extras package
    %{SOURCE20} $RPM_BUILD_ROOT lib/modules/$KernelVer $RPM_SOURCE_DIR/mod-extra.list
    # Identify modules in the kernel-modules-extras package
    %{SOURCE20} $RPM_BUILD_ROOT lib/modules/$KernelVer %{SOURCE84} internal

    #
    # Generate the kernel-core and kernel-modules files lists
    #

    # Copy the System.map file for depmod to use, and create a backup of the
    # full module tree so we can restore it after we're done filtering
    cp System.map $RPM_BUILD_ROOT/.
    pushd $RPM_BUILD_ROOT
    mkdir restore
    cp -r lib/modules/$KernelVer/* restore/.

    # don't include anything going into kernel-modules-extra in the file lists
    xargs rm -rf < mod-extra.list
    # don't include anything going int kernel-modules-internal in the file lists
    xargs rm -rf < mod-internal.list

    if [ $DoModules -eq 1 ]; then
	# Find all the module files and filter them out into the core and
	# modules lists.  This actually removes anything going into -modules
	# from the dir.
	find lib/modules/$KernelVer/kernel -name *.ko | sort -n > modules.list
	cp $RPM_SOURCE_DIR/filter-*.sh .
	./filter-modules.sh modules.list %{_target_cpu}
	rm filter-*.sh

	# Run depmod on the resulting module tree and make sure it isn't broken
	depmod -b . -aeF ./System.map $KernelVer &> depmod.out
	if [ -s depmod.out ]; then
	    echo "Depmod failure"
	    cat depmod.out
	    exit 1
	else
	    rm depmod.out
	fi
    else
	# Ensure important files/directories exist to let the packaging succeed
	echo '%%defattr(-,-,-)' > modules.list
	echo '%%defattr(-,-,-)' > k-d.list
	mkdir -p lib/modules/$KernelVer/kernel
	# Add files usually created by make modules, needed to prevent errors
	# thrown by depmod during package installation
	touch lib/modules/$KernelVer/modules.order
	touch lib/modules/$KernelVer/modules.builtin
    fi

    remove_depmod_files

    # Go back and find all of the various directories in the tree.  We use this
    # for the dir lists in kernel-core
    find lib/modules/$KernelVer/kernel -mindepth 1 -type d | sort -n > module-dirs.list

    # Cleanup
    rm System.map
    cp -r restore/* lib/modules/$KernelVer/.
    rm -rf restore
    popd

    # Make sure the files lists start with absolute paths or rpmbuild fails.
    # Also add in the dir entries
    sed -e 's/^lib*/\/lib/' %{?zipsed} $RPM_BUILD_ROOT/k-d.list > ../kernel${Variant:+-${Variant}}-modules.list
    sed -e 's/^lib*/%dir \/lib/' %{?zipsed} $RPM_BUILD_ROOT/module-dirs.list > ../kernel${Variant:+-${Variant}}-core.list
    sed -e 's/^lib*/\/lib/' %{?zipsed} $RPM_BUILD_ROOT/modules.list >> ../kernel${Variant:+-${Variant}}-core.list
    sed -e 's/^lib*/\/lib/' %{?zipsed} $RPM_BUILD_ROOT/mod-extra.list >> ../kernel${Variant:+-${Variant}}-modules-extra.list
    sed -e 's/^lib*/\/lib/' %{?zipsed} $RPM_BUILD_ROOT/mod-internal.list >> ../kernel${Variant:+-${Variant}}-modules-internal.list

    # Cleanup
    rm -f $RPM_BUILD_ROOT/k-d.list
    rm -f $RPM_BUILD_ROOT/modules.list
    rm -f $RPM_BUILD_ROOT/module-dirs.list
    rm -f $RPM_BUILD_ROOT/mod-extra.list
    rm -f $RPM_BUILD_ROOT/mod-internal.list

    # Move the devel headers out of the root file system
    mkdir -p $RPM_BUILD_ROOT/usr/src/kernels
    mv $RPM_BUILD_ROOT/lib/modules/$KernelVer/build $RPM_BUILD_ROOT/$DevelDir

    # This is going to create a broken link during the build, but we don't use
    # it after this point.  We need the link to actually point to something
    # when kernel-devel is installed, and a relative link doesn't work across
    # the F17 UsrMove feature.
    ln -sf $DevelDir $RPM_BUILD_ROOT/lib/modules/$KernelVer/build

%ifnarch armv7hl
    # Generate vmlinux.h and put it to kernel-devel path
    bpftool btf dump file vmlinux format c > $RPM_BUILD_ROOT/$DevelDir/vmlinux.h
%endif

    # prune junk from kernel-devel
    find $RPM_BUILD_ROOT/usr/src/kernels -name ".*.cmd" -delete

    # Rocky UEFI Secure Boot CA cert, which can be used to authenticate the kernel
    mkdir -p $RPM_BUILD_ROOT%{_datadir}/doc/kernel-keys/$KernelVer
%if %{signkernel}
    install -m 0644 %{secureboot_ca_0} $RPM_BUILD_ROOT%{_datadir}/doc/kernel-keys/$KernelVer/kernel-signing-ca.cer
    %ifarch s390x ppc64le
    if [ -x /usr/bin/rpm-sign ]; then
        install -m 0644 %{secureboot_key_0} $RPM_BUILD_ROOT%{_datadir}/doc/kernel-keys/$KernelVer/%{signing_key_filename}
    fi
    %endif
%endif

%if %{signmodules}
    if [ $DoModules -eq 1 ]; then
        # Save the signing keys so we can sign the modules in __modsign_install_post
        cp certs/signing_key.pem certs/signing_key.pem.sign${Variant:++${Variant}}
        cp certs/signing_key.x509 certs/signing_key.x509.sign${Variant:++${Variant}}
        %ifarch s390x ppc64le
        if [ ! -x /usr/bin/rpm-sign ]; then
            install -m 0644 certs/signing_key.x509.sign${Variant:++${Variant}} $RPM_BUILD_ROOT%{_datadir}/doc/kernel-keys/$KernelVer/kernel-signing-ca.cer
            openssl x509 -in certs/signing_key.pem.sign${Variant:++${Variant}} -outform der -out $RPM_BUILD_ROOT%{_datadir}/doc/kernel-keys/$KernelVer/%{signing_key_filename}
            chmod 0644 $RPM_BUILD_ROOT%{_datadir}/doc/kernel-keys/$KernelVer/%{signing_key_filename}
        fi
        %endif
    fi
%endif

%if %{with_ipaclones}
    MAXPROCS=$(echo %{?_smp_mflags} | sed -n 's/-j\s*\([0-9]\+\)/\1/p')
    if [ -z "$MAXPROCS" ]; then
        MAXPROCS=1
    fi
    if [ "$Variant" == "" ]; then
        mkdir -p $RPM_BUILD_ROOT/$DevelDir-ipaclones
        find . -name '*.ipa-clones' | xargs -i{} -r -n 1 -P $MAXPROCS install -m 644 -D "{}" "$RPM_BUILD_ROOT/$DevelDir-ipaclones/{}"
    fi
%endif

}

###
# DO it...
###

# prepare directories
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT/boot
mkdir -p $RPM_BUILD_ROOT%{_libexecdir}

cd linux-%{KVERREL}


%if %{with_debug}
BuildKernel %make_target %kernel_image %{_use_vdso} debug
%endif

%if %{with_zfcpdump}
BuildKernel %make_target %kernel_image %{_use_vdso} zfcpdump
%endif

%if %{with_pae}
BuildKernel %make_target %kernel_image %{use_vdso} lpae
%endif

%if %{with_up}
BuildKernel %make_target %kernel_image %{_use_vdso}
%endif

%ifnarch noarch i686
%if !%{with_debug} && !%{with_zfcpdump} && !%{with_pae} && !%{with_up}
# If only building the user space tools, then initialize the build environment
# and some variables so that the various userspace tools can be built.
InitBuildVars
%endif
%endif

%ifarch aarch64
%global perf_build_extra_opts CORESIGHT=1
%endif
%global perf_make \
  %{__make} %{?make_opts} EXTRA_CFLAGS="${RPM_OPT_FLAGS}" LDFLAGS="%{__global_ldflags} -Wl,-E" %{?cross_opts} -C tools/perf V=1 NO_PERF_READ_VDSO32=1 NO_PERF_READ_VDSOX32=1 WERROR=0 NO_LIBUNWIND=1 HAVE_CPLUS_DEMANGLE=1 NO_GTK2=1 NO_STRLCPY=1 NO_BIONIC=1 LIBBPF_DYNAMIC=1 LIBTRACEEVENT_DYNAMIC=1 %{?perf_build_extra_opts} prefix=%{_prefix} PYTHON=%{__python3}
%if %{with_perf}
# perf
# make sure check-headers.sh is executable
chmod +x tools/perf/check-headers.sh
%{perf_make} DESTDIR=$RPM_BUILD_ROOT all
%endif

%global tools_make \
  %{make} CFLAGS="${RPM_OPT_FLAGS}" LDFLAGS="%{__global_ldflags}" %{?make_opts}

%if %{with_tools}
%ifarch %{cpupowerarchs}
# cpupower
# make sure version-gen.sh is executable.
chmod +x tools/power/cpupower/utils/version-gen.sh
%{tools_make} %{?_smp_mflags} -C tools/power/cpupower CPUFREQ_BENCH=false DEBUG=false
%ifarch x86_64
    pushd tools/power/cpupower/debug/x86_64
    %{tools_make} %{?_smp_mflags} centrino-decode powernow-k8-decode
    popd
%endif
%ifarch x86_64
   pushd tools/power/x86/x86_energy_perf_policy/
   %{tools_make}
   popd
   pushd tools/power/x86/turbostat
   %{tools_make}
   popd
   pushd tools/power/x86/intel-speed-select
   %{make}
   popd
%endif
%endif
pushd tools/thermal/tmon/
%{tools_make}
popd
pushd tools/iio/
%{tools_make}
popd
pushd tools/gpio/
%{tools_make}
popd
# build VM tools
pushd tools/vm/
%{tools_make} slabinfo page_owner_sort
popd
%endif

if [ -f $DevelDir/vmlinux.h ]; then
  RPM_VMLINUX_H=$DevelDir/vmlinux.h
fi

%global bpftool_make \
  %{__make} EXTRA_CFLAGS="${RPM_OPT_FLAGS}" EXTRA_LDFLAGS="%{__global_ldflags}" DESTDIR=$RPM_BUILD_ROOT %{?make_opts} VMLINUX_H="${RPM_VMLINUX_H}" V=1
%if %{with_bpftool}
pushd tools/bpf/bpftool
%{bpftool_make}
popd
%endif

%if %{with_selftests}
# Unfortunately, samples/bpf/Makefile expects that the headers are installed
# in the source tree. We installed them previously to $RPM_BUILD_ROOT/usr
# but there's no way to tell the Makefile to take them from there.
%{make} %{?_smp_mflags} headers_install

# If we re building only tools without kernel, we need to generate config
# headers and prepare tree for modules building. The modules_prepare target
# will cover both.
if [ ! -f include/generated/autoconf.h ]; then
   %{make} %{?_smp_mflags} modules_prepare
fi

%{make} %{?_smp_mflags} ARCH=$Arch V=1 M=samples/bpf/

# Prevent bpf selftests to build bpftool repeatedly:
export BPFTOOL=$(pwd)/tools/bpf/bpftool/bpftool

pushd tools/testing/selftests
# We need to install here because we need to call make with ARCH set which
# doesn't seem possible to do in the install section.
%{make} %{?_smp_mflags} ARCH=$Arch V=1 TARGETS="bpf livepatch net net/forwarding net/mptcp netfilter tc-testing memfd" SKIP_TARGETS="" FORCE_TARGETS=1 INSTALL_PATH=%{buildroot}%{_libexecdir}/kselftests VMLINUX_H="${RPM_VMLINUX_H}" install

# 'make install' for bpf is broken and upstream refuses to fix it.
# Install the needed files manually.
for dir in bpf bpf/no_alu32 bpf/progs; do
	# In ARK, the rpm build continues even if some of the selftests
	# cannot be built. It's not always possible to build selftests,
	# as upstream sometimes dependens on too new llvm version or has
	# other issues. If something did not get built, just skip it.
	test -d $dir || continue
	mkdir -p %{buildroot}%{_libexecdir}/kselftests/$dir
	find $dir -maxdepth 1 -type f \( -executable -o -name '*.py' -o -name settings -o \
		-name 'btf_dump_test_case_*.c' -o -name '*.ko' -o \
		-name '*.o' -exec sh -c 'readelf -h "{}" | grep -q "^  Machine:.*BPF"' \; \) -print0 | \
	xargs -0 cp -t %{buildroot}%{_libexecdir}/kselftests/$dir || true
done
popd
export -n BPFTOOL
%endif

%if %{with_doc}
# Make the HTML pages.
%{__make} PYTHON=/usr/bin/python3 htmldocs || %{doc_build_fail}

# sometimes non-world-readable files sneak into the kernel source tree
chmod -R a=rX Documentation
find Documentation -type d | xargs chmod u+w
%endif

# In the modsign case, we do 3 things.  1) We check the "variant" and hard
# code the value in the following invocations.  This is somewhat sub-optimal
# but we're doing this inside of an RPM macro and it isn't as easy as it
# could be because of that.  2) We restore the .tmp_versions/ directory from
# the one we saved off in BuildKernel above.  This is to make sure we're
# signing the modules we actually built/installed in that variant.  3) We
# grab the arch and invoke mod-sign.sh command to actually sign the modules.
#
# We have to do all of those things _after_ find-debuginfo runs, otherwise
# that will strip the signature off of the modules.
#
# Don't sign modules for the zfcpdump variant as it is monolithic.

%define __modsign_install_post \
  if [ "%{signmodules}" -eq "1" ]; then \
    if [ "%{with_pae}" -ne "0" ]; then \
       %{modsign_cmd} certs/signing_key.pem.sign+lpae certs/signing_key.x509.sign+lpae $RPM_BUILD_ROOT/lib/modules/%{KVERREL}+lpae/ \
    fi \
    if [ "%{with_debug}" -ne "0" ]; then \
      %{modsign_cmd} certs/signing_key.pem.sign+debug certs/signing_key.x509.sign+debug $RPM_BUILD_ROOT/lib/modules/%{KVERREL}+debug/ \
    fi \
    if [ "%{with_up}" -ne "0" ]; then \
      %{modsign_cmd} certs/signing_key.pem.sign certs/signing_key.x509.sign $RPM_BUILD_ROOT/lib/modules/%{KVERREL}/ \
    fi \
  fi \
  if [ "%{zipmodules}" -eq "1" ]; then \
    find $RPM_BUILD_ROOT/lib/modules/ -type f -name '*.ko' | xargs -P%{zcpu} xz; \
  fi \
%{nil}

###
### Special hacks for debuginfo subpackages.
###

# This macro is used by %%install, so we must redefine it before that.
%define debug_package %{nil}

%if %{with_debuginfo}

%ifnarch noarch
%global __debug_package 1
%files -f debugfiles.list debuginfo-common-%{_target_cpu}
%endif

%endif

# We don't want to package debuginfo for self-tests and samples but
# we have to delete them to avoid an error messages about unpackaged
# files.
# Delete the debuginfo for kernel-devel files
%define __remove_unwanted_dbginfo_install_post \
  if [ "%{with_selftests}" -ne "0" ]; then \
    rm -rf $RPM_BUILD_ROOT/usr/lib/debug/usr/libexec/ksamples; \
    rm -rf $RPM_BUILD_ROOT/usr/lib/debug/usr/libexec/kselftests; \
  fi \
  rm -rf $RPM_BUILD_ROOT/usr/lib/debug/usr/src; \
%{nil}

#
# Disgusting hack alert! We need to ensure we sign modules *after* all
# invocations of strip occur, which is in __debug_install_post if
# find-debuginfo.sh runs, and __os_install_post if not.
#
%define __spec_install_post \
  %{?__debug_package:%{__debug_install_post}}\
  %{__arch_install_post}\
  %{__os_install_post}\
  %{__remove_unwanted_dbginfo_install_post}\
  %{__modsign_install_post}

###
### install
###

%install

cd linux-%{KVERREL}

%if %{with_doc}
docdir=$RPM_BUILD_ROOT%{_datadir}/doc/kernel-doc-%{rpmversion}-%{pkgrelease}

# copy the source over
mkdir -p $docdir
tar -h -f - --exclude=man --exclude='.*' -c Documentation | tar xf - -C $docdir

# with_doc
%endif

# We have to do the headers install before the tools install because the
# kernel headers_install will remove any header files in /usr/include that
# it doesn't install itself.

%if %{with_headers}
# Install kernel headers
%{__make} ARCH=%{hdrarch} INSTALL_HDR_PATH=$RPM_BUILD_ROOT/usr headers_install

find $RPM_BUILD_ROOT/usr/include \
     \( -name .install -o -name .check -o \
        -name ..install.cmd -o -name ..check.cmd \) -delete

%endif

%if %{with_cross_headers}
%if 0%{?fedora}
HDR_ARCH_LIST='arm arm64 powerpc s390 x86'
%else
HDR_ARCH_LIST='arm64 powerpc s390 x86'
%endif
mkdir -p $RPM_BUILD_ROOT/usr/tmp-headers

for arch in $HDR_ARCH_LIST; do
	mkdir $RPM_BUILD_ROOT/usr/tmp-headers/arch-${arch}
	%{__make} ARCH=${arch} INSTALL_HDR_PATH=$RPM_BUILD_ROOT/usr/tmp-headers/arch-${arch} headers_install
done

find $RPM_BUILD_ROOT/usr/tmp-headers \
     \( -name .install -o -name .check -o \
        -name ..install.cmd -o -name ..check.cmd \) -delete

# Copy all the architectures we care about to their respective asm directories
for arch in $HDR_ARCH_LIST ; do
	mkdir -p $RPM_BUILD_ROOT/usr/${arch}-linux-gnu/include
	mv $RPM_BUILD_ROOT/usr/tmp-headers/arch-${arch}/include/* $RPM_BUILD_ROOT/usr/${arch}-linux-gnu/include/
done

rm -rf $RPM_BUILD_ROOT/usr/tmp-headers
%endif

%if %{with_kernel_abi_stablelists}
# kabi directory
INSTALL_KABI_PATH=$RPM_BUILD_ROOT/lib/modules/
mkdir -p $INSTALL_KABI_PATH

# install kabi releases directories
tar xjvf %{SOURCE300} -C $INSTALL_KABI_PATH
# with_kernel_abi_stablelists
%endif

%if %{with_perf}
# perf tool binary and supporting scripts/binaries
%{perf_make} DESTDIR=$RPM_BUILD_ROOT lib=%{_lib} install-bin
# remove the 'trace' symlink.
rm -f %{buildroot}%{_bindir}/trace

# For both of the below, yes, this should be using a macro but right now
# it's hard coded and we don't actually want it anyway right now.
# Whoever wants examples can fix it up!

# remove examples
rm -rf %{buildroot}/usr/lib/perf/examples
rm -rf %{buildroot}/usr/lib/perf/include

# python-perf extension
%{perf_make} DESTDIR=$RPM_BUILD_ROOT install-python_ext

# perf man pages (note: implicit rpm magic compresses them later)
mkdir -p %{buildroot}/%{_mandir}/man1
%{perf_make} DESTDIR=$RPM_BUILD_ROOT install-man

# remove any tracevent files, eg. its plugins still gets built and installed,
# even if we build against system's libtracevent during perf build (by setting
# LIBTRACEEVENT_DYNAMIC=1 above in perf_make macro). Those files should already
# ship with libtraceevent package.
rm -rf %{buildroot}%{_libdir}/traceevent
%endif

%if %{with_tools}
%ifarch %{cpupowerarchs}
%{make} -C tools/power/cpupower DESTDIR=$RPM_BUILD_ROOT libdir=%{_libdir} mandir=%{_mandir} CPUFREQ_BENCH=false install
rm -f %{buildroot}%{_libdir}/*.{a,la}
%find_lang cpupower
mv cpupower.lang ../
%ifarch x86_64
    pushd tools/power/cpupower/debug/x86_64
    install -m755 centrino-decode %{buildroot}%{_bindir}/centrino-decode
    install -m755 powernow-k8-decode %{buildroot}%{_bindir}/powernow-k8-decode
    popd
%endif
chmod 0755 %{buildroot}%{_libdir}/libcpupower.so*
mkdir -p %{buildroot}%{_unitdir} %{buildroot}%{_sysconfdir}/sysconfig
install -m644 %{SOURCE2000} %{buildroot}%{_unitdir}/cpupower.service
install -m644 %{SOURCE2001} %{buildroot}%{_sysconfdir}/sysconfig/cpupower
%endif
%ifarch x86_64
   mkdir -p %{buildroot}%{_mandir}/man8
   pushd tools/power/x86/x86_energy_perf_policy
   %{tools_make} DESTDIR=%{buildroot} install
   popd
   pushd tools/power/x86/turbostat
   %{tools_make} DESTDIR=%{buildroot} install
   popd
   pushd tools/power/x86/intel-speed-select
   %{tools_make} CFLAGS+="-D_GNU_SOURCE -Iinclude" DESTDIR=%{buildroot} install
   popd
%endif
pushd tools/thermal/tmon
%{tools_make} INSTALL_ROOT=%{buildroot} install
popd
pushd tools/iio
%{tools_make} DESTDIR=%{buildroot} install
popd
pushd tools/gpio
%{tools_make} DESTDIR=%{buildroot} install
popd
install -m644 -D %{SOURCE2002} %{buildroot}%{_sysconfdir}/logrotate.d/kvm_stat
pushd tools/kvm/kvm_stat
%{__make} INSTALL_ROOT=%{buildroot} install-tools
%{__make} INSTALL_ROOT=%{buildroot} install-man
install -m644 -D kvm_stat.service %{buildroot}%{_unitdir}/kvm_stat.service
popd
# install VM tools
pushd tools/vm/
install -m755 slabinfo %{buildroot}%{_bindir}/slabinfo
install -m755 page_owner_sort %{buildroot}%{_bindir}/page_owner_sort
popd
%endif

if [ -f $DevelDir/vmlinux.h ]; then
  RPM_VMLINUX_H=$DevelDir/vmlinux.h
fi

%if %{with_bpftool}
pushd tools/bpf/bpftool
%{bpftool_make} prefix=%{_prefix} bash_compdir=%{_sysconfdir}/bash_completion.d/ mandir=%{_mandir} install doc-install
popd
%endif

%if %{with_selftests}
pushd samples
install -d %{buildroot}%{_libexecdir}/ksamples
# install bpf samples
pushd bpf
install -d %{buildroot}%{_libexecdir}/ksamples/bpf
find -type f -executable -exec install -m755 {} %{buildroot}%{_libexecdir}/ksamples/bpf \;
install -m755 *.sh %{buildroot}%{_libexecdir}/ksamples/bpf
# test_lwt_bpf.sh compiles test_lwt_bpf.c when run; this works only from the
# kernel tree. Just remove it.
rm %{buildroot}%{_libexecdir}/ksamples/bpf/test_lwt_bpf.sh
install -m644 *_kern.o %{buildroot}%{_libexecdir}/ksamples/bpf || true
install -m644 tcp_bpf.readme %{buildroot}%{_libexecdir}/ksamples/bpf
popd
# install pktgen samples
pushd pktgen
install -d %{buildroot}%{_libexecdir}/ksamples/pktgen
find . -type f -executable -exec install -m755 {} %{buildroot}%{_libexecdir}/ksamples/pktgen/{} \;
find . -type f ! -executable -exec install -m644 {} %{buildroot}%{_libexecdir}/ksamples/pktgen/{} \;
popd
popd
# install drivers/net/mlxsw selftests
pushd tools/testing/selftests/drivers/net/mlxsw
find -type d -exec install -d %{buildroot}%{_libexecdir}/kselftests/drivers/net/mlxsw/{} \;
find -type f -executable -exec install -D -m755 {} %{buildroot}%{_libexecdir}/kselftests/drivers/net/mlxsw/{} \;
find -type f ! -executable -exec install -D -m644 {} %{buildroot}%{_libexecdir}/kselftests/drivers/net/mlxsw/{} \;
popd
# install drivers/net/netdevsim selftests
pushd tools/testing/selftests/drivers/net/netdevsim
find -type d -exec install -d %{buildroot}%{_libexecdir}/kselftests/drivers/net/netdevsim/{} \;
find -type f -executable -exec install -D -m755 {} %{buildroot}%{_libexecdir}/kselftests/drivers/net/netdevsim/{} \;
find -type f ! -executable -exec install -D -m644 {} %{buildroot}%{_libexecdir}/kselftests/drivers/net/netdevsim/{} \;
popd
# install net/forwarding selftests
pushd tools/testing/selftests/net/forwarding
find -type d -exec install -d %{buildroot}%{_libexecdir}/kselftests/net/forwarding/{} \;
find -type f -executable -exec install -D -m755 {} %{buildroot}%{_libexecdir}/kselftests/net/forwarding/{} \;
find -type f ! -executable -exec install -D -m644 {} %{buildroot}%{_libexecdir}/kselftests/net/forwarding/{} \;
popd
# install net/mptcp selftests
pushd tools/testing/selftests/net/mptcp
find -type d -exec install -d %{buildroot}%{_libexecdir}/kselftests/net/mptcp/{} \;
find -type f -executable -exec install -D -m755 {} %{buildroot}%{_libexecdir}/kselftests/net/mptcp/{} \;
find -type f ! -executable -exec install -D -m644 {} %{buildroot}%{_libexecdir}/kselftests/net/mptcp/{} \;
popd
# install tc-testing selftests
pushd tools/testing/selftests/tc-testing
find -type d -exec install -d %{buildroot}%{_libexecdir}/kselftests/tc-testing/{} \;
find -type f -executable -exec install -D -m755 {} %{buildroot}%{_libexecdir}/kselftests/tc-testing/{} \;
find -type f ! -executable -exec install -D -m644 {} %{buildroot}%{_libexecdir}/kselftests/tc-testing/{} \;
popd
# install livepatch selftests
pushd tools/testing/selftests/livepatch
find -type d -exec install -d %{buildroot}%{_libexecdir}/kselftests/livepatch/{} \;
find -type f -executable -exec install -D -m755 {} %{buildroot}%{_libexecdir}/kselftests/livepatch/{} \;
find -type f ! -executable -exec install -D -m644 {} %{buildroot}%{_libexecdir}/kselftests/livepatch/{} \;
popd
# install netfilter selftests
pushd tools/testing/selftests/netfilter
find -type d -exec install -d %{buildroot}%{_libexecdir}/kselftests/netfilter/{} \;
find -type f -executable -exec install -D -m755 {} %{buildroot}%{_libexecdir}/kselftests/netfilter/{} \;
find -type f ! -executable -exec install -D -m644 {} %{buildroot}%{_libexecdir}/kselftests/netfilter/{} \;
popd

# install memfd selftests
pushd tools/testing/selftests/memfd
find -type d -exec install -d %{buildroot}%{_libexecdir}/kselftests/memfd/{} \;
find -type f -executable -exec install -D -m755 {} %{buildroot}%{_libexecdir}/kselftests/memfd/{} \;
find -type f ! -executable -exec install -D -m644 {} %{buildroot}%{_libexecdir}/kselftests/memfd/{} \;
popd
%endif

###
### clean
###

###
### scripts
###

%if %{with_tools}
%post -n kernel-tools-libs
/sbin/ldconfig

%postun -n kernel-tools-libs
/sbin/ldconfig
%endif

#
# This macro defines a %%post script for a kernel*-devel package.
#	%%kernel_devel_post [<subpackage>]
# Note we don't run hardlink if ostree is in use, as ostree is
# a far more sophisticated hardlink implementation.
# https://github.com/projectatomic/rpm-ostree/commit/58a79056a889be8814aa51f507b2c7a4dccee526
#
%define kernel_devel_post() \
%{expand:%%post %{?1:%{1}-}devel}\
if [ -f /etc/sysconfig/kernel ]\
then\
    . /etc/sysconfig/kernel || exit $?\
fi\
if [ "$HARDLINK" != "no" -a -x /usr/bin/hardlink -a ! -e /run/ostree-booted ] \
then\
    (cd /usr/src/kernels/%{KVERREL}%{?1:+%{1}} &&\
     /usr/bin/find . -type f | while read f; do\
       hardlink -c /usr/src/kernels/*%{?dist}.*/$f $f > /dev/null\
     done)\
fi\
%{nil}

#
# This macro defines a %%post script for a kernel*-modules-extra package.
# It also defines a %%postun script that does the same thing.
#	%%kernel_modules_extra_post [<subpackage>]
#
%define kernel_modules_extra_post() \
%{expand:%%post %{?1:%{1}-}modules-extra}\
/sbin/depmod -a %{KVERREL}%{?1:+%{1}}\
%{nil}\
%{expand:%%postun %{?1:%{1}-}modules-extra}\
/sbin/depmod -a %{KVERREL}%{?1:+%{1}}\
%{nil}

#
# This macro defines a %%post script for a kernel*-modules-internal package.
# It also defines a %%postun script that does the same thing.
#	%%kernel_modules_internal_post [<subpackage>]
#
%define kernel_modules_internal_post() \
%{expand:%%post %{?1:%{1}-}modules-internal}\
/sbin/depmod -a %{KVERREL}%{?1:+%{1}}\
%{nil}\
%{expand:%%postun %{?1:%{1}-}modules-internal}\
/sbin/depmod -a %{KVERREL}%{?1:+%{1}}\
%{nil}

#
# This macro defines a %%post script for a kernel*-modules package.
# It also defines a %%postun script that does the same thing.
#	%%kernel_modules_post [<subpackage>]
#
%define kernel_modules_post() \
%{expand:%%post %{?1:%{1}-}modules}\
/sbin/depmod -a %{KVERREL}%{?1:+%{1}}\
%{nil}\
%{expand:%%postun %{?1:%{1}-}modules}\
/sbin/depmod -a %{KVERREL}%{?1:+%{1}}\
%{nil}

# This macro defines a %%posttrans script for a kernel package.
#	%%kernel_variant_posttrans [<subpackage>]
# More text can follow to go at the end of this variant's %%post.
#
%define kernel_variant_posttrans() \
%{expand:%%posttrans %{?1:%{1}-}core}\
%if 0%{!?fedora:1}\
if [ -x %{_sbindir}/weak-modules ]\
then\
    %{_sbindir}/weak-modules --add-kernel %{KVERREL}%{?1:+%{1}} || exit $?\
fi\
%endif\
/bin/kernel-install add %{KVERREL}%{?1:+%{1}} /lib/modules/%{KVERREL}%{?1:+%{1}}/vmlinuz || exit $?\
%{nil}

#
# This macro defines a %%post script for a kernel package and its devel package.
#	%%kernel_variant_post [-v <subpackage>] [-r <replace>]
# More text can follow to go at the end of this variant's %%post.
#
%define kernel_variant_post(v:r:) \
%{expand:%%kernel_devel_post %{?-v*}}\
%{expand:%%kernel_modules_post %{?-v*}}\
%{expand:%%kernel_modules_extra_post %{?-v*}}\
%{expand:%%kernel_modules_internal_post %{?-v*}}\
%{expand:%%kernel_variant_posttrans %{?-v*}}\
%{expand:%%post %{?-v*:%{-v*}-}core}\
%{-r:\
if [ `uname -i` == "x86_64" -o `uname -i` == "i386" ] &&\
   [ -f /etc/sysconfig/kernel ]; then\
  /bin/sed -r -i -e 's/^DEFAULTKERNEL=%{-r*}$/DEFAULTKERNEL=kernel%{?-v:-%{-v*}}/' /etc/sysconfig/kernel || exit $?\
fi}\
%{nil}

#
# This macro defines a %%preun script for a kernel package.
#	%%kernel_variant_preun <subpackage>
#
%define kernel_variant_preun() \
%{expand:%%preun %{?1:%{1}-}core}\
/bin/kernel-install remove %{KVERREL}%{?1:+%{1}} /lib/modules/%{KVERREL}%{?1:+%{1}}/vmlinuz || exit $?\
if [ -x %{_sbindir}/weak-modules ]\
then\
    %{_sbindir}/weak-modules --remove-kernel %{KVERREL}%{?1:+%{1}} || exit $?\
fi\
%{nil}

%kernel_variant_preun
%kernel_variant_post -r kernel-smp

%if %{with_pae}
%kernel_variant_preun lpae
%kernel_variant_post -v lpae -r (kernel|kernel-smp)
%endif

%if %{with_debug}
%kernel_variant_preun debug
%kernel_variant_post -v debug
%endif

%if %{with_zfcpdump}
%kernel_variant_preun zfcpdump
%kernel_variant_post -v zfcpdump
%endif

if [ -x /sbin/ldconfig ]
then
    /sbin/ldconfig -X || exit $?
fi

###
### file lists
###

%if %{with_headers}
%files headers
/usr/include/*
%endif

%if %{with_cross_headers}
%files cross-headers
/usr/*-linux-gnu/include/*
%endif

%if %{with_kernel_abi_stablelists}
%files -n kernel-abi-stablelists
/lib/modules/kabi-*
%endif

%if %{with_kabidw_base}
%ifarch x86_64 s390x ppc64 ppc64le aarch64
%files kernel-kabidw-base-internal
%defattr(-,root,root)
/kabidw-base/%{_target_cpu}/*
%endif
%endif

# only some architecture builds need kernel-doc
%if %{with_doc}
%files doc
%defattr(-,root,root)
%{_datadir}/doc/kernel-doc-%{rpmversion}-%{pkgrelease}/Documentation/*
%dir %{_datadir}/doc/kernel-doc-%{rpmversion}-%{pkgrelease}/Documentation
%dir %{_datadir}/doc/kernel-doc-%{rpmversion}-%{pkgrelease}
%endif

%if %{with_perf}
%files -n perf
%{_bindir}/perf
%{_libdir}/libperf-jvmti.so
%dir %{_libexecdir}/perf-core
%{_libexecdir}/perf-core/*
%{_datadir}/perf-core/*
%{_mandir}/man[1-8]/perf*
%{_sysconfdir}/bash_completion.d/perf
%doc linux-%{KVERREL}/tools/perf/Documentation/examples.txt
%{_docdir}/perf-tip/tips.txt

%files -n python3-perf
%{python3_sitearch}/*

%if %{with_debuginfo}
%files -f perf-debuginfo.list -n perf-debuginfo

%files -f python3-perf-debuginfo.list -n python3-perf-debuginfo
%endif
# with_perf
%endif

%if %{with_tools}
%ifnarch %{cpupowerarchs}
%files -n kernel-tools
%else
%files -n kernel-tools -f cpupower.lang
%{_bindir}/cpupower
%{_datadir}/bash-completion/completions/cpupower
%ifarch x86_64
%{_bindir}/centrino-decode
%{_bindir}/powernow-k8-decode
%endif
%{_unitdir}/cpupower.service
%{_mandir}/man[1-8]/cpupower*
%config(noreplace) %{_sysconfdir}/sysconfig/cpupower
%ifarch x86_64
%{_bindir}/x86_energy_perf_policy
%{_mandir}/man8/x86_energy_perf_policy*
%{_bindir}/turbostat
%{_mandir}/man8/turbostat*
%{_bindir}/intel-speed-select
%endif
# cpupowerarchs
%endif
%{_bindir}/tmon
%{_bindir}/iio_event_monitor
%{_bindir}/iio_generic_buffer
%{_bindir}/lsiio
%{_bindir}/lsgpio
%{_bindir}/gpio-hammer
%{_bindir}/gpio-event-mon
%{_bindir}/gpio-watch
%{_mandir}/man1/kvm_stat*
%{_bindir}/kvm_stat
%{_unitdir}/kvm_stat.service
%config(noreplace) %{_sysconfdir}/logrotate.d/kvm_stat
%{_bindir}/page_owner_sort
%{_bindir}/slabinfo

%if %{with_debuginfo}
%files -f kernel-tools-debuginfo.list -n kernel-tools-debuginfo
%endif

%ifarch %{cpupowerarchs}
%files -n kernel-tools-libs
%{_libdir}/libcpupower.so.0
%{_libdir}/libcpupower.so.0.0.1

%files -n kernel-tools-libs-devel
%{_libdir}/libcpupower.so
%{_includedir}/cpufreq.h
%endif
# with_tools
%endif

%if %{with_bpftool}
%files -n bpftool
%{_sbindir}/bpftool
%{_sysconfdir}/bash_completion.d/bpftool
%{_mandir}/man8/bpftool-cgroup.8.gz
%{_mandir}/man8/bpftool-gen.8.gz
%{_mandir}/man8/bpftool-iter.8.gz
%{_mandir}/man8/bpftool-link.8.gz
%{_mandir}/man8/bpftool-map.8.gz
%{_mandir}/man8/bpftool-prog.8.gz
%{_mandir}/man8/bpftool-perf.8.gz
%{_mandir}/man8/bpftool.8.gz
%{_mandir}/man8/bpftool-net.8.gz
%{_mandir}/man8/bpftool-feature.8.gz
%{_mandir}/man8/bpftool-btf.8.gz
%{_mandir}/man8/bpftool-struct_ops.8.gz

%if %{with_debuginfo}
%files -f bpftool-debuginfo.list -n bpftool-debuginfo
%defattr(-,root,root)
%endif
%endif

%if %{with_selftests}
%files selftests-internal
%{_libexecdir}/ksamples
%{_libexecdir}/kselftests
%endif

# empty meta-package
%ifnarch %nobuildarches noarch
%files
%endif

%if %{with_gcov}
%ifnarch %nobuildarches noarch
%files gcov
%{_builddir}
%endif
%endif

# This is %%{image_install_path} on an arch where that includes ELF files,
# or empty otherwise.
%define elf_image_install_path %{?kernel_image_elf:%{image_install_path}}

#
# This macro defines the %%files sections for a kernel package
# and its devel and debuginfo packages.
#	%%kernel_variant_files [-k vmlinux] <use_vdso> <condition> <subpackage>
#
%define kernel_variant_files(k:) \
%if %{2}\
%{expand:%%files -f kernel-%{?3:%{3}-}core.list %{?1:-f kernel-%{?3:%{3}-}ldsoconf.list} %{?3:%{3}-}core}\
%{!?_licensedir:%global license %%doc}\
%license linux-%{KVERREL}/COPYING-%{version}-%{release}\
/lib/modules/%{KVERREL}%{?3:+%{3}}/%{?-k:%{-k*}}%{!?-k:vmlinuz}\
%ghost /%{image_install_path}/%{?-k:%{-k*}}%{!?-k:vmlinuz}-%{KVERREL}%{?3:+%{3}}\
/lib/modules/%{KVERREL}%{?3:+%{3}}/.vmlinuz.hmac \
%ghost /%{image_install_path}/.vmlinuz-%{KVERREL}%{?3:+%{3}}.hmac \
%ifarch %{arm} aarch64\
/lib/modules/%{KVERREL}%{?3:+%{3}}/dtb \
%ghost /%{image_install_path}/dtb-%{KVERREL}%{?3:+%{3}} \
%endif\
%attr(0600, root, root) /lib/modules/%{KVERREL}%{?3:+%{3}}/System.map\
%ghost %attr(0600, root, root) /boot/System.map-%{KVERREL}%{?3:+%{3}}\
/lib/modules/%{KVERREL}%{?3:+%{3}}/symvers.gz\
/lib/modules/%{KVERREL}%{?3:+%{3}}/config\
%ghost %attr(0600, root, root) /boot/symvers-%{KVERREL}%{?3:+%{3}}.gz\
%ghost %attr(0600, root, root) /boot/initramfs-%{KVERREL}%{?3:+%{3}}.img\
%ghost %attr(0644, root, root) /boot/config-%{KVERREL}%{?3:+%{3}}\
%dir /lib/modules\
%dir /lib/modules/%{KVERREL}%{?3:+%{3}}\
%dir /lib/modules/%{KVERREL}%{?3:+%{3}}/kernel\
/lib/modules/%{KVERREL}%{?3:+%{3}}/build\
/lib/modules/%{KVERREL}%{?3:+%{3}}/source\
/lib/modules/%{KVERREL}%{?3:+%{3}}/updates\
/lib/modules/%{KVERREL}%{?3:+%{3}}/weak-updates\
/lib/modules/%{KVERREL}%{?3:+%{3}}/systemtap\
%{_datadir}/doc/kernel-keys/%{KVERREL}%{?3:+%{3}}\
%if %{1}\
/lib/modules/%{KVERREL}%{?3:+%{3}}/vdso\
%endif\
/lib/modules/%{KVERREL}%{?3:+%{3}}/modules.*\
%{expand:%%files -f kernel-%{?3:%{3}-}modules.list %{?3:%{3}-}modules}\
%{expand:%%files %{?3:%{3}-}devel}\
%defverify(not mtime)\
/usr/src/kernels/%{KVERREL}%{?3:+%{3}}\
%{expand:%%files %{?3:%{3}-}devel-matched}\
%{expand:%%files -f kernel-%{?3:%{3}-}modules-extra.list %{?3:%{3}-}modules-extra}\
%config(noreplace) /etc/modprobe.d/*-blacklist.conf\
%{expand:%%files -f kernel-%{?3:%{3}-}modules-internal.list %{?3:%{3}-}modules-internal}\
%if %{with_debuginfo}\
%ifnarch noarch\
%{expand:%%files -f debuginfo%{?3}.list %{?3:%{3}-}debuginfo}\
%endif\
%endif\
%if %{?3:1} %{!?3:0}\
%{expand:%%files %{3}}\
%endif\
%endif\
%{nil}

%kernel_variant_files %{_use_vdso} %{with_up}
%kernel_variant_files %{_use_vdso} %{with_debug} debug
%if %{with_debug_meta}
%files debug
%files debug-core
%files debug-devel
%files debug-devel-matched
%files debug-modules
%files debug-modules-extra
%endif
%kernel_variant_files %{use_vdso} %{with_pae} lpae
%kernel_variant_files %{_use_vdso} %{with_zfcpdump} zfcpdump

%define kernel_variant_ipaclones(k:) \
%if %{1}\
%if %{with_ipaclones}\
%{expand:%%files %{?2:%{2}-}ipaclones-internal}\
%defattr(-,root,root)\
%defverify(not mtime)\
/usr/src/kernels/%{KVERREL}%{?2:+%{2}}-ipaclones\
%endif\
%endif\
%{nil}

%kernel_variant_ipaclones %{with_up}

# plz don't put in a version string unless you're going to tag
# and build.
#
#
%changelog
* Tue Jul 12 2022 Release Engineering <releng@rockylinux.org> - 5.14.0-70.17.1
- Porting to 9.0, debranding and Rocky branding with new release pkg (Sherif Nagy)
- Porting to 9.0, debranding and Rocky branding (Louis Abel)

* Tue Jun 14 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-70.17.1.el9_0]
- netfilter: nf_tables: disallow non-stateful expression in sets earlier (Phil Sutter) [2092994 2092995] {CVE-2022-1966}
- thunderx nic: mark device as unmaintained (Íñigo Huguet) [2092638 2060285]
- pseries/eeh: Fix the kdump kernel crash during eeh_pseries_init (Steve Best) [2092255 2067770]
- perf: Fix sys_perf_event_open() race against self (Michael Petlan) [2087963 2087964] {CVE-2022-1729}
- spec: Fix separate tools build (Jiri Olsa) [2090852 2054579]
- mm: lru_cache_disable: replace work queue synchronization with synchronize_rcu (Marcelo Tosatti) [2086963 2033500]

* Wed Jun 08 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-70.16.1.el9_0]
- dm integrity: fix memory corruption when tag_size is less than digest size (Benjamin Marzinski) [2082187 2081778]

* Wed Jun 01 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-70.15.1.el9_0]
- CI: Use zstream builder image (Veronika Kabatova)
- tcp: drop the hash_32() part from the index calculation (Guillaume Nault) [2087128 2064868] {CVE-2022-1012}
- tcp: increase source port perturb table to 2^16 (Guillaume Nault) [2087128 2064868] {CVE-2022-1012}
- tcp: dynamically allocate the perturb table used by source ports (Guillaume Nault) [2087128 2064868] {CVE-2022-1012}
- tcp: add small random increments to the source port (Guillaume Nault) [2087128 2064868] {CVE-2022-1012}
- tcp: resalt the secret every 10 seconds (Guillaume Nault) [2087128 2064868] {CVE-2022-1012}
- tcp: use different parts of the port_offset for index and offset (Guillaume Nault) [2087128 2064868] {CVE-2022-1012}
- secure_seq: use the 64 bits of the siphash for port offset calculation (Guillaume Nault) [2087128 2064868] {CVE-2022-1012}
- Revert "netfilter: conntrack: tag conntracks picked up in local out hook" (Florian Westphal) [2085480 2061850]
- Revert "netfilter: nat: force port remap to prevent shadowing well-known ports" (Florian Westphal) [2085480 2061850]
- redhat/koji/Makefile: Decouple koji Makefile from Makefile.common (Andrea Claudi)
- redhat: fix make {distg-brew,distg-koji} (Andrea Claudi)
- esp: limit skb_page_frag_refill use to a single page (Sabrina Dubroca) [2082950 2082951] {CVE-2022-27666}
- esp: Fix possible buffer overflow in ESP transformation (Sabrina Dubroca) [2082950 2082951] {CVE-2022-27666}
- sctp: use the correct skb for security_sctp_assoc_request (Ondrej Mosnacek) [2084044 2078856]
- security: implement sctp_assoc_established hook in selinux (Ondrej Mosnacek) [2084044 2078856]
- security: add sctp_assoc_established hook (Ondrej Mosnacek) [2084044 2078856]
- security: call security_sctp_assoc_request in sctp_sf_do_5_1D_ce (Ondrej Mosnacek) [2084044 2078856]
- security: pass asoc to sctp_assoc_request and sctp_sk_clone (Ondrej Mosnacek) [2084044 2078856]

* Wed May 11 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-70.14.1.el9_0]
- PCI: hv: Propagate coherence from VMbus device to PCI device (Vitaly Kuznetsov) [2074830 2068432]
- Drivers: hv: vmbus: Propagate VMbus coherence to each VMbus device (Vitaly Kuznetsov) [2074830 2068432]
- redhat: rpminspect: disable 'patches' check for known empty patch files (Herton R. Krzesinski)
- redhat/configs: make SHA512_arch algos and CRYPTO_USER built-ins (Vladis Dronov) [2072643 2070624]
- CI: Drop baseline runs (Veronika Kabatova)

* Thu Apr 14 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-70.13.1.el9_0]
- redhat: disable uncommon media device infrastructure (Jarod Wilson) [2074598]
- netfilter: nf_tables: unregister flowtable hooks on netns exit (Florian Westphal) [2056869]
- netfilter: nf_tables_offload: incorrect flow offload action array size (Florian Westphal) [2056869] {CVE-2022-25636}
- netfilter: nf_tables: validate registers coming from userspace. (Phil Sutter) [2065350] {CVE-2022-1015}
- scsi: qedi: Fix failed disconnect handling (Chris Leech) [2071524]
- scsi: iscsi: Fix unbound endpoint error handling (Chris Leech) [2071524]
- scsi: iscsi: Fix conn cleanup and stop race during iscsid restart (Chris Leech) [2071524]
- scsi: iscsi: Fix endpoint reuse regression (Chris Leech) [2071524]
- scsi: iscsi: Release endpoint ID when its freed (Chris Leech) [2071524]
- scsi: iscsi: Fix offload conn cleanup when iscsid restarts (Chris Leech) [2071524]
- Revert "scsi: iscsi: Fix offload conn cleanup when iscsid restarts" (Chris Leech) [2071524]
- scsi: iscsi: Speed up session unblocking and removal (Chris Leech) [2071524]
- scsi: iscsi: Fix recovery and unblocking race (Chris Leech) [2071524]
- scsi: qedi: Fix cmd_cleanup_cmpl counter mismatch issue (Chris Leech) [2071524]
- scsi: iscsi: Unblock session then wake up error handler (Chris Leech) [2071524]
- scsi: iscsi: Fix set_param() handling (Chris Leech) [2071524]
- scsi: iscsi: Fix iscsi_task use after free (Chris Leech) [2071524]
- scsi: iscsi: Adjust iface sysfs attr detection (Chris Leech) [2071524]
- scsi: qedi: Add support for fastpath doorbell recovery (Chris Leech) [2071524]

* Tue Apr 12 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-70.12.1.el9_0]
- redhat/configs: Enable WDT devices used by qemu VMs (Prarit Bhargava) [2074160]
- redhat/configs: disable CONFIG_CAN_SOFTING (Brian Masney) [2073521]

* Fri Apr 08 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-70.11.1.el9_0]
- myri10ge: mark as unmaintained (Michal Schmidt) [2054208]
- benet: mark device 0xe220 (Lancer) as unmaintained (Michal Schmidt) [2054208]
- bnx2: mark as unmaintained (Michal Schmidt) [2054208]
- ice: Fix race condition during interface enslave (Petr Oros) [1988953]
- ice: Fix error with handling of bonding MTU (Petr Oros) [1988953]
- ice: Avoid RTNL lock when re-creating auxiliary device (Petr Oros) [1988953]
- ice: Fix KASAN error in LAG NETDEV_UNREGISTER handler (Petr Oros) [1988953]

* Wed Apr 06 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-70.10.1.el9_0]
- CI: Remove deprecated option (Veronika Kabatova)
- scsi: iscsi: Fix nop handling during conn recovery (Chris Leech) [2069973]
- scsi: iscsi: Merge suspend fields (Chris Leech) [2069973]
- scsi: iscsi: Fix offload conn cleanup when iscsid restarts (Chris Leech) [2069973]
- scsi: iscsi: Move iscsi_ep_disconnect (Chris Leech) [2069973]

* Mon Apr 04 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-70.9.1.el9_0]
- NFS: Don't loop forever in nfs_do_recoalesce() (Steve Dickson) [2069274]
- perf/x86/intel/uncore: Make uncore_discovery clean for 64 bit addresses (Michael Petlan) [2069686]

* Fri Apr 01 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-70.8.1.el9_0]
- KVM: SVM: Allow AVIC support on system w/ physical APIC ID > 255 (Bandan Das) [2033070]
- iommu/amd: Fix I/O page table memory leak (Jerry Snitselaar) [2053219]
- iommu/amd: Recover from event log overflow (Jerry Snitselaar) [2053219]

* Thu Mar 31 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-70.7.1.el9_0]
- redhat/configs: drop some config options for rhel 9. (David Airlie) [2067027]
- arm64: proton-pack: Include unprivileged eBPF status in Spectre v2 mitigation reporting (Waiman Long) [2062288] {CVE-2022-23960}
- arm64: Use the clearbhb instruction in mitigations (Waiman Long) [2062288] {CVE-2022-23960}
- KVM: arm64: Allow SMCCC_ARCH_WORKAROUND_3 to be discovered and migrated (Waiman Long) [2062288] {CVE-2022-23960}
- arm64: Mitigate spectre style branch history side channels (Waiman Long) [2062288] {CVE-2022-23960}
- arm64: proton-pack: Report Spectre-BHB vulnerabilities as part of Spectre-v2 (Waiman Long) [2062288] {CVE-2022-23960}
- arm64: Add percpu vectors for EL1 (Waiman Long) [2062288] {CVE-2022-23960}
- arm64: entry: Add macro for reading symbol addresses from the trampoline (Waiman Long) [2062288] {CVE-2022-23960}
- arm64: entry: Add vectors that have the bhb mitigation sequences (Waiman Long) [2062288] {CVE-2022-23960}
- arm64: entry: Add non-kpti __bp_harden_el1_vectors for mitigations (Waiman Long) [2062288] {CVE-2022-23960}
- arm64: entry: Allow the trampoline text to occupy multiple pages (Waiman Long) [2062288] {CVE-2022-23960}
- arm64: entry: Make the kpti trampoline's kpti sequence optional (Waiman Long) [2062288] {CVE-2022-23960}
- arm64: entry: Move trampoline macros out of ifdef'd section (Waiman Long) [2062288] {CVE-2022-23960}
- arm64: entry: Don't assume tramp_vectors is the start of the vectors (Waiman Long) [2062288] {CVE-2022-23960}
- arm64: entry: Allow tramp_alias to access symbols after the 4K boundary (Waiman Long) [2062288] {CVE-2022-23960}
- arm64: entry: Move the trampoline data page before the text page (Waiman Long) [2062288] {CVE-2022-23960}
- arm64: entry: Free up another register on kpti's tramp_exit path (Waiman Long) [2062288] {CVE-2022-23960}
- arm64: entry: Make the trampoline cleanup optional (Waiman Long) [2062288] {CVE-2022-23960}
- KVM: arm64: Allow indirect vectors to be used without SPECTRE_V3A (Waiman Long) [2062288] {CVE-2022-23960}
- arm64: spectre: Rename spectre_v4_patch_fw_mitigation_conduit (Waiman Long) [2062288] {CVE-2022-23960}
- arm64: entry.S: Add ventry overflow sanity checks (Waiman Long) [2062288] {CVE-2022-23960}
- arm64: Add Cortex-A510 CPU part definition (Waiman Long) [2062288] {CVE-2022-23960}
- arm64: Add Cortex-X2 CPU part definition (Waiman Long) [2062288] {CVE-2022-23960}
- arm64: cpufeature: add HWCAP for FEAT_RPRES (Waiman Long) [2062288] {CVE-2022-23960}
- arm64: add ID_AA64ISAR2_EL1 sys register (Waiman Long) [2062288] {CVE-2022-23960}
- arm64: cpufeature: add HWCAP for FEAT_AFP (Waiman Long) [2062288] {CVE-2022-23960}
- arm64: Add Neoverse-N2, Cortex-A710 CPU part definition (Waiman Long) [2062288] {CVE-2022-23960}
- arm64: Add HWCAP for self-synchronising virtual counter (Waiman Long) [2062288] {CVE-2022-23960}
- iommu/vt-d: Fix double list_add when enabling VMD in scalable mode (Jerry Snitselaar) [2061621]
- redhat/configs: remove unnecessary GPIO options for aarch64 (Brian Masney) [2060951]
- redhat/configs: remove viperboard related Kconfig options (Brian Masney) [2060951]

* Mon Mar 28 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-70.6.1.el9_0]
- configs: enable CONFIG_RMI4_F3A (Benjamin Tissoires) [2067243]
- block: release rq qos structures for queue without disk (Ming Lei) [2065610]
- fuse: fix pipe buffer lifetime for direct_io (Miklos Szeredi) [2064862] {CVE-2022-1011}
- crypto: hmac - disallow keys < 112 bits in FIPS mode (Herbert Xu) [2033512]
- crypto: hmac - add fips_skip support (Herbert Xu) [2033512]
- crypto: des - disallow des3 in FIPS mode (Herbert Xu) [2033512]
- crypto: dh - limit key size to 2048 in FIPS mode (Herbert Xu) [2033512]
- crypto: rsa - limit key size to 2048 in FIPS mode (Herbert Xu) [2033512]
- watch_queue: Make comment about setting ->defunct more accurate (David Howells) [2063758]
- watch_queue: Fix lack of barrier/sync/lock between post and read (David Howells) [2063758]
- watch_queue: Free the alloc bitmap when the watch_queue is torn down (David Howells) [2063758]
- watch_queue: Fix the alloc bitmap size to reflect notes allocated (David Howells) [2063758]
- watch_queue: Use the bitmap API when applicable (David Howells) [2063758]
- watch_queue: Fix to always request a pow-of-2 pipe ring size (David Howells) [2063758]
- watch_queue: Fix to release page in ->release() (David Howells) [2063758]
- watch_queue, pipe: Free watchqueue state after clearing pipe ring (David Howells) [2063758]
- watch_queue: Fix filter limit check (David Howells) [2063758] {CVE-2022-0995}

* Thu Mar 24 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-70.5.1.el9_0]
- NFSD: Fix offset type in I/O trace points (Benjamin Coddington) [2063045]
- NFSD: COMMIT operations must not return NFS?ERR_INVAL (Benjamin Coddington) [2063045]
- NFSD: Clamp WRITE offsets (Benjamin Coddington) [2063045]
- NFSD: Fix NFSv3 SETATTR/CREATE's handling of large file sizes (Benjamin Coddington) [2063045]
- NFSD: Fix ia_size underflow (Benjamin Coddington) [2063045]
- NFSD: Fix the behavior of READ near OFFSET_MAX (Benjamin Coddington) [2063045]
- perf/x86/intel/uncore: Fix Intel SPR CHA event constraints (Michael Petlan) [2054100]
- perf/x86/intel/uncore: Fix Intel SPR IIO event constraints (Michael Petlan) [2054100]
- perf/x86/intel/uncore: Fix Intel SPR M2PCIE event constraints (Michael Petlan) [2054100]
- perf/x86/intel/uncore: Fix Intel SPR M3UPI event constraints (Michael Petlan) [2054100]
- perf/x86/intel/uncore: Support IMC free-running counters on Sapphire Rapids server (Michael Petlan) [2054100]
- perf/x86/intel/uncore: Support IIO free-running counters on Sapphire Rapids server (Michael Petlan) [2054100]
- perf/x86/intel/uncore: Factor out snr_uncore_mmio_map() (Michael Petlan) [2054100]
- perf/x86/intel/uncore: Add alias PMU name (Michael Petlan) [2054100]
- perf/x86/intel/uncore: Add Sapphire Rapids server MDF support (Michael Petlan) [2054100]
- perf/x86/intel/uncore: Add Sapphire Rapids server M3UPI support (Michael Petlan) [2054100]
- perf/x86/intel/uncore: Add Sapphire Rapids server UPI support (Michael Petlan) [2054100]
- perf/x86/intel/uncore: Add Sapphire Rapids server M2M support (Michael Petlan) [2054100]
- perf/x86/intel/uncore: Add Sapphire Rapids server IMC support (Michael Petlan) [2054100]
- perf/x86/intel/uncore: Add Sapphire Rapids server PCU support (Michael Petlan) [2054100]
- perf/x86/intel/uncore: Add Sapphire Rapids server M2PCIe support (Michael Petlan) [2054100]
- perf/x86/intel/uncore: Add Sapphire Rapids server IRP support (Michael Petlan) [2054100]
- perf/x86/intel/uncore: Add Sapphire Rapids server IIO support (Michael Petlan) [2054100]
- perf/x86/intel/uncore: Add Sapphire Rapids server CHA support (Michael Petlan) [2054100]
- perf/x86/intel/uncore: Add Sapphire Rapids server framework (Michael Petlan) [2054100]
- Revert "include/linux/ioport.h: Pad resource struct for KABI" (Prarit Bhargava) [2055736]
- powerpc/pseries: Fix use after free in remove_phb_dynamic() (Prarit Bhargava) [2055736]
- lib/sbitmap: kill 'depth' from sbitmap_word (Ming Lei) [2064695]
- KVM: use __vcalloc for very large allocations (David Hildenbrand) [2057367]
- mm: use vmalloc_array and vcalloc for array allocations (David Hildenbrand) [2057367]
- mm: vmalloc: introduce array allocation functions (David Hildenbrand) [2057367]
- tpm: fix potential NULL pointer access in tpm_del_char_device (Desnes A. Nunes do Rosario) [2032117]
- x86/speculation: Warn about eIBRS + LFENCE + Unprivileged eBPF + SMT (Waiman Long) [2062158 2062168] {CVE-2021-26401 CVE-2022-0001 CVE-2022-0002}
- x86/speculation: Warn about Spectre v2 LFENCE mitigation (Waiman Long) [2062158 2062168] {CVE-2021-26401 CVE-2022-0001 CVE-2022-0002}
- x86/speculation: Update link to AMD speculation whitepaper (Waiman Long) [2062168] {CVE-2021-26401}
- x86/speculation: Use generic retpoline by default on AMD (Waiman Long) [2062168] {CVE-2021-26401}
- x86/speculation: Include unprivileged eBPF status in Spectre v2 mitigation reporting (Waiman Long) [2062158] {CVE-2022-0001 CVE-2022-0002}
- Documentation/hw-vuln: Update spectre doc (Waiman Long) [2062158] {CVE-2022-0001 CVE-2022-0002}
- x86/speculation: Add eIBRS + Retpoline options (Waiman Long) [2062158] {CVE-2022-0001 CVE-2022-0002}
- x86/speculation: Rename RETPOLINE_AMD to RETPOLINE_LFENCE (Waiman Long) [2062158] {CVE-2022-0001 CVE-2022-0002}
- x86,bugs: Unconditionally allow spectre_v2=retpoline,amd (Waiman Long) [2062158] {CVE-2022-0001 CVE-2022-0002}
- x86: deduplicate the spectre_v2_user documentation (Waiman Long) [2062158] {CVE-2022-0001 CVE-2022-0002}
- redhat/configs: aarch64: Enable ARM_SPE_PMU (Mark Salter) [2063234]
- drm/i915/audio: Use BIOS provided value for RKL HDA link (Mika Penttilä) [2046691]
- redhat: configs: Disable TPM 1.2 device drivers (Jerry Snitselaar) [2060516]
- redhat: configs: Change aarch64 default dma domain to lazy (Jerry Snitselaar) [2050415]

* Wed Mar 23 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-70.4.1.el9_0]
- vdpa/mlx5: Fix tracking of current number of VQs (Cindy Lu) [2055451]
- vdpa/mlx5: Fix is_index_valid() to refer to features (Cindy Lu) [2055451]
- vdpa: Protect vdpa reset with cf_mutex (Cindy Lu) [2055451]
- vdpa: Avoid taking cf_mutex lock on get status (Cindy Lu) [2055451]
- vdpa/vdpa_sim_net: Report max device capabilities (Cindy Lu) [2055451]
- vdpa: Use BIT_ULL for bit operations (Cindy Lu) [2055451]
- vdpa/vdpa_sim: Configure max supported virtqueues (Cindy Lu) [2055451]
- vdpa/mlx5: Report max device capabilities (Cindy Lu) [2055451]
- vdpa: Support reporting max device capabilities (Cindy Lu) [2055451]
- vdpa/mlx5: Restore cur_num_vqs in case of failure in change_num_qps() (Cindy Lu) [2055451]
- vdpa: Add support for returning device configuration information (Cindy Lu) [2055451]
- vdpa/mlx5: Support configuring max data virtqueue (Cindy Lu) [2055451]
- vdpa/mlx5: Fix config_attr_mask assignment (Cindy Lu) [2055451]
- vdpa: Allow to configure max data virtqueues (Cindy Lu) [2055451]
- vdpa: Read device configuration only if FEATURES_OK (Cindy Lu) [2055451]
- vdpa: Sync calls set/get config/status with cf_mutex (Cindy Lu) [2055451]
- vdpa/mlx5: Distribute RX virtqueues in RQT object (Cindy Lu) [2055451]
- vdpa: Provide interface to read driver features (Cindy Lu) [2055451]
- vdpa: clean up get_config_size ret value handling (Cindy Lu) [2055451]
- vdpa/mlx5: Fix wrong configuration of virtio_version_1_0 (Cindy Lu) [2055451]
- vdpa: Mark vdpa_config_ops.get_vq_notification as optional (Cindy Lu) [2055451]
- vdpa: Avoid duplicate call to vp_vdpa get_status (Cindy Lu) [2055451]
- net/mlx5_vdpa: Offer VIRTIO_NET_F_MTU when setting MTU (Cindy Lu) [2055451]
- vdpa: add driver_override support (Cindy Lu) [2055451]
- docs: document sysfs ABI for vDPA bus (Cindy Lu) [2055451]
- ifcvf/vDPA: fix misuse virtio-net device config size for blk dev (Cindy Lu) [2055451]
- vdpa: Consider device id larger than 31 (Cindy Lu) [2055451]
- virtio: always enter drivers/virtio/ (Cindy Lu) [2055451]
- vdpa: check that offsets are within bounds (Cindy Lu) [2055451]
- vdpa_sim: avoid putting an uninitialized iova_domain (Cindy Lu) [2055451]
- vhost-vdpa: clean irqs before reseting vdpa device (Cindy Lu) [2055451]
- vdpa/mlx5: Forward only packets with allowed MAC address (Cindy Lu) [2055451]
- vdpa/mlx5: Support configuration of MAC (Cindy Lu) [2055451]
- vdpa/mlx5: Fix clearing of VIRTIO_NET_F_MAC feature bit (Cindy Lu) [2055451]
- vdpa_sim_net: Enable user to set mac address and mtu (Cindy Lu) [2055451]
- vdpa: Enable user to set mac and mtu of vdpa device (Cindy Lu) [2055451]
- vdpa: Use kernel coding style for structure comments (Cindy Lu) [2055451]
- vdpa: Introduce query of device config layout (Cindy Lu) [2055451]
- vdpa: Introduce and use vdpa device get, set config helpers (Cindy Lu) [2055451]
- vdpa/mlx5: Propagate link status from device to vdpa driver (Cindy Lu) [2055451]
- vdpa/mlx5: Rename control VQ workqueue to vdpa wq (Cindy Lu) [2055451]
- vdpa/mlx5: Remove mtu field from vdpa net device (Cindy Lu) [2055451]
- vdpa: add new attribute VDPA_ATTR_DEV_MIN_VQ_SIZE (Cindy Lu) [2055451]
- virtio_vdpa: setup correct vq size with callbacks get_vq_num_{max,min} (Cindy Lu) [2055451]
- vdpa: min vq num of vdpa device cannot be greater than max vq num (Cindy Lu) [2055451]
- vdpa: add new callback get_vq_num_min in vdpa_config_ops (Cindy Lu) [2055451]
- vp_vdpa: add vq irq offloading support (Cindy Lu) [2055451]
- vdpa: fix typo (Cindy Lu) [2055451]
- vhost-vdpa: Fix the wrong input in config_cb (Cindy Lu) [2055451]
- vhost_vdpa: unset vq irq before freeing irq (Cindy Lu) [2055451]
- vdpa: potential uninitialized return in vhost_vdpa_va_map() (Cindy Lu) [2055451]
- vdpa/mlx5: Avoid executing set_vq_ready() if device is reset (Cindy Lu) [2055451]
- vdpa/mlx5: Clear ready indication for control VQ (Cindy Lu) [2055451]
- vdpa: Support transferring virtual addressing during DMA mapping (Cindy Lu) [2055451]
- vdpa: factor out vhost_vdpa_pa_map() and vhost_vdpa_pa_unmap() (Cindy Lu) [2055451]
- vdpa: Add an opaque pointer for vdpa_config_ops.dma_map() (Cindy Lu) [2055451]
- vhost-iotlb: Add an opaque pointer for vhost IOTLB (Cindy Lu) [2055451]
- vhost-vdpa: Handle the failure of vdpa_reset() (Cindy Lu) [2055451]
- vdpa: Add reset callback in vdpa_config_ops (Cindy Lu) [2055451]
- vdpa: Fix some coding style issues (Cindy Lu) [2055451]
- vdpa: Make use of PFN_PHYS/PFN_UP/PFN_DOWN helper macro (Cindy Lu) [2055451]
- vdpa/mlx5: Add multiqueue support (Cindy Lu) [2055451]
- vdpa/mlx5: Add support for control VQ and MAC setting (Cindy Lu) [2055451]
- vdpa/mlx5: Ensure valid indices are provided (Cindy Lu) [2055451]
- vdpa/mlx5: Decouple virtqueue callback from struct mlx5_vdpa_virtqueue (Cindy Lu) [2055451]
- vdpa/mlx5: function prototype modifications in preparation to control VQ (Cindy Lu) [2055451]
- vdpa/mlx5: Remove redundant header file inclusion (Cindy Lu) [2055451]
- vDPA/ifcvf: enable multiqueue and control vq (Cindy Lu) [2055451]
- vDPA/ifcvf: detect and use the onboard number of queues directly (Cindy Lu) [2055451]
- vDPA/ifcvf: implement management netlink framework for ifcvf (Cindy Lu) [2055451]
- vDPA/ifcvf: introduce get_dev_type() which returns virtio dev id (Cindy Lu) [2055451]

* Tue Mar 22 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-70.3.1.el9_0]
- ipv6: fix skb drops in igmp6_event_query() and igmp6_event_report() (Hangbin Liu) [2059308] {CVE-2022-0742}
- redhat/configs: aarch64: Fix PAC/BTI config settings (Mark Salter) [2063215]
- RHEL9.0: arch_hw Update CONFIG_MOUSE_VSXXXAA=m (Tony Camuso) [2062909]
- redhat/configs: Disable KVM on POWER (Laurent Vivier) [2052898]
- drm/ast: Create threshold values for AST2600 (Jocelyn Falempe) [2062560]
- mm: gup: make fault_in_safe_writeable() use fixup_user_fault() (Andreas Gruenbacher) [2062797]
- drm/vmwgfx: Fix stale file descriptors on failed usercopy (David Airlie) [2047613] {CVE-2022-22942}
- netfilter: nf_queue: handle socket prefetch (Florian Westphal) [2060092]
- netfilter: nf_queue: fix possible use-after-free (Florian Westphal) [2060092]
- selftests: netfilter: add nfqueue TCP_NEW_SYN_RECV socket race test (Florian Westphal) [2060092]
- netfilter: nf_queue: don't assume sk is full socket (Florian Westphal) [2060092]
- scsi: mpi3mr: Fix flushing !WQ_MEM_RECLAIM events warning (Tomas Henzl) [2056626]
- scsi: mpi3mr: Fix memory leaks (Tomas Henzl) [2056626]
- scsi: mpi3mr: Fix reporting of actual data transfer size (Tomas Henzl) [2056626]
- scsi: mpi3mr: Fix cmnd getting marked as in use forever (Tomas Henzl) [2056626]
- scsi: mpi3mr: Fix hibernation issue (Tomas Henzl) [2056626]
- scsi: mpi3mr: Fix printing of pending I/O count (Tomas Henzl) [2056626]
- scsi: mpi3mr: Fix deadlock while canceling the fw event (Tomas Henzl) [2056626]
- scsi: mpi3mr: Fixes around reply request queues (Tomas Henzl) [2056626]
- scsi: mpi3mr: Enhanced Task Management Support Reply handling (Tomas Henzl) [2056626]
- scsi: mpi3mr: Use TM response codes from MPI3 headers (Tomas Henzl) [2056626]
- scsi: mpi3mr: Increase internal cmnds timeout to 60s (Tomas Henzl) [2056626]
- scsi: mpi3mr: Do access status validation before adding devices (Tomas Henzl) [2056626]
- scsi: mpi3mr: Update MPI3 headers - part2 (Tomas Henzl) [2056626]
- scsi: mpi3mr: Update MPI3 headers - part1 (Tomas Henzl) [2056626]
- scsi: mpi3mr: Don't reset IOC if cmnds flush with reset status (Tomas Henzl) [2056626]
- scsi: mpi3mr: Replace spin_lock() with spin_lock_irqsave() (Tomas Henzl) [2056626]
- scsi: mpi3mr: Add debug APIs based on logging_level bits (Tomas Henzl) [2056626]
- x86/kvm/fpu: Remove kvm_vcpu_arch.guest_supported_xcr0 (Leonardo Bras) [2043545]
- x86/kvm/fpu: Limit guest user_xfeatures to supported bits of XCR0 (Leonardo Bras) [2043545]
- KVM: x86: Move CPUID.(EAX=0x12,ECX=1) mangling to __kvm_update_cpuid_runtime() (Leonardo Bras) [2043545]
- KVM: x86: Do runtime CPUID update before updating vcpu->arch.cpuid_entries (Leonardo Bras) [2043545]
- x86/fpu: Fix inline prefix warnings (Leonardo Bras) [2043545]
- kvm: x86: Emulate IA32_XFD_ERR for guest (Leonardo Bras) [2043545]
- x86/fpu: Prepare xfd_err in struct fpu_guest (Leonardo Bras) [2043545]
- kvm: x86: Add emulation for IA32_XFD (Leonardo Bras) [2043545]
- x86/fpu: Provide fpu_update_guest_xfd() for IA32_XFD emulation (Leonardo Bras) [2043545]
- kvm: x86: Enable dynamic xfeatures at KVM_SET_CPUID2 (Leonardo Bras) [2043545]
- x86/fpu: Provide fpu_enable_guest_xfd_features() for KVM (Leonardo Bras) [2043545]
- x86/fpu: Add guest support to xfd_enable_feature() (Leonardo Bras) [2043545]
- x86/fpu: Prepare guest FPU for dynamically enabled FPU features (Leonardo Bras) [2043545]
- x86/fpu: Extend fpu_xstate_prctl() with guest permissions (Leonardo Bras) [2043545]
- cpuid: kvm_find_kvm_cpuid_features() should be declared 'static' (Leonardo Bras) [2043545]
- KVM: x86: Make sure KVM_CPUID_FEATURES really are KVM_CPUID_FEATURES (Leonardo Bras) [2043545]
- KVM: x86: Add helper to consolidate core logic of SET_CPUID{2} flows (Leonardo Bras) [2043545]
- redhat/configs: Disable watchdog components (Prarit Bhargava) [2060117]

* Wed Mar 16 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-70.2.1.el9_0]
- CI: Use 9.0-rt branch for rhel-9 realtime_check (Juri Lelli)
- redhat: enable zstream release numbering for rhel 9.0 (Herton R. Krzesinski)
- redhat: change kabi tarballs to use the package release (Herton R. Krzesinski)
- redhat: generate distgit changelog in genspec.sh as well (Herton R. Krzesinski)
- redhat: make genspec prefer metadata from git notes (Herton R. Krzesinski)
- redhat: use tags from git notes for zstream to generate changelog (Herton R. Krzesinski)
- CI: Add disttag setting (Veronika Kabatova)
- CI: Drop c9s config (Veronika Kabatova)
- virtio-net: fix pages leaking when building skb in big mode (Laurent Vivier) [2042559]
- lib/iov_iter: initialize "flags" in new pipe_buffer (Carlos Maiolino) [2060869] {CVE-2022-0847}
- redhat/configs: Make CRYPTO_ECDH algos built-in (Simo Sorce) [2062199]
- crypto: api - Move cryptomgr soft dependency into algapi (Vladis Dronov) [2062199]
- crypto: api - Fix boot-up crash when crypto manager is disabled (Vladis Dronov) [2062199]
- crypto: api - Do not create test larvals if manager is disabled (Vladis Dronov) [2062199]
- crypto: api - Export crypto_boot_test_finished (Vladis Dronov) [2062199]
- crypto: api - Fix built-in testing dependency failures (Vladis Dronov) [2062199]
- redhat/configs: Add CRYPTO_AES_ARM64 config explicitly (Vladis Dronov) [2062199]
- crypto: arm64/aes-ce - stop using SIMD helper for skciphers (Vladis Dronov) [2062199]
- crypto: arm64/aes-neonbs - stop using SIMD helper for skciphers (Vladis Dronov) [2062199]
- redhat: change default dist suffix for RHEL 9.0 (Herton R. Krzesinski)
- selftests: kvm: Check whether SIDA memop fails for normal guests (Thomas Huth) [2050813]
- KVM: s390: Return error on SIDA memop on normal guest (Thomas Huth) [2050813]
- block: kabi: reserve space for block layer public structure (Ming Lei) [2057238]
- block: kabi: reserve space for blk-mq related structure (Ming Lei) [2057238]
- block: kabi: reserve space for bsg related structure (Ming Lei) [2057238]
- block: kabi: reserve space for integrity related structure (Ming Lei) [2057238]
- scsi: lpfc: Fix pt2pt NVMe PRLI reject LOGO loop (Dick Kennedy) [2054866]
- x86/MCE/AMD, EDAC/mce_amd: Support non-uniform MCA bank type enumeration (Aristeu Rozanski) [1898165 2047430 2047446]
- x86/MCE/AMD, EDAC/mce_amd: Add new SMCA bank types (Aristeu Rozanski) [1898165 2047430 2047446]
- EDAC/amd64: Add support for AMD Family 19h Models 10h-1Fh and A0h-AFh (Aristeu Rozanski) [1898165 2047430 2047446]
- EDAC: Add RDDR5 and LRDDR5 memory types (Aristeu Rozanski) [1898165 2047430 2047446]
- drm/amdgpu: Register MCE notifier for Aldebaran RAS (Aristeu Rozanski) [1898165 2047430 2047446]
- x86/MCE/AMD: Export smca_get_bank_type symbol (Aristeu Rozanski) [1898165 2047430 2047446]
- PCI/ACPI: Fix acpi_pci_osc_control_set() kernel-doc comment (Mark Langsdorf) [2049635]
- PCI/ACPI: Check for _OSC support in acpi_pci_osc_control_set() (Mark Langsdorf) [2049635]
- PCI/ACPI: Move _OSC query checks to separate function (Mark Langsdorf) [2049635]
- PCI/ACPI: Move supported and control calculations to separate functions (Mark Langsdorf) [2049635]
- PCI/ACPI: Remove OSC_PCI_SUPPORT_MASKS and OSC_PCI_CONTROL_MASKS (Mark Langsdorf) [2049635]
- nvmet-tcp: fix missing unmainted messages (Chris Leech) [2054441]
- dm stats: fix too short end duration_ns when using precise_timestamps (Benjamin Marzinski) [2051798]
- dm: fix double accounting of flush with data (Benjamin Marzinski) [2051798]
- dm: interlock pending dm_io and dm_wait_for_bios_completion (Benjamin Marzinski) [2051798]
- dm: properly fix redundant bio-based IO accounting (Benjamin Marzinski) [2051798]
- dm: revert partial fix for redundant bio-based IO accounting (Benjamin Marzinski) [2051798]
- block: add bio_start_io_acct_time() to control start_time (Benjamin Marzinski) [2051798]
- scsi: mpt3sas: Fix incorrect system timestamp (Tomas Henzl) [2049631]
- scsi: mpt3sas: Fix system going into read-only mode (Tomas Henzl) [2049631]
- scsi: mpt3sas: Fix kernel panic during drive powercycle test (Tomas Henzl) [2049631]
- redhat/configs: enable mellanox platform drivers to support LED, fan & watchdog devices (Ivan Vecera) [2057491]

* Tue Mar 08 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-70.1.1.el9_0]
- Revert 8dffe2b6 "Merge: kabi: add lib ACKed symbols" (Čestmír Kalina) [2059972]
- include/linux/kernel.h: fix function name for mark_hardware_unmaintained() if !CONFIG_RHEL_DIFFERENCES (Ewan D. Milne) [2059687]
- scsi: sd: Mark ZBC host-managed SCSI disks as unmaintained (Ewan D. Milne) [2059687]
- spec: make linux-firmware weak(er) dependency (Jan Stancek) [2031113]
- redhat/configs: Enable CONFIG_INTEL_PCH_THERMAL for x86 (David Arcari) [2058186]
- redhat/configs: Disable CONFIG_SURFACE_PLATFORMS (David Arcari) [2056609]

* Thu Feb 24 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-70.el9]
- stmmac/intel: mark driver as tech preview (Mark Salter) [2045594]
- net: stmmac: Add GFP_DMA32 for rx buffers if no 64 capability (Mark Salter) [2045594]
- mm: fix invalid page pointer returned with FOLL_PIN gups (Peter Xu) [2037300]
- tipc: improve size validations for received domain records (Xin Long) [2048972] {CVE-2022-0435}
- cgroup-v1: Require capabilities to set release_agent (Waiman Long) [2052168] {CVE-2022-0492}
- bpf, arm64: Use emit_addr_mov_i64() for BPF_PSEUDO_FUNC (Yauheni Kaliuta) [2033596]
- bpf: Stop caching subprog index in the bpf_pseudo_func insn (Yauheni Kaliuta) [2033596]
- ucount: Make get_ucount a safe get_user replacement (Alexey Gladkov) [2049040] {CVE-2022-24122}
- ucounts: Add get_ucounts_or_wrap for clarity (Alexey Gladkov) [2049040]
- ucounts: Remove unnecessary test for NULL ucount in get_ucounts (Alexey Gladkov) [2049040]
- ucounts: Use atomic_long_sub_return for clarity (Alexey Gladkov) [2049040]
- ucounts: Fix rlimit max values check (Alexey Gladkov) [2049040]

* Wed Feb 23 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-69.el9]
- config: mt76: set CONFIG_MT7921S to not set, like in ark (Íñigo Huguet) [2043454]
- config: rtw89: enable driver and device RTL8852AE (Íñigo Huguet) [2043454]
- rtw89: 8852a: correct bit definition of dfs_en (Íñigo Huguet) [2043454]
- rtw89: coex: Update COEX to 5.5.8 (Íñigo Huguet) [2043454]
- rtw89: coex: Cancel PS leaving while C2H comes (Íñigo Huguet) [2043454]
- rtw89: coex: Update BT counters while receiving report (Íñigo Huguet) [2043454]
- rtw89: coex: Define LPS state for BTC using (Íñigo Huguet) [2043454]
- rtw89: coex: Add MAC API to get BT polluted counter (Íñigo Huguet) [2043454]
- rtw89: coex: Not to send H2C when WL not ready and count H2C (Íñigo Huguet) [2043454]
- rtw89: coex: correct C2H header length (Íñigo Huguet) [2043454]
- rtw89: don't kick off TX DMA if failed to write skb (Íñigo Huguet) [2043454]
- rtw89: remove cch_by_bw which is not used (Íñigo Huguet) [2043454]
- rtw89: fix sending wrong rtwsta->mac_id to firmware to fill address CAM (Íñigo Huguet) [2043454]
- rtw89: fix incorrect channel info during scan (Íñigo Huguet) [2043454]
- rtw89: update scan_mac_addr during scanning period (Íñigo Huguet) [2043454]
- rtw89: use inline function instead macro to set H2C and CAM (Íñigo Huguet) [2043454]
- rtw89: add const in the cast of le32_get_bits() (Íñigo Huguet) [2043454]
- rtw89: add AXIDMA and TX FIFO dump in mac_mem_dump (Íñigo Huguet) [2043454]
- rtw89: fix potentially access out of range of RF register array (Íñigo Huguet) [2043454]
- rtw89: remove unneeded variable (Íñigo Huguet) [2043454]
- rtw89: remove unnecessary conditional operators (Íñigo Huguet) [2043454]
- rtw89: update rtw89_regulatory map to R58-R31 (Íñigo Huguet) [2043454]
- rtw89: update tx power limit/limit_ru tables to R54 (Íñigo Huguet) [2043454]
- rtw89: update rtw89 regulation definition to R58-R31 (Íñigo Huguet) [2043454]
- rtw89: fill regd field of limit/limit_ru tables by enum (Íñigo Huguet) [2043454]
- iwlwifi: pcie: add killer devices to the driver (Íñigo Huguet) [2043454]
- iwlwifi: add support for BNJ HW (Íñigo Huguet) [2043454]
- iwlwifi: Read the correct addresses when getting the crf id (Íñigo Huguet) [2043454]
- iwlwifi: pcie: add jacket bit to device configuration parsing (Íñigo Huguet) [2043454]
- iwlwifi: add new ax1650 killer device (Íñigo Huguet) [2043454]
- iwlwifi: add new Qu-Hr device (Íñigo Huguet) [2043454]
- iwlwifi: add missing entries for Gf4 with So and SoF (Íñigo Huguet) [2043454]
- iwlwifi: remove unused iwlax210_2ax_cfg_so_hr_a0 structure (Íñigo Huguet) [2043454]
- iwlwifi: support 4-bits in MAC step value (Íñigo Huguet) [2043454]
- iwlwifi: mvm: Increase the scan timeout guard to 30 seconds (Íñigo Huguet) [2043454]
- wilc1000: fix double free error in probe() (Íñigo Huguet) [2043454]
- wilc1000: Fix spurious "FW not responding" error (Íñigo Huguet) [2043454]
- wilc1000: Fix missing newline in error message (Íñigo Huguet) [2043454]
- wilc1000: Fix copy-and-paste typo in wilc_set_mac_address (Íñigo Huguet) [2043454]
- iwlwifi: mvm: Use div_s64 instead of do_div in iwl_mvm_ftm_rtt_smoothing() (Íñigo Huguet) [2043454]
- mt76: mt7921: fix a possible race enabling/disabling runtime-pm (Íñigo Huguet) [2043454]
- ath11k: Fix unexpected return buffer manager error for QCA6390 (Íñigo Huguet) [2043454]
- ath11k: Fix napi related hang (Íñigo Huguet) [2043454]
- iwlwifi: yoyo: fix issue with new DBGI_SRAM region read. (Íñigo Huguet) [2043454]
- iwlwifi: pcie: make sure prph_info is set when treating wakeup IRQ (Íñigo Huguet) [2043454]
- iwlwifi: mvm: fix AUX ROC removal (Íñigo Huguet) [2043454]
- iwlwifi: mvm: set protected flag only for NDP ranging (Íñigo Huguet) [2043454]
- iwlwifi: mvm: perform 6GHz passive scan after suspend (Íñigo Huguet) [2043454]
- iwlwifi: mvm: Fix calculation of frame length (Íñigo Huguet) [2043454]
- iwlwifi: mvm: test roc running status bits before removing the sta (Íñigo Huguet) [2043454]
- iwlwifi: don't pass actual WGDS revision number in table_revision (Íñigo Huguet) [2043454]
- iwlwifi: fix leaks/bad data after failed firmware load (Íñigo Huguet) [2043454]
- iwlwifi: fix debug TLV parsing (Íñigo Huguet) [2043454]
- iwlwifi: mvm: fix 32-bit build in FTM (Íñigo Huguet) [2043454]
- iwlwifi: fix Bz NMI behaviour (Íñigo Huguet) [2043454]
- rtlwifi: rtl8192cu: Fix WARNING when calling local_irq_restore() with interrupts enabled (Íñigo Huguet) [2043454]
- rtw88: 8822c: update rx settings to prevent potential hw deadlock (Íñigo Huguet) [2043454]
- rtw88: Disable PCIe ASPM while doing NAPI poll on 8821CE (Íñigo Huguet) [2043454]
- ath9k: Fix out-of-bound memcpy in ath9k_hif_usb_rx_stream (Íñigo Huguet) [2043454]
- ath9k_htc: fix NULL pointer dereference at ath9k_htc_tx_get_packet() (Íñigo Huguet) [2043454]
- ath9k_htc: fix NULL pointer dereference at ath9k_htc_rxep() (Íñigo Huguet) [2043454]
- mac80211: fix FEC flag in radio tap header (Íñigo Huguet) [2043454]
- mt76: mt7921: fix possible resume failure (Íñigo Huguet) [2043454]
- mt76: mt7921: move mt76_connac_mcu_set_hif_suspend to bus-related files (Íñigo Huguet) [2043454]
- mt76: mt7921: fix network buffer leak by txs missing (Íñigo Huguet) [2043454]
- mt76: mt7615: clear mcu error interrupt status on mt7663 (Íñigo Huguet) [2043454]
- mt76: connac: fix last_chan configuration in mt76_connac_mcu_rate_txpower_band (Íñigo Huguet) [2043454]
- mt76: mt7921: use correct iftype data on 6GHz cap init (Íñigo Huguet) [2043454]
- mt76: mt7921: fix boolreturn.cocci warning (Íñigo Huguet) [2043454]
- mt76: mt7615: fix unused tx antenna mask in testmode (Íñigo Huguet) [2043454]
- mt76: fix the wiphy's available antennas to the correct value (Íñigo Huguet) [2043454]
- mt76: connac: fix a theoretical NULL pointer dereference in mt76_connac_get_phy_mode (Íñigo Huguet) [2043454]
- mt76: mt7921: fix possible NULL pointer dereference in mt7921_mac_write_txwi (Íñigo Huguet) [2043454]
- mt76: fix possible OOB issue in mt76_calculate_default_rate (Íñigo Huguet) [2043454]
- mt76: debugfs: fix queue reporting for mt76-usb (Íñigo Huguet) [2043454]
- mt76: mt7915: fix SMPS operation fail (Íñigo Huguet) [2043454]
- mt76: mt7915: fix return condition in mt7915_tm_reg_backup_restore() (Íñigo Huguet) [2043454]
- mt76: mt7921: fix MT7921E reset failure (Íñigo Huguet) [2043454]
- mt76: mt7615: fix possible deadlock while mt7615_register_ext_phy() (Íñigo Huguet) [2043454]
- mt76: mt7921: drop offload_flags overwritten (Íñigo Huguet) [2043454]
- mt76: mt7915: get rid of mt7915_mcu_set_fixed_rate routine (Íñigo Huguet) [2043454]
- bus: mhi: core: Use correctly sized arguments for bit field (Íñigo Huguet) [2043454]
- bus: mhi: core: Fix race while handling SYS_ERR at power up (Íñigo Huguet) [2043454]
- bus: mhi: core: Fix reading wake_capable channel configuration (Íñigo Huguet) [2043454]
- bus: mhi: core: Minor style and comment fixes (Íñigo Huguet) [2043454]
- bus: mhi: pci_generic: Graceful shutdown on freeze (Íñigo Huguet) [2043454]
- ath11k: Fix a NULL pointer dereference in ath11k_mac_op_hw_scan() (Íñigo Huguet) [2043454]
- mt76: remove variable set but not used (Íñigo Huguet) [2043454]
- ath11k: Fix deleting uninitialized kernel timer during fragment cache flush (Íñigo Huguet) [2043454]
- ath11k: add spectral/CFR buffer validation support (Íñigo Huguet) [2043454]
- ath11k: Fix buffer overflow when scanning with extraie (Íñigo Huguet) [2043454]
- mwifiex: Fix possible ABBA deadlock (Íñigo Huguet) [2043454]
- ath10k: fix scan abort when duration is set for hw scan (Íñigo Huguet) [2043454]
- ath10k: Fix tx hanging (Íñigo Huguet) [2043454]
- iwlwifi: Fix FW name for gl (Íñigo Huguet) [2043454]
- iwlwifi: add support for Bz-Z HW (Íñigo Huguet) [2043454]
- iwlwifi: acpi: fix wgds rev 3 size (Íñigo Huguet) [2043454]
- iwlwifi: mvm: avoid clearing a just saved session protection id (Íñigo Huguet) [2043454]
- iwlwifi: mvm: Fix wrong documentation for scan request command (Íñigo Huguet) [2043454]
- iwlwifi: mvm: synchronize with FW after multicast commands (Íñigo Huguet) [2043454]
- iwlwifi: mvm: fix delBA vs. NSSN queue sync race (Íñigo Huguet) [2043454]
- ath11k: Fix QMI file type enum value (Íñigo Huguet) [2043454]
- ath11k: add support for WCN6855 hw2.1 (Íñigo Huguet) [2043454]
- ath10k: Fix the MTU size on QCA9377 SDIO (Íñigo Huguet) [2043454]
- wireless: iwlwifi: Fix a double free in iwl_txq_dyn_alloc_dma (Íñigo Huguet) [2043454]
- mwifiex: Ignore BTCOEX events from the 88W8897 firmware (Íñigo Huguet) [2043454]
- mwifiex: Fix skb_over_panic in mwifiex_usb_recv() (Íñigo Huguet) [2043454]
- ath11k: Use host CE parameters for CE interrupts configuration (Íñigo Huguet) [2043454]
- ath11k: Fix mon status ring rx tlv processing (Íñigo Huguet) [2043454]
- ath11k: skip sending vdev down for channel switch (Íñigo Huguet) [2043454]
- ath11k: fix read fail for htt_stats and htt_peer_stats for single pdev (Íñigo Huguet) [2043454]
- ath11k: Set IRQ affinity to CPU0 in case of one MSI vector (Íñigo Huguet) [2043454]
- ath11k: do not restore ASPM in case of single MSI vector (Íñigo Huguet) [2043454]
- ath11k: add support one MSI vector (Íñigo Huguet) [2043454]
- ath11k: refactor multiple MSI vector implementation (Íñigo Huguet) [2043454]
- ath11k: use ATH11K_PCI_IRQ_DP_OFFSET for DP IRQ (Íñigo Huguet) [2043454]
- ath11k: add CE and ext IRQ flag to indicate irq_handler (Íñigo Huguet) [2043454]
- ath11k: get msi_data again after request_irq is called (Íñigo Huguet) [2043454]
- ath9k: fix intr_txqs setting (Íñigo Huguet) [2043454]
- ath11k: add hw_param for wakeup_mhi (Íñigo Huguet) [2043454]
- ath11k: reset RSN/WPA present state for open BSS (Íñigo Huguet) [2043454]
- ath11k: clear the keys properly via DISABLE_KEY (Íñigo Huguet) [2043454]
- ath11k: Fix crash caused by uninitialized TX ring (Íñigo Huguet) [2043454]
- ath11k: use cache line aligned buffers for dbring (Íñigo Huguet) [2043454]
- ath11k: Fix ETSI regd with weather radar overlap (Íñigo Huguet) [2043454]
- ath11k: fix FCS_ERR flag in radio tap header (Íñigo Huguet) [2043454]
- ath11k: fix the value of msecs_to_jiffies in ath11k_debugfs_fw_stats_request (Íñigo Huguet) [2043454]
- ath11k: fix firmware crash during channel switch (Íñigo Huguet) [2043454]
- ath11k: Fix 'unused-but-set-parameter' error (Íñigo Huguet) [2043454]
- ath11k: fix DMA memory free in CE pipe cleanup (Íñigo Huguet) [2043454]
- ath11k: fix error routine when fallback of add interface fails (Íñigo Huguet) [2043454]
- ath11k: fix fw crash due to peer get authorized before key install (Íñigo Huguet) [2043454]
- ath11k: Clear auth flag only for actual association in security mode (Íñigo Huguet) [2043454]
- ath11k: Send PPDU_STATS_CFG with proper pdev mask to firmware (Íñigo Huguet) [2043454]
- ath11k: set correct NL80211_FEATURE_DYNAMIC_SMPS for WCN6855 (Íñigo Huguet) [2043454]
- mac80211: mesh: embedd mesh_paths and mpp_paths into ieee80211_if_mesh (Íñigo Huguet) [2043454]
- mac80211: initialize variable have_higher_than_11mbit (Íñigo Huguet) [2043454]
- mac80211: fix locking in ieee80211_start_ap error path (Íñigo Huguet) [2043454]
- mac80211: do drv_reconfig_complete() before restarting all (Íñigo Huguet) [2043454]
- mac80211: mark TX-during-stop for TX in in_reconfig (Íñigo Huguet) [2043454]
- mac80211: update channel context before station state (Íñigo Huguet) [2043454]
- mac80211: Fix the size used for building probe request (Íñigo Huguet) [2043454]
- mac80211: fix lookup when adding AddBA extension element (Íñigo Huguet) [2043454]
- mac80211: validate extended element ID is present (Íñigo Huguet) [2043454]
- cfg80211: Acquire wiphy mutex on regulatory work (Íñigo Huguet) [2043454]
- mac80211: agg-tx: don't schedule_and_wake_txq() under sta->lock (Íñigo Huguet) [2043454]
- nl80211: remove reload flag from regulatory_request (Íñigo Huguet) [2043454]
- mac80211: send ADDBA requests using the tid/queue of the aggregation session (Íñigo Huguet) [2043454]
- bus: mhi: core: Add support for forced PM resume (Íñigo Huguet) [2043454]
- mt76: mt7921: fix build regression (Íñigo Huguet) [2043454]
- brcmsmac: rework LED dependencies (Íñigo Huguet) [2043454]
- iwlwifi: fix LED dependencies (Íñigo Huguet) [2043454]
- iwlwifi: mvm: don't crash on invalid rate w/o STA (Íñigo Huguet) [2043454]
- bus: mhi: pci_generic: Fix device recovery failed issue (Íñigo Huguet) [2043454]
- mt76: fix key pointer overwrite in mt7921s_write_txwi/mt7663_usb_sdio_write_txwi (Íñigo Huguet) [2043454]
- rt2x00: do not mark device gone on EPROTO errors during start (Íñigo Huguet) [2043454]
- nl80211: reset regdom when reloading regdb (Íñigo Huguet) [2043454]
- mac80211: add docs for ssn in struct tid_ampdu_tx (Íñigo Huguet) [2043454]
- mac80211: fix a memory leak where sta_info is not freed (Íñigo Huguet) [2043454]
- mac80211: set up the fwd_skb->dev for mesh forwarding (Íñigo Huguet) [2043454]
- mac80211: fix regression in SSN handling of addba tx (Íñigo Huguet) [2043454]
- mac80211: fix rate control for retransmitted frames (Íñigo Huguet) [2043454]
- mac80211: track only QoS data frames for admission control (Íñigo Huguet) [2043454]
- mac80211: fix TCP performance on mesh interface (Íñigo Huguet) [2043454]
- mt76: fix possible pktid leak (Íñigo Huguet) [2043454]
- mt76: fix timestamp check in tx_status (Íñigo Huguet) [2043454]
- mt76: mt7915: fix NULL pointer dereference in mt7915_get_phy_mode (Íñigo Huguet) [2043454]
- rtw89: update partition size of firmware header on skb->data (Íñigo Huguet) [2043454]
- iwlwifi: Fix memory leaks in error handling path (Íñigo Huguet) [2043454]
- iwlwifi: fix warnings produced by kernel debug options (Íñigo Huguet) [2043454]
- iwlwifi: mvm: retry init flow if failed (Íñigo Huguet) [2043454]
- iwlwifi: Fix missing error code in iwl_pci_probe() (Íñigo Huguet) [2043454]
- iwlwifi: pcie: fix constant-conversion warning (Íñigo Huguet) [2043454]
- mac80211: fix throughput LED trigger (Íñigo Huguet) [2043454]
- mac80211: fix monitor_sdata RCU/locking assertions (Íñigo Huguet) [2043454]
- mac80211: drop check for DONT_REORDER in __ieee80211_select_queue (Íñigo Huguet) [2043454]
- mac80211: fix radiotap header generation (Íñigo Huguet) [2043454]
- mac80211: do not access the IV when it was stripped (Íñigo Huguet) [2043454]
- nl80211: fix radio statistics in survey dump (Íñigo Huguet) [2043454]
- cfg80211: call cfg80211_stop_ap when switch from P2P_GO type (Íñigo Huguet) [2043454]
- mwifiex: fix division by zero in fw download path (Íñigo Huguet) [2043454]
- iwlwifi: bump FW API to 67 for AX devices (Íñigo Huguet) [2043454]
- iwlwifi: mvm: extend session protection on association (Íñigo Huguet) [2043454]
- iwlwifi: rename CHANNEL_SWITCH_NOA_NOTIF to CHANNEL_SWITCH_START_NOTIF (Íñigo Huguet) [2043454]
- iwlwifi: mvm: remove session protection on disassoc (Íñigo Huguet) [2043454]
- iwlwifi: mvm: fix WGDS table print in iwl_mvm_chub_update_mcc() (Íñigo Huguet) [2043454]
- iwlwifi: rename GEO_TX_POWER_LIMIT to PER_CHAIN_LIMIT_OFFSET_CMD (Íñigo Huguet) [2043454]
- iwlwifi: mvm: d3: use internal data representation (Íñigo Huguet) [2043454]
- iwlwifi: mvm: update RFI TLV (Íñigo Huguet) [2043454]
- iwlwifi: mvm: don't get address of mvm->fwrt just to dereference as a pointer (Íñigo Huguet) [2043454]
- iwlwifi: yoyo: support for ROM usniffer (Íñigo Huguet) [2043454]
- iwlwifi: fw: uefi: add missing include guards (Íñigo Huguet) [2043454]
- iwlwifi: dump host monitor data when NIC doesn't init (Íñigo Huguet) [2043454]
- iwlwifi: pcie: simplify iwl_pci_find_dev_info() (Íñigo Huguet) [2043454]
- iwlwifi: ACPI: support revision 3 WGDS tables (Íñigo Huguet) [2043454]
- iwlwifi: pcie: update sw error interrupt for BZ family (Íñigo Huguet) [2043454]
- iwlwifi: add new pci SoF with JF (Íñigo Huguet) [2043454]
- iwlwifi: mvm: Use all Rx chains for roaming scan (Íñigo Huguet) [2043454]
- iwlwifi: pcie: remove two duplicate PNJ device entries (Íñigo Huguet) [2043454]
- iwlwifi: pcie: refactor dev_info lookup (Íñigo Huguet) [2043454]
- iwlwifi: pcie: remove duplicate entry (Íñigo Huguet) [2043454]
- iwlwifi: pcie: fix killer name matching for AX200 (Íñigo Huguet) [2043454]
- iwlwifi: mvm: fix some kerneldoc issues (Íñigo Huguet) [2043454]
- ath10k: fix division by zero in send path (Íñigo Huguet) [2043454]
- ath10k: fix control-message timeout (Íñigo Huguet) [2043454]
- rtw89: Fix variable dereferenced before check 'sta' (Íñigo Huguet) [2043454]
- rtw89: fix return value in hfc_pub_cfg_chk (Íñigo Huguet) [2043454]
- rtw89: remove duplicate register definitions (Íñigo Huguet) [2043454]
- rtw89: fix error function parameter (Íñigo Huguet) [2043454]
- ath10k: fix module load regression with iram-recovery feature (Íñigo Huguet) [2043454]
- ath10k: fix invalid dma_addr_t token assignment (Íñigo Huguet) [2043454]
- ath11k: change return buffer manager for QCA6390 (Íñigo Huguet) [2043454]
- mt76: connac: fix unresolved symbols when CONFIG_PM is unset (Íñigo Huguet) [2043454]
- mt76: Make use of the helper macro kthread_run() (Íñigo Huguet) [2043454]
- mt76: Print error message when reading EEPROM from mtd failed (Íñigo Huguet) [2043454]
- mt76: mt7921: disable 4addr capability (Íñigo Huguet) [2043454]
- mt76: mt7915: add debugfs knobs for MCU utilization (Íñigo Huguet) [2043454]
- mt76: mt7915: add WA firmware log support (Íñigo Huguet) [2043454]
- mt76: mt7915: fix endiannes warning mt7915_mcu_beacon_check_caps (Íñigo Huguet) [2043454]
- mt76: mt7915: rework debugfs fixed-rate knob (Íñigo Huguet) [2043454]
- mt76: mt7915: rework .set_bitrate_mask() to support more options (Íñigo Huguet) [2043454]
- mt76: mt7915: remove mt7915_mcu_add_he() (Íñigo Huguet) [2043454]
- mt76: mt7615: apply cached RF data for DBDC (Íñigo Huguet) [2043454]
- mt76: mt7615: mt7622: fix ibss and meshpoint (Íñigo Huguet) [2043454]
- mt76: mt7921: fix Wformat build warning (Íñigo Huguet) [2043454]
- mt76: mt7921: fix mt7921s Kconfig (Íñigo Huguet) [2043454]
- iwlwifi: pnvm: print out the version properly (Íñigo Huguet) [2043454]
- iwlwifi: dbg: treat non active regions as unsupported regions (Íñigo Huguet) [2043454]
- iwlwifi: mvm: Read acpi dsm to get channel activation bitmap (Íñigo Huguet) [2043454]
- iwlwifi: add new device id 7F70 (Íñigo Huguet) [2043454]
- iwlwifi: mvm: improve log when processing CSA (Íñigo Huguet) [2043454]
- iwlwifi: mvm: set BT-coex high priority for 802.1X/4-way-HS (Íñigo Huguet) [2043454]
- iwlwifi: dbg: treat dbgc allocation failure when tlv is missing (Íñigo Huguet) [2043454]
- iwlwifi: add new killer devices to the driver (Íñigo Huguet) [2043454]
- iwlwifi: mvm: set inactivity timeouts also for PS-poll (Íñigo Huguet) [2043454]
- iwlwifi: pcie: try to grab NIC access early (Íñigo Huguet) [2043454]
- iwlwifi: mvm: reduce WARN_ON() in TX status path (Íñigo Huguet) [2043454]
- iwlwifi: allow rate-limited error messages (Íñigo Huguet) [2043454]
- iwlwifi: mvm: remove session protection after auth/assoc (Íñigo Huguet) [2043454]
- iwlwifi: remove redundant iwl_finish_nic_init() argument (Íñigo Huguet) [2043454]
- iwlwifi: mvm: Add RTS and CTS flags to iwl_tx_cmd_flags. (Íñigo Huguet) [2043454]
- iwlwifi: mvm: remove csi from iwl_mvm_pass_packet_to_mac80211() (Íñigo Huguet) [2043454]
- iwlwifi: mvm: Support new rate_n_flags for REPLY_RX_MPDU_CMD and RX_NO_DATA_NOTIF (Íñigo Huguet) [2043454]
- iwlwifi: mvm: Support new TX_RSP and COMPRESSED_BA_RES versions (Íñigo Huguet) [2043454]
- iwlwifi: mvm: Support new version of BEACON_TEMPLATE_CMD. (Íñigo Huguet) [2043454]
- iwlwifi: mvm: Add support for new rate_n_flags in tx_cmd. (Íñigo Huguet) [2043454]
- iwlwifi: BZ Family SW reset support (Íñigo Huguet) [2043454]
- iwlwifi: BZ Family BUS_MASTER_DISABLE_REQ code duplication (Íñigo Huguet) [2043454]
- iwlwifi: yoyo: fw debug config from context info and preset (Íñigo Huguet) [2043454]
- iwlwifi: mvm: Support new version of ranging response notification (Íñigo Huguet) [2043454]
- iwlwifi: mvm: Support version 3 of tlc_update_notif. (Íñigo Huguet) [2043454]
- iwlwifi: mvm: convert old rate & flags to the new format. (Íñigo Huguet) [2043454]
- iwlwifi: mvm: add definitions for new rate & flags (Íñigo Huguet) [2043454]
- iwlwifi: mvm: update definitions due to new rate & flags (Íñigo Huguet) [2043454]
- iwlwifi: mvm: scrub key material in firmware dumps (Íñigo Huguet) [2043454]
- iwlwifi: parse debug exclude data from firmware file (Íñigo Huguet) [2043454]
- iwlwifi: fw dump: add infrastructure for dump scrubbing (Íñigo Huguet) [2043454]
- iwlwifi: mvm: correct sta-state logic for TDLS (Íñigo Huguet) [2043454]
- iwlwifi: api: fix struct iwl_wowlan_status_v7 kernel-doc (Íñigo Huguet) [2043454]
- iwlwifi: fix fw/img.c license statement (Íñigo Huguet) [2043454]
- iwlwifi: remove contact information (Íñigo Huguet) [2043454]
- iwlwifi: remove MODULE_AUTHOR() statements (Íñigo Huguet) [2043454]
- iwlwifi: api: remove unused RX status bits (Íñigo Huguet) [2043454]
- iwlwifi: add some missing kernel-doc in struct iwl_fw (Íñigo Huguet) [2043454]
- iwlwifi: mvm: Remove antenna c references (Íñigo Huguet) [2043454]
- iwlwifi: mvm: add support for 160Mhz in ranging measurements (Íñigo Huguet) [2043454]
- iwlwifi: add vendor specific capabilities for some RFs (Íñigo Huguet) [2043454]
- iwlwifi: mvm: add lmac/umac PC info in case of error (Íñigo Huguet) [2043454]
- iwlwifi: mvm: disable RX-diversity in powersave (Íñigo Huguet) [2043454]
- iwlwifi: mvm: fix ieee80211_get_he_iftype_cap() iftype (Íñigo Huguet) [2043454]
- iwlwifi: Start scratch debug register for Bz family (Íñigo Huguet) [2043454]
- iwlwifi: Add support for more BZ HWs (Íñigo Huguet) [2043454]
- iwlwifi: Add support for getting rf id with blank otp (Íñigo Huguet) [2043454]
- cfg80211: fix kernel-doc for MBSSID EMA (Íñigo Huguet) [2043454]
- mac80211: Prevent AP probing during suspend (Íñigo Huguet) [2043454]
- nl80211: Add LC placeholder band definition to nl80211_band (Íñigo Huguet) [2043454]
- mac80211: split beacon retrieval functions (Íñigo Huguet) [2043454]
- cfg80211: separate get channel number from ies (Íñigo Huguet) [2043454]
- mac80211: use ieee80211_bss_get_elem() in most places (Íñigo Huguet) [2043454]
- cfg80211: scan: use element finding functions in easy cases (Íñigo Huguet) [2043454]
- nl80211: use element finding functions (Íñigo Huguet) [2043454]
- mac80211: fils: use cfg80211_find_ext_elem() (Íñigo Huguet) [2043454]
- mac80211: fix memory leaks with element parsing (Íñigo Huguet) [2043454]
- cfg80211: prepare for const netdev->dev_addr (Íñigo Huguet) [2043454]
- mac80211: use eth_hw_addr_set() (Íñigo Huguet) [2043454]
- wireless: mac80211_hwsim: use eth_hw_addr_set() (Íñigo Huguet) [2043454]
- mac80211: debugfs: calculate free buffer size correctly (Íñigo Huguet) [2043454]
- fq_codel: generalise ce_threshold marking for subset of traffic (Íñigo Huguet) [2043454]
- wl3501_cs: use eth_hw_addr_set() (Íñigo Huguet) [2043454]
- ray_cs: use eth_hw_addr_set() (Íñigo Huguet) [2043454]
- wilc1000: use eth_hw_addr_set() (Íñigo Huguet) [2043454]
- brcmfmac: prepare for const netdev->dev_addr (Íñigo Huguet) [2043454]
- wireless: use eth_hw_addr_set() instead of ether_addr_copy() (Íñigo Huguet) [2043454]
- wireless: use eth_hw_addr_set() (Íñigo Huguet) [2043454]
- iwlwifi: cfg: set low-latency-xtal for some integrated So devices (Íñigo Huguet) [2043454]
- iwlwifi: pnvm: read EFI data only if long enough (Íñigo Huguet) [2043454]
- iwlwifi: pnvm: don't kmemdup() more than we have (Íñigo Huguet) [2043454]
- iwlwifi: change all JnP to NO-160 configuration (Íñigo Huguet) [2043454]
- iwlwifi: mvm: reset PM state on unsuccessful resume (Íñigo Huguet) [2043454]
- mwifiex: Deactive host sleep using HSCFG after it was activated manually (Íñigo Huguet) [2043454]
- mwifiex: Send DELBA requests according to spec (Íñigo Huguet) [2043454]
- mwifiex: Fix an incorrect comment (Íñigo Huguet) [2043454]
- mwifiex: Log an error on command failure during key-material upload (Íñigo Huguet) [2043454]
- mwifiex: Don't log error on suspend if wake-on-wlan is disabled (Íñigo Huguet) [2043454]
- rtw89: remove unneeded semicolon (Íñigo Huguet) [2043454]
- rtw89: fix return value check in rtw89_cam_send_sec_key_cmd() (Íñigo Huguet) [2043454]
- mt76: mt7915: change max rx len limit of hw modules (Íñigo Huguet) [2043454]
- mt76: mt7915: fix missing HE phy cap (Íñigo Huguet) [2043454]
- mt76: mt7915: rework mt7915_mcu_sta_muru_tlv() (Íñigo Huguet) [2043454]
- mt76: mt7915: enable HE UL MU-MIMO (Íñigo Huguet) [2043454]
- mt76: mt7921: add per-vif counters in ethtool (Íñigo Huguet) [2043454]
- mt76: mt7921: move tx amsdu stats in mib_stats (Íñigo Huguet) [2043454]
- mt76: mt7921: add sta stats accounting in mt7921_mac_add_txs_skb (Íñigo Huguet) [2043454]
- mt76: mt7921: introduce stats reporting through ethtool (Íñigo Huguet) [2043454]
- mt76: mt7921: add some more MIB counters (Íñigo Huguet) [2043454]
- mt76: do not reset MIB counters in get_stats callback (Íñigo Huguet) [2043454]
- mt76: mt7915: move tx amsdu stats in mib_stats (Íñigo Huguet) [2043454]
- mt76: mt7915: run mt7915_get_et_stats holding mt76 mutex (Íñigo Huguet) [2043454]
- mt76: move mt76_ethtool_worker_info in mt76 module (Íñigo Huguet) [2043454]
- mt76: move mt76_sta_stats in mt76.h (Íñigo Huguet) [2043454]
- mt76: mt76x0: correct VHT MCS 8/9 tx power eeprom offset (Íñigo Huguet) [2043454]
- mt76: mt7921s: add reset support (Íñigo Huguet) [2043454]
- mt76: mt7921: introduce mt7921s support (Íñigo Huguet) [2043454]
- mt76: mt7921: refactor mt7921_mcu_send_message (Íñigo Huguet) [2043454]
- mt76: mt7921: rely on mcu_get_nic_capability (Íñigo Huguet) [2043454]
- mt76: connac: extend mcu_get_nic_capability (Íñigo Huguet) [2043454]
- mt76: sdio: extend sdio module to support CONNAC2 (Íñigo Huguet) [2043454]
- mt76: sdio: introduce parse_irq callback (Íñigo Huguet) [2043454]
- mt76: sdio: move common code in mt76_sdio module (Íñigo Huguet) [2043454]
- mt76: mt7921: use physical addr to unify register access (Íñigo Huguet) [2043454]
- mt76: mt7921: make all event parser reusable between mt7921s and mt7921e (Íñigo Huguet) [2043454]
- mt76: mt7663s: rely on mcu reg access utility (Íñigo Huguet) [2043454]
- mt76: connac: move mcu reg access utility routines in mt76_connac_lib module (Íñigo Huguet) [2043454]
- mt76: mt7921: add MT7921_COMMON module (Íñigo Huguet) [2043454]
- mt76: mt7921: refactor init.c to be bus independent (Íñigo Huguet) [2043454]
- mt76: mt7921: refactor mcu.c to be bus independent (Íñigo Huguet) [2043454]
- mt76: mt7921: refactor dma.c to be pcie specific (Íñigo Huguet) [2043454]
- mt76: mt7921: refactor mac.c to be bus independent (Íñigo Huguet) [2043454]
- mt76: mt7921: add MU EDCA cmd support (Íñigo Huguet) [2043454]
- mt76: mt7915: remove dead code in debugfs code (Íñigo Huguet) [2043454]
- mt76: sdio: export mt76s_alloc_rx_queue and mt76s_alloc_tx routines (Íñigo Huguet) [2043454]
- mt76: mt7915: improve code readability for xmit-queue handler (Íñigo Huguet) [2043454]
- mt76: mt7915: introduce mt76 debugfs sub-dir for ext-phy (Íñigo Huguet) [2043454]
- mt76: rely on phy pointer in mt76_register_debugfs_fops routine signature (Íñigo Huguet) [2043454]
- mt76: mt7915: set muru platform type (Íñigo Huguet) [2043454]
- mt76: mt7915: set VTA bit in tx descriptor (Íñigo Huguet) [2043454]
- mt76: mt7915: fix muar_idx in mt7915_mcu_alloc_sta_req() (Íñigo Huguet) [2043454]
- mt76: mt7915: rework starec TLV tags (Íñigo Huguet) [2043454]
- mt76: mt7915: fix sta_rec_wtbl tag len (Íñigo Huguet) [2043454]
- mt76: mt7915: improve starec readability of txbf (Íñigo Huguet) [2043454]
- mt76: mt7915: fix txbf starec TLV issues (Íñigo Huguet) [2043454]
- mt76: mt7915: introduce mt7915_mcu_beacon_check_caps() (Íñigo Huguet) [2043454]
- mt76: connac: fix possible NULL pointer dereference in mt76_connac_get_phy_mode_v2 (Íñigo Huguet) [2043454]
- mt76: do not access 802.11 header in ccmp check for 802.3 rx skbs (Íñigo Huguet) [2043454]
- mt76: use a separate CCMP PN receive counter for management frames (Íñigo Huguet) [2043454]
- mt76: mt7921: add delay config for sched scan (Íñigo Huguet) [2043454]
- mt76: mt7615: fix monitor mode tear down crash (Íñigo Huguet) [2043454]
- mt76: debugfs: improve queue node readability (Íñigo Huguet) [2043454]
- mt76: mt7915: add twt_stats knob in debugfs (Íñigo Huguet) [2043454]
- mt76: mt7915: enable twt responder capability (Íñigo Huguet) [2043454]
- mt76: mt7915: introduce mt7915_mac_add_twt_setup routine (Íñigo Huguet) [2043454]
- mt76: mt7915: introduce mt7915_mcu_twt_agrt_update mcu command (Íñigo Huguet) [2043454]
- mt76: mt7915: introduce __mt7915_get_tsf routine (Íñigo Huguet) [2043454]
- mt76: drop MCU header size from buffer size in __mt76_mcu_send_firmware (Íñigo Huguet) [2043454]
- mt76: introduce __mt76_mcu_send_firmware routine (Íñigo Huguet) [2043454]
- mt76: support reading EEPROM data embedded in fdt (Íñigo Huguet) [2043454]
- mt76: schedule status timeout at dma completion (Íñigo Huguet) [2043454]
- mt76: substitute sk_buff_head status_list with spinlock_t status_lock (Íñigo Huguet) [2043454]
- mt76: remove mt76_wcid pointer from mt76_tx_status_check signature (Íñigo Huguet) [2043454]
- mt76: introduce packet_id idr (Íñigo Huguet) [2043454]
- mt76: mt7921: add 6GHz support (Íñigo Huguet) [2043454]
- mt76: add 6GHz support (Íñigo Huguet) [2043454]
- mt76: connac: enable hw amsdu @ 6GHz (Íñigo Huguet) [2043454]
- mt76: connac: add 6GHz support to mt76_connac_mcu_uni_add_bss (Íñigo Huguet) [2043454]
- mt76: connac: add 6GHz support to mt76_connac_mcu_sta_tlv (Íñigo Huguet) [2043454]
- mt76: connac: set 6G phymode in single-sku support (Íñigo Huguet) [2043454]
- mt76: connac: add 6GHz support to mt76_connac_mcu_set_channel_domain (Íñigo Huguet) [2043454]
- mt76: connac: enable 6GHz band for hw scan (Íñigo Huguet) [2043454]
- mt76: connac: set 6G phymode in mt76_connac_get_phy_mode{,v2} (Íñigo Huguet) [2043454]
- mt76: mt7915: add mib counters to ethtool stats (Íñigo Huguet) [2043454]
- mt76: mt7915: add more MIB registers (Íñigo Huguet) [2043454]
- mt76: mt7915: add tx mu/su counters to mib (Íñigo Huguet) [2043454]
- mt76: mt7915: add some per-station tx stats to ethtool (Íñigo Huguet) [2043454]
- mt76: mt7915: add tx stats gathered from tx-status callbacks (Íñigo Huguet) [2043454]
- mt76: mt7915: add ethtool stats support (Íñigo Huguet) [2043454]
- mt76: mt7921: fix retrying release semaphore without end (Íñigo Huguet) [2043454]
- mt76: mt7921: robustify hardware initialization flow (Íñigo Huguet) [2043454]
- mt76: mt7915: fix possible infinite loop release semaphore (Íñigo Huguet) [2043454]
- mt76: mt7915: honor all possible error conditions in mt7915_mcu_init() (Íñigo Huguet) [2043454]
- mt76: move spin_lock_bh to spin_lock in tasklet (Íñigo Huguet) [2043454]
- mt76: mt7921: remove mt7921_sta_stats (Íñigo Huguet) [2043454]
- mt76: mt7921: remove mcu rate reporting code (Íñigo Huguet) [2043454]
- mt76: mt7921: report tx rate directly from tx status (Íñigo Huguet) [2043454]
- mt76: mt7921: add support for tx status reporting (Íñigo Huguet) [2043454]
- mt76: mt7921: start reworking tx rate reporting (Íñigo Huguet) [2043454]
- mt76: mt7615: fix hwmon temp sensor mem use-after-free (Íñigo Huguet) [2043454]
- mt76: mt7915: fix hwmon temp sensor mem use-after-free (Íñigo Huguet) [2043454]
- mt76: mt7915: enable configured beacon tx rate (Íñigo Huguet) [2043454]
- mt76: disable BH around napi_schedule() calls (Íñigo Huguet) [2043454]
- mt76: fill boottime_ns in Rx path (Íñigo Huguet) [2043454]
- mt76: switch from 'pci_' to 'dma_' API (Íñigo Huguet) [2043454]
- mt76: fix boolreturn.cocci warnings (Íñigo Huguet) [2043454]
- mt76: mt7921: update mib counters dumping phy stats (Íñigo Huguet) [2043454]
- mt76: mt7921: always wake device if necessary in debugfs (Íñigo Huguet) [2043454]
- mt76: mt7915: rename debugfs tx-queues (Íñigo Huguet) [2043454]
- mt76: mt7915: rework debugfs queue info (Íñigo Huguet) [2043454]
- mt76: mt7921: move mt7921_queue_rx_skb to mac.c (Íñigo Huguet) [2043454]
- mt76: mt7915: fix WMM index on DBDC cards (Íñigo Huguet) [2043454]
- mt76: mt7915: improve code readability in mt7915_mcu_sta_bfer_ht (Íñigo Huguet) [2043454]
- mt76: mt7915: introduce bss coloring support (Íñigo Huguet) [2043454]
- mt76: mt7915: add LED support (Íñigo Huguet) [2043454]
- mt76: mt7915: fix potential NPE in TXS processing (Íñigo Huguet) [2043454]
- mt76: mt7915: fix he_mcs capabilities for 160mhz (Íñigo Huguet) [2043454]
- mt76: use IEEE80211_OFFLOAD_ENCAP_ENABLED instead of MT_DRV_AMSDU_OFFLOAD (Íñigo Huguet) [2043454]
- mt76: mt7915: update mac timing settings (Íñigo Huguet) [2043454]
- mt76: mt7921: fix endianness warnings in mt7921_mac_decode_he_mu_radiotap (Íñigo Huguet) [2043454]
- mt76: mt7921: fix kernel warning from cfg80211_calculate_bitrate (Íñigo Huguet) [2043454]
- mt76: mt7921: fix firmware usage of RA info using legacy rates (Íñigo Huguet) [2043454]
- mt76: mt7915: add HE-LTF into fixed rate command (Íñigo Huguet) [2043454]
- mt76: mt7921: report HE MU radiotap (Íñigo Huguet) [2043454]
- mt76: mt7615: move mt7615_mcu_set_p2p_oppps in mt76_connac module (Íñigo Huguet) [2043454]
- mt76: overwrite default reg_ops if necessary (Íñigo Huguet) [2043454]
- mt76: mt7921: introduce mt7921_mcu_set_beacon_filter utility routine (Íñigo Huguet) [2043454]
- mt76: mt7921: get rid of mt7921_mac_set_beacon_filter (Íñigo Huguet) [2043454]
- mt76: mt7921: get rid of monitor_vif (Íñigo Huguet) [2043454]
- mt76: connac: add support for limiting to maximum regulatory Tx power (Íñigo Huguet) [2043454]
- mt76: connac: fix GTK rekey offload failure on WPA mixed mode (Íñigo Huguet) [2043454]
- mt76: mt7921: fix dma hang in rmmod (Íñigo Huguet) [2043454]
- mt76: add support for setting mcast rate (Íñigo Huguet) [2043454]
- mt76: mt7915: fix bit fields for HT rate idx (Íñigo Huguet) [2043454]
- mt76: mt7915: switch proper tx arbiter mode in testmode (Íñigo Huguet) [2043454]
- mt76: mt7915: fix potential overflow of eeprom page index (Íñigo Huguet) [2043454]
- mt76: mt7921: send EAPOL frames at lowest rate (Íñigo Huguet) [2043454]
- mt76: mt7915: send EAPOL frames at lowest rate (Íñigo Huguet) [2043454]
- mt76: mt7915: add control knobs for thermal throttling (Íñigo Huguet) [2043454]
- mt76: mt7921: Add mt7922 support (Íñigo Huguet) [2043454]
- mt76: mt7615: fix skb use-after-free on mac reset (Íñigo Huguet) [2043454]
- mt76: mt7921: Fix out of order process by invalid event pkt (Íñigo Huguet) [2043454]
- mt76: mt7915: fix mgmt frame using unexpected bitrate (Íñigo Huguet) [2043454]
- mt76: mt7921: fix mgmt frame using unexpected bitrate (Íñigo Huguet) [2043454]
- mt76: add mt76_default_basic_rate more devices can rely on (Íñigo Huguet) [2043454]
- mt76: mt7921: introduce testmode support (Íñigo Huguet) [2043454]
- mt76: mt7915: remove mt7915_sta_stats (Íñigo Huguet) [2043454]
- mt76: mt7915: report tx rate directly from tx status (Íñigo Huguet) [2043454]
- mt76: mt7915: cleanup -Wunused-but-set-variable (Íñigo Huguet) [2043454]
- mt76: mt7915: take RCU read lock when calling ieee80211_bss_get_elem() (Íñigo Huguet) [2043454]
- mt76: mt7915: fix an off-by-one bound check (Íñigo Huguet) [2043454]
- mt76: mt7921: add .set_sar_specs support (Íñigo Huguet) [2043454]
- mt76: mt7915: adapt new firmware to update BA winsize for Rx session (Íñigo Huguet) [2043454]
- mt76: mt7915: report HE MU radiotap (Íñigo Huguet) [2043454]
- mt76: mt76x02: fix endianness warnings in mt76x02_mac.c (Íñigo Huguet) [2043454]
- mt76: mt7921: fix survey-dump reporting (Íñigo Huguet) [2043454]
- mt76: fix build error implicit enumeration conversion (Íñigo Huguet) [2043454]
- mt76: mt7921: enable aspm by default (Íñigo Huguet) [2043454]
- mt76: connac: fix mt76_connac_gtk_rekey_tlv usage (Íñigo Huguet) [2043454]
- mt76: mt7915: fix calling mt76_wcid_alloc with incorrect parameter (Íñigo Huguet) [2043454]
- mt76: mt7915: fix info leak in mt7915_mcu_set_pre_cal() (Íñigo Huguet) [2043454]
- mt76: mt7615: fix endianness warning in mt7615_mac_write_txwi (Íñigo Huguet) [2043454]
- mt76: mt7921: fix endianness warning in mt7921_update_txs (Íñigo Huguet) [2043454]
- mt76: mt7915: fix endianness warning in mt7915_mac_add_txs_skb (Íñigo Huguet) [2043454]
- mt76: mt7921: avoid unnecessary spin_lock/spin_unlock in mt7921_mcu_tx_done_event (Íñigo Huguet) [2043454]
- mt76: mt7921: fix endianness in mt7921_mcu_tx_done_event (Íñigo Huguet) [2043454]
- rtw89: Remove redundant check of ret after call to rtw89_mac_enable_bb_rf (Íñigo Huguet) [2043454]
- rtw89: Fix two spelling mistakes in debug messages (Íñigo Huguet) [2043454]
- mwifiex: Try waking the firmware until we get an interrupt (Íñigo Huguet) [2043454]
- mwifiex: Read a PCI register after writing the TX ring write pointer (Íñigo Huguet) [2043454]
- fq_codel: implement L4S style ce_threshold_ect1 marking (Íñigo Huguet) [2043454]
- net: add skb_get_dsfield() helper (Íñigo Huguet) [2043454]
- wireless: Remove redundant 'flush_workqueue()' calls (Íñigo Huguet) [2043454]
- mt7601u: Remove redundant initialization of variable ret (Íñigo Huguet) [2043454]
- rtlwifi: rtl8192ee: Remove redundant initialization of variable version (Íñigo Huguet) [2043454]
- rtw89: add Realtek 802.11ax driver (Íñigo Huguet) [2043454]
- ath10k: fix max antenna gain unit (Íñigo Huguet) [2043454]
- ath9k: fix an IS_ERR() vs NULL check (Íñigo Huguet) [2043454]
- ath11k: Identify DFS channel when sending scan channel list command (Íñigo Huguet) [2043454]
- ath9k: support DT ieee80211-freq-limit property to limit channels (Íñigo Huguet) [2043454]
- ath11k: Change number of TCL rings to one for QCA6390 (Íñigo Huguet) [2043454]
- ath11k: Handle MSI enablement during rmmod and SSR (Íñigo Huguet) [2043454]
- ath: dfs_pattern_detector: Fix possible null-pointer dereference in channel_detector_create() (Íñigo Huguet) [2043454]
- ath11k: Use kcalloc() instead of kzalloc() (Íñigo Huguet) [2043454]
- ath11k: Remove redundant assignment to variable fw_size (Íñigo Huguet) [2043454]
- ath11k: fix m68k and xtensa build failure in ath11k_peer_assoc_h_smps() (Íñigo Huguet) [2043454]
- ath11k: Fix spelling mistake "incompaitiblity" -> "incompatibility" (Íñigo Huguet) [2043454]
- ath11k: Remove unused variable in ath11k_dp_rx_mon_merg_msdus() (Íñigo Huguet) [2043454]
- ath9k: Fix potential interrupt storm on queue reset (Íñigo Huguet) [2043454]
- ath9k: add option to reset the wifi chip via debugfs (Íñigo Huguet) [2043454]
- ath10k: Don't always treat modem stop events as crashes (Íñigo Huguet) [2043454]
- rtl8xxxu: Use lower tx rates for the ack packet (Íñigo Huguet) [2043454]
- brcmfmac: Add DMI nvram filename quirk for Cyberbook T116 tablet (Íñigo Huguet) [2043454]
- rtw88: refine fw_crash debugfs to show non-zero while triggering (Íñigo Huguet) [2043454]
- rtw88: fix RX clock gate setting while fifo dump (Íñigo Huguet) [2043454]
- net: qrtr: combine nameservice into main module (Íñigo Huguet) [2043454]
- ath10k: sdio: Add missing BH locking around napi_schdule() (Íñigo Huguet) [2043454]
- ath10k: Fix missing frame timestamp for beacon/probe-resp (Íñigo Huguet) [2043454]
- ath10k: high latency fixes for beacon buffer (Íñigo Huguet) [2043454]
- ath11k: Change DMA_FROM_DEVICE to DMA_TO_DEVICE when map reinjected packets (Íñigo Huguet) [2043454]
- ath11k: support SMPS configuration for 6 GHz (Íñigo Huguet) [2043454]
- ath11k: add 6 GHz params in peer assoc command (Íñigo Huguet) [2043454]
- ieee80211: Add new A-MPDU factor macro for HE 6 GHz peer caps (Íñigo Huguet) [2043454]
- ath11k: indicate to mac80211 scan complete with aborted flag for ATH11K_SCAN_STARTING state (Íñigo Huguet) [2043454]
- ath11k: indicate scan complete for scan canceled when scan running (Íñigo Huguet) [2043454]
- ath11k: add handler for scan event WMI_SCAN_EVENT_DEQUEUED (Íñigo Huguet) [2043454]
- ath11k: add HTT stats support for new stats (Íñigo Huguet) [2043454]
- ath11k: Change masking and shifting in htt stats (Íñigo Huguet) [2043454]
- ath11k: Remove htt stats fixed size array usage (Íñigo Huguet) [2043454]
- ath11k: Replace HTT_DBG_OUT with scnprintf (Íñigo Huguet) [2043454]
- ath11k: Rename macro ARRAY_TO_STRING to PRINT_ARRAY_TO_BUF (Íñigo Huguet) [2043454]
- ath11k: Fix memory leak in ath11k_qmi_driver_event_work (Íñigo Huguet) [2043454]
- ath11k: Fix inaccessible debug registers (Íñigo Huguet) [2043454]
- ath11k: Drop MSDU with length error in DP rx path (Íñigo Huguet) [2043454]
- ath11k: copy cap info of 6G band under WMI_HOST_WLAN_5G_CAP for WCN6855 (Íñigo Huguet) [2043454]
- ath11k: enable 6G channels for WCN6855 (Íñigo Huguet) [2043454]
- ath11k: re-enable ht_cap/vht_cap for 5G band for WCN6855 (Íñigo Huguet) [2043454]
- ath11k: fix survey dump collection in 6 GHz (Íñigo Huguet) [2043454]
- ath11k: fix packet drops due to incorrect 6 GHz freq value in rx status (Íñigo Huguet) [2043454]
- ath11k: add channel 2 into 6 GHz channel list (Íñigo Huguet) [2043454]
- mac80211: MBSSID support in interface handling (Íñigo Huguet) [2043454]
- ath11k: Add wmi peer create conf event in wmi_tlv_event_id (Íñigo Huguet) [2043454]
- ath11k: Avoid "No VIF found" warning message (Íñigo Huguet) [2043454]
- ath11k: Fix crash during firmware recovery on reo cmd ring access (Íñigo Huguet) [2043454]
- ath11k: Assign free_vdev_map value before ieee80211_register_hw (Íñigo Huguet) [2043454]
- ath11k: Add vdev start flag to disable hardware encryption (Íñigo Huguet) [2043454]
- ath11k: Avoid race during regd updates (Íñigo Huguet) [2043454]
- ath11k: Avoid reg rules update during firmware recovery (Íñigo Huguet) [2043454]
- ath11k: Update pdev tx and rx firmware stats (Íñigo Huguet) [2043454]
- ath11k: Fix pktlog lite rx events (Íñigo Huguet) [2043454]
- ath11k: Add support for RX decapsulation offload (Íñigo Huguet) [2043454]
- ath11k: fix some sleeping in atomic bugs (Íñigo Huguet) [2043454]
- ath11k: qmi: avoid error messages when dma allocation fails (Íñigo Huguet) [2043454]
- ath11k: Replace one-element array with flexible-array member (Íñigo Huguet) [2043454]
- ath11k: add caldata download support from EEPROM (Íñigo Huguet) [2043454]
- ath11k: add caldata file for multiple radios (Íñigo Huguet) [2043454]
- ath11k: clean up BDF download functions (Íñigo Huguet) [2043454]
- ath11k: use hw_params to access board_size and cal_offset (Íñigo Huguet) [2043454]
- ath11k: Wstringop-overread warning (Íñigo Huguet) [2043454]
- ath11k: Add spectral scan support for QCN9074 (Íñigo Huguet) [2043454]
- ath11k: Fix the spectral minimum FFT bin count (Íñigo Huguet) [2043454]
- ath11k: Introduce spectral hw configurable param (Íñigo Huguet) [2043454]
- ath11k: Refactor spectral FFT bin size (Íñigo Huguet) [2043454]
- ath11k: add support for 80P80 and 160 MHz bandwidth (Íñigo Huguet) [2043454]
- ath11k: add support for setting fixed HE rate/gi/ltf (Íñigo Huguet) [2043454]
- nl80211: MBSSID and EMA support in AP mode (Íñigo Huguet) [2043454]
- nl80211: don't kfree() ERR_PTR() value (Íñigo Huguet) [2043454]
- cfg80211: always free wiphy specific regdomain (Íñigo Huguet) [2043454]
- mac80211: save transmit power envelope element and power constraint (Íñigo Huguet) [2043454]
- mac80211: add parse regulatory info in 6 GHz operation information (Íñigo Huguet) [2043454]
- ieee80211: add power type definition for 6 GHz (Íñigo Huguet) [2043454]
- mac80211: twt: don't use potentially unaligned pointer (Íñigo Huguet) [2043454]
- cfg80211: AP mode driver offload for FILS association crypto (Íñigo Huguet) [2043454]
- ath11k: monitor mode clean up to use separate APIs (Íñigo Huguet) [2043454]
- ath11k: add separate APIs for monitor mode (Íñigo Huguet) [2043454]
- ath11k: move static function ath11k_mac_vdev_setup_sync to top (Íñigo Huguet) [2043454]
- rtw88: 8821c: correct 2.4G tx power for type 2/4 NIC (Íñigo Huguet) [2043454]
- rtw88: 8821c: support RFE type4 wifi NIC (Íñigo Huguet) [2043454]
- brcmfmac: Replace zero-length array with flexible array member (Íñigo Huguet) [2043454]
- mac80211_hwsim: enable 6GHz channels (Íñigo Huguet) [2043454]
- mac80211: use ieee802_11_parse_elems() in ieee80211_prep_channel() (Íñigo Huguet) [2043454]
- nl80211: don't put struct cfg80211_ap_settings on stack (Íñigo Huguet) [2043454]
- mac80211: always allocate struct ieee802_11_elems (Íñigo Huguet) [2043454]
- mac80211: mlme: find auth challenge directly (Íñigo Huguet) [2043454]
- mac80211: move CRC into struct ieee802_11_elems (Íñigo Huguet) [2043454]
- mac80211: mesh: clean up rx_bcn_presp API (Íñigo Huguet) [2043454]
- mac80211: reduce stack usage in debugfs (Íñigo Huguet) [2043454]
- nl80211: prefer struct_size over open coded arithmetic (Íñigo Huguet) [2043454]
- mac80211: check hostapd configuration parsing twt requests (Íñigo Huguet) [2043454]
- cfg80211: honour V=1 in certificate code generation (Íñigo Huguet) [2043454]
- rt2x00: remove duplicate USB device ID (Íñigo Huguet) [2043454]
- wilc1000: increase config packets response wait timeout limit (Íñigo Huguet) [2043454]
- wilc1000: use correct write command sequence in wilc_spi_sync_ext() (Íñigo Huguet) [2043454]
- wilc1000: add 'initialized' flag check before adding an element to TX queue (Íñigo Huguet) [2043454]
- wilc1000: invoke chip reset register before firmware download (Íñigo Huguet) [2043454]
- wilc1000: ignore clockless registers status response for SPI (Íñigo Huguet) [2043454]
- wilc1000: handle read failure issue for clockless registers (Íñigo Huguet) [2043454]
- wilc1000: add reset/terminate/repeat command support for SPI bus (Íñigo Huguet) [2043454]
- wilc1000: configure registers to handle chip wakeup sequence (Íñigo Huguet) [2043454]
- wilc1000: add new WID to pass wake_enable information to firmware (Íñigo Huguet) [2043454]
- wilc1000: fix possible memory leak in cfg_scan_result() (Íñigo Huguet) [2043454]
- wilc1000: move 'deinit_lock' lock init/destroy inside module probe (Íñigo Huguet) [2043454]
- mwifiex: Fix copy-paste mistake when creating virtual interface (Íñigo Huguet) [2043454]
- mwifiex: Properly initialize private structure on interface type changes (Íñigo Huguet) [2043454]
- mwifiex: Handle interface type changes from AP to STATION (Íñigo Huguet) [2043454]
- mwifiex: Allow switching interface type from P2P_CLIENT to P2P_GO (Íñigo Huguet) [2043454]
- mwifiex: Update virtual interface counters right after setting bss_type (Íñigo Huguet) [2043454]
- mwifiex: Use helper function for counting interface types (Íñigo Huguet) [2043454]
- mwifiex: Run SET_BSS_MODE when changing from P2P to STATION vif-type (Íñigo Huguet) [2043454]
- mwifiex: Use function to check whether interface type change is allowed (Íñigo Huguet) [2043454]
- mwifiex: Small cleanup for handling virtual interface type changes (Íñigo Huguet) [2043454]
- rtw88: move adaptivity mechanism to firmware (Íñigo Huguet) [2043454]
- rtw88: support adaptivity for ETSI/JP DFS region (Íñigo Huguet) [2043454]
- rtw88: add regulatory strategy by chip type (Íñigo Huguet) [2043454]
- rtw88: upgrade rtw_regulatory mechanism and mapping (Íñigo Huguet) [2043454]
- brcmfmac: fix incorrect error prints (Íñigo Huguet) [2043454]
- ath11k: Align bss_chan_info structure with firmware (Íñigo Huguet) [2043454]
- ath11k: add support in survey dump with bss_chan_info (Íñigo Huguet) [2043454]
- ath11k: Rename atf_config to flag1 in target_resource_config (Íñigo Huguet) [2043454]
- ath11k: fix 4addr multicast packet tx (Íñigo Huguet) [2043454]
- ath11k: fix 4-addr tx failure for AP and STA modes (Íñigo Huguet) [2043454]
- ath9k: owl-loader: fetch pci init values through nvmem (Íñigo Huguet) [2043454]
- ath9k: fetch calibration data via nvmem subsystem (Íñigo Huguet) [2043454]

* Tue Feb 22 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-68.el9]
- net: ena: Extract recurring driver reset code into a function (Petr Oros) [2038150]
- net: ena: Change the name of bad_csum variable (Petr Oros) [2038150]
- net: ena: Add debug prints for invalid req_id resets (Petr Oros) [2038150]
- net: ena: Remove ena_calc_queue_size_ctx struct (Petr Oros) [2038150]
- net: ena: Move reset completion print to the reset function (Petr Oros) [2038150]
- net: ena: Remove redundant return code check (Petr Oros) [2038150]
- net: ena: Update LLQ header length in ena documentation (Petr Oros) [2038150]
- net: ena: Change ENI stats support check to use capabilities field (Petr Oros) [2038150]
- net: ena: Add capabilities field with support for ENI stats capability (Petr Oros) [2038150]
- net: ena: Change return value of ena_calc_io_queue_size() to void (Petr Oros) [2038150]
- net: ena: Fix error handling when calculating max IO queues number (Petr Oros) [2038150]
- net: ena: Fix wrong rx request id by resetting device (Petr Oros) [2038150]
- net: ena: Fix undefined state when tx request id is out of bounds (Petr Oros) [2038150]
- net/packet: rx_owner_map depends on pg_vec (Hangbin Liu) [2050329] {CVE-2021-22600}
- powerpc: security: Lock down the kernel if booted in secure boot mode (Desnes A. Nunes do Rosario) [2041984]
- drm/i915: Flush TLBs before releasing backing store (Dave Airlie) [2044335] {CVE-2022-0330}
- sfc: The RX page_ring is optional (Íñigo Huguet) [2042801]
- sfc: Check null pointer of rx_queue->page_ring (Íñigo Huguet) [2042801]
- sfc_ef100: potential dereference of null pointer (Íñigo Huguet) [2042801]
- sfc: Don't use netif_info before net_device setup (Íñigo Huguet) [2042801]
- sfc: Export fibre-specific supported link modes (Íñigo Huguet) [2042801]
- sfc: Fix reading non-legacy supported link modes (Íñigo Huguet) [2042801]
- ethernet: constify references to netdev->dev_addr in drivers (Íñigo Huguet) [2042801]
- sfc: last resort fallback for lack of xdp tx queues (Íñigo Huguet) [2042801]
- sfc: fallback for lack of xdp tx queues (Íñigo Huguet) [2042801]
- RDMA/cma: Do not change route.addr.src_addr.ss_family (Kamal Heib) [2032069] {CVE-2021-4028}
- kernel/sched/sched.h: Exclude cpuidle from KABI (Prarit Bhargava) [2033340]
- redhat/configs: Disable CONFIG_SENSORS_NCT6683 in RHEL for arm/aarch64 (Dean Nelson) [2041186]
- kernel.spec: Add glibc-static build requirement (Prarit Bhargava)
- libbpf: Fix memleak in libbpf_netlink_recv() (Toke Høiland-Jørgensen) [2052543]
- libbpf: Use dynamically allocated buffer when receiving netlink messages (Toke Høiland-Jørgensen) [2052543]
- redhat/configs: Disable arch_hw disabled CONFIGS (Prarit Bhargava) [2053029]
- netfilter: conntrack: re-init state for retransmitted syn-ack (Florian Westphal) [2051973]
- netfilter: conntrack: move synack init code to helper (Florian Westphal) [2051973]
- ext4: fix remount with 'abort' option (Lukas Czerner) [2049657]
- thunderbolt: Enable retry logic for intra-domain control packets (David Arcari) [1960445]
- thunderbolt: Handle ring interrupt by reading interrupt status register (David Arcari) [1960445]
- thunderbolt: Add vendor specific NHI quirk for auto-clearing interrupt status (David Arcari) [1960445]
- thunderbolt: Fix port linking by checking all adapters (David Arcari) [1960445]
- thunderbolt: Do not read control adapter config space (David Arcari) [1960445]

* Tue Feb 22 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-67.el9]
- kabi: Adding symbol strncpy_from_user (lib/strncpy_from_user.c) (Čestmír Kalina) [2008872]
- kabi: Adding symbol strlcpy (lib/string.c) (Čestmír Kalina) [2008872]
- kabi: Adding symbol strchr (lib/string.c) (Čestmír Kalina) [2008872]
- kabi: Adding symbol simple_strtoull (lib/vsprintf.c) (Čestmír Kalina) [2008872]
- kabi: Adding symbol simple_strtol (lib/vsprintf.c) (Čestmír Kalina) [2008872]
- kabi: Adding symbol memparse (lib/cmdline.c) (Čestmír Kalina) [2008872]
- kabi: Adding symbol strsep (lib/string.c) (Čestmír Kalina) [2008872]
- kabi: Adding symbol kstrtoll (lib/kstrtox.c) (Čestmír Kalina) [2008872]
- kabi: Adding symbol __bitmap_weight (lib/bitmap.c) (Čestmír Kalina) [2008872]
- kabi: Adding symbol vsprintf (lib/vsprintf.c) (Čestmír Kalina) [2008872]
- kabi: Adding symbol vsnprintf (lib/vsprintf.c) (Čestmír Kalina) [2008872]
- kabi: Adding symbol strstr (lib/string.c) (Čestmír Kalina) [2008872]
- kabi: Adding symbol strrchr (lib/string.c) (Čestmír Kalina) [2008872]
- kabi: Adding symbol strlcat (lib/string.c) (Čestmír Kalina) [2008872]
- kabi: Adding symbol strcpy (lib/string.c) (Čestmír Kalina) [2008872]
- kabi: Adding symbol sprintf (lib/vsprintf.c) (Čestmír Kalina) [2008872]
- kabi: Adding symbol strnlen (lib/string.c) (Čestmír Kalina) [2008872]
- kabi: Adding symbol strncpy (lib/string.c) (Čestmír Kalina) [2008872]
- kabi: Adding symbol snprintf (lib/vsprintf.c) (Čestmír Kalina) [2008872]
- kabi: Adding symbol memcmp (lib/string.c) (Čestmír Kalina) [2008872]
- kabi: Adding symbol dump_stack (lib/dump_stack.c) (Čestmír Kalina) [2008872]
- kabi: Adding symbol strncmp (lib/string.c) (Čestmír Kalina) [2008872]
- kabi: Adding symbol sscanf (lib/vsprintf.c) (Čestmír Kalina) [2008872]
- kabi: Adding symbol memset (lib/string.c) (Čestmír Kalina) [2008872]
- kabi: Adding symbol memmove (lib/string.c) (Čestmír Kalina) [2008872]
- kabi: Adding symbol __list_add_valid (lib/list_debug.c) (Čestmír Kalina) [2008872]
- kabi: Adding symbol strlen (lib/string.c) (Čestmír Kalina) [2008872]
- kabi: Adding symbol strcmp (lib/string.c) (Čestmír Kalina) [2008872]
- kabi: Adding symbol memcpy (lib/string.c) (Čestmír Kalina) [2008872]
- kabi: Adding symbol _copy_to_user (lib/usercopy.c) (Čestmír Kalina) [2008872]
- kabi: Adding symbol _copy_from_user (lib/usercopy.c) (Čestmír Kalina) [2008872]
- block: bio-integrity: Advance seed correctly for larger interval sizes (Ming Lei) [2044184]
- blk-mq: Fix wrong wakeup batch configuration which will cause hang (Ming Lei) [2044184]
- block: fix memory leak in disk_register_independent_access_ranges (Ming Lei) [2044184]
- block: fix async_depth sysfs interface for mq-deadline (Ming Lei) [2044184]
- blk-mq: fix tag_get wait task can't be awakened (Ming Lei) [2044184]
- block: Fix wrong offset in bio_truncate() (Ming Lei) [2044184]
- block: assign bi_bdev for cloned bios in blk_rq_prep_clone (Ming Lei) [2044184]
- block: Fix fsync always failed if once failed (Ming Lei) [2044184]
- block: don't protect submit_bio_checks by q_usage_counter (Ming Lei) [2044184]
- blk-mq: use bio->bi_opf after bio is checked (Ming Lei) [2044184]
- block: fix double bio queue when merging in cached request path (Ming Lei) [2044184]
- blk-mq: cleanup request allocation (Ming Lei) [2044184]
- blk-mq: simplify the plug handling in blk_mq_submit_bio (Ming Lei) [2044184]
- block: null_blk: only set set->nr_maps as 3 if active poll_queues is > 0 (Ming Lei) [2044184]
- null_blk: allow zero poll queues (Ming Lei) [2044184]
- iocost: Fix divide-by-zero on donation from low hweight cgroup (Ming Lei) [2044184]
- block: fix ioprio_get(IOPRIO_WHO_PGRP) vs setuid(2) (Ming Lei) [2044184]
- block: fix single bio async DIO error handling (Ming Lei) [2044184]
- usb: xhci: Extend support for runtime power management for AMD's Yellow carp. (Renjith Pananchikkal) [2015776]
- usb: xhci: Enable runtime-pm by default on AMD Yellow Carp platform (Renjith Pananchikkal) [2015776]
- redhat: switch the vsyscall config to CONFIG_LEGACY_VSYSCALL_XONLY=y (Herton R. Krzesinski) [2023041]
- ice: Implement support for SMA and U.FL on E810-T (Jonathan Toppins) [1975008]
- ice: Add support for SMA control multiplexer (Jonathan Toppins) [1975008]
- ice: Implement functions for reading and setting GPIO pins (Jonathan Toppins) [1975008]
- ice: Refactor ice_aqc_link_topo_addr (Jonathan Toppins) [1975008]

* Mon Feb 21 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-66.el9]
- lockd: fix failure to cleanup client locks (Scott Mayhew) [2049200]
- lockd: fix server crash on reboot of client holding lock (Scott Mayhew) [2049200]
- SUNRPC: Don't dereference xprt->snd_task if it's a cookie (Scott Mayhew) [2049200]
- tracing: Fix mismatched comment in __string_len (Scott Mayhew) [2049200]
- nfs: block notification on fs with its own ->lock (Scott Mayhew) [2049200]
- NFSD: Fix READDIR buffer overflow (Scott Mayhew) [2049200]
- nfsd: fix use-after-free due to delegation race (Scott Mayhew) [2049200]
- nfsd: Fix nsfd startup race (again) (Scott Mayhew) [2049200]
- SUNRPC: use different lock keys for INET6 and LOCAL (Scott Mayhew) [2049200]
- NFSv4.1: handle NFS4ERR_NOSPC by CREATE_SESSION (Scott Mayhew) [2049200]
- NFSv42: Fix pagecache invalidation after COPY/CLONE (Scott Mayhew) [2049200]
- NFS: Add a tracepoint to show the results of nfs_set_cache_invalid() (Scott Mayhew) [2049200]
- NFSv42: Don't fail clone() unless the OP_CLONE operation failed (Scott Mayhew) [2049200]
- NFSD: Fix exposure in nfsd4_decode_bitmap() (Scott Mayhew) [2049200]
- NFSv4: Sanity check the parameters in nfs41_update_target_slotid() (Scott Mayhew) [2049200]
- NFS: Remove the nfs4_label argument from decode_getattr_*() functions (Scott Mayhew) [2049200]
- NFS: Remove the nfs4_label argument from nfs_setsecurity (Scott Mayhew) [2049200]
- NFS: Remove the nfs4_label argument from nfs_fhget() (Scott Mayhew) [2049200]
- NFS: Remove the nfs4_label argument from nfs_add_or_obtain() (Scott Mayhew) [2049200]
- NFS: Remove the nfs4_label argument from nfs_instantiate() (Scott Mayhew) [2049200]
- NFS: Remove the nfs4_label from the nfs_setattrres (Scott Mayhew) [2049200]
- NFS: Remove the nfs4_label from the nfs4_getattr_res (Scott Mayhew) [2049200]
- NFS: Remove the f_label from the nfs4_opendata and nfs_openres (Scott Mayhew) [2049200]
- NFS: Remove the nfs4_label from the nfs4_lookupp_res struct (Scott Mayhew) [2049200]
- NFS: Remove the label from the nfs4_lookup_res struct (Scott Mayhew) [2049200]
- NFS: Remove the nfs4_label from the nfs4_link_res struct (Scott Mayhew) [2049200]
- NFS: Remove the nfs4_label from the nfs4_create_res struct (Scott Mayhew) [2049200]
- NFS: Remove the nfs4_label from the nfs_entry struct (Scott Mayhew) [2049200]
- NFS: Create a new nfs_alloc_fattr_with_label() function (Scott Mayhew) [2049200]
- NFS: Always initialise fattr->label in nfs_fattr_alloc() (Scott Mayhew) [2049200]
- NFSv4.2: alloc_file_pseudo() takes an open flag, not an f_mode (Scott Mayhew) [2049200]
- NFS: Don't allocate nfs_fattr on the stack in __nfs42_ssc_open() (Scott Mayhew) [2049200]
- NFSv4: Remove unnecessary 'minor version' check (Scott Mayhew) [2049200]
- NFSv4: Fix potential Oops in decode_op_map() (Scott Mayhew) [2049200]
- NFSv4: Ensure decode_compound_hdr() sanity checks the tag (Scott Mayhew) [2049200]
- NFS: Don't trace an uninitialised value (Scott Mayhew) [2049200]
- SUNRPC: Prevent immediate close+reconnect (Scott Mayhew) [2049200]
- SUNRPC: Fix races when closing the socket (Scott Mayhew) [2049200]
- NFSv4.2 add tracepoint to OFFLOAD_CANCEL (Scott Mayhew) [2049200]
- NFSv4.2 add tracepoint to COPY_NOTIFY (Scott Mayhew) [2049200]
- NFSv4.2 add tracepoint to CB_OFFLOAD (Scott Mayhew) [2049200]
- NFSv4.2 add tracepoint to CLONE (Scott Mayhew) [2049200]
- NFSv4.2 add tracepoint to COPY (Scott Mayhew) [2049200]
- NFSv4.2 add tracepoints to FALLOCATE and DEALLOCATE (Scott Mayhew) [2049200]
- NFSv4.2 add tracepoint to SEEK (Scott Mayhew) [2049200]
- SUNRPC: Check if the xprt is connected before handling sysfs reads (Scott Mayhew) [2049200]
- nfs4: take a reference on the nfs_client when running FREE_STATEID (Scott Mayhew) [2049200]
- NFS: Add offset to nfs_aop_readahead tracepoint (Scott Mayhew) [2049200]
- xprtrdma: Fix a maybe-uninitialized compiler warning (Scott Mayhew) [2049200]
- NFS: Move NFS protocol display macros to global header (Scott Mayhew) [2049200]
- NFS: Move generic FS show macros to global header (Scott Mayhew) [2049200]
- nfsd4: remove obselete comment (Scott Mayhew) [2049200]
- SUNRPC: Clean up xs_tcp_setup_sock() (Scott Mayhew) [2049200]
- SUNRPC: Replace use of socket sk_callback_lock with sock_lock (Scott Mayhew) [2049200]
- NFSv4: Fix a regression in nfs_set_open_stateid_locked() (Scott Mayhew) [2049200]
- fsnotify: Protect fsnotify_handle_inode_event from no-inode events (Scott Mayhew) [2049200]
- NFS: Remove redundant call to __set_page_dirty_nobuffers (Scott Mayhew) [2049200]
- sunrpc: remove unnecessary test in rpc_task_set_client() (Scott Mayhew) [2049200]
- NFS: Unexport nfs_probe_fsinfo() (Scott Mayhew) [2049200]
- NFS: Call nfs_probe_server() during a fscontext-reconfigure event (Scott Mayhew) [2049200]
- NFS: Replace calls to nfs_probe_fsinfo() with nfs_probe_server() (Scott Mayhew) [2049200]
- NFS: Move nfs_probe_destination() into the generic client (Scott Mayhew) [2049200]
- NFS: Create an nfs4_server_set_init_caps() function (Scott Mayhew) [2049200]
- NFS: Remove --> and <-- dprintk call sites (Scott Mayhew) [2049200]
- SUNRPC: Trace calls to .rpc_call_done (Scott Mayhew) [2049200]
- NFS: Replace dprintk callsites in nfs_readpage(s) (Scott Mayhew) [2049200]
- SUNRPC: Use BIT() macro in rpc_show_xprt_state() (Scott Mayhew) [2049200]
- SUNRPC: Tracepoints should display tk_pid and cl_clid as a fixed-size field (Scott Mayhew) [2049200]
- xprtrdma: Remove rpcrdma_ep::re_implicit_roundup (Scott Mayhew) [2049200]
- xprtrdma: Provide a buffer to pad Write chunks of unaligned length (Scott Mayhew) [2049200]
- Fix user namespace leak (Scott Mayhew) [2049200]
- NFS: Save some space in the inode (Scott Mayhew) [2049200]
- NFS: Fix WARN_ON due to unionization of nfs_inode.nrequests (Scott Mayhew) [2049200]
- NFSv4: Fixes for nfs4_inode_return_delegation() (Scott Mayhew) [2049200]
- NFS: Fix an Oops in pnfs_mark_request_commit() (Scott Mayhew) [2049200]
- NFS: Fix up commit deadlocks (Scott Mayhew) [2049200]
- NFSD:fix boolreturn.cocci warning (Scott Mayhew) [2049200]
- nfsd: update create verifier comment (Scott Mayhew) [2049200]
- SUNRPC: Change return value type of .pc_encode (Scott Mayhew) [2049200]
- SUNRPC: Replace the "__be32 *p" parameter to .pc_encode (Scott Mayhew) [2049200]
- NFSD: Save location of NFSv4 COMPOUND status (Scott Mayhew) [2049200]
- SUNRPC: Change return value type of .pc_decode (Scott Mayhew) [2049200]
- SUNRPC: Replace the "__be32 *p" parameter to .pc_decode (Scott Mayhew) [2049200]
- SUNRPC: De-duplicate .pc_release() call sites (Scott Mayhew) [2049200]
- SUNRPC: Simplify the SVC dispatch code path (Scott Mayhew) [2049200]
- NFS: Fix deadlocks in nfs_scan_commit_list() (Scott Mayhew) [2049200]
- NFS: Instrument i_size_write() (Scott Mayhew) [2049200]
- SUNRPC: Per-rpc_clnt task PIDs (Scott Mayhew) [2049200]
- NFS: Remove unnecessary TRACE_DEFINE_ENUM()s (Scott Mayhew) [2049200]
- NFSD: Keep existing listeners on portlist error (Scott Mayhew) [2049200]
- nfs: Fix kerneldoc warning shown up by W=1 (Scott Mayhew) [2049200]
- SUNRPC: Capture value of xdr_buf::page_base (Scott Mayhew) [2049200]
- SUNRPC: Add trace event when alloc_pages_bulk() makes no progress (Scott Mayhew) [2049200]
- svcrdma: Split svcrmda_wc_{read,write} tracepoints (Scott Mayhew) [2049200]
- svcrdma: Split the svcrdma_wc_send() tracepoint (Scott Mayhew) [2049200]
- svcrdma: Split the svcrdma_wc_receive() tracepoint (Scott Mayhew) [2049200]
- pnfs/flexfiles: Fix misplaced barrier in nfs4_ff_layout_prepare_ds (Scott Mayhew) [2049200]
- NFS: Remove unnecessary page cache invalidations (Scott Mayhew) [2049200]
- NFS: Do not flush the readdir cache in nfs_dentry_iput() (Scott Mayhew) [2049200]
- NFS: Fix dentry verifier races (Scott Mayhew) [2049200]
- NFS: Further optimisations for 'ls -l' (Scott Mayhew) [2049200]
- NFS: Fix up nfs_readdir_inode_mapping_valid() (Scott Mayhew) [2049200]
- NFS: Ignore the directory size when marking for revalidation (Scott Mayhew) [2049200]
- NFS: Don't set NFS_INO_DATA_INVAL_DEFER and NFS_INO_INVALID_DATA (Scott Mayhew) [2049200]
- NFS: Default change_attr_type to NFS4_CHANGE_TYPE_IS_UNDEFINED (Scott Mayhew) [2049200]
- NFSv4: Retrieve ACCESS on open if we're not using NFS4_CREATE_EXCLUSIVE (Scott Mayhew) [2049200]
- NFS: Fix a few more clear_bit() instances that need release semantics (Scott Mayhew) [2049200]
- SUNRPC: xprt_clear_locked() only needs release memory semantics (Scott Mayhew) [2049200]
- SUNRPC: Remove unnecessary memory barriers (Scott Mayhew) [2049200]
- SUNRPC: Remove WQ_HIGHPRI from xprtiod (Scott Mayhew) [2049200]
- SUNRPC: Add cond_resched() at the appropriate point in __rpc_execute() (Scott Mayhew) [2049200]
- SUNRPC: Partial revert of commit 6f9f17287e78 (Scott Mayhew) [2049200]
- NFS: Fix up nfs_ctx_key_to_expire() (Scott Mayhew) [2049200]
- NFS: Label the dentry with a verifier in nfs_rmdir() and nfs_unlink() (Scott Mayhew) [2049200]
- NFS: Label the dentry with a verifier in nfs_link(), nfs_symlink() (Scott Mayhew) [2049200]
- NFSD: Have legacy NFSD WRITE decoders use xdr_stream_subsegment() (Scott Mayhew) [2049200]
- SUNRPC: xdr_stream_subsegment() must handle non-zero page_bases (Scott Mayhew) [2049200]
- NFSD: Initialize pointer ni with NULL and not plain integer 0 (Scott Mayhew) [2049200]
- NFSD: simplify struct nfsfh (Scott Mayhew) [2049200]
- NFSD: drop support for ancient filehandles (Scott Mayhew) [2049200]
- NFSD: move filehandle format declarations out of "uapi". (Scott Mayhew) [2049200]
- SUNRPC: fix sign error causing rpcsec_gss drops (Scott Mayhew) [2049200]
- nfsd: Fix a warning for nfsd_file_close_inode (Scott Mayhew) [2049200]
- nfsd4: Handle the NFSv4 READDIR 'dircount' hint being zero (Scott Mayhew) [2049200]
- nfsd: fix error handling of register_pernet_subsys() in init_nfsd() (Scott Mayhew) [2049200]
- UNRPC: Return specific error code on kmalloc failure (Scott Mayhew) [2049200]
- NFSD: Optimize DRC bucket pruning (Scott Mayhew) [2049200]
- nfsd: don't alloc under spinlock in rpc_parse_scope_id (Scott Mayhew) [2049200]
- nfsd: back channel stuck in SEQ4_STATUS_CB_PATH_DOWN (Scott Mayhew) [2049200]
- NLM: Fix svcxdr_encode_owner() (Scott Mayhew) [2049200]
- SUNRPC: improve error response to over-size gss credential (Scott Mayhew) [2049200]
- SUNRPC: don't pause on incomplete allocation (Scott Mayhew) [2049200]
- NFS: Always provide aligned buffers to the RPC read layers (Scott Mayhew) [2049200]
- NFSv4.1 add network transport when session trunking is detected (Scott Mayhew) [2049200]
- SUNRPC enforce creation of no more than max_connect xprts (Scott Mayhew) [2049200]
- NFSv4 introduce max_connect mount options (Scott Mayhew) [2049200]
- SUNRPC add xps_nunique_destaddr_xprts to xprt_switch_info in sysfs (Scott Mayhew) [2049200]
- SUNRPC keep track of number of transports to unique addresses (Scott Mayhew) [2049200]
- NFSv3: Delete duplicate judgement in nfs3_async_handle_jukebox (Scott Mayhew) [2049200]
- SUNRPC: Tweak TCP socket shutdown in the RPC client (Scott Mayhew) [2049200]
- SUNRPC: Simplify socket shutdown when not reusing TCP ports (Scott Mayhew) [2049200]
- nfsd: fix crash on LOCKT on reexported NFSv3 (Scott Mayhew) [2049200]
- nfs: don't allow reexport reclaims (Scott Mayhew) [2049200]
- lockd: don't attempt blocking locks on nfs reexports (Scott Mayhew) [2049200]
- nfs: don't atempt blocking locks on nfs reexports (Scott Mayhew) [2049200]
- Keep read and write fds with each nlm_file (Scott Mayhew) [2049200]
- lockd: update nlm_lookup_file reexport comment (Scott Mayhew) [2049200]
- nlm: minor refactoring (Scott Mayhew) [2049200]
- nlm: minor nlm_lookup_file argument change (Scott Mayhew) [2049200]
- lockd: lockd server-side shouldn't set fl_ops (Scott Mayhew) [2049200]
- SUNRPC: Server-side disconnect injection (Scott Mayhew) [2049200]
- SUNRPC: Move client-side disconnect injection (Scott Mayhew) [2049200]
- SUNRPC: Add a /sys/kernel/debug/fail_sunrpc/ directory (Scott Mayhew) [2049200]
- redhat/configs: Add CONFIG_FAIL_SUNRPC (Scott Mayhew) [2049200]
- svcrdma: xpt_bc_xprt is already clear in __svc_rdma_free() (Scott Mayhew) [2049200]
- nfsd4: Fix forced-expiry locking (Scott Mayhew) [2049200]
- rpc: fix gss_svc_init cleanup on failure (Scott Mayhew) [2049200]
- SUNRPC: Add RPC_AUTH_TLS protocol numbers (Scott Mayhew) [2049200]
- lockd: change the proc_handler for nsm_use_hostnames (Scott Mayhew) [2049200]
- sysctl: introduce new proc handler proc_dobool (Scott Mayhew) [2049200]
- SUNRPC: Fix a NULL pointer deref in trace_svc_stats_latency() (Scott Mayhew) [2049200]
- NFSD: remove vanity comments (Scott Mayhew) [2049200]
- svcrdma: Convert rdma->sc_rw_ctxts to llist (Scott Mayhew) [2049200]
- svcrdma: Relieve contention on sc_send_lock. (Scott Mayhew) [2049200]
- svcrdma: Fewer calls to wake_up() in Send completion handler (Scott Mayhew) [2049200]
- lockd: Fix invalid lockowner cast after vfs_test_lock (Scott Mayhew) [2049200]
- NFSD: Use new __string_len C macros for nfsd_clid_class (Scott Mayhew) [2049200]
- NFSD: Use new __string_len C macros for the nfs_dirent tracepoint (Scott Mayhew) [2049200]
- tracing: Add trace_event helper macros __string_len() and __assign_str_len() (Scott Mayhew) [2049200]
- NFSD: Batch release pages during splice read (Scott Mayhew) [2049200]
- SUNRPC: Add svc_rqst_replace_page() API (Scott Mayhew) [2049200]
- NFSD: Clean up splice actor (Scott Mayhew) [2049200]
- NFSv4.2: remove restriction of copy size for inter-server copy. (Scott Mayhew) [2049200]
- NFS: Clean up the synopsis of callback process_op() (Scott Mayhew) [2049200]
- NFS: Extract the xdr_init_encode/decode() calls from decode_compound (Scott Mayhew) [2049200]
- NFS: Remove unused callback void decoder (Scott Mayhew) [2049200]
- NFS: Add a private local dispatcher for NFSv4 callback operations (Scott Mayhew) [2049200]
- SUNRPC: Eliminate the RQ_AUTHERR flag (Scott Mayhew) [2049200]
- SUNRPC: Set rq_auth_stat in the pg_authenticate() callout (Scott Mayhew) [2049200]
- SUNRPC: Add svc_rqst::rq_auth_stat (Scott Mayhew) [2049200]
- SUNRPC: Add dst_port to the sysfs xprt info file (Scott Mayhew) [2049200]
- SUNRPC: Add srcaddr as a file in sysfs (Scott Mayhew) [2049200]
- sunrpc: Fix return value of get_srcport() (Scott Mayhew) [2049200]
- SUNRPC/xprtrdma: Fix reconnection locking (Scott Mayhew) [2049200]
- SUNRPC: Clean up scheduling of autoclose (Scott Mayhew) [2049200]
- SUNRPC: Fix potential memory corruption (Scott Mayhew) [2049200]
- NFSv4/pnfs: The layout barrier indicate a minimal value for the seqid (Scott Mayhew) [2049200]
- NFSv4/pNFS: Always allow update of a zero valued layout barrier (Scott Mayhew) [2049200]
- NFSv4/pNFS: Remove dead code (Scott Mayhew) [2049200]
- NFSv4/pNFS: Fix a layoutget livelock loop (Scott Mayhew) [2049200]
- SUNRPC: Convert rpc_client refcount to use refcount_t (Scott Mayhew) [2049200]
- xprtrdma: Eliminate rpcrdma_post_sends() (Scott Mayhew) [2049200]
- xprtrdma: Add an xprtrdma_post_send_err tracepoint (Scott Mayhew) [2049200]
- xprtrdma: Add xprtrdma_post_recvs_err() tracepoint (Scott Mayhew) [2049200]
- xprtrdma: Put rpcrdma_reps before waking the tear-down completion (Scott Mayhew) [2049200]
- xprtrdma: Disconnect after an ib_post_send() immediate error (Scott Mayhew) [2049200]
- SUNRPC: Record timeout value in xprt_retransmit tracepoint (Scott Mayhew) [2049200]
- SUNRPC: xprt_retransmit() displays the the NULL procedure incorrectly (Scott Mayhew) [2049200]
- SUNRPC: Update trace flags (Scott Mayhew) [2049200]
- SUNRPC: Remove unneeded TRACE_DEFINE_ENUMs (Scott Mayhew) [2049200]
- SUNRPC: Unset RPC_TASK_NO_RETRANS_TIMEOUT for NULL RPCs (Scott Mayhew) [2049200]
- SUNRPC: Refactor rpc_ping() (Scott Mayhew) [2049200]

* Sat Feb 19 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-65.el9]
- ALSA: memalloc: Unify x86 SG-buffer handling (take#3) (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: add mapping for MSI MPG X570S Carbon Max Wifi. (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Drop CONFIG_PM ifdefs (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Fix dB level of Bose Revolve+ SoundLink (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Add minimal-mute notion in dB mapping table (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Use int for dB map values (Jaroslav Kysela) [2017320]
- ALSA: hda/tegra: Fix Tegra194 HDA reset failure (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek: Use ALC285_FIXUP_HP_GPIO_LED on another HP laptop (Jaroslav Kysela) [2017320]
- ALSA: hda: Add new AlderLake-P variant PCI ID (Jaroslav Kysela) [2017320]
- ALSA: hda: Add AlderLake-N PCI ID (Jaroslav Kysela) [2017320]
- ALSA: hda: use swap() to make code cleaner (Jaroslav Kysela) [2017320]
- ALSA: Fix some typo (Jaroslav Kysela) [2017320]
- ALSA: hda/hdmi: Consider ELD is invalid when no SAD is present (Jaroslav Kysela) [2017320]
- ALSA: hda: Remove redundant runtime PM calls (Jaroslav Kysela) [2017320]
- ALSA: hda: Do disconnect jacks at codec unbind (Jaroslav Kysela) [2017320]
- ALSA: hda: intel: More comprehensive PM runtime setup for controller driver (Jaroslav Kysela) [2017320]
- ASoC: SOF: Intel: fix build issue related to CODEC_PROBE_ENTRIES (Jaroslav Kysela) [2017320]
- ASoC: cs42l42: Report initial jack state (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek: Re-order quirk entries for Lenovo (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek: Add quirk for Legion Y9000X 2020 (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek: Add speaker fixup for some Yoga 15ITL5 devices (Jaroslav Kysela) [2017320]
- tools headers UAPI: Sync sound/asound.h with the kernel sources (Jaroslav Kysela) [2017320]
- tools include UAPI: Sync sound/asound.h copy with the kernel sources (Jaroslav Kysela) [2017320]
- tools include UAPI: Sync sound/asound.h copy with the kernel sources (Jaroslav Kysela) [2017320]
- ASoC: SOF: handle paused streams during system suspend (Jaroslav Kysela) [2017320]
- ASoC: SOF: sof-audio: setup sched widgets during pipeline complete step (Jaroslav Kysela) [2017320]
- ASoC: SOF: free widgets in sof_tear_down_pipelines() for static pipelines (Jaroslav Kysela) [2017320]
- ASoC: mediatek: mt8195: correct default value (Jaroslav Kysela) [2017320]
- ASoC: mediatek: mt8195: correct pcmif BE dai control flow (Jaroslav Kysela) [2017320]
- ALSA: RHEL - update kernel configs for RHEL 9.0 (Jaroslav Kysela) [2017320]
- ALSA: core: Fix SSID quirk lookup for subvendor=0 (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Fix Jack detection after resume (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Increase delay during jack detection (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek - Fix silent output on Gigabyte X570 Aorus Master after reboot from Windows (Jaroslav Kysela) [2017320]
- ASoC: Intel: catpt: Test dmaengine_submit() result before moving on (Jaroslav Kysela) [2017320]
- ASoC: amd: Fix dependency for SPI master (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Drop superfluous '0' in Presonus Studio 1810c's ID (Jaroslav Kysela) [2017320]
- ALSA: oss: fix compile error when OSS_DEBUG is enabled (Jaroslav Kysela) [2017320]
- ALSA: hda: Make proper use of timecounter (Jaroslav Kysela) [2017320]
- ALSA: led: Use restricted type for iface assignment (Jaroslav Kysela) [2017320]
- ALSA: hda: Fix potential deadlock at codec unbinding (Jaroslav Kysela) [2017320]
- ALSA: hda: Add missing rwsem around snd_ctl_remove() calls (Jaroslav Kysela) [2017320]
- ALSA: PCM: Add missing rwsem around snd_ctl_remove() calls (Jaroslav Kysela) [2017320]
- ALSA: jack: Add missing rwsem around snd_ctl_remove() calls (Jaroslav Kysela) [2017320]
- ASoC: Intel: sof_sdw: fix jack detection on HP Spectre x360 convertible (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek: Fix quirk for Clevo NJ51CU (Jaroslav Kysela) [2017320]
- ALSA: rawmidi - fix the uninitalized user_pversion (Jaroslav Kysela) [2017320]
- ALSA: hda: intel-sdw-acpi: go through HDAS ACPI at max depth of 2 (Jaroslav Kysela) [2017320]
- ALSA: hda: intel-sdw-acpi: harden detection of controller (Jaroslav Kysela) [2017320]
- ALSA: hda/hdmi: Disable silent stream on GLK (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek: fix mute/micmute LEDs for a HP ProBook (Jaroslav Kysela) [2017320]
- ASoC: meson: aiu: Move AIU_I2S_MISC hold setting to aiu-fifo-i2s (Jaroslav Kysela) [2017320]
- ASoC: meson: aiu: fifo: Add missing dma_coerce_mask_and_coherent() (Jaroslav Kysela) [2017320]
- ASoC: tas2770: Fix setting of high sample rates (Jaroslav Kysela) [2017320]
- ASoC: rt5682: fix the wrong jack type detected (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek: Add new alc285-hp-amp-init model (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek: Amp init fixup for HP ZBook 15 G6 (Jaroslav Kysela) [2017320]
- ASoC: tegra: Restore headphones jack name on Nyan Big (Jaroslav Kysela) [2017320]
- ASoC: tegra: Add DAPM switches for headphones and mic jack (Jaroslav Kysela) [2017320]
- ALSA: jack: Check the return value of kstrdup() (Jaroslav Kysela) [2017320]
- ALSA: drivers: opl3: Fix incorrect use of vp->state (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek - Add headset Mic support for Lenovo ALC897 platform (Jaroslav Kysela) [2017320]
- ASoC: SOF: Intel: pci-tgl: add new ADL-P variant (Jaroslav Kysela) [2017320]
- ASoC: SOF: Intel: pci-tgl: add ADL-N support (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Reorder snd_djm_devices[] entries (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek: Fix quirk for TongFang PHxTxX1 (Jaroslav Kysela) [2017320]
- ALSA: ctl: Fix copy of updated id with element read/write (Jaroslav Kysela) [2017320]
- ALSA: pcm: oss: Handle missing errors in snd_pcm_oss_change_params*() (Jaroslav Kysela) [2017320]
- ALSA: pcm: oss: Limit the period size to 16MB (Jaroslav Kysela) [2017320]
- ALSA: pcm: oss: Fix negative period/buffer sizes (Jaroslav Kysela) [2017320]
- ASoC: codecs: wsa881x: fix return values from kcontrol put (Jaroslav Kysela) [2017320]
- ASoC: codecs: wcd934x: return correct value from mixer put (Jaroslav Kysela) [2017320]
- ASoC: codecs: wcd934x: handle channel mappping list correctly (Jaroslav Kysela) [2017320]
- ASoC: qdsp6: q6routing: Fix return value from msm_routing_put_audio_mixer (Jaroslav Kysela) [2017320]
- ALSA: hda/hdmi: fix HDA codec entry table order for ADL-P (Jaroslav Kysela) [2017320]
- ALSA: hda: Add Intel DG2 PCI ID and HDMI codec vid (Jaroslav Kysela) [2017320]
- ASoC: SOF: Intel: Retry codec probing if it fails (Jaroslav Kysela) [2017320]
- ASoC: amd: fix uninitialized variable in snd_acp6x_probe() (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Set PMSG_ON earlier inside cs8409 driver (Jaroslav Kysela) [2017320]
- ASoC: rt5682s: Fix crash due to out of scope stack vars (Jaroslav Kysela) [2017320]
- ASoC: rt5682: Fix crash due to out of scope stack vars (Jaroslav Kysela) [2017320]
- ASoC: tegra: Use normal system sleep for ADX (Jaroslav Kysela) [2017320]
- ASoC: tegra: Use normal system sleep for AMX (Jaroslav Kysela) [2017320]
- ASoC: tegra: Use normal system sleep for Mixer (Jaroslav Kysela) [2017320]
- ASoC: tegra: Use normal system sleep for MVC (Jaroslav Kysela) [2017320]
- ASoC: tegra: Use normal system sleep for SFC (Jaroslav Kysela) [2017320]
- ASoC: tegra: Balance runtime PM count (Jaroslav Kysela) [2017320]
- ASoC: SOF: hda: reset DAI widget before reconfiguring it (Jaroslav Kysela) [2017320]
- ASoC: cs35l41: Set the max SPI speed for the whole device (Jaroslav Kysela) [2017320]
- ALSA: intel-dsp-config: add quirk for CML devices based on ES8336 codec (Jaroslav Kysela) [2017320]
- ASoC: Intel: soc-acpi: add entry for ESSX8336 on CML (Jaroslav Kysela) [2017320]
- ASoC: rk817: Add module alias for rk817-codec (Jaroslav Kysela) [2017320]
- ASoC: soc-acpi: Set mach->id field on comp_ids matches (Jaroslav Kysela) [2017320]
- ALSA: intel-dsp-config: add quirk for JSL devices based on ES8336 codec (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Don't start stream for capture at prepare (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Switch back to non-latency mode at a later point (Jaroslav Kysela) [2017320]
- ALSA: ctxfi: Fix out-of-range access (Jaroslav Kysela) [2017320]
- ASoC: tegra: Fix kcontrol put callback in Mixer (Jaroslav Kysela) [2017320]
- ASoC: tegra: Fix kcontrol put callback in ADX (Jaroslav Kysela) [2017320]
- ASoC: tegra: Fix kcontrol put callback in AMX (Jaroslav Kysela) [2017320]
- ASoC: tegra: Fix kcontrol put callback in SFC (Jaroslav Kysela) [2017320]
- ASoC: tegra: Fix kcontrol put callback in MVC (Jaroslav Kysela) [2017320]
- ASoC: tegra: Fix kcontrol put callback in AHUB (Jaroslav Kysela) [2017320]
- ASoC: tegra: Fix kcontrol put callback in DSPK (Jaroslav Kysela) [2017320]
- ASoC: tegra: Fix kcontrol put callback in DMIC (Jaroslav Kysela) [2017320]
- ASoC: tegra: Fix kcontrol put callback in I2S (Jaroslav Kysela) [2017320]
- ASoC: tegra: Fix kcontrol put callback in ADMAIF (Jaroslav Kysela) [2017320]
- ASoC: tegra: Fix wrong value type in MVC (Jaroslav Kysela) [2017320]
- ASoC: tegra: Fix wrong value type in SFC (Jaroslav Kysela) [2017320]
- ASoC: tegra: Fix wrong value type in DSPK (Jaroslav Kysela) [2017320]
- ASoC: tegra: Fix wrong value type in DMIC (Jaroslav Kysela) [2017320]
- ASoC: tegra: Fix wrong value type in I2S (Jaroslav Kysela) [2017320]
- ASoC: tegra: Fix wrong value type in ADMAIF (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek: Fix LED on HP ProBook 435 G7 (Jaroslav Kysela) [2017320]
- ASoC: stm32: i2s: fix 32 bits channel length without mclk (Jaroslav Kysela) [2017320]
- ASoC: codecs: lpass-rx-macro: fix HPHR setting CLSH mask (Jaroslav Kysela) [2017320]
- ASoC: codecs: wcd934x: return error code correctly from hw_params (Jaroslav Kysela) [2017320]
- ASoC: codecs: wcd938x: fix volatile register range (Jaroslav Kysela) [2017320]
- ASoC: topology: Add missing rwsem around snd_ctl_remove() calls (Jaroslav Kysela) [2017320]
- ASoC: qdsp6: q6routing: validate port id before setting up route (Jaroslav Kysela) [2017320]
- ASoC: qdsp6: q6adm: improve error reporting (Jaroslav Kysela) [2017320]
- ASoC: qdsp6: q6asm: fix q6asm_dai_prepare error handling (Jaroslav Kysela) [2017320]
- ASoC: qdsp6: q6routing: Conditionally reset FrontEnd Mixer (Jaroslav Kysela) [2017320]
- ASoC: qdsp6: qdsp6: q6prm: handle clk disable correctly (Jaroslav Kysela) [2017320]
- ASoC: wm_adsp: wm_adsp_control_add() error: uninitialized symbol 'ret' (Jaroslav Kysela) [2017320]
- ALSA: cmipci: Drop stale variable assignment (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek: Add quirk for ASRock NUC Box 1100 (Jaroslav Kysela) [2017320]
- ASoC: rsnd: fixup DMAEngine API (Jaroslav Kysela) [2017320]
- ASoC: SOF: build compression interface into snd_sof.ko (Jaroslav Kysela) [2017320]
- ASoC: mediatek: mt8173: Fix debugfs registration for components (Jaroslav Kysela) [2017320]
- ASoC: rt5682: Re-detect the combo jack after resuming (Jaroslav Kysela) [2017320]
- ASoC: rt5682: Avoid the unexpected IRQ event during going to suspend (Jaroslav Kysela) [2017320]
- ASoC: rt1011: revert 'I2S Reference' to SOC_ENUM_EXT (Jaroslav Kysela) [2017320]
- ASoC: rt9120: Add the compatibility with rt9120s (Jaroslav Kysela) [2017320]
- ASoC: rt9120: Fix clock auto sync issue when fs is the multiple of 48 (Jaroslav Kysela) [2017320]
- ASoC: rt9120: Update internal ocp level to the correct value (Jaroslav Kysela) [2017320]
- ALSA: fireworks: add support for Loud Onyx 1200f quirk (Jaroslav Kysela) [2017320]
- ALSA: hda: fix general protection fault in azx_runtime_idle (Jaroslav Kysela) [2017320]
- ALSA: hda: Free card instance properly at probe errors (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek: Add quirk for HP EliteBook 840 G7 mute LED (Jaroslav Kysela) [2017320]
- ALSA: memalloc: Remove a stale comment (Jaroslav Kysela) [2017320]
- ALSA: synth: missing check for possible NULL after the call to kstrdup (Jaroslav Kysela) [2017320]
- ALSA: memalloc: Use proper SG helpers for noncontig allocations (Jaroslav Kysela) [2017320]
- ALSA: pci: rme: Fix unaligned buffer addresses (Jaroslav Kysela) [2017320]
- ALSA: firewire-motu: add support for MOTU Track 16 (Jaroslav Kysela) [2017320]
- ALSA: PCM: Fix NULL dereference at mmap checks (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek: Add quirk for ASUS UX550VE (Jaroslav Kysela) [2017320]
- ASoC: Intel: sof_sdw: Add support for SKU 0B12 product (Jaroslav Kysela) [2017320]
- ASoC: Intel: soc-acpi: add SKU 0B29 SoundWire configuration (Jaroslav Kysela) [2017320]
- ASoC: Intel: sof_sdw: Add support for SKU 0B29 product (Jaroslav Kysela) [2017320]
- ASoC: Intel: soc-acpi: add SKU 0B13 SoundWire configuration (Jaroslav Kysela) [2017320]
- ASoC: Intel: sof_sdw: Add support for SKU 0B13 product (Jaroslav Kysela) [2017320]
- ASoC: Intel: sof_sdw: Add support for SKU 0B11 product (Jaroslav Kysela) [2017320]
- ASoC: Intel: sof_sdw: Add support for SKU 0B00 and 0B01 products (Jaroslav Kysela) [2017320]
- ASoC: Intel: soc-acpi: add SKU 0AF3 SoundWire configuration (Jaroslav Kysela) [2017320]
- ASoC: Intel: sof_sdw: Add support for SKU 0AF3 product (Jaroslav Kysela) [2017320]
- ASoC: mediatek: mt8173-rt5650: Rename Speaker control to Ext Spk (Jaroslav Kysela) [2017320]
- mfd: arizona: Split of_match table into I2C and SPI versions (Jaroslav Kysela) [2017320]
- ASoC: DAPM: Cover regression by kctl change notification fix (Jaroslav Kysela) [2017320]
- ASoC: SOF: Intel: hda: fix hotplug when only codec is suspended (Jaroslav Kysela) [2017320]
- ALSA: timer: Unconditionally unlink slave instances, too (Jaroslav Kysela) [2017320]
- ALSA: memalloc: Catch call with NULL snd_dma_buffer pointer (Jaroslav Kysela) [2017320]
- Revert "ALSA: memalloc: Convert x86 SG-buffer handling with non-contiguous type" (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek: Add a quirk for Acer Spin SP513-54N (Jaroslav Kysela) [2017320]
- ALSA: firewire-motu: add support for MOTU Traveler mk3 (Jaroslav Kysela) [2017320]
- ASoC: SOF:control: Fix variable type in snd_sof_refresh_control() (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek: Headset fixup for Clevo NH77HJQ (Jaroslav Kysela) [2017320]
- ALSA: timer: Fix use-after-free problem (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Add quirk for Audient iD14 (Jaroslav Kysela) [2017320]
- ASoC: cs35l41: Change monitor widgets to siggens (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek: Add quirk for Clevo PC70HS (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Line6 HX-Stomp XL USB_ID for 48k-fixed quirk (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Add registration quirk for JBL Quantum 400 (Jaroslav Kysela) [2017320]
- ASoC: rsnd: Fix an error handling path in 'rsnd_node_count()' (Jaroslav Kysela) [2017320]
- ASoC: tlv320aic3x: Make aic3x_remove() return void (Jaroslav Kysela) [2017320]
- ASoC: Intel: soc-acpi: use const for all uses of snd_soc_acpi_codecs (Jaroslav Kysela) [2017320]
- ASoC: Intel: soc-acpi-cht: shrink tables using compatible IDs (Jaroslav Kysela) [2017320]
- ASoC: Intel: soc-acpi-byt: shrink tables using compatible IDs (Jaroslav Kysela) [2017320]
- ASoC: Intel: sof_rt5682: use comp_ids to enumerate rt5682s (Jaroslav Kysela) [2017320]
- ASoC: Intel: sof_rt5682: detect codec variant in probe function (Jaroslav Kysela) [2017320]
- ASoC: soc-acpi: add comp_ids field for machine driver matching (Jaroslav Kysela) [2017320]
- ASoC: mediatek: mt8195: add machine driver with mt6359, rt1011 and rt5682 (Jaroslav Kysela) [2017320]
- ASoC: Stop dummy from overriding hwparams (Jaroslav Kysela) [2017320]
- ASoC: topology: Change topology device to card device (Jaroslav Kysela) [2017320]
- ASoC: topology: Use correct device for prints (Jaroslav Kysela) [2017320]
- ASoC: topology: Check for dapm widget completeness (Jaroslav Kysela) [2017320]
- ASoC: topology: Add header payload_size verification (Jaroslav Kysela) [2017320]
- ASoC: core: Remove invalid snd_soc_component_set_jack call (Jaroslav Kysela) [2017320]
- ASoC: codecs: tfa989x: Add support for tfa9897 RCV bit (Jaroslav Kysela) [2017320]
- ASoC: amd: acp: select CONFIG_SND_SOC_ACPI (Jaroslav Kysela) [2017320]
- ASoC: Intel: glk_rt5682_max98357a: support ALC5682I-VS codec (Jaroslav Kysela) [2017320]
- ASoC: fix unmet dependencies on GPIOLIB for SND_SOC_RT1015P (Jaroslav Kysela) [2017320]
- ASoC: es8316: add support for ESSX8336 ACPI _HID (Jaroslav Kysela) [2017320]
- ASoC: cs42l42: Correct configuring of switch inversion from ts-inv (Jaroslav Kysela) [2017320]
- ALSA: firewire-motu: remove TODO for interaction with userspace about control message (Jaroslav Kysela) [2017320]
- ALSA: oxfw: fix functional regression for Mackie Onyx 1640i in v5.14 or later (Jaroslav Kysela) [2017320]
- ASoC: qdsp6: audioreach: Fix clang -Wimplicit-fallthrough (Jaroslav Kysela) [2017320]
- ASoC: fix unmet dependencies on GPIOLIB for SND_SOC_DMIC (Jaroslav Kysela) [2017320]
- ALSA: firewire-motu: export meter information to userspace as float value (Jaroslav Kysela) [2017320]
- ALSA: firewire-motu: refine parser for meter information in register DSP models (Jaroslav Kysela) [2017320]
- ALSA: firewire-motu: fix null pointer dereference when polling hwdep character device (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek: Add a quirk for HP OMEN 15 mute LED (Jaroslav Kysela) [2017320]
- ASoC: amd: acp: fix Kconfig dependencies (Jaroslav Kysela) [2017320]
- ASoC: rt5682-i2c: Use devm_clk_get_optional for optional clock (Jaroslav Kysela) [2017320]
- ASoC: Intel: soc-acpi: add entry for ESSX8336 on JSL (Jaroslav Kysela) [2017320]
- ASoC: amd: acp: Fix return value check in acp_machine_select() (Jaroslav Kysela) [2017320]
- ASoC: max98520: add max98520 audio amplifier driver (Jaroslav Kysela) [2017320]
- ASoC: mediatek: mt8195: fix return value (Jaroslav Kysela) [2017320]
- ASoC: mediatek: mt8195: rename shadowed array (Jaroslav Kysela) [2017320]
- ASoC: mediatek: remove unnecessary initialization (Jaroslav Kysela) [2017320]
- ASoC: nau8821: clarify out-of-bounds check (Jaroslav Kysela) [2017320]
- ASoC: nau8821: fix kernel-doc (Jaroslav Kysela) [2017320]
- ASoC: rt5682s: use 'static' qualifier (Jaroslav Kysela) [2017320]
- ASoC: topology: handle endianness warning (Jaroslav Kysela) [2017320]
- ALSA: ua101: fix division by zero at probe (Jaroslav Kysela) [2017320]
- ASoC: amd: acp: SND_SOC_AMD_ACP_COMMON should depend on X86 && PCI (Jaroslav Kysela) [2017320]
- ASoC: amd: acp: SND_SOC_AMD_{LEGACY_MACH,SOF_MACH} should depend on X86 && PCI && I2C (Jaroslav Kysela) [2017320]
- ASoC: amd: acp: Wrap AMD Audio ACP components in SND_SOC_AMD_ACP_COMMON (Jaroslav Kysela) [2017320]
- ASoC: cs42l42: free_irq() before powering-down on probe() fail (Jaroslav Kysela) [2017320]
- ASoC: cs42l42: Reset and power-down on remove() and failed probe() (Jaroslav Kysela) [2017320]
- ASoC: qdsp6: audioreach: add support for q6prm-clocks (Jaroslav Kysela) [2017320]
- ASoC: qdsp6: audioreach: add q6prm support (Jaroslav Kysela) [2017320]
- ASoC: qdsp6: audioreach: add q6apm lpass dai support (Jaroslav Kysela) [2017320]
- ASoC: qdsp6: audioreach: add q6apm-dai support (Jaroslav Kysela) [2017320]
- ASoC: qdsp6: audioreach: add topology support (Jaroslav Kysela) [2017320]
- ASoC: qdsp6: audioreach: add Kconfig and Makefile (Jaroslav Kysela) [2017320]
- ASoC: qdsp6: audioreach: add module configuration command helpers (Jaroslav Kysela) [2017320]
- ASoC: qdsp6: audioreach: add q6apm support (Jaroslav Kysela) [2017320]
- ASoC: qdsp6: audioreach: add basic pkt alloc support (Jaroslav Kysela) [2017320]
- ASoC: qdsp6: q6afe-clocks: move audio-clocks to common file (Jaroslav Kysela) [2017320]
- ASoC: qdsp6: q6afe-dai: move lpass audio ports to common file (Jaroslav Kysela) [2017320]
- ASoC: codecs: Change bulk clock voting to optional voting in digital codecs (Jaroslav Kysela) [2017320]
- ASoC: codecs: tx-macro: Update tx default values (Jaroslav Kysela) [2017320]
- ASoC: codecs: tx-macro: Enable tx top soundwire mic clock (Jaroslav Kysela) [2017320]
- ASoC: qcom: Add compatible names in va,wsa,rx,tx codec drivers for sc7280 (Jaroslav Kysela) [2017320]
- ASoC: nau8825: add clock management for power saving (Jaroslav Kysela) [2017320]
- ASoC: nau8825: add set_jack coponment support (Jaroslav Kysela) [2017320]
- ALSA: line6: fix control and interrupt message timeouts (Jaroslav Kysela) [2017320]
- ALSA: 6fire: fix control and bulk message timeouts (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: fix null pointer dereference on pointer cs_desc (Jaroslav Kysela) [2017320]
- ALSA: gus: fix null pointer dereference on pointer block (Jaroslav Kysela) [2017320]
- ALSA: mixer: fix deadlock in snd_mixer_oss_set_volume (Jaroslav Kysela) [2017320]
- ASoC: topology: Fix stub for snd_soc_tplg_component_remove() (Jaroslav Kysela) [2017320]
- ASoC: qcom: common: Respect status = "disabled" on DAI link nodes (Jaroslav Kysela) [2017320]
- ASoC: cs42l42: Prevent NULL pointer deref in interrupt handler (Jaroslav Kysela) [2017320]
- ASoC: wm8962: Convert to devm_clk_get_optional() (Jaroslav Kysela) [2017320]
- ASoC: fix unmet dependency on GPIOLIB for SND_SOC_MAX98357A (Jaroslav Kysela) [2017320]
- ASoC: cs35l41: Make cs35l41_remove() return void (Jaroslav Kysela) [2017320]
- ASoc: wm8900: Drop empty spi_driver remove callback (Jaroslav Kysela) [2017320]
- ASoC: tegra: Set default card name for Trimslice (Jaroslav Kysela) [2017320]
- ASoC: tegra: Restore AC97 support (Jaroslav Kysela) [2017320]
- ASoc: wm8731: Drop empty spi_driver remove callback (Jaroslav Kysela) [2017320]
- ASoC: doc: update codec example code (Jaroslav Kysela) [2017320]
- ASoC: amd: acp: Add acp_machine struct for renoir platform. (Jaroslav Kysela) [2017320]
- ASoC: rt5682s: Downsizing the DAC volume scale (Jaroslav Kysela) [2017320]
- ASoC: meson: axg-tdm-interface: manage formatters in trigger (Jaroslav Kysela) [2017320]
- ASoC: meson: axg-card: make links nonatomic (Jaroslav Kysela) [2017320]
- ASoC: cs42l42: Remove unused runtime_suspend/runtime_resume callbacks (Jaroslav Kysela) [2017320]
- ASoC: fix unmet dependency on GPIOLIB (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek: Fix mic mute LED for the HP Spectre x360 14 (Jaroslav Kysela) [2017320]
- ALSA: mixer: oss: Fix racy access to slots (Jaroslav Kysela) [2017320]
- ASoC: cirrus: i2s: Prepare clock before using it (Jaroslav Kysela) [2017320]
- soundwire: qcom: add debugfs entry for soundwire register dump (Jaroslav Kysela) [2017320]
- soundwire: bus: stop dereferencing invalid slave pointer (Jaroslav Kysela) [2017320]
- ASoC: amd: acp: Add support for RT5682-VS codec (Jaroslav Kysela) [2017320]
- ASoC: amd: acp: Add support for Maxim amplifier codec (Jaroslav Kysela) [2017320]
- ASoC: amd: acp: Add callback for machine driver on ACP (Jaroslav Kysela) [2017320]
- ASoC: rockchip: Use generic dmaengine code (Jaroslav Kysela) [2017320]
- ASoC: rockchip: i2s_tdm: Dup static DAI template (Jaroslav Kysela) [2017320]
- ASoC: rockchip: i2s_tdm: improve return value handling (Jaroslav Kysela) [2017320]
- ASoC: Intel: Move soc_intel_is_foo() helpers to a generic header (Jaroslav Kysela) [2017320]
- ALSA: memalloc: Fix a typo in snd_dma_buffer_sync() description (Jaroslav Kysela) [2017320]
- ALSA: memalloc: Drop superfluous snd_dma_buffer_sync() declaration (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Fix microphone sound on Jieli webcam. (Jaroslav Kysela) [2017320]
- ASoC: qcom: sm8250: Add Jack support (Jaroslav Kysela) [2017320]
- ASoC: qcom: sm8250: add support for TX and RX Macro dais (Jaroslav Kysela) [2017320]
- ASoC: amd: enable Yellow Carp platform machine driver build (Jaroslav Kysela) [2017320]
- ASoC: amd: add YC machine driver using dmic (Jaroslav Kysela) [2017320]
- ASoC: amd: create platform device for acp6x machine driver (Jaroslav Kysela) [2017320]
- ASoC: amd: enable Yellow carp acp6x drivers build (Jaroslav Kysela) [2017320]
- ASoC: amd: add acp6x pdm driver pm ops (Jaroslav Kysela) [2017320]
- ASoC: amd: add acp6x pci driver pm ops (Jaroslav Kysela) [2017320]
- ASoC: amd: add acp6x pdm driver dma ops (Jaroslav Kysela) [2017320]
- ASoC: amd: add acp6x irq handler (Jaroslav Kysela) [2017320]
- ASoC: amd: add acp6x pdm platform driver (Jaroslav Kysela) [2017320]
- ASoC: amd: add platform devices for acp6x pdm driver and dmic driver (Jaroslav Kysela) [2017320]
- ASoC: amd: add acp6x init/de-init functions (Jaroslav Kysela) [2017320]
- ASoC: amd: add Yellow Carp ACP PCI driver (Jaroslav Kysela) [2017320]
- ASoC: amd: add Yellow Carp ACP6x IP register header (Jaroslav Kysela) [2017320]
- ASoC: amd: acp: Add SOF audio support on Chrome board (Jaroslav Kysela) [2017320]
- ASoC: amd: acp: Add legacy sound card support for Chrome audio (Jaroslav Kysela) [2017320]
- ASoC: amd: acp: Add generic machine driver support for ACP cards (Jaroslav Kysela) [2017320]
- ASoC: amd: acp: Add I2S support on Renoir platform (Jaroslav Kysela) [2017320]
- ASoC: amd: Add common framework to support I2S on ACP SOC (Jaroslav Kysela) [2017320]
- ALSA: uapi: Fix a C++ style comment in asound.h (Jaroslav Kysela) [2017320]
- ALSA: firewire: Fix C++ style comments in uapi header (Jaroslav Kysela) [2017320]
- ASoC: rockchip: i2s-tdm: Fix refcount test (Jaroslav Kysela) [2017320]
- ASoC: meson: implement driver_name for snd_soc_card in meson-card-utils (Jaroslav Kysela) [2017320]
- ASoC: tlv320aic32x4: Make aic32x4_remove() return void (Jaroslav Kysela) [2017320]
- ASoC: soc-core: accept zero format at snd_soc_runtime_set_dai_fmt() (Jaroslav Kysela) [2017320]
- ASoC: soc-core: tidyup empty function (Jaroslav Kysela) [2017320]
- ASoC: soc-component: add snd_soc_component_is_codec() (Jaroslav Kysela) [2017320]
- ASoC: soc-pcm: tidyup soc_pcm_hw_clean() - step2 (Jaroslav Kysela) [2017320]
- ASoC: soc-pcm: tidyup soc_pcm_hw_clean() - step1 (Jaroslav Kysela) [2017320]
- ALSA: memalloc: Convert x86 SG-buffer handling with non-contiguous type (Jaroslav Kysela) [2017320]
- ALSA: memalloc: Support for non-coherent page allocation (Jaroslav Kysela) [2017320]
- ALSA: memalloc: Support for non-contiguous page allocation (Jaroslav Kysela) [2017320]
- ALSA: ISA: not for M68K (Jaroslav Kysela) [2017320]
- ASoC: rockchip: i2s-tdm: Strip out direct CRU use (Jaroslav Kysela) [2017320]
- ALSA: firewire-motu: notify event for parameter change in register DSP model (Jaroslav Kysela) [2017320]
- ALSA: firewire-motu: queue event for parameter change in register DSP model (Jaroslav Kysela) [2017320]
- ALSA: firewire-motu: add ioctl command to read cached parameters in register DSP model (Jaroslav Kysela) [2017320]
- ALSA: firewire-motu: parse messages for input parameters in register DSP model (Jaroslav Kysela) [2017320]
- ALSA: firewire-motu: parse messages for line input parameters in register DSP model (Jaroslav Kysela) [2017320]
- ALSA: firewire-motu: parse messages for output parameters in register DSP model (Jaroslav Kysela) [2017320]
- ALSA: firewire-motu: parse messages for mixer output parameters in register DSP model (Jaroslav Kysela) [2017320]
- ALSA: firewire-motu: parse messages for mixer source parameters in register-DSP model (Jaroslav Kysela) [2017320]
- ALSA: firewire-motu: add ioctl command to read cached hardware meter (Jaroslav Kysela) [2017320]
- ALSA: firewire-motu: add message parser for meter information in command DSP model (Jaroslav Kysela) [2017320]
- ALSA: firewire-motu: add message parser to gather meter information in register DSP model (Jaroslav Kysela) [2017320]
- ASoC: cs42l42: Always enable TS_PLUG and TS_UNPLUG interrupts (Jaroslav Kysela) [2017320]
- ASoC: cs42l42: Fix WARN in remove() if running without an interrupt (Jaroslav Kysela) [2017320]
- ASoC: cs42l42: Mark OSC_SWITCH_STATUS register volatile (Jaroslav Kysela) [2017320]
- ASoC: cs42l42: Set correct SRC MCLK (Jaroslav Kysela) [2017320]
- ASoC: cs42l42: Allow time for HP/ADC to power-up after enable (Jaroslav Kysela) [2017320]
- ASoC: cs42l42: Use PLL for SCLK > 12.288MHz (Jaroslav Kysela) [2017320]
- ASoC: cs42l42: Don't claim to support 192k (Jaroslav Kysela) [2017320]
- ASoC: cs42l42: Defer probe if request_threaded_irq() returns EPROBE_DEFER (Jaroslav Kysela) [2017320]
- ASoC: cs42l42: Don't set defaults for volatile registers (Jaroslav Kysela) [2017320]
- ASoC: cs42l42: Correct some register default values (Jaroslav Kysela) [2017320]
- ASoC: cs42l42: Always configure both ASP TX channels (Jaroslav Kysela) [2017320]
- ASoC: cs42l42: Don't reconfigure the PLL while it is running (Jaroslav Kysela) [2017320]
- ASoC: soc-component: improve error reporting for register access (Jaroslav Kysela) [2017320]
- ASoC: amd: enable vangogh platform machine driver build (Jaroslav Kysela) [2017320]
- ASoC: amd: add vangogh machine driver (Jaroslav Kysela) [2017320]
- ASoc: amd: create platform device for VG machine driver (Jaroslav Kysela) [2017320]
- ASoC: audio-graph-card2-custom-sample.dtsi: add Codec2Codec sample (Multi) (Jaroslav Kysela) [2017320]
- ASoC: audio-graph-card2-custom-sample.dtsi: add Codec2Codec sample (Single) (Jaroslav Kysela) [2017320]
- ASoC: audio-graph-card2-custom-sample.dtsi: add DPCM sample (Multi) (Jaroslav Kysela) [2017320]
- ASoC: audio-graph-card2-custom-sample.dtsi: add DPCM sample (Single) (Jaroslav Kysela) [2017320]
- ASoC: audio-graph-card2-custom-sample.dtsi: add Sample DT for Normal (Nulti) (Jaroslav Kysela) [2017320]
- ASoC: audio-graph-card2-custom-sample.dtsi: add Sample DT for Normal (Single) (Jaroslav Kysela) [2017320]
- ASoC: add Audio Graph Card2 Custom Sample (Jaroslav Kysela) [2017320]
- ASoC: audio-graph-card2: add Codec2Codec support (Jaroslav Kysela) [2017320]
- ASoC: audio-graph-card2: add DPCM support (Jaroslav Kysela) [2017320]
- ASoC: audio-graph-card2: add Multi CPU/Codec support (Jaroslav Kysela) [2017320]
- ASoC: add Audio Graph Card2 driver (Jaroslav Kysela) [2017320]
- ASoC: simple-card-utils: add codec2codec support (Jaroslav Kysela) [2017320]
- ASoC: simple-card-utils: add asoc_graph_is_ports0() (Jaroslav Kysela) [2017320]
- ASoC: test-component: add Test Component for Sound debug/test (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek: Fixes HP Spectre x360 15-eb1xxx speakers (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Provide quirk for Sennheiser GSP670 Headset (Jaroslav Kysela) [2017320]
- ALSA: pcm: Unify snd_pcm_delay() and snd_pcm_hwsync() (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Initialize every feature unit once at probe time (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Drop superfluous error message after disconnection (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Downgrade error message in get_ctl_value_v2() (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek: Add quirk for Clevo PC50HS (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: add Schiit Hel device to quirk table (Jaroslav Kysela) [2017320]
- ASoC: rt5682: fix a little pop while playback (Jaroslav Kysela) [2017320]
- ASoC: rt1011: Fix 'I2S Reference' enum control (Jaroslav Kysela) [2017320]
- ASoC: wm8960: Fix clock configuration on slave mode (Jaroslav Kysela) [2017320]
- ASoC: rt9120: Add rt9210 audio amplifier support (Jaroslav Kysela) [2017320]
- ASoC: amd: vangogh: constify static struct snd_soc_dai_ops (Jaroslav Kysela) [2017320]
- ASoC: mediatek: Constify static snd_soc_ops (Jaroslav Kysela) [2017320]
- ASoC: rt9120: Drop rt9210 audio amplifier support (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Add quirk for VF0770 (Jaroslav Kysela) [2017320]
- ALSA: hda: avoid write to STATESTS if controller is in reset (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Less restriction for low-latency playback mode (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek: Fix the mic type detection issue for ASUS G551JW (Jaroslav Kysela) [2017320]
- ASoC: rt1011: Fix 'I2S Reference' enum control caused error (Jaroslav Kysela) [2017320]
- ASoC: cs42l42: Ensure 0dB full scale volume is used for headsets (Jaroslav Kysela) [2017320]
- ALSA: pcm: Workaround for a wrong offset in SYNC_PTR compat ioctl (Jaroslav Kysela) [2017320]
- ASoC: Intel: bytcr_rt5651: Utilize dev_err_probe() to avoid log saturation (Jaroslav Kysela) [2017320]
- ASoC: Intel: bytcr_rt5651: use devm_clk_get_optional() for mclk (Jaroslav Kysela) [2017320]
- ASoC: Intel: bytcr_rt5651: Use temporary variable for struct device (Jaroslav Kysela) [2017320]
- ASoC: Intel: bytcr_rt5651: Get platform data via dev_get_platdata() (Jaroslav Kysela) [2017320]
- ASoC: Intel: bytcr_rt5640: Utilize dev_err_probe() to avoid log saturation (Jaroslav Kysela) [2017320]
- ASoC: Intel: bytcr_rt5640: use devm_clk_get_optional() for mclk (Jaroslav Kysela) [2017320]
- ASoC: Intel: bytcr_rt5640: Use temporary variable for struct device (Jaroslav Kysela) [2017320]
- ASoC: Intel: bytcr_rt5640: Get platform data via dev_get_platdata() (Jaroslav Kysela) [2017320]
- ASoC: amd: Kconfig: Select fch clock support with machine driver (Jaroslav Kysela) [2017320]
- ASoC: soc-core: fix null-ptr-deref in snd_soc_del_component_unlocked() (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek: Fix for quirk to enable speaker output on the Lenovo 13s Gen2 (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Add support for the Pioneer DJM 750MK2 Mixer/Soundcard (Jaroslav Kysela) [2017320]
- ASoC: rockchip: i2s-tdm: Fix error handling on i2s_tdm_prepare_enable_mclk failure (Jaroslav Kysela) [2017320]
- ASoC: rockchip: i2s-tdm: Remove call to rockchip_i2s_ch_to_io (Jaroslav Kysela) [2017320]
- ASoC: mediatek: mt8195: update audsys clock parent name (Jaroslav Kysela) [2017320]
- ASoC: SOF: prepare code to allocate IPC messages in fw_ready (Jaroslav Kysela) [2017320]
- ASoC: rt9120: Add rt9210 audio amplifier support (Jaroslav Kysela) [2017320]
- ASoC: soc-pcm: restore mixer functionality (Jaroslav Kysela) [2017320]
- ASoC: rt5682s: Fix hp pop produced immediately after resuming (Jaroslav Kysela) [2017320]
- ASoC: rockchip: add support for i2s-tdm controller (Jaroslav Kysela) [2017320]
- ASoC: SOF: Introduce fragment elapsed notification API (Jaroslav Kysela) [2017320]
- ASoC: SOF: imx: Use newly introduced generic IPC stream ops (Jaroslav Kysela) [2017320]
- ASoC: SOF: Make Intel IPC stream ops generic (Jaroslav Kysela) [2017320]
- ASoC: SOF: Introduce snd_sof_mailbox_read / snd_sof_mailbox_write callbacks (Jaroslav Kysela) [2017320]
- ASoC: SOF: pipelines: Harmonize all functions to use struct snd_sof_dev (Jaroslav Kysela) [2017320]
- ASoC: SOF: topology: do not power down primary core during topology removal (Jaroslav Kysela) [2017320]
- ASoC: SOF: Intel: hda: Dump registers and stack when SOF_DBG_DUMP_REGS is set (Jaroslav Kysela) [2017320]
- ASoC: SOF: Intel: hda-loader: Drop SOF_DBG_DUMP_REGS flag from dbg_dump calls (Jaroslav Kysela) [2017320]
- ASoC: SOF: loader: Drop SOF_DBG_DUMP_REGS flag when firmware start fails (Jaroslav Kysela) [2017320]
- ASoC: SOF: core: Clean up snd_sof_get_status() prints (Jaroslav Kysela) [2017320]
- ASoC: SOF: intel: hda: Drop 'error' prefix from error dump functions (Jaroslav Kysela) [2017320]
- ASoC: SOF: Introduce macro to set the firmware state (Jaroslav Kysela) [2017320]
- ASoC: SOF: ops: Force DSP panic dumps to be printed (Jaroslav Kysela) [2017320]
- ASoC: SOF: ipc: Re-enable dumps after successful IPC tx (Jaroslav Kysela) [2017320]
- ASoC: SOF: debug: Print out the fw_state along with the DSP dump (Jaroslav Kysela) [2017320]
- ASoC: SOF: Drop SOF_DBG_DUMP_FORCE_ERR_LEVEL and sof_dev_dbg_or_err (Jaroslav Kysela) [2017320]
- ASoC: SOF: intel: hda-loader: Use snd_sof_dsp_dbg_dump() for DSP dump (Jaroslav Kysela) [2017320]
- ASoC: SOF: debug: Add SOF_DBG_DUMP_OPTIONAL flag for DSP dumping (Jaroslav Kysela) [2017320]
- ASoC: SOF: debug/ops: Move the IPC and DSP dump functions out from the header (Jaroslav Kysela) [2017320]
- ASoC: SOF: intel: atom: No need to do a DSP dump in atom_run() (Jaroslav Kysela) [2017320]
- ASoC: SOF: loader: Print the DSP dump if boot fails (Jaroslav Kysela) [2017320]
- ASoC: SOF: Print the dbg_dump and ipc_dump once to reduce kernel log noise (Jaroslav Kysela) [2017320]
- ASoC: SOF: ipc and dsp dump: Add markers for better visibility (Jaroslav Kysela) [2017320]
- ASoC: SOF: debug: Swap the dsp_dump and ipc_dump sequence for fw_exception (Jaroslav Kysela) [2017320]
- ASoC: SOF: core: debug: force all processing on primary core (Jaroslav Kysela) [2017320]
- ASoC: max98927: Handle reset gpio when probing i2c (Jaroslav Kysela) [2017320]
- ASoC: codec: wcd938x: Add irq config support (Jaroslav Kysela) [2017320]
- ASoC: DAPM: Fix missing kctl change notifications (Jaroslav Kysela) [2017320]
- ASoC: Intel: bytcht_es8316: Utilize dev_err_probe() to avoid log saturation (Jaroslav Kysela) [2017320]
- ASoC: Intel: bytcht_es8316: Switch to use gpiod_get_optional() (Jaroslav Kysela) [2017320]
- ASoC: Intel: bytcht_es8316: Use temporary variable for struct device (Jaroslav Kysela) [2017320]
- ASoC: Intel: bytcht_es8316: Get platform data via dev_get_platdata() (Jaroslav Kysela) [2017320]
- ASoC: wcd938x: Fix jack detection issue (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Pass JOINT_DUPLEX info flag for implicit fb streams (Jaroslav Kysela) [2017320]
- ALSA: pcm: Add more disconnection checks at file ops (Jaroslav Kysela) [2017320]
- ALSA: hda: intel: Allow repeatedly probing on codec configuration errors (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek: Add quirk for TongFang PHxTxX1 (Jaroslav Kysela) [2017320]
- ASoC: SOF: OF: Add fw_path and tplg_path parameters (Jaroslav Kysela) [2017320]
- ASoC: amd: acp-rt5645: Constify static snd_soc_ops (Jaroslav Kysela) [2017320]
- ASoC: SOF: topology: return error if sof_connect_dai_widget() fails (Jaroslav Kysela) [2017320]
- ASoC: SOF: topology: allow for dynamic pipelines override for debug (Jaroslav Kysela) [2017320]
- ASoC: SOF: topology: show clks_control value in dynamic debug (Jaroslav Kysela) [2017320]
- ASoC: SOF: Intel: hda-dai: improve SSP DAI handling for dynamic pipelines (Jaroslav Kysela) [2017320]
- ASoC: SOF: dai-intel: add SOF_DAI_INTEL_SSP_CLKCTRL_MCLK/BCLK_ES bits (Jaroslav Kysela) [2017320]
- ASoC: SOF: Intel: hda: add new flags for DAI_CONFIG (Jaroslav Kysela) [2017320]
- ASoC: SOF: dai: include new flags for DAI_CONFIG (Jaroslav Kysela) [2017320]
- ASoC: SOF: dai: mirror group_id definition added in firmware (Jaroslav Kysela) [2017320]
- ASoC: Intel: sof_sdw: add missing quirk for Dell SKU 0A45 (Jaroslav Kysela) [2017320]
- ASoC: Intel: soc-acpi: add missing quirk for TGL SDCA single amp (Jaroslav Kysela) [2017320]
- ASoC: Intel: add machine driver for SOF+ES8336 (Jaroslav Kysela) [2017320]
- ALSA: intel-dsp-config: add quirk for APL/GLK/TGL devices based on ES8336 codec (Jaroslav Kysela) [2017320]
- ASoC: Intel: soc-acpi: apl/glk/tgl: add entry for devices based on ES8336 codec (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek - ALC236 headset MIC recording issue (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Enable rate validation for Scarlett devices (Jaroslav Kysela) [2017320]
- ASoC: Intel: cht_bsw_nau8824: Set card.components string (Jaroslav Kysela) [2017320]
- ASoC: nau8824: Add a nau8824_components() helper (Jaroslav Kysela) [2017320]
- ASoC: nau8824: Add DMI quirk mechanism for active-high jack-detect (Jaroslav Kysela) [2017320]
- ASoC: nau8824: Fix NAU8824_JACK_LOGIC define (Jaroslav Kysela) [2017320]
- ASoC: rt5651: Use IRQF_NO_AUTOEN when requesting the IRQ (Jaroslav Kysela) [2017320]
- ASoC: es8316: Use IRQF_NO_AUTOEN when requesting the IRQ (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek: Add quirk for Clevo X170KM-G (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek: Complete partial device name to avoid ambiguity (Jaroslav Kysela) [2017320]
- ASoC: nau8821: new driver (Jaroslav Kysela) [2017320]
- ASoC: fsl_spdif: implement bypass mode from in to out (Jaroslav Kysela) [2017320]
- ASoC: SOF: topology: Add kernel parameter for topology verification (Jaroslav Kysela) [2017320]
- ASoC: SOF: Add support for dynamic pipelines (Jaroslav Kysela) [2017320]
- ASoC: SOF: Intel: hda: make sure DAI widget is set up before IPC (Jaroslav Kysela) [2017320]
- ASoC: SOF: Introduce widget use_count (Jaroslav Kysela) [2017320]
- ASoC: SOF: Don't set up widgets during topology parsing (Jaroslav Kysela) [2017320]
- ASoC: SOF: restore kcontrols for widget during set up (Jaroslav Kysela) [2017320]
- ASoC: SOF: Add new fields to snd_sof_route (Jaroslav Kysela) [2017320]
- AsoC: dapm: export a couple of functions (Jaroslav Kysela) [2017320]
- ASoC: SOF: sof-audio: add helpers for widgets, kcontrols and dai config set up (Jaroslav Kysela) [2017320]
- ASoC: SOF: topology: Add new token for dynamic pipeline (Jaroslav Kysela) [2017320]
- ASoC: SOF: control: Add access field in struct snd_sof_control (Jaroslav Kysela) [2017320]
- ASoC: topology: change the complete op in snd_soc_tplg_ops to return int (Jaroslav Kysela) [2017320]
- ASoC: qcom: apq8096: Constify static snd_soc_ops (Jaroslav Kysela) [2017320]
- ASoC: rt5682s: Fix HP noise caused by SAR mode switch when the system resumes (Jaroslav Kysela) [2017320]
- ASoC: rt5682s: Enable ASRC auto-disable to fix pop during jack plug-in while playback (Jaroslav Kysela) [2017320]
- ASoC: mediatek: mt8195: move of_node_put to remove function (Jaroslav Kysela) [2017320]
- ASoC: Intel: sof_rt5682: Add support for max98360a speaker amp (Jaroslav Kysela) [2017320]
- ASoC: tegra: Constify static snd_soc_ops (Jaroslav Kysela) [2017320]
- ASoC: soc-component: Remove conditional definition of debugfs data members (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Fix packet size calculation regression (Jaroslav Kysela) [2017320]
- ALSA: hda - Enable headphone mic on Dell Latitude laptops with ALC3254 (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: disable implicit feedback sync for Behringer UFX1204 and UFX1604 (Jaroslav Kysela) [2017320]
- soundwire: debugfs: use controller id and link_id for debugfs (Jaroslav Kysela) [2017320]
- ASoC: rt5682: move clk related code to rt5682_i2c_probe (Jaroslav Kysela) [2017320]
- ASoC: fsl_rpmsg: Add rpmsg audio support for i.MX8ULP (Jaroslav Kysela) [2017320]
- ASoC: wm_adsp: remove a repeated including (Jaroslav Kysela) [2017320]
- ASoC: SOF: Change SND_SOC_SOF_TOPLEVEL from config to menuconfig (Jaroslav Kysela) [2017320]
- ASoC: rt5682s: Revise the macro RT5682S_PLLB_SRC_MASK (Jaroslav Kysela) [2017320]
- ASoC: rt5682s: Use dev_dbg instead of pr_debug (Jaroslav Kysela) [2017320]
- ASoC: rt5682s: Remove the volatile SW reset register from reg_default (Jaroslav Kysela) [2017320]
- ASoC: nau8824: Fix headphone vs headset, button-press detection no longer working (Jaroslav Kysela) [2017320]
- ALSA: seq: Fix a potential UAF by wrong private_free call order (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Avoid killing in-flight URBs during draining (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Improved lowlatency playback support (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Add spinlock to stop_urbs() (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Check available frames for the next packet size (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Disable low-latency mode for implicit feedback sync (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Disable low-latency playback for free-wheel mode (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Rename early_playback_start flag with lowlatency_playback (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Fix possible race at sync of urb completions (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Restrict rates for the shared clocks (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek: Enable 4-speaker output for Dell Precision 5560 laptop (Jaroslav Kysela) [2017320]
- ALSA: hda: Use position buffer for SKL+ again (Jaroslav Kysela) [2017320]
- ALSA: hda: Reduce udelay() at SKL+ position reporting (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Fix a missing error check in scarlett gen2 mixer (Jaroslav Kysela) [2017320]
- ALSA: virtio: Replace zero-length array with flexible-array member (Jaroslav Kysela) [2017320]
- ASoC: ux500: mop500: Constify static snd_soc_ops (Jaroslav Kysela) [2017320]
- ASoC: ti: Constify static snd_soc_ops (Jaroslav Kysela) [2017320]
- ASoC: intel: sof_rt5682: update platform device name for Maxim amplifier (Jaroslav Kysela) [2017320]
- ASoC: SOF: ipc: Make the error prints consistent in tx_wait_done() (Jaroslav Kysela) [2017320]
- ASoC: SOF: prefix some terse and cryptic dev_dbg() with __func__ (Jaroslav Kysela) [2017320]
- ASoC: SOF: add error handling to snd_sof_ipc_msg_data() (Jaroslav Kysela) [2017320]
- ASoC: mediatek: mt8195: add missing of_node_put in probe (Jaroslav Kysela) [2017320]
- ASoC: SOF: imx: add header file for ops (Jaroslav Kysela) [2017320]
- ASoC: SOF: pm: fix a stale comment (Jaroslav Kysela) [2017320]
- ASoC: SOF: Intel: hda-stream: Print stream name on STREAM_SD_OFFSET timeout (Jaroslav Kysela) [2017320]
- ALSA: pcsp: Make hrtimer forwarding more robust (Jaroslav Kysela) [2017320]
- ASoC: SOF: Intel: hda-dai: fix potential locking issue (Jaroslav Kysela) [2017320]
- ALSA: hda: hdac_ext_stream: fix potential locking issues (Jaroslav Kysela) [2017320]
- ALSA: hda: hdac_stream: fix potential locking issue in snd_hdac_stream_assign() (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: fix comment reference in __uac_clock_find_source (Jaroslav Kysela) [2017320]
- ASoC: ak4458: Use modern ASoC DAI format terminology (Jaroslav Kysela) [2017320]
- ASoC: ak5558: Use modern ASoC DAI format terminology (Jaroslav Kysela) [2017320]
- ASoC: dmaengine: Introduce module option prealloc_buffer_size_kbytes (Jaroslav Kysela) [2017320]
- ASoC: dwc-i2s: Update to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: ak4671: Use modern ASoC DAI format terminology (Jaroslav Kysela) [2017320]
- ASoC: alc5623: Use modern ASoC DAI format terminology (Jaroslav Kysela) [2017320]
- ASoC: bcm: Convert to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: cpcap: Use modern ASoC DAI format terminology (Jaroslav Kysela) [2017320]
- ASoC: meson: aiu: Fix spelling mistake "Unsupport" -> "Unsupported" (Jaroslav Kysela) [2017320]
- ASoC: codecs: Fix spelling mistake "Unsupport" -> "Unsupported" (Jaroslav Kysela) [2017320]
- ASoC: ad193x: Update to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: tegra: Constify static snd_soc_dai_ops structs (Jaroslav Kysela) [2017320]
- ASoC: cs42l42: Use two thresholds and increased wait time for manual type detection (Jaroslav Kysela) [2017320]
- ASoC: adav80x: Update to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: adau1977: Update to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: adau17x1: Update to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: adau1701: Update to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: adau1373: Update to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: adau1372: Update to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: ad1836: Update to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: ep93xx: Convert to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: samsung: add missing "fallthrough;" (Jaroslav Kysela) [2017320]
- ASoC: ak4642: Use modern ASoC DAI format terminology (Jaroslav Kysela) [2017320]
- ASoC: wcd9335: Use correct version to initialize Class H (Jaroslav Kysela) [2017320]
- ASoC: alc5632: Use modern ASoC DAI format terminology (Jaroslav Kysela) [2017320]
- ASoC: ak4104: Update to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: ak4118: Update to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: zl38060: Update to modern clocking terminology (Jaroslav Kysela) [2017320]
- firmware: cs_dsp: add driver to support firmware loading on Cirrus Logic DSPs (Jaroslav Kysela) [2017320]
- ASoC: wm_adsp: Separate wm_adsp specifics in cs_dsp_client_ops (Jaroslav Kysela) [2017320]
- ASoC: wm_adsp: Split out struct cs_dsp from struct wm_adsp (Jaroslav Kysela) [2017320]
- ASoC: wm_adsp: move firmware loading to client (Jaroslav Kysela) [2017320]
- ASoC: wm_adsp: Pass firmware names as parameters when starting DSP core (Jaroslav Kysela) [2017320]
- ASoC: wm_adsp: Move check of dsp->running to better place (Jaroslav Kysela) [2017320]
- ASoC: wm_adsp: Separate generic cs_dsp_coeff_ctl handling (Jaroslav Kysela) [2017320]
- ASoC: wm_adsp: Move sys_config_size to wm_adsp (Jaroslav Kysela) [2017320]
- ASoC: wm_adsp: Split DSP power operations into helper functions (Jaroslav Kysela) [2017320]
- ASoC: wm_adsp: Separate some ASoC and generic functions (Jaroslav Kysela) [2017320]
- ASoC: wm_adsp: Introduce cs_dsp logging macros (Jaroslav Kysela) [2017320]
- ASoC: wm_adsp: Rename generic DSP support (Jaroslav Kysela) [2017320]
- ASoC: wm_adsp: Cancel ongoing work when removing controls (Jaroslav Kysela) [2017320]
- ASoC: wm_adsp: Switch to using wm_coeff_read_ctrl for compressed buffers (Jaroslav Kysela) [2017320]
- ASoC: wm_adsp: Move check for control existence (Jaroslav Kysela) [2017320]
- ASoC: wm_adsp: Remove use of snd_ctl_elem_type_t (Jaroslav Kysela) [2017320]
- ASoC: cs4341: Add SPI device ID table (Jaroslav Kysela) [2017320]
- ASoC: pcm179x: Add missing entries SPI to device ID table (Jaroslav Kysela) [2017320]
- ALSA: rawmidi: introduce SNDRV_RAWMIDI_IOCTL_USER_PVERSION (Jaroslav Kysela) [2017320]
- ASoC: pl1022_rdk: Update to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: pl1022_ds: Update to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: mpc8610_hpcd: Update to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: imx-sgtl5000: Update to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: imx-rpmsg: Update to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: imx-hdmi: Update to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: imx-es8328: Update to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: imx-card: Update to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: imx-audmix: Update to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: fsl_ssi: Update to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: fsl_sai: Update to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: fsl-mqs: Update to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: fsl-esai: Update to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: fsl-audmix: Update to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: fsl-asoc-card: Update to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: eureka-tlv320: Update to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: cros_ec_codec: Use modern ASoC DAI format terminology (Jaroslav Kysela) [2017320]
- ALSA: firewire-motu: fix truncated bytes in message tracepoints (Jaroslav Kysela) [2017320]
- ALSA: usx2y: Prefer struct_size over open coded arithmetic (Jaroslav Kysela) [2017320]
- ASoC: qdsp6: q6afe-dai: Fix spelling mistake "Fronend" -> "Frontend" (Jaroslav Kysela) [2017320]
- ASoC: fsl_spdif: Add support for i.MX8ULP (Jaroslav Kysela) [2017320]
- ASoC: fsl: Constify static snd_soc_ops (Jaroslav Kysela) [2017320]
- ASoC: fsl_xcvr: Fix channel swap issue with ARC (Jaroslav Kysela) [2017320]
- ASoC: pcm512x: Mend accesses to the I2S_1 and I2S_2 registers (Jaroslav Kysela) [2017320]
- ASoC: codecs: max98390: simplify getting the adapter of a client (Jaroslav Kysela) [2017320]
- ASoC: Intel: boards: Update to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: ab8500: Update to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: SOF: Remove struct sof_ops_table and sof_get_ops() macro (Jaroslav Kysela) [2017320]
- ASoC: rt5682s: make rt5682s_aif2_dai_ops and rt5682s_soc_component_dev (Jaroslav Kysela) [2017320]
- ASoC: tegra: Add Tegra210 based Mixer driver (Jaroslav Kysela) [2017320]
- ASoC: tegra: Add Tegra210 based ADX driver (Jaroslav Kysela) [2017320]
- ASoC: tegra: Add Tegra210 based AMX driver (Jaroslav Kysela) [2017320]
- ASoC: tegra: Add Tegra210 based SFC driver (Jaroslav Kysela) [2017320]
- ASoC: tegra: Add Tegra210 based MVC driver (Jaroslav Kysela) [2017320]
- ASoC: tegra: Add routes for few AHUB modules (Jaroslav Kysela) [2017320]
- ASoC: audio-graph: Fixup CPU endpoint hw_params in a BE<->BE link (Jaroslav Kysela) [2017320]
- ASoC: simple-card-utils: Increase maximum DAI links limit to 512 (Jaroslav Kysela) [2017320]
- ASoC: soc-pcm: Don't reconnect an already active BE (Jaroslav Kysela) [2017320]
- ASoC: compress/component: Use module_get_when_open/put_when_close for cstream (Jaroslav Kysela) [2017320]
- ASoC: soc-component: Convert the mark_module to void* (Jaroslav Kysela) [2017320]
- ASoC: 88pm860x: Update to modern clocking terminology (Jaroslav Kysela) [2017320]
- ASoC: SOF: Rename sof_arch_ops to dsp_arch_ops (Jaroslav Kysela) [2017320]
- ASoC: SOF: ipc: Remove redundant error check from sof_ipc_tx_message_unlocked (Jaroslav Kysela) [2017320]
- ASoC: SOF: ipc: Print 0x prefix for errors in ipc_trace/stream_message() (Jaroslav Kysela) [2017320]
- ASoC: SOF: ipc: Clarify the parameter name for ipc_trace_message() (Jaroslav Kysela) [2017320]
- ASoC: SOF: trace: Omit error print when waking up trace sleepers (Jaroslav Kysela) [2017320]
- ASoC: mediatek: mt8195: remove wrong fixup assignment on HDMITX (Jaroslav Kysela) [2017320]
- ASoC: au1x: Convert to modern terminology for DAI clocking (Jaroslav Kysela) [2017320]
- ASoC: atmel: Convert to new style DAI format definitions (Jaroslav Kysela) [2017320]
- misc: cs35l41: Remove unused pdn variable (Jaroslav Kysela) [2017320]
- ASoC: SOF: imx8m: add SAI1 info (Jaroslav Kysela) [2017320]
- ASoC: cs42l42: Minor fix all errors reported by checkpatch.pl script (Jaroslav Kysela) [2017320]
- ASoC: SOF: core: Move probe work related code under a single if () branch (Jaroslav Kysela) [2017320]
- ASoC: cs42l42: Implement Manual Type detection as fallback (Jaroslav Kysela) [2017320]
- ASoC: SOF: sof-probes: Correct the function names used for snd_soc_cdai_ops (Jaroslav Kysela) [2017320]
- ASoC: SOF: Intel: Rename hda-compress.c to hda-probes.c (Jaroslav Kysela) [2017320]
- ASoC: SOF: probe: Merge and clean up the probe and compress files (Jaroslav Kysela) [2017320]
- ASoC: SOF: compress: move and export sof_probe_compr_ops (Jaroslav Kysela) [2017320]
- ASoC: SOF: pcm: Remove non existent CONFIG_SND_SOC_SOF_COMPRESS reference (Jaroslav Kysela) [2017320]
- ASoC: SOF: ipc: Add probe message logging to ipc_log_header() (Jaroslav Kysela) [2017320]
- ASoC: SOF: loader: Re-phrase the missing firmware error to avoid duplication (Jaroslav Kysela) [2017320]
- ASoC: SOF: loader: release_firmware() on load failure to avoid batching (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Setup Dolphin Headset Mic as Phantom Jack (Jaroslav Kysela) [2017320]
- ALSA: pcxhr: "fix" PCXHR_REG_TO_PORT definition (Jaroslav Kysela) [2017320]
- ASoC: SOF: debug: No need to export the snd_sof_debugfs_io_item() (Jaroslav Kysela) [2017320]
- ASoC: SOF: loader: Use the generic ops for region debugfs handling (Jaroslav Kysela) [2017320]
- ASoC: SOF: Intel: Provide debugfs_add_region_item ops for core (Jaroslav Kysela) [2017320]
- ASoC: SOF: imx: Provide debugfs_add_region_item ops for core (Jaroslav Kysela) [2017320]
- ASoC: SOF: debug: Add generic API and ops for DSP regions (Jaroslav Kysela) [2017320]
- ASoC: SOF: core: Do not use 'bar' as parameter for block_read/write (Jaroslav Kysela) [2017320]
- ASoC: SOF: loader: No need to export snd_sof_fw_parse_ext_data() (Jaroslav Kysela) [2017320]
- ASoC: SOF: imx: Do not initialize the snd_sof_dsp_ops.read64 (Jaroslav Kysela) [2017320]
- ASoC: SOF: ipc: Remove snd_sof_dsp_mailbox_init() (Jaroslav Kysela) [2017320]
- ASoC: SOF: Intel: bdw: Set the mailbox offset directly in bdw_probe (Jaroslav Kysela) [2017320]
- ASoC: SOF: imx: imx8m: Bar index is only valid for IRAM and SRAM types (Jaroslav Kysela) [2017320]
- ASoC: SOF: imx: imx8: Bar index is only valid for IRAM and SRAM types (Jaroslav Kysela) [2017320]
- ASoC: cs35l41: Fix a bunch of trivial code formating/style issues (Jaroslav Kysela) [2017320]
- ASoC: cs35l41: Fixup the error messages (Jaroslav Kysela) [2017320]
- ASoC: cs35l41: Don't overwrite returned error code (Jaroslav Kysela) [2017320]
- ASoC: cs35l41: Combine adjacent register writes (Jaroslav Kysela) [2017320]
- ASoC: cs35l41: Use regmap_read_poll_timeout to wait for OTP boot (Jaroslav Kysela) [2017320]
- ASoC: cs35l41: Fix use of an uninitialised variable (Jaroslav Kysela) [2017320]
- ASoC: mediatek: mt6359: Fix unexpected error in bind/unbind flow (Jaroslav Kysela) [2017320]
- ASoC: SOF: loader: load_firmware callback is mandatory, treat it like that (Jaroslav Kysela) [2017320]
- ASoC: mediatek: mt8195: make array adda_dai_list static const (Jaroslav Kysela) [2017320]
- ASoC: mediatek: mt8195: Add missing of_node_put() (Jaroslav Kysela) [2017320]
- ASoC: SOF: Intel: hda: Relocate inline definitions from hda.h to hda.c for sdw (Jaroslav Kysela) [2017320]
- ASoC: SOF: Intel: hda: Remove boot_firmware skl and iccmax_icl declarations (Jaroslav Kysela) [2017320]
- ASoC: SOF: Intel: hda-dsp: Declare locally used functions as static (Jaroslav Kysela) [2017320]
- ASoC: SOF: Drop resindex_dma_base, dma_engine, dma_size from sof_dev_desc (Jaroslav Kysela) [2017320]
- ASoC: SOF: intel: Do no initialize resindex_dma_base (Jaroslav Kysela) [2017320]
- ASoC: intel: sof_rt5682: support jsl_rt5682s_mx98360a board (Jaroslav Kysela) [2017320]
- ASoC: intel: sof_rt5682: support jsl_rt5682s_rt1015 board (Jaroslav Kysela) [2017320]
- ASoC: intel: sof_rt5682: support jsl_rt5682s_rt1015p board (Jaroslav Kysela) [2017320]
- ASoC: Intel: sof_rt5682: support ALC5682I-VS codec (Jaroslav Kysela) [2017320]
- ASoC: SOF: Fix DSP oops stack dump output contents (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek: Quirks to enable speaker output for Lenovo Legion 7i 15IMHG05, Yoga 7i 14ITL5/15ITL5, and 13s Gen2 laptops. (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Unify mixer resume and reset_resume procedure (Jaroslav Kysela) [2017320]
- Revert "ALSA: hda: Drop workaround for a hang at shutdown again" (Jaroslav Kysela) [2017320]
- ALSA: oxfw: fix transmission method for Loud models based on OXFW971 (Jaroslav Kysela) [2017320]
- ASoC: pcm5102a: increase rate from 192k to 384k (Jaroslav Kysela) [2017320]
- ASoC: rt1011: add i2s reference control for rt1011 (Jaroslav Kysela) [2017320]
- ASoC: SOF: Handle control change notification from firmware (Jaroslav Kysela) [2017320]
- ASoC: mt8195: remove unnecessary CONFIG_PM (Jaroslav Kysela) [2017320]
- ASoC: SOF: control: fix a typo in put operations for kcontrol (Jaroslav Kysela) [2017320]
- ASoC: fsl_rpmsg: add soc specific data structure (Jaroslav Kysela) [2017320]
- ASoC: rt5682s: Add driver for ALC5682I-VS codec (Jaroslav Kysela) [2017320]
- ASoC: mediatek: mt8195: Fix unused initialization of pointer etdm_data (Jaroslav Kysela) [2017320]
- ASoC: ti: rename CONFIG_SND_SOC_DM365_VOICE_CODEC_MODULE (Jaroslav Kysela) [2017320]
- ASoC: SOF: core: allow module parameter to override dma trace Kconfig (Jaroslav Kysela) [2017320]
- ASoC: mediatek: mt8195: Make use of the helper function devm_platform_ioremap_resource() (Jaroslav Kysela) [2017320]
- ASoC: soc-topology: Move template info print soc_tplg_dapm_widget_create() (Jaroslav Kysela) [2017320]
- ASoC: amd: acp: declare and add prefix to 'bt_uart_enable' symbol (Jaroslav Kysela) [2017320]
- ASoC: mediatek: mt8195: Remove unsued irqs_lock. (Jaroslav Kysela) [2017320]
- ASoC: cs35l41: CS35L41 Boosted Smart Amplifier (Jaroslav Kysela) [2017320]
- ASoC: rockchip: pdm: Add support for path map (Jaroslav Kysela) [2017320]
- ASoC: rockchip: pdm: Add support for rk3568 pdm (Jaroslav Kysela) [2017320]
- ASoC: rockchip: Add support for rv1126 pdm (Jaroslav Kysela) [2017320]
- ASoC: mediatek: common: handle NULL case in suspend/resume function (Jaroslav Kysela) [2017320]
- ASoC: fsl_xcvr: register platform component before registering cpu dai (Jaroslav Kysela) [2017320]
- ASoC: fsl_spdif: register platform component before registering cpu dai (Jaroslav Kysela) [2017320]
- ASoC: fsl_micfil: register platform component before registering cpu dai (Jaroslav Kysela) [2017320]
- ASoC: fsl_esai: register platform component before registering cpu dai (Jaroslav Kysela) [2017320]
- ASoC: fsl_sai: register platform component before registering cpu dai (Jaroslav Kysela) [2017320]
- ASoC: mediatek: add required config dependency (Jaroslav Kysela) [2017320]
- ASoC: Intel: sof_sdw: tag SoundWire BEs as non-atomic (Jaroslav Kysela) [2017320]
- ALSA: gus: Fix repeated probe for ISA interwave card (Jaroslav Kysela) [2017320]
- ALSA: gus: Fix repeated probes of snd_gus_create() (Jaroslav Kysela) [2017320]
- ALSA: vx222: fix null-ptr-deref (Jaroslav Kysela) [2017320]
- ASoC: rockchip: i2s: Fix concurrency between tx/rx (Jaroslav Kysela) [2017320]
- ASoC: mt8195: correct the dts parsing logic about DPTX and HDMITX (Jaroslav Kysela) [2017320]
- ASoC: Intel: boards: Fix CONFIG_SND_SOC_SDW_MOCKUP select (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Add registration quirk for JBL Quantum 800 (Jaroslav Kysela) [2017320]
- ASoC: rt5682: fix headset background noise when S3 state (Jaroslav Kysela) [2017320]
- ASoC: mediatek: SND_SOC_MT8195 should depend on ARCH_MEDIATEK (Jaroslav Kysela) [2017320]
- ASoC: samsung: s3c24xx_simtec: fix spelling mistake "devicec" -> "device" (Jaroslav Kysela) [2017320]
- ASoC: audio-graph: respawn Platform Support (Jaroslav Kysela) [2017320]
- ASoC: mediatek: mt8195: add MTK_PMIC_WRAP dependency (Jaroslav Kysela) [2017320]
- ASoC: Revert PCM trigger changes (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Add lowlatency module option (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Initialize Codec only in init fixup. (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Ensure Type Detection is only run on startup when necessary (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Work around for XRUN with low latency playback (Jaroslav Kysela) [2017320]
- ALSA: pcm: fix divide error in snd_pcm_lib_ioctl (Jaroslav Kysela) [2017320]
- ASoC: soc-pcm: test refcount before triggering (Jaroslav Kysela) [2017320]
- ASoC: soc-pcm: protect BE dailink state changes in trigger (Jaroslav Kysela) [2017320]
- ASoC: wcd9335: Disable irq on slave ports in the remove function (Jaroslav Kysela) [2017320]
- ASoC: wcd9335: Fix a memory leak in the error handling path of the probe function (Jaroslav Kysela) [2017320]
- ASoC: wcd9335: Fix a double irq free in the remove function (Jaroslav Kysela) [2017320]
- ALSA: hda: Disable runtime resume at shutdown (Jaroslav Kysela) [2017320]
- ASoC: rockchip: i2s: Add support for frame inversion (Jaroslav Kysela) [2017320]
- ASoC: rockchip: i2s: Add compatible for more SoCs (Jaroslav Kysela) [2017320]
- ASoC: rockchip: i2s: Make playback/capture optional (Jaroslav Kysela) [2017320]
- ASoC: rockchip: i2s: Fixup config for DAIFMT_DSP_A/B (Jaroslav Kysela) [2017320]
- ASoC: rockchip: i2s: Fix regmap_ops hang (Jaroslav Kysela) [2017320]
- ASoC: rockchip: i2s: Improve dma data transfer efficiency (Jaroslav Kysela) [2017320]
- ASoC: rockchip: i2s: Fixup clk div error (Jaroslav Kysela) [2017320]
- ASoC: rockchip: i2s: Add support for set bclk ratio (Jaroslav Kysela) [2017320]
- ASoC: rockchip: spdif: Add support for rk3568 spdif (Jaroslav Kysela) [2017320]
- ASoC: rockchip: spdif: Fix some coding style (Jaroslav Kysela) [2017320]
- ASoC: rockchip: spdif: Mark SPDIF_SMPDR as volatile (Jaroslav Kysela) [2017320]
- ASoC: mediatek: mt8195: Fix spelling mistake "bitwiedh" -> "bitwidth" (Jaroslav Kysela) [2017320]
- ASoC: dwc: Get IRQ optionally (Jaroslav Kysela) [2017320]
- ASoC: imx-rpmsg: change dev_err to dev_err_probe for -EPROBE_DEFER (Jaroslav Kysela) [2017320]
- ASoC: rt5682: Fix the vol+ button detection issue (Jaroslav Kysela) [2017320]
- ASoC: Intel: bytcr_rt5640: Make rt5640_jack_gpio/rt5640_jack2_gpio static (Jaroslav Kysela) [2017320]
- ASoC: SOF: intel: remove duplicate include (Jaroslav Kysela) [2017320]
- ASoC: mediatek: mt8195: add HDMITX audio support (Jaroslav Kysela) [2017320]
- ASoC: mediatek: mt8195: add DPTX audio support (Jaroslav Kysela) [2017320]
- ASoC: mediatek: mt8195: add machine driver with mt6359, rt1019 and rt5682 (Jaroslav Kysela) [2017320]
- ASoC: mediatek: mt8195: add platform driver (Jaroslav Kysela) [2017320]
- ASoC: mediatek: mt8195: support pcm in platform driver (Jaroslav Kysela) [2017320]
- ASoC: mediatek: mt8195: support adda in platform driver (Jaroslav Kysela) [2017320]
- ASoC: mediatek: mt8195: support etdm in platform driver (Jaroslav Kysela) [2017320]
- ASoC: mediatek: mt8195: support audsys clock control (Jaroslav Kysela) [2017320]
- ASoC: mediatek: mt8195: update mediatek common driver (Jaroslav Kysela) [2017320]
- ASoC: wm_adsp: Put debugfs_remove_recursive back in (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Move set-interface-first workaround into common quirk (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek: Quirk for HP Spectre x360 14 amp setup (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Fix regression on Sony WALKMAN NW-A45 DAC (Jaroslav Kysela) [2017320]
- ASoC: rt1015: remove possible unused variable `bclk_ms' (Jaroslav Kysela) [2017320]
- ASoC: Intel: bytcr_rt5640: Mark hp_elitepad_1000g2_jack?_check functions static (Jaroslav Kysela) [2017320]
- ASoC: ics43432: add CMM-4030D-261 support (Jaroslav Kysela) [2017320]
- ASoC: Intel: Skylake: Select first entry for singular pipe config arrays (Jaroslav Kysela) [2017320]
- ASoC: Intel: Skylake: Properly configure modules with generic extension (Jaroslav Kysela) [2017320]
- ASoC: Intel: Skylake: Support modules with generic extension (Jaroslav Kysela) [2017320]
- ASoC: Intel: Skylake: Support multiple format configs (Jaroslav Kysela) [2017320]
- ASoC: Intel: Skylake: Simplify m_state for loadable modules (Jaroslav Kysela) [2017320]
- ASoC: Intel: Skylake: Fix passing loadable flag for module (Jaroslav Kysela) [2017320]
- ASoC: Intel: Skylake: Fix module configuration for KPB and MIXER (Jaroslav Kysela) [2017320]
- ASoC: Intel: Skylake: Fix module resource and format selection (Jaroslav Kysela) [2017320]
- ASoC: Intel: Skylake: Select proper format for NHLT blob (Jaroslav Kysela) [2017320]
- ASoC: Intel: Skylake: Leave data as is when invoking TLV IPCs (Jaroslav Kysela) [2017320]
- ASoC: Intel: kbl_da7219_max98927: Fix format selection for max98373 (Jaroslav Kysela) [2017320]
- soundwire: cadence: do not extend reset delay (Jaroslav Kysela) [2017320]
- soundwire: intel: conditionally exit clock stop mode on system suspend (Jaroslav Kysela) [2017320]
- soundwire: intel: skip suspend/resume/wake when link was not started (Jaroslav Kysela) [2017320]
- soundwire: intel: fix potential race condition during power down (Jaroslav Kysela) [2017320]
- ASoC: intel: atom: Revert PCM buffer address setup workaround again (Jaroslav Kysela) [2017320]
- ALSA: doc: Fix indentation warning (Jaroslav Kysela) [2017320]
- ALSA: hda: Update documentation for aliasing via the model option (Jaroslav Kysela) [2017320]
- ALSA: hda: Allow model option to specify PCI SSID alias (Jaroslav Kysela) [2017320]
- ALSA: hda: Code refactoring snd_hda_pick_fixup() (Jaroslav Kysela) [2017320]
- ALSA: firewire-motu: add support for MOTU 896HD (Jaroslav Kysela) [2017320]
- ALSA: hda/realtek: Workaround for conflicting SSID on ASUS ROG Strix G17 (Jaroslav Kysela) [2017320]
- ASoC: rsnd: adg: clearly handle clock error / NULL case (Jaroslav Kysela) [2017320]
- ASoC: rsnd: core: make some arrays static const, makes object smaller (Jaroslav Kysela) [2017320]
- ASoC: Intel: bytcr_rt5640: Add support for HP Elite Pad 1000G2 jack-detect (Jaroslav Kysela) [2017320]
- ASoC: Intel: bytct_rt5640: Add a separate "Headset Mic 2" DAPM pin for the mic on the 2nd jack (Jaroslav Kysela) [2017320]
- ASoC: rt5640: Add rt5640_set_ovcd_params() helper (Jaroslav Kysela) [2017320]
- ASoC: rt5640: Add optional hp_det_gpio parameter to rt5640_detect_headset() (Jaroslav Kysela) [2017320]
- ASoC: rt5640: Delay requesting IRQ until the machine-drv calls set_jack (Jaroslav Kysela) [2017320]
- ASoC: rt5640: Move rt5640_disable_jack_detect() up in the rt5640.c file (Jaroslav Kysela) [2017320]
- ASoC: uniphier: make arrays mul and div static const, makes object smaller (Jaroslav Kysela) [2017320]
- ASoC: sh: rz-ssi: Improve error handling in rz_ssi_dma_request function (Jaroslav Kysela) [2017320]
- ASoC: fsl_rpmsg: Check -EPROBE_DEFER for getting clocks (Jaroslav Kysela) [2017320]
- ALSA: hda/analog - Sink ad198x_shutup() and shuffle CONFIG_PM guards (Jaroslav Kysela) [2017320]
- ALSA: hda/sigmatel - Sink stac_shutup() into stac_suspend() (Jaroslav Kysela) [2017320]
- ASoC: Intel: bytcr_rt5640: Use cfg-lineout:2 in the components string (Jaroslav Kysela) [2017320]
- ASoC: sh: rz-ssi: Fix wrong operator used issue (Jaroslav Kysela) [2017320]
- ASoC: tegra30: i2s: Fix incorrect usage of of_device_get_match_data (Jaroslav Kysela) [2017320]
- ASoC: tegra30: ahub: Fix incorrect usage of of_device_get_match_data (Jaroslav Kysela) [2017320]
- ALSA: hda: Drop workaround for a hang at shutdown again (Jaroslav Kysela) [2017320]
- ASoC: sh: rz-ssi: Fix dereference of noderef expression warning (Jaroslav Kysela) [2017320]
- ASoC: tegra30: i2s: Use of_device_get_match_data (Jaroslav Kysela) [2017320]
- ASoC: tegra30: ahub: Use of_device_get_match_data (Jaroslav Kysela) [2017320]
- ASoC: soc-ac97: cleanup cppcheck warning (Jaroslav Kysela) [2017320]
- ASoC: soc-component: cleanup cppcheck warning at snd_soc_pcm_component_pm_runtime_get() (Jaroslav Kysela) [2017320]
- ASoC: soc-jack: cleanup cppcheck warning for CONFIG_GPIOLIB (Jaroslav Kysela) [2017320]
- ASoC: soc-jack: cleanup cppcheck warning at snd_soc_jack_report() (Jaroslav Kysela) [2017320]
- ASoC: soc-dai: cleanup cppcheck warning at snd_soc_pcm_dai_new() (Jaroslav Kysela) [2017320]
- ASoC: soc-dai: cleanup cppcheck warning at snd_soc_dai_link_set_capabilities() (Jaroslav Kysela) [2017320]
- ASoC: soc-generic-dmaengine-pcm: cleanup cppcheck warning at dmaengine_copy_user() (Jaroslav Kysela) [2017320]
- ASoC: soc-generic-dmaengine-pcm: cleanup cppcheck warning at dmaengine_pcm_new() (Jaroslav Kysela) [2017320]
- ASoC: soc-generic-dmaengine-pcm: cleanup cppcheck warning at dmaengine_pcm_hw_params() (Jaroslav Kysela) [2017320]
- ALSA: hda: Nuke unused reboot_notify callback (Jaroslav Kysela) [2017320]
- ALSA: hda: Suspend codec at shutdown (Jaroslav Kysela) [2017320]
- ALSA: hda: conexant: Turn off EAPD at suspend, too (Jaroslav Kysela) [2017320]
- ALSA: pcm: Add SNDRV_PCM_INFO_EXPLICIT_SYNC flag (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Input source control - digidesign mbox (Jaroslav Kysela) [2017320]
- ASoC: Intel: boards: use software node API in Atom boards (Jaroslav Kysela) [2017320]
- ASoC: Intel: remove device_properties for Atom boards (Jaroslav Kysela) [2017320]
- ASoC: Intel: use software node API in SoundWire machines (Jaroslav Kysela) [2017320]
- ASoC: Intel: sof_sdw_rt711*: keep codec device reference until remove (Jaroslav Kysela) [2017320]
- ASoC: Intel: sof_sdw: pass card information to init/exit functions (Jaroslav Kysela) [2017320]
- ASoC: Intel: boards: get codec device with ACPI instead of bus search (Jaroslav Kysela) [2017320]
- ASoC: Intel: boards: handle errors with acpi_dev_get_first_match_dev() (Jaroslav Kysela) [2017320]
- ASoC: Intel: boards: harden codec property handling (Jaroslav Kysela) [2017320]
- ASoC: rt5682: Remove unused variable in rt5682_i2c_remove() (Jaroslav Kysela) [2017320]
- ASoC: sh: rz-ssi: Add SSI DMAC support (Jaroslav Kysela) [2017320]
- ASoC: sh: Add RZ/G2L SSIF-2 driver (Jaroslav Kysela) [2017320]
- ASoC: SOF: Intel: make DMI L1 selection more robust (Jaroslav Kysela) [2017320]
- ASoC: SOF: Intel: simplify logic for DMI_L1 handling (Jaroslav Kysela) [2017320]
- ASoC: SOF: Intel: hda-stream: remove always true condition (Jaroslav Kysela) [2017320]
- ASoC: SOF: Intel: Kconfig: clarify DMI L1 option description (Jaroslav Kysela) [2017320]
- ALSA: memalloc: Count continuous pages in vmalloc buffer handler (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Prevent pops and clicks during suspend (Jaroslav Kysela) [2017320]
- ALSA: hda_audio_ext: fix kernel-doc (Jaroslav Kysela) [2017320]
- ALSA: core: control_led: use strscpy instead of strlcpy (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Unmute/Mute codec when stream starts/stops (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Follow correct CS42L42 power down sequence for suspend (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Remove unnecessary delays (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Use timeout rather than retries for I2C transaction waits (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Set fixed sample rate of 48kHz for CS42L42 (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Enable Full Scale Volume for Line Out Codec on Dolphin (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Add support for dolphin (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Add Support to disable jack type detection for CS42L42 (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Support multiple sub_codecs for Suspend/Resume/Unsol events (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Move codec properties to its own struct (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Separate CS8409, CS42L42 and project functions (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Support i2c bulk read/write functions (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Avoid re-setting the same page as the last access (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Avoid setting the same I2C address for every access (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Dont disable I2C clock between consecutive accesses (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Generalize volume controls (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Prevent I2C access during suspend time (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Simplify CS42L42 jack detect. (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Mask CS42L42 wake events (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Disable unsolicited response for the first boot (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Disable unsolicited responses during suspend (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Disable unnecessary Ring Sense for Cyborg/Warlock/Bullseye (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Reduce HS pops/clicks for Cyborg (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Mask all CS42L42 interrupts on initialization (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Use enums for register names and coefficients (Jaroslav Kysela) [2017320]
- ALSA: hda/cs8409: Move arrays of configuration to a new file (Jaroslav Kysela) [2017320]
- ALSA: hda/cirrus: Move CS8409 HDA bridge to separate module (Jaroslav Kysela) [2017320]
- ASoC: rt5682: Properly turn off regulators if wrong device ID (Jaroslav Kysela) [2017320]
- ASoC: rt5682: Adjust headset volume button threshold again (Jaroslav Kysela) [2017320]
- ASoC: Intel: Fix platform ID matching (Jaroslav Kysela) [2017320]
- ASoC: rt1015p: add new acpi id and comapatible id (Jaroslav Kysela) [2017320]
- ASoC: max98390: Add support change dsm param name (Jaroslav Kysela) [2017320]
- ALSA: msnd: Use proper mmap method (Jaroslav Kysela) [2017320]
- ASoC: qdsp6: q6adm: fix cppcheck warnings for unnecessary initialization (Jaroslav Kysela) [2017320]
- ASoC: qdsp6: q6asm: fix cppcheck warnings for unnecessary initialization (Jaroslav Kysela) [2017320]
- ASoC: qcom: apq8016_sbc: Add SEC_MI2S support (Jaroslav Kysela) [2017320]
- ALSA: pci: cs46xx: Fix set up buffer type properly (Jaroslav Kysela) [2017320]
- ALSA: pci: rme: Set up buffer type properly (Jaroslav Kysela) [2017320]
- ALSA: pcm: Check mmap capability of runtime dma buffer at first (Jaroslav Kysela) [2017320]
- ALSA: harmony: Drop superfluous address setup (Jaroslav Kysela) [2017320]
- ALSA: memalloc: Fix mmap of SG-buffer with WC pages (Jaroslav Kysela) [2017320]
- ASoC: cs42l42: Update module authors (Jaroslav Kysela) [2017320]
- ASoC: cs42l42: Assume 24-bit samples are in 32-bit slots (Jaroslav Kysela) [2017320]
- ASoC: cs42l42: Validate dai_set_sysclk() frequency (Jaroslav Kysela) [2017320]
- ASoC: cs42l42: Add PLL configuration for 44.1kHz/16-bit (Jaroslav Kysela) [2017320]
- ASoC: rt5640: Silence warning message about missing interrupt (Jaroslav Kysela) [2017320]
- ASoC: codecs: wcd938x: add Multi Button Headset Control support (Jaroslav Kysela) [2017320]
- ASoC: simple-card-utils: Avoid over-allocating DLCs (Jaroslav Kysela) [2017320]
- ASoC: wcd938x: simplify return value (Jaroslav Kysela) [2017320]
- ASoC: mt6359-accdet.c: remove useless assignments (Jaroslav Kysela) [2017320]
- ASoC: max98090: remove duplicate status reads and useless assignmment (Jaroslav Kysela) [2017320]
- ASoC: soc-dapm: cleanup cppcheck warning at soc_dapm_dai_stream_event() (Jaroslav Kysela) [2017320]
- ASoC: soc-dapm: cleanup cppcheck warning at snd_soc_dapm_new_controls() (Jaroslav Kysela) [2017320]
- ASoC: soc-dapm: cleanup cppcheck warning at snd_soc_dapm_weak_routes() (Jaroslav Kysela) [2017320]
- ASoC: soc-dapm: cleanup cppcheck warning at snd_soc_dapm_add_routes() (Jaroslav Kysela) [2017320]
- ASoC: soc-dapm: cleanup cppcheck warning at snd_soc_dapm_del_route() (Jaroslav Kysela) [2017320]
- ASoC: soc-dapm: cleanup cppcheck warning at dapm_seq_run() (Jaroslav Kysela) [2017320]
- ASoC: soc-dapm: cleanup cppcheck warning at dapm_seq_check_event() (Jaroslav Kysela) [2017320]
- ASoC: soc-dapm: cleanup cppcheck warning at dapm_new_dai_link() (Jaroslav Kysela) [2017320]
- ASoC: soc-dapm: cleanup cppcheck warning at dapm_new_pga() (Jaroslav Kysela) [2017320]
- ASoC: soc-dapm: cleanup cppcheck warning at dapm_set_mixer_path_status() (Jaroslav Kysela) [2017320]
- ASoC: soc-dapm: cleanup cppcheck warning at dapm_connect_mux() (Jaroslav Kysela) [2017320]
- ASoC: soc-dapm: cleanup cppcheck warning at dapm_wcache_lookup() (Jaroslav Kysela) [2017320]
- ALSA: es1688: Avoid devres management for es1688 object creation (Jaroslav Kysela) [2017320]
- ALSA: pci/korg1212: completely remove 'set but not used' warnings (Jaroslav Kysela) [2017320]
- ASoC: amd: vangogh: Drop superfluous mmap callback (Jaroslav Kysela) [2017320]
- ALSA: memalloc: Store snd_dma_buffer.addr for continuous pages, too (Jaroslav Kysela) [2017320]
- ALSA: memalloc: Fix pgprot for WC mmap on x86 (Jaroslav Kysela) [2017320]
- ASoC: sprd: Use managed buffer allocation (Jaroslav Kysela) [2017320]
- ASoC: qcom: qdsp6: Use managed buffer allocation (Jaroslav Kysela) [2017320]
- ASoC: qcom: lpass: Use managed buffer allocation (Jaroslav Kysela) [2017320]
- ASoC: mpc5200: Use managed buffer allocation (Jaroslav Kysela) [2017320]
- ASoC: fsl_dma: Use managed buffer allocation (Jaroslav Kysela) [2017320]
- ASoC: fsl_asrc_dma: Use managed buffer allocation (Jaroslav Kysela) [2017320]
- ASoC: tegra: Use managed buffer allocation (Jaroslav Kysela) [2017320]
- ASoC: fsl: imx-pcm-rpmsg: Use managed buffer allocation (Jaroslav Kysela) [2017320]
- ASoC: fsl: imx-pcm-fiq: Use managed buffer allocation (Jaroslav Kysela) [2017320]
- ASoC: bcm: Use managed PCM buffer allocation (Jaroslav Kysela) [2017320]
- ALSA: pxa2xx: Use managed PCM buffer allocation (Jaroslav Kysela) [2017320]
- ALSA: memalloc: Support WC allocation on all architectures (Jaroslav Kysela) [2017320]
- ALSA: pcm: Allow exact buffer preallocation (Jaroslav Kysela) [2017320]
- ALSA: memalloc: Correctly name as WC (Jaroslav Kysela) [2017320]
- ALSA: memalloc: Minor refactoring (Jaroslav Kysela) [2017320]
- ASoC: mediatek: mt6359: convert to use module_platform_driver (Jaroslav Kysela) [2017320]
- ASoC: rt5514: make array div static const, makes object smaller (Jaroslav Kysela) [2017320]
- ASoC: codecs: ad193x: add support for 96kHz and 192kHz playback rates (Jaroslav Kysela) [2017320]
- ASoC: soc-ops: cleanup cppcheck warning at snd_soc_put_xr_sx() (Jaroslav Kysela) [2017320]
- ASoC: soc-ops: cleanup cppcheck warning at snd_soc_get_xr_sx() (Jaroslav Kysela) [2017320]
- ASoC: soc-ops: cleanup cppcheck warning at snd_soc_limit_volume() (Jaroslav Kysela) [2017320]
- ASoC: soc-ops: cleanup cppcheck warning at snd_soc_put_volsw_sx() (Jaroslav Kysela) [2017320]
- ASoC: Intel: sof_sdw_max98373: remove useless inits (Jaroslav Kysela) [2017320]
- ASoC: Intel: update sof_pcm512x quirks (Jaroslav Kysela) [2017320]
- ASoC: SOF: Intel: Use DMI string to search for adl_mx98373_rt5682 variant (Jaroslav Kysela) [2017320]
- ASoC: Intel: sof_sdw: add quirk for Dell XPS 9710 (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: make array static const, makes object smaller (Jaroslav Kysela) [2017320]
- ASoC: tlv320aic32x4: make array clocks static, makes object smaller (Jaroslav Kysela) [2017320]
- ASoC: Intel: bytcr_rt5640: Fix HP ElitePad 1000 G2 quirk (Jaroslav Kysela) [2017320]
- ASoC: Intel: bytcr_rt5640: Add support for a second headset mic input (Jaroslav Kysela) [2017320]
- ASoC: Intel: bytcr_rt5640: Add support for a second headphones output (Jaroslav Kysela) [2017320]
- ASoC: Intel: bytcr_rt5640: Add a byt_rt5640_get_codec_dai() helper (Jaroslav Kysela) [2017320]
- ASoC: Intel: bytcr_rt5640: Add line-out support (Jaroslav Kysela) [2017320]
- ASoC: Intel: bytcr_rt5640: Move "Platform Clock" routes to the maps for the matching in-/output (Jaroslav Kysela) [2017320]
- soundwire: intel: introduce shim and alh base (Jaroslav Kysela) [2017320]
- ASoC: SOF: intel: add snd_sof_dsp_check_sdw_irq ops (Jaroslav Kysela) [2017320]
- ASoC: SOF: intel: move sof_intel_dsp_desc() forward (Jaroslav Kysela) [2017320]
- ASoC: SOF: intel: hda: remove HDA_DSP_REG_SNDW_WAKE_STS definition (Jaroslav Kysela) [2017320]
- ASoC: SOF: intel: add sdw_shim/alh_base to sof_intel_dsp_desc (Jaroslav Kysela) [2017320]
- soundwire: move intel sdw register definitions to sdw_intel.h (Jaroslav Kysela) [2017320]
- ASoC: soc-topology: cleanup cppcheck warning at snd_soc_find_dai_link() (Jaroslav Kysela) [2017320]
- ASoC: soc-topology: cleanup cppcheck warning at soc_tplg_kcontrol_elems_load() (Jaroslav Kysela) [2017320]
- ASoC: soc-topology: cleanup cppcheck warning at soc_tplg_dapm_widget_elems_load() (Jaroslav Kysela) [2017320]
- ASoC: soc-topology: cleanup cppcheck warning at soc_tplg_dai_elems_load() (Jaroslav Kysela) [2017320]
- ASoC: soc-topology: cleanup cppcheck warning at soc_tplg_process_headers() (Jaroslav Kysela) [2017320]
- ASoC: rsnd: make some arrays static const, makes object smaller (Jaroslav Kysela) [2017320]
- ALSA: doc: Add the description of quirk_flags option for snd-usb-audio (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Add quirk_flags module option (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Move generic DSD raw detection into quirk_flags (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Move ignore_ctl_error check into quirk_flags (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Move autosuspend quirk into quirk_flags (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Move rate validation quirk into quirk_flags (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Move interface setup delay into quirk_flags (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Move control message delay quirk into quirk_flags (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Move ITF-USB DSD quirk handling into quirk_flags (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Move clock setup quirk into quirk_flags (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Move playback_first flag into quirk_flags (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Move tx_length quirk handling to quirk_flags (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Move txfr_quirk handling to quirk_flags (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Move media-controller API quirk into quirk_flags (Jaroslav Kysela) [2017320]
- ALSA: usb-audio: Introduce quirk_flags field (Jaroslav Kysela) [2017320]
- soundwire: cadence: override PDI configurations to create loopback (Jaroslav Kysela) [2017320]
- soundwire: cadence: add debugfs interface for PDI loopbacks (Jaroslav Kysela) [2017320]
- soundwire: stream: don't program mockup device ports (Jaroslav Kysela) [2017320]
- soundwire: bus: squelch error returned by mockup devices (Jaroslav Kysela) [2017320]
- soundwire: add flag to ignore all command/control for mockup devices (Jaroslav Kysela) [2017320]
- soundwire: stream: don't abort bank switch on Command_Ignored/-ENODATA (Jaroslav Kysela) [2017320]
- soundwire: cadence: add paranoid check on self-clearing bits (Jaroslav Kysela) [2017320]
- ALSA: core: Fix double calls of snd_card_free() via devres (Jaroslav Kysela) [2017320]
- ALSA: pcxhr: use __func__ to get funcion's name in an output message (Jaroslav Kysela) [2017320]
- ASoC: intel: skylake: Drop superfluous mmap callback (Jaroslav Kysela) [2017320]
- ASoC: amd: Drop superfluous mmap callbacks (Jaroslav Kysela) [2017320]
- ASoC: v253_init: eliminate pointer to string (Jaroslav Kysela) [2017320]
- ASoC: cx20442: tty_ldisc_ops::write_wakeup is optional (Jaroslav Kysela) [2017320]
- ASoC: samsung: Constify static snd_soc_ops (Jaroslav Kysela) [2017320]
- ASoC: soc-core: cleanup cppcheck warning at snd_soc_of_parse_audio_routing() (Jaroslav Kysela) [2017320]
- ASoC: soc-core: cleanup cppcheck warning at snd_soc_of_parse_audio_simple_widgets() (Jaroslav Kysela) [2017320]
- ASoC: soc-core: cleanup cppcheck warning at snd_soc_add_controls() (Jaroslav Kysela) [2017320]
- ASoC: soc-core: cleanup cppcheck warning at snd_soc_unregister_component() (Jaroslav Kysela) [2017320]
- ASoC: soc-core: cleanup cppcheck warning at snd_soc_daifmt_parse_format() (Jaroslav Kysela) [2017320]
- ASoC: soc-core: cleanup cppcheck warning at snd_soc_get_dai_name() (Jaroslav Kysela) [2017320]
- ASoC: soc-core: cleanup cppcheck warning at snd_soc_set_dmi_name() (Jaroslav Kysela) [2017320]
- ASoC: bcm: cygnus-pcm: Fix unused assignment about 'rc' (Jaroslav Kysela) [2017320]
- ASoC: Intel: Fix spelling contraction "cant" -> "can't" (Jaroslav Kysela) [2017320]
- ASoC: amd: fix an IS_ERR() vs NULL bug in probe (Jaroslav Kysela) [2017320]
- ASoC: rt5682: enable SAR ADC power saving mode during suspend (Jaroslav Kysela) [2017320]
- ASoC: soc-pcm: cleanup cppcheck warning at dpcm_runtime_setup_be_chan() (Jaroslav Kysela) [2017320]
- ASoC: soc-pcm: cleanup cppcheck warning at dpcm_be_is_active() (Jaroslav Kysela) [2017320]
- ASoC: soc-pcm: cleanup cppcheck warning at soc_get_playback_capture() (Jaroslav Kysela) [2017320]
- ASoC: soc-pcm: cleanup cppcheck warning at soc_pcm_components_close() (Jaroslav Kysela) [2017320]
- ASoC: soc-pcm: cleanup cppcheck warning at soc_pcm_apply_msb() (Jaroslav Kysela) [2017320]
- ALSA: seq: Fix comments of wrong client number for MIDI Passthrough (Jaroslav Kysela) [2017320]
- ASoC: rt1015: Remove unnecessary flush work on rt1015 driver (Jaroslav Kysela) [2017320]
- docs: sound: kernel-api: writing-an-alsa-driver.rst: replace some characters (Jaroslav Kysela) [2017320]
- ASoC: amd: Use dev_probe_err helper (Jaroslav Kysela) [2017320]
- ASoC: amd: Don't show messages about deferred probing by default (Jaroslav Kysela) [2017320]
- soundwire: dmi-quirks: add quirk for Intel 'Bishop County' NUC M15 (Jaroslav Kysela) [2017320]
- soundwire: bus: update Slave status in sdw_clear_slave_status (Jaroslav Kysela) [2017320]
- soundwire: cadence: Remove ret variable from sdw_cdns_irq() (Jaroslav Kysela) [2017320]
- soundwire: bus: filter out more -EDATA errors on clock stop (Jaroslav Kysela) [2017320]
- soundwire: dmi-quirks: add ull suffix for SoundWire _ADR values (Jaroslav Kysela) [2017320]
- ASoC: amd: enable vangogh acp5x driver build (Jaroslav Kysela) [2017320]
- ASoC: amd: add vangogh i2s dma driver pm ops (Jaroslav Kysela) [2017320]
- ASoC: amd: add vangogh pci driver pm ops (Jaroslav Kysela) [2017320]
- ASoC: amd: add vangogh i2s dai driver ops (Jaroslav Kysela) [2017320]
- ASoC: amd: add vangogh i2s controller driver (Jaroslav Kysela) [2017320]
- ASoC: amd: add ACP5x pcm dma driver ops (Jaroslav Kysela) [2017320]
- ASoC: amd: irq handler changes for ACP5x PCM dma driver (Jaroslav Kysela) [2017320]
- ASoC: amd: add ACP5x PCM platform driver (Jaroslav Kysela) [2017320]
- ASoC: amd: create acp5x platform devices (Jaroslav Kysela) [2017320]
- ASoc: amd: add acp5x init/de-init functions (Jaroslav Kysela) [2017320]
- ASoC: amd: add Vangogh ACP PCI driver (Jaroslav Kysela) [2017320]
- ASoC: amd: add Vangogh ACP5x IP register header (Jaroslav Kysela) [2017320]
- ALSA: sc6000: Use explicit cast for __iomem pointer (Jaroslav Kysela) [2017320]
- ALSA: korg1212: Fix wrongly shuffled firmware loader code (Jaroslav Kysela) [2017320]
- ALSA: als300: Fix missing chip initialization (Jaroslav Kysela) [2017320]
- ALSA: cs4281: Fix missing chip initialization (Jaroslav Kysela) [2017320]
- ALSA: sc6000: Assign vport directly on card's private_data (Jaroslav Kysela) [2017320]
- ALSA: sc6000: Fix incorrect sizeof operator (Jaroslav Kysela) [2017320]
- ALSA: opti9xx: fix missing { } around an if block (Jaroslav Kysela) [2017320]
- ALSA: nm256: Fix error return code in snd_nm256_create() (Jaroslav Kysela) [2017320]
- ASOC: Intel: sof_sdw: add quirk for Intel 'Bishop County' NUC M15 (Jaroslav Kysela) [2017320]
- ASoC: ti: j721e-evm: Convert the audio domain IDs to enum (Jaroslav Kysela) [2017320]
- ALSA: pcsp: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: dummy: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: aloop: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: mpu401: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: serial-u16550: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: mtpav: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: virmidi: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: x86: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: wavefront: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: sscape: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: sc6000: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: opl3sa2: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: opti9xx: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: msnd: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: gus: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: galaxy: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: es18xx: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: es1688: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: cs423x: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: cmi8330: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: cmi8328: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: azt2320: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: als100: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: adlib: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: ad1848: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: sb: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: wss: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: ad1816a: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: ymfpci: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: vx222: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: vx: Manage vx_core object with devres (Jaroslav Kysela) [2017320]
- ALSA: trident: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: rme9652: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: hdspm: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: hdsp: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: riptide: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: oxygen: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: nm256: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: lx6464es: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: lola: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: korg1212: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: ice1724: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: ali5451: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: ice1724: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: ice1712: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: emu10k1x: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: emu10k1: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: echoaudio: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: cs5535audio: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: cs46xx: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: ca0106: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: aw2: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: au88x0: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: ali5451: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: via82xx: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: sonicvibes: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: sis7019: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: rme96: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: rme32: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: maestro3: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: fm801: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: es1968: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: es1938: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: ens137x: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: cs5530: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: cs4281: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: cmipci: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: bt87x: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: azt3328: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: als4000: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: als300: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: ad1889: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: hda: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: atiixp: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: intel8x0: Allocate resources with device-managed APIs (Jaroslav Kysela) [2017320]
- ALSA: doc: Add device-managed resource section (Jaroslav Kysela) [2017320]
- ALSA: core: Add device-managed request_dma() (Jaroslav Kysela) [2017320]
- ALSA: core: Add managed card creation (Jaroslav Kysela) [2017320]
- ALSA: core: Add device-managed page allocator helper (Jaroslav Kysela) [2017320]
- ALSA: aloop: Fix spelling mistake "synchronization" -> "synchronization" (Jaroslav Kysela) [2017320]
- ASoC: codecs: wcd938x: remove unused port-map reference (Jaroslav Kysela) [2017320]
- ASoC: codecs: lpass-rx-macro: clean up for-loop indentation in switch statement (Jaroslav Kysela) [2017320]
- ALSA: compress: Initialize mutex in snd_compress_new() (Jaroslav Kysela) [2017320]
- ALSA: compress: Drop unused functions (Jaroslav Kysela) [2017320]
- ASoC: Intel: boards: sof_sdw: add SoundWire mockup codecs for tests (Jaroslav Kysela) [2017320]
- ASoC: soc-acpi: tgl: add table for SoundWire mockup devices (Jaroslav Kysela) [2017320]
- ASoC: soc-acpi: cnl: add table for SoundWire mockup devices (Jaroslav Kysela) [2017320]
- ASoC: codecs: add SoundWire mockup device support (Jaroslav Kysela) [2017320]
- ASoC: Intel: sof_sdw: update quirk for jack detection in ADL RVP (Jaroslav Kysela) [2017320]
- ASoC: Intel: sof_sdw: include rt711.h for RT711 JD mode (Jaroslav Kysela) [2017320]
- ASoC: Intel: sof_sdw: extends SOF_RT711_JDSRC to 4 bits (Jaroslav Kysela) [2017320]
- ASoC: Intel: sof_rt5682: code refactor for max98360a (Jaroslav Kysela) [2017320]
- ASoC: Intel: sof_cs42l42: add support for jsl_cs4242_mx98360a (Jaroslav Kysela) [2017320]
- ASoC: Intel: maxim-common: support max98360a (Jaroslav Kysela) [2017320]
- ASoC: Intel: sof_cs42l42: support arbitrary DAI link sequence (Jaroslav Kysela) [2017320]
- ALSA: intel8x0: Skip ac97 clock measurement on VM (Jaroslav Kysela) [2017320]
- ALSA: hda/hdmi: Add option to enable all pins forcibly (Jaroslav Kysela) [2017320]
- ALSA: x86: simplify with sync_stop PCM ops (Jaroslav Kysela) [2017320]
- ALSA: ice1724: Remove superfluous loop over model table (Jaroslav Kysela) [2017320]
- ALSA: hda/ca0132: remove redundant initialization of variable status (Jaroslav Kysela) [2017320]
- ASoC: amd: fix spelling mistakes (Jaroslav Kysela) [2017320]
- ASoC: tlv320aic32x4: Fix TAS2505/TAS2521 channel count (Jaroslav Kysela) [2017320]
- ASoC: fsl_xcvr: Omit superfluous error message in fsl_xcvr_probe() (Jaroslav Kysela) [2017320]
- ASoC: sh: rcar: dma: : use proper DMAENGINE API for termination (Jaroslav Kysela) [2017320]
- ASoC: wm_adsp: Remove pointless string comparison (Jaroslav Kysela) [2017320]
- ASoC: codecs: wcd938x: fix returnvar.cocci warnings (Jaroslav Kysela) [2017320]
- ASoC: atmel: ATMEL drivers don't need HAS_DMA (Jaroslav Kysela) [2017320]
- ASoC: ti: delete some dead code in omap_abe_probe() (Jaroslav Kysela) [2017320]
- ASoC: atmel: fix spelling mistakes (Jaroslav Kysela) [2017320]
- ASoC: Intel: sof_cs42l42: use helper function to get bclk frequency (Jaroslav Kysela) [2017320]
- ASoC: SOF: add a helper to get topology configured bclk (Jaroslav Kysela) [2017320]
- ASoC: Intel: soc-acpi: add support for SoundWire of TGL-H-RVP (Jaroslav Kysela) [2017320]
- ASoC: mediatek: mt8183: Fix Unbalanced pm_runtime_enable in mt8183_afe_pcm_dev_probe (Jaroslav Kysela) [2017320]
- ASoC: mediatek: mt8192:Fix Unbalanced pm_runtime_enable in mt8192_afe_pcm_dev_probe (Jaroslav Kysela) [2017320]
- ASoC: ti: davinci-mcasp: Add support for the OMAP4 version of McASP (Jaroslav Kysela) [2017320]
- ASoC: ti: davinci-mcasp: Fix DIT mode support (Jaroslav Kysela) [2017320]

* Thu Feb 17 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-64.el9]
- igc: Fix TX timestamp support for non-MSI-X platforms (Corinna Vinschen) [2040335]
- igc: Do not enable crosstimestamping for i225-V models (Corinna Vinschen) [2040335]
- igc: Fix typo in i225 LTR functions (Corinna Vinschen) [2040335]
- igc: enable XDP metadata in driver (Corinna Vinschen) [2040335]
- igc: AF_XDP zero-copy metadata adjust breaks SKBs on XDP_PASS (Corinna Vinschen) [2040335]
- igc: Change Device Reset to Port Reset (Corinna Vinschen) [2040335]
- igc: Add new device ID (Corinna Vinschen) [2040335]
- igc: Remove media type checking on the PHY initialization (Corinna Vinschen) [2040335]
- igc: Update I226_K device ID (Corinna Vinschen) [2040335]
- net: intel: igc_ptp: fix build for UML (Corinna Vinschen) [2040335]
- igc: fix tunnel offloading (Corinna Vinschen) [2040335]
- igc: Add support for CBS offloading (Corinna Vinschen) [2040335]
- igc: Simplify TSN flags handling (Corinna Vinschen) [2040335]
- igc: Use default cycle 'start' and 'end' values for queues (Corinna Vinschen) [2040335]
- igc: Add support for PTP getcrosststamp() (Corinna Vinschen) [2040335]
- igc: Enable PCIe PTM (Corinna Vinschen) [2040335]
- igc: Increase timeout value for Speed 100/1000/2500 (Corinna Vinschen) [2040335]
- igc: Set QBVCYCLET_S to 0 for TSN Basic Scheduling (Corinna Vinschen) [2040335]
- igc: Remove phy->type checking (Corinna Vinschen) [2040335]
- igc: Remove _I_PHY_ID checking (Corinna Vinschen) [2040335]
- igc: Check if num of q_vectors is smaller than max before array access (Corinna Vinschen) [2040335]
- Revert "igc: Export LEDs" (Corinna Vinschen) [2040335]
- igc: Export LEDs (Corinna Vinschen) [2040335]
- igc: Make flex filter more flexible (Corinna Vinschen) [2040335]
- igc: Allow for Flex Filters to be installed (Corinna Vinschen) [2040335]
- igc: Integrate flex filter into ethtool ops (Corinna Vinschen) [2040335]
- igc: Add possibility to add flex filter (Corinna Vinschen) [2040335]
- EDAC/i10nm: Retrieve and print retry_rd_err_log registers (Aristeu Rozanski) [1998360]
- nvme-fabrics: fix state check in nvmf_ctlr_matches_baseopts() (Gopal Tiwari) [2043756]
- scsi: reserve space in structures for KABI (Ewan D. Milne) [2044443]
- vt_kdsetmode: extend console locking (John W. Linville) [2003820]
- ice: Fix problems with DSCP QoS implementation (Jonathan Toppins) [2032582]
- ice: Fix race conditions between virtchnl handling and VF ndo ops (Jonathan Toppins) [2032582]
- ice: Fix not stopping Tx queues for VFs (Jonathan Toppins) [2032582]
- ice: Fix replacing VF hardware MAC to existing MAC filter (Jonathan Toppins) [2032582]
- ice: Remove toggling of antispoof for VF trusted promiscuous mode (Jonathan Toppins) [2032582]
- ice: Fix VF true promiscuous mode (Jonathan Toppins) [2032582]
- ice: Remove boolean vlan_promisc flag from function (Jonathan Toppins) [2032582]
- ice: check whether PTP is initialized in ice_ptp_release() (Jonathan Toppins) [2032582]
- ice: Respond to a NETDEV_UNREGISTER event for LAG (Jonathan Toppins) [2032582]
- ice: use devm_kcalloc() instead of devm_kzalloc() (Jonathan Toppins) [2032582]
- ice: Make use of the helper function devm_add_action_or_reset() (Jonathan Toppins) [2032582]
- ice: fix software generating extra interrupts (Jonathan Toppins) [2032582]
- ice: fix rate limit update after coalesce change (Jonathan Toppins) [2032582]
- ice: update dim usage and moderation (Jonathan Toppins) [2032582]
- ice: Add support for VF rate limiting (Jonathan Toppins) [2032582]
- ice: Add missing E810 device ids (Jonathan Toppins) [2032582]
- ice: make use of ice_for_each_* macros (Jonathan Toppins) [2032582]
- ice: split ice_ring onto Tx/Rx separate structs (Jonathan Toppins) [2032582]
- ice: move ice_container_type onto ice_ring_container (Jonathan Toppins) [2032582]
- ice: remove ring_active from ice_ring (Jonathan Toppins) [2032582]
- ice: Print the api_patch as part of the fw.mgmt.api (Jonathan Toppins) [2032582]
- ice: fix getting UDP tunnel entry (Jonathan Toppins) [1978828 2032582]
- ice: Avoid crash from unnecessary IDA free (Jonathan Toppins) [2032582]
- ice: Fix failure to re-add LAN/RDMA Tx queues (Jonathan Toppins) [2032582]
- ice: fix locking for Tx timestamp tracking flush (Jonathan Toppins) [2032582]
- ice: Prefer kcalloc over open coded arithmetic (Jonathan Toppins) [2032582]
- ice: Fix macro name for IPv4 fragment flag (Jonathan Toppins) [2032582]
- ice: refactor devlink getter/fallback functions to void (Jonathan Toppins) [2032582]
- ice: Fix link mode handling (Jonathan Toppins) [2032582]
- ice: Add feature bitmap, helpers and a check for DSCP (Jonathan Toppins) [2032582]
- ice: Add DSCP support (Jonathan Toppins) [2032582]
- ice: Correctly deal with PFs that do not support RDMA (Jonathan Toppins) [2032582]
- ice: add lock around Tx timestamp tracker flush (Jonathan Toppins) [2032582]
- ice: remove dead code for allocating pin_config (Jonathan Toppins) [2032582]

* Thu Feb 17 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-63.el9]
- wireguard: ratelimiter: use kvcalloc() instead of kvzalloc() (Hangbin Liu) [2041408]
- wireguard: receive: drop handshakes if queue lock is contended (Hangbin Liu) [2041408]
- wireguard: receive: use ring buffer for incoming handshakes (Hangbin Liu) [2041408]
- wireguard: allowedips: add missing __rcu annotation to satisfy sparse (Hangbin Liu) [2041408]
- ionic: Initialize the 'lif->dbid_inuse' bitmap (Jonathan Toppins) [2039988]
- ionic: tame the filter no space message (Jonathan Toppins) [2013549 2039988]
- ionic: allow adminq requests to override default error message (Jonathan Toppins) [2013549 2039988]
- ionic: handle vlan id overflow (Jonathan Toppins) [2013549 2039988]
- ionic: generic filter delete (Jonathan Toppins) [2013549 2039988]
- ionic: generic filter add (Jonathan Toppins) [2013549 2039988]
- ionic: add generic filter search (Jonathan Toppins) [2013549 2039988]
- ionic: remove mac overflow flags (Jonathan Toppins) [2013549 2039988]
- ionic: move lif mac address functions (Jonathan Toppins) [2013549 2039988]
- ionic: add filterlist to debugfs (Jonathan Toppins) [2013549 2039988]
- ionic: add lif param to ionic_qcq_disable (Jonathan Toppins) [2039988]
- ionic: have ionic_qcq_disable decide on sending to hardware (Jonathan Toppins) [2039988]
- ionic: add polling to adminq wait (Jonathan Toppins) [2039988]
- ionic: widen queue_lock use around lif init and deinit (Jonathan Toppins) [2039988]
- ionic: move lif mutex setup and delete (Jonathan Toppins) [2039988]
- ionic: check for binary values in FW ver string (Jonathan Toppins) [2039988]
- ionic: remove debug stats (Jonathan Toppins) [2039988]
- ionic: don't remove netdev->dev_addr when syncing uc list (Jonathan Toppins) [2039988]
- ionic: move filter sync_needed bit set (Jonathan Toppins) [2039988]
- ionic: fix gathering of debug stats (Jonathan Toppins) [2039988]
- ionic: fix a sleeping in atomic bug (Jonathan Toppins) [2039988]
- ionic: fix double use of queue-lock (Jonathan Toppins) [2039988]
- ionic: recreate hwstamp queues on ifup (Jonathan Toppins) [2039988]
- ionic: pull hwstamp queue_lock up a level (Jonathan Toppins) [2039988]
- ionic: add queue lock around open and stop (Jonathan Toppins) [2039988]
- ionic: fill mac addr earlier in add_addr (Jonathan Toppins) [2039988]
- ionic: squelch unnecessary fw halted message (Jonathan Toppins) [2039988]
- ionic: fire watchdog again after fw_down (Jonathan Toppins) [2039988]
- ionic: handle mac filter overflow (Jonathan Toppins) [2039988]
- ionic: refactor ionic_lif_addr to remove a layer (Jonathan Toppins) [2039988]
- ionic: sync the filters in the work task (Jonathan Toppins) [2039988]
- ionic: flatten calls to set-rx-mode (Jonathan Toppins) [2039988]
- ionic: remove old work task types (Jonathan Toppins) [2039988]
- ionic: add function tag to debug string (Jonathan Toppins) [2039988]
- ionic: enable rxhash only with multiple queues (Jonathan Toppins) [2039988]
- ionic: block some ethtool operations when fw in reset (Jonathan Toppins) [2039988]
- ionic: remove unneeded comp union fields (Jonathan Toppins) [2039988]
- ionic: increment num-vfs before configure (Jonathan Toppins) [2039988]
- ionic: use fewer inits on the buf_info struct (Jonathan Toppins) [2039988]
- ionic: init reconfig err to 0 (Jonathan Toppins) [2039988]
- ionic: print firmware version on identify (Jonathan Toppins) [2039988]
- ionic: monitor fw status generation (Jonathan Toppins) [2039988]
- ionic: minimize resources when under kdump (Jonathan Toppins) [2039988]
- ionic: drop useless check of PCI driver data validity (Jonathan Toppins) [2039988]

* Wed Feb 16 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-62.el9]
- ibmvnic: remove unused defines (Diego Domingos) [2047921]
- ibmvnic: Update driver return codes (Diego Domingos) [2047921]
- powerpc/fadump: opt out from freeing pages on cma activation failure (Diego Domingos) [2040289]
- mm/cma: provide option to opt out from exposing pages on activation failure (Diego Domingos) [2040289]
- firmware: smccc: Fix check for ARCH_SOC_ID not implemented (Vitaly Kuznetsov) [2052908]
- rcu: Tighten rcu_advance_cbs_nowake() checks (Daniel Vacek) [2026991]
- redhat/configs: Disable CONFIG_MACINTOSH_DRIVERS (Prarit Bhargava) [2053028]
- ibmvnic: remove unused ->wait_capability (Diego Domingos) [2047928]
- ibmvnic: don't spin in tasklet (Diego Domingos) [2047928]
- ibmvnic: init ->running_cap_crqs early (Diego Domingos) [2047928]
- ibmvnic: Allow extra failures before disabling (Diego Domingos) [2047928]
- s390/pv: fix the forcing of the swiotlb (Thomas Huth) [2051581]
- scsi: vmw_pvscsi: Set residual data length conditionally (Cathy Avery) [2048178]
- selinux: fix double free of cond_list on error paths (Ondrej Mosnacek) [2052439]
- selinux: fix NULL-pointer dereference when hashtab allocation fails (Ondrej Mosnacek) [2052436]
- isdn: cpai: check ctr->cnr to avoid array index out of bound (Chris von Recklinghausen) [2016492] {CVE-2021-43389}
- mm/hwpoison: fix unpoison_memory() (Aristeu Rozanski) [1972220]
- mm/hwpoison: remove MF_MSG_BUDDY_2ND and MF_MSG_POISONED_HUGE (Aristeu Rozanski) [1972220]
- mm/hwpoison: mf_mutex for soft offline and unpoison (Aristeu Rozanski) [1972220]
- mm/hwpoison: clear MF_COUNT_INCREASED before retrying get_any_page() (Aristeu Rozanski) [1972220]
- mm, hwpoison: fix condition in free hugetlb page path (Aristeu Rozanski) [1972220]
- filemap: remove PageHWPoison check from next_uptodate_page() (Aristeu Rozanski) [1972220]
- mm: hwpoison: handle non-anonymous THP correctly (Aristeu Rozanski) [1972220]
- mm: hwpoison: refactor refcount check handling (Aristeu Rozanski) [1972220]
- mm: filemap: coding style cleanup for filemap_map_pmd() (Aristeu Rozanski) [1972220]
- scsi: bnx2fc: Make bnx2fc_recv_frame() mp safe (John Meneghini) [2031648]
- scsi: bnx2fc: Flush destroy_work queue before calling bnx2fc_interface_put() (John Meneghini) [2006606]
- redhat/configs: Enable CONFIG_TEST_BPF (Viktor Malik) [2035168]
- ext4: fix potential NULL pointer dereference in ext4_fill_super() (Lukas Czerner) [2051466]
- netfilter: ipset: Emit deprecation warning at set creation time (Phil Sutter) [2048194]
- redhat: move CONFIG_ARM64_MTE to aarch64 config directory (Herton R. Krzesinski)
- cgroup/cpuset: Fix "suspicious RCU usage" lockdep warning (Waiman Long) [1996015]
- cpuset: Fix the bug that subpart_cpus updated wrongly in update_cpumask() (Waiman Long) [1996015]
- net ticp:fix a kernel-infoleak in __tipc_sendmsg() (Xin Long) [2050039]
- tipc: discard MSG_CRYPTO msgs when key_exchange_enabled is not set (Xin Long) [2050039]
- tipc: delete the unlikely branch in tipc_aead_encrypt (Xin Long) [2050039]
- blktrace: switch trace spinlock to a raw spinlock (Wander Lairson Costa) [2047971]
- NFSv4.1: handle NFS4ERR_NOSPC by CREATE_SESSION (Steve Dickson) [2027447]
- igb: fix deadlock caused by taking RTNL in RPM resume path (Corinna Vinschen) [2040312]
- igb: Fix removal of unicast MAC filters of VFs (Corinna Vinschen) [2040312]
- igb: fix netpoll exit with traffic (Corinna Vinschen) [2040312]
- igb: unbreak I2C bit-banging on i350 (Corinna Vinschen) [2040312]
- igb: Avoid memcpy() over-reading of ETH_SS_STATS (Corinna Vinschen) [2040312]
- igb: Add counter to i21x doublecheck (Corinna Vinschen) [2040312]
- net: create netdev->dev_addr assignment helpers (Josef Oskera) [2030720]

* Wed Feb 16 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-61.el9]
- Enable KUNIT tests for redhat kernel-modules-internal (Nico Pache) [2048326]
- kasan: test: fix compatibility with FORTIFY_SOURCE (Nico Pache) [2048326]
- kasan: test: silence intentional read overflow warnings (Nico Pache) [2048326]
- kasan: test: bypass __alloc_size checks (Nico Pache) [2048326]
- mm/damon/vaddr-test: split a test function having >1024 bytes frame size (Nico Pache) [2048326]
- lib: Introduce CONFIG_MEMCPY_KUNIT_TEST (Nico Pache) [2048326]
- nvme-rdma: fix possible use-after-free in transport error_recovery work (Chris Leech) [1994618 2033414]
- nvme-tcp: fix possible use-after-free in transport error_recovery work (Chris Leech) [1994618 2033414]
- nvme: fix a possible use-after-free in controller reset during load (Chris Leech) [1994618 2033414]
- redhat/configs: enable CONFIG_CMA on aarch64 as tech-preview (David Hildenbrand) [2043141]
- redhat/configs: simplify CONFIG_CMA_AREAS (David Hildenbrand) [2043141]
- redhat/configs: simplify CONFIG_CMA_DEBUG (David Hildenbrand) [2043141]
- redhat/configs: simplify CONFIG_CMA_DEBUGFS (David Hildenbrand) [2043141]
- bpf: Fix kernel address leakage in atomic fetch (Jiri Olsa) [2046636] {CVE-2021-4203}
- IB/rdmavt: Validate remote_addr during loopback atomic tests (Kamal Heib) [2032114]
- [s390] scsi: zfcp: Fix failed recovery on gone remote port with non-NPIV FCP devices (Mete Durlu) [2049016]
- [s390] s390/cpumf: Support for CPU Measurement Sampling Facility LS bit (Mete Durlu) [2048979]
- [s390] s390/cpumf: Support for CPU Measurement Facility CSVN 7 (Mete Durlu) [2048979]
- net: openvswitch: Fix ct_state nat flags for conns arriving from tc (Antoine Tenart) [2045048]
- net: openvswitch: Fix matching zone id for invalid conns arriving from tc (Antoine Tenart) [2045048]
- net/sched: flow_dissector: Fix matching on zone id for invalid conns (Antoine Tenart) [2045048]
- net/sched: Extend qdisc control block with tc control block (Antoine Tenart) [2045048]
- openvswitch: fix sparse warning incorrect type (Antoine Tenart) [2045048]
- openvswitch: fix alignment issues (Antoine Tenart) [2045048]
- openvswitch: update kdoc OVS_DP_ATTR_PER_CPU_PIDS (Antoine Tenart) [2045048]
- openvswitch: Introduce per-cpu upcall dispatch (Antoine Tenart) [2045048]
- netfilter: fix regression in looped (broad|multi)cast's MAC handling (Florian Westphal) [2044272]
- selftests: nft_concat_range: add test for reload with no element add/del (Florian Westphal) [2044272]
- selftests: netfilter: Add correctness test for mac,net set type (Florian Westphal) [2044272]
- netfilter: conntrack: don't increment invalid counter on NF_REPEAT (Florian Westphal) [2044272]
- netfilter: nft_set_pipapo: allocate pcpu scratch maps on clone (Florian Westphal) [2044272]
- netfilter: nft_payload: do not update layer 4 checksum when mangling fragments (Florian Westphal) [2044272]
- netfilter: bridge: add support for pppoe filtering (Florian Westphal) [2044272]
- netfilter: nf_tables: fix use-after-free in nft_set_catchall_destroy() (Florian Westphal) [2044272]
- netfilter: conntrack: annotate data-races around ct->timeout (Florian Westphal) [2044272]
- netfilter: nft_exthdr: break evaluation if setting TCP option fails (Florian Westphal) [2044272]
- nft_set_pipapo: Fix bucket load in AVX2 lookup routine for six 8-bit groups (Florian Westphal) [2044272]
- tracing: Tag trace_percpu_buffer as a percpu pointer (Jerome Marchand) [2035164]
- tracing: Fix check for trace_percpu_buffer validity in get_trace_buf() (Jerome Marchand) [2035164]
- selftests: cgroup: Test open-time cgroup namespace usage for migration checks (Chris von Recklinghausen) [2035768] {CVE-2021-4197}
- selftests: cgroup: Test open-time credential usage for migration checks (Chris von Recklinghausen) [2035768] {CVE-2021-4197}
- selftests: cgroup: Make cg_create() use 0755 for permission instead of 0644 (Chris von Recklinghausen) [2035768] {CVE-2021-4197}
- cgroup: Use open-time cgroup namespace for process migration perm checks (Chris von Recklinghausen) [2035768] {CVE-2021-4197}
- cgroup: Allocate cgroup_file_ctx for kernfs_open_file->priv (Chris von Recklinghausen) [2035768] {CVE-2021-4197}
- cgroup: Use open-time credentials for process migraton perm checks (Chris von Recklinghausen) [2035768] {CVE-2021-4197}
- x86/sched: Decrease further the priorities of SMT siblings (Prarit Bhargava) [1971926]

* Tue Feb 15 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-60.el9]
- crypto: jitter - add oversampling of noise source (Herbert Xu) [2036816]
- Revert "ipv6: Honor all IPv6 PIO Valid Lifetime values" (Guillaume Nault) [2027560]
- Change "-auto" suffix to fix CI automotive pipeline issues (Julio Faracco)
- nvme: drop unused variable ctrl in nvme_setup_cmd (John Meneghini) [2044616]
- nvme: increment request genctr on completion (John Meneghini) [2044616]
- nvme-pci: Fix abort command id (John Meneghini) [2044616]
- nvme: add command id quirk for apple controllers (John Meneghini) [2044616]
- nvme: move nvme_multi_css into nvme.h (John Meneghini) [2044616]
- nvme: code command_id with a genctr for use-after-free validation (John Meneghini) [2044616]
- nvme-pci: limit maximum queue depth to 4095 (John Meneghini) [2044616]
- selftests: Calculate udpgso segment count without header adjustment (Xin Long) [2044129]
- udp: using datalen to cap ipv6 udp max gso segments (Xin Long) [2044129]
- inet_diag: fix kernel-infoleak for UDP sockets (Xin Long) [2044129]
- udp: using datalen to cap max gso segments (Xin Long) [2044129]
- sctp: hold endpoint before calling cb in sctp_transport_lookup_process (Xin Long) [2043823]
- sctp: use call_rcu to free endpoint (Xin Long) [2043823]
- sctp: move hlist_node and hashent out of sctp_ep_common (Xin Long) [2043823]
- sctp: make the raise timer more simple and accurate (Xin Long) [2043823]
- nfsd: fix use-after-free due to delegation race (Benjamin Coddington) [1991929]
- bonding: Fix extraction of ports from the packet headers (Jonathan Toppins) [2042548]
- bonding: fix ad_actor_system option setting to default (Jonathan Toppins) [2042548]
- bonding: make tx_rebalance_counter an atomic (Jonathan Toppins) [2042548]
- bonding: Fix a use-after-free problem when bond_sysfs_slave_add() failed (Jonathan Toppins) [2042548]
- bonding: 3ad: pass parameter bond_params by reference (Jonathan Toppins) [2042548]
- bonding: complain about missing route only once for A/B ARP probes (Jonathan Toppins) [2042548]
- bonding: improve nl error msg when device can't be enslaved because of IFF_MASTER (Jonathan Toppins) [2042548]
- bonding: combine netlink and console error messages (Jonathan Toppins) [2042548]
- net, bonding: Refactor bond_xmit_hash for use with xdp_buff (Jonathan Toppins) [2042548]
- net: bonding: bond_alb: Remove the dependency on ipx network layer (Jonathan Toppins) [2042548]
- bonding: add new option lacp_active (Jonathan Toppins) [1951951 2042548]
- bonding: 3ad: fix the concurrency between __bond_release_one() and bond_3ad_state_machine_handler() (Jonathan Toppins) [2042548]
- fget: clarify and improve __fget_files() implementation (Miklos Szeredi) [2030418] {CVE-2021-4083}
- fget: check that the fd still exists after getting a ref to it (Miklos Szeredi) [2030418] {CVE-2021-4083}
- ipv6: Continue processing multipath route even if gateway attribute is invalid (Hangbin Liu) [2041401]
- ipv6: Check attribute length for RTA_GATEWAY when deleting multipath route (Hangbin Liu) [2041401]
- ipv6: Do cleanup if attribute validation fails in multipath route (Hangbin Liu) [2041401]
- ipv6: Check attribute length for RTA_GATEWAY in multipath route (Hangbin Liu) [2041401]
- ipv6: fix memory leak in fib6_rule_suppress (Hangbin Liu) [2041401]
- net: nexthop: reduce rcu synchronizations when replacing resilient groups (Hangbin Liu) [2041401]
- net: nexthop: release IPv6 per-cpu dsts when replacing a nexthop group (Hangbin Liu) [2041401]
- net: ipv6: add fib6_nh_release_dsts stub (Hangbin Liu) [2041401]
- ipv6: fix typos in __ip6_finish_output() (Hangbin Liu) [2041401]
- igbvf: Refactor trace (Corinna Vinschen) [2040322]
- igbvf: fix double free in `igbvf_probe` (Corinna Vinschen) [2040322]
- bnx2x: Fix enabling network interfaces without VFs (Manish Chopra) [1998304]
- tun: fix bonding active backup with arp monitoring (Jonathan Toppins) [2050837]

* Fri Feb 11 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-59.el9]
- gfs2: Fix gfs2_release for non-writers regression (Bob Peterson) [2030397]
- gfs2: gfs2_create_inode rework (Andreas Gruenbacher) [2002803]
- gfs2: gfs2_inode_lookup rework (Andreas Gruenbacher) [2002803]
- gfs2: gfs2_inode_lookup cleanup (Andreas Gruenbacher) [2002803]
- gfs2: Fix remote demote of weak glock holders (Andreas Gruenbacher) [1958140]
- gfs2: Fix unused value warning in do_gfs2_set_flags() (Andreas Gruenbacher) [1958140]
- gfs2: Fix glock_hash_walk bugs (Andreas Gruenbacher) [2008541]
- gfs2: Cancel remote delete work asynchronously (Bob Peterson) [2002803]
- gfs2: set glock object after nq (Bob Peterson) [1998303]
- gfs2: remove RDF_UPTODATE flag (Bob Peterson) [1998303]
- gfs2: Eliminate GIF_INVALID flag (Bob Peterson) [1998303]
- gfs2: Fix atomic bug in gfs2_instantiate (Andreas Gruenbacher) [1998303]
- gfs2: fix GL_SKIP node_scope problems (Bob Peterson) [1998303]
- gfs2: split glock instantiation off from do_promote (Bob Peterson) [1998303]
- gfs2: further simplify do_promote (Bob Peterson) [1998303]
- gfs2: re-factor function do_promote (Bob Peterson) [1998303]
- gfs2: Remove 'first' trace_gfs2_promote argument (Andreas Gruenbacher) [1998303]
- gfs2: change go_lock to go_instantiate (Bob Peterson) [1998303]
- gfs2: dump glocks from gfs2_consist_OBJ_i (Bob Peterson) [1998303]
- gfs2: dequeue iopen holder in gfs2_inode_lookup error (Bob Peterson) [2006870]
- gfs2: Save ip from gfs2_glock_nq_init (Bob Peterson) [1998303]
- gfs2: Allow append and immutable bits to coexist (Bob Peterson) [1998303]
- gfs2: Switch some BUG_ON to GLOCK_BUG_ON for debug (Bob Peterson) [1998303]
- gfs2: move GL_SKIP check from glops to do_promote (Bob Peterson) [1998303]
- gfs2: Add GL_SKIP holder flag to dump_holder (Bob Peterson) [1998303]
- gfs2: remove redundant check in gfs2_rgrp_go_lock (Bob Peterson) [1998303]
- gfs2: Fix mmap + page fault deadlocks for direct I/O (Andreas Gruenbacher) [1958140]
- iov_iter: Introduce nofault flag to disable page faults (Andreas Gruenbacher) [1958140]
- gup: Introduce FOLL_NOFAULT flag to disable page faults (Andreas Gruenbacher) [1958140]
- iomap: Add done_before argument to iomap_dio_rw (Andreas Gruenbacher) [1958140]
- iomap: Support partial direct I/O on user copy failures (Andreas Gruenbacher) [1958140]
- iomap: Fix iomap_dio_rw return value for user copies (Andreas Gruenbacher) [1958140]
- iomap: support reading inline data from non-zero pos (Andreas Gruenbacher) [1958140]
- gfs2: Only dereference i->iov when iter_is_iovec(i) (Andreas Gruenbacher) [1958140]
- gfs2: Prevent endless loops in gfs2_file_buffered_write (Andreas Gruenbacher) [1958140]
- gfs2: Fix mmap + page fault deadlocks for buffered I/O (Andreas Gruenbacher) [1958140]
- gfs2: Eliminate ip->i_gh (Andreas Gruenbacher) [1958140]
- gfs2: Move the inode glock locking to gfs2_file_buffered_write (Andreas Gruenbacher) [1958140]
- gfs2: Fix "Introduce flag for glock holder auto-demotion" (Andreas Gruenbacher) [1958140]
- gfs2: Introduce flag for glock holder auto-demotion (Bob Peterson) [1958140]
- gfs2: Clean up function may_grant (Andreas Gruenbacher) [1958140]
- gfs2: Add wrapper for iomap_file_buffered_write (Andreas Gruenbacher) [1958140]
- iov_iter: Introduce fault_in_iov_iter_writeable (Andreas Gruenbacher) [1958140]
- iov_iter: Turn iov_iter_fault_in_readable into fault_in_iov_iter_readable (Andreas Gruenbacher) [1958140]
- gup: Turn fault_in_pages_{readable,writeable} into fault_in_{readable,writeable} (Andreas Gruenbacher) [1958140]
- powerpc/kvm: Fix kvm_use_magic_page (Andreas Gruenbacher) [1958140]
- iov_iter: Fix iov_iter_get_pages{,_alloc} page fault return value (Andreas Gruenbacher) [1958140]
- gfs2: Fix length of holes reported at end-of-file (Andreas Gruenbacher) [2029955]
- gfs2: release iopen glock early in evict (Bob Peterson) [2009406]
- gfs2: Switch to may_setattr in gfs2_setattr (Bob Peterson) [2029947]
- fs: Move notify_change permission checks into may_setattr (Bob Peterson) [2029947]
- gfs2: Remove redundant check from gfs2_glock_dq (Bob Peterson) [2030090]
- gfs2: Delay withdraw from atomic context (Bob Peterson) [2030090]
- gfs2: nit: gfs2_drop_inode shouldn't return bool (Bob Peterson) [2030090]
- gfs2: Eliminate vestigial HIF_FIRST (Bob Peterson) [2030090]
- gfs2: Make recovery error more readable (Bob Peterson) [2030090]
- gfs2: Don't release and reacquire local statfs bh (Bob Peterson) [2030090]
- gfs2: init system threads before freeze lock (Bob Peterson) [2030090]
- gfs2: tiny cleanup in gfs2_log_reserve (Bob Peterson) [2030090]
- gfs2: trivial clean up of gfs2_ail_error (Bob Peterson) [2030090]
- gfs2: be more verbose replaying invalid rgrp blocks (Bob Peterson) [2030090]
- iomap: remove the iomap arguments to ->page_{prepare,done} (Andreas Gruenbacher) [1958140]
- gfs2: Fix glock recursion in freeze_go_xmote_bh (Bob Peterson) [2030090]
- gfs2: Fix memory leak of object lsi on error return path (Andreas Gruenbacher) [2030090]
- x86/sgx: Fix minor documentation issues (Vladis Dronov) [1920028]
- selftests/sgx: Add test for multiple TCS entry (Vladis Dronov) [1920028]
- selftests/sgx: Enable multiple thread support (Vladis Dronov) [1920028]
- selftests/sgx: Add page permission and exception test (Vladis Dronov) [1920028]
- selftests/sgx: Rename test properties in preparation for more enclave tests (Vladis Dronov) [1920028]
- selftests/sgx: Provide per-op parameter structs for the test enclave (Vladis Dronov) [1920028]
- selftests/sgx: Add a new kselftest: Unclobbered_vdso_oversubscribed (Vladis Dronov) [1920028]
- selftests/sgx: Move setup_test_encl() to each TEST_F() (Vladis Dronov) [1920028]
- selftests/sgx: Encpsulate the test enclave creation (Vladis Dronov) [1920028]
- selftests/sgx: Dump segments and /proc/self/maps only on failure (Vladis Dronov) [1920028]
- selftests/sgx: Create a heap for the test enclave (Vladis Dronov) [1920028]
- selftests/sgx: Make data measurement for an enclave segment optional (Vladis Dronov) [1920028]
- selftests/sgx: Assign source for each segment (Vladis Dronov) [1920028]
- selftests/sgx: Fix a benign linker warning (Vladis Dronov) [1920028]
- x86/sgx: Fix free page accounting (Vladis Dronov) [1920028]
- x86/sgx: Add check for SGX pages to ghes_do_memory_failure() (Vladis Dronov) [1920028]
- x86/sgx: Add hook to error injection address validation (Vladis Dronov) [1920028]
- x86/sgx: Hook arch_memory_failure() into mainline code (Vladis Dronov) [1920028]
- x86/sgx: Add SGX infrastructure to recover from poison (Vladis Dronov) [1920028]
- x86/sgx: Initial poison handling for dirty and free pages (Vladis Dronov) [1920028]
- x86/sgx: Add infrastructure to identify SGX EPC pages (Vladis Dronov) [1920028]
- x86/sgx: Add new sgx_epc_page flag bit to mark free pages (Vladis Dronov) [1920028]

* Wed Feb 09 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-58.el9]
- KVM: nVMX: Allow VMREAD when Enlightened VMCS is in use (Vitaly Kuznetsov) [2027639]
- KVM: nVMX: Implement evmcs_field_offset() suitable for handle_vmread() (Vitaly Kuznetsov) [2027639]
- KVM: nVMX: Rename vmcs_to_field_offset{,_table} (Vitaly Kuznetsov) [2027639]
- KVM: nVMX: eVMCS: Filter out VM_EXIT_SAVE_VMX_PREEMPTION_TIMER (Vitaly Kuznetsov) [2027639]
- KVM: nVMX: Also filter MSR_IA32_VMX_TRUE_PINBASED_CTLS when eVMCS (Vitaly Kuznetsov) [2027639]
- KVM: nVMX: Use INVALID_GPA for pointers used in nVMX. (Vitaly Kuznetsov) [2027639]
- x86/kvm: Always inline evmcs_write64() (Vitaly Kuznetsov) [2027639]
- [s390] s390/pci: move pseudo-MMIO to prevent MIO overlap (Mete Durlu) [2047755]
- CI: Update the RHEL9-private pipeline names to new schema (Veronika Kabatova)
- CI: Sync RHEL9-RT-baseline with c9s-RT-baseline (Veronika Kabatova)
- CI: Add kpet_tree_family to RT check config (Veronika Kabatova)
- selftests/bpf: Enlarge select() timeout for test_maps (Felix Maurer) [2032718]
- netfilter: nft_reject_bridge: Fix for missing reply from prerouting (Phil Sutter) [2044848]
- gre: Don't accidentally set RTO_ONLINK in gre_fill_metadata_dst() (Guillaume Nault) [2047202]
- net: fix use-after-free in tw_timer_handler (Guillaume Nault) [2047202]
- inet: use #ifdef CONFIG_SOCK_RX_QUEUE_MAPPING consistently (Guillaume Nault) [2047202]
- ipv4: convert fib_num_tclassid_users to atomic_t (Guillaume Nault) [2047202]
- vfs: fs_context: fix up param length parsing in legacy_parse_param (Carlos Maiolino) [2040587] {CVE-2022-0185}
- sched/pelt: Relax the sync of load_sum with load_avg (Phil Auld) [2045052]
- sched/pelt: Relax the sync of runnable_sum with runnable_avg (Phil Auld) [2045052]
- sched/pelt: Continue to relax the sync of util_sum with util_avg (Phil Auld) [2045052]
- sched/pelt: Relax the sync of util_sum with util_avg (Phil Auld) [2045052]
- pinctrl: amd: Fix wakeups when IRQ is shared with SCI (Renjith Pananchikkal) [2039350]
- platform/x86: amd-pmc: only use callbacks for suspend (David Arcari) [2016041]
- platform/x86: amd-pmc: Add support for AMD Smart Trace Buffer (David Arcari) [2016041]
- platform/x86: amd-pmc: Simplify error handling and store the pci_dev in amd_pmc_dev structure (David Arcari) [2016041]
- platform/x86: amd-pmc: Fix s2idle failures on certain AMD laptops (David Arcari) [2016041]
- platform/x86: amd-pmc: Make CONFIG_AMD_PMC depend on RTC_CLASS (David Arcari) [2016041]
- platform/x86: amd-pmc: Drop check for valid alarm time (David Arcari) [2016041]
- platform/x86: amd-pmc: Downgrade dev_info message to dev_dbg (David Arcari) [2016041]
- platform/x86: amd-pmc: fix compilation without CONFIG_RTC_SYSTOHC_DEVICE (David Arcari) [2016041]
- platform/x86: amd-pmc: Add special handling for timer based S0i3 wakeup (David Arcari) [2016041]
- platform/x86: amd-pmc: adjust arguments for `amd_pmc_send_cmd` (David Arcari) [2016041]
- platform/x86: amd-pmc: Add alternative acpi id for PMC controller (David Arcari) [2016041]
- platform/x86: amd-pmc: Add a message to print resume time info (David Arcari) [2016041]
- platform/x86: amd-pmc: Send command to dump data after clearing OS_HINT (David Arcari) [2016041]
- platform/x86: amd-pmc: Fix compilation when CONFIG_DEBUGFS is disabled (David Arcari) [2016041]
- platform/x86: amd-pmc: Export Idlemask values based on the APU (David Arcari) [2016041]
- platform/x86: amd-pmc: Check s0i3 cycle status (David Arcari) [2016041]
- platform/x86: amd-pmc: Increase the response register timeout (David Arcari) [2016041]
- mm/page_alloc.c: do not warn allocation failure on zone DMA if no managed pages (Baoquan He) [2024381]
- dma/pool: create dma atomic pool only if dma zone has managed pages (Baoquan He) [2024381]
- mm_zone: add function to check if managed dma zone exists (Baoquan He) [2024381]
- PCI: hv: Add arm64 Hyper-V vPCI support (Vitaly Kuznetsov) [2024852]
- PCI: hv: Make the code arch neutral by adding arch specific interfaces (Vitaly Kuznetsov) [2024852]
- PCI: hv: Remove unnecessary use of %%hx (Vitaly Kuznetsov) [2024852]

* Tue Feb 08 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-57.el9]
- block: assign bi_bdev for cloned bios in blk_rq_prep_clone (Benjamin Marzinski) [2026948]
- dm sysfs: use default_groups in kobj_type (Benjamin Marzinski) [2043224]
- dm space map common: add bounds check to sm_ll_lookup_bitmap() (Benjamin Marzinski) [2043224]
- dm btree: add a defensive bounds check to insert_at() (Benjamin Marzinski) [2043224]
- dm btree remove: change a bunch of BUG_ON() calls to proper errors (Benjamin Marzinski) [2043224]
- dm btree spine: eliminate duplicate le32_to_cpu() in node_check() (Benjamin Marzinski) [2043224]
- dm btree spine: remove extra node_check function declaration (Benjamin Marzinski) [2043224]
- redhat: drop the RELEASED_KERNEL switch (Herton R. Krzesinski) [2037084 2045327]
- redhat: switch the kernel package to use certs from system-sb-certs (Herton R. Krzesinski) [2037084 2045327]
- mptcp: disable by default (Davide Caratti) [2044392]
- sch_api: Don't skip qdisc attach on ingress (Davide Caratti) [2044560]
- flow_offload: return EOPNOTSUPP for the unsupported mpls action type (Davide Caratti) [2044560]
- sch_cake: do not call cake_destroy() from cake_init() (Davide Caratti) [2044560]
- net/sched: fq_pie: prevent dismantle issue (Davide Caratti) [2044560]
- vrf: Reset IPCB/IP6CB when processing outbound pkts in vrf dev xmit (Antoine Tenart) [2044252]
- qla2xxx: Add new messaging (Ewan D. Milne) [2039070]
- nvme-fc: remove freeze/unfreeze around update_nr_hw_queues (Ewan D. Milne) [2030051]
- nvme-fc: avoid race between time out and tear down (Ewan D. Milne) [2030051]
- nvme-fc: update hardware queues before using them (Ewan D. Milne) [2030051]
- lpfc: Add new messaging (Ewan D. Milne) [2039068]
- tee: handle lookup of shm with reference count 0 (Chris von Recklinghausen) [2030754] {CVE-2021-44733}
- dma-buf: move dma-buf symbols into the DMA_BUF module namespace (Chris von Recklinghausen) [2030754] {CVE-2021-44733}
- tee: add sec_world_id to struct tee_shm (Chris von Recklinghausen) [2030754] {CVE-2021-44733}
- drm/i915/selftests: Do not use import_obj uninitialized (Chris von Recklinghausen) [2030754] {CVE-2021-44733}
- drm/gem: Provide drm_gem_fb_{vmap,vunmap}() (Chris von Recklinghausen) [2030754] {CVE-2021-44733}
- drm: Define DRM_FORMAT_MAX_PLANES (Chris von Recklinghausen) [2030754] {CVE-2021-44733}
- drm/i915/gem: Correct the locking and pin pattern for dma-buf (v8) (Chris von Recklinghausen) [2030754] {CVE-2021-44733}
- drm/gm12u320: Use framebuffer dma-buf helpers (Chris von Recklinghausen) [2030754] {CVE-2021-44733}
- drm/gud: Use framebuffer dma-buf helpers (Chris von Recklinghausen) [2030754] {CVE-2021-44733}
- drm/udl: Use framebuffer dma-buf helpers (Chris von Recklinghausen) [2030754] {CVE-2021-44733}
- drm/gem: Provide drm_gem_fb_{begin,end}_cpu_access() helpers (Chris von Recklinghausen) [2030754] {CVE-2021-44733}
- dmaengine: idxd: Add wq occupancy information to sysfs attribute (Julia Denham) [1971888]
- arch/x86: KABI structs and array padding (Prarit Bhargava) [2033081]
- hpsa: add new messaging (Tomas Henzl) [2028575]
- aacraid: add new messaging (Tomas Henzl) [2028574]
- mptsas: add new messaging (Tomas Henzl) [2027741]
- megaraid_sas: add new messaging (Tomas Henzl) [2027741]
- mpt3sas: Add new messaging (Tomas Henzl) [2027741]
- scsi: mpi3mr: Use scnprintf() instead of snprintf() (Tomas Henzl) [1876005]
- scsi: mpi3mr: Clean up mpi3mr_print_ioc_info() (Tomas Henzl) [1876005]
- scsi: mpi3mr: Set up IRQs in resume path (Tomas Henzl) [1876005]
- scsi: mpi3mr: Use the proper SCSI midlayer interfaces for PI (Tomas Henzl) [1876005]

* Mon Feb 07 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-56.el9]
- KVM: VMX: switch blocked_vcpu_on_cpu_lock to raw spinlock (Marcelo Tosatti) [2034007]
- x86/hyperv: Properly deal with empty cpumasks in hyperv_flush_tlb_multi() (Vitaly Kuznetsov) [2035993]
- tcp: add missing htmldocs for skb->ll_node and sk->defer_list (Antoine Tenart) [2041382]
- net: move early demux fields close to sk_refcnt (Antoine Tenart) [2041382]
- tcp: defer skb freeing after socket lock is released (Antoine Tenart) [2041382]
- net: shrink struct sock by 8 bytes (Antoine Tenart) [2041382]
- ipv6: shrink struct ipcm6_cookie (Antoine Tenart) [2041382]
- net: remove sk_route_nocaps (Antoine Tenart) [2041382]
- net: remove sk_route_forced_caps (Antoine Tenart) [2041382]
- net: use sk_is_tcp() in more places (Antoine Tenart) [2041382]
- bpf, sockmap: Use stricter sk state checks in sk_lookup_assign (Antoine Tenart) [2041382]
- ipv6: move inet6_sk(sk)->rx_dst_cookie to sk->sk_rx_dst_cookie (Antoine Tenart) [2041382]
- tcp: move inet->rx_dst_ifindex to sk->sk_rx_dst_ifindex (Antoine Tenart) [2041382]
- [RHEL-9.0] IPMI Add RH_KABI_RESERVE to kABI sensitive structs (Tony Camuso) [2042031]
- configs: disable CONFIG_CRAMFS (Abhi Das) [2041184]
- ppp: ensure minimum packet size in ppp_write() (Guillaume Nault) [2042936]
- [pci] PCI: Add reserved fields to 'struct pci_sriov' (Myron Stowe) [2039086]
- [include] PCI: Add reserved fields to 'struct pci_driver' (Myron Stowe) [2039086]
- [include] PCI: Add reserved fields to 'struct pci_bus' (Myron Stowe) [2039086]
- [include] PCI: Add reserved fields, and extension, to 'struct pci_dev' (Myron Stowe) [2039086]
- PCI: ACPI: Check parent pointer in acpi_pci_find_companion() (Myron Stowe) [2039086]
- PCI/ACPI: Don't reset a fwnode set by OF (Myron Stowe) [2039086]
- PCI: Make saved capability state private to core (Myron Stowe) [2039086]
- PCI: Change the type of probe argument in reset functions (Myron Stowe) [2039086]
- PCI: Add support for ACPI _RST reset method (Myron Stowe) [2039086]
- PCI: Setup ACPI fwnode early and at the same time with OF (Myron Stowe) [2039086]
- PCI: Use acpi_pci_power_manageable() (Myron Stowe) [2039086]
- PCI: Add pci_set_acpi_fwnode() to set ACPI_COMPANION (Myron Stowe) [2039086]
- PCI: Allow userspace to query and set device reset mechanism (Myron Stowe) [2039086]
- PCI: Remove reset_fn field from pci_dev (Myron Stowe) [2039086]
- PCI: Add array to track reset method ordering (Myron Stowe) [2039086]
- PCI: Add pcie_reset_flr() with 'probe' argument (Myron Stowe) [2039086]
- PCI: Cache PCIe Device Capabilities register (Myron Stowe) [2039086]
- PCI: Allow PASID on fake PCIe devices without TLP prefixes (Myron Stowe) [2039086]
- clocksource: Reduce the default clocksource_watchdog() retries to 2 (Waiman Long) [2027463]
- clocksource: Avoid accidental unstable marking of clocksources (Waiman Long) [2027463]
- Revert "clocksource: Increase WATCHDOG_MAX_SKEW" (Waiman Long) [2027463]
- PCI: Add pcie_ptm_enabled() (Petr Oros) [2037314]
- Revert "PCI: Make pci_enable_ptm() private" (Petr Oros) [2037314]
- iommu/vt-d: Fix unmap_pages support (Jerry Snitselaar) [2027762]

* Fri Feb 04 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-55.el9]
- selftests: netfilter: switch to socat for tests using -q option (Hangbin Liu) [2041409]
- selftests: net: udpgro_fwd.sh: explicitly checking the available ping feature (Hangbin Liu) [2041409]
- selftests: net: using ping6 for IPv6 in udpgro_fwd.sh (Hangbin Liu) [2041409]
- selftests: net: Fix a typo in udpgro_fwd.sh (Hangbin Liu) [2041409]
- selftests/net: udpgso_bench_tx: fix dst ip argument (Hangbin Liu) [2041409]
- selftest/net/forwarding: declare NETIFS p9 p10 (Hangbin Liu) [2041409]
- selftests: Fix IPv6 address bind tests (Hangbin Liu) [2041409]
- selftests: Fix raw socket bind tests with VRF (Hangbin Liu) [2041409]
- selftests: Add duplicate config only for MD5 VRF tests (Hangbin Liu) [2041409]
- selftests: icmp_redirect: pass xfail=0 to log_test() (Hangbin Liu) [2041409]
- selftests: net: Correct ping6 expected rc from 2 to 1 (Hangbin Liu) [2041409]
- selftests/fib_tests: Rework fib_rp_filter_test() (Hangbin Liu) [2041409]
- selftests: net: Correct case name (Hangbin Liu) [2041409]
- redhat/configs: Enable CONFIG_PCI_P2PDMA (Myron Stowe) [1923862]
- nvme: drop scan_lock and always kick requeue list when removing namespaces (Gopal Tiwari) [2038783]
- ACPI: CPPC: Add NULL pointer check to cppc_get_perf() (David Arcari) [2025291]
- cpufreq: intel_pstate: Clear HWP Status during HWP Interrupt enable (David Arcari) [2025291]
- cpufreq: intel_pstate: Fix unchecked MSR 0x773 access (David Arcari) [2025291]
- cpufreq: intel_pstate: Clear HWP desired on suspend/shutdown and offline (David Arcari) [2025291]
- cpufreq: intel_pstate: Fix cpu->pstate.turbo_freq initialization (David Arcari) [2025291]
- cpufreq: intel_pstate: Process HWP Guaranteed change notification (David Arcari) [2025291]
- cpufreq: intel_pstate: Override parameters if HWP forced by BIOS (David Arcari) [2025291]
- cpufreq: intel_pstate: hybrid: Rework HWP calibration (David Arcari) [2025291]
- Revert "cpufreq: intel_pstate: Process HWP Guaranteed change notification" (David Arcari) [2025291]
- cpufreq: intel_pstate: Process HWP Guaranteed change notification (David Arcari) [2025291]
- cpufreq: Replace deprecated CPU-hotplug functions (David Arcari) [2025291]
- ACPI: CPPC: Introduce cppc_get_nominal_perf() (David Arcari) [2025291]
- Change s390x CONFIG_NODES_SHIFT from 4 to 1 (Prarit Bhargava) [2018568]
- Build CONFIG_SPI_PXA2XX as a module on x86 (Prarit Bhargava) [2018568]
- Turn on CONFIG_CPU_FREQ_GOV_SCHEDUTIL for x86 (Prarit Bhargava) [2018568]
- Turn CONFIG_DEVMEM back off for aarch64 (Prarit Bhargava) [2018568]
- New configs in drivers/media (Prarit Bhargava) [2018568]
- Manually add pending items that need to be set due to mismatch (Prarit Bhargava) [2018568]
- Build CRYPTO_SHA3_*_S390 inline for s390 zfcpdump (Prarit Bhargava) [2018568]
- configs: Remove pending CONFIG_CHELSIO_IPSEC_INLINE file (Prarit Bhargava) [2018568]
- New configs in arch/powerpc (Prarit Bhargava) [2018568]
- New configs in lib/Kconfig.debug (Prarit Bhargava) [2018568]
- New configs in drivers/vhost (Prarit Bhargava) [2018568]
- New configs in drivers/pinctrl (Prarit Bhargava) [2018568]
- New configs in drivers/gpu (Prarit Bhargava) [2018568]
- New configs in drivers/gpio (Prarit Bhargava) [2018568]
- New configs in drivers/block (Prarit Bhargava) [2018568]
- New configs in crypto/Kconfig (Prarit Bhargava) [2018568]
- New configs in drivers/acpi (Prarit Bhargava) [2018568]
- New configs in arch/arm64 (Prarit Bhargava) [2018568]
- New configs in arch/Kconfig (Prarit Bhargava) [2018568]
- AUTOMATIC: New configs (Prarit Bhargava) [2018568]
- Clean up pending common (Prarit Bhargava) [2018568]

* Thu Feb 03 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-54.el9]
- iwlwifi: mvm: read 6E enablement flags from DSM and pass to FW (Íñigo Huguet) [2033354]
- ath11k: add string type to search board data in board-2.bin for WCN6855 (Íñigo Huguet) [2033354]
- mt76: enable new device MT7921E (Íñigo Huguet) [2033354]
- cfg80211: correct bridge/4addr mode check (Íñigo Huguet) [2033354]
- cfg80211: fix management registrations locking (Íñigo Huguet) [2033354]
- cfg80211: scan: fix RCU in cfg80211_add_nontrans_list() (Íñigo Huguet) [2033354]
- mac80211: mesh: fix HE operation element length check (Íñigo Huguet) [2033354]
- mwifiex: avoid null-pointer-subtraction warning (Íñigo Huguet) [2033354]
- Revert "brcmfmac: use ISO3166 country code and 0 rev as fallback" (Íñigo Huguet) [2033354]
- iwlwifi: pcie: add configuration of a Wi-Fi adapter on Dell XPS 15 (Íñigo Huguet) [2033354]
- mac80211: Fix Ptk0 rekey documentation (Íñigo Huguet) [2033354]
- mac80211: check return value of rhashtable_init (Íñigo Huguet) [2033354]
- mac80211: fix use-after-free in CCMP/GCMP RX (Íñigo Huguet) [2033354]
- drivers: net: mhi: fix error path in mhi_net_newlink (Íñigo Huguet) [2033354]
- mac80211-hwsim: fix late beacon hrtimer handling (Íñigo Huguet) [2033354]
- mac80211: mesh: fix potentially unaligned access (Íñigo Huguet) [2033354]
- mac80211: limit injected vht mcs/nss in ieee80211_parse_tx_radiotap (Íñigo Huguet) [2033354]
- mac80211: Drop frames from invalid MAC address in ad-hoc mode (Íñigo Huguet) [2033354]
- mac80211: Fix ieee80211_amsdu_aggregate frag_tail bug (Íñigo Huguet) [2033354]
- Revert "mac80211: do not use low data rates for data frames with no ack flag" (Íñigo Huguet) [2033354]
- iwlwifi: mvm: d3: missing unlock in iwl_mvm_wowlan_program_keys() (Íñigo Huguet) [2033354]
- iwlwifi: mvm: d3: Fix off by ones in iwl_mvm_wowlan_get_rsc_v5_data() (Íñigo Huguet) [2033354]
- iwlwifi: mvm: Fix possible NULL dereference (Íñigo Huguet) [2033354]
- iwl: fix debug printf format strings (Íñigo Huguet) [2033354]
- iwlwifi: pnvm: Fix a memory leak in 'iwl_pnvm_get_from_fs()' (Íñigo Huguet) [2033354]
- iwlwifi: bump FW API to 66 for AX devices (Íñigo Huguet) [2033354]
- iwlwifi Add support for ax201 in Samsung Galaxy Book Flex2 Alpha (Íñigo Huguet) [2033354]
- iwlwifi: mvm: add rtnl_lock() in iwl_mvm_start_get_nvm() (Íñigo Huguet) [2033354]
- net: qrtr: revert check in qrtr_endpoint_post() (Íñigo Huguet) [2033354]
- net: qrtr: make checks in qrtr_endpoint_post() stricter (Íñigo Huguet) [2033354]
- intel: switch from 'pci_' to 'dma_' API (Íñigo Huguet) [2033354]
- mwifiex: pcie: add reset_d3cold quirk for Surface gen4+ devices (Íñigo Huguet) [2033354]
- mwifiex: pcie: add DMI-based quirk implementation for Surface devices (Íñigo Huguet) [2033354]
- brcmfmac: pcie: fix oops on failure to resume and reprobe (Íñigo Huguet) [2033354]
- wilc1000: Convert module-global "isinit" to device-specific variable (Íñigo Huguet) [2033354]
- brcmfmac: Add WPA3 Personal with FT to supported cipher suites (Íñigo Huguet) [2033354]
- rtlwifi: rtl8192de: Fix initialization of place in _rtl92c_phy_get_rightchnlplace() (Íñigo Huguet) [2033354]
- rtw88: add quirk to disable pci caps on HP Pavilion 14-ce0xxx (Íñigo Huguet) [2033354]
- ath9k: fix sleeping in atomic context (Íñigo Huguet) [2033354]
- ath9k: fix OOB read ar9300_eeprom_restore_internal (Íñigo Huguet) [2033354]
- iwlwifi: mvm: don't use FW key ID in beacon protection (Íñigo Huguet) [2033354]
- iwlwifi: mvm: Fix scan channel flags settings (Íñigo Huguet) [2033354]
- iwlwifi: mvm: support broadcast TWT alone (Íñigo Huguet) [2033354]
- iwlwifi: mvm: introduce iwl_stored_beacon_notif_v3 (Íñigo Huguet) [2033354]
- iwlwifi: move get pnvm file name to a separate function (Íñigo Huguet) [2033354]
- iwlwifi: mvm: add support for responder config command version 9 (Íñigo Huguet) [2033354]
- iwlwifi: mvm: add support for range request command version 13 (Íñigo Huguet) [2033354]
- iwlwifi: allow debug init in RF-kill (Íñigo Huguet) [2033354]
- iwlwifi: mvm: don't schedule the roc_done_wk if it is already running (Íñigo Huguet) [2033354]
- iwlwifi: yoyo: support for new DBGI_SRAM region (Íñigo Huguet) [2033354]
- iwlwifi: add 'Rx control frame to MBSSID' HE capability (Íñigo Huguet) [2033354]
- iwlwifi: fw: fix debug dump data declarations (Íñigo Huguet) [2033354]
- iwlwifi: api: remove datamember from struct (Íñigo Huguet) [2033354]
- iwlwifi: fix __percpu annotation (Íñigo Huguet) [2033354]
- iwlwifi: pcie: avoid dma unmap/remap in crash dump (Íñigo Huguet) [2033354]
- iwlwifi: acpi: fill in SAR tables with defaults (Íñigo Huguet) [2033354]
- iwlwifi: acpi: fill in WGDS table with defaults (Íñigo Huguet) [2033354]
- iwlwifi: bump FW API to 65 for AX devices (Íñigo Huguet) [2033354]
- iwlwifi: acpi: support reading and storing WGDS revision 2 (Íñigo Huguet) [2033354]
- iwlwifi: mvm: load regdomain at INIT stage (Íñigo Huguet) [2033354]
- iwlwifi: mvm: Read the PPAG and SAR tables at INIT stage (Íñigo Huguet) [2033354]
- iwlwifi: mvm: trigger WRT when no beacon heard (Íñigo Huguet) [2033354]
- iwlwifi: fw: correctly limit to monitor dump (Íñigo Huguet) [2033354]
- iwlwifi: skip first element in the WTAS ACPI table (Íñigo Huguet) [2033354]
- iwlwifi: mvm: support version 11 of wowlan statuses notification (Íñigo Huguet) [2033354]
- iwlwifi: convert flat GEO profile table to a struct version (Íñigo Huguet) [2033354]
- iwlwifi: remove unused ACPI_WGDS_TABLE_SIZE definition (Íñigo Huguet) [2033354]
- iwlwifi: support reading and storing EWRD revisions 1 and 2 (Íñigo Huguet) [2033354]
- iwlwifi: acpi: support reading and storing WRDS revision 1 and 2 (Íñigo Huguet) [2033354]
- iwlwifi: pass number of chains and sub-bands to iwl_sar_set_profile() (Íñigo Huguet) [2033354]
- iwlwifi: remove ACPI_SAR_NUM_TABLES definition (Íñigo Huguet) [2033354]
- iwlwifi: convert flat SAR profile table to a struct version (Íñigo Huguet) [2033354]
- iwlwifi: rename ACPI_SAR_NUM_CHAIN_LIMITS to ACPI_SAR_NUM_CHAINS (Íñigo Huguet) [2033354]
- iwlwifi: mvm: fix access to BSS elements (Íñigo Huguet) [2033354]
- iwlwifi: mvm: Refactor setting of SSIDs for 6GHz scan (Íñigo Huguet) [2033354]
- iwlwifi: mvm: silently drop encrypted frames for unknown station (Íñigo Huguet) [2033354]
- iwlwifi: mvm: d3: implement RSC command version 5 (Íñigo Huguet) [2033354]
- iwlwifi: mvm: d3: make key reprogramming iteration optional (Íñigo Huguet) [2033354]
- iwlwifi: mvm: d3: add separate key iteration for GTK type (Íñigo Huguet) [2033354]
- iwlwifi: mvm: d3: refactor TSC/RSC configuration (Íñigo Huguet) [2033354]
- iwlwifi: mvm: d3: remove fixed cmd_flags argument (Íñigo Huguet) [2033354]
- iwlwifi: mvm: d3: separate TKIP data from key iteration (Íñigo Huguet) [2033354]
- iwlwifi: mvm: simplify __iwl_mvm_set_sta_key() (Íñigo Huguet) [2033354]
- iwlwifi: mvm: support new station key API (Íñigo Huguet) [2033354]
- iwlwifi: mvm: Fix umac scan request probe parameters (Íñigo Huguet) [2033354]
- iwlwifi: pcie: implement Bz reset flow (Íñigo Huguet) [2033354]
- iwlwifi: implement Bz NMI behaviour (Íñigo Huguet) [2033354]
- iwlwifi: pcie: implement Bz device startup (Íñigo Huguet) [2033354]
- iwlwifi: read MAC address from correct place on Bz (Íñigo Huguet) [2033354]
- iwlwifi: give Bz devices their own name (Íñigo Huguet) [2033354]
- iwlwifi: split off Bz devices into their own family (Íñigo Huguet) [2033354]
- iwlwifi: yoyo: cleanup internal buffer allocation in D3 (Íñigo Huguet) [2033354]
- iwlwifi: mvm: treat MMPDUs in iwl_mvm_mac_tx() as bcast (Íñigo Huguet) [2033354]
- iwlwifi: mvm: clean up number of HW queues (Íñigo Huguet) [2033354]
- iwlwifi: mvm: avoid static queue number aliasing (Íñigo Huguet) [2033354]
- iwlwifi: use DEFINE_MUTEX() for mutex lock (Íñigo Huguet) [2033354]
- iwlwifi: remove trailing semicolon in macro definition (Íñigo Huguet) [2033354]
- iwlwifi: mvm: fix a memory leak in iwl_mvm_mac_ctxt_beacon_changed (Íñigo Huguet) [2033354]
- iwlwifi: mvm: fix old-style static const declaration (Íñigo Huguet) [2033354]
- iwlwifi: mvm: remove check for vif in iwl_mvm_vif_from_mac80211() (Íñigo Huguet) [2033354]
- iwlwifi: pcie: remove spaces from queue names (Íñigo Huguet) [2033354]
- iwlwifi: mvm: restrict FW SMPS request (Íñigo Huguet) [2033354]
- iwlwifi: mvm: set replay counter on key install (Íñigo Huguet) [2033354]
- iwlwifi: mvm: remove trigger EAPOL time event (Íñigo Huguet) [2033354]
- iwlwifi: iwl-dbg-tlv: add info about loading external dbg bin (Íñigo Huguet) [2033354]
- iwlwifi: mvm: Add support for hidden network scan on 6GHz band (Íñigo Huguet) [2033354]
- iwlwifi: mvm: Do not use full SSIDs in 6GHz scan (Íñigo Huguet) [2033354]
- iwlwifi: print PNVM complete notification status in hexadecimal (Íñigo Huguet) [2033354]
- iwlwifi: pcie: dump error on FW reset handshake failures (Íñigo Huguet) [2033354]
- iwlwifi: prepare for synchronous error dumps (Íñigo Huguet) [2033354]
- iwlwifi: pcie: free RBs during configure (Íñigo Huguet) [2033354]
- iwlwifi: pcie: optimise struct iwl_rx_mem_buffer layout (Íñigo Huguet) [2033354]
- iwlwifi: mvm: avoid FW restart while shutting down (Íñigo Huguet) [2033354]
- iwlwifi: nvm: enable IEEE80211_HE_PHY_CAP10_HE_MU_M1RU_MAX_LTF (Íñigo Huguet) [2033354]
- iwlwifi: mvm: set BROADCAST_TWT_SUPPORTED in MAC policy (Íñigo Huguet) [2033354]
- iwlwifi: iwl-nvm-parse: set STBC flags for HE phy capabilities (Íñigo Huguet) [2033354]
- cfg80211: use wiphy DFS domain if it is self-managed (Íñigo Huguet) [2033354]
- mac80211: parse transmit power envelope element (Íñigo Huguet) [2033354]
- ieee80211: add definition for transmit power envelope element (Íñigo Huguet) [2033354]
- ieee80211: add definition of regulatory info in 6 GHz operation information (Íñigo Huguet) [2033354]
- mac80211: introduce individual TWT support in AP mode (Íñigo Huguet) [2033354]
- ieee80211: add TWT element definitions (Íñigo Huguet) [2033354]
- brcmsmac: make array addr static const, makes object smaller (Íñigo Huguet) [2033354]
- rtw88: Remove unnecessary check code (Íñigo Huguet) [2033354]
- rtw88: wow: fix size access error of probe request (Íñigo Huguet) [2033354]
- rtw88: wow: report wow reason through mac80211 api (Íñigo Huguet) [2033354]
- rtw88: wow: build wow function only if CONFIG_PM is on (Íñigo Huguet) [2033354]
- rtw88: refine the setting of rsvd pages for different firmware (Íñigo Huguet) [2033354]
- rtw88: use read_poll_timeout instead of fixed sleep (Íñigo Huguet) [2033354]
- rtw88: 8822ce: set CLKREQ# signal to low during suspend (Íñigo Huguet) [2033354]
- rtw88: change beacon filter default mode (Íñigo Huguet) [2033354]
- rtw88: 8822c: add tx stbc support under HT mode (Íñigo Huguet) [2033354]
- rtw88: adjust the log level for failure of tx report (Íñigo Huguet) [2033354]
- rtl8xxxu: Fix the handling of TX A-MPDU aggregation (Íñigo Huguet) [2033354]
- rtl8xxxu: disable interrupt_in transfer for 8188cu and 8192cu (Íñigo Huguet) [2033354]
- mwifiex: make arrays static const, makes object smaller (Íñigo Huguet) [2033354]
- mwifiex: usb: Replace one-element array with flexible-array member (Íñigo Huguet) [2033354]
- mwifiex: drop redundant null-pointer check in mwifiex_dnld_cmd_to_fw() (Íñigo Huguet) [2033354]
- wilc1000: remove redundant code (Íñigo Huguet) [2033354]
- wilc1000: use devm_clk_get_optional() (Íñigo Huguet) [2033354]
- wilc1000: dispose irq on failure path (Íñigo Huguet) [2033354]
- wilc1000: use goto labels on error path (Íñigo Huguet) [2033354]
- rtlwifi: rtl8192de: make arrays static const, makes object smaller (Íñigo Huguet) [2033354]
- rtlwifi: rtl8192de: Remove redundant variable initializations (Íñigo Huguet) [2033354]
- ray_cs: Split memcpy() to avoid bounds check warning (Íñigo Huguet) [2033354]
- ray_cs: use %%*ph to print small buffer (Íñigo Huguet) [2033354]
- brcmfmac: add 43752 SDIO ids and initialization (Íñigo Huguet) [2033354]
- brcmfmac: Set SDIO workqueue as WQ_HIGHPRI (Íñigo Huguet) [2033354]
- brcmfmac: use separate firmware for 43430 revision 2 (Íñigo Huguet) [2033354]
- brcmfmac: support chipsets with different core enumeration space (Íñigo Huguet) [2033354]
- brcmfmac: add xtlv support to firmware interface layer (Íñigo Huguet) [2033354]
- brcmfmac: increase core revision column aligning core list (Íñigo Huguet) [2033354]
- brcmfmac: use different error value for invalid ram base address (Íñigo Huguet) [2033354]
- brcmfmac: firmware: Fix firmware loading (Íñigo Huguet) [2033354]
- cfg80211: fix BSS color notify trace enum confusion (Íñigo Huguet) [2033354]
- mac80211: Fix insufficient headroom issue for AMSDU (Íñigo Huguet) [2033354]
- mac80211: add support for BSS color change (Íñigo Huguet) [2033354]
- nl80211: add support for BSS coloring (Íñigo Huguet) [2033354]
- mac80211: Use flex-array for radiotap header bitmap (Íñigo Huguet) [2033354]
- mac80211: radiotap: Use BIT() instead of shifts (Íñigo Huguet) [2033354]
- mac80211: Remove unnecessary variable and label (Íñigo Huguet) [2033354]
- mac80211: include <linux/rbtree.h> (Íñigo Huguet) [2033354]
- mac80211: Fix monitor MTU limit so that A-MSDUs get through (Íñigo Huguet) [2033354]
- mac80211: remove unnecessary NULL check in ieee80211_register_hw() (Íñigo Huguet) [2033354]
- mac80211: Reject zero MAC address in sta_info_insert_check() (Íñigo Huguet) [2033354]
- bus: mhi: core: Improve debug messages for power up (Íñigo Huguet) [2033354]
- bus: mhi: core: Replace DMA allocation wrappers with original APIs (Íñigo Huguet) [2033354]
- bus: mhi: core: Add range checks for BHI and BHIe (Íñigo Huguet) [2033354]
- bus: mhi: pci_generic: Set register access length for MHI driver (Íñigo Huguet) [2033354]
- ath11k: set register access length for MHI driver (Íñigo Huguet) [2033354]
- bus: mhi: Add MMIO region length to controller structure (Íñigo Huguet) [2033354]
- bus: mhi: core: Set BHI and BHIe pointers to NULL in clean-up (Íñigo Huguet) [2033354]
- bus: mhi: core: Set BHI/BHIe offsets on power up preparation (Íñigo Huguet) [2033354]
- bus: mhi: pci_generic: Add Cinterion MV31-W PCIe to MHI (Íñigo Huguet) [2033354]
- net: mhi: Remove MBIM protocol (Íñigo Huguet) [2033354]
- brcmfmac: firmware: Allow per-board firmware binaries (Íñigo Huguet) [2033354]
- net: mhi: Improve MBIM packet counting (Íñigo Huguet) [2033354]
- bus: mhi: pci-generic: configurable network interface MRU (Íñigo Huguet) [2033354]
- ath11k: Remove some duplicate code (Íñigo Huguet) [2033354]
- ath: switch from 'pci_' to 'dma_' API (Íñigo Huguet) [2033354]

* Wed Feb 02 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-53.el9]
- quota: correct error number in free_dqentry() (Lukas Czerner) [2041793]
- quota: check block number when reading the block in quota file (Lukas Czerner) [2041793]
- ext4: don't use the orphan list when migrating an inode (Lukas Czerner) [2041486]
- ext4: use BUG_ON instead of if condition followed by BUG (Lukas Czerner) [2041486]
- ext4: fix a copy and paste typo (Lukas Czerner) [2041777]
- ext4: set csum seed in tmp inode while migrating to extents (Lukas Czerner) [2041486]
- ext4: remove unnecessary 'offset' assignment (Lukas Czerner) [2041486]
- ext4: remove redundant o_start statement (Lukas Czerner) [2041486]
- ext4: drop an always true check (Lukas Czerner) [2041486]
- ext4: remove unused assignments (Lukas Czerner) [2041486]
- ext4: remove redundant statement (Lukas Czerner) [2041486]
- ext4: remove useless resetting io_end_size in mpage_process_page() (Lukas Czerner) [2041486]
- ext4: allow to change s_last_trim_minblks via sysfs (Lukas Czerner) [2041486]
- ext4: change s_last_trim_minblks type to unsigned long (Lukas Czerner) [2041486]
- ext4: implement support for get/set fs label (Lukas Czerner) [2041486]
- ext4: only set EXT4_MOUNT_QUOTA when journalled quota file is specified (Lukas Czerner) [2041777]
- ext4: don't use kfree() on rcu protected pointer sbi->s_qf_names (Lukas Czerner) [2041486]
- ext4: avoid trim error on fs with small groups (Lukas Czerner) [2041486]
- ext4: fix an use-after-free issue about data=journal writeback mode (Lukas Czerner) [2041486]
- ext4: fix null-ptr-deref in '__ext4_journal_ensure_credits' (Lukas Czerner) [2041486]
- ext4: initialize err_blk before calling __ext4_get_inode_loc (Lukas Czerner) [2041486]
- ext4: fix a possible ABBA deadlock due to busy PA (Lukas Czerner) [2041486]
- ext4: replace snprintf in show functions with sysfs_emit (Lukas Czerner) [2041486]
- ext4: make sure to reset inode lockdep class when quota enabling fails (Lukas Czerner) [2041486]
- ext4: make sure quota gets properly shutdown on error (Lukas Czerner) [2041486]
- ext4: Fix BUG_ON in ext4_bread when write quota data (Lukas Czerner) [2041486]
- ext4: destroy ext4_fc_dentry_cachep kmemcache on module removal (Lukas Czerner) [2041486]
- ext4: fast commit may miss tracking unwritten range during ftruncate (Lukas Czerner) [2041486]
- ext4: use ext4_ext_remove_space() for fast commit replay delete range (Lukas Czerner) [2041486]
- ext4: fix fast commit may miss tracking range for FALLOC_FL_ZERO_RANGE (Lukas Czerner) [2041486]
- ext4: update fast commit TODOs (Lukas Czerner) [2041486]
- ext4: simplify updating of fast commit stats (Lukas Czerner) [2041486]
- ext4: drop ineligible txn start stop APIs (Lukas Czerner) [2041486]
- ext4: use ext4_journal_start/stop for fast commit transactions (Lukas Czerner) [2041486]
- ext4: fix i_version handling on remount (Lukas Czerner) [2041777]
- ext4: remove lazytime/nolazytime mount options handled by MS_LAZYTIME (Lukas Czerner) [2041777]
- ext4: don't fail remount if journalling mode didn't change (Lukas Czerner) [2041777]
- ext4: Remove unused match_table_t tokens (Lukas Czerner) [2041777]
- ext4: switch to the new mount api (Lukas Czerner) [2041777]
- ext4: change token2str() to use ext4_param_specs (Lukas Czerner) [2041777]
- ext4: clean up return values in handle_mount_opt() (Lukas Czerner) [2041777]
- ext4: Completely separate options parsing and sb setup (Lukas Czerner) [2041777]
- ext4: get rid of super block and sbi from handle_mount_ops() (Lukas Czerner) [2041777]
- ext4: check ext2/3 compatibility outside handle_mount_opt() (Lukas Czerner) [2041777]
- ext4: move quota configuration out of handle_mount_opt() (Lukas Czerner) [2041777]
- ext4: Allow sb to be NULL in ext4_msg() (Lukas Czerner) [2041777]
- ext4: Change handle_mount_opt() to use fs_parameter (Lukas Czerner) [2041777]
- ext4: move option validation to a separate function (Lukas Czerner) [2041777]
- ext4: Add fs parameter specifications for mount options (Lukas Czerner) [2041777]
- fs_parse: allow parameter value to be empty (Lukas Czerner) [2041777]
- ext4: fix error code saved on super block during file system abort (Lukas Czerner) [2041486]
- ext4: inline data inode fast commit replay fixes (Lukas Czerner) [2041486]
- ext4: commit inline data during fast commit (Lukas Czerner) [2041486]
- ext4: scope ret locally in ext4_try_to_trim_range() (Lukas Czerner) [2041486]
- ext4: remove an unused variable warning with CONFIG_QUOTA=n (Lukas Czerner) [2041486]
- ext4: fix boolreturn.cocci warnings in fs/ext4/name.c (Lukas Czerner) [2041486]
- ext4: prevent getting empty inode buffer (Lukas Czerner) [2041486]
- ext4: move ext4_fill_raw_inode() related functions (Lukas Czerner) [2041486]
- ext4: factor out ext4_fill_raw_inode() (Lukas Czerner) [2041486]
- ext4: prevent partial update of the extent blocks (Lukas Czerner) [2035878]
- ext4: check for inconsistent extents between index and leaf block (Lukas Czerner) [2035878]
- ext4: check for out-of-order index extents in ext4_valid_extent_entries() (Lukas Czerner) [2035878]
- ext4: convert from atomic_t to refcount_t on ext4_io_end->count (Lukas Czerner) [2041486]
- ext4: refresh the ext4_ext_path struct after dropping i_data_sem. (Lukas Czerner) [2041486]
- ext4: ensure enough credits in ext4_ext_shift_path_extents (Lukas Czerner) [2041486]
- ext4: correct the left/middle/right debug message for binsearch (Lukas Czerner) [2041486]
- ext4: fix lazy initialization next schedule time computation in more granular unit (Lukas Czerner) [2041486]
- ext4: recheck buffer uptodate bit under buffer lock (Lukas Czerner) [2041486]
- ext4: fix potential infinite loop in ext4_dx_readdir() (Lukas Czerner) [2041486]
- ext4: flush s_error_work before journal destroy in ext4_fill_super (Lukas Czerner) [2041486]
- ext4: fix loff_t overflow in ext4_max_bitmap_size() (Lukas Czerner) [2041486]
- ext4: fix reserved space counter leakage (Lukas Czerner) [2041486]
- ext4: limit the number of blocks in one ADD_RANGE TLV (Lukas Czerner) [2041486]
- ext4: remove extent cache entries when truncating inline data (Lukas Czerner) [2041486]
- ext4: drop unnecessary journal handle in delalloc write (Lukas Czerner) [2041486]
- ext4: factor out write end code of inline file (Lukas Czerner) [2041486]
- ext4: correct the error path of ext4_write_inline_data_end() (Lukas Czerner) [2041486]
- ext4: check and update i_disksize properly (Lukas Czerner) [2041486]
- ext4: add error checking to ext4_ext_replay_set_iblocks() (Lukas Czerner) [2041486]
- ext4: make the updating inode data procedure atomic (Lukas Czerner) [2041486]
- ext4: remove an unnecessary if statement in __ext4_get_inode_loc() (Lukas Czerner) [2041486]
- ext4: move inode eio simulation behind io completeion (Lukas Czerner) [2041486]
- ext4: Improve scalability of ext4 orphan file handling (Lukas Czerner) [2041486]
- ext4: Speedup ext4 orphan inode handling (Lukas Czerner) [2041486]
- ext4: Move orphan inode handling into a separate file (Lukas Czerner) [2041486]
- jbd2: add sparse annotations for add_transaction_credits() (Lukas Czerner) [2041486]
- ext4: Support for checksumming from journal triggers (Lukas Czerner) [2041486]
- ext4: fix sparse warnings (Lukas Czerner) [2041486]
- ext4: fix race writing to an inline_data file while its xattrs are changing (Lukas Czerner) [2003461]
- ext4: Make sure quota files are not grabbed accidentally (Lukas Czerner) [2041486]
- ext4: fix e2fsprogs checksum failure for mounted filesystem (Lukas Czerner) [2022859]
- ext4: if zeroout fails fall back to splitting the extent node (Lukas Czerner) [2041486]
- ext4: reduce arguments of ext4_fc_add_dentry_tlv (Lukas Czerner) [2041486]
- ext4: remove the repeated comment of ext4_trim_all_free (Lukas Czerner) [2041486]
- ext4: add new helper interface ext4_try_to_trim_range() (Lukas Czerner) [2041486]
- ext4: remove the 'group' parameter of ext4_trim_extent (Lukas Czerner) [2041486]
- jbd2: clean up two gcc -Wall warnings in recovery.c (Lukas Czerner) [2041486]
- jbd2: fix clang warning in recovery.c (Lukas Czerner) [2041486]
- jbd2: fix portability problems caused by unaligned accesses (Lukas Czerner) [2041486]
- ext4: Convert to use mapping->invalidate_lock (Lukas Czerner) [2041486]

* Tue Feb 01 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-52.el9]
- KVM: arm64: Avoid setting the upper 32 bits of TCR_EL2 and CPTR_EL2 to 1 (Andrew Jones) [2009341]
- KVM: arm64: Extract ESR_ELx.EC only (Andrew Jones) [2009341]
- KVM: selftests: Build the memslot tests for arm64 (Andrew Jones) [2009341]
- KVM: selftests: Make memslot_perf_test arch independent (Andrew Jones) [2009341]
- selftests: KVM: Fix kvm device helper ioctl assertions (Andrew Jones) [2009341]
- KVM: arm64: selftests: arch_timer: Support vCPU migration (Andrew Jones) [2009341]
- KVM: arm64: selftests: Add arch_timer test (Andrew Jones) [2009341]
- KVM: arm64: selftests: Add host support for vGIC (Andrew Jones) [2009341]
- KVM: arm64: selftests: Add basic GICv3 support (Andrew Jones) [2009341]
- KVM: arm64: selftests: Add light-weight spinlock support (Andrew Jones) [2009341]
- KVM: arm64: selftests: Add guest support to get the vcpuid (Andrew Jones) [2009341]
- KVM: arm64: selftests: Maintain consistency for vcpuid type (Andrew Jones) [2009341]
- KVM: arm64: selftests: Add support to disable and enable local IRQs (Andrew Jones) [2009341]
- KVM: arm64: selftests: Add basic support to generate delays (Andrew Jones) [2009341]
- KVM: arm64: selftests: Add basic support for arch_timers (Andrew Jones) [2009341]
- KVM: arm64: selftests: Add support for cpu_relax (Andrew Jones) [2009341]
- KVM: arm64: selftests: Introduce ARM64_SYS_KVM_REG (Andrew Jones) [2009341]
- tools: arm64: Import sysreg.h (Andrew Jones) [2009341]
- KVM: arm64: selftests: Add MMIO readl/writel support (Andrew Jones) [2009341]
- KVM: arm64: selftests: Add init ITS device test (Andrew Jones) [2009341]
- KVM: arm64: selftests: Add test for legacy GICv3 REDIST base partially above IPA range (Andrew Jones) [2009341]
- KVM: arm64: selftests: Add tests for GIC redist/cpuif partially above IPA range (Andrew Jones) [2009341]
- KVM: arm64: selftests: Add some tests for GICv2 in vgic_init (Andrew Jones) [2009341]
- KVM: arm64: selftests: Make vgic_init/vm_gic_create version agnostic (Andrew Jones) [2009341]
- KVM: arm64: selftests: Make vgic_init gic version agnostic (Andrew Jones) [2009341]
- KVM: arm64: vgic: Drop vgic_check_ioaddr() (Andrew Jones) [2009341]
- KVM: arm64: vgic-v3: Check ITS region is not above the VM IPA size (Andrew Jones) [2009341]
- KVM: arm64: vgic-v2: Check cpu interface region is not above the VM IPA size (Andrew Jones) [2009341]
- KVM: arm64: vgic-v3: Check redist region is not above the VM IPA size (Andrew Jones) [2009341]
- kvm: arm64: vgic: Introduce vgic_check_iorange (Andrew Jones) [2009341]
- KVM: arm64: Release mmap_lock when using VM_SHARED with MTE (Andrew Jones) [2009341]
- KVM: arm64: Report corrupted refcount at EL2 (Andrew Jones) [2009341]
- KVM: arm64: Fix host stage-2 PGD refcount (Andrew Jones) [2009341]
- KVM: arm64: Fix PMU probe ordering (Andrew Jones) [2009341]
- KVM: arm64: nvhe: Fix missing FORCE for hyp-reloc.S build rule (Andrew Jones) [2009341]
- arm64: Do not trap PMSNEVFR_EL1 (Andrew Jones) [2009341]
- KVM: arm64: Trim guest debug exception handling (Andrew Jones) [2009341]
- KVM: arm64: Minor optimization of range_is_memory (Andrew Jones) [2009341]
- KVM: arm64: Upgrade trace_kvm_arm_set_dreg32() to 64bit (Andrew Jones) [2009341]
- KVM: arm64: Add config register bit definitions (Andrew Jones) [2009341]
- KVM: arm64: Track value of cptr_el2 in struct kvm_vcpu_arch (Andrew Jones) [2009341]
- KVM: arm64: Keep mdcr_el2's value as set by __init_el2_debug (Andrew Jones) [2009341]
- KVM: arm64: Restore mdcr_el2 from vcpu (Andrew Jones) [2009341]
- KVM: arm64: Refactor sys_regs.h,c for nVHE reuse (Andrew Jones) [2009341]
- KVM: arm64: Fix names of config register fields (Andrew Jones) [2009341]
- KVM: arm64: MDCR_EL2 is a 64-bit register (Andrew Jones) [2009341]
- KVM: arm64: Remove trailing whitespace in comment (Andrew Jones) [2009341]
- KVM: arm64: placeholder to check if VM is protected (Andrew Jones) [2009341]
- KVM: arm64: Upgrade VMID accesses to {READ,WRITE}_ONCE (Andrew Jones) [2009341]
- KVM: arm64: Unify stage-2 programming behind __load_stage2() (Andrew Jones) [2009341]
- KVM: arm64: Move kern_hyp_va() usage in __load_guest_stage2() into the callers (Andrew Jones) [2009341]
- KVM: arm64: vgic: Resample HW pending state on deactivation (Andrew Jones) [2009341]
- KVM: arm64: vgic: Drop WARN from vgic_get_irq (Andrew Jones) [2009341]
- KVM: arm64: Use generic KVM xfer to guest work function (Andrew Jones) [2009341]
- entry: KVM: Allow use of generic KVM entry w/o full generic support (Andrew Jones) [2009341]
- KVM: arm64: Record number of signal exits as a vCPU stat (Andrew Jones) [2009341]
- selftests: KVM: Introduce psci_cpu_on_test (Andrew Jones) [2009341]
- KVM: arm64: Enforce reserved bits for PSCI target affinities (Andrew Jones) [2009341]
- KVM: arm64: Handle PSCI resets before userspace touches vCPU state (Andrew Jones) [2009341]
- KVM: arm64: Fix read-side race on updates to vcpu reset state (Andrew Jones) [2009341]
- KVM: arm64: Make hyp_panic() more robust when protected mode is enabled (Andrew Jones) [2009341]
- KVM: arm64: Drop unused REQUIRES_VIRT (Andrew Jones) [2009341]
- KVM: arm64: Drop check_kvm_target_cpu() based percpu probe (Andrew Jones) [2009341]
- KVM: arm64: Drop init_common_resources() (Andrew Jones) [2009341]
- KVM: arm64: Use ARM64_MIN_PARANGE_BITS as the minimum supported IPA (Andrew Jones) [2009341]
- arm64/mm: Add remaining ID_AA64MMFR0_PARANGE_ macros (Andrew Jones) [2009341]
- KVM: arm64: Return -EPERM from __pkvm_host_share_hyp() (Andrew Jones) [2009341]
- KVM: arm64: Restrict IPA size to maximum 48 bits on 4K and 16K page size (Andrew Jones) [2009341]
- arm64/mm: Define ID_AA64MMFR0_TGRAN_2_SHIFT (Andrew Jones) [2009341]
- KVM: arm64: perf: Replace '0xf' instances with ID_AA64DFR0_PMUVER_IMP_DEF (Andrew Jones) [2009341]
- KVM: arm64: Make __pkvm_create_mappings static (Andrew Jones) [2009341]
- KVM: arm64: Restrict EL2 stage-1 changes in protected mode (Andrew Jones) [2009341]
- KVM: arm64: Refactor protected nVHE stage-1 locking (Andrew Jones) [2009341]
- KVM: arm64: Remove __pkvm_mark_hyp (Andrew Jones) [2009341]
- KVM: arm64: Mark host bss and rodata section as shared (Andrew Jones) [2009341]
- KVM: arm64: Enable retrieving protections attributes of PTEs (Andrew Jones) [2009341]
- KVM: arm64: Introduce addr_is_memory() (Andrew Jones) [2009341]
- KVM: arm64: Expose pkvm_hyp_id (Andrew Jones) [2009341]
- KVM: arm64: Expose host stage-2 manipulation helpers (Andrew Jones) [2009341]
- KVM: arm64: Add helpers to tag shared pages in SW bits (Andrew Jones) [2009341]
- KVM: arm64: Allow populating software bits (Andrew Jones) [2009341]
- KVM: arm64: Enable forcing page-level stage-2 mappings (Andrew Jones) [2009341]
- KVM: arm64: Tolerate re-creating hyp mappings to set software bits (Andrew Jones) [2009341]
- KVM: arm64: Don't overwrite software bits with owner id (Andrew Jones) [2009341]
- KVM: arm64: Rename KVM_PTE_LEAF_ATTR_S2_IGNORED (Andrew Jones) [2009341]
- KVM: arm64: Optimize host memory aborts (Andrew Jones) [2009341]
- KVM: arm64: Expose page-table helpers (Andrew Jones) [2009341]
- KVM: arm64: Provide the host_stage2_try() helper macro (Andrew Jones) [2009341]
- KVM: arm64: Introduce hyp_assert_lock_held() (Andrew Jones) [2009341]
- redhat: configs: Disable NVHE_EL2_DEBUG (Andrew Jones) [2009341]
- KVM: arm64: Add hyp_spin_is_locked() for basic locking assertions at EL2 (Andrew Jones) [2009341]
- KVM: arm64: Unregister HYP sections from kmemleak in protected mode (Andrew Jones) [2009341]
- arm64: Move .hyp.rodata outside of the _sdata.._edata range (Andrew Jones) [2009341]
- KVM: arm64: Fix comments related to GICv2 PMR reporting (Andrew Jones) [2009341]
- KVM: arm64: Count VMID-wide TLB invalidations (Andrew Jones) [2009341]
- KVM: arm64: Remove PMSWINC_EL0 shadow register (Andrew Jones) [2009341]
- KVM: arm64: Disabling disabled PMU counters wastes a lot of time (Andrew Jones) [2009341]
- KVM: arm64: Drop unnecessary masking of PMU registers (Andrew Jones) [2009341]
- KVM: arm64: Narrow PMU sysreg reset values to architectural requirements (Andrew Jones) [2009341]
- KVM: arm64: Introduce helper to retrieve a PTE and its level (Andrew Jones) [2009341]
- KVM: Remove kvm_is_transparent_hugepage() and PageTransCompoundMap() (Andrew Jones) [2009341]
- KVM: arm64: Avoid mapping size adjustment on permission fault (Andrew Jones) [2009341]
- KVM: arm64: Walk userspace page tables to compute the THP mapping size (Andrew Jones) [2009341]

* Mon Jan 31 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-51.el9]
- selftests: bpf: Fix bind on used port (Felix Maurer) [2043528]
- Add packaged but empty /lib/modules/<kver>/systemtap (Herton R. Krzesinski) [2012908]
- powerpc/bpf: Update ldimm64 instructions during extra pass (Yauheni Kaliuta) [2040549]
- RDMA/irdma: Don't arm the CQ more than two times if no CE for this CQ (Kamal Heib) [2039426]
- RDMA/irdma: Report correct WC errors (Kamal Heib) [2039426]
- RDMA/irdma: Fix a potential memory allocation issue in 'irdma_prm_add_pble_mem()' (Kamal Heib) [2039426]
- RDMA/irdma: Fix a user-after-free in add_pble_prm (Kamal Heib) [2039426]
- RDMA/irdma: Do not hold qos mutex twice on QP resume (Kamal Heib) [2039426]
- RDMA/irdma: Set VLAN in UD work completion correctly (Kamal Heib) [2039426]
- RDMA/irdma: Process extended CQ entries correctly (Kamal Heib) [2039426]
- RDMA/irdma: Report correct WC error when there are MW bind errors (Kamal Heib) [2039426]
- RDMA/irdma: Report correct WC error when transport retry counter is exceeded (Kamal Heib) [2039426]
- RDMA/irdma: Validate number of CQ entries on create CQ (Kamal Heib) [2039426]
- RDMA/irdma: Skip CQP ring during a reset (Kamal Heib) [2039426]
- redhat/configs: Enable CONFIG_DM_MULTIPATH_HST (Benjamin Marzinski) [2000835]
- RDMA/core: Don't infoleak GRH fields (Kamal Heib) [2036599]
- RDMA/uverbs: Check for null return of kmalloc_array (Kamal Heib) [2036599]
- RDMA/sa_query: Use strscpy_pad instead of memcpy to copy a string (Kamal Heib) [2036599]
- RDMA/cma: Ensure rdma_addr_cancel() happens before issuing more requests (Kamal Heib) [2036599]
- RDMA/cma: Fix listener leak in rdma_cma_listen_on_all() failure (Kamal Heib) [2036599]
- IB/cma: Do not send IGMP leaves for sendonly Multicast groups (Kamal Heib) [2036599]
- IB/core: Remove deprecated current_seq comments (Kamal Heib) [2036599]
- RDMA/iwcm: Release resources if iw_cm module initialization fails (Kamal Heib) [2036599]
- sched: padding for user_struct for KABI (Phil Auld) [2033084]
- sched: padding for signal_struct in linux/sched/signal.h (Phil Auld) [2033084]
- sched: padding for struct rq and related (Phil Auld) [2033084]
- sched: Padding for sched_domain and root_domain (Phil Auld) [2033084]
- sched: Padding for task_struct and related in include/linux/sched.h (Phil Auld) [2033084]
- hwmon: (k10temp) Support up to 12 CCDs on AMD Family of processors (David Arcari) [2022526]
- hwmon: (k10temp) Add support for AMD Family 19h Models 10h-1Fh and A0h-AFh (David Arcari) [2022526]
- hwmon: (k10temp) Remove unused definitions (David Arcari) [2022526]
- x86/amd_nb: Add AMD Family 19h Models (10h-1Fh) and (A0h-AFh) PCI IDs (David Arcari) [2022526]
- hwmon: (k10temp) Remove residues of current and voltage (David Arcari) [2022526]
- tipc: check for null after calling kmemdup (Xin Long) [2024993]
- tipc: only accept encrypted MSG_CRYPTO msgs (Xin Long) [2024993]
- tipc: constify dev_addr passing (Xin Long) [2024993]
- tipc: increase timeout in tipc_sk_enqueue() (Xin Long) [2024993]
- tipc: clean up inconsistent indenting (Xin Long) [2024993]
- redhat: configs: add CONFIG_NTB and related items (John Linville) [1874186]

* Fri Jan 28 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-50.el9]
- net: fix possible NULL deref in sock_reserve_memory (Paolo Abeni) [2028420]
- mptcp: fix per socket endpoint accounting (Paolo Abeni) [2028420]
- mptcp: Check reclaim amount before reducing allocation (Paolo Abeni) [2028420]
- mptcp: fix a DSS option writing error (Paolo Abeni) [2028420]
- mptcp: fix opt size when sending DSS + MP_FAIL (Paolo Abeni) [2028420]
- mptcp: clean up harmless false expressions (Paolo Abeni) [2028420]
- selftests: mptcp: try to set mptcp ulp mode in different sk states (Paolo Abeni) [2028420]
- mptcp: enforce HoL-blocking estimation (Paolo Abeni) [2028420]
- mptcp: fix deadlock in __mptcp_push_pending() (Paolo Abeni) [2028420]
- mptcp: clear 'kern' flag from fallback sockets (Paolo Abeni) [2028420]
- mptcp: remove tcp ulp setsockopt support (Paolo Abeni) [2028420]
- mptcp: never allow the PM to close a listener subflow (Paolo Abeni) [2028420]
- selftests: mptcp: remove duplicate include in mptcp_inq.c (Paolo Abeni) [2028420]
- mptcp: support TCP_CORK and TCP_NODELAY (Paolo Abeni) [2028420]
- mptcp: expose mptcp_check_and_set_pending (Paolo Abeni) [2028420]
- tcp: expose __tcp_sock_set_cork and __tcp_sock_set_nodelay (Paolo Abeni) [2028420]
- selftests: mptcp: check IP_TOS in/out are the same (Paolo Abeni) [2028420]
- mptcp: getsockopt: add support for IP_TOS (Paolo Abeni) [2028420]
- mptcp: allow changing the "backup" bit by endpoint id (Paolo Abeni) [2028420]
- selftests: mptcp: add inq test case (Paolo Abeni) [2028420]
- mptcp: add SIOCINQ, OUTQ and OUTQNSD ioctls (Paolo Abeni) [2028420]
- selftests: mptcp: add TCP_INQ support (Paolo Abeni) [2028420]
- mptcp: add TCP_INQ cmsg support (Paolo Abeni) [2028420]
- mptcp: use delegate action to schedule 3rd ack retrans (Paolo Abeni) [2028420]
- mptcp: fix delack timer (Paolo Abeni) [2028420]
- selftests: mptcp: add tproxy test case (Paolo Abeni) [2028420]
- mptcp: sockopt: add SOL_IP freebind & transparent options (Paolo Abeni) [2028420]
- mptcp: Support for IP_TOS for MPTCP setsockopt() (Paolo Abeni) [2028420]
- ipv4: Exposing __ip_sock_set_tos() in ip.h (Paolo Abeni) [2028420]
- selftests: mptcp: more stable simult_flows tests (Paolo Abeni) [2028420]
- selftests: mptcp: fix proto type in link_failure tests (Paolo Abeni) [2028420]
- mptcp: fix corrupt receiver key in MPC + data + checksum (Paolo Abeni) [2028420]
- mptcp: drop unused sk in mptcp_push_release (Paolo Abeni) [2028420]
- mptcp: allocate fwd memory separately on the rx and tx path (Paolo Abeni) [2028420]
- net: introduce sk_forward_alloc_get() (Paolo Abeni) [2028420]
- tcp: define macros for a couple reclaim thresholds (Paolo Abeni) [2028420]
- net: add new socket option SO_RESERVE_MEM (Paolo Abeni) [2028420]
- mptcp: Make mptcp_pm_nl_mp_prio_send_ack() static (Paolo Abeni) [2028420]
- mptcp: increase default max additional subflows to 2 (Paolo Abeni) [2028420]
- mptcp: Avoid NULL dereference in mptcp_getsockopt_subflow_addrs() (Paolo Abeni) [2028420]
- mptcp: fix possible stall on recvmsg() (Paolo Abeni) [2028420]
- mptcp: use batch snmp operations in mptcp_seq_show() (Paolo Abeni) [2028420]
- net: snmp: inline snmp_get_cpu_field() (Paolo Abeni) [2028420]
- net: introduce and use lock_sock_fast_nested() (Paolo Abeni) [2028420]
- net: core: Correct the sock::sk_lock.owned lockdep annotations (Paolo Abeni) [2028420]
- mptcp: re-arm retransmit timer if data is pending (Paolo Abeni) [2028420]
- mptcp: remove tx_pending_data (Paolo Abeni) [2028420]
- mptcp: use lockdep_assert_held_once() instead of open-coding it (Paolo Abeni) [2028420]
- mptcp: use OPTIONS_MPTCP_MPC (Paolo Abeni) [2028420]
- mptcp: do not shrink snd_nxt when recovering (Paolo Abeni) [2028420]
- mptcp: allow changing the 'backup' bit when no sockets are open (Paolo Abeni) [2028420]
- mptcp: don't return sockets in foreign netns (Paolo Abeni) [2028420]
- tcp: remove sk_{tr}x_skb_cache (Paolo Abeni) [2028420]
- tcp: make tcp_build_frag() static (Paolo Abeni) [2028420]
- mptcp: stop relying on tcp_tx_skb_cache (Paolo Abeni) [2028420]
- tcp: expose the tcp_mark_push() and tcp_skb_entail() helpers (Paolo Abeni) [2028420]
- selftests: mptcp: add mptcp getsockopt test cases (Paolo Abeni) [2028420]
- mptcp: add MPTCP_SUBFLOW_ADDRS getsockopt support (Paolo Abeni) [2028420]
- mptcp: add MPTCP_TCPINFO getsockopt support (Paolo Abeni) [2028420]
- mptcp: add MPTCP_INFO getsockopt (Paolo Abeni) [2028420]
- mptcp: add new mptcp_fill_diag helper (Paolo Abeni) [2028420]
- mptcp: Only send extra TCP acks in eligible socket states (Paolo Abeni) [2028420]
- selftests: mptcp: clean tmp files in simult_flows (Paolo Abeni) [2028420]
- mptcp: ensure tx skbs always have the MPTCP ext (Paolo Abeni) [2028420]
- mptcp: fix possible divide by zero (Paolo Abeni) [2028420]
- mptcp: Fix duplicated argument in protocol.h (Paolo Abeni) [2028420]
- mptcp: make the locking tx schema more readable (Paolo Abeni) [2028420]
- mptcp: optimize the input options processing (Paolo Abeni) [2028420]
- mptcp: consolidate in_opt sub-options fields in a bitmask (Paolo Abeni) [2028420]
- mptcp: better binary layout for mptcp_options_received (Paolo Abeni) [2028420]
- mptcp: do not set unconditionally csum_reqd on incoming opt (Paolo Abeni) [2028420]
- selftests: mptcp: add MP_FAIL mibs check (Paolo Abeni) [2028420]
- mptcp: add the mibs for MP_FAIL (Paolo Abeni) [2028420]
- mptcp: send out MP_FAIL when data checksum fails (Paolo Abeni) [2028420]
- mptcp: MP_FAIL suboption receiving (Paolo Abeni) [2028420]
- mptcp: MP_FAIL suboption sending (Paolo Abeni) [2028420]
- mptcp: shrink mptcp_out_options struct (Paolo Abeni) [2028420]
- mptcp: optimize out option generation (Paolo Abeni) [2028420]
- selftests: mptcp: add_addr and echo race test (Paolo Abeni) [2028420]
- mptcp: remove MPTCP_ADD_ADDR_IPV6 and MPTCP_ADD_ADDR_PORT (Paolo Abeni) [2028420]
- mptcp: build ADD_ADDR/echo-ADD_ADDR option according pm.add_signal (Paolo Abeni) [2028420]
- mptcp: fix ADD_ADDR and RM_ADDR maybe flush addr_signal each other (Paolo Abeni) [2028420]
- mptcp: make MPTCP_ADD_ADDR_SIGNAL and MPTCP_ADD_ADDR_ECHO separate (Paolo Abeni) [2028420]
- mptcp: move drop_other_suboptions check under pm lock (Paolo Abeni) [2028420]
- selftests: mptcp: delete uncontinuous removing ids (Paolo Abeni) [2028420]
- selftests: mptcp: add fullmesh testcases (Paolo Abeni) [2028420]
- selftests: mptcp: set and print the fullmesh flag (Paolo Abeni) [2028420]
- mptcp: local addresses fullmesh (Paolo Abeni) [2028420]
- mptcp: remote addresses fullmesh (Paolo Abeni) [2028420]
- mptcp: drop flags and ifindex arguments (Paolo Abeni) [2028420]
- selftests: mptcp: add testcase for active-back (Paolo Abeni) [2028420]
- mptcp: backup flag from incoming MPJ ack option (Paolo Abeni) [2028420]
- mptcp: add mibs for stale subflows processing (Paolo Abeni) [2028420]
- mptcp: faster active backup recovery (Paolo Abeni) [2028420]
- mptcp: cleanup sysctl data and helpers (Paolo Abeni) [2028420]
- mptcp: handle pending data on closed subflow (Paolo Abeni) [2028420]
- mptcp: less aggressive retransmission strategy (Paolo Abeni) [2028420]
- mptcp: more accurate timeout (Paolo Abeni) [2028420]
- ionic: no devlink_unregister if not registered (Petr Oros) [2032260]
- devlink: fix netns refcount leak in devlink_nl_cmd_reload() (Petr Oros) [2032260]
- devlink: Don't throw an error if flash notification sent before devlink visible (Petr Oros) [2032260]
- devlink: make all symbols GPL-only (Petr Oros) [2032260]
- devlink: Simplify internal devlink params implementation (Petr Oros) [2032260]
- devlink: Clean not-executed param notifications (Petr Oros) [2032260]
- devlink: Delete obsolete parameters publish API (Petr Oros) [2032260]
- devlink: Remove extra device_lock assert checks (Petr Oros) [2032260]
- devlink: Delete reload enable/disable interface (Petr Oros) [2032260]
- net/mlx5: Set devlink reload feature bit for supported devices only (Petr Oros) [2032260]
- devlink: Allow control devlink ops behavior through feature mask (Petr Oros) [2032260]
- devlink: Annotate devlink API calls (Petr Oros) [2032260]
- devlink: Move netdev_to_devlink helpers to devlink.c (Petr Oros) [2032260]
- devlink: Reduce struct devlink exposure (Petr Oros) [2032260]
- devlink: report maximum number of snapshots with regions (Petr Oros) [2032260]
- devlink: Add missed notifications iterators (Petr Oros) [2032260]
- netdevsim: Move devlink registration to be last devlink command (Petr Oros) [2032260]
- qed: Move devlink registration to be last devlink command (Petr Oros) [2032260]
- ionic: Move devlink registration to be last devlink command (Petr Oros) [2032260]
- nfp: Move delink_register to be last command (Petr Oros) [2032260]
- mlxsw: core: Register devlink instance last (Petr Oros) [2032260]
- net/mlx5: Accept devlink user input after driver initialization complete (Petr Oros) [2032260]
- net/mlx4: Move devlink_register to be the last initialization command (Petr Oros) [2032260]
- ice: Open devlink when device is ready (Petr Oros) [2032260]
- net: hinic: Open device for the user access when it is ready (Petr Oros) [2032260]
- bnxt_en: Register devlink instance at the end devlink configuration (Petr Oros) [2032260]
- devlink: Notify users when objects are accessible (Petr Oros) [2032260]
- net/mlx5: Fix rdma aux device on devlink reload (Petr Oros) [2032260]
- qed: Don't ignore devlink allocation failures (Petr Oros) [2032260]
- ice: Delete always true check of PF pointer (Petr Oros) [2032260]
- devlink: Remove single line function obfuscations (Petr Oros) [2032260]
- devlink: Delete not used port parameters APIs (Petr Oros) [2032260]
- bnxt_en: Properly remove port parameter support (Petr Oros) [2032260]
- bnxt_en: Check devlink allocation and registration status (Petr Oros) [2032260]
- devlink: Make devlink_register to be void (Petr Oros) [2032260]
- devlink: Delete not-used devlink APIs (Petr Oros) [2032260]
- devlink: Delete not-used single parameter notification APIs (Petr Oros) [2032260]
- net/mlx5: Publish and unpublish all devlink parameters at once (Petr Oros) [2032260]
- devlink: Use xarray to store devlink instances (Petr Oros) [2032260]
- devlink: Count struct devlink consumers (Petr Oros) [2032260]
- devlink: Remove check of always valid devlink pointer (Petr Oros) [2032260]
- devlink: Simplify devlink_pernet_pre_exit call (Petr Oros) [2032260]
- net/mlx5: Support enable_vnet devlink dev param (Petr Oros) [2032260]
- net/mlx5: Support enable_rdma devlink dev param (Petr Oros) [2032260]
- net/mlx5: Support enable_eth devlink dev param (Petr Oros) [2032260]
- net/mlx5: Fix unpublish devlink parameters (Petr Oros) [2032260]
- devlink: Add APIs to publish, unpublish individual parameter (Petr Oros) [2032260]
- devlink: Add API to register and unregister single parameter (Petr Oros) [2032260]
- devlink: Create a helper function for one parameter registration (Petr Oros) [2032260]
- devlink: Add new "enable_vnet" generic device param (Petr Oros) [2032260]
- devlink: Add new "enable_rdma" generic device param (Petr Oros) [2032260]
- devlink: Add new "enable_eth" generic device param (Petr Oros) [2032260]
- devlink: Fix port_type_set function pointer check (Petr Oros) [2032260]
- devlink: Set device as early as possible (Petr Oros) [2032260]
- devlink: Simplify devlink port API calls (Petr Oros) [2032260]
- devlink: Allocate devlink directly in requested net namespace (Petr Oros) [2032260]
- devlink: Remove duplicated registration check (Petr Oros) [2032260]
- netdevsim: Protect both reload_down and reload_up paths (Petr Oros) [2032260]
- netdevsim: Forbid devlink reload when adding or deleting ports (Petr Oros) [2032260]
- net/mlx5: Don't rely on always true registered field (Petr Oros) [2032260]
- ionic: cleanly release devlink instance (Petr Oros) [2032260]
- selftests: net: bridge: fix typo in vlan_filtering dependency test (Ivan Vecera) [2037335]
- selftests: net: bridge: add test for vlan_filtering dependency (Ivan Vecera) [2037335]
- selftests: net: bridge: add vlan mcast_router tests (Ivan Vecera) [2037335]
- selftests: net: bridge: add vlan mcast query and query response interval tests (Ivan Vecera) [2037335]
- selftests: net: bridge: add vlan mcast_querier_interval tests (Ivan Vecera) [2037335]
- selftests: net: bridge: add vlan mcast_membership_interval test (Ivan Vecera) [2037335]
- selftests: net: bridge: add vlan mcast_startup_query_count/interval tests (Ivan Vecera) [2037335]
- selftests: net: bridge: add vlan mcast_last_member_count/interval tests (Ivan Vecera) [2037335]
- selftests: net: bridge: add vlan mcast igmp/mld version tests (Ivan Vecera) [2037335]
- selftests: net: bridge: add vlan mcast querier test (Ivan Vecera) [2037335]
- selftests: net: bridge: add vlan mcast snooping control test (Ivan Vecera) [2037335]
- net: bridge: mcast: fix br_multicast_ctx_vlan_global_disabled helper (Ivan Vecera) [2037335]
- net: bridge: mcast: add and enforce startup query interval minimum (Ivan Vecera) [2037335]
- net: bridge: mcast: add and enforce query interval minimum (Ivan Vecera) [2037335]
- net: bridge: fix ioctl old_deviceless bridge argument (Ivan Vecera) [2037335]
- net: bridge: Use array_size() helper in copy_to_user() (Ivan Vecera) [2037335]
- net: bridge: fix uninitialized variables when BRIDGE_CFM is disabled (Ivan Vecera) [2037335]
- net: bridge: mcast: use multicast_membership_interval for IGMPv3 (Ivan Vecera) [2037335]
- net: bridge: fix under estimation in br_get_linkxstats_size() (Ivan Vecera) [2037335]
- net: bridge: use nla_total_size_64bit() in br_get_linkxstats_size() (Ivan Vecera) [2037335]
- net: bridge: mcast: Associate the seqcount with its protecting lock. (Ivan Vecera) [2037335]
- net: bridge: mcast: fix vlan port router deadlock (Ivan Vecera) [2037335]
- net: bridge: use mld2r_ngrec instead of icmpv6_dataun (Ivan Vecera) [2037335]
- net: bridge: change return type of br_handle_ingress_vlan_tunnel (Ivan Vecera) [2037335]
- net: bridge: vlan: convert mcast router global option to per-vlan entry (Ivan Vecera) [2037335]
- net: bridge: mcast: br_multicast_set_port_router takes multicast context as argument (Ivan Vecera) [2037335]
- net: bridge: mcast: toggle also host vlan state in br_multicast_toggle_vlan (Ivan Vecera) [2037335]
- net: bridge: mcast: use the correct vlan group helper (Ivan Vecera) [2037335]
- net: bridge: vlan: account for router port lists when notifying (Ivan Vecera) [2037335]
- net: bridge: vlan: enable mcast snooping for existing master vlans (Ivan Vecera) [2037335]
- net: bridge: mcast: account for ipv6 size when dumping querier state (Ivan Vecera) [2037335]
- net: bridge: mcast: drop sizeof for nest attribute's zero size (Ivan Vecera) [2037335]
- net: bridge: mcast: don't dump querier state if snooping is disabled (Ivan Vecera) [2037335]
- net: bridge: vlan: dump mcast ctx querier state (Ivan Vecera) [2037335]
- net: bridge: mcast: dump ipv6 querier state (Ivan Vecera) [2037335]
- net: bridge: mcast: dump ipv4 querier state (Ivan Vecera) [2037335]
- net: bridge: mcast: consolidate querier selection for ipv4 and ipv6 (Ivan Vecera) [2037335]
- net: bridge: mcast: make sure querier port/address updates are consistent (Ivan Vecera) [2037335]
- net: bridge: mcast: record querier port device ifindex instead of pointer (Ivan Vecera) [2037335]
- net: bridge: vlan: use br_rports_fill_info() to export mcast router ports (Ivan Vecera) [2037335]
- net: bridge: mcast: use the proper multicast context when dumping router ports (Ivan Vecera) [2037335]
- net: bridge: vlan: add support for mcast router global option (Ivan Vecera) [2037335]
- net: bridge: vlan: add support for mcast querier global option (Ivan Vecera) [2037335]
- net: bridge: mcast: querier and query state affect only current context type (Ivan Vecera) [2037335]
- net: bridge: mcast: move querier state to the multicast context (Ivan Vecera) [2037335]
- net: bridge: vlan: add support for mcast startup query interval global option (Ivan Vecera) [2037335]
- net: bridge: vlan: add support for mcast query response interval global option (Ivan Vecera) [2037335]
- net: bridge: vlan: add support for mcast query interval global option (Ivan Vecera) [2037335]
- net: bridge: vlan: add support for mcast querier interval global option (Ivan Vecera) [2037335]
- net: bridge: vlan: add support for mcast membership interval global option (Ivan Vecera) [2037335]
- net: bridge: vlan: add support for mcast last member interval global option (Ivan Vecera) [2037335]
- net: bridge: vlan: add support for mcast startup query count global option (Ivan Vecera) [2037335]
- net: bridge: vlan: add support for mcast last member count global option (Ivan Vecera) [2037335]
- net: bridge: vlan: add support for mcast igmp/mld version global options (Ivan Vecera) [2037335]
- net: bridge: vlan: fix global vlan option range dumping (Ivan Vecera) [2037335]
- net: make switchdev_bridge_port_{,unoffload} loosely coupled with the bridge (Ivan Vecera) [2037335]
- net: bridge: switchdev: fix incorrect use of FDB flags when picking the dst device (Ivan Vecera) [2037335]
- net: bridge: switchdev: treat local FDBs the same as entries towards the bridge (Ivan Vecera) [2037335]
- net: bridge: switchdev: replay the entire FDB for each port (Ivan Vecera) [2037335]
- net: bridge: add a helper for retrieving port VLANs from the data path (Ivan Vecera) [2037335]
- net: bridge: update BROPT_VLAN_ENABLED before notifying switchdev in br_vlan_filter_toggle (Ivan Vecera) [2037335]
- net: bridge: fix build when setting skb->offload_fwd_mark with CONFIG_NET_SWITCHDEV=n (Ivan Vecera) [2037335]
- net: bridge: switchdev: allow the TX data plane forwarding to be offloaded (Ivan Vecera) [2037335]
- net: switchdev: fix FDB entries towards foreign ports not getting propagated to us (Ivan Vecera) [2037335]
- net: bridge: move the switchdev object replay helpers to "push" mode (Ivan Vecera) [2037335]
- net: bridge: guard the switchdev replay helpers against a NULL notifier block (Ivan Vecera) [2037335]
- net: bridge: switchdev: let drivers inform which bridge ports are offloaded (Ivan Vecera) [2037335]
- net: bridge: switchdev: recycle unused hwdoms (Ivan Vecera) [2037335]
- net: bridge: disambiguate offload_fwd_mark (Ivan Vecera) [2037335]
- net: bridge: multicast: add context support for host-joined groups (Ivan Vecera) [2037335]
- net: bridge: multicast: add mdb context support (Ivan Vecera) [2037335]
- net: bridge: multicast: fix igmp/mld port context null pointer dereferences (Ivan Vecera) [2037335]
- net: switchdev: recurse into __switchdev_handle_fdb_del_to_device (Ivan Vecera) [2037335]
- net: switchdev: remove stray semicolon in switchdev_handle_fdb_del_to_device shim (Ivan Vecera) [2037335]
- net: bridge: vlan: add mcast snooping control (Ivan Vecera) [2037335]
- net: bridge: vlan: notify when global options change (Ivan Vecera) [2037335]
- net: bridge: vlan: add support for dumping global vlan options (Ivan Vecera) [2037335]
- net: bridge: vlan: add support for global options (Ivan Vecera) [2037335]
- net: bridge: multicast: include router port vlan id in notifications (Ivan Vecera) [2037335]
- net: bridge: multicast: add vlan querier and query support (Ivan Vecera) [2037335]
- net: bridge: multicast: check if should use vlan mcast ctx (Ivan Vecera) [2037335]
- net: bridge: multicast: use the port group to port context helper (Ivan Vecera) [2037335]
- net: bridge: multicast: add helper to get port mcast context from port group (Ivan Vecera) [2037335]
- net: bridge: add vlan mcast snooping knob (Ivan Vecera) [2037335]
- net: bridge: multicast: add vlan state initialization and control (Ivan Vecera) [2037335]
- net: bridge: vlan: add global and per-port multicast context (Ivan Vecera) [2037335]
- net: bridge: multicast: use multicast contexts instead of bridge or port (Ivan Vecera) [2037335]
- net: bridge: multicast: factor out bridge multicast context (Ivan Vecera) [2037335]
- net: bridge: multicast: factor out port multicast context (Ivan Vecera) [2037335]
- net: switchdev: introduce a fanout helper for SWITCHDEV_FDB_{ADD,DEL}_TO_DEVICE (Ivan Vecera) [2037335]
- net: switchdev: introduce helper for checking dynamically learned FDB entries (Ivan Vecera) [2037335]
- kernel: Add redhat code (Prarit Bhargava) [2047259]
- nvme: Mark NVMe over FC Target support unmaintained (Prarit Bhargava) [2019379]
- hdlc_fr: Mark driver unmaintained (Prarit Bhargava) [2019379]
- sfc: Mark siena driver unmaintained (Prarit Bhargava) [2019379]
- qla3xxx: Mark driver unmaintained (Prarit Bhargava) [2019379]
- netxen: Mark nic driver unmaintained (Prarit Bhargava) [2019379]
- redhat/configs: Disable ethoc driver (Prarit Bhargava) [2019379]
- redhat/configs: Disable dnet driver (Prarit Bhargava) [2019379]
- drivers/pci/pci-driver.c: Fix if/ifdef typo (Prarit Bhargava) [2019379]
- kernel/rh_taint.c: Update to new messaging (Prarit Bhargava) [2019379]

* Wed Jan 26 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-49.el9]
- net: skb: use kfree_skb_reason() in __udp4_lib_rcv() (Antoine Tenart) [2041931]
- net: skb: use kfree_skb_reason() in tcp_v4_rcv() (Antoine Tenart) [2041931]
- net: skb: introduce kfree_skb_reason() (Antoine Tenart) [2041931]
- net: add kerneldoc comment for sk_peer_lock (Guillaume Nault) [2037783]
- af_unix: fix races in sk_peer_pid and sk_peer_cred accesses (Guillaume Nault) [2037783] {CVE-2021-4203}
- netfilter: nat: force port remap to prevent shadowing well-known ports (Florian Westphal) [2006169] {CVE-2021-3773}
- netfilter: conntrack: tag conntracks picked up in local out hook (Florian Westphal) [2006169]
- selftests: nft_nat: switch port shadow test cases to socat (Florian Westphal) [2006169]
- selftests: nft_nat: Simplify port shadow notrack test (Florian Westphal) [2006169]
- selftests: nft_nat: Improve port shadow test stability (Florian Westphal) [2006169]
- selftests: nft_nat: add udp hole punch test case (Florian Westphal) [2006169]
- net: Remove redundant if statements (Petr Oros) [2037315]
- netdevice: add the case if dev is NULL (Petr Oros) [2037315]
- redhat: fix the exclusion of rhdocs changes entries in the changelog (Herton R. Krzesinski)
- get_maintainer.conf: Update with new location of RHMAINTAINERS (Prarit Bhargava)
- redhat: make pathspec exclusion compatible with old git versions (Herton R. Krzesinski)
- redhat/scripts: Update merge-subtrees.sh with new subtree location (Prarit Bhargava)
- tree: remove existing redhat/rhdocs subtree in 9.0 (Prarit Bhargava)
- CI: Use realtime_check_baseline template (Veronika Kabatova)
- powerpc/fadump: Fix inaccurate CPU state info in vmcore generated with panic (Gustavo Walbon) [2025518]
- powerpc: handle kdump appropriately with crash_kexec_post_notifiers option (Gustavo Walbon) [2025518]
- powerpc/pseries: use slab context cpumask allocation in CPU hotplug init (Waiman Long) [2019671]
- powerpc/pseries: Fix build error when NUMA=n (Waiman Long) [2019671]
- powerpc/smp: Use existing L2 cache_map cpumask to find L3 cache siblings (Diego Domingos) [2039639]
- powerpc/cacheinfo: Remove the redundant get_shared_cpu_map() (Diego Domingos) [2039639]
- powerpc/cacheinfo: Lookup cache by dt node and thread-group id (Diego Domingos) [2039639]
- powerpc: select CPUMASK_OFFSTACK if NR_CPUS >= 8192 (Diego Domingos) [2039163]
- powerpc: remove cpu_online_cores_map function (Diego Domingos) [2039163]
- adding support for c9s automotive coverage build (bgrech)
- CI: Use tagged containers (Veronika Kabatova)
- xfs: map unwritten blocks in XFS_IOC_{ALLOC,FREE}SP just like fallocate (Carlos Maiolino) [2034871] {CVE-2021-4155}
- selftests/powerpc: skip tests for unavailable mitigations. (Diego Domingos) [2021389]
- selftests/powerpc: Use date instead of EPOCHSECONDS in mitigation-patching.sh (Diego Domingos) [2021389]
- ip6_vti: initialize __ip6_tnl_parm struct in vti6_siocdevprivate (William Zhao) [2037810]
- KVM: x86: Wait for IPIs to be delivered when handling Hyper-V TLB flush hypercall (Vitaly Kuznetsov) [2036570]
- net: vlan: fix underflow for the real_dev refcnt (Balazs Nemeth) [2030036]
- net: vlan: fix a UAF in vlan_dev_real_dev() (Balazs Nemeth) [2030036]

* Mon Jan 24 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-48.el9]
- net: mana: Add RX fencing (Mohammed Gamal) [2030357]
- net: mana: Add XDP support (Mohammed Gamal) [2030357]
- net: mana: Fix memory leak in mana_hwc_create_wq (Mohammed Gamal) [2030357]
- net: mana: Fix spelling mistake "calledd" -> "called" (Mohammed Gamal) [2030357]
- ibmvnic: drop bad optimization in reuse_tx_pools() (Diego Domingos) [2014236]
- ibmvnic: drop bad optimization in reuse_rx_pools() (Diego Domingos) [2014236]
- ibmvnic: Reuse tx pools when possible (Diego Domingos) [2014236]
- ibmvnic: Reuse rx pools when possible (Diego Domingos) [2014236]
- ibmvnic: Reuse LTB when possible (Diego Domingos) [2014236]
- ibmvnic: init_tx_pools move loop-invariant code (Diego Domingos) [2014236]
- ibmvnic: Use/rename local vars in init_tx_pools (Diego Domingos) [2014236]
- ibmvnic: Use/rename local vars in init_rx_pools (Diego Domingos) [2014236]
- ibmvnic: Consolidate code in replenish_rx_pool() (Diego Domingos) [2014236]
- ibmvnic: Fix up some comments and messages (Diego Domingos) [2014236]
- ibmvnic: Use bitmap for LTB map_ids (Diego Domingos) [2014236]
- [s390] s390/qeth: fix deadlock during failing recovery (Mete Durlu) [1869669]
- [s390] s390/qeth: Fix deadlock in remove_discipline (Mete Durlu) [1869669]
- [s390] s390/qeth: fix NULL deref in qeth_clear_working_pool_list() (Mete Durlu) [1869669]
- [s390] s390/qeth: Update MACs of LEARNING_SYNC device (Mete Durlu) [1869669]
- [s390] s390/qeth: Switchdev event handler (Mete Durlu) [1869669]
- [s390] s390/qeth: Register switchdev event handler (Mete Durlu) [1869669]
- [s390] s390/qdio: propagate error when cancelling a ccw fails (Mete Durlu) [1869669]
- [s390] s390/qdio: improve roll-back after error on ESTABLISH ccw (Mete Durlu) [1869669]
- [s390] s390/qdio: cancel the ESTABLISH ccw after timeout (Mete Durlu) [1869669]
- [s390] s390/qdio: fix roll-back after timeout on ESTABLISH ccw (Mete Durlu) [1869669]
- [s390] s390/qeth: remove OSN support (Mete Durlu) [1869669]
- [s390] s390: add HWCAP_S390_PCI_MIO to ELF hwcaps (Mete Durlu) [2030640]
- [s390] s390: make PCI mio support a machine flag (Mete Durlu) [2030640]
- ima: silence measurement list hexdump during kexec (Bruno Meneguele) [2034157]
- scsi: lpfc: Update lpfc version to 14.0.0.4 (Dick Kennedy) [2034278]
- scsi: lpfc: Add additional debugfs support for CMF (Dick Kennedy) [2034278]
- scsi: lpfc: Cap CMF read bytes to MBPI (Dick Kennedy) [2034278]
- scsi: lpfc: Adjust CMF total bytes and rxmonitor (Dick Kennedy) [2034278]
- scsi: lpfc: Trigger SLI4 firmware dump before doing driver cleanup (Dick Kennedy) [2034278]
- scsi: lpfc: Fix NPIV port deletion crash (Dick Kennedy) [2034278]
- scsi: lpfc: Fix lpfc_force_rscn ndlp kref imbalance (Dick Kennedy) [2034278]
- scsi: lpfc: Change return code on I/Os received during link bounce (Dick Kennedy) [2034278]
- scsi: lpfc: Fix leaked lpfc_dmabuf mbox allocations with NPIV (Dick Kennedy) [2034278]
- scsi: lpfc: Fix non-recovery of remote ports following an unsolicited LOGO (Dick Kennedy) [2039036]
- mm/memcg: Exclude mem_cgroup pointer from kABI signature computation (Waiman Long) [2036995]
- NFS: Default change_attr_type to NFS4_CHANGE_TYPE_IS_UNDEFINED (Steve Dickson) [2016699]

* Sat Jan 22 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-47.el9]
- nvmet: register discovery subsystem as 'current' (John Meneghini) [2021672]
- nvme: add new discovery log page entry definitions (John Meneghini) [2021672]
- nvmet: switch check for subsystem type (John Meneghini) [2021672]
- nvme: display correct subsystem NQN (John Meneghini) [2021672]
- nvme: Add connect option 'discovery' (John Meneghini) [2021672]
- nvme: expose subsystem type in sysfs attribute 'subsystype' (John Meneghini) [2021672]
- nvmet: set 'CNTRLTYPE' in the identify controller data (John Meneghini) [2021672]
- nvmet: add nvmet_is_disc_subsys() helper (John Meneghini) [2021672]
- nvme: add CNTRLTYPE definitions for 'identify controller' (John Meneghini) [2021672]
- nvmet: make discovery NQN configurable (John Meneghini) [2021672]
- nitro_enclaves: Use get_user_pages_unlocked() call to handle mmap assert (Vitaly Kuznetsov) [2034619]
- include/linux/pci.h: Exclude struct hotplug_slot from KABI (Prarit Bhargava) [2034338]
- virtio/vsock: fix the transport to work with VMADDR_CID_ANY (Stefano Garzarella) [2026949]
- vhost/vsock: cleanup removing `len` variable (Stefano Garzarella) [2026949]
- vhost/vsock: fix incorrect used length reported to the guest (Stefano Garzarella) [2026949]
- vsock: prevent unnecessary refcnt inc for nonblocking connect (Stefano Garzarella) [2026949]
- vsock_diag_test: remove free_sock_stat() call in test_no_sockets (Stefano Garzarella) [2026949]
- vsock: Enable y2038 safe timeval for timeout (Stefano Garzarella) [2026949]
- vsock: Refactor vsock_*_getsockopt to resemble sock_getsockopt (Stefano Garzarella) [2026949]
- vsock_test: update message bounds test for MSG_EOR (Stefano Garzarella) [2026949]
- af_vsock: rename variables in receive loop (Stefano Garzarella) [2026949]
- virtio/vsock: support MSG_EOR bit processing (Stefano Garzarella) [2026949]
- vhost/vsock: support MSG_EOR bit processing (Stefano Garzarella) [2026949]
- virtio/vsock: add 'VIRTIO_VSOCK_SEQ_EOR' bit. (Stefano Garzarella) [2026949]
- virtio/vsock: rename 'EOR' to 'EOM' bit. (Stefano Garzarella) [2026949]
- include/linux/irq*.h: Pad irq structs for KABI (Prarit Bhargava) [2034264]
- include/linux/fwnode.h: Exclude fwnode structs from KABI (Prarit Bhargava) [2033388]
- bpf: Fix toctou on read-only map's constant scalar tracking (Jiri Olsa) [2029198] {CVE-2021-4001}
- ACPI: tables: FPDT: Do not print FW_BUG message if record types are reserved (Mark Langsdorf) [2000202]
- redhat: support virtio-mem on x86-64 as tech-preview (David Hildenbrand) [2014492]
- proc/vmcore: fix clearing user buffer by properly using clear_user() (David Hildenbrand) [2014492]
- virtio-mem: support VIRTIO_MEM_F_UNPLUGGED_INACCESSIBLE (David Hildenbrand) [2014492]
- virtio-mem: disallow mapping virtio-mem memory via /dev/mem (David Hildenbrand) [2014492]
- kernel/resource: disallow access to exclusive system RAM regions (David Hildenbrand) [2014492]
- kernel/resource: clean up and optimize iomem_is_exclusive() (David Hildenbrand) [2014492]
- virtio-mem: kdump mode to sanitize /proc/vmcore access (David Hildenbrand) [2014492]
- virtio-mem: factor out hotplug specifics from virtio_mem_remove() into virtio_mem_deinit_hotplug() (David Hildenbrand) [2014492]
- virtio-mem: factor out hotplug specifics from virtio_mem_probe() into virtio_mem_init_hotplug() (David Hildenbrand) [2014492]
- virtio-mem: factor out hotplug specifics from virtio_mem_init() into virtio_mem_init_hotplug() (David Hildenbrand) [2014492]
- proc/vmcore: convert oldmem_pfn_is_ram callback to more generic vmcore callbacks (David Hildenbrand) [2014492]
- proc/vmcore: let pfn_is_ram() return a bool (David Hildenbrand) [2014492]
- x86/xen: print a warning when HVMOP_get_mem_type fails (David Hildenbrand) [2014492]
- x86/xen: simplify xen_oldmem_pfn_is_ram() (David Hildenbrand) [2014492]
- x86/xen: update xen_oldmem_pfn_is_ram() documentation (David Hildenbrand) [2014492]

* Thu Jan 20 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-46.el9]
- crypto: qat - fix definition of ring reset results (Vladis Dronov) [2015145]
- crypto: qat - add support for compression for 4xxx (Vladis Dronov) [2015145]
- crypto: qat - allow detection of dc capabilities for 4xxx (Vladis Dronov) [2015145]
- crypto: qat - add PFVF support to enable the reset of ring pairs (Vladis Dronov) [2015145]
- crypto: qat - add PFVF support to the GEN4 host driver (Vladis Dronov) [2015145]
- crypto: qat - config VFs based on ring-to-svc mapping (Vladis Dronov) [2015145]
- crypto: qat - exchange ring-to-service mappings over PFVF (Vladis Dronov) [2015145]
- crypto: qat - support fast ACKs in the PFVF protocol (Vladis Dronov) [2015145]
- crypto: qat - exchange device capabilities over PFVF (Vladis Dronov) [2015145]
- crypto: qat - introduce support for PFVF block messages (Vladis Dronov) [2015145]
- crypto: qat - store the ring-to-service mapping (Vladis Dronov) [2015145]
- crypto: qat - store the PFVF protocol version of the endpoints (Vladis Dronov) [2015145]
- crypto: qat - improve the ACK timings in PFVF send (Vladis Dronov) [2015145]
- crypto: qat - leverage read_poll_timeout in PFVF send (Vladis Dronov) [2015145]
- crypto: qat - leverage bitfield.h utils for PFVF messages (Vladis Dronov) [2015145]
- crypto: qat - abstract PFVF messages with struct pfvf_message (Vladis Dronov) [2015145]
- crypto: qat - set PFVF_MSGORIGIN just before sending (Vladis Dronov) [2015145]
- crypto: qat - make PFVF send and receive direction agnostic (Vladis Dronov) [2015145]
- crypto: qat - make PFVF message construction direction agnostic (Vladis Dronov) [2015145]
- crypto: qat - add the adf_get_pmisc_base() helper function (Vladis Dronov) [2015145]
- crypto: qat - support the reset of ring pairs on PF (Vladis Dronov) [2015145]
- crypto: qat - extend crypto capability detection for 4xxx (Vladis Dronov) [2015145]
- crypto: qat - set COMPRESSION capability for QAT GEN2 (Vladis Dronov) [2015145]
- crypto: qat - set CIPHER capability for QAT GEN2 (Vladis Dronov) [2015145]
- crypto: qat - get compression extended capabilities (Vladis Dronov) [2015145]
- crypto: qat - improve logging of PFVF messages (Vladis Dronov) [2015145]
- crypto: qat - fix VF IDs in PFVF log messages (Vladis Dronov) [2015145]
- crypto: qat - do not rely on min version (Vladis Dronov) [2015145]
- crypto: qat - refactor pfvf version request messages (Vladis Dronov) [2015145]
- crypto: qat - pass the PF2VF responses back to the callers (Vladis Dronov) [2015145]
- crypto: qat - use enums for PFVF protocol codes (Vladis Dronov) [2015145]
- crypto: qat - reorganize PFVF protocol definitions (Vladis Dronov) [2015145]
- crypto: qat - reorganize PFVF code (Vladis Dronov) [2015145]
- crypto: qat - abstract PFVF receive logic (Vladis Dronov) [2015145]
- crypto: qat - abstract PFVF send function (Vladis Dronov) [2015145]
- crypto: qat - differentiate between pf2vf and vf2pf offset (Vladis Dronov) [2015145]
- crypto: qat - add pfvf_ops (Vladis Dronov) [2015145]
- crypto: qat - relocate PFVF disabled function (Vladis Dronov) [2015145]
- crypto: qat - relocate PFVF VF related logic (Vladis Dronov) [2015145]
- crypto: qat - relocate PFVF PF related logic (Vladis Dronov) [2015145]
- crypto: qat - handle retries due to collisions in adf_iov_putmsg() (Vladis Dronov) [2015145]
- crypto: qat - split PFVF message decoding from handling (Vladis Dronov) [2015145]
- crypto: qat - re-enable interrupts for legacy PFVF messages (Vladis Dronov) [2015145]
- crypto: qat - change PFVF ACK behaviour (Vladis Dronov) [2015145]
- crypto: qat - move interrupt code out of the PFVF handler (Vladis Dronov) [2015145]
- crypto: qat - move VF message handler to adf_vf2pf_msg.c (Vladis Dronov) [2015145]
- crypto: qat - move vf2pf interrupt helpers (Vladis Dronov) [2015145]
- crypto: qat - refactor PF top half for PFVF (Vladis Dronov) [2015145]
- crypto: qat - fix undetected PFVF timeout in ACK loop (Vladis Dronov) [2015145]
- crypto: qat - do not handle PFVF sources for qat_4xxx (Vladis Dronov) [2015145]
- crypto: qat - simplify adf_enable_aer() (Vladis Dronov) [2015145]
- crypto: qat - share adf_enable_pf2vf_comms() from adf_pf2vf_msg.c (Vladis Dronov) [2015145]
- crypto: qat - extract send and wait from adf_vf2pf_request_version() (Vladis Dronov) [2015145]
- crypto: qat - add VF and PF wrappers to common send function (Vladis Dronov) [2015145]
- crypto: qat - rename pfvf collision constants (Vladis Dronov) [2015145]
- crypto: qat - move pfvf collision detection values (Vladis Dronov) [2015145]
- crypto: qat - make pfvf send message direction agnostic (Vladis Dronov) [2015145]
- crypto: qat - use hweight for bit counting (Vladis Dronov) [2015145]
- crypto: qat - remove duplicated logic across GEN2 drivers (Vladis Dronov) [2015145]
- crypto: qat - fix handling of VF to PF interrupts (Vladis Dronov) [2015145]
- crypto: qat - remove unnecessary collision prevention step in PFVF (Vladis Dronov) [2015145]
- crypto: qat - disregard spurious PFVF interrupts (Vladis Dronov) [2015145]
- crypto: qat - detect PFVF collision after ACK (Vladis Dronov) [2015145]
- crypto: qat - power up 4xxx device (Vladis Dronov) [2015145]
- crypto: qat - remove unneeded packed attribute (Vladis Dronov) [2015145]
- crypto: qat - free irq in case of failure (Vladis Dronov) [2015145]
- crypto: qat - free irqs only if allocated (Vladis Dronov) [2015145]
- crypto: qat - remove unmatched CPU affinity to cluster IRQ (Vladis Dronov) [2015145]
- crypto: qat - replace deprecated MSI API (Vladis Dronov) [2015145]
- crypto: qat - store vf.compatible flag (Vladis Dronov) [2015145]
- crypto: qat - do not export adf_iov_putmsg() (Vladis Dronov) [2015145]
- crypto: qat - flush vf workqueue at driver removal (Vladis Dronov) [2015145]
- crypto: qat - remove the unnecessary get_vintmsk_offset() (Vladis Dronov) [2015145]
- crypto: qat - fix naming of PF/VF enable functions (Vladis Dronov) [2015145]
- crypto: qat - complete all the init steps before service notification (Vladis Dronov) [2015145]
- crypto: qat - move IO virtualization functions (Vladis Dronov) [2015145]
- crypto: qat - fix naming for init/shutdown VF to PF notifications (Vladis Dronov) [2015145]
- crypto: qat - protect interrupt mask CSRs with a spinlock (Vladis Dronov) [2015145]
- crypto: qat - move pf2vf interrupt [en|dis]able to adf_vf_isr.c (Vladis Dronov) [2015145]
- crypto: qat - fix reuse of completion variable (Vladis Dronov) [2015145]
- crypto: qat - remove intermediate tasklet for vf2pf (Vladis Dronov) [2015145]
- crypto: qat - rename compatibility version definition (Vladis Dronov) [2015145]
- crypto: qat - prevent spurious MSI interrupt in PF (Vladis Dronov) [2015145]
- crypto: qat - prevent spurious MSI interrupt in VF (Vladis Dronov) [2015145]
- crypto: qat - handle both source of interrupt in VF ISR (Vladis Dronov) [2015145]
- crypto: qat - do not ignore errors from enable_vf2pf_comms() (Vladis Dronov) [2015145]
- crypto: qat - enable interrupts only after ISR allocation (Vladis Dronov) [2015145]
- crypto: qat - remove empty sriov_configure() (Vladis Dronov) [2015145]
- crypto: qat - use proper type for vf_mask (Vladis Dronov) [2015145]
- crypto: qat - fix a typo in a comment (Vladis Dronov) [2015145]
- crypto: qat - disable AER if an error occurs in probe functions (Vladis Dronov) [2015145]
- crypto: qat - set DMA mask to 48 bits for Gen2 (Vladis Dronov) [2015145]
- crypto: qat - simplify code and axe the use of a deprecated API (Vladis Dronov) [2015145]

* Tue Jan 18 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-45.el9]
- workqueue, kasan: avoid alloc_pages() when recording stack (Phil Auld) [2022894]
- kasan: generic: introduce kasan_record_aux_stack_noalloc() (Phil Auld) [2022894]
- kasan: common: provide can_alloc in kasan_save_stack() (Phil Auld) [2022894]
- lib/stackdepot: introduce __stack_depot_save() (Phil Auld) [2022894]
- lib/stackdepot: remove unused function argument (Phil Auld) [2022894]
- lib/stackdepot: include gfp.h (Phil Auld) [2022894]
- workqueue: Introduce show_one_worker_pool and show_one_workqueue. (Phil Auld) [2022894]
- workqueue: make sysfs of unbound kworker cpumask more clever (Phil Auld) [2022894]
- workqueue: fix state-dump console deadlock (Phil Auld) [2022894]
- workqueue: Remove unused WORK_NO_COLOR (Phil Auld) [2022894]
- workqueue: Assign a color to barrier work items (Phil Auld) [2022894]
- workqueue: Mark barrier work with WORK_STRUCT_INACTIVE (Phil Auld) [2022894]
- workqueue: Change the code of calculating work_flags in insert_wq_barrier() (Phil Auld) [2022894]
- workqueue: Change arguement of pwq_dec_nr_in_flight() (Phil Auld) [2022894]
- workqueue: Rename "delayed" (delayed by active management) to "inactive" (Phil Auld) [2022894]
- workqueue: Replace deprecated ida_simple_*() with ida_alloc()/ida_free() (Phil Auld) [2022894]
- workqueue: Fix typo in comments (Phil Auld) [2022894]
- workqueue: Fix possible memory leaks in wq_numa_init() (Phil Auld) [2022894]
- nvme: avoid race in shutdown namespace removal (Ewan D. Milne) [2014529]
- powerpc/xmon: Dump XIVE information for online-only processors. (Steve Best) [2037642]
- ipv4: make exception cache less predictible (Antoine Tenart) [2015112] {CVE-2021-20322}
- [s390] s390/cio: make ccw_device_dma_* more robust (Claudio Imbrenda) [1997541]
- [s390] s390/pci: add s390_iommu_aperture kernel parameter (Claudio Imbrenda) [2034134]
- [s390] s390/pci: fix zpci_zdev_put() on reserve (Claudio Imbrenda) [2034132]
- [s390] s390/pci: cleanup resources only if necessary (Claudio Imbrenda) [2034132]
- [s390] s390/sclp: fix Secure-IPL facility detection (Claudio Imbrenda) [2034116]
- Revert "[redhat] Generate a crashkernel.default for each kernel build" (Coiby Xu) [2034490]
- ibmvnic: Process crqs after enabling interrupts (Diego Domingos) [2020021]
- ibmvnic: delay complete() (Diego Domingos) [2020021]
- ibmvnic: don't stop queue in xmit (Diego Domingos) [2019988]
- bpf/selftests: disable test failing on RHEL9 (Viktor Malik) [2006315]
- bpf/selftests: disable a verifier test for powerpc (Viktor Malik) [2032734]
- bpf/selftests: allow disabling tests (Viktor Malik) [2036656]
- kernel/crash_core: suppress unknown crashkernel parameter warning (Philipp Rudo) [2026570]
- mm/vmalloc: do not adjust the search size for alignment overhead (David Hildenbrand) [2029493]
- Bluetooth: fix use-after-free error in lock_sock_nested() (Gopal Tiwari) [2005691]
- lib: zstd: Don't add -O3 to cflags (Neal Gompa) [2034834]
- lib: zstd: Don't inline functions in zstd_opt.c (Neal Gompa) [2034834]
- lib: zstd: Fix unused variable warning (Neal Gompa) [2034834]
- lib: zstd: Add cast to silence clang's -Wbitwise-instead-of-logical (Neal Gompa) [2034834]
- MAINTAINERS: Add maintainer entry for zstd (Neal Gompa) [2034834]
- lib: zstd: Upgrade to latest upstream zstd version 1.4.10 (Neal Gompa) [2034834]
- lib: zstd: Add decompress_sources.h for decompress_unzstd (Neal Gompa) [2034834]
- lib: zstd: Add kernel-specific API (Neal Gompa) [2034834]

* Mon Jan 17 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-44.el9]
- dm btree remove: fix use after free in rebalance_children() (Benjamin Marzinski) [2031198]
- dm table: log table creation error code (Benjamin Marzinski) [2031198]
- dm: make workqueue names device-specific (Benjamin Marzinski) [2031198]
- dm writecache: Make use of the helper macro kthread_run() (Benjamin Marzinski) [2031198]
- dm crypt: Make use of the helper macro kthread_run() (Benjamin Marzinski) [2031198]
- dm: Remove redundant flush_workqueue() calls (Benjamin Marzinski) [2031198]
- dm crypt: log aead integrity violations to audit subsystem (Benjamin Marzinski) [2031198]
- dm integrity: log audit events for dm-integrity target (Benjamin Marzinski) [2031198]
- dm: introduce audit event module for device mapper (Benjamin Marzinski) [2031198]
- dm: fix mempool NULL pointer race when completing IO (Benjamin Marzinski) [2031198]
- dm rq: don't queue request to blk-mq during DM suspend (Benjamin Marzinski) [2031198]
- dm clone: make array 'descs' static (Benjamin Marzinski) [2031198]
- dm verity: skip redundant verity_handle_err() on I/O errors (Benjamin Marzinski) [2031198]
- dm crypt: use in_hardirq() instead of deprecated in_irq() (Benjamin Marzinski) [2031198]
- dm ima: update dm documentation for ima measurement support (Benjamin Marzinski) [2031198]
- dm ima: update dm target attributes for ima measurements (Benjamin Marzinski) [2031198]
- dm ima: add a warning in dm_init if duplicate ima events are not measured (Benjamin Marzinski) [2031198]
- dm ima: prefix ima event name related to device mapper with dm_ (Benjamin Marzinski) [2031198]
- dm ima: add version info to dm related events in ima log (Benjamin Marzinski) [2031198]
- dm ima: prefix dm table hashes in ima log with hash algorithm (Benjamin Marzinski) [2031198]
- dm crypt: Avoid percpu_counter spinlock contention in crypt_page_alloc() (Benjamin Marzinski) [2031198]
- dm: add documentation for IMA measurement support (Benjamin Marzinski) [2031198]
- dm: update target status functions to support IMA measurement (Benjamin Marzinski) [2031198]
- dm ima: measure data on device rename (Benjamin Marzinski) [2031198]
- dm ima: measure data on table clear (Benjamin Marzinski) [2031198]
- dm ima: measure data on device remove (Benjamin Marzinski) [2031198]
- dm ima: measure data on device resume (Benjamin Marzinski) [2031198]
- dm ima: measure data on table load (Benjamin Marzinski) [2031198]
- dm writecache: add event counters (Benjamin Marzinski) [2031198]
- dm writecache: report invalid return from writecache_map helpers (Benjamin Marzinski) [2031198]
- dm writecache: further writecache_map() cleanup (Benjamin Marzinski) [2031198]
- dm writecache: factor out writecache_map_remap_origin() (Benjamin Marzinski) [2031198]
- dm writecache: split up writecache_map() to improve code readability (Benjamin Marzinski) [2031198]
- redhat: Pull in openssl-devel as a build dependency correctly (Neal Gompa) [2034670]
- redhat/configs: Enable ThinkLMI support (Mark Pearson) [2030770]
- platform/x86: think-lmi: Abort probe on analyze failure (Mark Pearson) [2030770]
- platform/x86: think-lmi: add debug_cmd (Mark Pearson) [2030770]
- include/linux/timer.h: Pad timer_list struct for KABI (Prarit Bhargava) [2034452]
- kernel: Include RHEL Ecosystem message (Prarit Bhargava) [2033650]
- include/linux/ioport.h: Pad resource struct for KABI (Prarit Bhargava) [2033475]
- include/linux/hrtimer.h: Pad hrtimer struct for KABI (Prarit Bhargava) [2033473]
- redhat/configs: Add explicit values for ZRAM_DEF_COMP_LZ4* configs (Neal Gompa) [2032758]
- redhat/configs: Enable CONFIG_CRYPTO_ZSTD (Neal Gompa) [2032758]
- redhat/configs: Migrate defaults for ZRAM from pending-common to common (Neal Gompa) [2032758]
- Enable iSER on s390x (Stefan Schulze Frielinghaus) [1965279]

* Fri Jan 14 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-43.el9]
- mm: COW: restore full accuracy in page reuse (Andrea Arcangeli) [1958742]
- mm: thp: replace the page lock with the seqlock for the THP mapcount (Andrea Arcangeli) [1958742]
- mm: COW: skip the page lock in the COW copy path (Andrea Arcangeli) [1958742]
- mm: gup: gup_must_unshare() use can_read_pin_swap_page() (Andrea Arcangeli) [1958742]
- mm: hugetlbfs: gup: gup_must_unshare(): enable hugetlbfs (Andrea Arcangeli) [1958742]
- mm: hugetlbfs: FOLL_FAULT_UNSHARE (Andrea Arcangeli) [1958742]
- mm: hugetlbfs: COR: copy-on-read fault (Andrea Arcangeli) [1958742]
- mm: gup: FOLL_UNSHARE RHEL (Andrea Arcangeli) [1958742]
- mm: gup: FOLL_NOUNSHARE: optimize follow_page (Andrea Arcangeli) [1958742]
- mm: gup: FOLL_UNSHARE (Andrea Arcangeli) [1958742]
- mm: gup: gup_must_unshare() (Andrea Arcangeli) [1958742]
- mm: gup: COR: copy-on-read fault (Andrea Arcangeli) [1958742]
- mm: thp: introduce page_trans_huge_anon_shared (Andrea Arcangeli) [1958742]
- mm: thp: stabilize the THP mapcount in page_remove_anon_compound_rmap (Andrea Arcangeli) [1958742]
- mm: thp: make the THP mapcount atomic with a seqlock (Andrea Arcangeli) [1958742]
- mm: thp: consolidate mapcount logic on THP split (David Hildenbrand) [1958742]
- powerpc/xive: Change IRQ domain to a tree domain (Daniel Henrique Barboza) [2008723]
- tcp: fix page frag corruption on page fault (Paolo Abeni) [2028276]
- sock: fix /proc/net/sockstat underflow in sk_clone_lock() (Paolo Abeni) [2028276]
- net: add and use skb_unclone_keeptruesize() helper (Paolo Abeni) [2028276]
- net: stream: don't purge sk_error_queue in sk_stream_kill_queues() (Paolo Abeni) [2028276]
- net, neigh: Fix NTF_EXT_LEARNED in combination with NTF_USE (Paolo Abeni) [2028276]
- net-sysfs: initialize uid and gid before calling net_ns_get_ownership (Paolo Abeni) [2028276]
- net: Prevent infinite while loop in skb_tx_hash() (Paolo Abeni) [2028276]
- napi: fix race inside napi_enable (Paolo Abeni) [2028276]
- skb_expand_head() adjust skb->truesize incorrectly (Paolo Abeni) [2028276]
- bpf: use skb_expand_head in bpf_out_neigh_v4/6 (Paolo Abeni) [2028276]
- ax25: use skb_expand_head (Paolo Abeni) [2028276]
- vrf: fix NULL dereference in vrf_finish_output() (Paolo Abeni) [2028276]
- vrf: use skb_expand_head in vrf_finish_output (Paolo Abeni) [2028276]
- ipv4: use skb_expand_head in ip_finish_output2 (Paolo Abeni) [2028276]
- ipv6: use skb_expand_head in ip6_xmit (Paolo Abeni) [2028276]
- ipv6: use skb_expand_head in ip6_finish_output2 (Paolo Abeni) [2028276]
- skbuff: introduce skb_expand_head() (Paolo Abeni) [2028276]
- net/af_unix: fix a data-race in unix_dgram_poll (Paolo Abeni) [2028276]
- net: don't unconditionally copy_from_user a struct ifreq for socket ioctls (Paolo Abeni) [2028276]
- devlink: Clear whole devlink_flash_notify struct (Paolo Abeni) [2028276]
- devlink: Break parameter notification sequence to be before/after unload/load driver (Paolo Abeni) [2028276]
- vhost_net: fix OoB on sendmsg() failure. (Paolo Abeni) [2026821]
- printk: restore flushing of NMI buffers on remote CPUs after NMI backtraces (Prarit Bhargava) [2023082]
- lib/nmi_backtrace: Serialize even messages about idle CPUs (Prarit Bhargava) [2023082]
- printk: syslog: close window between wait and read (Prarit Bhargava) [2023082]
- printk: convert @syslog_lock to mutex (Prarit Bhargava) [2023082]
- printk: remove NMI tracking (Prarit Bhargava) [2023082]
- printk: remove safe buffers (Prarit Bhargava) [2023082]
- printk: track/limit recursion (Prarit Bhargava) [2023082]
- lib/nmi_backtrace: explicitly serialize banner and regs (Prarit Bhargava) [2023082]

* Thu Jan 13 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-42.el9]
- scsi: smartpqi: Update version to 2.1.12-055 (Don Brace) [1869853]
- scsi: smartpqi: Add 3252-8i PCI id (Don Brace) [1869853]
- scsi: smartpqi: Fix duplicate device nodes for tape changers (Don Brace) [1869853]
- scsi: smartpqi: Fix boot failure during LUN rebuild (Don Brace) [1869853]
- scsi: smartpqi: Add extended report physical LUNs (Don Brace) [1869853]
- scsi: smartpqi: Avoid failing I/Os for offline devices (Don Brace) [1869853]
- scsi: smartpqi: Add TEST UNIT READY check for SANITIZE operation (Don Brace) [1869853]
- scsi: smartpqi: Update LUN reset handler (Don Brace) [1869853]
- scsi: smartpqi: Capture controller reason codes (Don Brace) [1869853]
- scsi: smartpqi: Add controller handshake during kdump (Don Brace) [1869853]
- scsi: smartpqi: Update device removal management (Don Brace) [1869853]
- scsi: smartpqi: Replace one-element array with flexible-array member (Don Brace) [1869853]
- scsi: smartpqi: Fix an error code in pqi_get_raid_map() (Don Brace) [1869853]
- scsi: smartpqi: Update version to 2.1.10-020 (Don Brace) [1869853]
- scsi: smartpqi: Fix ISR accessing uninitialized data (Don Brace) [1869853]
- scsi: smartpqi: Add PCI IDs for new ZTE controllers (Don Brace) [1869853]
- scsi: smartpqi: Add PCI ID for new ntcom controller (Don Brace) [1869853]
- scsi: smartpqi: Add SCSI cmd info for resets (Don Brace) [1869853]
- scsi: smartpqi: Change Kconfig menu entry to Microchip (Don Brace) [1869853]
- scsi: smartpqi: Change driver module macros to Microchip (Don Brace) [1869853]
- scsi: smartpqi: Update copyright notices (Don Brace) [1869853]
- scsi: smartpqi: Add PCI IDs for H3C P4408 controllers (Don Brace) [1869853]
- powerpc/module_64: Fix livepatching for RO modules (Joe Lawrence) [2019205]
- net-sysfs: try not to restart the syscall if it will fail eventually (Antoine Tenart) [2030634]
- CI: Enable realtime checks for baselines (Veronika Kabatova)
- CI: Cleanup residue from ARK (Veronika Kabatova)
- redhat: ignore ksamples and kselftests on the badfuncs rpminspect test (Herton R. Krzesinski)
- redhat: disable upstream check for rpminspect (Herton R. Krzesinski)
- redhat/configs: Enable CONFIG_CRYPTO_BLAKE2B (Neal Gompa) [2031547]
- selftests: netfilter: switch zone stress to socat (Florian Westphal) [2030759]
- netfilter: conntrack: set on IPS_ASSURED if flows enters internal stream state (Florian Westphal) [2030759]
- netfilter: conntrack: serialize hash resizes and cleanups (Florian Westphal) [2030759]
- selftests: netfilter: add zone stress test with colliding tuples (Florian Westphal) [2030759]
- selftests: netfilter: add selftest for directional zone support (Florian Westphal) [2030759]
- netfilter: conntrack: include zone id in tuple hash again (Florian Westphal) [2030759]
- netfilter: conntrack: make max chain length random (Florian Westphal) [2030759]
- netfilter: refuse insertion if chain has grown too large (Florian Westphal) [2030759]
- netfilter: conntrack: switch to siphash (Florian Westphal) [2030759]
- netfilter: conntrack: sanitize table size default settings (Florian Westphal) [2030759]
- redhat: configs: increase CONFIG_DEBUG_KMEMLEAK_MEM_POOL_SIZE (Rafael Aquini) [2008118]
- iommu/dma: Fix incorrect error return on iommu deferred attach (Jerry Snitselaar) [2030394]
- RDMA/siw: Mark Software iWARP Driver as tech-preview (Kamal Heib) [2023416]
- genirq: Fix kernel doc indentation (Prarit Bhargava) [2023084]
- genirq: Change force_irqthreads to a static key (Prarit Bhargava) [2023084]
- genirq: Clarify documentation for request_threaded_irq() (Prarit Bhargava) [2023084]

* Wed Jan 12 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-41.el9]
- af_unix: Return errno instead of NULL in unix_create1(). (Balazs Nemeth) [2030037]
- s390/ftrace: remove preempt_disable()/preempt_enable() pair (Wander Lairson Costa) [1938117]
- ftrace: do CPU checking after preemption disabled (Wander Lairson Costa) [1938117]
- ftrace: disable preemption when recursion locked (Wander Lairson Costa) [1938117]
- redhat: build and include memfd to kernel-selftests-internal (Aristeu Rozanski) [2027506]
- netfilter: flowtable: fix IPv6 tunnel addr match (Florian Westphal) [2028203]
- netfilter: ipvs: Fix reuse connection if RS weight is 0 (Florian Westphal) [2028203]
- netfilter: ctnetlink: do not erase error code with EINVAL (Florian Westphal) [2028203]
- netfilter: ctnetlink: fix filtering with CTA_TUPLE_REPLY (Florian Westphal) [2028203]
- netfilter: nfnetlink_queue: fix OOB when mac header was cleared (Florian Westphal) [2028203]
- netfilter: core: Fix clang warnings about unused static inlines (Florian Westphal) [2028203]
- netfilter: nft_dynset: relax superfluous check on set updates (Florian Westphal) [2028203]
- netfilter: nf_tables: skip netdev events generated on netns removal (Florian Westphal) [2028203]
- netfilter: Kconfig: use 'default y' instead of 'm' for bool config option (Florian Westphal) [2028203]
- netfilter: xt_IDLETIMER: fix panic that occurs when timer_type has garbage value (Florian Westphal) [2028203]
- netfilter: nf_tables: honor NLM_F_CREATE and NLM_F_EXCL in event notification (Florian Westphal) [2028203]
- netfilter: nf_tables: reverse order in rule replacement expansion (Florian Westphal) [2028203]
- netfilter: nf_tables: add position handle in event notification (Florian Westphal) [2028203]
- netfilter: conntrack: fix boot failure with nf_conntrack.enable_hooks=1 (Florian Westphal) [2028203]
- netfilter: log: work around missing softdep backend module (Florian Westphal) [2028203]
- netfilter: nf_tables: unlink table before deleting it (Florian Westphal) [2028203]
- ipvs: check that ip_vs_conn_tab_bits is between 8 and 20 (Florian Westphal) [2028203]
- netfilter: nft_ct: protect nft_ct_pcpu_template_refcnt with mutex (Florian Westphal) [2028203]
- netfilter: ipvs: make global sysctl readonly in non-init netns (Antoine Tenart) [2008417]
- net/sched: sch_ets: don't remove idle classes from the round-robin list (Davide Caratti) [2025552]
- net/sched: store the last executed chain also for clsact egress (Davide Caratti) [2025552]
- net: sched: act_mirred: drop dst for the direction from egress to ingress (Davide Caratti) [2025552]
- net/sched: sch_ets: don't peek at classes beyond 'nbands' (Davide Caratti) [2025552]
- net/sched: sch_ets: properly init all active DRR list handles (Davide Caratti) [2025552]
- net: Fix offloading indirect devices dependency on qdisc order creation (Davide Caratti) [2025552]
- net/core: Remove unused field from struct flow_indr_dev (Davide Caratti) [2025552]
- net/sched: sch_taprio: fix undefined behavior in ktime_mono_to_any (Davide Caratti) [2025552]
- net/sched: act_ct: Fix byte count on fragmented packets (Davide Caratti) [2025552]
- mqprio: Correct stats in mqprio_dump_class_stats(). (Davide Caratti) [2025552]
- net/sched: sch_taprio: properly cancel timer from taprio_destroy() (Davide Caratti) [2025552]
- net_sched: fix NULL deref in fifo_set_limit() (Davide Caratti) [2025552]
- net: sched: flower: protect fl_walk() with rcu (Davide Caratti) [2025552]
- fq_codel: reject silly quantum parameters (Davide Caratti) [2025552]
- net: sched: Fix qdisc_rate_table refcount leak when get tcf_block failed (Davide Caratti) [2025552]
- sch_htb: Fix inconsistency when leaf qdisc creation fails (Davide Caratti) [2025552]
- redhat/configs: Add two new CONFIGs (Prarit Bhargava) [2022993]
- redhat/configs: Remove dead CONFIG files (Prarit Bhargava) [2022993]
- redhat/configs/evaluate_configs: Add find dead configs option (Prarit Bhargava) [2022993]

* Mon Jan 10 2022 Herton R. Krzesinski <herton@redhat.com> [5.14.0-40.el9]
- cpu/hotplug: Remove deprecated CPU-hotplug functions. (Prarit Bhargava) [2023079]
- livepatch: Replace deprecated CPU-hotplug functions. (Prarit Bhargava) [2023079]
- coresight: Replace deprecated CPU-hotplug functions. (Prarit Bhargava) [2023079]
- hwmon: Replace deprecated CPU-hotplug functions. (Prarit Bhargava) [2023079]
- tracing: Replace deprecated CPU-hotplug functions. (Prarit Bhargava) [2023079]
- padata: Replace deprecated CPU-hotplug functions. (Prarit Bhargava) [2023079]
- crypto: virtio - Replace deprecated CPU-hotplug functions. (Prarit Bhargava) [2023079]
- platform/x86: Replace deprecated CPU-hotplug functions. (Prarit Bhargava) [2023079]
- powerpc: Replace deprecated CPU-hotplug functions. (Prarit Bhargava) [2023079]
- x86/mce/inject: Replace deprecated CPU-hotplug functions. (Prarit Bhargava) [2023079]
- x86/microcode: Replace deprecated CPU-hotplug functions. (Prarit Bhargava) [2023079]
- x86/mtrr: Replace deprecated CPU-hotplug functions. (Prarit Bhargava) [2023079]
- x86/mmiotrace: Replace deprecated CPU-hotplug functions. (Prarit Bhargava) [2023079]
- workqueue: Replace deprecated CPU-hotplug functions. (Prarit Bhargava) [2023079]
- net/iucv: Replace deprecated CPU-hotplug functions. (Prarit Bhargava) [2023079]
- s390/sclp: replace deprecated CPU-hotplug functions (Prarit Bhargava) [2023079]
- s390: replace deprecated CPU-hotplug functions (Prarit Bhargava) [2023079]
- net: Replace deprecated CPU-hotplug functions. (Prarit Bhargava) [2023079]
- virtio_net: Replace deprecated CPU-hotplug functions. (Prarit Bhargava) [2023079]
- ACPI: processor: Replace deprecated CPU-hotplug functions (Prarit Bhargava) [2023079]
- PM: sleep: s2idle: Replace deprecated CPU-hotplug functions (Prarit Bhargava) [2023079]
- cpufreq: Replace deprecated CPU-hotplug functions (Prarit Bhargava) [2023079]
- powercap: intel_rapl: Replace deprecated CPU-hotplug functions (Prarit Bhargava) [2023079]
- sgi-xpc: Replace deprecated CPU-hotplug functions. (Prarit Bhargava) [2023079]
- Input: i8042 - Add quirk for Fujitsu Lifebook T725 (Neal Gompa) [2019937]
- sctp: remove unreachable code from sctp_sf_violation_chunk() (Xin Long) [2024909]
- sctp: return true only for pathmtu update in sctp_transport_pl_toobig (Xin Long) [2024909]
- sctp: subtract sctphdr len in sctp_transport_pl_hlen (Xin Long) [2024909]
- sctp: reset probe_timer in sctp_transport_pl_update (Xin Long) [2024909]
- sctp: allow IP fragmentation when PLPMTUD enters Error state (Xin Long) [2024909]
- sctp: fix transport encap_port update in sctp_vtag_verify (Xin Long) [2024909]
- sctp: account stream padding length for reconf chunk (Xin Long) [2024909]
- sctp: break out if skb_header_pointer returns NULL in sctp_rcv_ootb (Xin Long) [2024909]
- sctp: add vtag check in sctp_sf_ootb (Xin Long) [2003494] {CVE-2021-3772}
- sctp: add vtag check in sctp_sf_do_8_5_1_E_sa (Xin Long) [2003494] {CVE-2021-3772}
- sctp: add vtag check in sctp_sf_violation (Xin Long) [2003494] {CVE-2021-3772}
- sctp: fix the processing for COOKIE_ECHO chunk (Xin Long) [2003494] {CVE-2021-3772}
- sctp: fix the processing for INIT_ACK chunk (Xin Long) [2003494] {CVE-2021-3772}
- sctp: fix the processing for INIT chunk (Xin Long) [2003494] {CVE-2021-3772}
- sctp: use init_tag from inithdr for ABORT chunk (Xin Long) [2003494] {CVE-2021-3772}
- drm/nouveau: clean up all clients on device removal (Karol Herbst) [1911185] {CVE-2020-27820}
- drm/nouveau: Add a dedicated mutex for the clients list (Karol Herbst) [1911185] {CVE-2020-27820}
- drm/nouveau: use drm_dev_unplug() during device removal (Karol Herbst) [1911185] {CVE-2020-27820}
- redhat/configs: NFS: disable UDP, insecure enctypes (Benjamin Coddington) [1952863]

* Fri Dec 24 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-39.el9]
- cpuidle: pseries: Do not cap the CEDE0 latency in fixup_cede0_latency() (Gustavo Walbon) [2029870]
- cpuidle: pseries: Fixup CEDE0 latency only for POWER10 onwards (Gustavo Walbon) [2029870]
- powerpc/mce: Fix access error in mce handler (Gustavo Walbon) [2027829]
- powerpc/pseries/mobility: ignore ibm, platform-facilities updates (Gustavo Walbon) [2023438]
- KVM: SVM: Do not terminate SEV-ES guests on GHCB validation failure (Vitaly Kuznetsov) [1961151]
- KVM: SEV: Fall back to vmalloc for SEV-ES scratch area if necessary (Vitaly Kuznetsov) [1961151]
- KVM: SEV: Return appropriate error codes if SEV-ES scratch setup fails (Vitaly Kuznetsov) [1961151]
- KVM: SEV: Refactor out sev_es_state struct (Vitaly Kuznetsov) [1961151]
- redhat/configs: enable DWARF5 feature if toolchain supports it (Lianbo Jiang) [2009205]
- init: make unknown command line param message clearer (Andrew Halaney) [2004361]
- Bluetooth: btusb: Add one more Bluetooth part for WCN6855 (Gopal Tiwari) [2020943]
- Bluetooth: btusb: Add the new support IDs for WCN6855 (Gopal Tiwari) [2020943]
- Bluetooth: btusb: re-definition for board_id in struct qca_version (Gopal Tiwari) [2020943]
- Bluetooth: btusb: Add support using different nvm for variant WCN6855 controller (Gopal Tiwari) [2020943]
- cgroup: Make rebind_subsystems() disable v2 controllers all at once (Waiman Long) [1986734]
- bnxt_en: Event handler for PPS events (Ken Cox) [1990151]
- bnxt_en: 1PPS functions to configure TSIO pins (Ken Cox) [1990151]
- bnxt_en: 1PPS support for 5750X family chips (Ken Cox) [1990151]
- bnxt_en: Do not read the PTP PHC during chip reset (Ken Cox) [1990151]
- bnxt_en: Move bnxt_ptp_init() from bnxt_open() back to bnxt_init_one() (Ken Cox) [1990151]

* Thu Dec 23 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-38.el9]
- x86/fpu/signal: Initialize sw_bytes in save_xstate_epilog() (David Arcari) [2004190]
- iommu/vt-d: Remove unused PASID_DISABLED (David Arcari) [2004190]
- Add CONFIG_STRICT_SIGALTSTACK_SIZE (David Arcari) [2004190]
- selftests/x86/amx: Add context switch test (David Arcari) [2004190]
- selftests/x86/amx: Add test cases for AMX state management (David Arcari) [2004190]
- x86/signal: Use fpu::__state_user_size for sigalt stack validation (David Arcari) [2004190]
- x86/signal: Implement sigaltstack size validation (David Arcari) [2004190]
- signal: Add an optional check for altstack size (David Arcari) [2004190]
- tools arch x86: Sync the msr-index.h copy with the kernel sources (David Arcari) [2004190]
- tools headers cpufeatures: Sync with the kernel sources (David Arcari) [2004190]
- tools headers UAPI: Sync arch prctl headers with the kernel sources (David Arcari) [2004190]
- x86/fpu: Optimize out sigframe xfeatures when in init state (David Arcari) [2004190]
- Documentation/x86: Add documentation for using dynamic XSTATE features (David Arcari) [2004190]
- x86/fpu: Include vmalloc.h for vzalloc() (David Arcari) [2004190]
- x86/fpu/amx: Enable the AMX feature in 64-bit mode (David Arcari) [2004190]
- x86/msr-index: Add MSRs for XFD (David Arcari) [2004190]
- x86/cpufeatures: Add eXtended Feature Disabling (XFD) feature bit (David Arcari) [2004190]
- x86/fpu: Add XFD handling for dynamic states (David Arcari) [2004190]
- x86/fpu: Calculate the default sizes independently (David Arcari) [2004190]
- x86/fpu/amx: Define AMX state components and have it used for boot-time checks (David Arcari) [2004190]
- x86/fpu/xstate: Prepare XSAVE feature table for gaps in state component numbers (David Arcari) [2004190]
- x86/fpu/xstate: Add fpstate_realloc()/free() (David Arcari) [2004190]
- x86/fpu/xstate: Add XFD #NM handler (David Arcari) [2004190]
- x86/fpu: Update XFD state where required (David Arcari) [2004190]
- x86/fpu: Add sanity checks for XFD (David Arcari) [2004190]
- x86/fpu: Add XFD state to fpstate (David Arcari) [2004190]
- x86/fpu: Reset permission and fpstate on exec() (David Arcari) [2004190]
- x86/fpu: Prepare fpu_clone() for dynamically enabled features (David Arcari) [2004190]
- x86/process: Clone FPU in copy_thread() (David Arcari) [2004190]
- x86/fpu/signal: Prepare for variable sigframe length (David Arcari) [2004190]
- x86/fpu: Add basic helpers for dynamically enabled features (David Arcari) [2004190]
- x86/arch_prctl: Add controls for dynamic XSTATE components (David Arcari) [2004190]
- x86/fpu: Add fpu_state_config::legacy_features (David Arcari) [2004190]
- x86/fpu: Add members to struct fpu to cache permission information (David Arcari) [2004190]
- x86/fpu/xstate: Provide xstate_calculate_size() (David Arcari) [2004190]
- x86/fpu: Remove old KVM FPU interface (David Arcari) [2004190]
- x86/kvm: Convert FPU handling to a single swap buffer (David Arcari) [2004190]
- x86/fpu: Provide infrastructure for KVM FPU cleanup (David Arcari) [2004190]
- x86/fpu: Prepare for sanitizing KVM FPU code (David Arcari) [2004190]
- x86/fpu/xstate: Move remaining xfeature helpers to core (David Arcari) [2004190]
- x86/fpu: Rework restore_regs_from_fpstate() (David Arcari) [2004190]
- x86/fpu: Mop up xfeatures_mask_uabi() (David Arcari) [2004190]
- x86/fpu: Move xstate feature masks to fpu_*_cfg (David Arcari) [2004190]
- x86/fpu: Move xstate size to fpu_*_cfg (David Arcari) [2004190]
- x86/fpu/xstate: Cleanup size calculations (David Arcari) [2004190]
- x86/fpu: Cleanup fpu__init_system_xstate_size_legacy() (David Arcari) [2004190]
- x86/fpu: Provide struct fpu_config (David Arcari) [2004190]
- x86/fpu/signal: Use fpstate for size and features (David Arcari) [2004190]
- x86/fpu/xstate: Use fpstate for copy_uabi_to_xstate() (David Arcari) [2004190]
- x86/fpu: Use fpstate in __copy_xstate_to_uabi_buf() (David Arcari) [2004190]
- x86/fpu: Use fpstate in fpu_copy_kvm_uabi_to_fpstate() (David Arcari) [2004190]
- x86/fpu/xstate: Use fpstate for xsave_to_user_sigframe() (David Arcari) [2004190]
- x86/fpu/xstate: Use fpstate for os_xsave() (David Arcari) [2004190]
- x86/fpu: Use fpstate::size (David Arcari) [2004190]
- x86/fpu: Add size and mask information to fpstate (David Arcari) [2004190]
- x86/process: Move arch_thread_struct_whitelist() out of line (David Arcari) [2004190]
- x86/fpu: Remove fpu::state (David Arcari) [2004190]
- x86/KVM: Convert to fpstate (David Arcari) [2004190]
- x86/math-emu: Convert to fpstate (David Arcari) [2004190]
- x86/fpu/core: Convert to fpstate (David Arcari) [2004190]
- x86/fpu/signal: Convert to fpstate (David Arcari) [2004190]
- x86/fpu/regset: Convert to fpstate (David Arcari) [2004190]
- x86/fpu: Convert tracing to fpstate (David Arcari) [2004190]
- x86/fpu: Replace KVMs xstate component clearing (David Arcari) [2004190]
- x86/fpu: Convert restore_fpregs_from_fpstate() to struct fpstate (David Arcari) [2004190]
- x86/fpu: Convert fpstate_init() to struct fpstate (David Arcari) [2004190]
- x86/fpu: Provide struct fpstate (David Arcari) [2004190]
- x86/fpu: Replace KVMs home brewed FPU copy to user (David Arcari) [2004190]
- x86/fpu: Provide a proper function for ex_handler_fprestore() (David Arcari) [2004190]
- x86/fpu: Replace the includes of fpu/internal.h (David Arcari) [2004190]
- x86/fpu: Mop up the internal.h leftovers (David Arcari) [2004190]
- x86/fpu: Remove internal.h dependency from fpu/signal.h (David Arcari) [2004190]
- x86/fpu: Move fpstate functions to api.h (David Arcari) [2004190]
- x86/fpu: Move mxcsr related code to core (David Arcari) [2004190]
- x86/sev: Include fpu/xcr.h (David Arcari) [2004190]
- x86/fpu: Move fpregs_restore_userregs() to core (David Arcari) [2004190]
- x86/fpu: Make WARN_ON_FPU() private (David Arcari) [2004190]
- x86/fpu: Move legacy ASM wrappers to core (David Arcari) [2004190]
- x86/fpu: Move os_xsave() and os_xrstor() to core (David Arcari) [2004190]
- x86/fpu: Make os_xrstor_booting() private (David Arcari) [2004190]
- x86/fpu: Clean up CPU feature tests (David Arcari) [2004190]
- x86/fpu: Move context switch and exit to user inlines into sched.h (David Arcari) [2004190]
- x86/fpu: Mark fpu__init_prepare_fx_sw_frame() as __init (David Arcari) [2004190]
- x86/fpu: Rework copy_xstate_to_uabi_buf() (David Arcari) [2004190]
- x86/fpu: Replace KVMs home brewed FPU copy from user (David Arcari) [2004190]
- x86/fpu: Move KVMs FPU swapping to FPU core (David Arcari) [2004190]
- x86/fpu/xstate: Mark all init only functions __init (David Arcari) [2004190]
- x86/fpu/xstate: Provide and use for_each_xfeature() (David Arcari) [2004190]
- x86/fpu: Cleanup xstate xcomp_bv initialization (David Arcari) [2004190]
- x86/fpu: Do not inherit FPU context for kernel and IO worker threads (David Arcari) [2004190]
- x86/fpu: Remove pointless memset in fpu_clone() (David Arcari) [2004190]
- x86/fpu: Cleanup the on_boot_cpu clutter (David Arcari) [2004190]
- x86/fpu: Restrict xsaves()/xrstors() to independent states (David Arcari) [2004190]
- x86/fpu: Update stale comments (David Arcari) [2004190]
- x86/fpu: Remove pointless argument from switch_fpu_finish() (David Arcari) [2004190]
- iommu/vt-d: Clean up unused PASID updating functions (David Arcari) [2004190]
- x86/fpu: Mask out the invalid MXCSR bits properly (David Arcari) [2004190]
- x86/fpu: Restore the masking out of reserved MXCSR bits (David Arcari) [2004190]
- x86/fpu/signal: Fix missed conversion to correct boolean retval in save_xstate_epilog() (David Arcari) [2004190]
- x86/fpu/signal: Change return code of restore_fpregs_from_user() to boolean (David Arcari) [2004190]
- x86/fpu/signal: Change return code of check_xstate_in_sigframe() to boolean (David Arcari) [2004190]
- x86/fpu/signal: Change return type of __fpu_restore_sig() to boolean (David Arcari) [2004190]
- x86/fpu/signal: Change return type of fpu__restore_sig() to boolean (David Arcari) [2004190]
- x86/signal: Change return type of restore_sigcontext() to boolean (David Arcari) [2004190]
- x86/fpu/signal: Change return type of copy_fpregs_to_sigframe() helpers to boolean (David Arcari) [2004190]
- x86/fpu/signal: Change return type of copy_fpstate_to_sigframe() to boolean (David Arcari) [2004190]
- x86/fpu/signal: Move xstate clearing out of copy_fpregs_to_sigframe() (David Arcari) [2004190]
- x86/fpu/signal: Move header zeroing out of xsave_to_user_sigframe() (David Arcari) [2004190]
- x86/fpu/signal: Clarify exception handling in restore_fpregs_from_user() (David Arcari) [2004190]
- x86/fpu: Use EX_TYPE_FAULT_MCE_SAFE for exception fixups (David Arcari) [2004190]
- x86/extable: Provide EX_TYPE_DEFAULT_MCE_SAFE and EX_TYPE_FAULT_MCE_SAFE (David Arcari) [2004190]
- x86/extable: Rework the exception table mechanics (David Arcari) [2004190]
- x86/mce: Deduplicate exception handling (David Arcari) [2004190]
- x86/extable: Get rid of redundant macros (David Arcari) [2004190]
- x86/extable: Tidy up redundant handler functions (David Arcari) [2004190]

* Wed Dec 22 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-37.el9]
- sched,x86: Don't use cluster topology for x86 hybrid CPUs (Phil Auld) [2020279]
- sched/uclamp: Fix rq->uclamp_max not set on first enqueue (Phil Auld) [2020279]
- preempt/dynamic: Fix setup_preempt_mode() return value (Phil Auld) [2020279]
- sched/cputime: Fix getrusage(RUSAGE_THREAD) with nohz_full (Phil Auld) [2020279 2029640]
- sched/scs: Reset task stack state in bringup_cpu() (Phil Auld) [2020279]
- Enable CONFIG_SCHED_CLUSTER for RHEL (Phil Auld) [2020279]
- arch_topology: Fix missing clear cluster_cpumask in remove_cpu_topology() (Phil Auld) [2020279]
- mm: move node_reclaim_distance to fix NUMA without SMP (Phil Auld) [2020279]
- sched/core: Mitigate race cpus_share_cache()/update_top_cache_domain() (Phil Auld) [2020279]
- sched/fair: Prevent dead task groups from regaining cfs_rq's (Phil Auld) [2020279]
- x86/smp: Factor out parts of native_smp_prepare_cpus() (Phil Auld) [2020279]
- sched,x86: Fix L2 cache mask (Phil Auld) [2020279]
- sched/fair: Cleanup newidle_balance (Phil Auld) [2020279]
- sched/fair: Remove sysctl_sched_migration_cost condition (Phil Auld) [2020279]
- sched/fair: Wait before decaying max_newidle_lb_cost (Phil Auld) [2020279]
- sched/fair: Skip update_blocked_averages if we are defering load balance (Phil Auld) [2020279]
- sched/fair: Account update_blocked_averages in newidle_balance cost (Phil Auld) [2020279]
- sched/core: Remove rq_relock() (Phil Auld) [2020279]
- sched: Improve wake_up_all_idle_cpus() take #2 (Phil Auld) [2020279]
- sched: Disable -Wunused-but-set-variable (Phil Auld) [2020279]
- irq_work: Handle some irq_work in a per-CPU thread on PREEMPT_RT (Phil Auld) [2020279]
- irq_work: Also rcuwait for !IRQ_WORK_HARD_IRQ on PREEMPT_RT (Phil Auld) [2020279]
- irq_work: Allow irq_work_sync() to sleep if irq_work() no IRQ support. (Phil Auld) [2020279]
- sched/rt: Annotate the RT balancing logic irqwork as IRQ_WORK_HARD_IRQ (Phil Auld) [2020279]
- sched: Fix DEBUG && !SCHEDSTATS warn (Phil Auld) [2020279]
- sched/numa: Fix a few comments (Phil Auld) [2020279]
- sched/numa: Remove the redundant member numa_group::fault_cpus (Phil Auld) [2020279]
- sched/numa: Replace hard-coded number by a define in numa_task_group() (Phil Auld) [2020279]
- sched: Remove pointless preemption disable in sched_submit_work() (Phil Auld) [2020279]
- sched: Move mmdrop to RCU on RT (Phil Auld) [2020279]
- sched: Move kprobes cleanup out of finish_task_switch() (Phil Auld) [2020279]
- sched: Disable TTWU_QUEUE on RT (Phil Auld) [2020279]
- sched: Limit the number of task migrations per batch on RT (Phil Auld) [2020279]
- sched/fair: Removed useless update of p->recent_used_cpu (Phil Auld) [2020279]
- sched: Add cluster scheduler level for x86 (Phil Auld) [1921343 2020279]
- x86/cpu: Add get_llc_id() helper function (Phil Auld) [2020279]
- x86/smp: Add a per-cpu view of SMT state (Phil Auld) [2020279]
- sched: Add cluster scheduler level in core and related Kconfig for ARM64 (Phil Auld) [2020279]
- topology: Represent clusters of CPUs within a die (Phil Auld) [2020279]
- topology: use bin_attribute to break the size limitation of cpumap ABI (Phil Auld) [2020279]
- cpumask: Omit terminating null byte in cpumap_print_{list,bitmask}_to_buf (Phil Auld) [2020279]
- cpumask: introduce cpumap_print_list/bitmask_to_buf to support large bitmask and list (Phil Auld) [2020279]
- sched: Make cookie functions static (Phil Auld) [2020279]
- sched,livepatch: Use wake_up_if_idle() (Phil Auld) [2020279]
- sched: Simplify wake_up_*idle*() (Phil Auld) [2020279]
- sched,livepatch: Use task_call_func() (Phil Auld) [2020279]
- sched,rcu: Rework try_invoke_on_locked_down_task() (Phil Auld) [2020279]
- sched: Improve try_invoke_on_locked_down_task() (Phil Auld) [2020279]
- kernel/sched: Fix sched_fork() access an invalid sched_task_group (Phil Auld) [2020279]
- sched/topology: Remove unused numa_distance in cpu_attach_domain() (Phil Auld) [2020279]
- sched: Remove unused inline function __rq_clock_broken() (Phil Auld) [2020279]
- sched/fair: Consider SMT in ASYM_PACKING load balance (Phil Auld) [2020279]
- sched/fair: Carve out logic to mark a group for asymmetric packing (Phil Auld) [2020279]
- sched/fair: Provide update_sg_lb_stats() with sched domain statistics (Phil Auld) [2020279]
- sched/fair: Optimize checking for group_asym_packing (Phil Auld) [2020279]
- sched/topology: Introduce sched_group::flags (Phil Auld) [2020279]
- sched/dl: Support schedstats for deadline sched class (Phil Auld) [2020279]
- sched/dl: Support sched_stat_runtime tracepoint for deadline sched class (Phil Auld) [2020279]
- sched/rt: Support schedstats for RT sched class (Phil Auld) [2020279]
- sched/rt: Support sched_stat_runtime tracepoint for RT sched class (Phil Auld) [2020279]
- sched: Introduce task block time in schedstats (Phil Auld) [2020279]
- sched: Make schedstats helpers independent of fair sched class (Phil Auld) [2020279]
- sched: Make struct sched_statistics independent of fair sched class (Phil Auld) [2020279]
- sched/fair: Use __schedstat_set() in set_next_entity() (Phil Auld) [2020279]
- kselftests/sched: cleanup the child processes (Phil Auld) [2020279]
- sched/fair: Add document for burstable CFS bandwidth (Phil Auld) [2020279]
- sched/fair: Add cfs bandwidth burst statistics (Phil Auld) [2020279]
- fs/proc/uptime.c: Fix idle time reporting in /proc/uptime (Phil Auld) [2020279]
- sched: Switch wait_task_inactive to HRTIMER_MODE_REL_HARD (Phil Auld) [2020279]
- sched/core: Simplify core-wide task selection (Phil Auld) [2020279]
- sched/fair: Trigger nohz.next_balance updates when a CPU goes NOHZ-idle (Phil Auld) [2020279]
- sched/fair: Add NOHZ balancer flag for nohz.next_balance updates (Phil Auld) [2020279]
- sched: adjust sleeper credit for SCHED_IDLE entities (Phil Auld) [2020279]
- sched: reduce sched slice for SCHED_IDLE entities (Phil Auld) [2020279]
- sched: Account number of SCHED_IDLE entities on each cfs_rq (Phil Auld) [2020279]
- wait: use LIST_HEAD_INIT() to initialize wait_queue_head (Phil Auld) [2020279]
- kthread: Move prio/affinite change into the newly created thread (Phil Auld) [2020279]

* Tue Dec 21 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-36.el9]
- drivers: base: cacheinfo: Get rid of DEFINE_SMP_CALL_CACHE_FUNCTION() (Vitaly Kuznetsov) [2031644]
- hugetlbfs: flush TLBs correctly after huge_pmd_unshare (Rafael Aquini) [2026378] {CVE-2021-4002}
- bareudp: Add extack support to bareudp_configure() (Guillaume Nault) [2032483]
- bareudp: Move definition of struct bareudp_conf to bareudp.c (Guillaume Nault) [2032483]
- bareudp: Remove bareudp_dev_create() (Guillaume Nault) [2032483]
- scsi: core: Fix shost->cmd_per_lun calculation in scsi_add_host_with_dma() (Cathy Avery) [2030468]
- net: fix GRO skb truesize update (Paolo Abeni) [2028927]
- sk_buff: avoid potentially clearing 'slow_gro' field (Paolo Abeni) [2028927]
- veth: use skb_prepare_for_gro() (Paolo Abeni) [2028927]
- skbuff: allow 'slow_gro' for skb carring sock reference (Paolo Abeni) [2028927]
- net: optimize GRO for the common case. (Paolo Abeni) [2028927]
- sk_buff: track extension status in slow_gro (Paolo Abeni) [2028927]
- sk_buff: track dst status in slow_gro (Paolo Abeni) [2028927]
- sk_buff: introduce 'slow_gro' flags (Paolo Abeni) [2028927]
- selftests: net: veth: add tests for set_channel (Paolo Abeni) [2028927]
- veth: create by default nr_possible_cpus queues (Paolo Abeni) [2028927]
- veth: implement support for set_channel ethtool op (Paolo Abeni) [2028927]
- veth: factor out initialization helper (Paolo Abeni) [2028927]
- veth: always report zero combined channels (Paolo Abeni) [2028927]
- [kernel] bpf: set default value for bpf_jit_harden (Jiri Olsa) [2028734]
- scsi: ibmvfc: Fix up duplicate response detection (Steve Best) [2028709]
- kabi: Add kABI macros for enum type (Čestmír Kalina) [2024595]
- kabi: expand and clarify documentation of aux structs (Čestmír Kalina) [2024595]
- kabi: introduce RH_KABI_USE_AUX_PTR (Čestmír Kalina) [2024595]
- kabi: rename RH_KABI_SIZE_AND_EXTEND to AUX (Čestmír Kalina) [2024595]
- kabi: more consistent _RH_KABI_SIZE_AND_EXTEND (Čestmír Kalina) [2024595]
- kabi: use fixed field name for extended part (Čestmír Kalina) [2024595]
- kabi: fix dereference in RH_KABI_CHECK_EXT (Čestmír Kalina) [2024595]
- kabi: fix RH_KABI_SET_SIZE macro (Čestmír Kalina) [2024595]
- kabi: expand and clarify documentation (Čestmír Kalina) [2024595]
- kabi: make RH_KABI_USE replace any number of reserved fields (Čestmír Kalina) [2024595]
- kabi: rename RH_KABI_USE2 to RH_KABI_USE_SPLIT (Čestmír Kalina) [2024595]
- kabi: change RH_KABI_REPLACE2 to RH_KABI_REPLACE_SPLIT (Čestmír Kalina) [2024595]
- kabi: change RH_KABI_REPLACE_UNSAFE to RH_KABI_BROKEN_REPLACE (Čestmír Kalina) [2024595]
- kabi: introduce RH_KABI_ADD_MODIFIER (Čestmír Kalina) [2024595]
- kabi: Include kconfig.h (Čestmír Kalina) [2024595]
- kabi: macros for intentional kABI breakage (Čestmír Kalina) [2024595]
- kabi: fix the note about terminating semicolon (Čestmír Kalina) [2024595]
- kabi: introduce RH_KABI_HIDE_INCLUDE and RH_KABI_FAKE_INCLUDE (Čestmír Kalina) [2024595]

* Mon Dec 20 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-35.el9]
- drm/hyperv: Fix device removal on Gen1 VMs (Mohammed Gamal) [2018067]
- wireguard: device: reset peer src endpoint when netns exits (Hangbin Liu) [1967796]
- nvmet: use IOCB_NOWAIT only if the filesystem supports it (Chris Leech) [2022054]
- nvmet-tcp: fix incomplete data digest send (Chris Leech) [2022054]
- nvmet-tcp: fix memory leak when performing a controller reset (Chris Leech) [2022054]
- nvmet-tcp: add an helper to free the cmd buffers (Chris Leech) [2022054]
- nvmet-tcp: fix a race condition between release_queue and io_work (Chris Leech) [2022054]
- nvmet-tcp: fix use-after-free when a port is removed (Chris Leech) [2022054]
- nvmet-rdma: fix use-after-free when a port is removed (Chris Leech) [2022054]
- nvmet: fix use-after-free when a port is removed (Chris Leech) [2022054]
- nvmet-tcp: fix header digest verification (Chris Leech) [2022054]
- nvmet-tcp: fix data digest pointer calculation (Chris Leech) [2022054]
- nvmet-tcp: fix a memory leak when releasing a queue (Chris Leech) [2022054]
- nvmet: fix a width vs precision bug in nvmet_subsys_attr_serial_show() (Chris Leech) [2022054]
- nvmet: fixup buffer overrun in nvmet_subsys_attr_serial() (Chris Leech) [2022054]
- nvmet: return bool from nvmet_passthru_ctrl and nvmet_is_passthru_req (Chris Leech) [2022054]
- nvmet: looks at the passthrough controller when initializing CAP (Chris Leech) [2022054]
- nvmet: check that host sqsize does not exceed ctrl MQES (Chris Leech) [2022054]
- nvmet: avoid duplicate qid in connect cmd (Chris Leech) [2022054]
- nvmet: pass back cntlid on successful completion (Chris Leech) [2022054]
- nvmet: remove redundant assignments of variable status (Chris Leech) [2022054]
- nvme-fabrics: ignore invalid fast_io_fail_tmo values (Chris Leech) [2022054]
- nvme-tcp: fix memory leak when freeing a queue (Chris Leech) [2022054]
- nvme-tcp: validate R2T PDU in nvme_tcp_handle_r2t() (Chris Leech) [2022054]
- nvme-tcp: fix data digest pointer calculation (Chris Leech) [2022054]
- nvme-tcp: fix possible req->offset corruption (Chris Leech) [2022054]
- nvme-tcp: fix H2CData PDU send accounting (again) (Chris Leech) [2022054]
- nvme: fix per-namespace chardev deletion (Chris Leech) [2022054]
- nvme: keep ctrl->namespaces ordered (Chris Leech) [2022054]
- nvme-tcp: fix incorrect h2cdata pdu offset accounting (Chris Leech) [2022054]
- nvme-tcp: fix io_work priority inversion (Chris Leech) [2022054]
- nvme-multipath: fix ANA state updates when a namespace is not present (Chris Leech) [2022054]
- nvme: update keep alive interval when kato is modified (Chris Leech) [2022054]
- nvme-tcp: Do not reset transport on data digest errors (Chris Leech) [2022054]
- nvme-rdma: don't update queue count when failing to set io queues (Chris Leech) [2022054]
- nvme-tcp: don't update queue count when failing to set io queues (Chris Leech) [2022054]
- nvme-tcp: pair send_mutex init with destroy (Chris Leech) [2022054]
- nvme-tcp: don't check blk_mq_tag_to_rq when receiving pdu data (Chris Leech) [2022054]
- ovl: fix missing negative dentry check in ovl_rename() (Miklos Szeredi) [2011181]
- selftests/bpf/xdp_redirect_multi: Limit the tests in netns (Hangbin Liu) [2008895]
- selftests/bpf/xdp_redirect_multi: Give tcpdump a chance to terminate cleanly (Hangbin Liu) [2008895]
- selftests/bpf/xdp_redirect_multi: Use arping to accurate the arp number (Hangbin Liu) [2008895]
- selftests/bpf/xdp_redirect_multi: Put the logs to tmp folder (Hangbin Liu) [2008895]

* Sat Dec 18 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-34.el9]
- nvdimm/pmem: cleanup the disk if pmem_release_disk() is yet assigned (Ming Lei) [2018403]
- nvdimm/pmem: stop using q_usage_count as external pgmap refcount (Ming Lei) [2018403]
- libnvdimm/pmem: Fix crash triggered when I/O in-flight during unbind (Ming Lei) [2018403]
- nvdimm/pmem: fix creating the dax group (Ming Lei) [2018403]
- md: fix a lock order reversal in md_alloc (Ming Lei) [2018403]
- tools headers UAPI: Sync linux/fs.h with the kernel sources (Ming Lei) [2018403]
- Documentation: raise minimum supported version of GCC to 5.1 (Ming Lei) [2018403]
- loop: Use pr_warn_once() for loop_control_remove() warning (Ming Lei) [2018403]
- zram: only make zram_wb_devops for CONFIG_ZRAM_WRITEBACK (Ming Lei) [2018403]
- block: call rq_qos_done() before ref check in batch completions (Ming Lei) [2018403]
- block: fix parameter not described warning (Ming Lei) [2018403]
- block: avoid to touch unloaded module instance when opening bdev (Ming Lei) [2018403]
- block: Hold invalidate_lock in BLKRESETZONE ioctl (Ming Lei) [2018403]
- block: Hold invalidate_lock in BLKZEROOUT ioctl (Ming Lei) [2018403]
- block: Hold invalidate_lock in BLKDISCARD ioctl (Ming Lei) [2018403]
- blk-mq: don't insert FUA request with data into scheduler queue (Ming Lei) [2018403]
- blk-cgroup: fix missing put device in error path from blkg_conf_pref() (Ming Lei) [2018403]
- block: avoid to quiesce queue in elevator_init_mq (Ming Lei) [2018403]
- Revert "mark pstore-blk as broken" (Ming Lei) [2018403]
- blk-mq: cancel blk-mq dispatch work in both blk_cleanup_queue and disk_release() (Ming Lei) [2018403]
- block: fix missing queue put in error path (Ming Lei) [2018403]
- block: Check ADMIN before NICE for IOPRIO_CLASS_RT (Ming Lei) [2018403]
- blk-mq: fix filesystem I/O request allocation (Ming Lei) [2018403]
- blkcg: Remove extra blkcg_bio_issue_init (Ming Lei) [2018403]
- blk-mq: rename blk_attempt_bio_merge (Ming Lei) [2018403]
- blk-mq: don't grab ->q_usage_counter in blk_mq_sched_bio_merge (Ming Lei) [2018403]
- block: fix kerneldoc for disk_register_independent_access__ranges() (Ming Lei) [2018403]
- block: use enum type for blk_mq_alloc_data->rq_flags (Ming Lei) [2018403]
- bcache: Revert "bcache: use bvec_virt" (Ming Lei) [2018403]
- ataflop: Add missing semicolon to return statement (Ming Lei) [2018403]
- floppy: address add_disk() error handling on probe (Ming Lei) [2018403]
- ataflop: address add_disk() error handling on probe (Ming Lei) [2018403]
- block: update __register_blkdev() probe documentation (Ming Lei) [2018403]
- ataflop: remove ataflop_probe_lock mutex (Ming Lei) [2018403]
- mtd/ubi/block: add error handling support for add_disk() (Ming Lei) [2018403]
- block/sunvdc: add error handling support for add_disk() (Ming Lei) [2018403]
- z2ram: add error handling support for add_disk() (Ming Lei) [2018403]
- loop: Remove duplicate assignments (Ming Lei) [2018403]
- drbd: Fix double free problem in drbd_create_device (Ming Lei) [2018403]
- bcache: fix use-after-free problem in bcache_device_free() (Ming Lei) [2018403]
- zram: replace fsync_bdev with sync_blockdev (Ming Lei) [2018403]
- zram: avoid race between zram_remove and disksize_store (Ming Lei) [2018403]
- zram: don't fail to remove zram during unloading module (Ming Lei) [2018403]
- zram: fix race between zram_reset_device() and disksize_store() (Ming Lei) [2018403]
- nbd: error out if socket index doesn't match in nbd_handle_reply() (Ming Lei) [2018403]
- nbd: Fix hungtask when nbd_config_put (Ming Lei) [2018403]
- nbd: Fix incorrect error handle when first_minor is illegal in nbd_dev_add (Ming Lei) [2018403]
- nbd: fix possible overflow for 'first_minor' in nbd_dev_add() (Ming Lei) [2018403]
- nbd: fix max value for 'first_minor' (Ming Lei) [2018403]
- block/brd: add error handling support for add_disk() (Ming Lei) [2018403]
- ps3vram: add error handling support for add_disk() (Ming Lei) [2018403]
- ps3disk: add error handling support for add_disk() (Ming Lei) [2018403]
- zram: add error handling support for add_disk() (Ming Lei) [2018403]
- nvme: wait until quiesce is done (Ming Lei) [2018403]
- scsi: make sure that request queue queiesce and unquiesce balanced (Ming Lei) [2018403]
- scsi: avoid to quiesce sdev->request_queue two times (Ming Lei) [2018403]
- blk-mq: add one API for waiting until quiesce is done (Ming Lei) [2018403]
- blk-mq: don't free tags if the tag_set is used by other device in queue initialztion (Ming Lei) [2018403]
- block: fix device_add_disk() kobject_create_and_add() error handling (Ming Lei) [2018403]
- block: ensure cached plug request matches the current queue (Ming Lei) [2018403]
- block: move queue enter logic into blk_mq_submit_bio() (Ming Lei) [2018403]
- block: make bio_queue_enter() fast-path available inline (Ming Lei) [2018403]
- block: split request allocation components into helpers (Ming Lei) [2018403]
- block: have plug stored requests hold references to the queue (Ming Lei) [2018403]
- blk-mq: update hctx->nr_active in blk_mq_end_request_batch() (Ming Lei) [2018403]
- blk-mq: add RQF_ELV debug entry (Ming Lei) [2018403]
- blk-mq: only try to run plug merge if request has same queue with incoming bio (Ming Lei) [2018403]
- block: move RQF_ELV setting into allocators (Ming Lei) [2018403]
- dm: don't stop request queue after the dm device is suspended (Ming Lei) [2018403]
- block: replace always false argument with 'false' (Ming Lei) [2018403]
- block: assign correct tag before doing prefetch of request (Ming Lei) [2018403]
- blk-mq: fix redundant check of !e expression (Ming Lei) [2018403]
- block: use new bdev_nr_bytes() helper for blkdev_{read,write}_iter() (Ming Lei) [2018403]
- block: add a loff_t cast to bdev_nr_bytes (Ming Lei) [2018403]
- null_blk: Fix handling of submit_queues and poll_queues attributes (Ming Lei) [2018403]
- block: ataflop: Fix warning comparing pointer to 0 (Ming Lei) [2018403]
- bcache: replace snprintf in show functions with sysfs_emit (Ming Lei) [2018403]
- bcache: move uapi header bcache.h to bcache code directory (Ming Lei) [2018403]
- block: ataflop: more blk-mq refactoring fixes (Ming Lei) [2018403]
- block: remove support for cryptoloop and the xor transfer (Ming Lei) [2018403]
- mtd: add add_disk() error handling (Ming Lei) [2018403]
- rnbd: add error handling support for add_disk() (Ming Lei) [2018403]
- um/drivers/ubd_kern: add error handling support for add_disk() (Ming Lei) [2018403]
- m68k/emu/nfblock: add error handling support for add_disk() (Ming Lei) [2018403]
- xen-blkfront: add error handling support for add_disk() (Ming Lei) [2018403]
- bcache: add error handling support for add_disk() (Ming Lei) [2018403]
- dm: add add_disk() error handling (Ming Lei) [2018403]
- block: aoe: fixup coccinelle warnings (Ming Lei) [2018403]
- bcache: remove bch_crc64_update (Ming Lei) [2018403]
- bcache: use bvec_kmap_local in bch_data_verify (Ming Lei) [2018403]
- bcache: remove the backing_dev_name field from struct cached_dev (Ming Lei) [2018403]
- bcache: remove the cache_dev_name field from struct cache (Ming Lei) [2018403]
- bcache: move calc_cached_dev_sectors to proper place on backing device detach (Ming Lei) [2018403]
- bcache: fix error info in register_bcache() (Ming Lei) [2018403]
- bcache: reserve never used bits from bkey.high (Ming Lei) [2018403]
- md: bcache: Fix spelling of 'acquire' (Ming Lei) [2018403]
- s390/dasd: fix possibly missed path verification (Ming Lei) [2018403]
- s390/dasd: fix missing path conf_data after failed allocation (Ming Lei) [2018403]
- s390/dasd: summarize dasd configuration data in a separate structure (Ming Lei) [2018403]
- s390/dasd: move dasd_eckd_read_fc_security (Ming Lei) [2018403]
- s390/dasd: split up dasd_eckd_read_conf (Ming Lei) [2018403]
- s390/dasd: fix kernel doc comment (Ming Lei) [2018403]
- s390/dasd: handle request magic consistently as unsigned int (Ming Lei) [2018403]
- nbd: Fix use-after-free in pid_show (Ming Lei) [2018403]
- block: ataflop: fix breakage introduced at blk-mq refactoring (Ming Lei) [2018403]
- nbd: fix uaf in nbd_handle_reply() (Ming Lei) [2018403]
- nbd: partition nbd_read_stat() into nbd_read_reply() and nbd_handle_reply() (Ming Lei) [2018403]
- nbd: clean up return value checking of sock_xmit() (Ming Lei) [2018403]
- nbd: don't start request if nbd_queue_rq() failed (Ming Lei) [2018403]
- nbd: check sock index in nbd_read_stat() (Ming Lei) [2018403]
- nbd: make sure request completion won't concurrent (Ming Lei) [2018403]
- nbd: don't handle response without a corresponding request message (Ming Lei) [2018403]
- mtip32xx: Remove redundant 'flush_workqueue()' calls (Ming Lei) [2018403]
- swim3: add missing major.h include (Ming Lei) [2018403]
- sx8: fix an error code in carm_init_one() (Ming Lei) [2018403]
- pf: fix error codes in pf_init_unit() (Ming Lei) [2018403]
- pcd: fix error codes in pcd_init_unit() (Ming Lei) [2018403]
- xtensa/platforms/iss/simdisk: add error handling support for add_disk() (Ming Lei) [2018403]
- block/ataflop: add error handling support for add_disk() (Ming Lei) [2018403]
- block/ataflop: provide a helper for cleanup up an atari disk (Ming Lei) [2018403]
- block/ataflop: add registration bool before calling del_gendisk() (Ming Lei) [2018403]
- block/ataflop: use the blk_cleanup_disk() helper (Ming Lei) [2018403]
- swim: add error handling support for add_disk() (Ming Lei) [2018403]
- swim: add a floppy registration bool which triggers del_gendisk() (Ming Lei) [2018403]
- swim: add helper for disk cleanup (Ming Lei) [2018403]
- swim: simplify using blk_cleanup_disk() on swim_remove() (Ming Lei) [2018403]
- amiflop: add error handling support for add_disk() (Ming Lei) [2018403]
- floppy: add error handling support for add_disk() (Ming Lei) [2018403]
- floppy: fix calling platform_device_unregister() on invalid drives (Ming Lei) [2018403]
- floppy: use blk_cleanup_disk() (Ming Lei) [2018403]
- floppy: fix add_disk() assumption on exit due to new developments (Ming Lei) [2018403]
- block/swim3: add error handling support for add_disk() (Ming Lei) [2018403]
- rbd: add add_disk() error handling (Ming Lei) [2018403]
- cdrom/gdrom: add error handling support for add_disk() (Ming Lei) [2018403]
- pf: add error handling support for add_disk() (Ming Lei) [2018403]
- block/sx8: add error handling support for add_disk() (Ming Lei) [2018403]
- block/rsxx: add error handling support for add_disk() (Ming Lei) [2018403]
- pktcdvd: add error handling support for add_disk() (Ming Lei) [2018403]
- mtip32xx: add error handling support for add_disk() (Ming Lei) [2018403]
- pd: add error handling support for add_disk() (Ming Lei) [2018403]
- pcd: capture errors on cdrom_register() (Ming Lei) [2018403]
- pcd: fix ordering of unregister_cdrom() (Ming Lei) [2018403]
- pcd: add error handling support for add_disk() (Ming Lei) [2018403]
- pd: cleanup initialization (Ming Lei) [2018403]
- pf: cleanup initialization (Ming Lei) [2018403]
- pcd: cleanup initialization (Ming Lei) [2018403]
- pcd: move the identify buffer into pcd_identify (Ming Lei) [2018403]
- n64cart: add error handling support for add_disk() (Ming Lei) [2018403]
- drbd: add error handling support for add_disk() (Ming Lei) [2018403]
- aoe: add error handling support for add_disk() (Ming Lei) [2018403]
- nbd: add error handling support for add_disk() (Ming Lei) [2018403]
- loop: add error handling support for add_disk() (Ming Lei) [2018403]
- null_blk: poll queue support (Ming Lei) [2018403]
- block: simplify the block device syncing code (Ming Lei) [2018403]
- fat: use sync_blockdev_nowait (Ming Lei) [2018403]
- btrfs: use sync_blockdev (Ming Lei) [2018403]
- xen-blkback: use sync_blockdev (Ming Lei) [2018403]
- block: remove __sync_blockdev (Ming Lei) [2018403]
- fs: remove __sync_filesystem (Ming Lei) [2018403]
- cdrom: Remove redundant variable and its assignment (Ming Lei) [2018403]
- cdrom: docs: reformat table in Documentation/userspace-api/ioctl/cdrom.rst (Ming Lei) [2018403]
- drivers/cdrom: improved ioctl for media change detection (Ming Lei) [2018403]
- partitions/ibm: use bdev_nr_sectors instead of open coding it (Ming Lei) [2018403]
- partitions/efi: use bdev_nr_bytes instead of open coding it (Ming Lei) [2018403]
- block/ioctl: use bdev_nr_sectors and bdev_nr_bytes (Ming Lei) [2018403]
- block: cache inode size in bdev (Ming Lei) [2018403]
- udf: use sb_bdev_nr_blocks (Ming Lei) [2018403]
- reiserfs: use sb_bdev_nr_blocks (Ming Lei) [2018403]
- ntfs: use sb_bdev_nr_blocks (Ming Lei) [2018403]
- jfs: use sb_bdev_nr_blocks (Ming Lei) [2018403]
- ext4: use sb_bdev_nr_blocks (Ming Lei) [2018403]
- block: add a sb_bdev_nr_blocks helper (Ming Lei) [2018403]
- block: use bdev_nr_bytes instead of open coding it in blkdev_fallocate (Ming Lei) [2018403]
- squashfs: use bdev_nr_bytes instead of open coding it (Ming Lei) [2018403]
- reiserfs: use bdev_nr_bytes instead of open coding it (Ming Lei) [2018403]
- pstore/blk: use bdev_nr_bytes instead of open coding it (Ming Lei) [2018403]
- nilfs2: use bdev_nr_bytes instead of open coding it (Ming Lei) [2018403]
- nfs/blocklayout: use bdev_nr_bytes instead of open coding it (Ming Lei) [2018403]
- jfs: use bdev_nr_bytes instead of open coding it (Ming Lei) [2018403]
- hfsplus: use bdev_nr_sectors instead of open coding it (Ming Lei) [2018403]
- hfs: use bdev_nr_sectors instead of open coding it (Ming Lei) [2018403]
- fat: use bdev_nr_sectors instead of open coding it (Ming Lei) [2018403]
- cramfs: use bdev_nr_bytes instead of open coding it (Ming Lei) [2018403]
- btrfs: use bdev_nr_bytes instead of open coding it (Ming Lei) [2018403]
- affs: use bdev_nr_sectors instead of open coding it (Ming Lei) [2018403]
- fs: simplify init_page_buffers (Ming Lei) [2018403]
- fs: use bdev_nr_bytes instead of open coding it in blkdev_max_block (Ming Lei) [2018403]
- target/iblock: use bdev_nr_bytes instead of open coding it (Ming Lei) [2018403]
- nvmet: use bdev_nr_bytes instead of open coding it (Ming Lei) [2018403]
- md: use bdev_nr_sectors instead of open coding it (Ming Lei) [2018403]
- dm: use bdev_nr_sectors and bdev_nr_bytes instead of open coding them (Ming Lei) [2018403]
- drbd: use bdev_nr_sectors instead of open coding it (Ming Lei) [2018403]
- bcache: remove bdev_sectors (Ming Lei) [2018403]
- block: add a bdev_nr_bytes helper (Ming Lei) [2018403]
- block: move the SECTOR_SIZE related definitions to blk_types.h (Ming Lei) [2018403]
- blk-mq-debugfs: Show active requests per queue for shared tags (Ming Lei) [2018403]
- block: improve readability of blk_mq_end_request_batch() (Ming Lei) [2018403]
- virtio-blk: Use blk_validate_block_size() to validate block size (Ming Lei) [2018403]
- loop: Use blk_validate_block_size() to validate block size (Ming Lei) [2018403]
- nbd: Use blk_validate_block_size() to validate block size (Ming Lei) [2018403]
- block: Add a helper to validate the block size (Ming Lei) [2018403]
- block: re-flow blk_mq_rq_ctx_init() (Ming Lei) [2018403]
- block: prefetch request to be initialized (Ming Lei) [2018403]
- block: pass in blk_mq_tags to blk_mq_rq_ctx_init() (Ming Lei) [2018403]
- block: add rq_flags to struct blk_mq_alloc_data (Ming Lei) [2018403]
- block: add async version of bio_set_polled (Ming Lei) [2018403]
- block: kill DIO_MULTI_BIO (Ming Lei) [2018403]
- block: kill unused polling bits in __blkdev_direct_IO() (Ming Lei) [2018403]
- block: avoid extra iter advance with async iocb (Ming Lei) [2018403]
- block: Add independent access ranges support (Ming Lei) [2018403]
- blk-mq: don't issue request directly in case that current is to be blocked (Ming Lei) [2018403]
- sbitmap: silence data race warning (Ming Lei) [2018403]
- blk-cgroup: synchronize blkg creation against policy deactivation (Ming Lei) [2018403]
- block: refactor bio_iov_bvec_set() (Ming Lei) [2018403]
- block: add single bio async direct IO helper (Ming Lei) [2018403]
- sched: make task_struct->plug always defined (Ming Lei) [2018403]
- blk-mq-sched: Don't reference queue tagset in blk_mq_sched_tags_teardown() (Ming Lei) [2018403]
- block: fix req_bio_endio append error handling (Ming Lei) [2018403]
- blk-crypto: update inline encryption documentation (Ming Lei) [2018403]
- blk-crypto: rename blk_keyslot_manager to blk_crypto_profile (Ming Lei) [2018403]
- blk-crypto: rename keyslot-manager files to blk-crypto-profile (Ming Lei) [2018403]
- blk-crypto-fallback: properly prefix function and struct names (Ming Lei) [2018403]
- nbd: Use invalidate_disk() helper on disconnect (Ming Lei) [2018403]
- loop: Remove the unnecessary bdev checks and unused bdev variable (Ming Lei) [2018403]
- loop: Use invalidate_disk() helper to invalidate gendisk (Ming Lei) [2018403]
- block: Add invalidate_disk() helper to invalidate the gendisk (Ming Lei) [2018403]
- block: kill extra rcu lock/unlock in queue enter (Ming Lei) [2018403]
- percpu_ref: percpu_ref_tryget_live() version holding RCU (Ming Lei) [2018403]
- block: convert fops.c magic constants to SHIFT_SECTOR (Ming Lei) [2018403]
- block: clean up blk_mq_submit_bio() merging (Ming Lei) [2018403]
- block: optimise boundary blkdev_read_iter's checks (Ming Lei) [2018403]
- fs: bdev: fix conflicting comment from lookup_bdev (Ming Lei) [2018403]
- blk-mq: Fix blk_mq_tagset_busy_iter() for shared tags (Ming Lei) [2018403]
- block: cleanup the flush plug helpers (Ming Lei) [2018403]
- block: optimise blk_flush_plug_list (Ming Lei) [2018403]
- blk-mq: move blk_mq_flush_plug_list to block/blk-mq.h (Ming Lei) [2018403]
- blk-mq: only flush requests from the plug in blk_mq_submit_bio (Ming Lei) [2018403]
- block: remove inaccurate requeue check (Ming Lei) [2018403]
- block: inline a part of bio_release_pages() (Ming Lei) [2018403]
- block: don't bloat enter_queue with percpu_ref (Ming Lei) [2018403]
- block: optimise req_bio_endio() (Ming Lei) [2018403]
- block: convert leftovers to bdev_get_queue (Ming Lei) [2018403]
- block: turn macro helpers into inline functions (Ming Lei) [2018403]
- blk-mq: support concurrent queue quiesce/unquiesce (Ming Lei) [2018403]
- nvme: loop: clear NVME_CTRL_ADMIN_Q_STOPPED after admin queue is reallocated (Ming Lei) [2018403]
- nvme: paring quiesce/unquiesce (Ming Lei) [2018403]
- nvme: prepare for pairing quiescing and unquiescing (Ming Lei) [2018403]
- nvme: apply nvme API to quiesce/unquiesce admin queue (Ming Lei) [2018403]
- nvme: add APIs for stopping/starting admin queue (Ming Lei) [2018403]
- block, bfq: fix UAF problem in bfqg_stats_init() (Ming Lei) [2018403]
- block: inline fast path of driver tag allocation (Ming Lei) [2018403]
- blk-mq: don't handle non-flush requests in blk_insert_flush (Ming Lei) [2018403]
- block: attempt direct issue of plug list (Ming Lei) [2018403]
- block: change plugging to use a singly linked list (Ming Lei) [2018403]
- blk-wbt: prevent NULL pointer dereference in wb_timer_fn (Ming Lei) [2018403]
- block: align blkdev_dio inlined bio to a cacheline (Ming Lei) [2018403]
- block: move blk_mq_tag_to_rq() inline (Ming Lei) [2018403]
- block: get rid of plug list sorting (Ming Lei) [2018403]
- block: return whether or not to unplug through boolean (Ming Lei) [2018403]
- block: don't call blk_status_to_errno in blk_update_request (Ming Lei) [2018403]
- block: move bdev_read_only() into the header (Ming Lei) [2018403]
- block: fix too broad elevator check in blk_mq_free_request() (Ming Lei) [2018403]
- block: add support for blk_mq_end_request_batch() (Ming Lei) [2018403]
- sbitmap: add helper to clear a batch of tags (Ming Lei) [2018403]
- block: add a struct io_comp_batch argument to fops->iopoll() (Ming Lei) [2018403]
- block: provide helpers for rq_list manipulation (Ming Lei) [2018403]
- block: remove some blk_mq_hw_ctx debugfs entries (Ming Lei) [2018403]
- block: remove debugfs blk_mq_ctx dispatched/merged/completed attributes (Ming Lei) [2018403]
- block: cache rq_flags inside blk_mq_rq_ctx_init() (Ming Lei) [2018403]
- block: blk_mq_rq_ctx_init cache ctx/q/hctx (Ming Lei) [2018403]
- block: skip elevator fields init for non-elv queue (Ming Lei) [2018403]
- block: store elevator state in request (Ming Lei) [2018403]
- block: only mark bio as tracked if it really is tracked (Ming Lei) [2018403]
- block: improve layout of struct request (Ming Lei) [2018403]
- block: move update request helpers into blk-mq.c (Ming Lei) [2018403]
- block: remove useless caller argument to print_req_error() (Ming Lei) [2018403]
- block: don't bother iter advancing a fully done bio (Ming Lei) [2018403]
- block: convert the rest of block to bdev_get_queue (Ming Lei) [2018403]
- block: use bdev_get_queue() in blk-core.c (Ming Lei) [2018403]
- block: use bdev_get_queue() in bio.c (Ming Lei) [2018403]
- block: use bdev_get_queue() in bdev.c (Ming Lei) [2018403]
- block: cache request queue in bdev (Ming Lei) [2018403]
- block: handle fast path of bio splitting inline (Ming Lei) [2018403]
- block: use flags instead of bit fields for blkdev_dio (Ming Lei) [2018403]
- block: cache bdev in struct file for raw bdev IO (Ming Lei) [2018403]
- block: don't allow writing to the poll queue attribute (Ming Lei) [2018403]
- block: switch polling to be bio based (Ming Lei) [2018403]
- block: define 'struct bvec_iter' as packed (Ming Lei) [2018403]
- block: use SLAB_TYPESAFE_BY_RCU for the bio slab (Ming Lei) [2018403]
- block: rename REQ_HIPRI to REQ_POLLED (Ming Lei) [2018403]
- io_uring: don't sleep when polling for I/O (Ming Lei) [2018403]
- block: replace the spin argument to blk_iopoll with a flags argument (Ming Lei) [2018403]
- blk-mq: remove blk_qc_t_valid (Ming Lei) [2018403]
- blk-mq: remove blk_qc_t_to_tag and blk_qc_t_is_internal (Ming Lei) [2018403]
- blk-mq: factor out a "classic" poll helper (Ming Lei) [2018403]
- blk-mq: factor out a blk_qc_to_hctx helper (Ming Lei) [2018403]
- io_uring: fix a layering violation in io_iopoll_req_issued (Ming Lei) [2018403]
- block: don't try to poll multi-bio I/Os in __blkdev_direct_IO (Ming Lei) [2018403]
- direct-io: remove blk_poll support (Ming Lei) [2018403]
- block: only check previous entry for plug merge attempt (Ming Lei) [2018403]
- block: move CONFIG_BLOCK guard to top Makefile (Ming Lei) [2018403]
- block: move menu "Partition type" to block/partitions/Kconfig (Ming Lei) [2018403]
- block: simplify Kconfig files (Ming Lei) [2018403]
- block: remove redundant =y from BLK_CGROUP dependency (Ming Lei) [2018403]
- block: improve batched tag allocation (Ming Lei) [2018403]
- sbitmap: add __sbitmap_queue_get_batch() (Ming Lei) [2018403]
- blk-mq: optimise *end_request non-stat path (Ming Lei) [2018403]
- block: mark bio_truncate static (Ming Lei) [2018403]
- block: move bio_get_{first,last}_bvec out of bio.h (Ming Lei) [2018403]
- block: mark __bio_try_merge_page static (Ming Lei) [2018403]
- block: move bio_full out of bio.h (Ming Lei) [2018403]
- block: fold bio_cur_bytes into blk_rq_cur_bytes (Ming Lei) [2018403]
- block: move bio_mergeable out of bio.h (Ming Lei) [2018403]
- block: don't include <linux/ioprio.h> in <linux/bio.h> (Ming Lei) [2018403]
- block: remove BIO_BUG_ON (Ming Lei) [2018403]
- blk-mq: inline hot part of __blk_mq_sched_restart (Ming Lei) [2018403]
- block: inline hot paths of blk_account_io_*() (Ming Lei) [2018403]
- block: merge block_ioctl into blkdev_ioctl (Ming Lei) [2018403]
- block: move the *blkdev_ioctl declarations out of blkdev.h (Ming Lei) [2018403]
- block: unexport blkdev_ioctl (Ming Lei) [2018403]
- block: don't dereference request after flush insertion (Ming Lei) [2018403]
- blk-mq: cleanup blk_mq_submit_bio (Ming Lei) [2018403]
- blk-mq: cleanup and rename __blk_mq_alloc_request (Ming Lei) [2018403]
- block: pre-allocate requests if plug is started and is a batch (Ming Lei) [2018403]
- block: bump max plugged deferred size from 16 to 32 (Ming Lei) [2018403]
- block: inherit request start time from bio for BLK_CGROUP (Ming Lei) [2018403]
- block: move blk-throtl fast path inline (Ming Lei) [2018403]
- blk-mq: Change shared sbitmap naming to shared tags (Ming Lei) [2018403]
- blk-mq: Stop using pointers for blk_mq_tags bitmap tags (Ming Lei) [2018403]
- blk-mq: Use shared tags for shared sbitmap support (Ming Lei) [2018403]
- blk-mq: Refactor and rename blk_mq_free_map_and_{requests->rqs}() (Ming Lei) [2018403]
- blk-mq: Add blk_mq_alloc_map_and_rqs() (Ming Lei) [2018403]
- blk-mq: Add blk_mq_tag_update_sched_shared_sbitmap() (Ming Lei) [2018403]
- blk-mq: Don't clear driver tags own mapping (Ming Lei) [2018403]
- blk-mq: Pass driver tags to blk_mq_clear_rq_mapping() (Ming Lei) [2018403]
- blk-mq-sched: Rename blk_mq_sched_free_{requests -> rqs}() (Ming Lei) [2018403]
- blk-mq-sched: Rename blk_mq_sched_alloc_{tags -> map_and_rqs}() (Ming Lei) [2018403]
- blk-mq: Invert check in blk_mq_update_nr_requests() (Ming Lei) [2018403]
- blk-mq: Relocate shared sbitmap resize in blk_mq_update_nr_requests() (Ming Lei) [2018403]
- block: Rename BLKDEV_MAX_RQ -> BLKDEV_DEFAULT_RQ (Ming Lei) [2018403]
- blk-mq: Change rqs check in blk_mq_free_rqs() (Ming Lei) [2018403]
- block: print the current process in handle_bad_sector (Ming Lei) [2018403]
- block/mq-deadline: Prioritize high-priority requests (Ming Lei) [2018403]
- block/mq-deadline: Stop using per-CPU counters (Ming Lei) [2018403]
- block/mq-deadline: Add an invariant check (Ming Lei) [2018403]
- block/mq-deadline: Improve request accounting further (Ming Lei) [2018403]
- block: move struct request to blk-mq.h (Ming Lei) [2018403]
- block: move integrity handling out of <linux/blkdev.h> (Ming Lei) [2018403]
- block: move a few merge helpers out of <linux/blkdev.h> (Ming Lei) [2018403]
- block: drop unused includes in <linux/genhd.h> (Ming Lei) [2018403]
- block: drop unused includes in <linux/blkdev.h> (Ming Lei) [2018403]
- block: move elevator.h to block/ (Ming Lei) [2018403]
- block: remove the struct blk_queue_ctx forward declaration (Ming Lei) [2018403]
- block: remove the cmd_size field from struct request_queue (Ming Lei) [2018403]
- block: remove the unused blk_queue_state enum (Ming Lei) [2018403]
- block: remove the unused rq_end_sector macro (Ming Lei) [2018403]
- sched: move the <linux/blkdev.h> include out of kernel/sched/sched.h (Ming Lei) [2018403]
- kernel: remove spurious blkdev.h includes (Ming Lei) [2018403]
- arch: remove spurious blkdev.h includes (Ming Lei) [2018403]
- mm: remove spurious blkdev.h includes (Ming Lei) [2018403]
- mm: don't include <linux/blkdev.h> in <linux/backing-dev.h> (Ming Lei) [2018403]
- mm: don't include <linux/blk-cgroup.h> in <linux/backing-dev.h> (Ming Lei) [2018403]
- mm: don't include <linux/blk-cgroup.h> in <linux/writeback.h> (Ming Lei) [2018403]
- block: nbd: add sanity check for first_minor (Ming Lei) [2018403]
- mmc: core: Store pointer to bio_crypt_ctx in mmc_request (Ming Lei) [2018403]
- iomap: simplify iomap_add_to_ioend (Ming Lei) [2018403]
- iomap: simplify iomap_readpage_actor (Ming Lei) [2018403]
- io_uring: don't halt iopoll too early (Ming Lei) [2018403]
- block: Fix partition check for host-aware zoned block devices (Ming Lei) [2018403]
- block: schedule queue restart after BLK_STS_ZONE_RESOURCE (Ming Lei) [2018403]
- block: drain queue after disk is removed from sysfs (Ming Lei) [2018403]
- block: fix incorrect references to disk objects (Ming Lei) [2018403]
- blk-cgroup: blk_cgroup_bio_start() should use irq-safe operations on blkg->iostat_cpu (Ming Lei) [2018403]
- block, bfq: reset last_bfqq_created on group change (Ming Lei) [2018403]
- block: warn when putting the final reference on a registered disk (Ming Lei) [2018403]
- brd: reduce the brd_devices_mutex scope (Ming Lei) [2018403]
- kyber: avoid q->disk dereferences in trace points (Ming Lei) [2018403]
- block: keep q_usage_counter in atomic mode after del_gendisk (Ming Lei) [2018403]
- block: drain file system I/O on del_gendisk (Ming Lei) [2018403]
- block: split bio_queue_enter from blk_queue_enter (Ming Lei) [2018403]
- block: factor out a blk_try_enter_queue helper (Ming Lei) [2018403]
- block: call submit_bio_checks under q_usage_counter (Ming Lei) [2018403]
- block/rnbd-clt-sysfs: fix a couple uninitialized variable bugs (Ming Lei) [2018403]
- block: decode QUEUE_FLAG_HCTX_ACTIVE in debugfs output (Ming Lei) [2018403]
- block: genhd: fix double kfree() in __alloc_disk_node() (Ming Lei) [2018403]
- nbd: use shifts rather than multiplies (Ming Lei) [2018403]
- Revert "block, bfq: honor already-setup queue merges" (Ming Lei) [2018403]
- block: hold ->invalidate_lock in blkdev_fallocate (Ming Lei) [2018403]
- blktrace: Fix uaf in blk_trace access after removing by sysfs (Ming Lei) [2018403]
- block: don't call rq_qos_ops->done_bio if the bio isn't tracked (Ming Lei) [2018403]
- blk-cgroup: fix UAF by grabbing blkcg lock before destroying blkg pd (Ming Lei) [2018403]
- blkcg: fix memory leak in blk_iolatency_init (Ming Lei) [2018403]
- block: flush the integrity workqueue in blk_integrity_unregister (Ming Lei) [2018403]
- block: check if a profile is actually registered in blk_integrity_unregister (Ming Lei) [2018403]
- blk-mq: avoid to iterate over stale request (Ming Lei) [2018403]
- n64cart: fix return value check in n64cart_probe() (Ming Lei) [2018403]
- blk-mq: allow 4x BLK_MAX_REQUEST_COUNT at blk_plug for multiple_queues (Ming Lei) [2018403]
- block: move fs/block_dev.c to block/bdev.c (Ming Lei) [2018403]
- block: split out operations on block special files (Ming Lei) [2018403]
- blk-throttle: fix UAF by deleteing timer in blk_throtl_exit() (Ming Lei) [2018403]
- block: genhd: don't call blkdev_show() with major_names_lock held (Ming Lei) [2018403]
- cdrom: update uniform CD-ROM maintainership in MAINTAINERS file (Ming Lei) [2018403]
- loop: reduce the loop_ctl_mutex scope (Ming Lei) [2018403]
- bio: fix kerneldoc documentation for bio_alloc_kiocb() (Ming Lei) [2018403]
- block, bfq: honor already-setup queue merges (Ming Lei) [2018403]
- block/mq-deadline: Move dd_queued() to fix defined but not used warning (Ming Lei) [2018403]
- bio: improve kerneldoc documentation for bio_alloc_kiocb() (Ming Lei) [2018403]
- block: provide bio_clear_hipri() helper (Ming Lei) [2018403]
- block: use the percpu bio cache in __blkdev_direct_IO (Ming Lei) [2018403]
- io_uring: enable use of bio alloc cache (Ming Lei) [2018403]
- block: clear BIO_PERCPU_CACHE flag if polling isn't supported (Ming Lei) [2018403]
- bio: add allocation cache abstraction (Ming Lei) [2018403]
- fs: add kiocb alloc cache flag (Ming Lei) [2018403]
- bio: optimize initialization of a bio (Ming Lei) [2018403]
- Revert "floppy: reintroduce O_NDELAY fix" (Ming Lei) [2018403]
- nbd: remove nbd->destroy_complete (Ming Lei) [2018403]
- nbd: only return usable devices from nbd_find_unused (Ming Lei) [2018403]
- nbd: set nbd->index before releasing nbd_index_mutex (Ming Lei) [2018403]
- nbd: prevent IDR lookups from finding partially initialized devices (Ming Lei) [2018403]
- nbd: reset NBD to NULL when restarting in nbd_genl_connect (Ming Lei) [2018403]
- nbd: add missing locking to the nbd_dev_add error path (Ming Lei) [2018403]
- params: lift param_set_uint_minmax to common code (Ming Lei) [2018403]
- nbd: reduce the nbd_index_mutex scope (Ming Lei) [2018403]
- nbd: refactor device search and allocation in nbd_genl_connect (Ming Lei) [2018403]
- nbd: return the allocated nbd_device from nbd_dev_add (Ming Lei) [2018403]
- nbd: remove nbd_del_disk (Ming Lei) [2018403]
- nbd: refactor device removal (Ming Lei) [2018403]
- nbd: do del_gendisk() asynchronously for NBD_DESTROY_ON_DISCONNECT (Ming Lei) [2018403]
- nbd: add the check to prevent overflow in __nbd_ioctl() (Ming Lei) [2018403]
- xen-blkfront: Remove redundant assignment to variable err (Ming Lei) [2018403]
- block/rnbd: Use sysfs_emit instead of s*printf function for sysfs show (Ming Lei) [2018403]
- block/rnbd-clt: Use put_cpu_ptr after get_cpu_ptr (Ming Lei) [2018403]
- sg: pass the device name to blk_trace_setup (Ming Lei) [2018403]
- block, bfq: cleanup the repeated declaration (Ming Lei) [2018403]
- blk-crypto: fix check for too-large dun_bytes (Ming Lei) [2018403]
- blk-zoned: allow BLKREPORTZONE without CAP_SYS_ADMIN (Ming Lei) [2018403]
- blk-zoned: allow zone management send operations without CAP_SYS_ADMIN (Ming Lei) [2018403]
- block: mark blkdev_fsync static (Ming Lei) [2018403]
- block: refine the disk_live check in del_gendisk (Ming Lei) [2018403]
- mmc: sdhci-tegra: Enable MMC_CAP2_ALT_GPT_TEGRA (Ming Lei) [2018403]
- mmc: block: Support alternative_gpt_sector() operation (Ming Lei) [2018403]
- partitions/efi: Support non-standard GPT location (Ming Lei) [2018403]
- block: Add alternative_gpt_sector() operation (Ming Lei) [2018403]
- bio: fix page leak bio_add_hw_page failure (Ming Lei) [2018403]
- block: remove CONFIG_DEBUG_BLOCK_EXT_DEVT (Ming Lei) [2018403]
- block: remove a pointless call to MINOR() in device_add_disk (Ming Lei) [2018403]
- null_blk: add error handling support for add_disk() (Ming Lei) [2018403]
- virtio_blk: add error handling support for add_disk() (Ming Lei) [2018403]
- block: add error handling for device_add_disk / add_disk (Ming Lei) [2018403]
- block: return errors from disk_alloc_events (Ming Lei) [2018403]
- block: return errors from blk_integrity_add (Ming Lei) [2018403]
- block: call blk_register_queue earlier in device_add_disk (Ming Lei) [2018403]
- block: call blk_integrity_add earlier in device_add_disk (Ming Lei) [2018403]
- block: create the bdi link earlier in device_add_disk (Ming Lei) [2018403]
- block: call bdev_add later in device_add_disk (Ming Lei) [2018403]
- block: fold register_disk into device_add_disk (Ming Lei) [2018403]
- block: add a sanity check for a live disk in del_gendisk (Ming Lei) [2018403]
- block: add an explicit ->disk backpointer to the request_queue (Ming Lei) [2018403]
- block: hold a request_queue reference for the lifetime of struct gendisk (Ming Lei) [2018403]
- block: pass a request_queue to __blk_alloc_disk (Ming Lei) [2018403]
- block: remove the minors argument to __alloc_disk_node (Ming Lei) [2018403]
- block: remove alloc_disk and alloc_disk_node (Ming Lei) [2018403]
- block: cleanup the lockdep handling in *alloc_disk (Ming Lei) [2018403]
- sg: do not allocate a gendisk (Ming Lei) [2018403]
- st: do not allocate a gendisk (Ming Lei) [2018403]
- nvme: use blk_mq_alloc_disk (Ming Lei) [2018403]
- block: add back the bd_holder_dir reference in bd_link_disk_holder (Ming Lei) [2018403]
- block: fix default IO priority handling (Ming Lei) [2018403]
- block: Introduce IOPRIO_NR_LEVELS (Ming Lei) [2018403]
- block: fix IOPRIO_PRIO_CLASS() and IOPRIO_PRIO_VALUE() macros (Ming Lei) [2018403]
- block: change ioprio_valid() to an inline function (Ming Lei) [2018403]
- block: improve ioprio class description comment (Ming Lei) [2018403]
- block: bfq: fix bfq_set_next_ioprio_data() (Ming Lei) [2018403]
- block: unexport blk_register_queue (Ming Lei) [2018403]
- blk-cgroup: stop using seq_get_buf (Ming Lei) [2018403]
- blk-cgroup: refactor blkcg_print_stat (Ming Lei) [2018403]
- nvme: use bvec_virt (Ming Lei) [2018403]
- dcssblk: use bvec_virt (Ming Lei) [2018403]
- dasd: use bvec_virt (Ming Lei) [2018403]
- ps3vram: use bvec_virt (Ming Lei) [2018403]
- ubd: use bvec_virt (Ming Lei) [2018403]
- sd: use bvec_virt (Ming Lei) [2018403]
- bcache: use bvec_virt (Ming Lei) [2018403]
- virtio_blk: use bvec_virt (Ming Lei) [2018403]
- rbd: use bvec_virt (Ming Lei) [2018403]
- squashfs: use bvec_virt (Ming Lei) [2018403]
- dm-integrity: use bvec_virt (Ming Lei) [2018403]
- dm-ebs: use bvec_virt (Ming Lei) [2018403]
- dm: make EBS depend on !HIGHMEM (Ming Lei) [2018403]
- block: use bvec_virt in bio_integrity_{process,free} (Ming Lei) [2018403]
- bvec: add a bvec_virt helper (Ming Lei) [2018403]
- block: ensure the bdi is freed after inode_detach_wb (Ming Lei) [2018403]
- block: free the extended dev_t minor later (Ming Lei) [2018403]
- blk-throtl: optimize IOPS throttle for large IO scenarios (Ming Lei) [2018403]
- block: pass a gendisk to bdev_resize_partition (Ming Lei) [2018403]
- block: pass a gendisk to bdev_del_partition (Ming Lei) [2018403]
- block: pass a gendisk to bdev_add_partition (Ming Lei) [2018403]
- block: store a gendisk in struct parsed_partitions (Ming Lei) [2018403]
- block: remove GENHD_FL_UP (Ming Lei) [2018403]
- bcache: move the del_gendisk call out of bcache_device_free (Ming Lei) [2018403]
- bcache: add proper error unwinding in bcache_device_init (Ming Lei) [2018403]
- sx8: use the internal state machine to check if del_gendisk needs to be called (Ming Lei) [2018403]
- nvme: replace the GENHD_FL_UP check in nvme_mpath_shutdown_disk (Ming Lei) [2018403]
- nvme: remove the GENHD_FL_UP check in nvme_ns_remove (Ming Lei) [2018403]
- mmc: block: cleanup gendisk creation (Ming Lei) [2018403]
- mmc: block: let device_add_disk create disk attributes (Ming Lei) [2018403]
- block: move some macros to blkdev.h (Ming Lei) [2018403]
- block: return ELEVATOR_DISCARD_MERGE if possible (Ming Lei) [2018403]
- block: remove the bd_bdi in struct block_device (Ming Lei) [2018403]
- block: move the bdi from the request_queue to the gendisk (Ming Lei) [2018403]
- block: add a queue_has_disk helper (Ming Lei) [2018403]
- block: pass a gendisk to blk_queue_update_readahead (Ming Lei) [2018403]
- block: remove support for delayed queue registrations (Ming Lei) [2018403]
- dm: delay registering the gendisk (Ming Lei) [2018403]
- dm: move setting md->type into dm_setup_md_queue (Ming Lei) [2018403]
- dm: cleanup cleanup_mapped_device (Ming Lei) [2018403]
- block: support delayed holder registration (Ming Lei) [2018403]
- block: look up holders by bdev (Ming Lei) [2018403]
- block: remove the extra kobject reference in bd_link_disk_holder (Ming Lei) [2018403]
- block: make the block holder code optional (Ming Lei) [2018403]
- loop: Select I/O scheduler 'none' from inside add_disk() (Ming Lei) [2018403]
- blk-mq: Introduce the BLK_MQ_F_NO_SCHED_BY_DEFAULT flag (Ming Lei) [2018403]
- block: remove blk-mq-sysfs dead code (Ming Lei) [2018403]
- loop: raise media_change event (Ming Lei) [2018403]
- block: add a helper to raise a media changed event (Ming Lei) [2018403]
- block: export diskseq in sysfs (Ming Lei) [2018403]
- block: add ioctl to read the disk sequence number (Ming Lei) [2018403]
- block: export the diskseq in uevents (Ming Lei) [2018403]
- block: add disk sequence number (Ming Lei) [2018403]
- block: remove cmdline-parser.c (Ming Lei) [2018403]
- block: remove disk_name() (Ming Lei) [2018403]
- block: simplify disk name formatting in check_partition (Ming Lei) [2018403]
- block: simplify printing the device names disk_stack_limits (Ming Lei) [2018403]
- block: use the %%pg format specifier in show_partition (Ming Lei) [2018403]
- block: use the %%pg format specifier in printk_all_partitions (Ming Lei) [2018403]
- block: reduce stack usage in diskstats_show (Ming Lei) [2018403]
- block: remove bdput (Ming Lei) [2018403]
- block: remove bdgrab (Ming Lei) [2018403]
- loop: don't grab a reference to the block device (Ming Lei) [2018403]
- block: change the refcounting for partitions (Ming Lei) [2018403]
- block: allocate bd_meta_info later in add_partitions (Ming Lei) [2018403]
- block: unhash the whole device inode earlier (Ming Lei) [2018403]
- block: assert the locking state in delete_partition (Ming Lei) [2018403]
- block: use bvec_kmap_local in bio_integrity_process (Ming Lei) [2018403]
- block: use bvec_kmap_local in t10_pi_type1_{prepare,complete} (Ming Lei) [2018403]
- block: use memcpy_from_bvec in __blk_queue_bounce (Ming Lei) [2018403]
- block: use memcpy_from_bvec in bio_copy_kern_endio_read (Ming Lei) [2018403]
- block: use memcpy_to_bvec in copy_to_high_bio_irq (Ming Lei) [2018403]
- block: rewrite bio_copy_data_iter to use bvec_kmap_local and memcpy_to_bvec (Ming Lei) [2018403]
- block: remove bvec_kmap_irq and bvec_kunmap_irq (Ming Lei) [2018403]
- ps3disk: use memcpy_{from,to}_bvec (Ming Lei) [2018403]
- dm-writecache: use bvec_kmap_local instead of bvec_kmap_irq (Ming Lei) [2018403]
- rbd: use memzero_bvec (Ming Lei) [2018403]
- block: use memzero_page in zero_fill_bio (Ming Lei) [2018403]
- bvec: add memcpy_{from,to}_bvec and memzero_bvec helper (Ming Lei) [2018403]
- bvec: add a bvec_kmap_local helper (Ming Lei) [2018403]
- bvec: fix the include guards for bvec.h (Ming Lei) [2018403]
- MIPS: don't include <linux/genhd.h> in <asm/mach-rc32434/rb.h> (Ming Lei) [2018403]
- ioprio: move user space relevant ioprio bits to UAPI includes (Ming Lei) [2018403]
- Revert "virtio-blk: Add validation for block size in config space" (Ming Lei) [2018403]
- virtio-blk: remove unneeded "likely" statements (Ming Lei) [2018403]
- Revert "blk-mq: avoid to iterate over stale request" (Ming Lei) [2018403]
- Revert "block: return ELEVATOR_DISCARD_MERGE if possible" (Ming Lei) [2018403]

* Thu Dec 16 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-33.el9]
- s390/kexec: handle R_390_PLT32DBL rela in arch_kexec_apply_relocations_add() (Philipp Rudo) [2023155]
- s390/kexec_file: fix error handling when applying relocations (Philipp Rudo) [2023155]
- s390/kexec_file: print some more error messages (Philipp Rudo) [2023155]
- udp: Validate checksum in udp_read_sock() (Xin Long) [2026952]
- net: udp: correct the document for udp_mem (Xin Long) [2026952]
- net: udp6: replace __UDP_INC_STATS() with __UDP6_INC_STATS() (Xin Long) [2026952]
- net: prefer socket bound to interface when not in VRF (Xin Long) [2026952]
- udp6: allow SO_MARK ctrl msg to affect routing (Xin Long) [2026952]
- net: udp: annotate data race around udp_sk(sk)->corkflag (Xin Long) [2026952]
- net/ipv4/udp_tunnel_core.c: remove superfluous header files from udp_tunnel_core.c (Xin Long) [2026952]
- udp_tunnel: Fix udp_tunnel_nic work-queue type (Xin Long) [2026952]
- selftests: add a test case for mirred egress to ingress (Hangbin Liu) [2025461]
- selftests/net: udpgso_bench_rx: fix port argument (Hangbin Liu) [2025461]
- selftests: net: test_vxlan_under_vrf: fix HV connectivity test (Hangbin Liu) [2025461]
- selftests: net: tls: remove unused variable and code (Hangbin Liu) [2025461]
- selftests/net: Fix reuseport_bpf_numa by skipping unavailable nodes (Hangbin Liu) [2025461]
- selftests: net: switch to socat in the GSO GRE test (Hangbin Liu) [2025461]
- selftests: net: properly support IPv6 in GSO GRE test (Hangbin Liu) [2025461]
- kselftests/net: add missed vrf_strict_mode_test.sh test to Makefile (Hangbin Liu) [2025461]
- kselftests/net: add missed setup_loopback.sh/setup_veth.sh to Makefile (Hangbin Liu) [2025461]
- kselftests/net: add missed icmp.sh test to Makefile (Hangbin Liu) [2025461]
- selftests: udp: test for passing SO_MARK as cmsg (Hangbin Liu) [2025461]
- selftests/net: update .gitignore with newly added tests (Hangbin Liu) [2025461]
- selftests: net: bridge: update IGMP/MLD membership interval value (Hangbin Liu) [2025461]
- selftests: lib: forwarding: allow tests to not require mz and jq (Hangbin Liu) [2025461]
- fcnal-test: kill hanging ping/nettest binaries on cleanup (Hangbin Liu) [2025461]
- selftests: net/fcnal: Test --{force,no}-bind-key-ifindex (Hangbin Liu) [2025461]
- selftests: nettest: Add --{force,no}-bind-key-ifindex (Hangbin Liu) [2025461]
- selftests: forwarding: Add IPv6 GRE hierarchical tests (Hangbin Liu) [2025461]
- selftests: forwarding: Add IPv6 GRE flat tests (Hangbin Liu) [2025461]
- testing: selftests: tc_common: Add tc_check_at_least_x_packets() (Hangbin Liu) [2025461]
- testing: selftests: forwarding.config.sample: Add tc flag (Hangbin Liu) [2025461]
- selftests: net: fib_nexthops: Wait before checking reported idle time (Hangbin Liu) [2025461]
- selftest: net: fix typo in altname test (Hangbin Liu) [2025461]
- selftests: add simple GSO GRE test (Hangbin Liu) [2025461]
- selftests/net: allow GRO coalesce test on veth (Hangbin Liu) [2025461]
- selftests/net: Use kselftest skip code for skipped tests (Hangbin Liu) [2025461]
- tools/net: Use bitwise instead of arithmetic operator for flags (Hangbin Liu) [2025461]
- selftests: vrf: Add test for SNAT over VRF (Hangbin Liu) [2025461]
- selftests/net: GRO coalesce test (Hangbin Liu) [2025461]
- selftests/net: remove min gso test in packet_snd (Hangbin Liu) [2025461]
- tipc: fix size validations for the MSG_CRYPTO type (Xin Long) [2020513] {CVE-2021-43267}
- redhat/configs: enable CONFIG_RD_ZSTD for rhel (Tao Liu) [2020132]
- powerpc/security: Use a mutex for interrupt exit code patching (Steve Best) [2019202]
- EDAC/mce_amd: Do not load edac_mce_amd module on guests (Aristeu Rozanski) [2000778]

* Thu Dec 16 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-32.el9]
- redhat: configs: explicitly unset CONFIG_DAMON (Rafael Aquini) [2023396]
- mm/memory_hotplug: restrict CONFIG_MEMORY_HOTPLUG to 64 bit (Rafael Aquini) [2023396]
- mm/memory_hotplug: remove CONFIG_MEMORY_HOTPLUG_SPARSE (Rafael Aquini) [2023396]
- mm/memory_hotplug: remove CONFIG_X86_64_ACPI_NUMA dependency from CONFIG_MEMORY_HOTPLUG (Rafael Aquini) [2023396]
- memory-hotplug.rst: document the "auto-movable" online policy (Rafael Aquini) [2023396]
- memory-hotplug.rst: fix wrong /sys/module/memory_hotplug/parameters/ path (Rafael Aquini) [2023396]
- memory-hotplug.rst: fix two instances of "movablecore" that should be "movable_node" (Rafael Aquini) [2023396]
- selftest/vm: fix ksm selftest to run with different NUMA topologies (Rafael Aquini) [2023396]
- mm/vmalloc: introduce alloc_pages_bulk_array_mempolicy to accelerate memory allocation (Rafael Aquini) [2023396]
- memcg: unify memcg stat flushing (Rafael Aquini) [2023396]
- memcg: flush stats only if updated (Rafael Aquini) [2023396]
- mm/swapfile: fix an integer overflow in swap_show() (Rafael Aquini) [2023396]
- mm/gup: further simplify __gup_device_huge() (Rafael Aquini) [2023396]
- kasan: test: add memcpy test that avoids out-of-bounds write (Rafael Aquini) [2023396]
- tools/testing/selftests/vm/split_huge_page_test.c: fix application of sizeof to pointer (Rafael Aquini) [2023396]
- mm/damon/core-test: fix wrong expectations for 'damon_split_regions_of()' (Rafael Aquini) [2023396]
- mm: khugepaged: skip huge page collapse for special files (Rafael Aquini) [2023396]
- mm, thp: bail out early in collapse_file for writeback page (Rafael Aquini) [2023396]
- mm/vmalloc: fix numa spreading for large hash tables (Rafael Aquini) [2023396]
- mm/secretmem: avoid letting secretmem_users drop to zero (Rafael Aquini) [2023396]
- mm/oom_kill.c: prevent a race between process_mrelease and exit_mmap (Rafael Aquini) [2023396]
- mm: filemap: check if THP has hwpoisoned subpage for PMD page fault (Rafael Aquini) [2023396]
- mm: hwpoison: remove the unnecessary THP check (Rafael Aquini) [2023396]
- memcg: page_alloc: skip bulk allocator for __GFP_ACCOUNT (Rafael Aquini) [2023396]
- secretmem: Prevent secretmem_users from wrapping to zero (Rafael Aquini) [2023396]
- Revert "mm/secretmem: use refcount_t instead of atomic_t" (Rafael Aquini) [2023396]
- memblock: exclude MEMBLOCK_NOMAP regions from kmemleak (Rafael Aquini) [2023396]
- Revert "memblock: exclude NOMAP regions from kmemleak" (Rafael Aquini) [2023396]
- mm/thp: decrease nr_thps in file's mapping on THP split (Rafael Aquini) [2023396]
- mm/secretmem: fix NULL page->mapping dereference in page_is_secretmem() (Rafael Aquini) [2023396]
- mm, slub: fix incorrect memcg slab count for bulk free (Rafael Aquini) [2023396]
- mm, slub: fix potential use-after-free in slab_debugfs_fops (Rafael Aquini) [2023396]
- mm, slub: fix potential memoryleak in kmem_cache_open() (Rafael Aquini) [2023396]
- mm, slub: fix mismatch between reconstructed freelist depth and cnt (Rafael Aquini) [2023396]
- mm, slub: fix two bugs in slab_debug_trace_open() (Rafael Aquini) [2023396]
- mm/mempolicy: do not allow illegal MPOL_F_NUMA_BALANCING | MPOL_LOCAL in mbind() (Rafael Aquini) [2023396]
- memblock: check memory total_size (Rafael Aquini) [2023396]
- mm/migrate: fix CPUHP state to update node demotion order (Rafael Aquini) [2023396]
- mm/migrate: add CPU hotplug to demotion #ifdef (Rafael Aquini) [2023396]
- mm/migrate: optimize hotplug-time demotion order updates (Rafael Aquini) [2023396]
- userfaultfd: fix a race between writeprotect and exit_mmap() (Rafael Aquini) [2023396]
- mm/userfaultfd: selftests: fix memory corruption with thp enabled (Rafael Aquini) [2023396]
- memblock: exclude NOMAP regions from kmemleak (Rafael Aquini) [2023396]
- misc: fastrpc: Add missing lock before accessing find_vma() (Rafael Aquini) [2023396]
- mm: fix uninitialized use in overcommit_policy_handler (Rafael Aquini) [2023396]
- mm/memory_failure: fix the missing pte_unmap() call (Rafael Aquini) [2023396]
- kasan: always respect CONFIG_KASAN_STACK (Rafael Aquini) [2023396]
- mm/debug: sync up latest migrate_reason to migrate_reason_names (Rafael Aquini) [2023396]
- mm/debug: sync up MR_CONTIG_RANGE and MR_LONGTERM_PIN (Rafael Aquini) [2023396]
- mm: fs: invalidate bh_lrus for only cold path (Rafael Aquini) [2023396]
- mm/shmem.c: fix judgment error in shmem_is_huge() (Rafael Aquini) [2023396]
- mm/damon: don't use strnlen() with known-bogus source length (Rafael Aquini) [2023396]
- kasan: fix Kconfig check of CC_HAS_WORKING_NOSANITIZE_ADDRESS (Rafael Aquini) [2023396]
- mm, hwpoison: add is_free_buddy_page() in HWPoisonHandlable() (Rafael Aquini) [2023396]
- memcg: flush lruvec stats in the refault (Rafael Aquini) [2023396]
- netfilter: nf_tables: Fix oversized kvmalloc() calls (Rafael Aquini) [2023396]
- mm: Fully initialize invalidate_lock, amend lock class later (Rafael Aquini) [2023396]
- tools/bootconfig: Define memblock_free_ptr() to fix build error (Rafael Aquini) [2023396]
- memblock: introduce saner 'memblock_free_ptr()' interface (Rafael Aquini) [2023396]
- bpf: Add oversize check before call kvcalloc() (Rafael Aquini) [2023396]
- netfilter: ipset: Fix oversized kvmalloc() calls (Rafael Aquini) [2023396]
- bpf, mm: Fix lockdep warning triggered by stack_map_get_build_id_offset() (Rafael Aquini) [2023396]
- tools headers UAPI: Sync files changed by new process_mrelease syscall and the removal of some compat entry points (Rafael Aquini) [2023396]
- arm64: kdump: Skip kmemleak scan reserved memory for kdump (Rafael Aquini) [2023396]
- mm/mempolicy: fix a race between offset_il_node and mpol_rebind_task (Rafael Aquini) [2023396]
- mm/kmemleak: allow __GFP_NOLOCKDEP passed to kmemleak's gfp (Rafael Aquini) [2023396]
- mmap_lock: change trace and locking order (Rafael Aquini) [2023396]
- mm/page_alloc.c: avoid accessing uninitialized pcp page migratetype (Rafael Aquini) [2023396]
- mm,vmscan: fix divide by zero in get_scan_count (Rafael Aquini) [2023396]
- mm/hugetlb: initialize hugetlb_usage in mm_init (Rafael Aquini) [2023396]
- mm/hmm: bypass devmap pte when all pfn requested flags are fulfilled (Rafael Aquini) [2023396]
- arch: remove compat_alloc_user_space (Rafael Aquini) [2023396]
- compat: remove some compat entry points (Rafael Aquini) [2023396]
- mm: simplify compat numa syscalls (Rafael Aquini) [2023396]
- mm: simplify compat_sys_move_pages (Rafael Aquini) [2023396]
- kexec: avoid compat_alloc_user_space (Rafael Aquini) [2023396]
- kexec: move locking into do_kexec_load (Rafael Aquini) [2023396]
- mm: migrate: change to use bool type for 'page_was_mapped' (Rafael Aquini) [2023396]
- mm: migrate: fix the incorrect function name in comments (Rafael Aquini) [2023396]
- mm: migrate: introduce a local variable to get the number of pages (Rafael Aquini) [2023396]
- mm/vmstat: protect per cpu variables with preempt disable on RT (Rafael Aquini) [2023396]
- mm/workingset: correct kernel-doc notations (Rafael Aquini) [2023396]
- percpu: remove export of pcpu_base_addr (Rafael Aquini) [2023396]
- MAINTAINERS: update for DAMON (Rafael Aquini) [2023396]
- mm/damon: add user space selftests (Rafael Aquini) [2023396]
- mm/damon: add kunit tests (Rafael Aquini) [2023396]
- Documentation: add documents for DAMON (Rafael Aquini) [2023396]
- mm/damon/dbgfs: support multiple contexts (Rafael Aquini) [2023396]
- mm/damon/dbgfs: export kdamond pid to the user space (Rafael Aquini) [2023396]
- mm/damon: implement a debugfs-based user space interface (Rafael Aquini) [2023396]
- mm/damon: add a tracepoint (Rafael Aquini) [2023396]
- mm/damon: implement primitives for the virtual memory address spaces (Rafael Aquini) [2023396]
- mm/idle_page_tracking: make PG_idle reusable (Rafael Aquini) [2023396]
- mm/damon: adaptively adjust regions (Rafael Aquini) [2023396]
- mm/damon/core: implement region-based sampling (Rafael Aquini) [2023396]
- mm: introduce Data Access MONitor (DAMON) (Rafael Aquini) [2023396]
- kfence: test: fail fast if disabled at boot (Rafael Aquini) [2023396]
- kfence: show cpu and timestamp in alloc/free info (Rafael Aquini) [2023396]
- mm/secretmem: use refcount_t instead of atomic_t (Rafael Aquini) [2023396]
- mm: introduce PAGEFLAGS_MASK to replace ((1UL << NR_PAGEFLAGS) - 1) (Rafael Aquini) [2023396]
- mm: in_irq() cleanup (Rafael Aquini) [2023396]
- highmem: don't disable preemption on RT in kmap_atomic() (Rafael Aquini) [2023396]
- mm/early_ioremap.c: remove redundant early_ioremap_shutdown() (Rafael Aquini) [2023396]
- mm: don't allow executable ioremap mappings (Rafael Aquini) [2023396]
- mm: move ioremap_page_range to vmalloc.c (Rafael Aquini) [2023396]
- mm: remove redundant compound_head() calling (Rafael Aquini) [2023396]
- mm/memory_hotplug: use helper zone_is_zone_device() to simplify the code (Rafael Aquini) [2023396]
- mm/memory_hotplug: improved dynamic memory group aware "auto-movable" online policy (Rafael Aquini) [2023396]
- mm/memory_hotplug: memory group aware "auto-movable" online policy (Rafael Aquini) [2023396]
- virtio-mem: use a single dynamic memory group for a single virtio-mem device (Rafael Aquini) [2023396]
- dax/kmem: use a single static memory group for a single probed unit (Rafael Aquini) [2023396]
- ACPI: memhotplug: use a single static memory group for a single memory device (Rafael Aquini) [2023396]
- mm/memory_hotplug: track present pages in memory groups (Rafael Aquini) [2023396]
- drivers/base/memory: introduce "memory groups" to logically group memory blocks (Rafael Aquini) [2023396]
- mm/memory_hotplug: introduce "auto-movable" online policy (Rafael Aquini) [2023396]
- mm: track present early pages per zone (Rafael Aquini) [2023396]
- ACPI: memhotplug: memory resources cannot be enabled yet (Rafael Aquini) [2023396]
- mm/memory_hotplug: remove nid parameter from remove_memory() and friends (Rafael Aquini) [2023396]
- mm/memory_hotplug: remove nid parameter from arch_remove_memory() (Rafael Aquini) [2023396]
- mm/memory_hotplug: use "unsigned long" for PFN in zone_for_pfn_range() (Rafael Aquini) [2023396]
- mm: memory_hotplug: cleanup after removal of pfn_valid_within() (Rafael Aquini) [2023396]
- mm: remove pfn_valid_within() and CONFIG_HOLES_IN_ZONE (Rafael Aquini) [2023396]
- memory-hotplug.rst: complete admin-guide overhaul (Rafael Aquini) [2023396]
- memory-hotplug.rst: remove locking details from admin-guide (Rafael Aquini) [2023396]
- Revert "memcg: enable accounting for pollfd and select bits arrays" (Rafael Aquini) [2023396]
- Revert "memcg: enable accounting for file lock caches" (Rafael Aquini) [2023396]
- Revert "mm/gup: remove try_get_page(), call try_get_compound_head() directly" (Rafael Aquini) [2023396]
- binfmt: a.out: Fix bogus semicolon (Rafael Aquini) [2023396]
- mm, slub: convert kmem_cpu_slab protection to local_lock (Rafael Aquini) [2023396]
- mm, slub: use migrate_disable() on PREEMPT_RT (Rafael Aquini) [2023396]
- mm, slub: protect put_cpu_partial() with disabled irqs instead of cmpxchg (Rafael Aquini) [2023396]
- mm, slub: make slab_lock() disable irqs with PREEMPT_RT (Rafael Aquini) [2023396]
- mm: slub: make object_map_lock a raw_spinlock_t (Rafael Aquini) [2023396]
- mm: slub: move flush_cpu_slab() invocations __free_slab() invocations out of IRQ context (Rafael Aquini) [2023396]
- mm, slab: split out the cpu offline variant of flush_slab() (Rafael Aquini) [2023396]
- mm, slub: don't disable irqs in slub_cpu_dead() (Rafael Aquini) [2023396]
- mm, slub: only disable irq with spin_lock in __unfreeze_partials() (Rafael Aquini) [2023396]
- mm, slub: separate detaching of partial list in unfreeze_partials() from unfreezing (Rafael Aquini) [2023396]
- mm, slub: detach whole partial list at once in unfreeze_partials() (Rafael Aquini) [2023396]
- mm, slub: discard slabs in unfreeze_partials() without irqs disabled (Rafael Aquini) [2023396]
- mm, slub: move irq control into unfreeze_partials() (Rafael Aquini) [2023396]
- mm, slub: call deactivate_slab() without disabling irqs (Rafael Aquini) [2023396]
- mm, slub: make locking in deactivate_slab() irq-safe (Rafael Aquini) [2023396]
- mm, slub: move reset of c->page and freelist out of deactivate_slab() (Rafael Aquini) [2023396]
- mm, slub: stop disabling irqs around get_partial() (Rafael Aquini) [2023396]
- mm, slub: check new pages with restored irqs (Rafael Aquini) [2023396]
- mm, slub: validate slab from partial list or page allocator before making it cpu slab (Rafael Aquini) [2023396]
- mm, slub: restore irqs around calling new_slab() (Rafael Aquini) [2023396]
- mm, slub: move disabling irqs closer to get_partial() in ___slab_alloc() (Rafael Aquini) [2023396]
- mm, slub: do initial checks in ___slab_alloc() with irqs enabled (Rafael Aquini) [2023396]
- mm, slub: move disabling/enabling irqs to ___slab_alloc() (Rafael Aquini) [2023396]
- mm, slub: simplify kmem_cache_cpu and tid setup (Rafael Aquini) [2023396]
- mm, slub: restructure new page checks in ___slab_alloc() (Rafael Aquini) [2023396]
- mm, slub: return slab page from get_partial() and set c->page afterwards (Rafael Aquini) [2023396]
- mm, slub: dissolve new_slab_objects() into ___slab_alloc() (Rafael Aquini) [2023396]
- mm, slub: extract get_partial() from new_slab_objects() (Rafael Aquini) [2023396]
- mm, slub: remove redundant unfreeze_partials() from put_cpu_partial() (Rafael Aquini) [2023396]
- mm, slub: don't disable irq for debug_check_no_locks_freed() (Rafael Aquini) [2023396]
- mm, slub: allocate private object map for validate_slab_cache() (Rafael Aquini) [2023396]
- mm, slub: allocate private object map for debugfs listings (Rafael Aquini) [2023396]
- mm, slub: don't call flush_all() from slab_debug_trace_open() (Rafael Aquini) [2023396]
- mm/madvise: add MADV_WILLNEED to process_madvise() (Rafael Aquini) [2023396]
- mm/vmstat: remove unneeded return value (Rafael Aquini) [2023396]
- mm/vmstat: simplify the array size calculation (Rafael Aquini) [2023396]
- mm/vmstat: correct some wrong comments (Rafael Aquini) [2023396]
- mm/percpu,c: remove obsolete comments of pcpu_chunk_populated() (Rafael Aquini) [2023396]
- selftests: vm: add COW time test for KSM pages (Rafael Aquini) [2023396]
- selftests: vm: add KSM merging time test (Rafael Aquini) [2023396]
- mm: KSM: fix data type (Rafael Aquini) [2023396]
- selftests: vm: add KSM merging across nodes test (Rafael Aquini) [2023396]
- selftests: vm: add KSM zero page merging test (Rafael Aquini) [2023396]
- selftests: vm: add KSM unmerge test (Rafael Aquini) [2023396]
- selftests: vm: add KSM merge test (Rafael Aquini) [2023396]
- mm/migrate: correct kernel-doc notation (Rafael Aquini) [2023396]
- mm: wire up syscall process_mrelease (Rafael Aquini) [2023396]
- mm: introduce process_mrelease system call (Rafael Aquini) [2023396]
- memblock: make memblock_find_in_range method private (Rafael Aquini) [2023396]
- mm/mempolicy.c: use in_task() in mempolicy_slab_node() (Rafael Aquini) [2023396]
- mm/mempolicy: unify the create() func for bind/interleave/prefer-many policies (Rafael Aquini) [2023396]
- mm/mempolicy: advertise new MPOL_PREFERRED_MANY (Rafael Aquini) [2023396]
- mm/hugetlb: add support for mempolicy MPOL_PREFERRED_MANY (Rafael Aquini) [2023396]
- mm/memplicy: add page allocation function for MPOL_PREFERRED_MANY policy (Rafael Aquini) [2023396]
- mm/mempolicy: add MPOL_PREFERRED_MANY for multiple preferred nodes (Rafael Aquini) [2023396]
- mm/mempolicy: use readable NUMA_NO_NODE macro instead of magic number (Rafael Aquini) [2023396]
- mm: compaction: support triggering of proactive compaction by user (Rafael Aquini) [2023396]
- mm: compaction: optimize proactive compaction deferrals (Rafael Aquini) [2023396]
- mm, vmscan: guarantee drop_slab_node() termination (Rafael Aquini) [2023396]
- mm/vmscan: add 'else' to remove check_pending label (Rafael Aquini) [2023396]
- mm/vmscan: remove unneeded return value of kswapd_run() (Rafael Aquini) [2023396]
- mm/vmscan: remove misleading setting to sc->priority (Rafael Aquini) [2023396]
- mm/vmscan: remove the PageDirty check after MADV_FREE pages are page_ref_freezed (Rafael Aquini) [2023396]
- mm/vmpressure: replace vmpressure_to_css() with vmpressure_to_memcg() (Rafael Aquini) [2023396]
- mm/migrate: add sysfs interface to enable reclaim migration (Rafael Aquini) [2023396]
- mm/vmscan: never demote for memcg reclaim (Rafael Aquini) [2023396]
- mm/vmscan: Consider anonymous pages without swap (Rafael Aquini) [2023396]
- mm/vmscan: add helper for querying ability to age anonymous pages (Rafael Aquini) [2023396]
- mm/vmscan: add page demotion counter (Rafael Aquini) [2023396]
- mm/migrate: demote pages during reclaim (Rafael Aquini) [2023396]
- mm/migrate: enable returning precise migrate_pages() success count (Rafael Aquini) [2023396]
- mm/migrate: update node demotion order on hotplug events (Rafael Aquini) [2023396]
- mm/numa: automatically generate node migration order (Rafael Aquini) [2023396]
- selftests/vm/userfaultfd: wake after copy failure (Rafael Aquini) [2023396]
- userfaultfd: prevent concurrent API initialization (Rafael Aquini) [2023396]
- userfaultfd: change mmap_changing to atomic (Rafael Aquini) [2023396]
- hugetlb: fix hugetlb cgroup refcounting during vma split (Rafael Aquini) [2023396]
- hugetlb: before freeing hugetlb page set dtor to appropriate value (Rafael Aquini) [2023396]
- hugetlb: drop ref count earlier after page allocation (Rafael Aquini) [2023396]
- hugetlb: simplify prep_compound_gigantic_page ref count racing code (Rafael Aquini) [2023396]
- mm: fix panic caused by __page_handle_poison() (Rafael Aquini) [2023396]
- mm: hwpoison: dump page for unhandlable page (Rafael Aquini) [2023396]
- doc: hwpoison: correct the support for hugepage (Rafael Aquini) [2023396]
- mm: hwpoison: don't drop slab caches for offlining non-LRU page (Rafael Aquini) [2023396]
- mm/hwpoison: fix some obsolete comments (Rafael Aquini) [2023396]
- mm/hwpoison: change argument struct page **hpagep to *hpage (Rafael Aquini) [2023396]
- mm/hwpoison: fix potential pte_unmap_unlock pte error (Rafael Aquini) [2023396]
- mm/hwpoison: remove unneeded variable unmap_success (Rafael Aquini) [2023396]
- mm/page_isolation: tracing: trace all test_pages_isolated failures (Rafael Aquini) [2023396]
- mm/page_alloc.c: use in_task() (Rafael Aquini) [2023396]
- mm/page_alloc: make alloc_node_mem_map() __init rather than __ref (Rafael Aquini) [2023396]
- mm/page_alloc.c: fix 'zone_id' may be used uninitialized in this function warning (Rafael Aquini) [2023396]
- memblock: stop poisoning raw allocations (Rafael Aquini) [2023396]
- mm: introduce memmap_alloc() to unify memory map allocation (Rafael Aquini) [2023396]
- mm/page_alloc: always initialize memory map for the holes (Rafael Aquini) [2023396]
- kasan: test: avoid corrupting memory in kasan_rcu_uaf (Rafael Aquini) [2023396]
- kasan: test: avoid corrupting memory in copy_user_test (Rafael Aquini) [2023396]
- kasan: test: clean up ksize_uaf (Rafael Aquini) [2023396]
- kasan: test: only do kmalloc_uaf_memset for generic mode (Rafael Aquini) [2023396]
- kasan: test: disable kmalloc_memmove_invalid_size for HW_TAGS (Rafael Aquini) [2023396]
- kasan: test: avoid corrupting memory via memset (Rafael Aquini) [2023396]
- kasan: test: avoid writing invalid memory (Rafael Aquini) [2023396]
- kasan: test: rework kmalloc_oob_right (Rafael Aquini) [2023396]
- mm/kasan: move kasan.fault to mm/kasan/report.c (Rafael Aquini) [2023396]
- mm/vmalloc: fix wrong behavior in vread (Rafael Aquini) [2023396]
- lib/test_vmalloc.c: add a new 'nr_pages' parameter (Rafael Aquini) [2023396]
- mm/vmalloc: remove gfpflags_allow_blocking() check (Rafael Aquini) [2023396]
- mm/vmalloc: use batched page requests in bulk-allocator (Rafael Aquini) [2023396]
- mm/sparse: clarify pgdat_to_phys (Rafael Aquini) [2023396]
- include/linux/mmzone.h: avoid a warning in sparse memory support (Rafael Aquini) [2023396]
- mm/sparse: set SECTION_NID_SHIFT to 6 (Rafael Aquini) [2023396]
- mm: sparse: remove __section_nr() function (Rafael Aquini) [2023396]
- mm: sparse: pass section_nr to find_memory_block (Rafael Aquini) [2023396]
- mm: sparse: pass section_nr to section_mark_present (Rafael Aquini) [2023396]
- mm/bootmem_info.c: mark __init on register_page_bootmem_info_section (Rafael Aquini) [2023396]
- mm/mremap: fix memory account on do_munmap() failure (Rafael Aquini) [2023396]
- remap_file_pages: Use vma_lookup() instead of find_vma() (Rafael Aquini) [2023396]
- mm/pagemap: add mmap_assert_locked() annotations to find_vma*() (Rafael Aquini) [2023396]
- mm: change fault_in_pages_* to have an unsigned size parameter (Rafael Aquini) [2023396]
- mm,do_huge_pmd_numa_page: remove unnecessary TLB flushing code (Rafael Aquini) [2023396]
- mm: remove flush_kernel_dcache_page (Rafael Aquini) [2023396]
- scatterlist: replace flush_kernel_dcache_page with flush_dcache_page (Rafael Aquini) [2023396]
- mmc: mmc_spi: replace flush_kernel_dcache_page with flush_dcache_page (Rafael Aquini) [2023396]
- mmc: JZ4740: remove the flush_kernel_dcache_page call in jz4740_mmc_read_data (Rafael Aquini) [2023396]
- selftests: Fix spelling mistake "cann't" -> "cannot" (Rafael Aquini) [2023396]
- selftests/vm: use kselftest skip code for skipped tests (Rafael Aquini) [2023396]
- memcg: make memcg->event_list_lock irqsafe (Rafael Aquini) [2023396]
- memcg: fix up drain_local_stock comment (Rafael Aquini) [2023396]
- mm, memcg: save some atomic ops when flush is already true (Rafael Aquini) [2023396]
- mm, memcg: remove unused functions (Rafael Aquini) [2023396]
- mm: memcontrol: set the correct memcg swappiness restriction (Rafael Aquini) [2023396]
- memcg: replace in_interrupt() by !in_task() in active_memcg() (Rafael Aquini) [2023396]
- memcg: cleanup racy sum avoidance code (Rafael Aquini) [2023396]
- memcg: enable accounting for ldt_struct objects (Rafael Aquini) [2023396]
- memcg: enable accounting for posix_timers_cache slab (Rafael Aquini) [2023396]
- memcg: enable accounting for signals (Rafael Aquini) [2023396]
- memcg: enable accounting for new namesapces and struct nsproxy (Rafael Aquini) [2023396]
- memcg: enable accounting for fasync_cache (Rafael Aquini) [2023396]
- memcg: enable accounting for file lock caches (Rafael Aquini) [2023396]
- memcg: enable accounting for pollfd and select bits arrays (Rafael Aquini) [2023396]
- memcg: enable accounting for mnt_cache entries (Rafael Aquini) [2023396]
- memcg: charge fs_context and legacy_fs_context (Rafael Aquini) [2023396]
- memcg: infrastructure to flush memcg stats (Rafael Aquini) [2023396]
- memcg: switch lruvec stats to rstat (Rafael Aquini) [2023396]
- mm, memcg: inline swap-related functions to improve disabled memcg config (Rafael Aquini) [2023396]
- mm, memcg: inline mem_cgroup_{charge/uncharge} to improve disabled memcg config (Rafael Aquini) [2023396]
- mm, memcg: add mem_cgroup_disabled checks in vmpressure and swap-related functions (Rafael Aquini) [2023396]
- huge tmpfs: decide stat.st_blksize by shmem_is_huge() (Rafael Aquini) [2023396]
- huge tmpfs: shmem_is_huge(vma, inode, index) (Rafael Aquini) [2023396]
- huge tmpfs: SGP_NOALLOC to stop collapse_file() on race (Rafael Aquini) [2023396]
- huge tmpfs: move shmem_huge_enabled() upwards (Rafael Aquini) [2023396]
- huge tmpfs: revert shmem's use of transhuge_vma_enabled() (Rafael Aquini) [2023396]
- huge tmpfs: remove shrinklist addition from shmem_setattr() (Rafael Aquini) [2023396]
- huge tmpfs: fix split_huge_page() after FALLOC_FL_KEEP_SIZE (Rafael Aquini) [2023396]
- huge tmpfs: fix fallocate(vanilla) advance over huge pages (Rafael Aquini) [2023396]
- shmem: shmem_writepage() split unlikely i915 THP (Rafael Aquini) [2023396]
- shmem: include header file to declare swap_info (Rafael Aquini) [2023396]
- shmem: remove unneeded function forward declaration (Rafael Aquini) [2023396]
- shmem: remove unneeded header file (Rafael Aquini) [2023396]
- shmem: remove unneeded variable ret (Rafael Aquini) [2023396]
- shmem: use raw_spinlock_t for ->stat_lock (Rafael Aquini) [2023396]
- mm/gup: remove try_get_page(), call try_get_compound_head() directly (Rafael Aquini) [2023396]
- mm/gup: small refactoring: simplify try_grab_page() (Rafael Aquini) [2023396]
- mm/gup: documentation corrections for gup/pup (Rafael Aquini) [2023396]
- mm: gup: use helper PAGE_ALIGNED in populate_vma_page_range() (Rafael Aquini) [2023396]
- mm: gup: fix potential pgmap refcnt leak in __gup_device_huge() (Rafael Aquini) [2023396]
- mm: gup: remove useless BUG_ON in __get_user_pages() (Rafael Aquini) [2023396]
- mm: gup: remove unneed local variable orig_refs (Rafael Aquini) [2023396]
- mm: gup: remove set but unused local variable major (Rafael Aquini) [2023396]
- mm: delete unused get_kernel_page() (Rafael Aquini) [2023396]
- include/linux/buffer_head.h: fix boolreturn.cocci warnings (Rafael Aquini) [2023396]
- fs, mm: fix race in unlinking swapfile (Rafael Aquini) [2023396]
- fs: inode: count invalidated shadow pages in pginodesteal (Rafael Aquini) [2023396]
- fs: drop_caches: fix skipping over shadow cache inodes (Rafael Aquini) [2023396]
- fs: update documentation of get_write_access() and friends (Rafael Aquini) [2023396]
- filesystems/locking: fix Malformed table warning (Rafael Aquini) [2023396]
- writeback: memcg: simplify cgroup_writeback_by_id (Rafael Aquini) [2023396]
- writeback: use READ_ONCE for unlocked reads of writeback stats (Rafael Aquini) [2023396]
- writeback: rename domain_update_bandwidth() (Rafael Aquini) [2023396]
- writeback: fix bandwidth estimate for spiky workload (Rafael Aquini) [2023396]
- writeback: reliably update bandwidth estimation (Rafael Aquini) [2023396]
- writeback: track number of inodes under writeback (Rafael Aquini) [2023396]
- writeback: make the laptop_mode prototypes available unconditionally (Rafael Aquini) [2023396]
- mm: remove irqsave/restore locking from contexts with irqs enabled (Rafael Aquini) [2023396]
- mm: add kernel_misc_reclaimable in show_free_areas (Rafael Aquini) [2023396]
- mm: report a more useful address for reclaim acquisition (Rafael Aquini) [2023396]
- mm/debug_vm_pgtable: fix corrupted page flag (Rafael Aquini) [2023396]
- mm/debug_vm_pgtable: remove unused code (Rafael Aquini) [2023396]
- mm/debug_vm_pgtable: use struct pgtable_debug_args in PGD and P4D modifying tests (Rafael Aquini) [2023396]
- mm/debug_vm_pgtable: use struct pgtable_debug_args in PUD modifying tests (Rafael Aquini) [2023396]
- mm/debug_vm_pgtable: use struct pgtable_debug_args in PMD modifying tests (Rafael Aquini) [2023396]
- mm/debug_vm_pgtable: use struct pgtable_debug_args in PTE modifying tests (Rafael Aquini) [2023396]
- mm/debug_vm_pgtable: use struct pgtable_debug_args in migration and thp tests (Rafael Aquini) [2023396]
- mm/debug_vm_pgtable: use struct pgtable_debug_args in soft_dirty and swap tests (Rafael Aquini) [2023396]
- mm/debug_vm_pgtable: use struct pgtable_debug_args in protnone and devmap tests (Rafael Aquini) [2023396]
- mm/debug_vm_pgtable: use struct pgtable_debug_args in leaf and savewrite tests (Rafael Aquini) [2023396]
- mm/debug_vm_pgtable: use struct pgtable_debug_args in basic tests (Rafael Aquini) [2023396]
- mm/debug_vm_pgtable: introduce struct pgtable_debug_args (Rafael Aquini) [2023396]
- mm: ignore MAP_DENYWRITE in ksys_mmap_pgoff() (Rafael Aquini) [2023396]
- mm: remove VM_DENYWRITE (Rafael Aquini) [2023396]
- binfmt: remove in-tree usage of MAP_DENYWRITE (Rafael Aquini) [2023396]
- kernel/fork: always deny write access to current MM exe_file (Rafael Aquini) [2023396]
- kernel/fork: factor out replacing the current MM exe_file (Rafael Aquini) [2023396]
- binfmt: don't use MAP_DENYWRITE when loading shared libraries via uselib() (Rafael Aquini) [2023396]
- ARM: 9115/1: mm/maccess: fix unaligned copy_{from,to}_kernel_nofault (Rafael Aquini) [2023396]
- net-memcg: pass in gfp_t mask to mem_cgroup_charge_skmem() (Rafael Aquini) [2023396]
- memblock: Check memory add/cap ordering (Rafael Aquini) [2023396]
- memblock: Add missing debug code to memblock_add_node() (Rafael Aquini) [2023396]
- mm: don't allow oversized kvmalloc() calls (Rafael Aquini) [2023396]
- mm: Add kvrealloc() (Rafael Aquini) [2023396]
- mm: hide laptop_mode_wb_timer entirely behind the BDI API (Rafael Aquini) [2023396]
- mm: Add functions to lock invalidate_lock for two mappings (Rafael Aquini) [2023396]
- mm: Protect operations adding pages to page cache with invalidate_lock (Rafael Aquini) [2023396]
- mm: Fix comments mentioning i_mutex (Rafael Aquini) [2023396]
- exit/bdflush: Remove the deprecated bdflush system call (Rafael Aquini) [2023396]

* Tue Dec 14 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-31.el9]
- Disable CONFIG_DEBUG_PREEMPT to restore performance (Phil Auld) [2030877]
- tcp: seq_file: Avoid skipping sk during tcp_seek_last_pos (Paolo Abeni) [2028279]
- tcp: fix tp->undo_retrans accounting in tcp_sacktag_one() (Paolo Abeni) [2028279]
- tcp: md5: Fix overlap between vrf and non-vrf keys (Paolo Abeni) [2028279]
- tcp: don't free a FIN sk_buff in tcp_remove_empty_skb() (Paolo Abeni) [2028279]
- tcp: Fix uninitialized access in skb frags array for Rx 0cp. (Paolo Abeni) [2028279]
- tcp_cubic: fix spurious Hystart ACK train detections for not-cwnd-limited flows (Paolo Abeni) [2028279]
- Revert "ibmvnic: check failover_pending in login response" (Steve Best) [2010612]
- ibmvnic: check failover_pending in login response (Steve Best) [2010612]
- ibmvnic: check failover_pending in login response (Steve Best) [2010612]
- kernfs: don't create a negative dentry if inactive node exists (Ian Kent) [2004858]
- kernfs: also call kernfs_set_rev() for positive dentry (Ian Kent) [2004858]
- kernfs: dont call d_splice_alias() under kernfs node lock (Ian Kent) [2004858]
- kernfs: use i_lock to protect concurrent inode updates (Ian Kent) [2004858]
- kernfs: switch kernfs to use an rwsem (Ian Kent) [2004858]
- kernfs: use VFS negative dentry caching (Ian Kent) [2004858]
- kernfs: add a revision to identify directory node changes (Ian Kent) [2004858]
- drm/hyperv: Fix double mouse pointers (Vitaly Kuznetsov) [1999697]
- Revert "watchdog: iTCO_wdt: Account for rebooting on second timeout" (Frantisek Sumsal) [2020918]
- watchdog: iTCO_wdt: Fix detection of SMI-off case (Frantisek Sumsal) [2020918]
- redhat/kernel.spec.template: enable dependencies generation (Eugene Syromiatnikov) [1975927]
- redhat: configs: Update configs for vmware (Kamal Heib) [1991676 2009344]
- redhat/configs: Enable CONFIG_DRM_VMWGFX on aarch64 (Michel Dänzer) [1992253]

* Mon Dec 13 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-30.el9]
- selftests: KVM: avoid failures due to reserved HyperTransport region (Vitaly Kuznetsov) [2009338]
- KVM: X86: Fix when shadow_root_level=5 && guest root_level<4 (Vitaly Kuznetsov) [2009338]
- KVM: x86: inhibit APICv when KVM_GUESTDBG_BLOCKIRQ active (Vitaly Kuznetsov) [2009338]
- KVM: x86/xen: Fix get_attr of KVM_XEN_ATTR_TYPE_SHARED_INFO (Vitaly Kuznetsov) [2009338]
- KVM: x86: Use rw_semaphore for APICv lock to allow vCPU parallelism (Vitaly Kuznetsov) [2009338]
- KVM: selftests: test KVM_GUESTDBG_BLOCKIRQ (Vitaly Kuznetsov) [2009338]
- x86/sgx/virt: implement SGX_IOC_VEPC_REMOVE ioctl (Vitaly Kuznetsov) [2009338]
- x86/sgx/virt: extract sgx_vepc_remove_page (Vitaly Kuznetsov) [2009338]
- KVM: x86: Do not mark all registers as avail/dirty during RESET/INIT (Vitaly Kuznetsov) [2009338]
- KVM: x86/mmu: Complete prefetch for trailing SPTEs for direct, legacy MMU (Vitaly Kuznetsov) [2009338]
- KVM: x86: SVM: don't set VMLOAD/VMSAVE intercepts on vCPU reset (Vitaly Kuznetsov) [2009338]
- selftests: kvm: fix mismatched fclose() after popen() (Vitaly Kuznetsov) [2009338]
- KVM: selftests: set CPUID before setting sregs in vcpu creation (Vitaly Kuznetsov) [2009338]
- KVM: VMX: Unregister posted interrupt wakeup handler on hardware unsetup (Vitaly Kuznetsov) [2009338]
- Revert "x86/kvm: fix vcpu-id indexed array sizes" (Vitaly Kuznetsov) [2009338]
- KVM: X86: Cache CR3 in prev_roots when PCID is disabled (Vitaly Kuznetsov) [2009338]
- KVM: X86: Fix tlb flush for tdp in kvm_invalidate_pcid() (Vitaly Kuznetsov) [2009338]
- KVM: X86: Don't reset mmu context when toggling X86_CR4_PGE (Vitaly Kuznetsov) [2009338]
- KVM: X86: Don't reset mmu context when X86_CR4_PCIDE 1->0 (Vitaly Kuznetsov) [2009338]
- KVM: x86/mmu: kvm_faultin_pfn has to return false if pfh is returned (Vitaly Kuznetsov) [2009338]
- KVM: x86/mmu: Drop a redundant, broken remote TLB flush (Vitaly Kuznetsov) [2009338]
- KVM: x86/mmu: Drop a redundant remote TLB flush in kvm_zap_gfn_range() (Vitaly Kuznetsov) [2009338]
- KVM: x86: Take srcu lock in post_kvm_run_save() (Vitaly Kuznetsov) [2009338]
- KVM: SEV-ES: fix another issue with string I/O VMGEXITs (Vitaly Kuznetsov) [2009338]
- KVM: x86/xen: Fix kvm_xen_has_interrupt() sleeping in kvm_vcpu_block() (Vitaly Kuznetsov) [2009338]
- KVM: x86: switch pvclock_gtod_sync_lock to a raw spinlock (Vitaly Kuznetsov) [2009338]
- tools headers UAPI: Sync x86's asm/kvm.h with the kernel sources (Vitaly Kuznetsov) [2009338]
- tools headers UAPI: Sync linux/kvm.h with the kernel sources (Vitaly Kuznetsov) [2009338]
- KVM: kvm_stat: do not show halt_wait_ns (Vitaly Kuznetsov) [2009338]
- KVM: SEV-ES: go over the sev_pio_data buffer in multiple passes if needed (Vitaly Kuznetsov) [2009338]
- KVM: SEV-ES: keep INS functions together (Vitaly Kuznetsov) [2009338]
- KVM: x86: remove unnecessary arguments from complete_emulator_pio_in (Vitaly Kuznetsov) [2009338]
- KVM: x86: split the two parts of emulator_pio_in (Vitaly Kuznetsov) [2009338]
- KVM: SEV-ES: clean up kvm_sev_es_ins/outs (Vitaly Kuznetsov) [2009338]
- KVM: x86: leave vcpu->arch.pio.count alone in emulator_pio_in_out (Vitaly Kuznetsov) [2009338]
- KVM: SEV-ES: rename guest_ins_data to sev_pio_data (Vitaly Kuznetsov) [2009338]
- KVM: SEV: Flush cache on non-coherent systems before RECEIVE_UPDATE_DATA (Vitaly Kuznetsov) [2009338]
- KVM: MMU: Reset mmu->pkru_mask to avoid stale data (Vitaly Kuznetsov) [2009338]
- KVM: nVMX: promptly process interrupts delivered while in guest mode (Vitaly Kuznetsov) [2009338]
- KVM: x86: check for interrupts before deciding whether to exit the fast path (Vitaly Kuznetsov) [2009338]
- KVM: SEV-ES: reduce ghcb_sa_len to 32 bits (Vitaly Kuznetsov) [2009338]
- KVM: VMX: Remove redundant handling of bus lock vmexit (Vitaly Kuznetsov) [2009338]
- KVM: x86: WARN if APIC HW/SW disable static keys are non-zero on unload (Vitaly Kuznetsov) [2009338]
- Revert "KVM: x86: Open code necessary bits of kvm_lapic_set_base() at vCPU RESET" (Vitaly Kuznetsov) [2009338]
- KVM: SEV-ES: Set guest_state_protected after VMSA update (Vitaly Kuznetsov) [2009338]
- KVM: X86: fix lazy allocation of rmaps (Vitaly Kuznetsov) [2009338]
- KVM: SEV-ES: fix length of string I/O (Vitaly Kuznetsov) [2009338]
- kvm: fix objtool relocation warning (Vitaly Kuznetsov) [2009338]
- KVM: selftests: Ensure all migrations are performed when test is affined (Vitaly Kuznetsov) [2009338]
- KVM: x86: Swap order of CPUID entry "index" vs. "significant flag" checks (Vitaly Kuznetsov) [2009338]
- x86/kvmclock: Move this_cpu_pvti into kvmclock.h (Vitaly Kuznetsov) [2009338]
- selftests: KVM: Don't clobber XMM register when read (Vitaly Kuznetsov) [2009338]
- KVM: VMX: Fix a TSX_CTRL_CPUID_CLEAR field mask issue (Vitaly Kuznetsov) [2009338]
- selftests: KVM: Explicitly use movq to read xmm registers (Vitaly Kuznetsov) [2009338]
- selftests: KVM: Call ucall_init when setting up in rseq_test (Vitaly Kuznetsov) [2009338]
- KVM: Remove tlbs_dirty (Vitaly Kuznetsov) [2009338]
- KVM: X86: Synchronize the shadow pagetable before link it (Vitaly Kuznetsov) [2009338]
- KVM: X86: Fix missed remote tlb flush in rmap_write_protect() (Vitaly Kuznetsov) [2009338]
- KVM: x86: nSVM: don't copy virt_ext from vmcb12 (Vitaly Kuznetsov) [2009338]
- KVM: x86: nSVM: test eax for 4K alignment for GP errata workaround (Vitaly Kuznetsov) [2009338]
- KVM: x86: selftests: test simultaneous uses of V_IRQ from L1 and L0 (Vitaly Kuznetsov) [2009338]
- KVM: x86: nSVM: restore int_vector in svm_clear_vintr (Vitaly Kuznetsov) [2009338]
- kvm: x86: Add AMD PMU MSRs to msrs_to_save_all[] (Vitaly Kuznetsov) [2009338]
- KVM: x86: nVMX: re-evaluate emulation_required on nested VM exit (Vitaly Kuznetsov) [2009338]
- KVM: x86: nVMX: don't fail nested VM entry on invalid guest state if !from_vmentry (Vitaly Kuznetsov) [2009338]
- KVM: x86: VMX: synthesize invalid VM exit when emulating invalid guest state (Vitaly Kuznetsov) [2009338]
- KVM: x86: nSVM: refactor svm_leave_smm and smm_enter_smm (Vitaly Kuznetsov) [2009338]
- KVM: x86: SVM: call KVM_REQ_GET_NESTED_STATE_PAGES on exit from SMM mode (Vitaly Kuznetsov) [2009338]
- KVM: x86: reset pdptrs_from_userspace when exiting smm (Vitaly Kuznetsov) [2009338]
- KVM: x86: nSVM: restore the L1 host state prior to resuming nested guest on SMM exit (Vitaly Kuznetsov) [2009338]
- KVM: KVM: Use cpumask_available() to check for NULL cpumask when kicking vCPUs (Vitaly Kuznetsov) [2009338]
- KVM: Clean up benign vcpu->cpu data races when kicking vCPUs (Vitaly Kuznetsov) [2009338]
- KVM: selftests: Create a separate dirty bitmap per slot (Vitaly Kuznetsov) [2009338]
- KVM: selftests: Refactor help message for -s backing_src (Vitaly Kuznetsov) [2009338]
- KVM: selftests: Change backing_src flag to -s in demand_paging_test (Vitaly Kuznetsov) [2009338]
- KVM: SEV: Allow some commands for mirror VM (Vitaly Kuznetsov) [2009338]
- KVM: SEV: Update svm_vm_copy_asid_from for SEV-ES (Vitaly Kuznetsov) [2009338]
- KVM: nVMX: Fix nested bus lock VM exit (Vitaly Kuznetsov) [2009338]
- KVM: x86: Identify vCPU0 by its vcpu_idx instead of its vCPUs array entry (Vitaly Kuznetsov) [2009338]
- KVM: x86: Query vcpu->vcpu_idx directly and drop its accessor (Vitaly Kuznetsov) [2009338]
- kvm: fix wrong exception emulation in check_rdtsc (Vitaly Kuznetsov) [2009338]
- KVM: SEV: Pin guest memory for write for RECEIVE_UPDATE_DATA (Vitaly Kuznetsov) [2009338]
- KVM: SVM: fix missing sev_decommission in sev_receive_start (Vitaly Kuznetsov) [2009338]
- KVM: SEV: Acquire vcpu mutex when updating VMSA (Vitaly Kuznetsov) [2009338]
- KVM: do not shrink halt_poll_ns below grow_start (Vitaly Kuznetsov) [2009338]
- KVM: nVMX: fix comments of handle_vmon() (Vitaly Kuznetsov) [2009338]
- KVM: x86: Handle SRCU initialization failure during page track init (Vitaly Kuznetsov) [2009338]
- KVM: VMX: Remove defunct "nr_active_uret_msrs" field (Vitaly Kuznetsov) [2009338]
- selftests: KVM: Align SMCCC call with the spec in steal_time (Vitaly Kuznetsov) [2009338]
- selftests: KVM: Fix check for !POLLIN in demand_paging_test (Vitaly Kuznetsov) [2009338]
- KVM: x86: Clear KVM's cached guest CR3 at RESET/INIT (Vitaly Kuznetsov) [2009338]
- KVM: x86: Mark all registers as avail/dirty at vCPU creation (Vitaly Kuznetsov) [2009338]
- KVM: selftests: Add a test for KVM_RUN+rseq to detect task migration bugs (Vitaly Kuznetsov) [2009338]
- tools: Move x86 syscall number fallbacks to .../uapi/ (Vitaly Kuznetsov) [2009338]
- KVM: rseq: Update rseq when processing NOTIFY_RESUME on xfer to KVM guest (Vitaly Kuznetsov) [2009338]
- selftests: kvm: fix get_run_delay() ignoring fscanf() return warn (Vitaly Kuznetsov) [2009338]
- selftests: kvm: move get_run_delay() into lib/test_util (Vitaly Kuznetsov) [2009338]
- selftests:kvm: fix get_trans_hugepagesz() ignoring fscanf() return warn (Vitaly Kuznetsov) [2009338]
- selftests:kvm: fix get_warnings_count() ignoring fscanf() return warn (Vitaly Kuznetsov) [2009338]
- tools: rename bitmap_alloc() to bitmap_zalloc() (Vitaly Kuznetsov) [2009338]
- KVM: Drop unused kvm_dirty_gfn_invalid() (Vitaly Kuznetsov) [2009338]
- KVM: x86: Update vCPU's hv_clock before back to guest when tsc_offset is adjusted (Vitaly Kuznetsov) [2009338]
- KVM: MMU: mark role_regs and role accessors as maybe unused (Vitaly Kuznetsov) [2009338]
- x86/kvm: Don't enable IRQ when IRQ enabled in kvm_wait (Vitaly Kuznetsov) [2009338]
- KVM: stats: Add VM stat for remote tlb flush requests (Vitaly Kuznetsov) [2009338]
- KVM: Remove unnecessary export of kvm_{inc,dec}_notifier_count() (Vitaly Kuznetsov) [2009338]
- KVM: x86/mmu: Move lpage_disallowed_link further "down" in kvm_mmu_page (Vitaly Kuznetsov) [2009338]
- KVM: x86/mmu: Relocate kvm_mmu_page.tdp_mmu_page for better cache locality (Vitaly Kuznetsov) [2009338]
- Revert "KVM: x86: mmu: Add guest physical address check in translate_gpa()" (Vitaly Kuznetsov) [2009338]
- KVM: x86/mmu: Remove unused field mmio_cached in struct kvm_mmu_page (Vitaly Kuznetsov) [2009338]
- kvm: x86: Increase KVM_SOFT_MAX_VCPUS to 710 (Vitaly Kuznetsov) [2009338]
- kvm: x86: Increase MAX_VCPUS to 1024 (Vitaly Kuznetsov) [2009338]
- kvm: x86: Set KVM_MAX_VCPU_ID to 4*KVM_MAX_VCPUS (Vitaly Kuznetsov) [2009338]
- KVM: VMX: avoid running vmx_handle_exit_irqoff in case of emulation (Vitaly Kuznetsov) [2009338]
- KVM: x86/mmu: Don't freak out if pml5_root is NULL on 4-level host (Vitaly Kuznetsov) [2009338]
- KVM: SVM: Add 5-level page table support for SVM (Vitaly Kuznetsov) [2009338]
- KVM: x86/mmu: Support shadowing NPT when 5-level paging is enabled in host (Vitaly Kuznetsov) [2009338]
- KVM: x86: Allow CPU to force vendor-specific TDP level (Vitaly Kuznetsov) [2009338]
- KVM: x86: clamp host mapping level to max_level in kvm_mmu_max_mapping_level (Vitaly Kuznetsov) [2009338]
- KVM: x86: implement KVM_GUESTDBG_BLOCKIRQ (Vitaly Kuznetsov) [2009338]
- KVM: SVM: split svm_handle_invalid_exit (Vitaly Kuznetsov) [2009338]
- KVM: x86/mmu: Drop 'shared' param from tdp_mmu_link_page() (Vitaly Kuznetsov) [2009338]
- KVM: x86/mmu: Add detailed page size stats (Vitaly Kuznetsov) [2009338]
- KVM: x86/mmu: Avoid collision with !PRESENT SPTEs in TDP MMU lpage stats (Vitaly Kuznetsov) [2009338]
- KVM: x86/mmu: Remove redundant spte present check in mmu_set_spte (Vitaly Kuznetsov) [2009338]
- KVM: stats: Add halt polling related histogram stats (Vitaly Kuznetsov) [2009338]
- KVM: stats: Add halt_wait_ns stats for all architectures (Vitaly Kuznetsov) [2009338]
- KVM: selftests: Add checks for histogram stats bucket_size field (Vitaly Kuznetsov) [2009338]
- KVM: stats: Update doc for histogram statistics (Vitaly Kuznetsov) [2009338]
- KVM: stats: Support linear and logarithmic histogram statistics (Vitaly Kuznetsov) [2009338]
- KVM: SVM: AVIC: drop unsupported AVIC base relocation code (Vitaly Kuznetsov) [2009338]
- KVM: SVM: call avic_vcpu_load/avic_vcpu_put when enabling/disabling AVIC (Vitaly Kuznetsov) [2009338]
- KVM: SVM: move check for kvm_vcpu_apicv_active outside of avic_vcpu_{put|load} (Vitaly Kuznetsov) [2009338]
- KVM: SVM: avoid refreshing avic if its state didn't change (Vitaly Kuznetsov) [2009338]
- KVM: SVM: remove svm_toggle_avic_for_irq_window (Vitaly Kuznetsov) [2009338]
- KVM: x86: hyper-v: Deactivate APICv only when AutoEOI feature is in use (Vitaly Kuznetsov) [2009338]
- KVM: SVM: add warning for mistmatch between AVIC vcpu state and AVIC inhibition (Vitaly Kuznetsov) [2009338]
- KVM: x86: APICv: fix race in kvm_request_apicv_update on SVM (Vitaly Kuznetsov) [2009338]
- KVM: x86: don't disable APICv memslot when inhibited (Vitaly Kuznetsov) [2009338]
- KVM: x86/mmu: allow APICv memslot to be enabled but invisible (Vitaly Kuznetsov) [2009338]
- KVM: x86/mmu: allow kvm_faultin_pfn to return page fault handling code (Vitaly Kuznetsov) [2009338]
- KVM: x86/mmu: rename try_async_pf to kvm_faultin_pfn (Vitaly Kuznetsov) [2009338]
- KVM: x86/mmu: bump mmu notifier count in kvm_zap_gfn_range (Vitaly Kuznetsov) [2009338]
- KVM: x86/mmu: add comment explaining arguments to kvm_zap_gfn_range (Vitaly Kuznetsov) [2009338]
- KVM: x86/mmu: fix parameters to kvm_flush_remote_tlbs_with_address (Vitaly Kuznetsov) [2009338]
- Revert "KVM: x86/mmu: Allow zap gfn range to operate under the mmu read lock" (Vitaly Kuznetsov) [2009338]
- KVM: X86: Introduce mmu_rmaps_stat per-vm debugfs file (Vitaly Kuznetsov) [2009338]
- KVM: X86: Introduce kvm_mmu_slot_lpages() helpers (Vitaly Kuznetsov) [2009338]
- KVM: Allow to have arch-specific per-vm debugfs files (Vitaly Kuznetsov) [2009338]
- KVM: nVMX: Unconditionally clear nested.pi_pending on nested VM-Enter (Vitaly Kuznetsov) [2009338]
- KVM: x86: Clean up redundant ROL16(val, n) macro definition (Vitaly Kuznetsov) [2009338]
- KVM: x86: Move declaration of kvm_spurious_fault() to x86.h (Vitaly Kuznetsov) [2009338]
- KVM: x86: Kill off __ex() and __kvm_handle_fault_on_reboot() (Vitaly Kuznetsov) [2009338]
- KVM: VMX: Hide VMCS control calculators in vmx.c (Vitaly Kuznetsov) [2009338]
- KVM: VMX: Drop caching of KVM's desired sec exec controls for vmcs01 (Vitaly Kuznetsov) [2009338]
- KVM: nVMX: Pull KVM L0's desired controls directly from vmcs01 (Vitaly Kuznetsov) [2009338]
- KVM: stats: remove dead stores (Vitaly Kuznetsov) [2009338]
- KVM: VMX: Reset DR6 only when KVM_DEBUGREG_WONT_EXIT (Vitaly Kuznetsov) [2009338]
- KVM: X86: Set host DR6 only on VMX and for KVM_DEBUGREG_WONT_EXIT (Vitaly Kuznetsov) [2009338]
- KVM: X86: Remove unneeded KVM_DEBUGREG_RELOAD (Vitaly Kuznetsov) [2009338]
- x86: Fix typo s/ECLR/ELCR/ for the PIC register (Vitaly Kuznetsov) [2009338]
- KVM: selftests: Move vcpu_args_set into perf_test_util (Vitaly Kuznetsov) [2009338]
- KVM: selftests: Support multiple slots in dirty_log_perf_test (Vitaly Kuznetsov) [2009338]
- KVM: x86/mmu: Rename __gfn_to_rmap to gfn_to_rmap (Vitaly Kuznetsov) [2009338]
- KVM: x86/mmu: Leverage vcpu->last_used_slot for rmap_add and rmap_recycle (Vitaly Kuznetsov) [2009338]
- KVM: x86/mmu: Leverage vcpu->last_used_slot in tdp_mmu_map_handle_target_level (Vitaly Kuznetsov) [2009338]
- KVM: Cache the last used slot index per vCPU (Vitaly Kuznetsov) [2009338]
- KVM: Move last_used_slot logic out of search_memslots (Vitaly Kuznetsov) [2009338]
- KVM: xen: do not use struct gfn_to_hva_cache (Vitaly Kuznetsov) [2009338]
- KVM: x86/pmu: Introduce pmc->is_paused to reduce the call time of perf interfaces (Vitaly Kuznetsov) [2009338]
- KVM: X86: Optimize zapping rmap (Vitaly Kuznetsov) [2009338]
- KVM: X86: Optimize pte_list_desc with per-array counter (Vitaly Kuznetsov) [2009338]
- KVM: X86: MMU: Tune PTE_LIST_EXT to be bigger (Vitaly Kuznetsov) [2009338]
- KVM: const-ify all relevant uses of struct kvm_memory_slot (Vitaly Kuznetsov) [2009338]
- KVM: Don't take mmu_lock for range invalidation unless necessary (Vitaly Kuznetsov) [2009338]
- KVM: Block memslot updates across range_start() and range_end() (Vitaly Kuznetsov) [2009338]
- KVM: nSVM: remove useless kvm_clear_*_queue (Vitaly Kuznetsov) [2009338]
- KVM: x86: Preserve guest's CR0.CD/NW on INIT (Vitaly Kuznetsov) [2009338]
- KVM: SVM: Drop redundant clearing of vcpu->arch.hflags at INIT/RESET (Vitaly Kuznetsov) [2009338]
- KVM: SVM: Emulate #INIT in response to triple fault shutdown (Vitaly Kuznetsov) [2009338]
- KVM: VMX: Move RESET-only VMWRITE sequences to init_vmcs() (Vitaly Kuznetsov) [2009338]
- KVM: VMX: Remove redundant write to set vCPU as active at RESET/INIT (Vitaly Kuznetsov) [2009338]
- KVM: VMX: Smush x2APIC MSR bitmap adjustments into single function (Vitaly Kuznetsov) [2009338]
- KVM: VMX: Remove unnecessary initialization of msr_bitmap_mode (Vitaly Kuznetsov) [2009338]
- KVM: VMX: Don't redo x2APIC MSR bitmaps when userspace filter is changed (Vitaly Kuznetsov) [2009338]
- KVM: nVMX: Remove obsolete MSR bitmap refresh at nested transitions (Vitaly Kuznetsov) [2009338]
- KVM: VMX: Remove obsolete MSR bitmap refresh at vCPU RESET/INIT (Vitaly Kuznetsov) [2009338]
- KVM: x86: Move setting of sregs during vCPU RESET/INIT to common x86 (Vitaly Kuznetsov) [2009338]
- KVM: VMX: Don't _explicitly_ reconfigure user return MSRs on vCPU INIT (Vitaly Kuznetsov) [2009338]
- KVM: VMX: Refresh list of user return MSRs after setting guest CPUID (Vitaly Kuznetsov) [2009338]
- KVM: VMX: Skip pointless MSR bitmap update when setting EFER (Vitaly Kuznetsov) [2009338]
- KVM: SVM: Stuff save->dr6 at during VMSA sync, not at RESET/INIT (Vitaly Kuznetsov) [2009338]
- KVM: SVM: Drop redundant writes to vmcb->save.cr4 at RESET/INIT (Vitaly Kuznetsov) [2009338]
- KVM: SVM: Tweak order of cr0/cr4/efer writes at RESET/INIT (Vitaly Kuznetsov) [2009338]
- KVM: nVMX: Don't evaluate "emulation required" on nested VM-Exit (Vitaly Kuznetsov) [2009338]
- KVM: VMX: Skip emulation required checks during pmode/rmode transitions (Vitaly Kuznetsov) [2009338]
- KVM: VMX: Process CR0.PG side effects after setting CR0 assets (Vitaly Kuznetsov) [2009338]
- KVM: x86/mmu: Skip the permission_fault() check on MMIO if CR0.PG=0 (Vitaly Kuznetsov) [2009338]
- KVM: VMX: Pull GUEST_CR3 from the VMCS iff CR3 load exiting is disabled (Vitaly Kuznetsov) [2009338]
- KVM: nVMX: Do not clear CR3 load/store exiting bits if L1 wants 'em (Vitaly Kuznetsov) [2009338]
- KVM: VMX: Fold ept_update_paging_mode_cr0() back into vmx_set_cr0() (Vitaly Kuznetsov) [2009338]
- KVM: VMX: Remove direct write to vcpu->arch.cr0 during vCPU RESET/INIT (Vitaly Kuznetsov) [2009338]
- KVM: VMX: Invert handling of CR0.WP for EPT without unrestricted guest (Vitaly Kuznetsov) [2009338]
- KVM: SVM: Don't bother writing vmcb->save.rip at vCPU RESET/INIT (Vitaly Kuznetsov) [2009338]
- KVM: x86: Move EDX initialization at vCPU RESET to common code (Vitaly Kuznetsov) [2009338]
- KVM: x86: Consolidate APIC base RESET initialization code (Vitaly Kuznetsov) [2009338]
- KVM: x86: Open code necessary bits of kvm_lapic_set_base() at vCPU RESET (Vitaly Kuznetsov) [2009338]
- KVM: VMX: Stuff vcpu->arch.apic_base directly at vCPU RESET (Vitaly Kuznetsov) [2009338]
- KVM: x86: Set BSP bit in reset BSP vCPU's APIC base by default (Vitaly Kuznetsov) [2009338]
- KVM: x86: Don't force set BSP bit when local APIC is managed by userspace (Vitaly Kuznetsov) [2009338]
- KVM: x86: Migrate the PIT only if vcpu0 is migrated, not any BSP (Vitaly Kuznetsov) [2009338]
- KVM: x86: Remove defunct BSP "update" in local APIC reset (Vitaly Kuznetsov) [2009338]
- KVM: x86: WARN if the APIC map is dirty without an in-kernel local APIC (Vitaly Kuznetsov) [2009338]
- KVM: SVM: Drop explicit MMU reset at RESET/INIT (Vitaly Kuznetsov) [2009338]
- KVM: VMX: Remove explicit MMU reset in enter_rmode() (Vitaly Kuznetsov) [2009338]
- KVM: SVM: Fall back to KVM's hardcoded value for EDX at RESET/INIT (Vitaly Kuznetsov) [2009338]
- KVM: SVM: Require exact CPUID.0x1 match when stuffing EDX at INIT (Vitaly Kuznetsov) [2009338]
- KVM: VMX: Set EDX at INIT with CPUID.0x1, Family-Model-Stepping (Vitaly Kuznetsov) [2009338]
- KVM: SVM: Zero out GDTR.base and IDTR.base on INIT (Vitaly Kuznetsov) [2009338]
- KVM: nVMX: Set LDTR to its architecturally defined value on nested VM-Exit (Vitaly Kuznetsov) [2009338]
- KVM: x86: Flush the guest's TLB on INIT (Vitaly Kuznetsov) [2009338]
- KVM: x86: APICv: drop immediate APICv disablement on current vCPU (Vitaly Kuznetsov) [2009338]
- KVM: x86: enable TDP MMU by default (Vitaly Kuznetsov) [2009338]
- KVM: x86/mmu: fast_page_fault support for the TDP MMU (Vitaly Kuznetsov) [2009338]
- KVM: x86/mmu: Make walk_shadow_page_lockless_{begin,end} interoperate with the TDP MMU (Vitaly Kuznetsov) [2009338]
- KVM: x86/mmu: Fix use of enums in trace_fast_page_fault (Vitaly Kuznetsov) [2009338]
- KVM: x86/mmu: Rename cr2_or_gpa to gpa in fast_page_fault (Vitaly Kuznetsov) [2009338]
- KVM: Introduce kvm_get_kvm_safe() (Vitaly Kuznetsov) [2009338]
- x86/kvm: remove non-x86 stuff from arch/x86/kvm/ioapic.h (Vitaly Kuznetsov) [2009338]
- KVM: X86: Add per-vm stat for max rmap list size (Vitaly Kuznetsov) [2009338]
- KVM: x86/mmu: Return old SPTE from mmu_spte_clear_track_bits() (Vitaly Kuznetsov) [2009338]
- KVM: x86/mmu: Refactor shadow walk in __direct_map() to reduce indentation (Vitaly Kuznetsov) [2009338]
- KVM: x86: Hoist kvm_dirty_regs check out of sync_regs() (Vitaly Kuznetsov) [2009338]
- KVM: x86/mmu: Mark VM as bugged if page fault returns RET_PF_INVALID (Vitaly Kuznetsov) [2009338]
- KVM: x86: Use KVM_BUG/KVM_BUG_ON to handle bugs that are fatal to the VM (Vitaly Kuznetsov) [2009338]
- KVM: Export kvm_make_all_cpus_request() for use in marking VMs as bugged (Vitaly Kuznetsov) [2009338]
- KVM: Add infrastructure and macro to mark VM as bugged (Vitaly Kuznetsov) [2009338]
- KVM: Get rid of kvm_get_pfn() (Vitaly Kuznetsov) [2009338]
- KVM: arm64: Use get_page() instead of kvm_get_pfn() (Vitaly Kuznetsov) [2009338]
- docs: kvm: properly format code blocks and lists (Vitaly Kuznetsov) [2009338]
- docs: kvm: fix build warnings (Vitaly Kuznetsov) [2009338]

* Thu Dec 09 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-29.el9]
- posix-cpu-timers: Prevent spuriously armed 0-value itimer (Phil Auld) [2022896]
- hrtimer: Unbreak hrtimer_force_reprogram() (Phil Auld) [2022896]
- hrtimer: Use raw_cpu_ptr() in clock_was_set() (Phil Auld) [2022896]
- clocksource: Make clocksource watchdog test safe for slow-HZ systems (Phil Auld) [2022896]
- posix-cpu-timers: Recalc next expiration when timer_settime() ends up not queueing (Phil Auld) [2022896]
- posix-cpu-timers: Consolidate timer base accessor (Phil Auld) [2022896]
- posix-cpu-timers: Remove confusing return value override (Phil Auld) [2022896]
- posix-cpu-timers: Force next expiration recalc after itimer reset (Phil Auld) [2022896]
- posix-cpu-timers: Force next_expiration recalc after timer deletion (Phil Auld) [2022896]
- posix-cpu-timers: Assert task sighand is locked while starting cputime counter (Phil Auld) [2022896]
- posix-timers: Remove redundant initialization of variable ret (Phil Auld) [2022896]
- hrtimer: Avoid more SMP function calls in clock_was_set() (Phil Auld) [2022896]
- hrtimer: Avoid unnecessary SMP function calls in clock_was_set() (Phil Auld) [2022896]
- hrtimer: Add bases argument to clock_was_set() (Phil Auld) [2022896]
- time/timekeeping: Avoid invoking clock_was_set() twice (Phil Auld) [2022896]
- timekeeping: Distangle resume and clock-was-set events (Phil Auld) [2022896]
- timerfd: Provide timerfd_resume() (Phil Auld) [2022896]
- hrtimer: Force clock_was_set() handling for the HIGHRES=n, NOHZ=y case (Phil Auld) [2022896]
- hrtimer: Ensure timerfd notification for HIGHRES=n (Phil Auld) [2022896]
- hrtimer: Consolidate reprogramming code (Phil Auld) [2022896]
- hrtimer: Avoid double reprogramming in __hrtimer_start_range_ns() (Phil Auld) [2022896]

* Wed Dec 08 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-28.el9]
- rcu: Fix rcu_dynticks_curr_cpu_in_eqs() vs noinstr (Waiman Long) [2022806]
- efi: Change down_interruptible() in virt_efi_reset_system() to down_trylock() (Waiman Long) [2022806]
- Documentation: core-api/cpuhotplug: Rewrite the API section (Waiman Long) [2022806]
- docs/core-api: Modify document layout (Waiman Long) [2022806]
- futex: Avoid redundant task lookup (Waiman Long) [2022806]
- futex: Clarify comment for requeue_pi_wake_futex() (Waiman Long) [2022806]
- cgroup: Avoid compiler warnings with no subsystems (Waiman Long) [2022806]
- media/atomisp: Use lockdep instead of *mutex_is_locked() (Waiman Long) [2022806]
- debugobjects: Make them PREEMPT_RT aware (Waiman Long) [2022806]
- cgroup/cpuset: Enable event notification when partition state changes (Waiman Long) [2022806]
- cgroup: cgroup-v1: clean up kernel-doc notation (Waiman Long) [2022806]
- locking/semaphore: Add might_sleep() to down_*() family (Waiman Long) [2022806]
- static_call: Update API documentation (Waiman Long) [2022806]
- torture: Replace deprecated CPU-hotplug functions. (Waiman Long) [2022806]
- clocksource: Replace deprecated CPU-hotplug functions. (Waiman Long) [2022806]
- smpboot: Replace deprecated CPU-hotplug functions. (Waiman Long) [2022806]
- rcu: Replace deprecated CPU-hotplug functions (Waiman Long) [2022806]
- genirq/affinity: Replace deprecated CPU-hotplug functions. (Waiman Long) [2022806]
- cgroup: Replace deprecated CPU-hotplug functions. (Waiman Long) [2022806]
- mm: Replace deprecated CPU-hotplug functions. (Waiman Long) [2022806]
- thermal: Replace deprecated CPU-hotplug functions. (Waiman Long) [2022806]
- md/raid5: Replace deprecated CPU-hotplug functions. (Waiman Long) [2022806]
- perf/hw_breakpoint: Replace deprecated CPU-hotplug functions (Waiman Long) [2022806]
- perf/x86/intel: Replace deprecated CPU-hotplug functions (Waiman Long) [2022806]
- Documentation: Replace deprecated CPU-hotplug functions. (Waiman Long) [2022806]
- Documentation/atomic_t: Document forward progress expectations (Waiman Long) [2022806]
- eventfd: Make signal recursion protection a task bit (Waiman Long) [2022806]
- locking/atomic: simplify non-atomic wrappers (Waiman Long) [2022806]
- cgroup/cpuset: Fix violation of cpuset locking rule (Waiman Long) [2022806]
- cgroup/cpuset: Fix a partition bug with hotplug (Waiman Long) [2022806]
- cgroup/cpuset: Miscellaneous code cleanup (Waiman Long) [2022806]
- rcu: Mark accesses to rcu_state.n_force_qs (Waiman Long) [2022806]
- rcu: Print human-readable message for schedule() in RCU reader (Waiman Long) [2022806]
- cgroup: remove cgroup_mount from comments (Waiman Long) [2022806]
- doc: Update stallwarn.rst with recent changes (Waiman Long) [2022806]
- locking/atomic: add generic arch_*() bitops (Waiman Long) [2022806]
- locking/atomic: add arch_atomic_long*() (Waiman Long) [2022806]
- locking/atomic: centralize generated headers (Waiman Long) [2022806]
- locking/atomic: remove ARCH_ATOMIC remanants (Waiman Long) [2022806]
- locking/atomic: simplify ifdef generation (Waiman Long) [2022806]
- rcu: Fix macro name CONFIG_TASKS_RCU_TRACE (Waiman Long) [2022806]
- scftorture: Avoid NULL pointer exception on early exit (Waiman Long) [2022806]
- torture: Make kvm-test-1-run-qemu.sh check for reboot loops (Waiman Long) [2022806]
- torture: Add timestamps to kvm-test-1-run-qemu.sh output (Waiman Long) [2022806]
- torture: Don't use "test" command's "-a" argument (Waiman Long) [2022806]
- torture: Make kvm-test-1-run-batch.sh select per-scenario affinity masks (Waiman Long) [2022806]
- torture: Consistently name "qemu*" test output files (Waiman Long) [2022806]
- torture: Use numeric taskset argument in jitter.sh (Waiman Long) [2022806]
- rcutorture: Upgrade two-CPU scenarios to four CPUs (Waiman Long) [2022806]
- torture: Make kvm-test-1-run-qemu.sh apply affinity (Waiman Long) [2022806]
- torture: Don't redirect qemu-cmd comment lines (Waiman Long) [2022806]
- torture: Make kvm.sh select per-scenario affinity masks (Waiman Long) [2022806]
- torture: Put kvm.sh batch-creation awk script into a temp file (Waiman Long) [2022806]
- locking/rwsem: Remove an unused parameter of rwsem_wake() (Waiman Long) [2022806]
- rcu: Explain why rcu_all_qs() is a stub in preemptible TREE RCU (Waiman Long) [2022806]
- Documentation/atomic_t: Document cmpxchg() vs try_cmpxchg() (Waiman Long) [2022806]
- rcu: Use per_cpu_ptr to get the pointer of per_cpu variable (Waiman Long) [2022806]
- rcu: Remove useless "ret" update in rcu_gp_fqs_loop() (Waiman Long) [2022806]
- scftorture: Add RPC-like IPI tests (Waiman Long) [2022806]
- tools/nolibc: Implement msleep() (Waiman Long) [2022806]
- tools: include: nolibc: Fix a typo occured to occurred in the file nolibc.h (Waiman Long) [2022806]
- torture: Move parse-console.sh call to PATH-aware scripts (Waiman Long) [2022806]
- torture: Make kvm-recheck.sh skip kcsan.sum for build-only runs (Waiman Long) [2022806]
- rcu-tasks: Fix synchronize_rcu_rude() typo in comment (Waiman Long) [2022806]
- rcuscale: Console output claims too few grace periods (Waiman Long) [2022806]
- torture: Protect kvm-remote.sh directory trees from /tmp reaping (Waiman Long) [2022806]
- torture: Log more kvm-remote.sh information (Waiman Long) [2022806]
- torture: Make kvm-recheck-lock.sh tolerate qemu-cmd comments (Waiman Long) [2022806]
- torture: Make kvm-recheck-scf.sh tolerate qemu-cmd comments (Waiman Long) [2022806]
- rcu/doc: Add a quick quiz to explain further why we need smp_mb__after_unlock_lock() (Waiman Long) [2022806]
- rcu: Make rcu_gp_init() and rcu_gp_fqs_loop noinline to conserve stack (Waiman Long) [2022806]
- torture: Create KCSAN summaries for torture.sh runs (Waiman Long) [2022806]
- torture: Enable KCSAN summaries over groups of torture-test runs (Waiman Long) [2022806]
- rcu: Mark lockless ->qsmask read in rcu_check_boost_fail() (Waiman Long) [2022806]
- srcutiny: Mark read-side data races (Waiman Long) [2022806]
- locktorture: Count lock readers (Waiman Long) [2022806]
- locktorture: Mark statistics data races (Waiman Long) [2022806]
- docs: Fix a typo in Documentation/RCU/stallwarn.rst (Waiman Long) [2022806]
- rcu-tasks: Mark ->trc_reader_special.b.need_qs data races (Waiman Long) [2022806]
- rcu-tasks: Mark ->trc_reader_nesting data races (Waiman Long) [2022806]
- rcu-tasks: Add comments explaining task_struct strategy (Waiman Long) [2022806]
- rcu: Start timing stall repetitions after warning complete (Waiman Long) [2022806]
- rcu: Do not disable GP stall detection in rcu_cpu_stall_reset() (Waiman Long) [2022806]
- rcu/tree: Handle VM stoppage in stall detection (Waiman Long) [2022806]
- rculist: Unify documentation about missing list_empty_rcu() (Waiman Long) [2022806]
- rcu: Mark accesses in tree_stall.h (Waiman Long) [2022806]
- Documentation/RCU: Fix nested inline markup (Waiman Long) [2022806]
- rcu: Mark accesses to ->rcu_read_lock_nesting (Waiman Long) [2022806]
- Documentation/RCU: Fix emphasis markers (Waiman Long) [2022806]
- rcu: Weaken ->dynticks accesses and updates (Waiman Long) [2022806]
- rcu: Remove special bit at the bottom of the ->dynticks counter (Waiman Long) [2022806]
- rcu/nocb: Remove NOCB deferred wakeup from rcutree_dead_cpu() (Waiman Long) [2022806]
- rcu/nocb: Start moving nocb code to its own plugin file (Waiman Long) [2022806]
- rcutorture: Preempt rather than block when testing task stalls (Waiman Long) [2022806]
- rcu: Fix stall-warning deadlock due to non-release of rcu_node ->lock (Waiman Long) [2022806]
- rcu: Fix to include first blocked task in stall warning (Waiman Long) [2022806]
- torture: Make torture.sh accept --do-all and --donone (Waiman Long) [2022806]
- torture: Add clocksource-watchdog testing to torture.sh (Waiman Long) [2022806]
- refscale: Add measurement of clock readout (Waiman Long) [2022806]

* Tue Dec 07 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-27.el9]
- x86: change default to spec_store_bypass_disable=prctl spectre_v2_user=prctl (Wander Lairson Costa) [2002637]
- Enable PREEMPT_DYNAMIC for all but s390x (Phil Auld) [2019472]
- preempt: Restore preemption model selection configs (Phil Auld) [2019472]
- sched: Provide Kconfig support for default dynamic preempt mode (Phil Auld) [2019472]
- x86/sgx: Add TAINT_TECH_PREVIEW for virtual EPC (Wander Lairson Costa) [2025959]
- x86/sgx: mark tech preview (Wander Lairson Costa) [2025959]
- ipv6: When forwarding count rx stats on the orig netdev (Hangbin Liu) [2025457]
- ipv6: make exception cache less predictible (Hangbin Liu) [2025457]
- icmp: fix icmp_ext_echo_iio parsing in icmp_build_probe (Guillaume Nault) [2024572]
- net: prefer socket bound to interface when not in VRF (Guillaume Nault) [2024572]
- net: ipv4: Fix rtnexthop len when RTA_FLOW is present (Guillaume Nault) [2024572]
- nexthop: Fix memory leaks in nexthop notification chain listeners (Guillaume Nault) [2024572]
- nexthop: Fix division by zero while replacing a resilient group (Guillaume Nault) [2024572]
- ipv4: fix endianness issue in inet_rtm_getroute_build_skb() (Guillaume Nault) [2024572]
- crypto: ccp - Make use of the helper macro kthread_run() (Vladis Dronov) [1997595]
- crypto: ccp - Fix whitespace in sev_cmd_buffer_len() (Vladis Dronov) [1997595]
- crypto: ccp - fix resource leaks in ccp_run_aes_gcm_cmd() (Vladis Dronov) [1997595] {CVE-2021-3744 CVE-2021-3764}
- net/l2tp: Fix reference count leak in l2tp_udp_recv_core (Guillaume Nault) [2023271]
- scsi: megaraid: Clean up some inconsistent indenting (Tomas Henzl) [1879402]
- scsi: megaraid: Fix Coccinelle warning (Tomas Henzl) [1879402]
- scsi: megaraid_sas: Driver version update to 07.719.03.00-rc1 (Tomas Henzl) [1879402]
- scsi: megaraid_sas: Add helper functions for irq_context (Tomas Henzl) [1879402]
- scsi: megaraid_sas: Fix concurrent access to ISR between IRQ polling and real interrupt (Tomas Henzl) [1879402]
- tpm: ibmvtpm: Avoid error message when process gets signal while waiting (Štěpán Horáček) [1983089]
- char: tpm: cr50_i2c: convert to new probe interface (Štěpán Horáček) [1983089]
- char: tpm: Kconfig: remove bad i2c cr50 select (Štěpán Horáček) [1983089]

* Mon Dec 06 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-26.el9]
- redhat/configs: enable CONFIG_CEPH_FSCACHE (Jeffrey Layton) [2017798]
- ceph: add a new metric to keep track of remote object copies (Jeffrey Layton) [2017798]
- libceph, ceph: move ceph_osdc_copy_from() into cephfs code (Jeffrey Layton) [2017798]
- ceph: clean-up metrics data structures to reduce code duplication (Jeffrey Layton) [2017798]
- ceph: split 'metric' debugfs file into several files (Jeffrey Layton) [2017798]
- ceph: return the real size read when it hits EOF (Jeffrey Layton) [2017798]
- ceph: properly handle statfs on multifs setups (Jeffrey Layton) [2017798]
- ceph: shut down mount on bad mdsmap or fsmap decode (Jeffrey Layton) [2017798]
- ceph: fix mdsmap decode when there are MDS's beyond max_mds (Jeffrey Layton) [2017798]
- ceph: ignore the truncate when size won't change with Fx caps issued (Jeffrey Layton) [2017798]
- ceph: don't rely on error_string to validate blocklisted session. (Jeffrey Layton) [2017798]
- ceph: just use ci->i_version for fscache aux info (Jeffrey Layton) [2017798]
- ceph: shut down access to inode when async create fails (Jeffrey Layton) [2017798]
- ceph: refactor remove_session_caps_cb (Jeffrey Layton) [2017798]
- ceph: fix auth cap handling logic in remove_session_caps_cb (Jeffrey Layton) [2017798]
- ceph: drop private list from remove_session_caps_cb (Jeffrey Layton) [2017798]
- ceph: don't use -ESTALE as special return code in try_get_cap_refs (Jeffrey Layton) [2017798]
- ceph: print inode numbers instead of pointer values (Jeffrey Layton) [2017798]
- ceph: enable async dirops by default (Jeffrey Layton) [2017798]
- libceph: drop ->monmap and err initialization (Jeffrey Layton) [2017798]
- ceph: convert to noop_direct_IO (Jeffrey Layton) [2017798]
- ceph: fix handling of "meta" errors (Jeffrey Layton) [2017798]
- ceph: skip existing superblocks that are blocklisted or shut down when mounting (Jeffrey Layton) [2017798]
- ceph: fix off by one bugs in unsafe_request_wait() (Jeffrey Layton) [2017798]
- ceph: fix dereference of null pointer cf (Jeffrey Layton) [2017798]
- ceph: drop the mdsc_get_session/put_session dout messages (Jeffrey Layton) [2017798]
- ceph: lockdep annotations for try_nonblocking_invalidate (Jeffrey Layton) [2017798]
- ceph: don't WARN if we're forcibly removing the session caps (Jeffrey Layton) [2017798]
- ceph: don't WARN if we're force umounting (Jeffrey Layton) [2017798]
- ceph: remove the capsnaps when removing caps (Jeffrey Layton) [2017798]
- ceph: request Fw caps before updating the mtime in ceph_write_iter (Jeffrey Layton) [2017798]
- ceph: reconnect to the export targets on new mdsmaps (Jeffrey Layton) [2017798]
- ceph: print more information when we can't find snaprealm (Jeffrey Layton) [2017798]
- ceph: add ceph_change_snap_realm() helper (Jeffrey Layton) [2017798]
- ceph: remove redundant initializations from mdsc and session (Jeffrey Layton) [2017798]
- ceph: cancel delayed work instead of flushing on mdsc teardown (Jeffrey Layton) [2017798]
- ceph: add a new vxattr to return auth mds for an inode (Jeffrey Layton) [2017798]
- ceph: remove some defunct forward declarations (Jeffrey Layton) [2017798]
- ceph: flush the mdlog before waiting on unsafe reqs (Jeffrey Layton) [2017798]
- ceph: flush mdlog before umounting (Jeffrey Layton) [2017798]
- ceph: make iterate_sessions a global symbol (Jeffrey Layton) [2017798]
- ceph: make ceph_create_session_msg a global symbol (Jeffrey Layton) [2017798]
- ceph: fix comment about short copies in ceph_write_end (Jeffrey Layton) [2017798]
- ceph: fix memory leak on decode error in ceph_handle_caps (Jeffrey Layton) [2017798]

* Fri Dec 03 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-25.el9]
- x86: Pin task-stack in __get_wchan() (Chris von Recklinghausen) [2022169]
- x86: Fix __get_wchan() for !STACKTRACE (Chris von Recklinghausen) [2022169]
- sched: Add wrapper for get_wchan() to keep task blocked (Chris von Recklinghausen) [2022169]
- x86: Fix get_wchan() to support the ORC unwinder (Chris von Recklinghausen) [2022169]
- proc: Use task_is_running() for wchan in /proc/$pid/stat (Chris von Recklinghausen) [2022169]
- leaking_addresses: Always print a trailing newline (Chris von Recklinghausen) [2022169]
- Revert "proc/wchan: use printk format instead of lookup_symbol_name()" (Chris von Recklinghausen) [2022169]
- sched: Fill unconditional hole induced by sched_entity (Chris von Recklinghausen) [2022169]
- powerpc/bpf: Fix write protecting JIT code (Jiri Olsa) [2023618]
- vfs: check fd has read access in kernel_read_file_from_fd() (Carlos Maiolino) [2022893]
- Disable idmapped mounts (Alexey Gladkov) [2018141]
- KVM: s390: Fix handle_sske page fault handling (Thomas Huth) [1870686]
- KVM: s390: Simplify SIGP Set Arch handling (Thomas Huth) [1870686]
- KVM: s390: pv: avoid stalls when making pages secure (Thomas Huth) [1870686]
- KVM: s390: pv: avoid stalls for kvm_s390_pv_init_vm (Thomas Huth) [1870686]
- KVM: s390: pv: avoid double free of sida page (Thomas Huth) [1870686]
- KVM: s390: pv: add macros for UVC CC values (Thomas Huth) [1870686]
- s390/uv: fully validate the VMA before calling follow_page() (Thomas Huth) [1870686]
- s390/gmap: don't unconditionally call pte_unmap_unlock() in __gmap_zap() (Thomas Huth) [1870686]
- s390/gmap: validate VMA in __gmap_zap() (Thomas Huth) [1870686]
- KVM: s390: preserve deliverable_mask in __airqs_kick_single_vcpu (Thomas Huth) [1870686]
- KVM: s390: index kvm->arch.idle_mask by vcpu_idx (Thomas Huth) [1870686]
- KVM: s390: clear kicked_mask before sleeping again (Thomas Huth) [1870686]
- KVM: s390: Function documentation fixes (Thomas Huth) [1870686]
- s390/mm: fix kernel doc comments (Thomas Huth) [1870686]
- KVM: s390: generate kvm hypercall functions (Thomas Huth) [1870686]
- s390/vfio-ap: replace open coded locks for VFIO_GROUP_NOTIFY_SET_KVM notification (Thomas Huth) [1870686]
- s390/vfio-ap: r/w lock for PQAP interception handler function pointer (Thomas Huth) [1870686]
- KVM: Rename lru_slot to last_used_slot (Thomas Huth) [1870686]
- s390/uv: de-duplicate checks for Protected Host Virtualization (Thomas Huth) [1870686]
- s390/boot: disable Secure Execution in dump mode (Thomas Huth) [1870686]
- s390/boot: move uv function declarations to boot/uv.h (Thomas Huth) [1870686]
- s390/boot: move all linker symbol declarations from c to h files (Thomas Huth) [1870686]
- redhat/configs: Remove CONFIG_INFINIBAND_I40IW (Kamal Heib) [1920720]

* Wed Dec 01 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-24.el9]
- perf test: Handle fd gaps in test__dso_data_reopen (Michael Petlan) [1937209]
- perf tests vmlinux-kallsyms: Ignore hidden symbols (Michael Petlan) [1975103]
- perf script: Fix PERF_SAMPLE_WEIGHT_STRUCT support (Michael Petlan) [2009378]
- redhat/kernel.spec.template: Link perf with --export-dynamic (Michael Petlan) [2006775]
- xfs: fix I_DONTCACHE (Carlos Maiolino) [2022435]
- virtio: write back F_VERSION_1 before validate (Thomas Huth) [2008401]
- net/tls: Fix flipped sign in tls_err_abort() calls (Sabrina Dubroca) [2022006]
- net/tls: Fix flipped sign in async_wait.err assignment (Sabrina Dubroca) [2022006]
- hyper-v: Replace uuid.h with types.h (Mohammed Gamal) [2008572]
- Drivers: hv: vmbus: Remove unused code to check for subchannels (Mohammed Gamal) [2008572]
- hv: hyperv.h: Remove unused inline functions (Mohammed Gamal) [2008572]
- asm-generic/hyperv: provide cpumask_to_vpset_noself (Mohammed Gamal) [2008572]
- asm-generic/hyperv: Add missing #include of nmi.h (Mohammed Gamal) [2008572]
- x86/hyperv: Avoid erroneously sending IPI to 'self' (Mohammed Gamal) [2008572]
- x86/hyperv: remove on-stack cpumask from hv_send_ipi_mask_allbutself (Mohammed Gamal) [2008572]
- [s390] net/smc: improved fix wait on already cleared link (Mete Durlu) [1869652]
- [s390] net/smc: fix 'workqueue leaked lock' in smc_conn_abort_work (Mete Durlu) [1869652]
- [s390] net/smc: add missing error check in smc_clc_prfx_set() (Mete Durlu) [1869652]
- cifs: enable SMB_DIRECT in RHEL9 (Ronnie Sahlberg) [1965209]
- scsi: mpt3sas: Clean up some inconsistent indenting (Tomas Henzl) [1876119]
- scsi: mpt3sas: Call cpu_relax() before calling udelay() (Tomas Henzl) [1876119]
- scsi: mpt3sas: Introduce sas_ncq_prio_supported sysfs sttribute (Tomas Henzl) [1876119]
- scsi: mpt3sas: Update driver version to 39.100.00.00 (Tomas Henzl) [1876119]
- scsi: mpt3sas: Use firmware recommended queue depth (Tomas Henzl) [1876119]
- scsi: mpt3sas: Bump driver version to 38.100.00.00 (Tomas Henzl) [1876119]
- scsi: mpt3sas: Add io_uring iopoll support (Tomas Henzl) [1876119]
- serial: 8250_lpss: Extract dw8250_do_set_termios() for common use (David Arcari) [1880032]
- serial: 8250_lpss: Enable DMA on Intel Elkhart Lake (David Arcari) [1880032]
- dmaengine: dw: Convert members to u32 in platform data (David Arcari) [1880032]
- dmaengine: dw: Simplify DT property parser (David Arcari) [1880032]
- dmaengine: dw: Remove error message from DT parsing code (David Arcari) [1880032]
- dmaengine: dw: Program xBAR hardware for Elkhart Lake (David Arcari) [1880032]
- vmxnet3: switch from 'pci_' to 'dma_' API (Kamal Heib) [2003297]
- vmxnet3: update to version 6 (Kamal Heib) [2003297]
- vmxnet3: increase maximum configurable mtu to 9190 (Kamal Heib) [2003297]
- vmxnet3: set correct hash type based on rss information (Kamal Heib) [2003297]
- vmxnet3: add support for ESP IPv6 RSS (Kamal Heib) [2003297]
- vmxnet3: remove power of 2 limitation on the queues (Kamal Heib) [2003297]
- vmxnet3: add support for 32 Tx/Rx queues (Kamal Heib) [2003297]
- vmxnet3: prepare for version 6 changes (Kamal Heib) [2003297]

* Mon Nov 29 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-23.el9]
- PCI/VPD: Defer VPD sizing until first access (Myron Stowe) [2021298]
- PCI/VPD: Use unaligned access helpers (Myron Stowe) [2021298]
- PCI/VPD: Clean up public VPD defines and inline functions (Myron Stowe) [2021298]
- cxgb4: Use pci_vpd_find_id_string() to find VPD ID string (Myron Stowe) [2021298]
- PCI/VPD: Add pci_vpd_find_id_string() (Myron Stowe) [2021298]
- PCI/VPD: Include post-processing in pci_vpd_find_tag() (Myron Stowe) [2021298]
- PCI/VPD: Stop exporting pci_vpd_find_info_keyword() (Myron Stowe) [2021298]
- PCI/VPD: Stop exporting pci_vpd_find_tag() (Myron Stowe) [2021298]
- scsi: cxlflash: Search VPD with pci_vpd_find_ro_info_keyword() (Myron Stowe) [2021298]
- cxgb4: Search VPD with pci_vpd_find_ro_info_keyword() (Myron Stowe) [2021298]
- cxgb4: Remove unused vpd_param member ec (Myron Stowe) [2021298]
- cxgb4: Validate VPD checksum with pci_vpd_check_csum() (Myron Stowe) [2021298]
- bnxt: Search VPD with pci_vpd_find_ro_info_keyword() (Myron Stowe) [2021298]
- bnxt: Read VPD with pci_vpd_alloc() (Myron Stowe) [2021298]
- bnx2x: Search VPD with pci_vpd_find_ro_info_keyword() (Myron Stowe) [2021298]
- bnx2x: Read VPD with pci_vpd_alloc() (Myron Stowe) [2021298]
- bnx2: Replace open-coded byte swapping with swab32s() (Myron Stowe) [2021298]
- bnx2: Search VPD with pci_vpd_find_ro_info_keyword() (Myron Stowe) [2021298]
- sfc: falcon: Search VPD with pci_vpd_find_ro_info_keyword() (Myron Stowe) [2021298]
- sfc: falcon: Read VPD with pci_vpd_alloc() (Myron Stowe) [2021298]
- tg3: Search VPD with pci_vpd_find_ro_info_keyword() (Myron Stowe) [2021298]
- tg3: Validate VPD checksum with pci_vpd_check_csum() (Myron Stowe) [2021298]
- tg3: Read VPD with pci_vpd_alloc() (Myron Stowe) [2021298]
- sfc: Search VPD with pci_vpd_find_ro_info_keyword() (Myron Stowe) [2021298]
- sfc: Read VPD with pci_vpd_alloc() (Myron Stowe) [2021298]
- PCI/VPD: Add pci_vpd_check_csum() (Myron Stowe) [2021298]
- PCI/VPD: Add pci_vpd_find_ro_info_keyword() (Myron Stowe) [2021298]
- PCI/VPD: Add pci_vpd_alloc() (Myron Stowe) [2021298]
- PCI/VPD: Treat invalid VPD like missing VPD capability (Myron Stowe) [2021298]
- PCI/VPD: Determine VPD size in pci_vpd_init() (Myron Stowe) [2021298]
- PCI/VPD: Embed struct pci_vpd in struct pci_dev (Myron Stowe) [2021298]
- PCI/VPD: Remove struct pci_vpd.valid member (Myron Stowe) [2021298]
- PCI/VPD: Remove struct pci_vpd_ops (Myron Stowe) [2021298]
- PCI/VPD: Reorder pci_read_vpd(), pci_write_vpd() (Myron Stowe) [2021298]
- PCI/VPD: Remove struct pci_vpd.flag (Myron Stowe) [2021298]
- PCI/VPD: Make pci_vpd_wait() uninterruptible (Myron Stowe) [2021298]
- PCI/VPD: Remove pci_vpd_size() old_size argument (Myron Stowe) [2021298]
- PCI/VPD: Allow access to valid parts of VPD if some is invalid (Myron Stowe) [2021298]
- PCI/VPD: Don't check Large Resource Item Names for validity (Myron Stowe) [2021298]
- PCI/VPD: Reject resource tags with invalid size (Myron Stowe) [2021298]
- PCI/VPD: Treat initial 0xff as missing EEPROM (Myron Stowe) [2021298]
- PCI/VPD: Check Resource Item Names against those valid for type (Myron Stowe) [2021298]
- PCI/VPD: Correct diagnostic for VPD read failure (Myron Stowe) [2021298]

* Fri Nov 26 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-22.el9]
- Add automotive CI jobs (Michael Hofmann)
- sched/scs: Reset the shadow stack when idle_task_exit (Phil Auld) [1992256]
- sched/fair: Null terminate buffer when updating tunable_scaling (Phil Auld) [1992256]
- sched/fair: Add ancestors of unthrottled undecayed cfs_rq (Phil Auld) [1981743 1992256]
- cpufreq: schedutil: Destroy mutex before kobject_put() frees the memory (Phil Auld) [1992256]
- sched/idle: Make the idle timer expire in hard interrupt context (Phil Auld) [1992256]
- sched: Prevent balance_push() on remote runqueues (Phil Auld) [1992256]
- sched/fair: Mark tg_is_idle() an inline in the !CONFIG_FAIR_GROUP_SCHED case (Phil Auld) [1992256]
- sched/topology: Skip updating masks for non-online nodes (Phil Auld) [1992256]
- sched: Skip priority checks with SCHED_FLAG_KEEP_PARAMS (Phil Auld) [1992256]
- sched: Fix UCLAMP_FLAG_IDLE setting (Phil Auld) [1992256]
- cpufreq: schedutil: Use kobject release() method to free sugov_tunables (Phil Auld) [1992256]
- sched/deadline: Fix missing clock update in migrate_task_rq_dl() (Phil Auld) [1992256]
- sched/fair: Avoid a second scan of target in select_idle_cpu (Phil Auld) [1992256]
- sched/fair: Use prev instead of new target as recent_used_cpu (Phil Auld) [1992256]
- sched: Replace deprecated CPU-hotplug functions. (Phil Auld) [1992256]
- sched: Introduce dl_task_check_affinity() to check proposed affinity (Phil Auld) [1992256]
- sched: Allow task CPU affinity to be restricted on asymmetric systems (Phil Auld) [1992256]
- sched: Split the guts of sched_setaffinity() into a helper function (Phil Auld) [1992256]
- sched: Introduce task_struct::user_cpus_ptr to track requested affinity (Phil Auld) [1992256]
- sched: Reject CPU affinity changes based on task_cpu_possible_mask() (Phil Auld) [1992256]
- cpuset: Cleanup cpuset_cpus_allowed_fallback() use in select_fallback_rq() (Phil Auld) [1992256]
- cpuset: Honour task_cpu_possible_mask() in guarantee_online_cpus() (Phil Auld) [1992256]
- cpuset: Don't use the cpu_possible_mask as a last resort for cgroup v1 (Phil Auld) [1992256]
- sched: Introduce task_cpu_possible_mask() to limit fallback rq selection (Phil Auld) [1992256]
- sched: Cgroup SCHED_IDLE support (Phil Auld) [1992256]
- sched: Don't report SCHED_FLAG_SUGOV in sched_getattr() (Phil Auld) [1992256]
- sched/deadline: Fix reset_on_fork reporting of DL tasks (Phil Auld) [1992256]
- sched/numa: Fix is_core_idle() (Phil Auld) [1992256]
- sched: remove redundant on_rq status change (Phil Auld) [1992256]
- sched: Optimize housekeeping_cpumask() in for_each_cpu_and() (Phil Auld) [1992256]
- sched/sysctl: Move extern sysctl declarations to sched.h (Phil Auld) [1992256]
- sched/debug: Don't update sched_domain debug directories before sched_debug_init() (Phil Auld) [1992256]

* Thu Nov 25 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-21.el9]
- clocksource: Increase WATCHDOG_MAX_SKEW (Waiman Long) [2017164]
- x86/hpet: Use another crystalball to evaluate HPET usability (Waiman Long) [2017164]
- scsi: target: Fix the pgr/alua_support_store functions (Maurizio Lombardi) [2023439]
- redhat: fix typo and make the output more silent for dist-git sync (Herton R. Krzesinski)
- x86: ACPI: cstate: Optimize C3 entry on AMD CPUs (David Arcari) [1998526]
- scsi: lpfc: Update lpfc version to 14.0.0.3 (Dick Kennedy) [2021327]
- scsi: lpfc: Allow fabric node recovery if recovery is in progress before devloss (Dick Kennedy) [2021327]
- scsi: lpfc: Fix link down processing to address NULL pointer dereference (Dick Kennedy) [2021327]
- scsi: lpfc: Allow PLOGI retry if previous PLOGI was aborted (Dick Kennedy) [2021327]
- scsi: lpfc: Fix use-after-free in lpfc_unreg_rpi() routine (Dick Kennedy) [2021327]
- scsi: lpfc: Correct sysfs reporting of loop support after SFP status change (Dick Kennedy) [2021327]
- scsi: lpfc: Wait for successful restart of SLI3 adapter during host sg_reset (Dick Kennedy) [2021327]
- scsi: lpfc: Revert LOG_TRACE_EVENT back to LOG_INIT prior to driver_resource_setup() (Dick Kennedy) [2021327]
- x86/Kconfig: Do not enable AMD_MEM_ENCRYPT_ACTIVE_BY_DEFAULT automatically (Prarit Bhargava) [2021200]
- ucounts: Move get_ucounts from cred_alloc_blank to key_change_session_keyring (Alexey Gladkov) [2018142]
- ucounts: Proper error handling in set_cred_ucounts (Alexey Gladkov) [2018142]
- ucounts: Pair inc_rlimit_ucounts with dec_rlimit_ucoutns in commit_creds (Alexey Gladkov) [2018142]
- ucounts: Fix signal ucount refcounting (Alexey Gladkov) [2018142]
- x86/cpu: Fix migration safety with X86_BUG_NULL_SEL (Vitaly Kuznetsov) [2016959]
- ip6_gre: Revert "ip6_gre: add validation for csum_start" (Guillaume Nault) [2014993]
- ip_gre: validate csum_start only on pull (Guillaume Nault) [2014993]
- redhat/configs: enable KEXEC_IMAGE_VERIFY_SIG for RHEL (Coiby Xu) [1994858]
- redhat/configs: enable KEXEC_SIG for aarch64 RHEL (Coiby Xu) [1994858]
- kernel.spec: add bpf_testmod.ko to kselftests/bpf (Viktor Malik) [2006318 2006319]
- netfilter: Add deprecation notices for xtables (Phil Sutter) [1945179]
- redhat: Add mark_driver_deprecated() (Phil Sutter) [1945179]

* Tue Nov 23 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-20.el9]
- powerpc/svm: Don't issue ultracalls if !mem_encrypt_active() (Herton R. Krzesinski) [2025186]

* Fri Nov 19 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-19.el9]
- net: core: don't call SIOCBRADD/DELIF for non-bridge devices (Ivan Vecera) [2008927]
- net: bridge: fix ioctl old_deviceless bridge argument (Ivan Vecera) [2008927]
- net: bridge: fix ioctl locking (Ivan Vecera) [2008927]
- ethtool: Fix rxnfc copy to user buffer overflow (Ivan Vecera) [2008927]
- net: bonding: move ioctl handling to private ndo operation (Ivan Vecera) [2008927]
- net: bridge: move bridge ioctls out of .ndo_do_ioctl (Ivan Vecera) [2008927]
- net: socket: return changed ifreq from SIOCDEVPRIVATE (Ivan Vecera) [2008927]
- net: split out ndo_siowandev ioctl (Ivan Vecera) [2008927]
- dev_ioctl: split out ndo_eth_ioctl (Ivan Vecera) [2008927]
- dev_ioctl: pass SIOCDEVPRIVATE data separately (Ivan Vecera) [2008927]
- wan: cosa: remove dead cosa_net_ioctl() function (Ivan Vecera) [2008927]
- wan: use ndo_siocdevprivate (Ivan Vecera) [2008927]
- ppp: use ndo_siocdevprivate (Ivan Vecera) [2008927]
- sb1000: use ndo_siocdevprivate (Ivan Vecera) [2008927]
- hippi: use ndo_siocdevprivate (Ivan Vecera) [2008927]
- ip_tunnel: use ndo_siocdevprivate (Ivan Vecera) [2008927]
- airo: use ndo_siocdevprivate (Ivan Vecera) [2008927]
- hamradio: use ndo_siocdevprivate (Ivan Vecera) [2008927]
- cxgb3: use ndo_siocdevprivate (Ivan Vecera) [2008927]
- qeth: use ndo_siocdevprivate (Ivan Vecera) [2008927]
- slip/plip: use ndo_siocdevprivate (Ivan Vecera) [2008927]
- net: usb: use ndo_siocdevprivate (Ivan Vecera) [2008927]
- fddi: use ndo_siocdevprivate (Ivan Vecera) [2008927]
- eql: use ndo_siocdevprivate (Ivan Vecera) [2008927]
- tehuti: use ndo_siocdevprivate (Ivan Vecera) [2008927]
- hamachi: use ndo_siocdevprivate (Ivan Vecera) [2008927]
- appletalk: use ndo_siocdevprivate (Ivan Vecera) [2008927]
- bonding: use siocdevprivate (Ivan Vecera) [2008927]
- tulip: use ndo_siocdevprivate (Ivan Vecera) [2008927]
- phonet: use siocdevprivate (Ivan Vecera) [2008927]
- bridge: use ndo_siocdevprivate (Ivan Vecera) [2008927]
- hostap: use ndo_siocdevprivate (Ivan Vecera) [2008927]
- staging: wlan-ng: use siocdevprivate (Ivan Vecera) [2008927]
- staging: rtlwifi: use siocdevprivate (Ivan Vecera) [2008927]
- net: split out SIOCDEVPRIVATE handling from dev_ioctl (Ivan Vecera) [2008927]
- net: socket: rework compat_ifreq_ioctl() (Ivan Vecera) [2008927]
- net: socket: simplify dev_ifconf handling (Ivan Vecera) [2008927]
- net: socket: remove register_gifconf (Ivan Vecera) [2008927]
- net: socket: rework SIOC?IFMAP ioctls (Ivan Vecera) [2008927]
- ethtool: improve compat ioctl handling (Ivan Vecera) [2008927]
- compat: make linux/compat.h available everywhere (Ivan Vecera) [2008927]

* Thu Nov 18 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-18.el9]
- CI: Add template for baseline gcov build (c9s repos) (Michael Hofmann)
- PCI: vmd: depend on !UML (Myron Stowe) [1994932]
- PCI: vmd: Do not disable MSI-X remapping if interrupt remapping is enabled by IOMMU (Myron Stowe) [1994932]
- PCI: vmd: Assign a number to each VMD controller (Myron Stowe) [1994932]
- PCI: VMD: ACPI: Make ACPI companion lookup work for VMD bus (Myron Stowe) [1994932]
- swiotlb-xen: drop DEFAULT_NSLABS (Jerry Snitselaar) [2004348]
- swiotlb-xen: arrange to have buffer info logged (Jerry Snitselaar) [2004348]
- swiotlb-xen: drop leftover __ref (Jerry Snitselaar) [2004348]
- swiotlb-xen: limit init retries (Jerry Snitselaar) [2004348]
- swiotlb-xen: suppress certain init retries (Jerry Snitselaar) [2004348]
- swiotlb-xen: maintain slab count properly (Jerry Snitselaar) [2004348]
- swiotlb-xen: fix late init retry (Jerry Snitselaar) [2004348]
- swiotlb-xen: avoid double free (Jerry Snitselaar) [2004348]
- dma-debug: teach add_dma_entry() about DMA_ATTR_SKIP_CPU_SYNC (Jerry Snitselaar) [2004348]
- dma-debug: fix sg checks in debug_dma_map_sg() (Jerry Snitselaar) [2004348]
- dma-mapping: fix the kerneldoc for dma_map_sgtable() (Jerry Snitselaar) [2004348]
- dma-debug: prevent an error message from causing runtime problems (Jerry Snitselaar) [2004348]
- dma-mapping: fix the kerneldoc for dma_map_sg_attrs (Jerry Snitselaar) [2004348]
- iommu/vt-d: Drop "0x" prefix from PCI bus & device addresses (Jerry Snitselaar) [2004348]
- iommu: Clarify default domain Kconfig (Jerry Snitselaar) [2004348]
- iommu/vt-d: Fix a deadlock in intel_svm_drain_prq() (Jerry Snitselaar) [2004348]
- iommu/vt-d: Fix PASID leak in intel_svm_unbind_mm() (Jerry Snitselaar) [2004348]
- iommu/amd: Remove iommu_init_ga() (Jerry Snitselaar) [2004348]
- iommu/amd: Relocate GAMSup check to early_enable_iommus (Jerry Snitselaar) [2004348]
- iommu/io-pgtable: Abstract iommu_iotlb_gather access (Jerry Snitselaar) [2004348]
- iommu/vt-d: Add present bit check in pasid entry setup helpers (Jerry Snitselaar) [2004348]
- iommu/vt-d: Use pasid_pte_is_present() helper function (Jerry Snitselaar) [2004348]
- iommu/vt-d: Drop the kernel doc annotation (Jerry Snitselaar) [2004348]
- iommu/vt-d: Allow devices to have more than 32 outstanding PRs (Jerry Snitselaar) [1921363]
- iommu/vt-d: Preset A/D bits for user space DMA usage (Jerry Snitselaar) [2004348]
- iomm/vt-d: Enable Intel IOMMU scalable mode by default (Jerry Snitselaar) [2004348]
- iommu/vt-d: Refactor Kconfig a bit (Jerry Snitselaar) [2004348]
- iommu/vt-d: Remove unnecessary oom message (Jerry Snitselaar) [2004348]
- iommu/vt-d: Update the virtual command related registers (Jerry Snitselaar) [2004348]
- iommu: Allow enabling non-strict mode dynamically (Jerry Snitselaar) [2004348]
- iommu: Merge strictness and domain type configs (Jerry Snitselaar) [2004348]
- iommu: Only log strictness for DMA domains (Jerry Snitselaar) [2004348]
- iommu: Expose DMA domain strictness via sysfs (Jerry Snitselaar) [2004348]
- iommu: Express DMA strictness via the domain type (Jerry Snitselaar) [2004348]
- iommu/vt-d: Prepare for multiple DMA domain types (Jerry Snitselaar) [2004348]
- iommu/arm-smmu: Prepare for multiple DMA domain types (Jerry Snitselaar) [2004348]
- iommu/amd: Prepare for multiple DMA domain types (Jerry Snitselaar) [2004348]
- iommu: Introduce explicit type for non-strict DMA domains (Jerry Snitselaar) [2004348]
- iommu/io-pgtable: Remove non-strict quirk (Jerry Snitselaar) [2004348]
- iommu: Indicate queued flushes via gather data (Jerry Snitselaar) [2004348]
- iommu/dma: Remove redundant "!dev" checks (Jerry Snitselaar) [2004348]
- iommu/virtio: Drop IOVA cookie management (Jerry Snitselaar) [2004348]
- iommu/vt-d: Drop IOVA cookie management (Jerry Snitselaar) [2004348]
- iommu/arm-smmu: Drop IOVA cookie management (Jerry Snitselaar) [2004348]
- iommu/amd: Drop IOVA cookie management (Jerry Snitselaar) [2004348]
- iommu: Pull IOVA cookie management into the core (Jerry Snitselaar) [2004348]
- iommu/amd: Remove stale amd_iommu_unmap_flush usage (Jerry Snitselaar) [2004348]
- iommu/amd: Use only natural aligned flushes in a VM (Jerry Snitselaar) [2004348]
- iommu/amd: Sync once for scatter-gather operations (Jerry Snitselaar) [2004348]
- iommu/amd: Tailored gather logic for AMD (Jerry Snitselaar) [2004348]
- iommu: Factor iommu_iotlb_gather_is_disjoint() out (Jerry Snitselaar) [2004348]
- iommu: Improve iommu_iotlb_gather helpers (Jerry Snitselaar) [2004348]
- iommu/amd: Do not use flush-queue when NpCache is on (Jerry Snitselaar) [2004348]
- iommu/amd: Selective flush on unmap (Jerry Snitselaar) [2004348]
- iommu/amd: Fix printing of IOMMU events when rate limiting kicks in (Jerry Snitselaar) [2004348]
- iommu/amd: Convert from atomic_t to refcount_t on pasid_state->count (Jerry Snitselaar) [2004348]
- iommu/arm-smmu: Fix missing unlock on error in arm_smmu_device_group() (Jerry Snitselaar) [2004348]
- iommu/arm-smmu-v3: Stop pre-zeroing batch commands (Jerry Snitselaar) [2004348]
- iommu/arm-smmu-v3: Extract reusable function __arm_smmu_cmdq_skip_err() (Jerry Snitselaar) [2004348]
- iommu/arm-smmu-v3: Add and use static helper function arm_smmu_get_cmdq() (Jerry Snitselaar) [2004348]
- iommu/arm-smmu-v3: Add and use static helper function arm_smmu_cmdq_issue_cmd_with_sync() (Jerry Snitselaar) [2004348]
- iommu/arm-smmu-v3: Use command queue batching helpers to improve performance (Jerry Snitselaar) [2004348]
- iommu/arm-smmu: Optimize ->tlb_flush_walk() for qcom implementation (Jerry Snitselaar) [2004348]
- iommu/arm-smmu: Fix race condition during iommu_group creation (Jerry Snitselaar) [2004348]
- iommu: Fix race condition during default domain allocation (Jerry Snitselaar) [2004348]
- iommu/arm-smmu: Add clk_bulk_{prepare/unprepare} to system pm callbacks (Jerry Snitselaar) [2004348]
- iommu/arm-smmu-v3: Remove some unneeded init in arm_smmu_cmdq_issue_cmdlist() (Jerry Snitselaar) [2004348]
- iommu/arm-smmu-v3: Implement the map_pages() IOMMU driver callback (Jerry Snitselaar) [1971978]
- iommu/arm-smmu-v3: Implement the unmap_pages() IOMMU driver callback (Jerry Snitselaar) [1971978]
- iommu/vt-d: Move clflush'es from iotlb_sync_map() to map_pages() (Jerry Snitselaar) [1971978]
- iommu/vt-d: Implement map/unmap_pages() iommu_ops callback (Jerry Snitselaar) [1971978]
- iommu/vt-d: Report real pgsize bitmap to iommu core (Jerry Snitselaar) [1971978]
- iommu: Streamline iommu_iova_to_phys() (Jerry Snitselaar) [2004348]
- iommu: Remove mode argument from iommu_set_dma_strict() (Jerry Snitselaar) [2004348]
- redhat/configs: Use new iommu default dma config options (Jerry Snitselaar) [2004348]
- iommu/amd: Add support for IOMMU default DMA mode build options (Jerry Snitselaar) [2004348]
- iommu/vt-d: Add support for IOMMU default DMA mode build options (Jerry Snitselaar) [2004348]
- iommu: Enhance IOMMU default DMA mode build options (Jerry Snitselaar) [2004348]
- iommu: Print strict or lazy mode at init time (Jerry Snitselaar) [2004348]
- iommu: Deprecate Intel and AMD cmdline methods to enable strict mode (Jerry Snitselaar) [2004348]
- iommu/arm-smmu: Implement the map_pages() IOMMU driver callback (Jerry Snitselaar) [1971978]
- iommu/arm-smmu: Implement the unmap_pages() IOMMU driver callback (Jerry Snitselaar) [1971978]
- iommu/io-pgtable-arm-v7s: Implement arm_v7s_map_pages() (Jerry Snitselaar) [1971978]
- iommu/io-pgtable-arm-v7s: Implement arm_v7s_unmap_pages() (Jerry Snitselaar) [1971978]
- iommu/io-pgtable-arm: Implement arm_lpae_map_pages() (Jerry Snitselaar) [1971978]
- iommu/io-pgtable-arm: Implement arm_lpae_unmap_pages() (Jerry Snitselaar) [1971978]
- iommu/io-pgtable-arm: Prepare PTE methods for handling multiple entries (Jerry Snitselaar) [1971978]
- iommu/io-pgtable: Introduce map_pages() as a page table op (Jerry Snitselaar) [1971978]
- iommu/io-pgtable: Introduce unmap_pages() as a page table op (Jerry Snitselaar) [1971978]
- iommu: Add support for the map_pages() callback (Jerry Snitselaar) [1971978]
- iommu: Hook up '->unmap_pages' driver callback (Jerry Snitselaar) [1971978]
- iommu: Split 'addr_merge' argument to iommu_pgsize() into separate parts (Jerry Snitselaar) [1971978]
- iommu: Use bitmap to calculate page size in iommu_pgsize() (Jerry Snitselaar) [1971978]
- iommu: Add a map_pages() op for IOMMU drivers (Jerry Snitselaar) [1971978]
- iommu: Add an unmap_pages() op for IOMMU drivers (Jerry Snitselaar) [1971978]
- swiotlb: use depends on for DMA_RESTRICTED_POOL (Jerry Snitselaar) [2004348]
- swiotlb: Free tbl memory in swiotlb_exit() (Jerry Snitselaar) [2004348]
- swiotlb: Emit diagnostic in swiotlb_exit() (Jerry Snitselaar) [2004348]
- swiotlb: Convert io_default_tlb_mem to static allocation (Jerry Snitselaar) [2004348]
- swiotlb: add overflow checks to swiotlb_bounce (Jerry Snitselaar) [2004348]
- swiotlb: fix implicit debugfs declarations (Jerry Snitselaar) [2004348]
- swiotlb: Add restricted DMA pool initialization (Jerry Snitselaar) [2004348]
- redhat/configs: Add CONFIG_DMA_RESTRICTED_POOL (Jerry Snitselaar) [2004348]
- swiotlb: Add restricted DMA alloc/free support (Jerry Snitselaar) [2004348]
- swiotlb: Refactor swiotlb_tbl_unmap_single (Jerry Snitselaar) [2004348]
- swiotlb: Move alloc_size to swiotlb_find_slots (Jerry Snitselaar) [2004348]
- swiotlb: Use is_swiotlb_force_bounce for swiotlb data bouncing (Jerry Snitselaar) [2004348]
- swiotlb: Update is_swiotlb_active to add a struct device argument (Jerry Snitselaar) [2004348]
- swiotlb: Update is_swiotlb_buffer to add a struct device argument (Jerry Snitselaar) [2004348]
- swiotlb: Set dev->dma_io_tlb_mem to the swiotlb pool used (Jerry Snitselaar) [2004348]
- swiotlb: Refactor swiotlb_create_debugfs (Jerry Snitselaar) [2004348]
- swiotlb: Refactor swiotlb init functions (Jerry Snitselaar) [2004348]
- dma-mapping: make the global coherent pool conditional (Jerry Snitselaar) [2004348]
- dma-mapping: add a dma_init_global_coherent helper (Jerry Snitselaar) [2004348]
- dma-mapping: simplify dma_init_coherent_memory (Jerry Snitselaar) [2004348]
- dma-mapping: allow using the global coherent pool for !ARM (Jerry Snitselaar) [2004348]
- dma-direct: add support for dma_coherent_default_memory (Jerry Snitselaar) [2004348]
- dma-mapping: return an unsigned int from dma_map_sg{,_attrs} (Jerry Snitselaar) [2004348]
- dma-mapping: disallow .map_sg operations from returning zero on error (Jerry Snitselaar) [2004348]
- dma-mapping: return error code from dma_dummy_map_sg() (Jerry Snitselaar) [2004348]
- xen: swiotlb: return error code from xen_swiotlb_map_sg() (Jerry Snitselaar) [2004348]
- s390/pci: don't set failed sg dma_address to DMA_MAPPING_ERROR (Jerry Snitselaar) [2004348]
- s390/pci: return error code from s390_dma_map_sg() (Jerry Snitselaar) [2004348]
- powerpc/iommu: don't set failed sg dma_address to DMA_MAPPING_ERROR (Jerry Snitselaar) [2004348]
- powerpc/iommu: return error code from .map_sg() ops (Jerry Snitselaar) [2004348]
- iommu/dma: return error code from iommu_dma_map_sg() (Jerry Snitselaar) [2004348]
- iommu: return full error code from iommu_map_sg[_atomic]() (Jerry Snitselaar) [2004348]
- dma-direct: return appropriate error code from dma_direct_map_sg() (Jerry Snitselaar) [2004348]
- dma-mapping: allow map_sg() ops to return negative error codes (Jerry Snitselaar) [2004348]
- dma-debug: fix debugfs initialization order (Jerry Snitselaar) [2004348]
- dma-debug: use memory_intersects() directly (Jerry Snitselaar) [2004348]

* Tue Nov 16 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-17.el9]
- net: mana: Support hibernation and kexec (Mohammed Gamal) [2011883]
- net: mana: Improve the HWC error handling (Mohammed Gamal) [2011883]
- net: mana: Report OS info to the PF driver (Mohammed Gamal) [2011883]
- net: mana: Fix the netdev_err()'s vPort argument in mana_init_port() (Mohammed Gamal) [2011883]
- net: mana: Allow setting the number of queues while the NIC is down (Mohammed Gamal) [2011883]
- net: mana: Fix error handling in mana_create_rxq() (Mohammed Gamal) [2011883]
- net: mana: Use kcalloc() instead of kzalloc() (Mohammed Gamal) [2011883]
- net: mana: Prefer struct_size over open coded arithmetic (Mohammed Gamal) [2011883]
- net: mana: Add WARN_ON_ONCE in case of CQE read overflow (Mohammed Gamal) [2011883]
- net: mana: Add support for EQ sharing (Mohammed Gamal) [2011883]
- net: mana: Move NAPI from EQ to CQ (Mohammed Gamal) [2011883]
- PCI: hv: Fix sleep while in non-sleep context when removing child devices from the bus (Mohammed Gamal) [2008571]
- objtool: Remove redundant 'len' field from struct section (C. Erastus Toe) [2002440]
- objtool: Make .altinstructions section entry size consistent (C. Erastus Toe) [2002440]
- s390/topology: fix topology information when calling cpu hotplug notifiers (Phil Auld) [2003998]
- fs: remove leftover comments from mandatory locking removal (Jeffrey Layton) [2017438]
- locks: remove changelog comments (Jeffrey Layton) [2017438]
- docs: fs: locks.rst: update comment about mandatory file locking (Jeffrey Layton) [2017438]
- Documentation: remove reference to now removed mandatory-locking doc (Jeffrey Layton) [2017438]
- locks: remove LOCK_MAND flock lock support (Jeffrey Layton) [2017438]
- fs: clean up after mandatory file locking support removal (Jeffrey Layton) [2017438]
- fs: remove mandatory file locking support (Jeffrey Layton) [2017438]
- fcntl: fix potential deadlock for &fasync_struct.fa_lock (Jeffrey Layton) [2017438]
- fcntl: fix potential deadlocks for &fown_struct.lock (Jeffrey Layton) [2017438]
- KVM: s390: Enable specification exception interpretation (Thomas Huth) [2001770]
- redhat/configs: enable CONFIG_BCMGENET as module (Joel Savitz) [2011025]

* Fri Nov 12 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-16.el9]
- CI: Add template for baseline gcov build for RHEL (Israel Santana Aleman)
- redhat/configs: Enable Nitro Enclaves on Aarch64 (Vitaly Kuznetsov) [2001582]
- nitro_enclaves: Add fixes for checkpatch blank line reports (Vitaly Kuznetsov) [2001582]
- nitro_enclaves: Add fixes for checkpatch spell check reports (Vitaly Kuznetsov) [2001582]
- nitro_enclaves: Add fixes for checkpatch match open parenthesis reports (Vitaly Kuznetsov) [2001582]
- nitro_enclaves: Update copyright statement to include 2021 (Vitaly Kuznetsov) [2001582]
- nitro_enclaves: Add fix for the kernel-doc report (Vitaly Kuznetsov) [2001582]
- nitro_enclaves: Update documentation for Arm64 support (Vitaly Kuznetsov) [2001582]
- nitro_enclaves: Enable Arm64 support (Vitaly Kuznetsov) [2001582]
- redhat/configs: Enable Hyper-V support on ARM (Vitaly Kuznetsov) [1949613]
- redhat/configs: enable CONFIG_INPUT_KEYBOARD for AARCH64 (Vitaly Kuznetsov) [1949613]
- Drivers: hv: Enable Hyper-V code to be built on ARM64 (Vitaly Kuznetsov) [1949613]
- arm64: efi: Export screen_info (Vitaly Kuznetsov) [1949613]
- arm64: hyperv: Initialize hypervisor on boot (Vitaly Kuznetsov) [1949613]
- arm64: hyperv: Add panic handler (Vitaly Kuznetsov) [1949613]
- arm64: hyperv: Add Hyper-V hypercall and register access utilities (Vitaly Kuznetsov) [1949613]
- PCI: hv: Turn on the host bridge probing on ARM64 (Vitaly Kuznetsov) [1949613]
- PCI: hv: Set up MSI domain at bridge probing time (Vitaly Kuznetsov) [1949613]
- PCI: hv: Set ->domain_nr of pci_host_bridge at probing time (Vitaly Kuznetsov) [1949613]
- PCI: hv: Generify PCI probing (Vitaly Kuznetsov) [1949613]
- arm64: PCI: Support root bridge preparation for Hyper-V (Vitaly Kuznetsov) [1949613]
- arm64: PCI: Restructure pcibios_root_bridge_prepare() (Vitaly Kuznetsov) [1949613]
- PCI: Support populating MSI domains of root buses via bridges (Vitaly Kuznetsov) [1949613]
- PCI: Introduce domain_nr in pci_host_bridge (Vitaly Kuznetsov) [1949613]
- drivers: hv: Decouple Hyper-V clock/timer code from VMbus drivers (Vitaly Kuznetsov) [1949613]
- Drivers: hv: Move Hyper-V misc functionality to arch-neutral code (Vitaly Kuznetsov) [1949613]
- Drivers: hv: Add arch independent default functions for some Hyper-V handlers (Vitaly Kuznetsov) [1949613]
- Drivers: hv: Make portions of Hyper-V init code be arch neutral (Vitaly Kuznetsov) [1949613]
- asm-generic/hyperv: Add missing #include of nmi.h (Vitaly Kuznetsov) [1949613]
- PCI: hv: Support for create interrupt v3 (Vitaly Kuznetsov) [1949613]
- x86_64: Enable Elkhart Lake Quadrature Encoder Peripheral support (Prarit Bhargava) [1874997]

* Thu Nov 11 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-15.el9]
- scsi: lpfc: Fix memory overwrite during FC-GS I/O abort handling (Dick Kennedy) [1879528]
- scsi: lpfc: Fix gcc -Wstringop-overread warning, again (Dick Kennedy) [1879528]
- scsi: lpfc: Use correct scnprintf() limit (Dick Kennedy) [1879528]
- scsi: lpfc: Fix sprintf() overflow in lpfc_display_fpin_wwpn() (Dick Kennedy) [1879528]
- scsi: lpfc: Fix compilation errors on kernels with no CONFIG_DEBUG_FS (Dick Kennedy) [1879528]
- scsi: lpfc: Fix CPU to/from endian warnings introduced by ELS processing (Dick Kennedy) [1879528]
- scsi: lpfc: Update lpfc version to 14.0.0.2 (Dick Kennedy) [1879528]
- scsi: lpfc: Improve PBDE checks during SGL processing (Dick Kennedy) [1879528]
- scsi: lpfc: Zero CGN stats only during initial driver load and stat reset (Dick Kennedy) [1879528]
- scsi: lpfc: Fix I/O block after enabling managed congestion mode (Dick Kennedy) [1879528]
- scsi: lpfc: Adjust bytes received vales during cmf timer interval (Dick Kennedy) [1879528]
- scsi: lpfc: Fix EEH support for NVMe I/O (Dick Kennedy) [1879528]
- scsi: lpfc: Fix FCP I/O flush functionality for TMF routines (Dick Kennedy) [1879528]
- scsi: lpfc: Fix NVMe I/O failover to non-optimized path (Dick Kennedy) [1879528]
- scsi: lpfc: Don't remove ndlp on PRLI errors in P2P mode (Dick Kennedy) [1879528]
- scsi: lpfc: Fix rediscovery of tape device after LIP (Dick Kennedy) [1879528]
- scsi: lpfc: Fix hang on unload due to stuck fport node (Dick Kennedy) [1879528]
- scsi: lpfc: Fix premature rpi release for unsolicited TPLS and LS_RJT (Dick Kennedy) [1879528]
- scsi: lpfc: Don't release final kref on Fport node while ABTS outstanding (Dick Kennedy) [1879528]
- scsi: lpfc: Fix list_add() corruption in lpfc_drain_txq() (Dick Kennedy) [1879528]
- scsi: fc: Add EDC ELS definition (Dick Kennedy) [1879528]
- scsi: lpfc: Copyright updates for 14.0.0.1 patches (Dick Kennedy) [1879528]
- scsi: lpfc: Update lpfc version to 14.0.0.1 (Dick Kennedy) [1879528]
- scsi: lpfc: Add bsg support for retrieving adapter cmf data (Dick Kennedy) [1879528]
- scsi: lpfc: Add cmf_info sysfs entry (Dick Kennedy) [1879528]
- scsi: lpfc: Add debugfs support for cm framework buffers (Dick Kennedy) [1879528]
- scsi: lpfc: Add support for maintaining the cm statistics buffer (Dick Kennedy) [1879528]
- scsi: lpfc: Add rx monitoring statistics (Dick Kennedy) [1879528]
- scsi: lpfc: Add support for the CM framework (Dick Kennedy) [1879528]
- scsi: lpfc: Add cmfsync WQE support (Dick Kennedy) [1879528]
- scsi: lpfc: Add support for cm enablement buffer (Dick Kennedy) [1879528]
- scsi: lpfc: Add cm statistics buffer support (Dick Kennedy) [1879528]
- scsi: lpfc: Add EDC ELS support (Dick Kennedy) [1879528]
- scsi: lpfc: Expand FPIN and RDF receive logging (Dick Kennedy) [1879528]
- scsi: lpfc: Add MIB feature enablement support (Dick Kennedy) [1879528]
- scsi: lpfc: Add SET_HOST_DATA mbox cmd to pass date/time info to firmware (Dick Kennedy) [1879528]
- scsi: lpfc: Fix possible ABBA deadlock in nvmet_xri_aborted() (Dick Kennedy) [1879528]
- scsi: lpfc: Remove redundant assignment to pointer pcmd (Dick Kennedy) [1879528]
- scsi: lpfc: Copyright updates for 14.0.0.0 patches (Dick Kennedy) [1879528]
- scsi: lpfc: Update lpfc version to 14.0.0.0 (Dick Kennedy) [1879528]
- scsi: lpfc: Add 256 Gb link speed support (Dick Kennedy) [1879528]
- scsi: lpfc: Revise Topology and RAS support checks for new adapters (Dick Kennedy) [1879528]
- scsi: lpfc: Fix cq_id truncation in rq create (Dick Kennedy) [1879528]
- scsi: lpfc: Add PCI ID support for LPe37000/LPe38000 series adapters (Dick Kennedy) [1879528]
- scsi: lpfc: Copyright updates for 12.8.0.11 patches (Dick Kennedy) [1879528]
- scsi: lpfc: Update lpfc version to 12.8.0.11 (Dick Kennedy) [1879528]
- scsi: lpfc: Skip issuing ADISC when node is in NPR state (Dick Kennedy) [1879528]
- scsi: lpfc: Skip reg_vpi when link is down for SLI3 in ADISC cmpl path (Dick Kennedy) [1879528]
- scsi: lpfc: Call discovery state machine when handling PLOGI/ADISC completions (Dick Kennedy) [1879528]
- scsi: lpfc: Delay unregistering from transport until GIDFT or ADISC completes (Dick Kennedy) [1879528]
- scsi: lpfc: Enable adisc discovery after RSCN by default (Dick Kennedy) [1879528]
- scsi: lpfc: Use PBDE feature enabled bit to determine PBDE support (Dick Kennedy) [1879528]
- scsi: lpfc: Clear outstanding active mailbox during PCI function reset (Dick Kennedy) [1879528]
- scsi: lpfc: Fix KASAN slab-out-of-bounds in lpfc_unreg_rpi() routine (Dick Kennedy) [1879528]
- scsi: lpfc: Remove REG_LOGIN check requirement to issue an ELS RDF (Dick Kennedy) [1879528]
- scsi: lpfc: Fix memory leaks in error paths while issuing ELS RDF/SCR request (Dick Kennedy) [1879528]
- scsi: lpfc: Fix NULL ptr dereference with NPIV ports for RDF handling (Dick Kennedy) [1879528]
- scsi: lpfc: Keep NDLP reference until after freeing the IOCB after ELS handling (Dick Kennedy) [1879528]
- scsi: lpfc: Fix target reset handler from falsely returning FAILURE (Dick Kennedy) [1879528]
- scsi: lpfc: Discovery state machine fixes for LOGO handling (Dick Kennedy) [1879528]
- scsi: lpfc: Fix function description comments for vmid routines (Dick Kennedy) [1879528]
- scsi: lpfc: Improve firmware download logging (Dick Kennedy) [1879528]
- scsi: lpfc: Remove use of kmalloc() in trace event logging (Dick Kennedy) [1879528]
- scsi: lpfc: Fix NVMe support reporting in log message (Dick Kennedy) [1879528]

* Wed Nov 10 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-14.el9]
- evm: mark evm_fixmode as __ro_after_init (Bruno Meneguele) [2017160]
- IMA: remove -Wmissing-prototypes warning (Bruno Meneguele) [2017160]
- perf flamegraph: flamegraph.py script improvements (Michael Petlan) [2010271]
- redhat/configs/evaluate_configs: insert EMPTY tags at correct place (Jan Stancek) [2015082]
- redhat/configs/evaluate_configs: walk cfgvariants line by line (Jan Stancek) [2015082]
- redhat/configs: create a separate config for gcov options (Jan Stancek) [2015082]
- redhat/kernel.spec.template: don't hardcode gcov arches (Jan Stancek) [2015082]
- i40e: fix endless loop under rtnl (Stefan Assmann) [1992939]
- selftests/bpf: Use nanosleep tracepoint in perf buffer test (Jiri Olsa) [2006310]
- selftests/bpf: Fix possible/online index mismatch in perf_buffer test (Jiri Olsa) [2006310]
- selftests/bpf: Fix perf_buffer test on system with offline cpus (Jiri Olsa) [2006310]
- KVM: x86: Fix stack-out-of-bounds memory access from ioapic_write_indirect() (Vitaly Kuznetsov) [1965145]
- selftest/bpf: Switch recursion test to use htab_map_delete_elem (Jiri Olsa) [2006313]

* Mon Nov 08 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-13.el9]
- futex: Remove unused variable 'vpid' in futex_proxy_trylock_atomic() (Waiman Long) [2007032]
- futex: Prevent inconsistent state and exit race (Waiman Long) [2007032]
- locking/ww_mutex: Initialize waiter.ww_ctx properly (Waiman Long) [2007032]
- futex: Return error code instead of assigning it without effect (Waiman Long) [2007032]
- locking/rwbase: Take care of ordering guarantee for fastpath reader (Waiman Long) [2007032]
- locking/rwbase: Extract __rwbase_write_trylock() (Waiman Long) [2007032]
- locking/rwbase: Properly match set_and_save_state() to restore_state() (Waiman Long) [2007032]
- locking/rtmutex: Fix ww_mutex deadlock check (Waiman Long) [2007032]
- locking/rwsem: Add missing __init_rwsem() for PREEMPT_RT (Waiman Long) [2007032]
- locking/rtmutex: Return success on deadlock for ww_mutex waiters (Waiman Long) [2007032]
- locking/rtmutex: Prevent spurious EDEADLK return caused by ww_mutexes (Waiman Long) [2007032]
- locking/rtmutex: Dequeue waiter on ww_mutex deadlock (Waiman Long) [2007032]
- locking/rtmutex: Dont dereference waiter lockless (Waiman Long) [2007032]
- locking/local_lock: Add PREEMPT_RT support (Waiman Long) [2007032]
- locking/spinlock/rt: Prepare for RT local_lock (Waiman Long) [2007032]
- locking/rtmutex: Add adaptive spinwait mechanism (Waiman Long) [2007032]
- locking/rtmutex: Implement equal priority lock stealing (Waiman Long) [2007032]
- preempt: Adjust PREEMPT_LOCK_OFFSET for RT (Waiman Long) [2007032]
- locking/rtmutex: Prevent lockdep false positive with PI futexes (Waiman Long) [2007032]
- futex: Prevent requeue_pi() lock nesting issue on RT (Waiman Long) [2007032]
- futex: Simplify handle_early_requeue_pi_wakeup() (Waiman Long) [2007032]
- futex: Reorder sanity checks in futex_requeue() (Waiman Long) [2007032]
- futex: Clarify comment in futex_requeue() (Waiman Long) [2007032]
- futex: Restructure futex_requeue() (Waiman Long) [2007032]
- futex: Correct the number of requeued waiters for PI (Waiman Long) [2007032]
- futex: Remove bogus condition for requeue PI (Waiman Long) [2007032]
- futex: Clarify futex_requeue() PI handling (Waiman Long) [2007032]
- futex: Clean up stale comments (Waiman Long) [2007032]
- futex: Validate waiter correctly in futex_proxy_trylock_atomic() (Waiman Long) [2007032]
- lib/test_lockup: Adapt to changed variables (Waiman Long) [2007032]
- locking/rtmutex: Add mutex variant for RT (Waiman Long) [2007032]
- locking/ww_mutex: Implement rtmutex based ww_mutex API functions (Waiman Long) [2007032]
- locking/rtmutex: Extend the rtmutex core to support ww_mutex (Waiman Long) [2007032]
- locking/ww_mutex: Add rt_mutex based lock type and accessors (Waiman Long) [2007032]
- locking/ww_mutex: Add RT priority to W/W order (Waiman Long) [2007032]
- locking/ww_mutex: Implement rt_mutex accessors (Waiman Long) [2007032]
- locking/ww_mutex: Abstract out internal lock accesses (Waiman Long) [2007032]
- locking/ww_mutex: Abstract out mutex types (Waiman Long) [2007032]
- locking/ww_mutex: Abstract out mutex accessors (Waiman Long) [2007032]
- locking/ww_mutex: Abstract out waiter enqueueing (Waiman Long) [2007032]
- locking/ww_mutex: Abstract out the waiter iteration (Waiman Long) [2007032]
- locking/ww_mutex: Remove the __sched annotation from ww_mutex APIs (Waiman Long) [2007032]
- locking/ww_mutex: Split out the W/W implementation logic into kernel/locking/ww_mutex.h (Waiman Long) [2007032]
- locking/ww_mutex: Split up ww_mutex_unlock() (Waiman Long) [2007032]
- locking/ww_mutex: Gather mutex_waiter initialization (Waiman Long) [2007032]
- locking/ww_mutex: Simplify lockdep annotations (Waiman Long) [2007032]
- locking/mutex: Make mutex::wait_lock raw (Waiman Long) [2007032]
- locking/ww_mutex: Move the ww_mutex definitions from <linux/mutex.h> into <linux/ww_mutex.h> (Waiman Long) [2007032]
- locking/mutex: Move the 'struct mutex_waiter' definition from <linux/mutex.h> to the internal header (Waiman Long) [2007032]
- locking/mutex: Consolidate core headers, remove kernel/locking/mutex-debug.h (Waiman Long) [2007032]
- locking/rtmutex: Squash !RT tasks to DEFAULT_PRIO (Waiman Long) [2007032]
- locking/rwlock: Provide RT variant (Waiman Long) [2007032]
- locking/spinlock: Provide RT variant (Waiman Long) [2007032]
- locking/rtmutex: Provide the spin/rwlock core lock function (Waiman Long) [2007032]
- locking/spinlock: Provide RT variant header: <linux/spinlock_rt.h> (Waiman Long) [2007032]
- locking/spinlock: Provide RT specific spinlock_t (Waiman Long) [2007032]
- locking/rtmutex: Reduce <linux/rtmutex.h> header dependencies, only include <linux/rbtree_types.h> (Waiman Long) [2007032]
- rbtree: Split out the rbtree type definitions into <linux/rbtree_types.h> (Waiman Long) [2007032]
- locking/lockdep: Reduce header dependencies in <linux/debug_locks.h> (Waiman Long) [2007032]
- locking/rtmutex: Prevent future include recursion hell (Waiman Long) [2007032]
- locking/spinlock: Split the lock types header, and move the raw types into <linux/spinlock_types_raw.h> (Waiman Long) [2007032]
- locking/rtmutex: Guard regular sleeping locks specific functions (Waiman Long) [2007032]
- locking/rtmutex: Prepare RT rt_mutex_wake_q for RT locks (Waiman Long) [2007032]
- locking/rtmutex: Use rt_mutex_wake_q_head (Waiman Long) [2007032]
- locking/rtmutex: Provide rt_wake_q_head and helpers (Waiman Long) [2007032]
- locking/rtmutex: Add wake_state to rt_mutex_waiter (Waiman Long) [2007032]
- locking/rwsem: Add rtmutex based R/W semaphore implementation (Waiman Long) [2007032]
- locking/rt: Add base code for RT rw_semaphore and rwlock (Waiman Long) [2007032]
- locking/rtmutex: Provide rt_mutex_base_is_locked() (Waiman Long) [2007032]
- locking/rtmutex: Provide rt_mutex_slowlock_locked() (Waiman Long) [2007032]
- locking/rtmutex: Split out the inner parts of 'struct rtmutex' (Waiman Long) [2007032]
- locking/rtmutex: Split API from implementation (Waiman Long) [2007032]
- locking/rtmutex: Switch to from cmpxchg_*() to try_cmpxchg_*() (Waiman Long) [2007032]
- locking/rtmutex: Convert macros to inlines (Waiman Long) [2007032]
- locking/rtmutex: Remove rt_mutex_is_locked() (Waiman Long) [2007032]
- sched/wake_q: Provide WAKE_Q_HEAD_INITIALIZER() (Waiman Long) [2007032]
- sched/core: Provide a scheduling point for RT locks (Waiman Long) [2007032]
- sched/core: Rework the __schedule() preempt argument (Waiman Long) [2007032]
- sched/wakeup: Prepare for RT sleeping spin/rwlocks (Waiman Long) [2007032]
- sched/wakeup: Reorganize the current::__state helpers (Waiman Long) [2007032]
- sched/wakeup: Introduce the TASK_RTLOCK_WAIT state bit (Waiman Long) [2007032]
- sched/wakeup: Split out the wakeup ->__state check (Waiman Long) [2007032]
- locking/rtmutex: Set proper wait context for lockdep (Waiman Long) [2007032]
- locking/local_lock: Add missing owner initialization (Waiman Long) [2007032]
- locking/mutex: Add MUTEX_WARN_ON (Waiman Long) [2007032]
- locking/mutex: Introduce __mutex_trylock_or_handoff() (Waiman Long) [2007032]
- locking/mutex: Fix HANDOFF condition (Waiman Long) [2007032]
- locking/mutex: Use try_cmpxchg() (Waiman Long) [2007032]

* Thu Nov 04 2021 Jarod Wilson <jarod@redhat.com> [5.14.0-12.el9]
- redhat: make dist-srpm-gcov add to BUILDOPTS (Jan Stancek) [2017628]
- redhat: Fix dist-srpm-gcov (Jan Stancek) [2017628]
- s390: report more CPU capabilities (Robin Dapp) [2012095]
- s390/disassembler: add instructions (Robin Dapp) [2012095]
- audit: move put_tree() to avoid trim_trees refcount underflow and UAF (Richard Guy Briggs) [1985904]
- libbpf: Properly ignore STT_SECTION symbols in legacy map definitions (Jiri Olsa) [1998266]
- libbpf: Ignore STT_SECTION symbols in 'maps' section (Jiri Olsa) [1998266]
- selftests, bpf: test_lwt_ip_encap: Really disable rp_filter (Jiri Benc) [2006328]

* Thu Oct 28 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-11.el9]
- selinux: remove the SELinux lockdown implementation (Ondrej Mosnacek) [1940843 1945581]
- bpf: Fix integer overflow in prealloc_elems_and_freelist() (Yauheni Kaliuta) [2010494] {CVE-2021-41864}
- seltests: bpf: test_tunnel: Use ip neigh (Jiri Benc) [2006326]

* Tue Oct 26 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-10.el9]
- block: return ELEVATOR_DISCARD_MERGE if possible (Ming Lei) [1991958]
- blk-mq: avoid to iterate over stale request (Ming Lei) [2009110]
- redhat/configs: enable CONFIG_IMA_WRITE_POLICY (Bruno Meneguele) [2006320]
- CI: Update deprecated configs (Veronika Kabatova)

* Wed Oct 20 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-9.el9]
- powerpc/pseries: Prevent free CPU ids being reused on another node (Desnes A. Nunes do Rosario) [2004809]
- pseries/drmem: update LMBs after LPM (Desnes A. Nunes do Rosario) [2004809]
- powerpc/numa: Consider the max NUMA node for migratable LPAR (Desnes A. Nunes do Rosario) [2004809]
- selftests: bpf: disable test_lirc_mode2 (Jiri Benc) [2006359]
- selftests: bpf: disable test_doc_build.sh (Jiri Benc) [2006359]
- selftests: bpf: define SO_RCVTIMEO and SO_SNDTIMEO properly for ppc64le (Jiri Benc) [2006359]
- selftests: bpf: skip FOU tests in test_tc_tunnel (Jiri Benc) [2006359]
- selftests: bpf: disable test_seg6_loop test (Jiri Benc) [2006359]
- selftests: bpf: disable test_lwt_seg6local (Jiri Benc) [2006359]
- selftests: bpf: disable test_bpftool_build.sh (Jiri Benc) [2006359]
- selftests: add option to skip specific tests in RHEL (Jiri Benc) [2006359]

* Fri Oct 15 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-8.el9]
- selftests/powerpc: Add scv versions of the basic TM syscall tests (Desnes A. Nunes do Rosario) [1986651]
- powerpc/64s: system call scv tabort fix for corrupt irq soft-mask state (Desnes A. Nunes do Rosario) [1986651]
- mm/swap: consider max pages in iomap_swapfile_add_extent (Carlos Maiolino) [2005191]
- platform/x86/intel: pmc/core: Add GBE Package C10 fix for Alder Lake PCH (David Arcari) [2007707]
- platform/x86/intel: pmc/core: Add Alder Lake low power mode support for pmc core (David Arcari) [2007707]
- platform/x86/intel: pmc/core: Add Latency Tolerance Reporting (LTR) support to Alder Lake (David Arcari) [2007707]
- platform/x86/intel: pmc/core: Add Alderlake support to pmc core driver (David Arcari) [2007707]
- platform/x86: intel_pmc_core: Move to intel sub-directory (David Arcari) [2007707]
- platform/x86: intel_pmc_core: Prevent possibile overflow (David Arcari) [2007707]
- Clean-up CONFIG_X86_PLATFORM_DRIVERS_INTEL (David Arcari) [2007707]
- KVM: nVMX: Filter out all unsupported controls when eVMCS was activated (Vitaly Kuznetsov) [2001912]
- ipc: remove memcg accounting for sops objects in do_semtimedop() (Rafael Aquini) [1999707] {CVE-2021-3759}
- memcg: enable accounting of ipc resources (Rafael Aquini) [1999707] {CVE-2021-3759}
- redhat: BUILDID parameter must come last in genspec.sh (Herton R. Krzesinski)
- redhat/Makefile.variables: Set INCLUDE_FEDORA_FILES to 0 (Prarit Bhargava) [2009545]
- redhat: Remove fedora configs directories and files. (Prarit Bhargava) [2009545]
- redhat/kernel.spec.template: Cleanup source numbering (Prarit Bhargava) [2009545]
- redhat/kernel.spec.template: Reorganize RHEL and Fedora specific files (Prarit Bhargava) [2009545]
- redhat/kernel.spec.template: Add include_fedora and include_rhel variables (Prarit Bhargava) [2009545]
- redhat/Makefile: Make kernel-local global (Prarit Bhargava) [2009545]
- redhat/Makefile: Use flavors file (Prarit Bhargava) [2009545]

* Mon Oct 11 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-7.el9]
- redhat: Enable Nitro Enclaves driver on x86 for real (Vitaly Kuznetsov) [2011739]
- redhat/.gitignore: Add rhel9 KABI files (Prarit Bhargava) [2009489]
- hwmon: (k10temp) Add support for yellow carp (David Arcari) [1987069]
- hwmon: (k10temp) Rework the temperature offset calculation (David Arcari) [1987069]
- hwmon: (k10temp) Don't show Tdie for all Zen/Zen2/Zen3 CPU/APU (David Arcari) [1987069]
- hwmon: (k10temp) Add additional missing Zen2 and Zen3 APUs (David Arcari) [1987069]
- hwmon: (k10temp) support Zen3 APUs (David Arcari) [1987069]
- selinux,smack: fix subjective/objective credential use mixups (Ondrej Mosnacek) [2008145]
- redhat: kernel.spec: selftests: abort on build failure (Jiri Benc) [2004012]
- Revert "bpf, selftests: Disable tests that need clang13" (Jiri Benc) [2004012]
- selftests, bpf: Fix makefile dependencies on libbpf (Jiri Benc) [2004012]

* Fri Oct 08 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-6.el9]
- pinctrl: Bulk conversion to generic_handle_domain_irq() (David Arcari) [2000232]
- pinctrl: amd: Handle wake-up interrupt (David Arcari) [2000232]
- pinctrl: amd: Add irq field data (David Arcari) [2000232]
- Revert "redhat: define _rhel variable because pesign macro now needs it" (Jan Stancek)
- redhat: switch secureboot kernel image signing to release keys (Jan Stancek)
- redhat/configs: Disable FIREWIRE (Prarit Bhargava) [1871862]
- Enable e1000 in rhel9 as unsupported (Ken Cox) [2002344]

* Mon Oct 04 2021 Jan Stancek <jstancek@redhat.com> [5.14.0-1.6.1.el9]
- Revert "redhat: define _rhel variable because pesign macro now needs it" (Jan Stancek)
- redhat: switch secureboot kernel image signing to release keys (Jan Stancek)
- redhat/configs: Disable FIREWIRE (Prarit Bhargava) [1871862]
- Enable e1000 in rhel9 as unsupported (Ken Cox) [2002344]

* Thu Sep 30 2021 Herton R. Krzesinski <herton@redhat.com> [5.14.0-5.el9]
- redhat/configs: enable CONFIG_SQUASHFS_ZSTD which is already enabled in Fedora 34 (Tao Liu) [1998953]
- fs: dlm: fix return -EINTR on recovery stopped (Alexander Aring) [2004213]
- redhat: replace redhatsecureboot303 signing key with redhatsecureboot601 (Jan Stancek) [2002499]
- redhat: define _rhel variable because pesign macro now needs it (Jan Stancek) [2002499]
- redhat: drop certificates that were deprecated after GRUB's BootHole flaw (Jan Stancek) [1994849]
- redhat: correct file name of redhatsecurebootca1 (Jan Stancek) [2002499]
- redhat: align file names with names of signing keys for ppc and s390 (Jan Stancek) [2002499]
- redhat: restore sublevel in changelog (Jan Stancek)
- fs: dlm: avoid comms shutdown delay in release_lockspace (Alexander Aring) [1994749]
- redhat/configs: Enable CONFIG_BLK_CGROUP_IOLATENCY & CONFIG_BLK_CGROUP_FC_APPID (Waiman Long) [1996675]
- redhat/configs: remove conflicting SYSTEM_BLACKLIST_KEYRING (Bruno Meneguele) [2002350]
- Enable "inter server to server" NFSv4.2 COPY (Steve Dickson) [1487367]

* Wed Sep 29 2021 Jan Stancek <jstancek@redhat.com> [5.14.0-1.5.1.el9]
- fs: dlm: fix return -EINTR on recovery stopped (Alexander Aring) [2004213]
- redhat/configs: Update configs for secure IPL (Claudio Imbrenda) [1976884]
- redhat: replace redhatsecureboot303 signing key with redhatsecureboot601 (Jan Stancek) [2002499]
- redhat: define _rhel variable because pesign macro now needs it (Jan Stancek) [2002499]
- redhat: drop certificates that were deprecated after GRUB's BootHole flaw (Jan Stancek) [1994849]
- redhat: correct file name of redhatsecurebootca1 (Jan Stancek) [2002499]
- redhat: align file names with names of signing keys for ppc and s390 (Jan Stancek) [2002499]

* Mon Sep 27 2021 Jan Stancek <jstancek@redhat.com> [5.14.0-1.4.1.el9]
- redhat: restore sublevel in changelog (Jan Stancek)
- fs: dlm: avoid comms shutdown delay in release_lockspace (Alexander Aring) [1994749]
- redhat/configs: Enable CONFIG_BLK_CGROUP_IOLATENCY & CONFIG_BLK_CGROUP_FC_APPID (Waiman Long) [1996675]

* Wed Sep 22 2021 Herton R. Krzesinski <herton@redhat.com> [5.14-4.el9]
- Drivers: hv: vmbus: Fix kernel crash upon unbinding a device from uio_hv_generic driver (Vitaly Kuznetsov) [1999535]
- ipc: replace costly bailout check in sysvipc_find_ipc() (Rafael Aquini) [1987130 2003270] {CVE-2021-3669}
- redhat/configs: Disable CONFIG_DRM_VMWGFX on aarch64 (Michel Dänzer) [1996993]
- redhat: set USE_DIST_IN_SOURCE=1 for 9.0-beta (Jan Stancek)
- redhat: add option to use DIST tag in sources (Jan Stancek)
- CI: Enable notification messages for RHEL9 (Veronika Kabatova)
- CI: Enable private pipelines for RT branches (Veronika Kabatova)
- CI: Remove ARK leftovers (Veronika Kabatova)
- redhat: add *-matched meta packages to rpminspect emptyrpm config (Herton R. Krzesinski)
- gfs2: Don't call dlm after protocol is unmounted (Bob Peterson) [1988451]
- gfs2: don't stop reads while withdraw in progress (Bob Peterson) [1988451]
- gfs2: Mark journal inodes as "don't cache" (Bob Peterson) [1988451]
- cgroup/cpuset: Avoid memory migration when nodemasks match (Waiman Long) [1980430]
- cgroup/cpuset: Enable memory migration for cpuset v2 (Waiman Long) [1980430]
- iscsi_ibft: Fix isa_bus_to_virt not working under ARM (Maurizio Lombardi) [1963801]
- x86/setup: Explicitly include acpi.h (Maurizio Lombardi) [1963801]
- iscsi_ibft: fix warning in reserve_ibft_region() (Maurizio Lombardi) [1963801]
- iscsi_ibft: fix crash due to KASLR physical memory remapping (Maurizio Lombardi) [1963801]
- redhat: fix chronological order in the changelog file (Herton R. Krzesinski)

* Wed Sep 22 2021 Jan Stancek <jstancek@redhat.com> [5.14.0-1.3.1.el9]
- redhat/configs: remove conflicting SYSTEM_BLACKLIST_KEYRING (Bruno Meneguele) [2002350]
- Enable "inter server to server" NFSv4.2 COPY (Steve Dickson) [1487367]

* Fri Sep 17 2021 Jan Stancek <jstancek@redhat.com> [5.14-1.2.1.el9]
- redhat/configs: Disable CONFIG_DRM_VMWGFX on aarch64 (Michel Dänzer) [1996993]
- redhat: set USE_DIST_IN_SOURCE=1 for 9.0-beta (Jan Stancek)
- redhat: add option to use DIST tag in sources (Jan Stancek)
- CI: Enable notification messages for RHEL9 (Veronika Kabatova)
- CI: Enable private pipelines for RT branches (Veronika Kabatova)
- CI: Remove ARK leftovers (Veronika Kabatova)
- redhat: add *-matched meta packages to rpminspect emptyrpm config (Herton R. Krzesinski)
- gfs2: Don't call dlm after protocol is unmounted (Bob Peterson) [1988451]
- gfs2: don't stop reads while withdraw in progress (Bob Peterson) [1988451]
- gfs2: Mark journal inodes as "don't cache" (Bob Peterson) [1988451]
- cgroup/cpuset: Avoid memory migration when nodemasks match (Waiman Long) [1980430]
- cgroup/cpuset: Enable memory migration for cpuset v2 (Waiman Long) [1980430]
- iscsi_ibft: Fix isa_bus_to_virt not working under ARM (Maurizio Lombardi) [1963801]
- x86/setup: Explicitly include acpi.h (Maurizio Lombardi) [1963801]
- iscsi_ibft: fix warning in reserve_ibft_region() (Maurizio Lombardi) [1963801]
- iscsi_ibft: fix crash due to KASLR physical memory remapping (Maurizio Lombardi) [1963801]

* Thu Sep 16 2021 Herton R. Krzesinski <herton@redhat.com> [5.14-3]
- misc/pvpanic-pci: Allow automatic loading (Eric Auger) [1977192]
- md/raid10: Remove unnecessary rcu_dereference in raid10_handle_discard (Nigel Croxon) [1965294]
- rcu: Avoid unneeded function call in rcu_read_unlock() (Waiman Long) [1998549]
- Enable bridge jobs for scratch pipelines (Michael Hofmann)
- CI: use 9.0-beta-rt branch for -rt pipeline (Jan Stancek)
- crypto: ccp - Add support for new CCP/PSP device ID (Vladis Dronov) [1987099]
- crypto: ccp - shutdown SEV firmware on kexec (Vladis Dronov) [1987099]

* Tue Sep 14 2021 Jan Stancek <jstancek@redhat.com> [5.14-1.1.1]
- md/raid10: Remove unnecessary rcu_dereference in raid10_handle_discard (Nigel Croxon) [1965294]
- rcu: Avoid unneeded function call in rcu_read_unlock() (Waiman Long) [1998549]

* Mon Sep 13 2021 Herton R. Krzesinski <herton@redhat.com> [5.14-2]
- redhat: update branches/targets after 9 Beta fork (Herton R. Krzesinski)
- hv_utils: Set the maximum packet size for VSS driver to the length of the receive buffer (Vitaly Kuznetsov) [1996628]
- Enable bridge jobs for scratch pipelines (Michael Hofmann)

* Mon Aug 30 2021 Herton R. Krzesinski <herton@redhat.com> [5.14-1]
- redhat: drop Patchlist.changelog for RHEL (Jan Stancek) [1997494]
- redhat: update Makefile.variables for centos/rhel9 fork (Herton R. Krzesinski)
- redhat: add support for stream profile in koji/brew (Herton R. Krzesinski)
- redhat: make DIST default to .el9 (Herton R. Krzesinski)
- redhat: set default values in Makefiles for RHEL 9 Beta (Jan Stancek) [1997494]
- arm64: use common CONFIG_MAX_ZONEORDER for arm kernel (Mark Salter)
- Create Makefile.variables for a single point of configuration change (Justin M. Forbes)
- rpmspec: drop traceevent files instead of just excluding them from files list (Herton R. Krzesinski) [1967640]
- redhat/config: Enablement of CONFIG_PAPR_SCM for PowerPC (Gustavo Walbon) [1962936]
- Attempt to fix Intel PMT code (David Arcari)
- CI: Enable realtime branch testing (Veronika Kabatova)
- CI: Enable realtime checks for c9s and RHEL9 (Veronika Kabatova)
- [fs] dax: mark tech preview (Bill O'Donnell)
- ark: wireless: enable all rtw88 pcie wirless variants (Peter Robinson)
- wireless: rtw88: move debug options to common/debug (Peter Robinson)
- fedora: minor PTP clock driver cleanups (Peter Robinson)
- common: x86: enable VMware PTP support on ark (Peter Robinson)
- arm64: dts: rockchip: Disable CDN DP on Pinebook Pro (Matthias Brugger)
- arm64: dts: rockchip: Setup USB typec port as datarole on (Dan Johansen)
- [scsi] megaraid_sas: re-add certain pci-ids (Tomas Henzl)
- xfs: drop experimental warnings for bigtime and inobtcount (Bill O'Donnell) [1995321]
- Disable liquidio driver on ark/rhel (Herton R. Krzesinski) [1993393]
- More Fedora config updates (Justin M. Forbes)
- Fedora config updates for 5.14 (Justin M. Forbes)
- CI: Rename ARK CI pipeline type (Veronika Kabatova)
- CI: Finish up c9s config (Veronika Kabatova)
- CI: Update ppc64le config (Veronika Kabatova)
- CI: use more templates (Veronika Kabatova)
- Filter updates for aarch64 (Justin M. Forbes)
- increase CONFIG_NODES_SHIFT for aarch64 (Chris von Recklinghausen) [1890304]
- redhat: configs: Enable CONFIG_WIRELESS_HOTKEY (Hans de Goede)
- redhat/configs: Update CONFIG_NVRAM (Desnes A. Nunes do Rosario) [1988254]
- common: serial: build in SERIAL_8250_LPSS for x86 (Peter Robinson)
- powerpc: enable CONFIG_FUNCTION_PROFILER (Diego Domingos) [1831065]
- crypto: rng - Override drivers/char/random in FIPS mode (Herbert Xu)
- random: Add hook to override device reads and getrandom(2) (Herbert Xu)
- redhat/configs: Disable Soft-RoCE driver (Kamal Heib)
- redhat/configs/evaluate_configs: Update help output (Prarit Bhargava)
- redhat/configs: Double MAX_LOCKDEP_CHAINS (Justin M. Forbes)
- fedora: configs: Fix WM5102 Kconfig (Hans de Goede)
- powerpc: enable CONFIG_POWER9_CPU (Diego Domingos) [1876436]
- redhat/configs: Fix CONFIG_VIRTIO_IOMMU to 'y' on aarch64 (Eric Auger) [1972795]
- filter-modules.sh: add more sound modules to filter (Jaroslav Kysela)
- redhat/configs: sound configuration cleanups and updates (Jaroslav Kysela)
- common: Update for CXL (Compute Express Link) configs (Peter Robinson)
- redhat: configs: disable CRYPTO_SM modules (Herton R. Krzesinski) [1990040]
- Remove fedora version of the LOCKDEP_BITS, we should use common (Justin M. Forbes)
- Re-enable sermouse for x86 (rhbz 1974002) (Justin M. Forbes)
- Fedora 5.14 configs round 1 (Justin M. Forbes)
- redhat: add gating configuration for centos stream/rhel9 (Herton R. Krzesinski)
- x86: configs: Enable CONFIG_TEST_FPU for debug kernels (Vitaly Kuznetsov) [1988384]
- redhat/configs: Move CHACHA and POLY1305 to core kernel to allow BIG_KEYS=y (root) [1983298]
- kernel.spec: fix build of samples/bpf (Jiri Benc)
- Enable OSNOISE_TRACER and TIMERLAT_TRACER (Jerome Marchand) [1979379]
- rpmspec: switch iio and gpio tools to use tools_make (Herton R. Krzesinski) [1956988]
- configs/process_configs.sh: Handle config items with no help text (Patrick Talbert)
- fedora: sound config updates for 5.14 (Peter Robinson)
- fedora: Only enable FSI drivers on POWER platform (Peter Robinson)
- The CONFIG_RAW_DRIVER has been removed from upstream (Peter Robinson)
- fedora: updates for 5.14 with a few disables for common from pending (Peter Robinson)
- fedora: migrate from MFD_TPS68470 -> INTEL_SKL_INT3472 (Peter Robinson)
- fedora: Remove STAGING_GASKET_FRAMEWORK (Peter Robinson)
- Fedora: move DRM_VMWGFX configs from ark -> common (Peter Robinson)
- fedora: arm: disabled unused FB drivers (Peter Robinson)
- fedora: don't enable FB_VIRTUAL (Peter Robinson)
- redhat/configs: Double MAX_LOCKDEP_ENTRIES (Waiman Long) [1940075]
- rpmspec: fix verbose output on kernel-devel installation (Herton R. Krzesinski) [1981406]
- Build Fedora x86s kernels with bytcr-wm5102 (Marius Hoch)
- Deleted redhat/configs/fedora/generic/x86/CONFIG_FB_HYPERV (Patrick Lang)
- rpmspec: correct the ghost initramfs attributes (Herton R. Krzesinski) [1977056]
- rpmspec: amend removal of depmod created files to include modules.builtin.alias.bin (Herton R. Krzesinski) [1977056]
- configs: remove duplicate CONFIG_DRM_HYPERV file (Patrick Talbert)
- CI: use common code for merge and release (Don Zickus)
- rpmspec: add release string to kernel doc directory name (Jan Stancek)
- redhat/configs: Add CONFIG_INTEL_PMT_CRASHLOG (Michael Petlan) [1880486]
- redhat/configs: Add CONFIG_INTEL_PMT_TELEMETRY (Michael Petlan) [1880486]
- redhat/configs: Add CONFIG_MFD_INTEL_PMT (Michael Petlan) [1880486]
- redhat/configs: enable CONFIG_BLK_DEV_ZONED (Ming Lei) [1638087]
- Add --with clang_lto option to build the kernel with Link Time Optimizations (Tom Stellard)
- common: disable DVB_AV7110 and associated pieces (Peter Robinson)
- Fix fedora-only config updates (Don Zickus)
- Fedor config update for new option (Justin M. Forbes)
- redhat/configs: Enable stmmac NIC for x86_64 (Mark Salter)
- all: hyperv: use the DRM driver rather than FB (Peter Robinson)
- all: hyperv: unify the Microsoft HyperV configs (Peter Robinson)
- all: VMWare: clean up VMWare configs (Peter Robinson)
- Update CONFIG_ARM_FFA_TRANSPORT (Patrick Talbert)
- CI: Handle all mirrors (Veronika Kabatova)
- Turn on CONFIG_STACKTRACE for s390x zfpcdump kernels (Justin M. Forbes)
- arm64: switch ark kernel to 4K pagesize (Mark Salter)
- Disable AMIGA_PARTITION and KARMA_PARTITION (Prarit Bhargava) [1802694]
- all: unify and cleanup i2c TPM2 modules (Peter Robinson)
- redhat/configs: Set CONFIG_VIRTIO_IOMMU on aarch64 (Eric Auger) [1972795]
- redhat/configs: Disable CONFIG_RT_GROUP_SCHED in rhel config (Phil Auld)
- redhat/configs: enable KEXEC_SIG which is already enabled in RHEL8 for s390x and x86_64 (Coiby Xu) [1976835]
- rpmspec: do not BuildRequires bpftool on noarch (Herton R. Krzesinski)
- redhat/configs: disable {IMA,EVM}_LOAD_X509 (Bruno Meneguele) [1977529]
- redhat: add secureboot CA certificate to trusted kernel keyring (Bruno Meneguele)
- redhat/configs: enable IMA_ARCH_POLICY for aarch64 and s390x (Bruno Meneguele)
- redhat/configs: Enable CONFIG_MLXBF_GIGE on aarch64 (Alaa Hleihel) [1858599]
- common: enable STRICT_MODULE_RWX everywhere (Peter Robinson)
- COMMON_CLK_STM32MP157_SCMI is bool and selects COMMON_CLK_SCMI (Justin M. Forbes)
- kernel.spec: Add kernel{,-debug}-devel-matched meta packages (Timothée Ravier)
- Turn off with_selftests for Fedora (Justin M. Forbes)
- Don't build bpftool on Fedora (Justin M. Forbes)
- Fix location of syscall scripts for kernel-devel (Justin M. Forbes)
- fedora: arm: Enable some i.MX8 options (Peter Robinson)
- Enable Landlock for Fedora (Justin M. Forbes)
- Filter update for Fedora aarch64 (Justin M. Forbes)
- rpmspec: only build debug meta packages where we build debug ones (Herton R. Krzesinski)
- rpmspec: do not BuildRequires bpftool on nobuildarches (Herton R. Krzesinski)
- redhat/configs: Consolidate CONFIG_HMC_DRV in the common s390x folder (Thomas Huth) [1976270]
- redhat/configs: Consolidate CONFIG_EXPOLINE_OFF in the common folder (Thomas Huth) [1976270]
- redhat/configs: Move CONFIG_HW_RANDOM_S390 into the s390x/ subfolder (Thomas Huth) [1976270]
- redhat/configs: Disable CONFIG_HOTPLUG_PCI_SHPC in the Fedora settings (Thomas Huth) [1976270]
- redhat/configs: Remove the non-existent CONFIG_NO_BOOTMEM switch (Thomas Huth) [1976270]
- redhat/configs: Compile the virtio-console as a module on s390x (Thomas Huth) [1976270]
- redhat/configs: Enable CONFIG_S390_CCW_IOMMU and CONFIG_VFIO_CCW for ARK, too (Thomas Huth) [1976270]
- Revert "Merge branch 'ec_fips' into 'os-build'" (Vladis Dronov) [1947240]
- Fix typos in fedora filters (Justin M. Forbes)
- More filtering for Fedora (Justin M. Forbes)
- Fix Fedora module filtering for spi-altera-dfl (Justin M. Forbes)
- Fedora 5.13 config updates (Justin M. Forbes)
- fedora: cleanup TCG_TIS_I2C_CR50 (Peter Robinson)
- fedora: drop duplicate configs (Peter Robinson)
- More Fedora config updates for 5.13 (Justin M. Forbes)
- redhat/configs: Enable needed drivers for BlueField SoC on aarch64 (Alaa Hleihel) [1858592 1858594 1858596]
- redhat: Rename mod-blacklist.sh to mod-denylist.sh (Prarit Bhargava)
- redhat/configs: enable CONFIG_NET_ACT_MPLS (Marcelo Ricardo Leitner)
- configs: Enable CONFIG_DEBUG_KERNEL for zfcpdump (Jiri Olsa)
- kernel.spec: Add support to use vmlinux.h (Don Zickus)
- spec: Add vmlinux.h to kernel-devel package (Jiri Olsa)
- Turn off DRM_XEN_FRONTEND for Fedora as we had DRM_XEN off already (Justin M. Forbes)
- Fedora 5.13 config updates pt 3 (Justin M. Forbes)
- all: enable ath11k wireless modules (Peter Robinson)
- all: Enable WWAN and associated MHI bus pieces (Peter Robinson)
- spec: Enable sefltests rpm build (Jiri Olsa)
- spec: Allow bpf selftest/samples to fail (Jiri Olsa)
- bpf, selftests: Disable tests that need clang13 (Toke Høiland-Jørgensen)
- kvm: Add kvm_stat.service file and kvm_stat logrotate config to the tools (Jiri Benc)
- kernel.spec: Add missing source files to kernel-selftests-internal (Jiri Benc)
- kernel.spec: selftests: add net/forwarding to TARGETS list (Jiri Benc)
- kernel.spec: selftests: add build requirement on libmnl-devel (Jiri Benc)
- kernel.spec: add action.o to kernel-selftests-internal (Jiri Benc)
- kernel.spec: avoid building bpftool repeatedly (Jiri Benc)
- kernel.spec: selftests require python3 (Jiri Benc)
- kernel.spec: skip selftests that failed to build (Jiri Benc)
- kernel.spec: fix installation of bpf selftests (Jiri Benc)
- redhat: fix samples and selftests make options (Jiri Benc)
- kernel.spec: enable mptcp selftests for kernel-selftests-internal (Jiri Benc)
- kernel.spec: Do not export shared objects from libexecdir to RPM Provides (Jiri Benc)
- kernel.spec: add missing dependency for the which package (Jiri Benc)
- kernel.spec: add netfilter selftests to kernel-selftests-internal (Jiri Benc)
- kernel.spec: move slabinfo and page_owner_sort debuginfo to tools-debuginfo (Jiri Benc)
- kernel.spec: package and ship VM tools (Jiri Benc)
- configs: enable CONFIG_PAGE_OWNER (Jiri Benc)
- kernel.spec: add coreutils (Jiri Benc)
- kernel.spec: add netdevsim driver selftests to kernel-selftests-internal (Jiri Benc)
- redhat/Makefile: Clean out the --without flags from the baseonly rule (Jiri Benc)
- kernel.spec: Stop building unnecessary rpms for baseonly builds (Jiri Benc)
- kernel.spec: disable more kabi switches for gcov build (Jiri Benc)
- kernel.spec: Rename kabi-dw base (Jiri Benc)
- kernel.spec: Fix error messages during build of zfcpdump kernel (Jiri Benc)
- kernel.spec: perf: remove bpf examples (Jiri Benc)
- kernel.spec: selftests should not depend on modules-internal (Jiri Benc)
- kernel.spec: build samples (Jiri Benc)
- kernel.spec: tools: sync missing options with RHEL 8 (Jiri Benc)
- redhat/configs: nftables: Enable extra flowtable symbols (Phil Sutter)
- redhat/configs: Sync netfilter options with RHEL8 (Phil Sutter)
- Fedora 5.13 config updates pt 2 (Justin M. Forbes)
- Move CONFIG_ARCH_INTEL_SOCFPGA up a level for Fedora (Justin M. Forbes)
- fedora: enable the Rockchip rk3399 pcie drivers (Peter Robinson)
- Fedora 5.13 config updates pt 1 (Justin M. Forbes)
- Fix version requirement from opencsd-devel buildreq (Justin M. Forbes)
- configs/ark/s390: set CONFIG_MARCH_Z14 and CONFIG_TUNE_Z15 (Philipp Rudo) [1876435]
- configs/common/s390: Clean up CONFIG_{MARCH,TUNE}_Z* (Philipp Rudo)
- configs/process_configs.sh: make use of dummy-tools (Philipp Rudo)
- configs/common: disable CONFIG_INIT_STACK_ALL_{PATTERN,ZERO} (Philipp Rudo)
- configs/common/aarch64: disable CONFIG_RELR (Philipp Rudo)
- redhat/config: enable STMICRO nic for RHEL (Mark Salter)
- redhat/configs: Enable ARCH_TEGRA on RHEL (Mark Salter)
- redhat/configs: enable IMA_KEXEC for supported arches (Bruno Meneguele)
- redhat/configs: enable INTEGRITY_SIGNATURE to all arches (Bruno Meneguele)
- configs: enable CONFIG_LEDS_BRIGHTNESS_HW_CHANGED (Benjamin Tissoires)
- RHEL: disable io_uring support (Jeff Moyer)
- all: Changing CONFIG_UV_SYSFS to build uv_sysfs.ko as a loadable module. (Frank Ramsay)
- Enable NITRO_ENCLAVES on RHEL (Vitaly Kuznetsov)
- Update the Quick Start documentation (David Ward)
- redhat/configs: Set PVPANIC_MMIO for x86 and PVPANIC_PCI for aarch64 (Eric Auger) [1961178]
- bpf: Fix unprivileged_bpf_disabled setup (Jiri Olsa)
- Enable CONFIG_BPF_UNPRIV_DEFAULT_OFF (Jiri Olsa)
- configs/common/s390: disable CONFIG_QETH_{OSN,OSX} (Philipp Rudo) [1903201]
- nvme: nvme_mpath_init remove multipath check (Mike Snitzer)
- team: mark team driver as deprecated (Hangbin Liu) [1945477]
- Make CRYPTO_EC also builtin (Simo Sorce) [1947240]
- Do not hard-code a default value for DIST (David Ward)
- Override %%{debugbuildsenabled} if the --with-release option is used (David Ward)
- Improve comments in SPEC file, and move some option tests and macros (David Ward)
- configs: enable CONFIG_EXFAT_FS (Pavel Reichl) [1943423]
- Revert s390x/zfcpdump part of a9d179c40281 and ecbfddd98621 (Vladis Dronov)
- Embed crypto algos, modes and templates needed in the FIPS mode (Vladis Dronov) [1947240]
- configs: Add and enable CONFIG_HYPERV_TESTING for debug kernels (Mohammed Gamal)
- mm/cma: mark CMA on x86_64 tech preview and print RHEL-specific infos (David Hildenbrand) [1945002]
- configs: enable CONFIG_CMA on x86_64 in ARK (David Hildenbrand) [1945002]
- rpmspec: build debug-* meta-packages if debug builds are disabled (Herton R. Krzesinski)
- UIO: disable unused config options (Aristeu Rozanski) [1957819]
- ARK-config: Make amd_pinctrl module builtin (Hans de Goede)
- rpmspec: revert/drop content hash for kernel-headers (Herton R. Krzesinski)
- rpmspec: fix check that calls InitBuildVars (Herton R. Krzesinski)
- fedora: enable zonefs (Damien Le Moal)
- redhat: load specific ARCH keys to INTEGRITY_PLATFORM_KEYRING (Bruno Meneguele)
- redhat: enable INTEGRITY_TRUSTED_KEYRING across all variants (Bruno Meneguele)
- redhat: enable SYSTEM_BLACKLIST_KEYRING across all variants (Bruno Meneguele)
- redhat: enable INTEGRITY_ASYMMETRIC_KEYS across all variants (Bruno Meneguele)
- Remove unused boot loader specification files (David Ward)
- redhat/configs: Enable mlx5 IPsec and TLS offloads (Alaa Hleihel) [1869674 1957636]
- Force DWARF4 because crash does not support DWARF5 yet (Justin M. Forbes)
- common: disable Apple Silicon generally (Peter Robinson)
- cleanup Intel's FPGA configs (Peter Robinson)
- common: move PTP KVM support from ark to common (Peter Robinson)
- Enable CONFIG_DRM_AMDGPU_USERPTR for everyone (Justin M. Forbes)
- redhat: add initial rpminspect configuration (Herton R. Krzesinski)
- fedora: arm updates for 5.13 (Peter Robinson)
- fedora: Enable WWAN and associated MHI bits (Peter Robinson)
- Update CONFIG_MODPROBE_PATH to /usr/sbin (Justin Forbes)
- Fedora set modprobe path (Justin M. Forbes)
- Keep sctp and l2tp modules in modules-extra (Don Zickus)
- Fix ppc64le cross build packaging (Don Zickus)
- Fedora: Make amd_pinctrl module builtin (Hans de Goede)
- Keep CONFIG_KASAN_HW_TAGS off for aarch64 debug configs (Justin M. Forbes)
- New configs in drivers/bus (Fedora Kernel Team)
- RHEL: Don't build KVM PR module on ppc64 (David Gibson) [1930649]
- Flip CONFIG_USB_ROLE_SWITCH from m to y (Justin M. Forbes)
- Set valid options for CONFIG_FW_LOADER_USER_HELPER (Justin M. Forbes)
- Clean up CONFIG_FB_MODE_HELPERS (Justin M. Forbes)
- Turn off CONFIG_VFIO for the s390x zfcpdump kernel (Justin M. Forbes)
- Delete unused CONFIG_SND_SOC_MAX98390 pending-common (Justin M. Forbes)
- Update pending-common configs, preparing to set correctly (Justin M. Forbes)
- Update fedora filters for surface (Justin M. Forbes)
- Build CONFIG_CRYPTO_ECDSA inline for s390x zfcpdump (Justin M. Forbes)
- Replace "flavour" where "variant" is meant instead (David Ward)
- Drop the %%{variant} macro and fix --with-vanilla (David Ward)
- Fix syntax of %%kernel_variant_files (David Ward)
- Change description of --without-vdso-install to fix typo (David Ward)
- Config updates to work around mismatches (Justin M. Forbes)
- CONFIG_SND_SOC_FSL_ASOC_CARD selects CONFIG_MFD_WM8994 now (Justin M. Forbes)
- wireguard: disable in FIPS mode (Hangbin Liu) [1940794]
- Enable mtdram for fedora (rhbz 1955916) (Justin M. Forbes)
- Remove reference to bpf-helpers man page (Justin M. Forbes)
- Fedora: enable more modules for surface devices (Dave Olsthoorn)
- Fix Fedora config mismatch for CONFIG_FSL_ENETC_IERB (Justin M. Forbes)
- hardlink is in /usr/bin/ now (Justin M. Forbes)
- Ensure CONFIG_KVM_BOOK3S_64_PR stays on in Fedora, even if it is turned off in RHEL (Justin M. Forbes)
- Set date in package release from repository commit, not system clock (David Ward)
- Use a better upstream tarball filename for snapshots (David Ward)
- Don't create empty pending-common files on pending-fedora commits (Don Zickus)
- nvme: decouple basic ANA log page re-read support from native multipathing (Mike Snitzer)
- nvme: allow local retry and proper failover for REQ_FAILFAST_TRANSPORT (Mike Snitzer)
- nvme: Return BLK_STS_TARGET if the DNR bit is set (Mike Snitzer)
- Add redhat/configs/pending-common/generic/s390x/zfcpdump/CONFIG_NETFS_SUPPORT (Justin M. Forbes)
- Create ark-latest branch last for CI scripts (Don Zickus)
- Replace /usr/libexec/platform-python with /usr/bin/python3 (David Ward)
- Turn off ADI_AXI_ADC and AD9467 which now require CONFIG_OF (Justin M. Forbes)
- Export ark infrastructure files (Don Zickus)
- docs: Update docs to reflect newer workflow. (Don Zickus)
- Use upstream/master for merge-base with fallback to master (Don Zickus)
- Fedora: Turn off the SND_INTEL_BYT_PREFER_SOF option (Hans de Goede)
- filter-modules.sh.fedora: clean up "netprots" (Paul Bolle)
- filter-modules.sh.fedora: clean up "scsidrvs" (Paul Bolle)
- filter-*.sh.fedora: clean up "ethdrvs" (Paul Bolle)
- filter-*.sh.fedora: clean up "driverdirs" (Paul Bolle)
- filter-*.sh.fedora: remove incorrect entries (Paul Bolle)
- filter-*.sh.fedora: clean up "singlemods" (Paul Bolle)
- filter-modules.sh.fedora: drop unused list "iiodrvs" (Paul Bolle)
- Update mod-internal to fix depmod issue (Nico Pache)
- Turn on CONFIG_VDPA_SIM_NET (rhbz 1942343) (Justin M. Forbes)
- New configs in drivers/power (Fedora Kernel Team)
- Turn on CONFIG_NOUVEAU_DEBUG_PUSH for debug configs (Justin M. Forbes)
- Turn off KFENCE sampling by default for Fedora (Justin M. Forbes)
- Fedora config updates round 2 (Justin M. Forbes)
- New configs in drivers/soc (Jeremy Cline)
- filter-modules.sh: Fix copy/paste error 'input' (Paul Bolle)
- Update module filtering for 5.12 kernels (Justin M. Forbes)
- Fix genlog.py to ensure that comments retain "%%" characters. (Mark Mielke)
- New configs in drivers/leds (Fedora Kernel Team)
- Limit CONFIG_USB_CDNS_SUPPORT to x86_64 and arm in Fedora (David Ward)
- Fedora: Enable CHARGER_GPIO on aarch64 too (Peter Robinson)
- Fedora config updates (Justin M. Forbes)
- wireguard: mark as Tech Preview (Hangbin Liu) [1613522]
- configs: enable CONFIG_WIREGUARD in ARK (Hangbin Liu) [1613522]
- Remove duplicate configs acroos fedora, ark and common (Don Zickus)
- Combine duplicate configs across ark and fedora into common (Don Zickus)
- common/ark: cleanup and unify the parport configs (Peter Robinson)
- iommu/vt-d: enable INTEL_IDXD_SVM for both fedora and rhel (Jerry Snitselaar)
- REDHAT: coresight: etm4x: Disable coresight on HPE Apollo 70 (Jeremy Linton)
- configs/common/generic: disable CONFIG_SLAB_MERGE_DEFAULT (Rafael Aquini)
- Remove _legacy_common_support (Justin M. Forbes)
- redhat/mod-blacklist.sh: Fix floppy blacklisting (Hans de Goede)
- New configs in fs/pstore (CKI@GitLab)
- New configs in arch/powerpc (Fedora Kernel Team)
- configs: enable BPF LSM on Fedora and ARK (Ondrej Mosnacek)
- configs: clean up LSM configs (Ondrej Mosnacek)
- New configs in drivers/platform (CKI@GitLab)
- New configs in drivers/firmware (CKI@GitLab)
- New configs in drivers/mailbox (Fedora Kernel Team)
- New configs in drivers/net/phy (Justin M. Forbes)
- Update CONFIG_DM_MULTIPATH_IOA (Augusto Caringi)
- New configs in mm/Kconfig (CKI@GitLab)
- New configs in arch/powerpc (Jeremy Cline)
- New configs in arch/powerpc (Jeremy Cline)
- New configs in drivers/input (Fedora Kernel Team)
- New configs in net/bluetooth (Justin M. Forbes)
- New configs in drivers/clk (Fedora Kernel Team)
- New configs in init/Kconfig (Jeremy Cline)
- redhat: allow running fedora-configs and rh-configs targets outside of redhat/ (Herton R. Krzesinski)
- all: unify the disable of goldfish (android emulation platform) (Peter Robinson)
- common: minor cleanup/de-dupe of dma/dmabuf debug configs (Peter Robinson)
- common/ark: these drivers/arches were removed in 5.12 (Peter Robinson)
- Correct kernel-devel make prepare build for 5.12. (Paulo E. Castro)
- redhat: add initial support for centos stream dist-git sync on Makefiles (Herton R. Krzesinski)
- redhat/configs: Enable CONFIG_SCHED_STACK_END_CHECK for Fedora and ARK (Josh Poimboeuf) [1856174]
- CONFIG_VFIO now selects IOMMU_API instead of depending on it, causing several config mismatches for the zfcpdump kernel (Justin M. Forbes)
- Turn off weak-modules for Fedora (Justin M. Forbes)
- redhat: enable CONFIG_FW_LOADER_COMPRESS for ARK (Herton R. Krzesinski) [1939095]
- Fedora: filters: update to move dfl-emif to modules (Peter Robinson)
- drop duplicate DEVFREQ_GOV_SIMPLE_ONDEMAND config (Peter Robinson)
- efi: The EFI_VARS is legacy and now x86 only (Peter Robinson)
- common: enable RTC_SYSTOHC to supplement update_persistent_clock64 (Peter Robinson)
- generic: arm: enable SCMI for all options (Peter Robinson)
- fedora: the PCH_CAN driver is x86-32 only (Peter Robinson)
- common: disable legacy CAN device support (Peter Robinson)
- common: Enable Microchip MCP251x/MCP251xFD CAN controllers (Peter Robinson)
- common: Bosch MCAN support for Intel Elkhart Lake (Peter Robinson)
- common: enable CAN_PEAK_PCIEFD PCI-E driver (Peter Robinson)
- common: disable CAN_PEAK_PCIEC PCAN-ExpressCard (Peter Robinson)
- common: enable common CAN layer 2 protocols (Peter Robinson)
- ark: disable CAN_LEDS option (Peter Robinson)
- Fedora: Turn on SND_SOC_INTEL_SKYLAKE_HDAUDIO_CODEC option (Hans de Goede)
- Fedora: enable modules for surface devices (Dave Olsthoorn)
- Turn on SND_SOC_INTEL_SOUNDWIRE_SOF_MACH for Fedora again (Justin M. Forbes)
- common: fix WM8804 codec dependencies (Peter Robinson)
- Build SERIO_SERPORT as a module (Peter Robinson)
- input: touchscreen: move ELO and Wacom serial touchscreens to x86 (Peter Robinson)
- Sync serio touchscreens for non x86 architectures to the same as ARK (Peter Robinson)
- Only enable SERIO_LIBPS2 on x86 (Peter Robinson)
- Only enable PC keyboard controller and associated keyboard on x86 (Peter Robinson)
- Generic: Mouse: Tweak generic serial mouse options (Peter Robinson)
- Only enable PS2 Mouse options on x86 (Peter Robinson)
- Disable bluetooth highspeed by default (Peter Robinson)
- Fedora: A few more general updates for 5.12 window (Peter Robinson)
- Fedora: Updates for 5.12 merge window (Peter Robinson)
- Fedora: remove dead options that were removed upstream (Peter Robinson)
- redhat: remove CONFIG_DRM_PANEL_XINGBANGDA_XBD599 (Herton R. Krzesinski)
- New configs in arch/powerpc (Fedora Kernel Team)
- Turn on CONFIG_PPC_QUEUED_SPINLOCKS as it is default upstream now (Justin M. Forbes)
- Update pending-common configs to address new upstream config deps (Justin M. Forbes)
- rpmspec: ship gpio-watch.debug in the proper debuginfo package (Herton R. Krzesinski)
- Removed description text as a comment confuses the config generation (Justin M. Forbes)
- New configs in drivers/dma-buf (Jeremy Cline)
- Fedora: ARMv7: build for 16 CPUs. (Peter Robinson)
- Fedora: only enable DEBUG_HIGHMEM on debug kernels (Peter Robinson)
- process_configs.sh: fix find/xargs data flow (Ondrej Mosnacek)
- Fedora config update (Justin M. Forbes)
- fedora: minor arm sound config updates (Peter Robinson)
- Fix trailing white space in redhat/configs/fedora/generic/CONFIG_SND_INTEL_BYT_PREFER_SOF (Justin M. Forbes)
- Add a redhat/rebase-notes.txt file (Hans de Goede)
- Turn on SND_INTEL_BYT_PREFER_SOF for Fedora (Hans de Goede)
- CI: Drop MR ID from the name variable (Veronika Kabatova)
- redhat: add DUP and kpatch certificates to system trusted keys for RHEL build (Herton R. Krzesinski)
- The comments in CONFIG_USB_RTL8153_ECM actually turn off CONFIG_USB_RTL8152 (Justin M. Forbes)
- Update CKI pipeline project (Veronika Kabatova)
- Turn off additional KASAN options for Fedora (Justin M. Forbes)
- Rename the master branch to rawhide for Fedora (Justin M. Forbes)
- Makefile targets for packit integration (Ben Crocker)
- Turn off KASAN for rawhide debug builds (Justin M. Forbes)
- New configs in arch/arm64 (Justin Forbes)
- Remove deprecated Intel MIC config options (Peter Robinson)
- redhat: replace inline awk script with genlog.py call (Herton R. Krzesinski)
- redhat: add genlog.py script (Herton R. Krzesinski)
- kernel.spec.template - fix use_vdso usage (Ben Crocker)
- redhat: remove remaining references of CONFIG_RH_DISABLE_DEPRECATED (Herton R. Krzesinski)
- Turn off vdso_install for ppc (Justin M. Forbes)
- Remove bpf-helpers.7 from bpftool package (Jiri Olsa)
- New configs in lib/Kconfig.debug (Fedora Kernel Team)
- Turn off CONFIG_VIRTIO_CONSOLE for s390x zfcpdump (Justin M. Forbes)
- New configs in drivers/clk (Justin M. Forbes)
- Keep VIRTIO_CONSOLE on s390x available. (Jakub Čajka)
- New configs in lib/Kconfig.debug (Jeremy Cline)
- Fedora 5.11 config updates part 4 (Justin M. Forbes)
- Fedora 5.11 config updates part 3 (Justin M. Forbes)
- Fedora 5.11 config updates part 2 (Justin M. Forbes)
- Update internal (test) module list from RHEL-8 (Joe Lawrence) [1915073]
- Fix USB_XHCI_PCI regression (Justin M. Forbes)
- fedora: fixes for ARMv7 build issue by disabling HIGHPTE (Peter Robinson)
- all: s390x: Increase CONFIG_PCI_NR_FUNCTIONS to 512 (#1888735) (Dan Horák)
- Fedora 5.11 configs pt 1 (Justin M. Forbes)
- redhat: avoid conflict with mod-blacklist.sh and released_kernel defined (Herton R. Krzesinski)
- redhat: handle certificate files conditionally as done for src.rpm (Herton R. Krzesinski)
- specfile: add %%{?_smp_mflags} to "make headers_install" in tools/testing/selftests (Denys Vlasenko)
- specfile: add %%{?_smp_mflags} to "make samples/bpf/" (Denys Vlasenko)
- Run MR testing in CKI pipeline (Veronika Kabatova)
- Reword comment (Nicolas Chauvet)
- Add with_cross_arm conditional (Nicolas Chauvet)
- Redefines __strip if with_cross (Nicolas Chauvet)
- fedora: only enable ACPI_CONFIGFS, ACPI_CUSTOM_METHOD in debug kernels (Peter Robinson)
- fedora: User the same EFI_CUSTOM_SSDT_OVERLAYS as ARK (Peter Robinson)
- all: all arches/kernels enable the same DMI options (Peter Robinson)
- all: move SENSORS_ACPI_POWER to common/generic (Peter Robinson)
- fedora: PCIE_HISI_ERR is already in common (Peter Robinson)
- all: all ACPI platforms enable ATA_ACPI so move it to common (Peter Robinson)
- all: x86: move shared x86 acpi config options to generic (Peter Robinson)
- All: x86: Move ACPI_VIDEO to common/x86 (Peter Robinson)
- All: x86: Enable ACPI_DPTF (Intel DPTF) (Peter Robinson)
- All: enable ACPI_BGRT for all ACPI platforms. (Peter Robinson)
- All: Only build ACPI_EC_DEBUGFS for debug kernels (Peter Robinson)
- All: Disable Intel Classmate PC ACPI_CMPC option (Peter Robinson)
- cleanup: ACPI_PROCFS_POWER was removed upstream (Peter Robinson)
- All: ACPI: De-dupe the ACPI options that are the same across ark/fedora on x86/arm (Peter Robinson)
- Enable the vkms module in Fedora (Jeremy Cline)
- Fedora: arm updates for 5.11 and general cross Fedora cleanups (Peter Robinson)
- Add gcc-c++ to BuildRequires (Justin M. Forbes)
- Update CONFIG_KASAN_HW_TAGS (Justin M. Forbes)
- fedora: arm: move generic power off/reset to all arm (Peter Robinson)
- fedora: ARMv7: build in DEVFREQ_GOV_SIMPLE_ONDEMAND until I work out why it's changed (Peter Robinson)
- fedora: cleanup joystick_adc (Peter Robinson)
- fedora: update some display options (Peter Robinson)
- fedora: arm: enable TI PRU options (Peter Robinson)
- fedora: arm: minor exynos plaform updates (Peter Robinson)
- arm: SoC: disable Toshiba Visconti SoC (Peter Robinson)
- common: disable ARCH_BCM4908 (NFC) (Peter Robinson)
- fedora: minor arm config updates (Peter Robinson)
- fedora: enable Tegra 234 SoC (Peter Robinson)
- fedora: arm: enable new Hikey 3xx options (Peter Robinson)
- Fedora: USB updates (Peter Robinson)
- fedora: enable the GNSS receiver subsystem (Peter Robinson)
- Remove POWER_AVS as no longer upstream (Peter Robinson)
- Cleanup RESET_RASPBERRYPI (Peter Robinson)
- Cleanup GPIO_CDEV_V1 options. (Peter Robinson)
- fedora: arm crypto updates (Peter Robinson)
- CONFIG_KASAN_HW_TAGS for aarch64 (Justin M. Forbes)
- Fedora: cleanup PCMCIA configs, move to x86 (Peter Robinson)
- New configs in drivers/rtc (Fedora Kernel Team)
- redhat/configs: Enable CONFIG_GCC_PLUGIN_STRUCTLEAK_BYREF_ALL (Josh Poimboeuf) [1856176]
- redhat/configs: Enable CONFIG_GCC_PLUGIN_STRUCTLEAK (Josh Poimboeuf) [1856176]
- redhat/configs: Enable CONFIG_GCC_PLUGINS on ARK (Josh Poimboeuf) [1856176]
- redhat/configs: Enable CONFIG_KASAN on Fedora (Josh Poimboeuf) [1856176]
- New configs in init/Kconfig (Fedora Kernel Team)
- build_configs.sh: Fix syntax flagged by shellcheck (Ben Crocker)
- genspec.sh: Fix syntax flagged by shellcheck (Ben Crocker)
- mod-blacklist.sh: Fix syntax flagged by shellcheck (Ben Crocker)
- Enable Speakup accessibility driver (Justin M. Forbes)
- New configs in init/Kconfig (Fedora Kernel Team)
- Fix fedora config mismatch due to dep changes (Justin M. Forbes)
- New configs in drivers/crypto (Jeremy Cline)
- Remove duplicate ENERGY_MODEL configs (Peter Robinson)
- This is selected by PCIE_QCOM so must match (Justin M. Forbes)
- drop unused BACKLIGHT_GENERIC (Peter Robinson)
- Remove cp instruction already handled in instruction below. (Paulo E. Castro)
- Add all the dependencies gleaned from running `make prepare` on a bloated devel kernel. (Paulo E. Castro)
- Add tools to path mangling script. (Paulo E. Castro)
- Remove duplicate cp statement which is also not specific to x86. (Paulo E. Castro)
- Correct orc_types failure whilst running `make prepare` https://bugzilla.redhat.com/show_bug.cgi?id=1882854 (Paulo E. Castro)
- redhat: ark: enable CONFIG_IKHEADERS (Jiri Olsa)
- Add missing '$' sign to (GIT) in redhat/Makefile (Augusto Caringi)
- Remove filterdiff and use native git instead (Don Zickus)
- New configs in net/sched (Justin M. Forbes)
- New configs in drivers/mfd (CKI@GitLab)
- New configs in drivers/mfd (Fedora Kernel Team)
- New configs in drivers/firmware (Fedora Kernel Team)
- Temporarily backout parallel xz script (Justin M. Forbes)
- redhat: explicitly disable CONFIG_IMA_APPRAISE_SIGNED_INIT (Bruno Meneguele)
- redhat: enable CONFIG_EVM_LOAD_X509 on ARK (Bruno Meneguele)
- redhat: enable CONFIG_EVM_ATTR_FSUUID on ARK (Bruno Meneguele)
- redhat: enable CONFIG_EVM in all arches and flavors (Bruno Meneguele)
- redhat: enable CONFIG_IMA_LOAD_X509 on ARK (Bruno Meneguele)
- redhat: set CONFIG_IMA_DEFAULT_HASH to SHA256 (Bruno Meneguele)
- redhat: enable CONFIG_IMA_SECURE_AND_OR_TRUSTED_BOOT (Bruno Meneguele)
- redhat: enable CONFIG_IMA_READ_POLICY on ARK (Bruno Meneguele)
- redhat: set default IMA template for all ARK arches (Bruno Meneguele)
- redhat: enable CONFIG_IMA_DEFAULT_HASH_SHA256 for all flavors (Bruno Meneguele)
- redhat: disable CONFIG_IMA_DEFAULT_HASH_SHA1 (Bruno Meneguele)
- redhat: enable CONFIG_IMA_ARCH_POLICY for ppc and x86 (Bruno Meneguele)
- redhat: enable CONFIG_IMA_APPRAISE_MODSIG (Bruno Meneguele)
- redhat: enable CONFIG_IMA_APPRAISE_BOOTPARAM (Bruno Meneguele)
- redhat: enable CONFIG_IMA_APPRAISE (Bruno Meneguele)
- redhat: enable CONFIG_INTEGRITY for aarch64 (Bruno Meneguele)
- kernel: Update some missing KASAN/KCSAN options (Jeremy Linton)
- kernel: Enable coresight on aarch64 (Jeremy Linton)
- Update CONFIG_INET6_ESPINTCP (Justin Forbes)
- New configs in net/ipv6 (Justin M. Forbes)
- fedora: move CONFIG_RTC_NVMEM options from ark to common (Peter Robinson)
- configs: Enable CONFIG_DEBUG_INFO_BTF (Don Zickus)
- fedora: some minor arm audio config tweaks (Peter Robinson)
- Ship xpad with default modules on Fedora and RHEL (Bastien Nocera)
- Fedora: Only enable legacy serial/game port joysticks on x86 (Peter Robinson)
- Fedora: Enable the options required for the Librem 5 Phone (Peter Robinson)
- Fedora config update (Justin M. Forbes)
- Fedora config change because CONFIG_FSL_DPAA2_ETH now selects CONFIG_FSL_XGMAC_MDIO (Justin M. Forbes)
- redhat: generic  enable CONFIG_INET_MPTCP_DIAG (Davide Caratti)
- Fedora config update (Justin M. Forbes)
- Enable NANDSIM for Fedora (Justin M. Forbes)
- Re-enable CONFIG_ACPI_TABLE_UPGRADE for Fedora since upstream disables this if secureboot is active (Justin M. Forbes)
- Ath11k related config updates (Justin M. Forbes)
- Fedora config updates for ath11k (Justin M. Forbes)
- Turn on ATH11K for Fedora (Justin M. Forbes)
- redhat: enable CONFIG_INTEL_IOMMU_SVM (Jerry Snitselaar)
- More Fedora config fixes (Justin M. Forbes)
- Fedora 5.10 config updates (Justin M. Forbes)
- Fedora 5.10 configs round 1 (Justin M. Forbes)
- Fedora config updates (Justin M. Forbes)
- Allow kernel-tools to build without selftests (Don Zickus)
- Allow building of kernel-tools standalone (Don Zickus)
- redhat: ark: disable CONFIG_NET_ACT_CTINFO (Davide Caratti)
- redhat: ark: disable CONFIG_NET_SCH_TEQL (Davide Caratti)
- redhat: ark: disable CONFIG_NET_SCH_SFB (Davide Caratti)
- redhat: ark: disable CONFIG_NET_SCH_QFQ (Davide Caratti)
- redhat: ark: disable CONFIG_NET_SCH_PLUG (Davide Caratti)
- redhat: ark: disable CONFIG_NET_SCH_PIE (Davide Caratti)
- redhat: ark: disable CONFIG_NET_SCH_HHF (Davide Caratti)
- redhat: ark: disable CONFIG_NET_SCH_DSMARK (Davide Caratti)
- redhat: ark: disable CONFIG_NET_SCH_DRR (Davide Caratti)
- redhat: ark: disable CONFIG_NET_SCH_CODEL (Davide Caratti)
- redhat: ark: disable CONFIG_NET_SCH_CHOKE (Davide Caratti)
- redhat: ark: disable CONFIG_NET_SCH_CBQ (Davide Caratti)
- redhat: ark: disable CONFIG_NET_SCH_ATM (Davide Caratti)
- redhat: ark: disable CONFIG_NET_EMATCH and sub-targets (Davide Caratti)
- redhat: ark: disable CONFIG_NET_CLS_TCINDEX (Davide Caratti)
- redhat: ark: disable CONFIG_NET_CLS_RSVP6 (Davide Caratti)
- redhat: ark: disable CONFIG_NET_CLS_RSVP (Davide Caratti)
- redhat: ark: disable CONFIG_NET_CLS_ROUTE4 (Davide Caratti)
- redhat: ark: disable CONFIG_NET_CLS_BASIC (Davide Caratti)
- redhat: ark: disable CONFIG_NET_ACT_SKBMOD (Davide Caratti)
- redhat: ark: disable CONFIG_NET_ACT_SIMP (Davide Caratti)
- redhat: ark: disable CONFIG_NET_ACT_NAT (Davide Caratti)
- arm64/defconfig: Enable CONFIG_KEXEC_FILE (Bhupesh Sharma) [1821565]
- redhat/configs: Cleanup CONFIG_CRYPTO_SHA512 (Prarit Bhargava)
- New configs in drivers/mfd (Fedora Kernel Team)
- Fix LTO issues with kernel-tools (Don Zickus)
- Point pathfix to the new location for gen_compile_commands.py (Justin M. Forbes)
- configs: Disable CONFIG_SECURITY_SELINUX_DISABLE (Ondrej Mosnacek)
- [Automatic] Handle config dependency changes (Don Zickus)
- configs/iommu: Add config comment to empty CONFIG_SUN50I_IOMMU file (Jerry Snitselaar)
- New configs in kernel/trace (Fedora Kernel Team)
- Fix Fedora config locations (Justin M. Forbes)
- Fedora config updates (Justin M. Forbes)
- configs: enable CONFIG_CRYPTO_CTS=y so cts(cbc(aes)) is available in FIPS mode (Vladis Dronov) [1855161]
- Partial revert: Add master merge check (Don Zickus)
- Update Maintainers doc to reflect workflow changes (Don Zickus)
- WIP: redhat/docs: Update documentation for single branch workflow (Prarit Bhargava)
- Add CONFIG_ARM64_MTE which is not picked up by the config scripts for some reason (Justin M. Forbes)
- Disable Speakup synth DECEXT (Justin M. Forbes)
- Enable Speakup for Fedora since it is out of staging (Justin M. Forbes)
- Modify patchlist changelog output (Don Zickus)
- process_configs.sh: Fix syntax flagged by shellcheck (Ben Crocker)
- generate_all_configs.sh: Fix syntax flagged by shellcheck (Ben Crocker)
- redhat/self-test: Initial commit (Ben Crocker)
- Fixes "acpi: prefer booting with ACPI over DTS" to be RHEL only (Peter Robinson)
- arch/x86: Remove vendor specific CPU ID checks (Prarit Bhargava)
- redhat: Replace hardware.redhat.com link in Unsupported message (Prarit Bhargava) [1810301]
- x86: Fix compile issues with rh_check_supported() (Don Zickus)
- KEYS: Make use of platform keyring for module signature verify (Robert Holmes)
- Input: rmi4 - remove the need for artificial IRQ in case of HID (Benjamin Tissoires)
- ARM: tegra: usb no reset (Peter Robinson)
- arm: make CONFIG_HIGHPTE optional without CONFIG_EXPERT (Jon Masters)
- redhat: rh_kabi: deduplication friendly structs (Jiri Benc)
- redhat: rh_kabi add a comment with warning about RH_KABI_EXCLUDE usage (Jiri Benc)
- redhat: rh_kabi: introduce RH_KABI_EXTEND_WITH_SIZE (Jiri Benc)
- redhat: rh_kabi: Indirect EXTEND macros so nesting of other macros will resolve. (Don Dutile)
- redhat: rh_kabi: Fix RH_KABI_SET_SIZE to use dereference operator (Tony Camuso)
- redhat: rh_kabi: Add macros to size and extend structs (Prarit Bhargava)
- Removing Obsolete hba pci-ids from rhel8 (Dick Kennedy)
- mptsas: pci-id table changes (Laura Abbott)
- mptsas: Taint kernel if mptsas is loaded (Laura Abbott)
- mptspi: pci-id table changes (Laura Abbott)
- qla2xxx: Remove PCI IDs of deprecated adapter (Jeremy Cline)
- be2iscsi: remove unsupported device IDs (Chris Leech)
- mptspi: Taint kernel if mptspi is loaded (Laura Abbott)
- hpsa: remove old cciss-based smartarray pci ids (Joseph Szczypek)
- qla4xxx: Remove deprecated PCI IDs from RHEL 8 (Chad Dupuis)
- aacraid: Remove depreciated device and vendor PCI id's (Raghava Aditya Renukunta)
- megaraid_sas: remove deprecated pci-ids (Tomas Henzl)
- mpt*: remove certain deprecated pci-ids (Jeremy Cline)
- kernel: add SUPPORT_REMOVED kernel taint (Tomas Henzl)
- Rename RH_DISABLE_DEPRECATED to RHEL_DIFFERENCES (Don Zickus)
- Add option of 13 for FORCE_MAX_ZONEORDER (Peter Robinson)
- s390: Lock down the kernel when the IPL secure flag is set (Jeremy Cline)
- efi: Lock down the kernel if booted in secure boot mode (David Howells)
- efi: Add an EFI_SECURE_BOOT flag to indicate secure boot mode (David Howells)
- security: lockdown: expose a hook to lock the kernel down (Jeremy Cline)
- Make get_cert_list() use efi_status_to_str() to print error messages. (Peter Jones)
- Add efi_status_to_str() and rework efi_status_to_err(). (Peter Jones)
- Add support for deprecating processors (Laura Abbott) [1565717 1595918 1609604 1610493]
- arm: aarch64: Drop the EXPERT setting from ARM64_FORCE_52BIT (Jeremy Cline)
- iommu/arm-smmu: workaround DMA mode issues (Laura Abbott)
- rh_kabi: introduce RH_KABI_EXCLUDE (Jakub Racek)
- ipmi: do not configure ipmi for HPE m400 (Laura Abbott) [1670017]
- kABI: Add generic kABI macros to use for kABI workarounds (Myron Stowe) [1546831]
- add pci_hw_vendor_status() (Maurizio Lombardi)
- ahci: thunderx2: Fix for errata that affects stop engine (Robert Richter)
- Vulcan: AHCI PCI bar fix for Broadcom Vulcan early silicon (Robert Richter)
- bpf: set unprivileged_bpf_disabled to 1 by default, add a boot parameter (Eugene Syromiatnikov) [1561171]
- add Red Hat-specific taint flags (Eugene Syromiatnikov) [1559877]
- tags.sh: Ignore redhat/rpm (Jeremy Cline)
- put RHEL info into generated headers (Laura Abbott) [1663728]
- acpi: prefer booting with ACPI over DTS (Mark Salter) [1576869]
- aarch64: acpi scan: Fix regression related to X-Gene UARTs (Mark Salter) [1519554]
- ACPI / irq: Workaround firmware issue on X-Gene based m400 (Mark Salter) [1519554]
- modules: add rhelversion MODULE_INFO tag (Laura Abbott)
- ACPI: APEI: arm64: Ignore broken HPE moonshot APEI support (Al Stone) [1518076]
- Add Red Hat tainting (Laura Abbott) [1565704]
- Introduce CONFIG_RH_DISABLE_DEPRECATED (Laura Abbott)
- Stop merging ark-patches for release (Don Zickus)
- Fix path location for ark-update-configs.sh (Don Zickus)
- Combine Red Hat patches into single patch (Don Zickus)
- New configs in drivers/misc (Jeremy Cline)
- New configs in drivers/net/wireless (Justin M. Forbes)
- New configs in drivers/phy (Fedora Kernel Team)
- New configs in drivers/tty (Fedora Kernel Team)
- Set SquashFS decompression options for all flavors to match RHEL (Bohdan Khomutskyi)
- configs: Enable CONFIG_ENERGY_MODEL (Phil Auld)
- New configs in drivers/pinctrl (Fedora Kernel Team)
- Update CONFIG_THERMAL_NETLINK (Justin Forbes)
- Separate merge-upstream and release stages (Don Zickus)
- Re-enable CONFIG_IR_SERIAL on Fedora (Prarit Bhargava)
- Create Patchlist.changelog file (Don Zickus)
- Filter out upstream commits from changelog (Don Zickus)
- Merge Upstream script fixes (Don Zickus)
- kernel.spec: Remove kernel-keys directory on rpm erase (Prarit Bhargava)
- Add mlx5_vdpa to module filter for Fedora (Justin M. Forbes)
- Add python3-sphinx_rtd_theme buildreq for docs (Justin M. Forbes)
- redhat/configs/process_configs.sh: Remove *.config.orig files (Prarit Bhargava)
- redhat/configs/process_configs.sh: Add process_configs_known_broken flag (Prarit Bhargava)
- redhat/Makefile: Fix '*-configs' targets (Prarit Bhargava)
- dist-merge-upstream: Checkout known branch for ci scripts (Don Zickus)
- kernel.spec: don't override upstream compiler flags for ppc64le (Dan Horák)
- Fedora config updates (Justin M. Forbes)
- Fedora confi gupdate (Justin M. Forbes)
- mod-sign.sh: Fix syntax flagged by shellcheck (Ben Crocker)
- Swap how ark-latest is built (Don Zickus)
- Add extra version bump to os-build branch (Don Zickus)
- dist-release: Avoid needless version bump. (Don Zickus)
- Add dist-fedora-release target (Don Zickus)
- Remove redundant code in dist-release (Don Zickus)
- Makefile.common rename TAG to _TAG (Don Zickus)
- Fedora config change (Justin M. Forbes)
- Fedora filter update (Justin M. Forbes)
- Config update for Fedora (Justin M. Forbes)
- enable PROTECTED_VIRTUALIZATION_GUEST for all s390x kernels (Dan Horák)
- redhat: ark: enable CONFIG_NET_SCH_TAPRIO (Davide Caratti)
- redhat: ark: enable CONFIG_NET_SCH_ETF (Davide Caratti)
- More Fedora config updates (Justin M. Forbes)
- New config deps (Justin M. Forbes)
- Fedora config updates (Justin M. Forbes)
- First half of config updates for Fedora (Justin M. Forbes)
- Updates for Fedora arm architectures for the 5.9 window (Peter Robinson)
- Merge 5.9 config changes from Peter Robinson (Justin M. Forbes)
- Add config options that only show up when we prep on arm (Justin M. Forbes)
- Config updates for Fedora (Justin M. Forbes)
- fedora: enable enery model (Peter Robinson)
- Use the configs/generic config for SND_HDA_INTEL everywhere (Peter Robinson)
- Enable ZSTD compression algorithm on all kernels (Peter Robinson)
- Enable ARM_SMCCC_SOC_ID on all aarch64 kernels (Peter Robinson)
- iio: enable LTR-559 light and proximity sensor (Peter Robinson)
- iio: chemical: enable some popular chemical and partical sensors (Peter Robinson)
- More mismatches (Justin M. Forbes)
- Fedora config change due to deps (Justin M. Forbes)
- CONFIG_SND_SOC_MAX98390 is now selected by SND_SOC_INTEL_DA7219_MAX98357A_GENERIC (Justin M. Forbes)
- Config change required for build part 2 (Justin M. Forbes)
- Config change required for build (Justin M. Forbes)
- Fedora config update (Justin M. Forbes)
- Add ability to sync upstream through Makefile (Don Zickus)
- Add master merge check (Don Zickus)
- Replace hardcoded values 'os-build' and project id with variables (Don Zickus)
- redhat/Makefile.common: Fix MARKER (Prarit Bhargava)
- gitattributes: Remove unnecesary export restrictions (Prarit Bhargava)
- Add new certs for dual signing with boothole (Justin M. Forbes)
- Update secureboot signing for dual keys (Justin M. Forbes)
- fedora: enable LEDS_SGM3140 for arm configs (Peter Robinson)
- Enable CONFIG_DM_VERITY_VERIFY_ROOTHASH_SIG (Justin M. Forbes)
- redhat/configs: Fix common CONFIGs (Prarit Bhargava)
- redhat/configs: General CONFIG cleanups (Prarit Bhargava)
- redhat/configs: Update & generalize evaluate_configs (Prarit Bhargava)
- fedora: arm: Update some meson config options (Peter Robinson)
- redhat/docs: Add Fedora RPM tagging date (Prarit Bhargava)
- Update config for renamed panel driver. (Peter Robinson)
- Enable SERIAL_SC16IS7XX for SPI interfaces (Peter Robinson)
- s390x-zfcpdump: Handle missing Module.symvers file (Don Zickus)
- Fedora config updates (Justin M. Forbes)
- redhat/configs: Add .tmp files to .gitignore (Prarit Bhargava)
- disable uncommon TCP congestion control algorithms (Davide Caratti)
- Add new bpf man pages (Justin M. Forbes)
- Add default option for CONFIG_ARM64_BTI_KERNEL to pending-common so that eln kernels build (Justin M. Forbes)
- redhat/Makefile: Add fedora-configs and rh-configs make targets (Prarit Bhargava)
- redhat/configs: Use SHA512 for module signing (Prarit Bhargava)
- genspec.sh: 'touch' empty Patchlist file for single tarball (Don Zickus)
- Fedora config update for rc1 (Justin M. Forbes)
- Fedora config updates (Justin M. Forbes)
- Fedora config updates (Justin M. Forbes)
- redhat/Makefile.common: fix RPMKSUBLEVEL condition (Ondrej Mosnacek)
- redhat/Makefile: silence KABI tar output (Ondrej Mosnacek)
- One more Fedora config update (Justin M. Forbes)
- Fedora config updates (Justin M. Forbes)
- Fix PATCHLEVEL for merge window (Justin M. Forbes)
- Change ark CONFIG_COMMON_CLK to yes, it is selected already by other options (Justin M. Forbes)
- Fedora config updates (Justin M. Forbes)
- Fedora config updates (Justin M. Forbes)
- Fedora config updates (Justin M. Forbes)
- More module filtering for Fedora (Justin M. Forbes)
- Update filters for rnbd in Fedora (Justin M. Forbes)
- Fedora config updates (Justin M. Forbes)
- Fix up module filtering for 5.8 (Justin M. Forbes)
- Fedora config updates (Justin M. Forbes)
- More Fedora config work (Justin M. Forbes)
- RTW88BE and CE have been extracted to their own modules (Justin M. Forbes)
- Set CONFIG_BLK_INLINE_ENCRYPTION_FALLBACK for Fedora (Justin M. Forbes)
- Fedora config updates (Justin M. Forbes)
- Arm64 Use Branch Target Identification for kernel (Justin M. Forbes)
- Change value of CONFIG_SECURITY_SELINUX_CHECKREQPROT_VALUE (Justin M. Forbes)
- Fedora config updates (Justin M. Forbes)
- Fix configs for Fedora (Justin M. Forbes)
- Add zero-commit to format-patch options (Justin M. Forbes)
- Copy Makefile.rhelver as a source file rather than a patch (Jeremy Cline)
- Move the sed to clear the patch templating outside of conditionals (Justin M. Forbes)
- Match template format in kernel.spec.template (Justin M. Forbes)
- Break out the Patches into individual files for dist-git (Justin M. Forbes)
- Break the Red Hat patch into individual commits (Jeremy Cline)
- Fix update_scripts.sh unselective pattern sub (David Howells)
- Add cec to the filter overrides (Justin M. Forbes)
- Add overrides to filter-modules.sh (Justin M. Forbes)
- redhat/configs: Enable CONFIG_SMC91X and disable CONFIG_SMC911X (Prarit Bhargava) [1722136]
- Include bpftool-struct_ops man page in the bpftool package (Jeremy Cline)
- Add sharedbuffer_configuration.py to the pathfix.py script (Jeremy Cline)
- Use __make macro instead of make (Tom Stellard)
- Sign off generated configuration patches (Jeremy Cline)
- Drop the static path configuration for the Sphinx docs (Jeremy Cline)
- redhat: Add dummy-module kernel module (Prarit Bhargava)
- redhat: enable CONFIG_LWTUNNEL_BPF (Jiri Benc)
- Remove typoed config file aarch64CONFIG_SM_GCC_8150 (Justin M. Forbes)
- Add Documentation back to kernel-devel as it has Kconfig now (Justin M. Forbes)
- Copy distro files rather than moving them (Jeremy Cline)
- kernel.spec: fix 'make scripts' for kernel-devel package (Brian Masney)
- Makefile: correct help text for dist-cross-<arch>-rpms (Brian Masney)
- redhat/Makefile: Fix RHEL8 python warning (Prarit Bhargava)
- redhat: Change Makefile target names to dist- (Prarit Bhargava)
- configs: Disable Serial IR driver (Prarit Bhargava)
- Fix "multiple %%files for package kernel-tools" (Pablo Greco)
- Introduce a Sphinx documentation project (Jeremy Cline)
- Build ARK against ELN (Don Zickus)
- Drop the requirement to have a remote called linus (Jeremy Cline)
- Rename 'internal' branch to 'os-build' (Don Zickus)
- Only include open merge requests with "Include in Releases" label (Jeremy Cline)
- Package gpio-watch in kernel-tools (Jeremy Cline)
- Exit non-zero if the tag already exists for a release (Jeremy Cline)
- Adjust the changelog update script to not push anything (Jeremy Cline)
- Drop --target noarch from the rh-rpms make target (Jeremy Cline)
- Add a script to generate release tags and branches (Jeremy Cline)
- Set CONFIG_VDPA for fedora (Justin M. Forbes)
- Add a README to the dist-git repository (Jeremy Cline)
- Provide defaults in ark-rebase-patches.sh (Jeremy Cline)
- Default ark-rebase-patches.sh to not report issues (Jeremy Cline)
- Drop DIST from release commits and tags (Jeremy Cline)
- Place the buildid before the dist in the release (Jeremy Cline)
- Sync up with Fedora arm configuration prior to merging (Jeremy Cline)
- Disable CONFIG_PROTECTED_VIRTUALIZATION_GUEST for zfcpdump (Jeremy Cline)
- Add RHMAINTAINERS file and supporting conf (Don Zickus)
- Add a script to test if all commits are signed off (Jeremy Cline)
- Fix make rh-configs-arch (Don Zickus)
- Drop RH_FEDORA in favor of the now-merged RHEL_DIFFERENCES (Jeremy Cline)
- Sync up Fedora configs from the first week of the merge window (Jeremy Cline)
- Migrate blacklisting floppy.ko to mod-blacklist.sh (Don Zickus)
- kernel packaging: Combine mod-blacklist.sh and mod-extra-blacklist.sh (Don Zickus)
- kernel packaging: Fix extra namespace collision (Don Zickus)
- mod-extra.sh: Rename to mod-blacklist.sh (Don Zickus)
- mod-extra.sh: Make file generic (Don Zickus)
- Fix a painfully obvious YAML syntax error in .gitlab-ci.yml (Jeremy Cline)
- Add in armv7hl kernel header support (Don Zickus)
- Disable all BuildKernel commands when only building headers (Don Zickus)
- Drop any gitlab-ci patches from ark-patches (Jeremy Cline)
- Build the srpm for internal branch CI using the vanilla tree (Jeremy Cline)
- Pull in the latest ARM configurations for Fedora (Jeremy Cline)
- Fix xz memory usage issue (Neil Horman)
- Use ark-latest instead of master for update script (Jeremy Cline)
- Move the CI jobs back into the ARK repository (Jeremy Cline)
- Sync up ARK's Fedora config with the dist-git repository (Jeremy Cline)
- Pull in the latest configuration changes from Fedora (Jeremy Cline)
- configs: enable CONFIG_NET_SCH_CBS (Marcelo Ricardo Leitner)
- Drop configuration options in fedora/ that no longer exist (Jeremy Cline)
- Set RH_FEDORA for ARK and Fedora (Jeremy Cline)
- redhat/kernel.spec: Include the release in the kernel COPYING file (Jeremy Cline)
- redhat/kernel.spec: add scripts/jobserver-exec to py3_shbang_opts list (Jeremy Cline)
- redhat/kernel.spec: package bpftool-gen man page (Jeremy Cline)
- distgit-changelog: handle multiple y-stream BZ numbers (Bruno Meneguele)
- redhat/kernel.spec: remove all inline comments (Bruno Meneguele)
- redhat/genspec: awk unknown whitespace regex pattern (Bruno Meneguele)
- Improve the readability of gen_config_patches.sh (Jeremy Cline)
- Fix some awkward edge cases in gen_config_patches.sh (Jeremy Cline)
- Update the CI environment to use Fedora 31 (Jeremy Cline)
- redhat: drop whitespace from with_gcov macro (Jan Stancek)
- configs: Enable CONFIG_KEY_DH_OPERATIONS on ARK (Ondrej Mosnacek)
- configs: Adjust CONFIG_MPLS_ROUTING and CONFIG_MPLS_IPTUNNEL (Laura Abbott)
- New configs in lib/crypto (Jeremy Cline)
- New configs in drivers/char (Jeremy Cline)
- Turn on BLAKE2B for Fedora (Jeremy Cline)
- kernel.spec.template: Clean up stray *.h.s files (Laura Abbott)
- Build the SRPM in the CI job (Jeremy Cline)
- New configs in net/tls (Jeremy Cline)
- New configs in net/tipc (Jeremy Cline)
- New configs in lib/kunit (Jeremy Cline)
- Fix up released_kernel case (Laura Abbott)
- New configs in lib/Kconfig.debug (Jeremy Cline)
- New configs in drivers/ptp (Jeremy Cline)
- New configs in drivers/nvme (Jeremy Cline)
- New configs in drivers/net/phy (Jeremy Cline)
- New configs in arch/arm64 (Jeremy Cline)
- New configs in drivers/crypto (Jeremy Cline)
- New configs in crypto/Kconfig (Jeremy Cline)
- Add label so the Gitlab to email bridge ignores the changelog (Jeremy Cline)
- Temporarily switch TUNE_DEFAULT to y (Jeremy Cline)
- Run config test for merge requests and internal (Jeremy Cline)
- Add missing licensedir line (Laura Abbott)
- redhat/scripts: Remove redhat/scripts/rh_get_maintainer.pl (Prarit Bhargava)
- configs: Take CONFIG_DEFAULT_MMAP_MIN_ADDR from Fedra (Laura Abbott)
- configs: Turn off ISDN (Laura Abbott)
- Add a script to generate configuration patches (Laura Abbott)
- Introduce rh-configs-commit (Laura Abbott)
- kernel-packaging: Remove kernel files from kernel-modules-extra package (Prarit Bhargava)
- configs: Enable CONFIG_DEBUG_WX (Laura Abbott)
- configs: Disable wireless USB (Laura Abbott)
- Clean up some temporary config files (Laura Abbott)
- configs: New config in drivers/gpu for v5.4-rc1 (Jeremy Cline)
- configs: New config in arch/powerpc for v5.4-rc1 (Jeremy Cline)
- configs: New config in crypto for v5.4-rc1 (Jeremy Cline)
- configs: New config in drivers/usb for v5.4-rc1 (Jeremy Cline)
- AUTOMATIC: New configs (Jeremy Cline)
- Skip ksamples for bpf, they are broken (Jeremy Cline)
- configs: New config in fs/erofs for v5.4-rc1 (Jeremy Cline)
- configs: New config in mm for v5.4-rc1 (Jeremy Cline)
- configs: New config in drivers/md for v5.4-rc1 (Jeremy Cline)
- configs: New config in init for v5.4-rc1 (Jeremy Cline)
- configs: New config in fs/fuse for v5.4-rc1 (Jeremy Cline)
- merge.pl: Avoid comments but do not skip them (Don Zickus)
- configs: New config in drivers/net/ethernet/pensando for v5.4-rc1 (Jeremy Cline)
- Update a comment about what released kernel means (Laura Abbott)
- Provide both Fedora and RHEL files in the SRPM (Laura Abbott)
- kernel.spec.template: Trim EXTRAVERSION in the Makefile (Laura Abbott)
- kernel.spec.template: Add macros for building with nopatches (Laura Abbott)
- kernel.spec.template: Add some macros for Fedora differences (Laura Abbott)
- kernel.spec.template: Consolodate the options (Laura Abbott)
- configs: Add pending direcory to Fedora (Laura Abbott)
- kernel.spec.template: Don't run hardlink if rpm-ostree is in use (Laura Abbott)
- configs: New config in net/can for v5.4-rc1 (Jeremy Cline)
- configs: New config in drivers/net/phy for v5.4-rc1 (Jeremy Cline)
- configs: Increase x86_64 NR_UARTS to 64 (Prarit Bhargava) [1730649]
- configs: turn on ARM64_FORCE_52BIT for debug builds (Jeremy Cline)
- kernel.spec.template: Tweak the python3 mangling (Laura Abbott)
- kernel.spec.template: Add --with verbose option (Laura Abbott)
- kernel.spec.template: Switch to using %%install instead of %%__install (Laura Abbott)
- kernel.spec.template: Make the kernel.org URL https (Laura Abbott)
- kernel.spec.template: Update message about secure boot signing (Laura Abbott)
- kernel.spec.template: Move some with flags definitions up (Laura Abbott)
- kernel.spec.template: Update some BuildRequires (Laura Abbott)
- kernel.spec.template: Get rid of %%clean (Laura Abbott)
- configs: New config in drivers/char for v5.4-rc1 (Jeremy Cline)
- configs: New config in net/sched for v5.4-rc1 (Jeremy Cline)
- configs: New config in lib for v5.4-rc1 (Jeremy Cline)
- configs: New config in fs/verity for v5.4-rc1 (Jeremy Cline)
- configs: New config in arch/aarch64 for v5.4-rc4 (Jeremy Cline)
- configs: New config in arch/arm64 for v5.4-rc1 (Jeremy Cline)
- Flip off CONFIG_ARM64_VA_BITS_52 so the bundle that turns it on applies (Jeremy Cline)
- New configuration options for v5.4-rc4 (Jeremy Cline)
- Correctly name tarball for single tarball builds (Laura Abbott)
- configs: New config in drivers/pci for v5.4-rc1 (Jeremy Cline)
- Allow overriding the dist tag on the command line (Laura Abbott)
- Allow scratch branch target to be overridden (Laura Abbott)
- Remove long dead BUILD_DEFAULT_TARGET (Laura Abbott)
- Amend the changelog when rebasing (Laura Abbott)
- configs: New config in drivers/platform for v5.4-rc1 (Jeremy Cline)
- configs: New config in drivers/pinctrl for v5.4-rc1 (Jeremy Cline)
- configs: New config in drivers/net/wireless for v5.4-rc1 (Jeremy Cline)
- configs: New config in drivers/net/ethernet/mellanox for v5.4-rc1 (Jeremy Cline)
- configs: New config in drivers/net/can for v5.4-rc1 (Jeremy Cline)
- configs: New config in drivers/hid for v5.4-rc1 (Jeremy Cline)
- configs: New config in drivers/dma-buf for v5.4-rc1 (Jeremy Cline)
- configs: New config in drivers/crypto for v5.4-rc1 (Jeremy Cline)
- configs: New config in arch/s390 for v5.4-rc1 (Jeremy Cline)
- configs: New config in block for v5.4-rc1 (Jeremy Cline)
- configs: New config in drivers/cpuidle for v5.4-rc1 (Jeremy Cline)
- redhat: configs: Split CONFIG_CRYPTO_SHA512 (Laura Abbott)
- redhat: Set Fedora options (Laura Abbott)
- Set CRYPTO_SHA3_*_S390 to builtin on zfcpdump (Jeremy Cline)
- configs: New config in drivers/edac for v5.4-rc1 (Jeremy Cline)
- configs: New config in drivers/firmware for v5.4-rc1 (Jeremy Cline)
- configs: New config in drivers/hwmon for v5.4-rc1 (Jeremy Cline)
- configs: New config in drivers/iio for v5.4-rc1 (Jeremy Cline)
- configs: New config in drivers/mmc for v5.4-rc1 (Jeremy Cline)
- configs: New config in drivers/tty for v5.4-rc1 (Jeremy Cline)
- configs: New config in arch/s390 for v5.4-rc1 (Jeremy Cline)
- configs: New config in drivers/bus for v5.4-rc1 (Jeremy Cline)
- Add option to allow mismatched configs on the command line (Laura Abbott)
- configs: New config in drivers/crypto for v5.4-rc1 (Jeremy Cline)
- configs: New config in sound/pci for v5.4-rc1 (Jeremy Cline)
- configs: New config in sound/soc for v5.4-rc1 (Jeremy Cline)
- gitlab: Add CI job for packaging scripts (Major Hayden)
- Speed up CI with CKI image (Major Hayden)
- Disable e1000 driver in ARK (Neil Horman)
- configs: Fix the pending default for CONFIG_ARM64_VA_BITS_52 (Jeremy Cline)
- configs: Turn on OPTIMIZE_INLINING for everything (Jeremy Cline)
- configs: Set valid pending defaults for CRYPTO_ESSIV (Jeremy Cline)
- Add an initial CI configuration for the internal branch (Jeremy Cline)
- New drop of configuration options for v5.4-rc1 (Jeremy Cline)
- New drop of configuration options for v5.4-rc1 (Jeremy Cline)
- Pull the RHEL version defines out of the Makefile (Jeremy Cline)
- Sync up the ARK build scripts (Jeremy Cline)
- Sync up the Fedora Rawhide configs (Jeremy Cline)
- Sync up the ARK config files (Jeremy Cline)
- configs: Adjust CONFIG_FORCE_MAX_ZONEORDER for Fedora (Laura Abbott)
- configs: Add README for some other arches (Laura Abbott)
- configs: Sync up Fedora configs (Laura Abbott)
- [initial commit] Add structure for building with git (Laura Abbott)
- [initial commit] Add Red Hat variables in the top level makefile (Laura Abbott)
- [initial commit] Red Hat gitignore and attributes (Laura Abbott)
- [initial commit] Add changelog (Laura Abbott)
- [initial commit] Add makefile (Laura Abbott)
- [initial commit] Add files for generating the kernel.spec (Laura Abbott)
- [initial commit] Add rpm directory (Laura Abbott)
- [initial commit] Add files for packaging (Laura Abbott)
- [initial commit] Add kabi files (Laura Abbott)
- [initial commit] Add scripts (Laura Abbott)
- [initial commit] Add configs (Laura Abbott)
- [initial commit] Add Makefiles (Laura Abbott)

# The following bit is important for automation so please do not remove
# END OF CHANGELOG

###
# The following Emacs magic makes C-c C-e use UTC dates.
# Local Variables:
# rpm-change-log-uses-utc: t
# End:
###
