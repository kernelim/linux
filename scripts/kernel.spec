# All Global changes to build and install go here.
# Per the below section about __spec_install_pre, any rpm
# environment changes that affect %%install need to go
# here before the %%install macro is pre-built.

# Disable frame pointers
%undefine _include_frame_pointers

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

# RPM macros strip everything in BUILDROOT, either with __strip
# or find-debuginfo.sh. Make use of __spec_install_post override
# and save/restore binaries we want to package as unstripped.
%define buildroot_unstripped %{_builddir}/root_unstripped
%define buildroot_save_unstripped() \
(cd %{buildroot}; cp -rav --parents -t %{buildroot_unstripped}/ %1 || true) \
%{nil}
%define __restore_unstripped_root_post \
    echo "Restoring unstripped artefacts %{buildroot_unstripped} -> %{buildroot}" \
    cp -rav %{buildroot_unstripped}/. %{buildroot}/ \
%{nil}

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

# Replace '-' with '_' where needed so that variants can use '-' in
# their name.
%define uname_suffix() %{lua:
	local flavour = rpm.expand('%{?1:+%{1}}')
	flavour = flavour:gsub('-', '_')
	if flavour ~= '' then
		print(flavour)
	end
}

# This returns the main kernel tied to a debug variant. For example,
# kernel-debug is the debug version of kernel, so we return an empty
# string. However, kernel-64k-debug is the debug version of kernel-64k,
# in this case we need to return "64k", and so on. This is used in
# macros below where we need this for some uname based requires.
%define uname_variant() %{lua:
	local flavour = rpm.expand('%{?1:%{1}}')
	_, _, main, sub = flavour:find("(%w+)-(.*)")
	if main then
		print("+" .. main)
	end
}


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

Summary: The Linux kernel
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

# Default compression algorithm
%global compression xz
%global compression_flags --compress
%global compext xz

%if 0%{?fedora}
%define primary_target fedora
%else
%define primary_target rhel
%endif

#
# genspec.sh variables
#

# kernel package name
%global package_name kernel
%global gemini 0
# Include Fedora files
%global include_fedora 0
# Include RHEL files
%global include_rhel 1
# Include RT files
%global include_rt 1
# Include Automotive files
%global include_automotive 1
# Provide Patchlist.changelog file
%global patchlist_changelog 0
# Set released_kernel to 1 when the upstream source tarball contains a
#  kernel release. (This includes prepatch or "rc" releases.)
# Set released_kernel to 0 when the upstream source tarball contains an
#  unreleased kernel development snapshot.
%global released_kernel 0
# Set debugbuildsenabled to 1 to build separate base and debug kernels
#  (on supported architectures). The kernel-debug-* subpackages will
#  contain the debug kernel.
# Set debugbuildsenabled to 0 to not build a separate debug kernel, but
#  to build the base kernel using the debug configuration. (Specifying
#  the --with-release option overrides this setting.)
%define debugbuildsenabled 1
# define buildid .local
%define specrpmversion 6.12.0
%define specversion 6.12.0
%define patchversion 6.12
%define pkgrelease 55.12.1
%define kversion 6
%define tarfile_release 6.12.0-55.12.1.el10_0
# This is needed to do merge window version magic
%define patchlevel 12
# This allows pkg_release to have configurable %%{?dist} tag
%define specrelease 55.12.1%{?buildid}%{?dist}
# This defines the kabi tarball version
%define kabiversion 6.12.0-55.12.1.el10_0

# If this variable is set to 1, a bpf selftests build failure will cause a
# fatal kernel package build error
%define selftests_must_build 0

#
# End of genspec.sh variables
#

%define pkg_release %{specrelease}

# libexec dir is not used by the linker, so the shared object there
# should not be exported to RPM provides
%global __provides_exclude_from ^%{_libexecdir}/kselftests

%define _with_kabidupchk 1
# The following build options are (mostly) enabled by default, but may become
# enabled/disabled by later architecture-specific checks.
# Where disabled by default, they can be enabled by using --with <opt> in the
# rpmbuild command, or by forcing these values to 1.
# Where enabled by default, they can be disabled by using --without <opt> in
# the rpmbuild command, or by forcing these values to 0.
#
# standard kernel
%define with_up        %{?_without_up:        0} %{?!_without_up:        1}
# build the base variants
%define with_base      %{?_without_base:      0} %{?!_without_base:      1}
# build also debug variants
%define with_debug     %{?_without_debug:     0} %{?!_without_debug:     1}
# kernel-zfcpdump (s390 specific kernel for zfcpdump)
%define with_zfcpdump  %{?_without_zfcpdump:  0} %{?!_without_zfcpdump:  1}
# kernel-16k (aarch64 kernel with 16K page_size)
%define with_arm64_16k %{?_with_arm64_16k:    1} %{?!_with_arm64_16k:    0}
# kernel-64k (aarch64 kernel with 64K page_size)
%define with_arm64_64k %{?_without_arm64_64k: 0} %{?!_without_arm64_64k: 1}
# kernel-rt (x86_64 and aarch64 only PREEMPT_RT enabled kernel)
%define with_realtime  %{?_without_realtime:  0} %{?!_without_realtime:  1}
# kernel-rt-64k (aarch64 RT kernel with 64K page_size)
%define with_realtime_arm64_64k %{?_without_realtime_arm64_64k: 0} %{?!_without_realtime_arm64_64k: 1}
# kernel-automotive (x86_64 and aarch64 with PREEMPT_RT enabled - currently off by default)
%define with_automotive %{?_with_automotive:  1} %{?!_with_automotive:   0}

# Supported variants
#            with_base with_debug    with_gcov
# up         X         X             X
# zfcpdump   X                       X
# arm64_16k  X         X             X
# arm64_64k  X         X             X
# realtime   X         X             X
# automotive X         X             X

# kernel-doc
%define with_doc       %{?_without_doc:       0} %{?!_without_doc:       1}
# kernel-headers
%define with_headers   %{?_without_headers:   0} %{?!_without_headers:   1}
%define with_cross_headers   %{?_without_cross_headers:   0} %{?!_without_cross_headers:   1}
# perf
%define with_perf      %{?_without_perf:      0} %{?!_without_perf:      1}
# libperf
%define with_libperf   %{?_without_libperf:   0} %{?!_without_libperf:   1}
# tools
%define with_tools     %{?_without_tools:     0} %{?!_without_tools:     1}
# ynl
%define with_ynl      %{?_without_ynl:      0} %{?!_without_ynl:      1}
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
# Only build the debug variants (--with dbgonly):
%define with_dbgonly   %{?_with_dbgonly:      1} %{?!_with_dbgonly:      0}
# Only build the realtime kernel (--with rtonly):
%define with_rtonly    %{?_with_rtonly:       1} %{?!_with_rtonly:       0}
# Only build the automotive kernel (--with automotiveonly):%
%define with_automotiveonly %{?_with_automotiveonly:       1} %{?!_with_automotiveonly:       0}
# Control whether we perform a compat. check against published ABI.
%define with_kabichk   %{?_without_kabichk:   0} %{?!_without_kabichk:   1}
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

%ifarch x86_64 aarch64 riscv64
%define with_efiuki %{?_without_efiuki: 0} %{?!_without_efiuki: 1}
%else
%define with_efiuki 0
%endif

%if 0%{?fedora}
# Kernel headers are being split out into a separate package
%define with_headers 0
%define with_cross_headers 0
# no ipa_clone for now
%define with_ipaclones 0
# no stablelist
%define with_kernel_abi_stablelists 0
%define with_arm64_64k 0
%define with_realtime 0
%define with_realtime_arm64_64k 0
%define with_automotive 0
%endif

%if %{with_verbose}
%define make_opts V=1
%else
%define make_opts -s
%endif

%if %{with toolchain_clang}
%ifarch s390x ppc64le
%global llvm_ias 0
%else
%global llvm_ias 1
%endif
%global clang_make_opts HOSTCC=clang CC=clang LLVM_IAS=%{llvm_ias}
%if %{with clang_lto}
# LLVM=1 enables use of all LLVM tools.
%global clang_make_opts %{clang_make_opts} LLVM=1
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

%define KVERREL %{specversion}-%{release}.%{_target_cpu}
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

# if requested, only build base kernel
%if %{with_baseonly}
%define with_debug 0
%define with_realtime 0
%define with_vdso_install 0
%define with_perf 0
%define with_libperf 0
%define with_tools 0
%define with_kernel_abi_stablelists 0
%define with_selftests 0
%define with_ipaclones 0
%endif

# if requested, only build debug kernel
%if %{with_dbgonly}
%define with_base 0
%define with_vdso_install 0
%define with_perf 0
%define with_libperf 0
%define with_tools 0
%define with_kernel_abi_stablelists 0
%define with_selftests 0
%define with_ipaclones 0
%endif

# if requested, only build realtime kernel
%if %{with_rtonly}
%define with_realtime 1
%define with_realtime_arm64_64k 1
%define with_automotive 0
%define with_up 0
%define with_debug 0
%define with_debuginfo 0
%define with_vdso_install 0
%define with_perf 0
%define with_libperf 0
%define with_tools 0
%define with_kernel_abi_stablelists 0
%define with_selftests 0
%define with_ipaclones 0
%define with_headers 0
%define with_efiuki 0
%define with_zfcpdump 0
%define with_arm64_16k 0
%define with_arm64_64k 0
%endif

# if requested, only build automotive kernel
%if %{with_automotiveonly}
%define with_automotive 1
%define with_realtime 0
%define with_up 0
%define with_debug 0
%define with_debuginfo 0
%define with_vdso_install 0
%define with_selftests 1
%endif

# RT and Automotive kernels are only built on x86_64 and aarch64
%ifnarch x86_64 aarch64
%define with_realtime 0
%define with_automotive 0
%endif

%if %{with_automotive}
# overrides compression algorithms for automotive
%global compression zstd
%global compression_flags --rm
%global compext zst

# automotive does not support the following variants
%define with_realtime 0
%define with_realtime_arm64_64k 0
%define with_arm64_16k 0
%define with_arm64_64k 0
%define with_efiuki 0
%define with_doc 0
%define with_headers 0
%define with_cross_headers 0
%define with_perf 0
%define with_libperf 0
%define with_tools 0
%define with_kabichk 0
%define with_kernel_abi_stablelists 0
%define with_kabidw_base 0
%define with_ipaclones 0
%endif


%if %{zipmodules}
%global zipsed -e 's/\.ko$/\.ko.%compext/'
# for parallel xz processes, replace with 1 to go back to single process
%endif

# turn off kABI DUP check and DWARF-based check if kABI check is disabled
%if !%{with_kabichk}
%define with_kabidupchk 0
%define with_kabidwchk 0
%endif

%if %{with_vdso_install}
%define use_vdso 1
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
# don't do debug builds on anything but aarch64 and x86_64
%ifnarch aarch64 x86_64
%define with_debug 0
%endif
%endif

%define all_configs %{name}-%{specrpmversion}-*.config

# don't build noarch kernels or headers (duh)
%ifarch noarch
%define with_up 0
%define with_realtime 0
%define with_automotive 0
%define with_headers 0
%define with_cross_headers 0
%define with_tools 0
%define with_perf 0
%define with_libperf 0
%define with_selftests 0
%define with_debug 0
%endif

# sparse blows up on ppc
%ifnarch ppc64le
%define with_sparse 0
%endif

# zfcpdump mechanism is s390 only
%ifnarch s390x
%define with_zfcpdump 0
%endif

# 16k and 64k variants only for aarch64
%ifnarch aarch64
%define with_arm64_16k 0
%define with_arm64_64k 0
%define with_realtime_arm64_64k 0
%endif

%if 0%{?fedora}
# This is not for Fedora
%define with_zfcpdump 0
%endif

# Per-arch tweaks

%ifarch i686
%define asmarch x86
%define hdrarch i386
%define kernel_image arch/x86/boot/bzImage
%endif

%ifarch x86_64
%define asmarch x86
%define kernel_image arch/x86/boot/bzImage
%endif

%ifarch ppc64le
%define asmarch powerpc
%define hdrarch powerpc
%define make_target vmlinux
%define kernel_image vmlinux
%define kernel_image_elf 1
%define use_vdso 0
%endif

%ifarch s390x
%define asmarch s390
%define hdrarch s390
%define kernel_image arch/s390/boot/bzImage
%define vmlinux_decompressor arch/s390/boot/vmlinux
%endif

%ifarch aarch64
%define asmarch arm64
%define hdrarch arm64
%define make_target vmlinuz.efi
%define kernel_image arch/arm64/boot/vmlinuz.efi
%endif

%ifarch riscv64
%define asmarch riscv
%define hdrarch riscv
%define make_target vmlinuz.efi
%define kernel_image arch/riscv/boot/vmlinuz.efi
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
%define nobuildarches i386 i686
%endif

%ifarch %nobuildarches
# disable BuildKernel commands
%define with_up 0
%define with_debug 0
%define with_zfcpdump 0
%define with_arm64_16k 0
%define with_arm64_64k 0
%define with_realtime 0
%define with_realtime_arm64_64k 0
%define with_automotive 0

%define with_debuginfo 0
%define with_perf 0
%define with_libperf 0
%define with_tools 0
%define with_selftests 0
%define _enable_debug_packages 0
%endif

# Architectures we build tools/cpupower on
%if 0%{?fedora}
%define cpupowerarchs %{ix86} x86_64 ppc64le aarch64
%else
%define cpupowerarchs i686 x86_64 ppc64le aarch64
%endif

# Architectures we build kernel livepatching selftests on
%define klptestarches x86_64 ppc64le s390x

%if 0%{?use_vdso}
%define _use_vdso 1
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

# short-hand for "are we building base/non-debug variants of ...?"
%if %{with_up} && %{with_base}
%define with_up_base 1
%else
%define with_up_base 0
%endif
%if %{with_realtime} && %{with_base}
%define with_realtime_base 1
%else
%define with_realtime_base 0
%endif
%if %{with_automotive} && %{with_base}
%define with_automotive_base 1
%else
%define with_automotive_base 0
%endif
%if %{with_arm64_16k} && %{with_base}
%define with_arm64_16k_base 1
%else
%define with_arm64_16k_base 0
%endif
%if %{with_arm64_64k} && %{with_base}
%define with_arm64_64k_base 1
%else
%define with_arm64_64k_base 0
%endif
%if %{with_realtime_arm64_64k} && %{with_base}
%define with_realtime_arm64_64k_base 1
%else
%define with_realtime_arm64_64k_base 0
%endif

#
# Packages that need to be installed before the kernel is, because the %%post
# scripts use them.
#
%define kernel_prereq  coreutils, systemd >= 203-2, /usr/bin/kernel-install
%define initrd_prereq  dracut >= 027


Name: %{package_name}
License: ((GPL-2.0-only WITH Linux-syscall-note) OR BSD-2-Clause) AND ((GPL-2.0-only WITH Linux-syscall-note) OR BSD-3-Clause) AND ((GPL-2.0-only WITH Linux-syscall-note) OR CDDL-1.0) AND ((GPL-2.0-only WITH Linux-syscall-note) OR Linux-OpenIB) AND ((GPL-2.0-only WITH Linux-syscall-note) OR MIT) AND ((GPL-2.0-or-later WITH Linux-syscall-note) OR BSD-3-Clause) AND ((GPL-2.0-or-later WITH Linux-syscall-note) OR MIT) AND 0BSD AND BSD-2-Clause AND (BSD-2-Clause OR Apache-2.0) AND BSD-3-Clause AND BSD-3-Clause-Clear AND CC0-1.0 AND GFDL-1.1-no-invariants-or-later AND GPL-1.0-or-later AND (GPL-1.0-or-later OR BSD-3-Clause) AND (GPL-1.0-or-later WITH Linux-syscall-note) AND GPL-2.0-only AND (GPL-2.0-only OR Apache-2.0) AND (GPL-2.0-only OR BSD-2-Clause) AND (GPL-2.0-only OR BSD-3-Clause) AND (GPL-2.0-only OR CDDL-1.0) AND (GPL-2.0-only OR GFDL-1.1-no-invariants-or-later) AND (GPL-2.0-only OR GFDL-1.2-no-invariants-only) AND (GPL-2.0-only WITH Linux-syscall-note) AND GPL-2.0-or-later AND (GPL-2.0-or-later OR BSD-2-Clause) AND (GPL-2.0-or-later OR BSD-3-Clause) AND (GPL-2.0-or-later OR CC-BY-4.0) AND (GPL-2.0-or-later WITH GCC-exception-2.0) AND (GPL-2.0-or-later WITH Linux-syscall-note) AND ISC AND LGPL-2.0-or-later AND (LGPL-2.0-or-later OR BSD-2-Clause) AND (LGPL-2.0-or-later WITH Linux-syscall-note) AND LGPL-2.1-only AND (LGPL-2.1-only OR BSD-2-Clause) AND (LGPL-2.1-only WITH Linux-syscall-note) AND LGPL-2.1-or-later AND (LGPL-2.1-or-later WITH Linux-syscall-note) AND (Linux-OpenIB OR GPL-2.0-only) AND (Linux-OpenIB OR GPL-2.0-only OR BSD-2-Clause) AND Linux-man-pages-copyleft AND MIT AND (MIT OR Apache-2.0) AND (MIT OR GPL-2.0-only) AND (MIT OR GPL-2.0-or-later) AND (MIT OR LGPL-2.1-only) AND (MPL-1.1 OR GPL-2.0-only) AND (X11 OR GPL-2.0-only) AND (X11 OR GPL-2.0-or-later) AND Zlib AND (copyleft-next-0.3.1 OR GPL-2.0-or-later)
URL: https://www.kernel.org/
Version: %{specrpmversion}
Release: %{pkg_release}
# DO NOT CHANGE THE 'ExclusiveArch' LINE TO TEMPORARILY EXCLUDE AN ARCHITECTURE BUILD.
# SET %%nobuildarches (ABOVE) INSTEAD
%if 0%{?fedora}
ExclusiveArch: noarch x86_64 s390x aarch64 ppc64le riscv64
%else
ExclusiveArch: noarch i386 i686 x86_64 s390x aarch64 ppc64le riscv64
%endif
ExclusiveOS: Linux
%ifnarch %{nobuildarches}
Requires: kernel-core-uname-r = %{KVERREL}
Requires: kernel-modules-uname-r = %{KVERREL}
Requires: kernel-modules-core-uname-r = %{KVERREL}
Provides: installonlypkg(kernel)
%endif


#
# List the packages used during the kernel build
#
BuildRequires: kmod, bash, coreutils, tar, git-core, which
BuildRequires: bzip2, xz, findutils, m4, perl-interpreter, perl-Carp, perl-devel, perl-generators, make, diffutils, gawk, %compression
BuildRequires: gcc, binutils, redhat-rpm-config, hmaccalc, bison, flex, gcc-c++
%if 0%{?fedora}
BuildRequires: rust, rust-src, bindgen
%endif
BuildRequires: net-tools, hostname, bc, elfutils-devel
BuildRequires: dwarves
BuildRequires: python3
BuildRequires: python3-devel
BuildRequires: python3-pyyaml
BuildRequires: kernel-rpm-macros
# glibc-static is required for a consistent build environment (specifically
# CONFIG_CC_CAN_LINK_STATIC=y).
BuildRequires: glibc-static
%if %{with_headers} || %{with_cross_headers}
BuildRequires: rsync
%endif
%if %{with_doc}
BuildRequires: xmlto, asciidoc, python3-sphinx, python3-sphinx_rtd_theme
%endif
%if %{with_sparse}
BuildRequires: sparse
%endif
%if %{with_perf}
BuildRequires: zlib-devel binutils-devel newt-devel perl(ExtUtils::Embed) bison flex xz-devel
BuildRequires: audit-libs-devel python3-setuptools
BuildRequires: java-devel
BuildRequires: libbpf-devel >= 0.6.0-1
BuildRequires: libbabeltrace-devel
BuildRequires: libtraceevent-devel
%ifnarch s390x
BuildRequires: numactl-devel
%endif
%ifarch aarch64
BuildRequires: opencsd-devel >= 1.0.0
%endif
%endif
%if %{with_tools}
BuildRequires: python3-docutils
BuildRequires: gettext ncurses-devel
BuildRequires: libcap-devel libcap-ng-devel
# The following are rtla requirements
BuildRequires: python3-docutils
BuildRequires: libtraceevent-devel
BuildRequires: libtracefs-devel

%ifnarch s390x
BuildRequires: pciutils-devel
%endif
%ifarch i686 x86_64
BuildRequires: libnl3-devel
%endif
%endif

%if %{with_tools} && %{with_ynl}
BuildRequires: python3-pyyaml python3-jsonschema python3-pip python3-setuptools python3-wheel
%endif

%if %{with_tools} || %{signmodules} || %{signkernel}
BuildRequires: openssl-devel
%endif
%if %{with_selftests}
BuildRequires: clang llvm-devel fuse-devel zlib-devel binutils-devel
%ifarch x86_64 riscv64
BuildRequires: lld
%endif
BuildRequires: libcap-devel libcap-ng-devel rsync libmnl-devel libxml2-devel
BuildRequires: numactl-devel
%endif
BuildConflicts: rhbuildsys(DiskFree) < 500Mb
%if %{with_debuginfo}
BuildRequires: rpm-build, elfutils
BuildConflicts: rpm < 4.13.0.1-19
BuildConflicts: dwarves < 1.13
# Most of these should be enabled after more investigation
%undefine _include_minidebuginfo
%undefine _find_debuginfo_dwz_opts
%undefine _unique_build_ids
%undefine _unique_debug_names
%undefine _unique_debug_srcs
%undefine _debugsource_packages
%undefine _debuginfo_subpackages

# Remove -q option below to provide 'extracting debug info' messages
%global _find_debuginfo_opts -r -q

%global _missing_build_ids_terminate_build 1
%global _no_recompute_build_ids 1
%endif
%if %{with_kabidwchk} || %{with_kabidw_base}
BuildRequires: kabi-dw
%endif

%if %{signkernel}%{signmodules}
BuildRequires: openssl
%if %{signkernel}
# ELN uses Fedora signing process, so exclude
%if 0%{?rhel}%{?centos} && !0%{?eln}
BuildRequires: system-sb-certs
%endif
%ifarch x86_64 aarch64 riscv64
BuildRequires: nss-tools
BuildRequires: pesign >= 0.10-4
%endif
%endif
%endif

%if %{with_cross}
BuildRequires: binutils-%{_build_arch}-linux-gnu, gcc-%{_build_arch}-linux-gnu
%define cross_opts CROSS_COMPILE=%{_build_arch}-linux-gnu-
%define __strip %{_build_arch}-linux-gnu-strip

# Work around find-debuginfo for cross builds.
# find-debuginfo doesn't support any of CROSS options (RHEL-21797),
# and since debugedit > 5.0-16.el10, or since commit
#   dfe1f7ff30f4 ("find-debuginfo.sh: Exit with real exit status in parallel jobs")
# it now aborts and build fails.
%undefine _include_gdb_index
%endif

# These below are required to build man pages
%if %{with_perf}
BuildRequires: xmlto
%endif
%if %{with_perf} || %{with_tools}
BuildRequires: asciidoc
%endif

%if %{with toolchain_clang}
BuildRequires: clang
%endif

%if %{with clang_lto}
BuildRequires: llvm
BuildRequires: lld
%endif

%if %{with_efiuki}
BuildRequires: dracut >= 104
# For dracut UEFI uki binaries
BuildRequires: binutils
# For the initrd
BuildRequires: lvm2
BuildRequires: systemd-boot-unsigned
# For systemd-stub and systemd-pcrphase
BuildRequires: systemd-udev >= 252-1
# For UKI kernel cmdline addons
BuildRequires: systemd-ukify
# For TPM operations in UKI initramfs
BuildRequires: tpm2-tools
# For UKI sb cert
%if 0%{?rhel}%{?centos} && !0%{?eln}
%if 0%{?centos}
BuildRequires: centos-sb-certs >= 9.0-23
%else
BuildRequires: redhat-sb-certs >= 9.4-0.1
%endif
%endif
%endif

# Because this is the kernel, it's hard to get a single upstream URL
# to represent the base without needing to do a bunch of patching. This
# tarball is generated from a src-git tree. If you want to see the
# exact git commit you can run
#
# xzcat -qq ${TARBALL} | git get-tar-commit-id
Source0: linux-%{tarfile_release}.tar.xz

Source1: Makefile.rhelver
Source2: kernel.changelog

Source10: redhatsecurebootca5.cer
Source13: redhatsecureboot501.cer

%if %{signkernel}
# Name of the packaged file containing signing key
%ifarch ppc64le
%define signing_key_filename kernel-signing-ppc.cer
%endif
%ifarch s390x
%define signing_key_filename kernel-signing-s390.cer
%endif

# Fedora/ELN pesign macro expects to see these cert file names, see:
# https://github.com/rhboot/pesign/blob/main/src/pesign-rpmbuild-helper.in#L216
%if 0%{?fedora}%{?eln}
%define pesign_name_0 redhatsecureboot501
%define secureboot_ca_0 %{SOURCE10}
%define secureboot_key_0 %{SOURCE13}
%endif

# RHEL/centos certs come from system-sb-certs
%if 0%{?rhel} && !0%{?eln}
%define secureboot_ca_0 %{_datadir}/pki/sb-certs/secureboot-ca-%{_arch}.cer
%define secureboot_key_0 %{_datadir}/pki/sb-certs/secureboot-kernel-%{_arch}.cer
%define pesign_name_0 rockysigning
%endif
%endif

Source20: mod-denylist.sh
Source21: mod-sign.sh
Source22: filtermods.py

%define modsign_cmd %{SOURCE21}

%if 0%{?include_rhel}
Source23: x509.genkey.rhel

Source24: %{name}-aarch64-rhel.config
Source25: %{name}-aarch64-debug-rhel.config

Source27: %{name}-ppc64le-rhel.config
Source28: %{name}-ppc64le-debug-rhel.config
Source29: %{name}-s390x-rhel.config
Source30: %{name}-s390x-debug-rhel.config
Source31: %{name}-s390x-zfcpdump-rhel.config
Source32: %{name}-x86_64-rhel.config
Source33: %{name}-x86_64-debug-rhel.config
Source1000: %{name}-riscv64-rhel.config
Source1001: %{name}-riscv64-debug-rhel.config

Source34: def_variants.yaml.rhel

Source41: x509.genkey.centos
# ARM64 64K page-size kernel config
Source42: %{name}-aarch64-64k-rhel.config
Source43: %{name}-aarch64-64k-debug-rhel.config

%endif

%if 0%{?include_fedora}
Source50: x509.genkey.fedora

Source52: %{name}-aarch64-fedora.config
Source53: %{name}-aarch64-debug-fedora.config
Source54: %{name}-aarch64-16k-fedora.config
Source55: %{name}-aarch64-16k-debug-fedora.config
Source56: %{name}-ppc64le-fedora.config
Source57: %{name}-ppc64le-debug-fedora.config
Source58: %{name}-s390x-fedora.config
Source59: %{name}-s390x-debug-fedora.config
Source60: %{name}-x86_64-fedora.config
Source61: %{name}-x86_64-debug-fedora.config
Source700: %{name}-riscv64-fedora.config
Source701: %{name}-riscv64-debug-fedora.config

Source62: def_variants.yaml.fedora
%endif

Source70: partial-kgcov-snip.config
Source71: partial-kgcov-debug-snip.config
Source72: partial-clang-snip.config
Source73: partial-clang-debug-snip.config
Source74: partial-clang_lto-x86_64-snip.config
Source75: partial-clang_lto-x86_64-debug-snip.config
Source76: partial-clang_lto-aarch64-snip.config
Source77: partial-clang_lto-aarch64-debug-snip.config
Source80: generate_all_configs.sh
Source81: process_configs.sh

Source86: dracut-virt.conf

Source87: flavors

Source151: uki_create_addons.py
Source152: uki_addons.json

Source100: rockydup1.x509
Source101: rockykpatch1.x509
Source102: rocky-nvidiagpuoot101.x509
Source110: rockydup1-aarch64.x509
Source111: rockykpatch1-aarch64.x509
Source112: rocky-nvidiagpuoot101-aarch64.x509
Source103: rocky-ima-ca.crt
Source104: rocky-imarelease.crt
Source106: fedoraimaca.x509

%if 0%{?fedora}%{?eln}
%define ima_ca_cert %{SOURCE106}
%endif

%if 0%{?rhel} && !0%{?eln}
%define ima_ca_cert %{SOURCE103}
# rhel && !eln
%endif

%ifarch aarch64
%define driver_cert %{SOURCE110}
%define kpatch_cert %{SOURCE111}
%define nvidia_cert %{SOURCE112}
%else
%define driver_cert %{SOURCE100}
%define kpatch_cert %{SOURCE101}
%define nvidia_cert %{SOURCE102}
%endif

%define ima_signing_cert %{SOURCE104}
%define ima_cert_name ima.cer

Source200: check-kabi

Source201: Module.kabi_aarch64
Source202: Module.kabi_ppc64le
Source203: Module.kabi_s390x
Source204: Module.kabi_x86_64
Source205: Module.kabi_riscv64

Source210: Module.kabi_dup_aarch64
Source211: Module.kabi_dup_ppc64le
Source212: Module.kabi_dup_s390x
Source213: Module.kabi_dup_x86_64
Source214: Module.kabi_dup_riscv64

Source300: kernel-abi-stablelists-%{kabiversion}.tar.xz
Source301: kernel-kabi-dw-%{kabiversion}.tar.xz

%if 0%{include_rt}
%if 0%{include_rhel}
Source474: %{name}-aarch64-rt-rhel.config
Source475: %{name}-aarch64-rt-debug-rhel.config
Source476: %{name}-aarch64-rt-64k-rhel.config
Source477: %{name}-aarch64-rt-64k-debug-rhel.config
Source478: %{name}-x86_64-rt-rhel.config
Source479: %{name}-x86_64-rt-debug-rhel.config
%endif
%if 0%{include_fedora}
Source478: %{name}-aarch64-rt-fedora.config
Source479: %{name}-aarch64-rt-debug-fedora.config
Source480: %{name}-aarch64-rt-64k-fedora.config
Source481: %{name}-aarch64-rt-64k-debug-fedora.config
Source482: %{name}-x86_64-rt-fedora.config
Source483: %{name}-x86_64-rt-debug-fedora.config
Source484: %{name}-riscv64-rt-fedora.config
Source485: %{name}-riscv64-rt-debug-fedora.config
%endif
%endif

%if %{include_automotive}
# automotive config files
Source486: %{name}-aarch64-automotive-rhel.config
Source487: %{name}-aarch64-automotive-debug-rhel.config
Source488: %{name}-x86_64-automotive-rhel.config
Source489: %{name}-x86_64-automotive-debug-rhel.config
%endif


# Sources for kernel-tools
Source2002: kvm_stat.logrotate

# Some people enjoy building customized kernels from the dist-git in Fedora and
# use this to override configuration options. One day they may all use the
# source tree, but in the mean time we carry this to support the legacy workflow
Source3000: merge.py
Source3001: kernel-local
%if %{patchlist_changelog}
Source3002: Patchlist.changelog
%endif

Source4000: README.rst
Source4001: rpminspect.yaml
Source4002: gating.yaml

## Patches needed for building this package

%if !%{nopatches}

Patch1: patch-%{patchversion}-redhat.patch
%endif

# empty final patch to facilitate testing of kernel patches
Patch999999: linux-kernel-test.patch
Patch1000000: 1000-debrand-some-messages.patch
Patch1000001: 1001-fix-riscv.patch

# END OF PATCH DEFINITIONS

%description
The kernel meta package

#
# This macro does requires, provides, conflicts, obsoletes for a kernel package.
#	%%kernel_reqprovconf [-o] <subpackage>
# It uses any kernel_<subpackage>_conflicts and kernel_<subpackage>_obsoletes
# macros defined above.
#
%define kernel_reqprovconf(o) \
%if %{-o:0}%{!-o:1}\
Provides: kernel = %{specversion}-%{pkg_release}\
%endif\
Provides: kernel-%{_target_cpu} = %{specrpmversion}-%{pkg_release}%{uname_suffix %{?1:+%{1}}}\
Provides: kernel-uname-r = %{KVERREL}%{uname_suffix %{?1:+%{1}}}\
Requires: kernel%{?1:-%{1}}-modules-core-uname-r = %{KVERREL}%{uname_suffix %{?1:+%{1}}}\
Requires(pre): %{kernel_prereq}\
Requires(pre): %{initrd_prereq}\
Requires(pre): ((linux-firmware >= 20150904-56.git6ebf5d57) if linux-firmware)\
Recommends: linux-firmware\
Requires(preun): systemd >= 200\
Conflicts: xfsprogs < 4.3.0-1\
Conflicts: xorg-x11-drv-vmmouse < 13.0.99\
%{expand:%%{?kernel%{?1:_%{1}}_conflicts:Conflicts: %%{kernel%{?1:_%{1}}_conflicts}}}\
%{expand:%%{?kernel%{?1:_%{1}}_obsoletes:Obsoletes: %%{kernel%{?1:_%{1}}_obsoletes}}}\
%{expand:%%{?kernel%{?1:_%{1}}_provides:Provides: %%{kernel%{?1:_%{1}}_provides}}}\
# We can't let RPM do the dependencies automatic because it'll then pick up\
# a correct but undesirable perl dependency from the module headers which\
# isn't required for the kernel proper to function\
AutoReq: no\
AutoProv: yes\
%{nil}


%package doc
Summary: Various documentation bits found in the kernel source
Group: Documentation
%description doc
This package contains documentation files from the kernel
source. Various bits of information about the Linux kernel and the
device drivers shipped with it are documented in these files.

You'll want to install this package if you need a reference to the
options that can be passed to Linux kernel modules at load time.


%package headers
Summary: Header files for the Linux kernel for use by glibc
Obsoletes: glibc-kernheaders < 3.0-46
Provides: glibc-kernheaders = 3.0-46
%if 0%{?gemini}
Provides: kernel-headers = %{specversion}-%{release}
Obsoletes: kernel-headers < %{specversion}
%endif
%description headers
Kernel-headers includes the C header files that specify the interface
between the Linux kernel and userspace libraries and programs.  The
header files define structures and constants that are needed for
building most standard programs and are also needed for rebuilding the
glibc package.

%package cross-headers
Summary: Header files for the Linux kernel for use by cross-glibc
%if 0%{?gemini}
Provides: kernel-cross-headers = %{specversion}-%{release}
Obsoletes: kernel-cross-headers < %{specversion}
%endif
%description cross-headers
Kernel-cross-headers includes the C header files that specify the interface
between the Linux kernel and userspace libraries and programs.  The
header files define structures and constants that are needed for
building most standard programs and are also needed for rebuilding the
cross-glibc package.

%package debuginfo-common-%{_target_cpu}
Summary: Kernel source files used by %{name}-debuginfo packages
Provides: installonlypkg(kernel)
%description debuginfo-common-%{_target_cpu}
This package is required by %{name}-debuginfo subpackages.
It provides the kernel source files common to all builds.

%if %{with_perf}
%package -n perf
%if 0%{gemini}
Epoch: %{gemini}
%endif
Summary: Performance monitoring for the Linux kernel
Requires: bzip2
%description -n perf
This package contains the perf tool, which enables performance monitoring
of the Linux kernel.

%package -n perf-debuginfo
%if 0%{gemini}
Epoch: %{gemini}
%endif
Summary: Debug information for package perf
Requires: %{name}-debuginfo-common-%{_target_cpu} = %{specrpmversion}-%{release}
AutoReqProv: no
%description -n perf-debuginfo
This package provides debug information for the perf package.

# Note that this pattern only works right to match the .build-id
# symlinks because of the trailing nonmatching alternation and
# the leading .*, because of find-debuginfo.sh's buggy handling
# of matching the pattern against the symlinks file.
%{expand:%%global _find_debuginfo_opts %{?_find_debuginfo_opts} -p '.*%%{_bindir}/perf(\.debug)?|.*%%{_libexecdir}/perf-core/.*|.*%%{_libdir}/libperf-jvmti.so(\.debug)?|XXX' -o perf-debuginfo.list}

%package -n python3-perf
%if 0%{gemini}
Epoch: %{gemini}
%endif
Summary: Python bindings for apps which will manipulate perf events
%description -n python3-perf
The python3-perf package contains a module that permits applications
written in the Python programming language to use the interface
to manipulate perf events.

%package -n python3-perf-debuginfo
%if 0%{gemini}
Epoch: %{gemini}
%endif
Summary: Debug information for package perf python bindings
Requires: %{name}-debuginfo-common-%{_target_cpu} = %{specrpmversion}-%{release}
AutoReqProv: no
%description -n python3-perf-debuginfo
This package provides debug information for the perf python bindings.

# the python_sitearch macro should already be defined from above
%{expand:%%global _find_debuginfo_opts %{?_find_debuginfo_opts} -p '.*%%{python3_sitearch}/perf.*so(\.debug)?|XXX' -o python3-perf-debuginfo.list}

# with_perf
%endif

%if %{with_libperf}
%package -n libperf
Summary: The perf library from kernel source
%description -n libperf
This package contains the kernel source perf library.

%package -n libperf-devel
Summary: Developement files for the perf library from kernel source
Requires: libperf = %{version}-%{release}
%description -n libperf-devel
This package includes libraries and header files needed for development
of applications which use perf library from kernel source.

%package -n libperf-debuginfo
Summary: Debug information for package libperf
Group: Development/Debug
Requires: %{name}-debuginfo-common-%{_target_cpu} = %{version}-%{release}
AutoReqProv: no
%description -n libperf-debuginfo
This package provides debug information for the libperf package.

# Note that this pattern only works right to match the .build-id
# symlinks because of the trailing nonmatching alternation and
# the leading .*, because of find-debuginfo.sh's buggy handling
# of matching the pattern against the symlinks file.
%{expand:%%global _find_debuginfo_opts %{?_find_debuginfo_opts} -p '.*%%{_libdir}/libperf.so.*(\.debug)?|XXX' -o libperf-debuginfo.list}
# with_libperf
%endif

%if %{with_tools}
%package -n %{package_name}-tools
Summary: Assortment of tools for the Linux kernel
%ifarch %{cpupowerarchs}
Provides: cpupowerutils = 1:009-0.6.p1
Obsoletes: cpupowerutils < 1:009-0.6.p1
Provides: cpufreq-utils = 1:009-0.6.p1
Provides: cpufrequtils = 1:009-0.6.p1
Obsoletes: cpufreq-utils < 1:009-0.6.p1
Obsoletes: cpufrequtils < 1:009-0.6.p1
Obsoletes: cpuspeed < 1:1.5-16
Requires: %{package_name}-tools-libs = %{specrpmversion}-%{release}
%endif
%define __requires_exclude ^%{_bindir}/python
%description -n %{package_name}-tools
This package contains the tools/ directory from the kernel source
and the supporting documentation.

%package -n %{package_name}-tools-libs
Summary: Libraries for the kernels-tools
%description -n %{package_name}-tools-libs
This package contains the libraries built from the tools/ directory
from the kernel source.

%package -n %{package_name}-tools-libs-devel
Summary: Assortment of tools for the Linux kernel
Requires: %{package_name}-tools = %{version}-%{release}
%ifarch %{cpupowerarchs}
Provides: cpupowerutils-devel = 1:009-0.6.p1
Obsoletes: cpupowerutils-devel < 1:009-0.6.p1
%endif
Requires: %{package_name}-tools-libs = %{version}-%{release}
Provides: %{package_name}-tools-devel
%description -n %{package_name}-tools-libs-devel
This package contains the development files for the tools/ directory from
the kernel source.

%package -n %{package_name}-tools-debuginfo
Summary: Debug information for package %{package_name}-tools
Requires: %{name}-debuginfo-common-%{_target_cpu} = %{version}-%{release}
AutoReqProv: no
%description -n %{package_name}-tools-debuginfo
This package provides debug information for package %{package_name}-tools.

# Note that this pattern only works right to match the .build-id
# symlinks because of the trailing nonmatching alternation and
# the leading .*, because of find-debuginfo.sh's buggy handling
# of matching the pattern against the symlinks file.
%{expand:%%global _find_debuginfo_opts %{?_find_debuginfo_opts} -p '.*%%{_bindir}/bootconfig(\.debug)?|.*%%{_bindir}/centrino-decode(\.debug)?|.*%%{_bindir}/powernow-k8-decode(\.debug)?|.*%%{_bindir}/cpupower(\.debug)?|.*%%{_libdir}/libcpupower.*|.*%%{_bindir}/turbostat(\.debug)?|.*%%{_bindir}/x86_energy_perf_policy(\.debug)?|.*%%{_bindir}/tmon(\.debug)?|.*%%{_bindir}/lsgpio(\.debug)?|.*%%{_bindir}/gpio-hammer(\.debug)?|.*%%{_bindir}/gpio-event-mon(\.debug)?|.*%%{_bindir}/gpio-watch(\.debug)?|.*%%{_bindir}/iio_event_monitor(\.debug)?|.*%%{_bindir}/iio_generic_buffer(\.debug)?|.*%%{_bindir}/lsiio(\.debug)?|.*%%{_bindir}/intel-speed-select(\.debug)?|.*%%{_bindir}/page_owner_sort(\.debug)?|.*%%{_bindir}/slabinfo(\.debug)?|.*%%{_sbindir}/intel_sdsi(\.debug)?|XXX' -o %{package_name}-tools-debuginfo.list}

%package -n rtla
%if 0%{gemini}
Epoch: %{gemini}
%endif
Summary: Real-Time Linux Analysis tools
Requires: libtraceevent
Requires: libtracefs
%ifarch %{cpupowerarchs}
Requires: %{package_name}-tools-libs = %{version}-%{release}
%endif
%description -n rtla
The rtla meta-tool includes a set of commands that aims to analyze
the real-time properties of Linux. Instead of testing Linux as a black box,
rtla leverages kernel tracing capabilities to provide precise information
about the properties and root causes of unexpected results.

%package -n rv
Summary: RV: Runtime Verification
%description -n rv
Runtime Verification (RV) is a lightweight (yet rigorous) method that
complements classical exhaustive verification techniques (such as model
checking and theorem proving) with a more practical approach for
complex systems.
The rv tool is the interface for a collection of monitors that aim
analysing the logical and timing behavior of Linux.

# with_tools
%endif

%if %{with_selftests}

%package selftests-internal
Summary: Kernel samples and selftests
Requires: binutils, bpftool, iproute-tc, nmap-ncat, python3, fuse-libs, keyutils
%description selftests-internal
Kernel sample programs and selftests.

# Note that this pattern only works right to match the .build-id
# symlinks because of the trailing nonmatching alternation and
# the leading .*, because of find-debuginfo.sh's buggy handling
# of matching the pattern against the symlinks file.
%{expand:%%global _find_debuginfo_opts %{?_find_debuginfo_opts} -p '.*%%{_libexecdir}/(ksamples|kselftests)/.*|XXX' -o selftests-debuginfo.list}

%define __requires_exclude ^liburandom_read.so.*$

# with_selftests
%endif

%define kernel_gcov_package() \
%package %{?1:%{1}-}gcov\
Summary: gcov graph and source files for coverage data collection.\
%description %{?1:%{1}-}gcov\
%{?1:%{1}-}gcov includes the gcov graph and source files for gcov coverage collection.\
%{nil}

%package -n %{package_name}-abi-stablelists
Summary: The Rocky Linux kernel ABI symbol stablelists
AutoReqProv: no
%description -n %{package_name}-abi-stablelists
The kABI package contains information pertaining to the Rocky
Linux kernel ABI, including lists of kernel symbols that are needed by
external Linux kernel modules, and a yum plugin to aid enforcement.

%if %{with_kabidw_base}
%package kernel-kabidw-base-internal
Summary: The baseline dataset for kABI verification using DWARF data
Group: System Environment/Kernel
AutoReqProv: no
%description kernel-kabidw-base-internal
The package contains data describing the current ABI of the Rocky
Linux kernel, suitable for the kabi-dw tool.
%endif

#
# This macro creates a kernel-<subpackage>-debuginfo package.
#	%%kernel_debuginfo_package <subpackage>
#
# Explanation of the find_debuginfo_opts: We build multiple kernels (debug,
# rt, 64k etc.) so the regex filters those kernels appropriately. We also
# have to package several binaries as part of kernel-devel but getting
# unique build-ids is tricky for these userspace binaries. We don't really
# care about debugging those so we just filter those out and remove it.
%define kernel_debuginfo_package() \
%package %{?1:%{1}-}debuginfo\
Summary: Debug information for package %{name}%{?1:-%{1}}\
Requires: %{name}-debuginfo-common-%{_target_cpu} = %{specrpmversion}-%{release}\
Provides: %{name}%{?1:-%{1}}-debuginfo-%{_target_cpu} = %{specrpmversion}-%{release}\
Provides: installonlypkg(kernel)\
AutoReqProv: no\
%description %{?1:%{1}-}debuginfo\
This package provides debug information for package %{name}%{?1:-%{1}}.\
This is required to use SystemTap with %{name}%{?1:-%{1}}-%{KVERREL}.\
%{expand:%%global _find_debuginfo_opts %{?_find_debuginfo_opts} --keep-section '.BTF' -p '.*\/usr\/src\/kernels/.*|XXX' -o ignored-debuginfo.list -p '/.*/%%{KVERREL_RE}%{?1:[+]%{1}}/.*|/.*%%{KVERREL_RE}%{?1:\+%{1}}(\.debug)?' -o debuginfo%{?1}.list}\
%{nil}

#
# This macro creates a kernel-<subpackage>-devel package.
#	%%kernel_devel_package [-m] <subpackage> <pretty-name>
#
%define kernel_devel_package(m) \
%package %{?1:%{1}-}devel\
Summary: Development package for building kernel modules to match the %{?2:%{2} }kernel\
Provides: kernel%{?1:-%{1}}-devel-%{_target_cpu} = %{specrpmversion}-%{release}\
Provides: kernel-devel-%{_target_cpu} = %{specrpmversion}-%{release}%{uname_suffix %{?1:+%{1}}}\
Provides: kernel-devel-uname-r = %{KVERREL}%{uname_suffix %{?1:+%{1}}}\
Provides: installonlypkg(kernel)\
AutoReqProv: no\
Requires(pre): findutils\
Requires: findutils\
Requires: perl-interpreter\
Requires: openssl-devel\
Requires: elfutils-libelf-devel\
Requires: bison\
Requires: flex\
Requires: make\
Requires: gcc\
%if %{-m:1}%{!-m:0}\
Requires: kernel-devel-uname-r = %{KVERREL}%{uname_variant %{?1:%{1}}}\
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
Summary: Meta package to install matching core and devel packages for a given %{?2:%{2} }kernel\
Requires: %{package_name}%{?1:-%{1}}-devel = %{specrpmversion}-%{release}\
Requires: %{package_name}%{?1:-%{1}}-core = %{specrpmversion}-%{release}\
%description %{?1:%{1}-}devel-matched\
This meta package is used to install matching core and devel packages for a given %{?2:%{2} }kernel.\
%{nil}

#
# kernel-<variant>-ipaclones-internal package
#
%define kernel_ipaclones_package() \
%package %{?1:%{1}-}ipaclones-internal\
Summary: *.ipa-clones files generated by -fdump-ipa-clones for kernel%{?1:-%{1}}\
Group: System Environment/Kernel\
AutoReqProv: no\
%description %{?1:%{1}-}ipaclones-internal\
This package provides *.ipa-clones files.\
%{nil}

#
# This macro creates a kernel-<subpackage>-modules-internal package.
#	%%kernel_modules_internal_package <subpackage> <pretty-name>
#
%define kernel_modules_internal_package() \
%package %{?1:%{1}-}modules-internal\
Summary: Extra kernel modules to match the %{?2:%{2} }kernel\
Group: System Environment/Kernel\
Provides: kernel%{?1:-%{1}}-modules-internal-%{_target_cpu} = %{specrpmversion}-%{release}\
Provides: kernel%{?1:-%{1}}-modules-internal-%{_target_cpu} = %{specrpmversion}-%{release}%{uname_suffix %{?1:+%{1}}}\
Provides: kernel%{?1:-%{1}}-modules-internal = %{specrpmversion}-%{release}%{uname_suffix %{?1:+%{1}}}\
Provides: installonlypkg(kernel-module)\
Provides: kernel%{?1:-%{1}}-modules-internal-uname-r = %{KVERREL}%{uname_suffix %{?1:+%{1}}}\
Requires: kernel-uname-r = %{KVERREL}%{uname_suffix %{?1:+%{1}}}\
Requires: kernel%{?1:-%{1}}-modules-uname-r = %{KVERREL}%{uname_suffix %{?1:+%{1}}}\
Requires: kernel%{?1:-%{1}}-modules-core-uname-r = %{KVERREL}%{uname_suffix %{?1:+%{1}}}\
AutoReq: no\
AutoProv: yes\
%description %{?1:%{1}-}modules-internal\
This package provides kernel modules for the %{?2:%{2} }kernel package for Red Hat internal usage.\
%{nil}

#
# This macro creates a kernel-<subpackage>-modules-extra package.
#	%%kernel_modules_extra_package [-m] <subpackage> <pretty-name>
#
%define kernel_modules_extra_package(m) \
%package %{?1:%{1}-}modules-extra\
Summary: Extra kernel modules to match the %{?2:%{2} }kernel\
Provides: kernel%{?1:-%{1}}-modules-extra-%{_target_cpu} = %{specrpmversion}-%{release}\
Provides: kernel%{?1:-%{1}}-modules-extra-%{_target_cpu} = %{specrpmversion}-%{release}%{uname_suffix %{?1:+%{1}}}\
Provides: kernel%{?1:-%{1}}-modules-extra = %{specrpmversion}-%{release}%{uname_suffix %{?1:+%{1}}}\
Provides: installonlypkg(kernel-module)\
Provides: kernel%{?1:-%{1}}-modules-extra-uname-r = %{KVERREL}%{uname_suffix %{?1:+%{1}}}\
Requires: kernel-uname-r = %{KVERREL}%{uname_suffix %{?1:+%{1}}}\
Requires: kernel%{?1:-%{1}}-modules-uname-r = %{KVERREL}%{uname_suffix %{?1:+%{1}}}\
Requires: kernel%{?1:-%{1}}-modules-core-uname-r = %{KVERREL}%{uname_suffix %{?1:+%{1}}}\
%if %{-m:1}%{!-m:0}\
Requires: kernel-modules-extra-uname-r = %{KVERREL}%{uname_variant %{?1:+%{1}}}\
%endif\
AutoReq: no\
AutoProv: yes\
%description %{?1:%{1}-}modules-extra\
This package provides less commonly used kernel modules for the %{?2:%{2} }kernel package.\
%{nil}

#
# This macro creates a kernel-<subpackage>-modules package.
#	%%kernel_modules_package [-m] <subpackage> <pretty-name>
#
%define kernel_modules_package(m) \
%package %{?1:%{1}-}modules\
Summary: kernel modules to match the %{?2:%{2}-}core kernel\
Provides: kernel%{?1:-%{1}}-modules-%{_target_cpu} = %{specrpmversion}-%{release}\
Provides: kernel-modules-%{_target_cpu} = %{specrpmversion}-%{release}%{uname_suffix %{?1:+%{1}}}\
Provides: kernel-modules = %{specrpmversion}-%{release}%{uname_suffix %{?1:+%{1}}}\
Provides: installonlypkg(kernel-module)\
Provides: kernel%{?1:-%{1}}-modules-uname-r = %{KVERREL}%{uname_suffix %{?1:+%{1}}}\
Requires: kernel-uname-r = %{KVERREL}%{uname_suffix %{?1:+%{1}}}\
Requires: kernel%{?1:-%{1}}-modules-core-uname-r = %{KVERREL}%{uname_suffix %{?1:+%{1}}}\
%if %{-m:1}%{!-m:0}\
Requires: kernel-modules-uname-r = %{KVERREL}%{uname_variant %{?1:+%{1}}}\
%endif\
AutoReq: no\
AutoProv: yes\
%description %{?1:%{1}-}modules\
This package provides commonly used kernel modules for the %{?2:%{2}-}core kernel package.\
%{nil}

#
# This macro creates a kernel-<subpackage>-modules-core package.
#	%%kernel_modules_core_package [-m] <subpackage> <pretty-name>
#
%define kernel_modules_core_package(m) \
%package %{?1:%{1}-}modules-core\
Summary: Core kernel modules to match the %{?2:%{2}-}core kernel\
Provides: kernel%{?1:-%{1}}-modules-core-%{_target_cpu} = %{specrpmversion}-%{release}\
Provides: kernel-modules-core-%{_target_cpu} = %{specrpmversion}-%{release}%{uname_suffix %{?1:+%{1}}}\
Provides: kernel-modules-core = %{specrpmversion}-%{release}%{uname_suffix %{?1:+%{1}}}\
Provides: installonlypkg(kernel-module)\
Provides: kernel%{?1:-%{1}}-modules-core-uname-r = %{KVERREL}%{uname_suffix %{?1:+%{1}}}\
Requires: kernel-uname-r = %{KVERREL}%{uname_suffix %{?1:+%{1}}}\
%if %{-m:1}%{!-m:0}\
Requires: kernel-modules-core-uname-r = %{KVERREL}%{uname_variant %{?1:+%{1}}}\
%endif\
AutoReq: no\
AutoProv: yes\
%description %{?1:%{1}-}modules-core\
This package provides essential kernel modules for the %{?2:%{2}-}core kernel package.\
%{nil}

#
# this macro creates a kernel-<subpackage> meta package.
#	%%kernel_meta_package <subpackage>
#
%define kernel_meta_package() \
%package %{1}\
summary: kernel meta-package for the %{1} kernel\
Requires: kernel-%{1}-core-uname-r = %{KVERREL}%{uname_suffix %{1}}\
Requires: kernel-%{1}-modules-uname-r = %{KVERREL}%{uname_suffix %{1}}\
Requires: kernel-%{1}-modules-core-uname-r = %{KVERREL}%{uname_suffix %{1}}\
%if "%{1}" == "rt" || "%{1}" == "rt-debug" || "%{1}" == "rt-64k" || "%{1}" == "rt-64k-debug"\
Requires: realtime-setup\
%endif\
Provides: installonlypkg(kernel)\
%description %{1}\
The meta-package for the %{1} kernel\
%{nil}

%if %{with_realtime} || %{with_realtime_arm64_64k}
#
# this macro creates a kernel-rt-<subpackage>-kvm package
# %%kernel_kvm_package <subpackage>
#
%define kernel_kvm_package() \
%package %{?1:%{1}-}kvm\
Summary: KVM modules for package kernel%{?1:-%{1}}\
Group: System Environment/Kernel\
Requires: kernel-uname-r = %{KVERREL}%{uname_suffix %{?1:%{1}}}\
Requires: kernel%{?1:-%{1}}-modules-core-uname-r = %{KVERREL}%{uname_suffix %{?1:+%{1}}}\
Provides: installonlypkg(kernel-module)\
Provides: kernel%{?1:-%{1}}-kvm-%{_target_cpu} = %{version}-%{release}\
AutoReq: no\
%description -n kernel%{?1:-%{1}}-kvm\
This package provides KVM modules for package kernel%{?1:-%{1}}.\
%{nil}
%endif

#
# This macro creates a kernel-<subpackage> and its -devel and -debuginfo too.
#	%%define variant_summary The Linux kernel compiled for <configuration>
#	%%kernel_variant_package [-n <pretty-name>] [-m] [-o] <subpackage>
#
%define kernel_variant_package(n:mo) \
%package %{?1:%{1}-}core\
Summary: %{variant_summary}\
Provides: kernel-%{?1:%{1}-}core-uname-r = %{KVERREL}%{uname_suffix %{?1:+%{1}}}\
Provides: installonlypkg(kernel)\
%if %{-m:1}%{!-m:0}\
Requires: kernel-core-uname-r = %{KVERREL}%{uname_variant %{?1:+%{1}}}\
Requires: kernel-%{?1:%{1}-}-modules-core-uname-r = %{KVERREL}%{uname_variant %{?1:+%{1}}}\
%endif\
%{expand:%%kernel_reqprovconf %{?1:%{1}} %{-o:%{-o}}}\
%if %{?1:1} %{!?1:0} \
%{expand:%%kernel_meta_package %{?1:%{1}}}\
%endif\
%{expand:%%kernel_devel_package %{?1:%{1}} %{!?{-n}:%{1}}%{?{-n}:%{-n*}} %{-m:%{-m}}}\
%{expand:%%kernel_devel_matched_package %{?1:%{1}} %{!?{-n}:%{1}}%{?{-n}:%{-n*}} %{-m:%{-m}}}\
%{expand:%%kernel_modules_package %{?1:%{1}} %{!?{-n}:%{1}}%{?{-n}:%{-n*}} %{-m:%{-m}}}\
%{expand:%%kernel_modules_core_package %{?1:%{1}} %{!?{-n}:%{1}}%{?{-n}:%{-n*}} %{-m:%{-m}}}\
%{expand:%%kernel_modules_extra_package %{?1:%{1}} %{!?{-n}:%{1}}%{?{-n}:%{-n*}} %{-m:%{-m}}}\
%if %{-m:0}%{!-m:1}\
%{expand:%%kernel_modules_internal_package %{?1:%{1}} %{!?{-n}:%{1}}%{?{-n}:%{-n*}}}\
%if 0%{!?fedora:1}\
%{expand:%%kernel_modules_partner_package %{?1:%{1}} %{!?{-n}:%{1}}%{?{-n}:%{-n*}}}\
%endif\
%{expand:%%kernel_debuginfo_package %{?1:%{1}}}\
%endif\
%if "%{1}" == "rt" || "%{1}" == "rt-debug" || "%{1}" == "rt-64k" || "%{1}" == "rt-64k-debug"\
%{expand:%%kernel_kvm_package %{?1:%{1}} %{!?{-n}:%{1}}%{?{-n}:%{-n*}}}\
%else \
%if %{with_efiuki}\
%package %{?1:%{1}-}uki-virt\
Summary: %{variant_summary} unified kernel image for virtual machines\
Provides: installonlypkg(kernel)\
Provides: kernel-uname-r = %{KVERREL}%{uname_suffix %{?1:+%{1}}}\
Requires: kernel%{?1:-%{1}}-modules-core-uname-r = %{KVERREL}%{uname_suffix %{?1:+%{1}}}\
Requires(pre): %{kernel_prereq}\
Requires(pre): systemd >= 254-1\
%package %{?1:%{1}-}uki-virt-addons\
Summary: %{variant_summary} unified kernel image addons for virtual machines\
Provides: installonlypkg(kernel)\
Requires: kernel%{?1:-%{1}}-uki-virt = %{specrpmversion}-%{release}\
Requires(pre): systemd >= 254-1\
%endif\
%endif\
%if %{with_gcov}\
%{expand:%%kernel_gcov_package %{?1:%{1}}}\
%endif\
%{nil}

#
# This macro creates a kernel-<subpackage>-modules-partner package.
#	%%kernel_modules_partner_package <subpackage> <pretty-name>
#
%define kernel_modules_partner_package() \
%package %{?1:%{1}-}modules-partner\
Summary: Extra kernel modules to match the %{?2:%{2} }kernel\
Group: System Environment/Kernel\
Provides: kernel%{?1:-%{1}}-modules-partner-%{_target_cpu} = %{specrpmversion}-%{release}\
Provides: kernel%{?1:-%{1}}-modules-partner-%{_target_cpu} = %{specrpmversion}-%{release}%{uname_suffix %{?1:+%{1}}}\
Provides: kernel%{?1:-%{1}}-modules-partner = %{specrpmversion}-%{release}%{uname_suffix %{?1:+%{1}}}\
Provides: installonlypkg(kernel-module)\
Provides: kernel%{?1:-%{1}}-modules-partner-uname-r = %{KVERREL}%{uname_suffix %{?1:+%{1}}}\
Requires: kernel-uname-r = %{KVERREL}%{uname_suffix %{?1:+%{1}}}\
Requires: kernel%{?1:-%{1}}-modules-uname-r = %{KVERREL}%{uname_suffix %{?1:+%{1}}}\
Requires: kernel%{?1:-%{1}}-modules-core-uname-r = %{KVERREL}%{uname_suffix %{?1:+%{1}}}\
AutoReq: no\
AutoProv: yes\
%description %{?1:%{1}-}modules-partner\
This package provides kernel modules for the %{?2:%{2} }kernel package for Red Hat partners usage.\
%{nil}

# Now, each variant package.
%if %{with_zfcpdump}
%define variant_summary The Linux kernel compiled for zfcpdump usage
%kernel_variant_package -o zfcpdump
%description zfcpdump-core
The kernel package contains the Linux kernel (vmlinuz) for use by the
zfcpdump infrastructure.
# with_zfcpdump
%endif

%if %{with_arm64_16k_base}
%define variant_summary The Linux kernel compiled for 16k pagesize usage
%kernel_variant_package 16k
%description 16k-core
The kernel package contains a variant of the ARM64 Linux kernel using
a 16K page size.
%endif

%if %{with_arm64_16k} && %{with_debug}
%define variant_summary The Linux kernel compiled with extra debugging enabled
%if !%{debugbuildsenabled}
%kernel_variant_package -m 16k-debug
%else
%kernel_variant_package 16k-debug
%endif
%description 16k-debug-core
The debug kernel package contains a variant of the ARM64 Linux kernel using
a 16K page size.
This variant of the kernel has numerous debugging options enabled.
It should only be installed when trying to gather additional information
on kernel bugs, as some of these options impact performance noticably.
%endif

%if %{with_arm64_64k_base}
%define variant_summary The Linux kernel compiled for 64k pagesize usage
%kernel_variant_package 64k
%description 64k-core
The kernel package contains a variant of the ARM64 Linux kernel using
a 64K page size.
%endif

%if %{with_arm64_64k} && %{with_debug}
%define variant_summary The Linux kernel compiled with extra debugging enabled
%if !%{debugbuildsenabled}
%kernel_variant_package -m 64k-debug
%else
%kernel_variant_package 64k-debug
%endif
%description 64k-debug-core
The debug kernel package contains a variant of the ARM64 Linux kernel using
a 64K page size.
This variant of the kernel has numerous debugging options enabled.
It should only be installed when trying to gather additional information
on kernel bugs, as some of these options impact performance noticably.
%endif

%if %{with_debug} && %{with_realtime}
%define variant_summary The Linux PREEMPT_RT kernel compiled with extra debugging enabled
%kernel_variant_package rt-debug
%description rt-debug-core
The kernel package contains the Linux kernel (vmlinuz), the core of any
Linux operating system.  The kernel handles the basic functions
of the operating system:  memory allocation, process allocation, device
input and output, etc.

This variant of the kernel has numerous debugging options enabled.
It should only be installed when trying to gather additional information
on kernel bugs, as some of these options impact performance noticably.
%endif

%if %{with_realtime_base}
%define variant_summary The Linux kernel compiled with PREEMPT_RT enabled
%kernel_variant_package rt
%description rt-core
This package includes a version of the Linux kernel compiled with the
PREEMPT_RT real-time preemption support
%endif

%if %{with_realtime_arm64_64k_base}
%define variant_summary The Linux PREEMPT_RT kernel compiled for 64k pagesize usage
%kernel_variant_package rt-64k
%description rt-64k-core
The kernel package contains a variant of the ARM64 Linux PREEMPT_RT kernel using
a 64K page size.
%endif

%if %{with_realtime_arm64_64k} && %{with_debug}
%define variant_summary The Linux PREEMPT_RT kernel compiled with extra debugging enabled
%if !%{debugbuildsenabled}
%kernel_variant_package -m rt-64k-debug
%else
%kernel_variant_package rt-64k-debug
%endif
%description rt-64k-debug-core
The debug kernel package contains a variant of the ARM64 Linux PREEMPT_RT kernel using
a 64K page size.
This variant of the kernel has numerous debugging options enabled.
It should only be installed when trying to gather additional information
on kernel bugs, as some of these options impact performance noticably.
%endif

%if %{with_debug} && %{with_automotive}
%define variant_summary The Linux Automotive kernel compiled with extra debugging enabled
%kernel_variant_package automotive-debug
%description automotive-debug-core
The kernel package contains the Linux kernel (vmlinuz), the core of any
Linux operating system.  The kernel handles the basic functions
of the operating system:  memory allocation, process allocation, device
input and output, etc.

This variant of the kernel has numerous debugging options enabled.
It should only be installed when trying to gather additional information
on kernel bugs, as some of these options impact performance noticably.
%endif

%if %{with_automotive_base}
%define variant_summary The Linux kernel compiled with PREEMPT_RT enabled
%kernel_variant_package automotive
%description automotive-core
This package includes a version of the Linux kernel compiled with the
PREEMPT_RT real-time preemption support, targeted for Automotive platforms
%endif

%if %{with_up} && %{with_debug}
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
%endif

%if %{with_up_base}
# And finally the main -core package

%define variant_summary The Linux kernel
%kernel_variant_package
%description core
The kernel package contains the Linux kernel (vmlinuz), the core of any
Linux operating system.  The kernel handles the basic functions
of the operating system: memory allocation, process allocation, device
input and output, etc.
%endif

%if %{with_up} && %{with_debug} && %{with_efiuki}
%description debug-uki-virt
Prebuilt debug unified kernel image for virtual machines.

%description debug-uki-virt-addons
Prebuilt debug unified kernel image addons for virtual machines.
%endif

%if %{with_up_base} && %{with_efiuki}
%description uki-virt
Prebuilt default unified kernel image for virtual machines.

%description uki-virt-addons
Prebuilt default unified kernel image addons for virtual machines.
%endif

%if %{with_arm64_16k} && %{with_debug} && %{with_efiuki}
%description 16k-debug-uki-virt
Prebuilt 16k debug unified kernel image for virtual machines.

%description 16k-debug-uki-virt-addons
Prebuilt 16k debug unified kernel image addons for virtual machines.
%endif

%if %{with_arm64_16k_base} && %{with_efiuki}
%description 16k-uki-virt
Prebuilt 16k unified kernel image for virtual machines.

%description 16k-uki-virt-addons
Prebuilt 16k unified kernel image addons for virtual machines.
%endif

%if %{with_arm64_64k} && %{with_debug} && %{with_efiuki}
%description 64k-debug-uki-virt
Prebuilt 64k debug unified kernel image for virtual machines.

%description 64k-debug-uki-virt-addons
Prebuilt 64k debug unified kernel image addons for virtual machines.
%endif

%if %{with_arm64_64k_base} && %{with_efiuki}
%description 64k-uki-virt
Prebuilt 64k unified kernel image for virtual machines.

%description 64k-uki-virt-addons
Prebuilt 64k unified kernel image addons for virtual machines.
%endif

%if %{with_ipaclones}
%kernel_ipaclones_package
%endif

%define log_msg() \
	{ set +x; } 2>/dev/null \
	_log_msglineno=$(grep -n %{*} %{_specdir}/${RPM_PACKAGE_NAME}.spec | grep log_msg | cut -d":" -f1) \
	echo "kernel.spec:${_log_msglineno}: %{*}" \
	set -x

%prep
%{log_msg "Start of prep stage"}

%{log_msg "Sanity checks"}

# do a few sanity-checks for --with *only builds
%if %{with_baseonly}
%if !%{with_up}
%{log_msg "Cannot build --with baseonly, up build is disabled"}
exit 1
%endif
%endif

# more sanity checking; do it quietly
if [ "%{patches}" != "%%{patches}" ] ; then
  for patch in %{patches} ; do
    if [ ! -f $patch ] ; then
	%{log_msg "ERROR: Patch  ${patch##/*/}  listed in specfile but is missing"}
      exit 1
    fi
  done
fi 2>/dev/null

patch_command='git --work-tree=. apply'
ApplyPatch()
{
  local patch=$1
  shift
  if [ ! -f $RPM_SOURCE_DIR/$patch ]; then
    exit 1
  fi
  if ! grep -E "^Patch[0-9]+: $patch\$" %{_specdir}/${RPM_PACKAGE_NAME}.spec ; then
    if [ "${patch:0:8}" != "patch-%{kversion}." ] ; then
	%{log_msg "ERROR: Patch  $patch  not listed as a source patch in specfile"}
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
  %{log_msg "ApplyOptionalPatch: $1"}
  if [ ! -f $RPM_SOURCE_DIR/$patch ]; then
    exit 1
  fi
  local C=$(wc -l $RPM_SOURCE_DIR/$patch | awk '{print $1}')
  if [ "$C" -gt 9 ]; then
    ApplyPatch $patch ${1+"$@"}
  fi
}

%{log_msg "Untar kernel tarball"}
%setup -q -n kernel-%{tarfile_release} -c
mv linux-%{tarfile_release} linux-%{KVERREL}

cd linux-%{KVERREL}
cp -a %{SOURCE1} .

%{log_msg "Start of patch applications"}
%if !%{nopatches}

ApplyOptionalPatch patch-%{patchversion}-redhat.patch
%endif

ApplyOptionalPatch 1000-debrand-some-messages.patch
%ifarch riscv64
ApplyOptionalPatch 1001-fix-riscv.patch
%endif
ApplyOptionalPatch linux-kernel-test.patch

%{log_msg "End of patch applications"}
# END OF PATCH APPLICATIONS

# Any further pre-build tree manipulations happen here.
%{log_msg "Pre-build tree manipulations"}
chmod +x scripts/checkpatch.pl
mv COPYING COPYING-%{specrpmversion}-%{release}

# on linux-next prevent scripts/setlocalversion from mucking with our version numbers
rm -f localversion-next localversion-rt

# Mangle /usr/bin/python shebangs to /usr/bin/python3
# Mangle all Python shebangs to be Python 3 explicitly
# -p preserves timestamps
# -n prevents creating ~backup files
# -i specifies the interpreter for the shebang
# This fixes errors such as
# *** ERROR: ambiguous python shebang in /usr/bin/kvm_stat: #!/usr/bin/python. Change it to python3 (or python2) explicitly.
# We patch all sources below for which we got a report/error.
%{log_msg "Fixing Python shebangs..."}
%py3_shebang_fix \
	tools/kvm/kvm_stat/kvm_stat \
	scripts/show_delta \
	scripts/diffconfig \
	scripts/bloat-o-meter \
	scripts/jobserver-exec \
	tools \
	Documentation \
	scripts/clang-tools 2> /dev/null

# only deal with configs if we are going to build for the arch
%ifnarch %nobuildarches

if [ -L configs ]; then
	rm -f configs
fi
mkdir configs
cd configs

%{log_msg "Copy additional source files into buildroot"}
# Drop some necessary files from the source dir into the buildroot
cp $RPM_SOURCE_DIR/%{name}-*.config .
cp %{SOURCE80} .
# merge.py
cp %{SOURCE3000} .
# kernel-local - rename and copy for partial snippet config process
cp %{SOURCE3001} partial-kernel-local-snip.config
cp %{SOURCE3001} partial-kernel-local-debug-snip.config
FLAVOR=%{primary_target} SPECPACKAGE_NAME=%{name} SPECVERSION=%{specversion} SPECRPMVERSION=%{specrpmversion} ./generate_all_configs.sh %{debugbuildsenabled}

# Collect custom defined config options
%{log_msg "Collect custom defined config options"}
PARTIAL_CONFIGS=""
%if %{with_gcov}
PARTIAL_CONFIGS="$PARTIAL_CONFIGS %{SOURCE70} %{SOURCE71}"
%endif
%if %{with toolchain_clang}
PARTIAL_CONFIGS="$PARTIAL_CONFIGS %{SOURCE72} %{SOURCE73}"
%endif
%if %{with clang_lto}
PARTIAL_CONFIGS="$PARTIAL_CONFIGS %{SOURCE74} %{SOURCE75} %{SOURCE76} %{SOURCE77}"
%endif
PARTIAL_CONFIGS="$PARTIAL_CONFIGS partial-kernel-local-snip.config partial-kernel-local-debug-snip.config"

GetArch()
{
  case "$1" in
  *aarch64*) echo "aarch64" ;;
  *ppc64le*) echo "ppc64le" ;;
  *s390x*) echo "s390x" ;;
  *x86_64*) echo "x86_64" ;;
  *riscv64*) echo "riscv64" ;;
  # no arch, apply everywhere
  *) echo "" ;;
  esac
}

# Merge in any user-provided local config option changes
%{log_msg "Merge in any user-provided local config option changes"}
%ifnarch %nobuildarches
for i in %{all_configs}
do
  kern_arch="$(GetArch $i)"
  kern_debug="$(echo $i | grep -q debug && echo "debug" || echo "")"

  for j in $PARTIAL_CONFIGS
  do
    part_arch="$(GetArch $j)"
    part_debug="$(echo $j | grep -q debug && echo "debug" || echo "")"

    # empty arch means apply to all arches
    if [ "$part_arch" == "" -o "$part_arch" == "$kern_arch" ] && [ "$part_debug" == "$kern_debug" ]
    then
      mv $i $i.tmp
      ./merge.py $j $i.tmp > $i
    fi
  done
  rm -f $i.tmp
done
%endif

%if %{signkernel}%{signmodules}

# Add DUP and kpatch certificates to system trusted keys for RHEL
%if 0%{?rhel}
%{log_msg "Add DUP and kpatch certificates to system trusted keys for Rocky Linux"}
openssl x509 -inform der -in %{driver_cert} -out rheldup3.pem
openssl x509 -inform der -in %{kpatch_cert} -out rhelkpatch1.pem
openssl x509 -inform der -in %{nvidia_cert} -out nvidiagpuoot001.pem
cat rheldup3.pem rhelkpatch1.pem nvidiagpuoot001.pem > ../certs/rhel.pem
%if %{signkernel}
%ifarch s390x ppc64le
openssl x509 -inform der -in %{secureboot_ca_0} -out secureboot.pem
cat secureboot.pem >> ../certs/rhel.pem
%endif
%endif

# rhel
%endif

openssl x509 -inform der -in %{ima_ca_cert} -out imaca.pem
cat imaca.pem >> ../certs/rhel.pem

for i in *.config; do
  sed -i 's@CONFIG_SYSTEM_TRUSTED_KEYS=""@CONFIG_SYSTEM_TRUSTED_KEYS="certs/rhel.pem"@' $i
done
%endif

# Adjust FIPS module name for RHEL
%if 0%{?rhel}
%{log_msg "Adjust FIPS module name for Rocky Linux"}
for i in *.config; do
  sed -i 's/CONFIG_CRYPTO_FIPS_NAME=.*/CONFIG_CRYPTO_FIPS_NAME="Rocky Linux %{rhel} - Kernel Cryptographic API"/' $i
done
%endif

%{log_msg "Set process_configs.sh $OPTS"}
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
%{log_msg "Generate redhat configs"}
RHJOBS=$RPM_BUILD_NCPUS SPECPACKAGE_NAME=%{name} ./process_configs.sh $OPTS %{specrpmversion}

# We may want to override files from the primary target in case of building
# against a flavour of it (eg. centos not rhel), thus override it here if
# necessary
update_scripts() {
	TARGET="$1"

	for i in "$RPM_SOURCE_DIR"/*."$TARGET"; do
		NEW=${i%."$TARGET"}
		cp "$i" "$(basename "$NEW")"
	done
}

%{log_msg "Set scripts/SOURCES targets"}
update_target=%{primary_target}
if [ "%{primary_target}" == "rhel" ]; then
: # no-op to avoid empty if-fi error
%if 0%{?centos}
  update_scripts $update_target
  %{log_msg "Updating scripts/sources to centos version"}
  update_target=centos
%endif
fi
update_scripts $update_target

%endif

%{log_msg "End of kernel config"}
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
%{log_msg "Start of build stage"}

%{log_msg "General arch build configuration"}
rm -rf %{buildroot_unstripped} || true
mkdir -p %{buildroot_unstripped}

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
    %{log_msg "InitBuildVars for $1"}

    %{log_msg "InitBuildVars: Initialize build variables"}
    # Initialize the kernel .config file and create some variables that are
    # needed for the actual build process.

    Variant=$1

    # Pick the right kernel config file
    Config=%{name}-%{specrpmversion}-%{_target_cpu}${Variant:+-${Variant}}.config
    DevelDir=/usr/src/kernels/%{KVERREL}${Variant:++${Variant}}

    KernelVer=%{specversion}-%{release}.%{_target_cpu}${Variant:++${Variant}}

    %{log_msg "InitBuildVars: Update Makefile"}
    # make sure EXTRAVERSION says what we want it to say
    # Trim the release if this is a CI build, since KERNELVERSION is limited to 64 characters
    ShortRel=$(perl -e "print \"%{release}\" =~ s/\.pr\.[0-9A-Fa-f]{32}//r")
    perl -p -i -e "s/^EXTRAVERSION.*/EXTRAVERSION = -${ShortRel}.%{_target_cpu}${Variant:++${Variant}}/" Makefile

    # if pre-rc1 devel kernel, must fix up PATCHLEVEL for our versioning scheme
    # if we are post rc1 this should match anyway so this won't matter
    perl -p -i -e 's/^PATCHLEVEL.*/PATCHLEVEL = %{patchlevel}/' Makefile

    %{log_msg "InitBuildVars: Copy files"}
    %{make} %{?_smp_mflags} mrproper
    cp configs/$Config .config

    %if %{signkernel}%{signmodules}
    cp configs/x509.genkey certs/.
    %endif

%if %{with_debuginfo} == 0
    sed -i 's/^\(CONFIG_DEBUG_INFO.*\)=y/# \1 is not set/' .config
%endif

    Arch=`head -1 .config | cut -b 3-`
    %{log_msg "InitBuildVars: USING ARCH=$Arch"}

    KCFLAGS="%{?kcflags}"

    # add kpatch flags for base kernel
    %{log_msg "InitBuildVars: Configure KCFLAGS"}
    if [ "$Variant" == "" ]; then
        KCFLAGS="$KCFLAGS %{?kpatch_kcflags}"
    fi
}

BuildKernel() {
    %{log_msg "BuildKernel for $4"}
    MakeTarget=$1
    KernelImage=$2
    DoVDSO=$3
    Variant=$4
    InstallName=${5:-vmlinuz}

    %{log_msg "Setup variables"}
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

%if %{with_gcov}
    %{log_msg "Setup build directories"}
    # Make build directory unique for each variant, so that gcno symlinks
    # are also unique for each variant.
    if [ -n "$Variant" ]; then
        ln -s $(pwd) ../linux-%{KVERREL}-${Variant}
    fi
    %{log_msg "GCOV - continuing build in: $(pwd)"}
    pushd ../linux-%{KVERREL}${Variant:+-${Variant}}
    pwd > ../kernel${Variant:+-${Variant}}-gcov.list
%endif

    %{log_msg "Calling InitBuildVars for $Variant"}
    InitBuildVars $Variant

    %{log_msg "BUILDING A KERNEL FOR ${Variant} %{_target_cpu}..."}

    %{make} ARCH=$Arch olddefconfig >/dev/null

    %{log_msg "Setup build-ids"}
    # This ensures build-ids are unique to allow parallel debuginfo
    perl -p -i -e "s/^CONFIG_BUILD_SALT.*/CONFIG_BUILD_SALT=\"%{KVERREL}\"/" .config
    %{make} ARCH=$Arch KCFLAGS="$KCFLAGS" WITH_GCOV="%{?with_gcov}" %{?_smp_mflags} $MakeTarget %{?sparse_mflags} %{?kernel_mflags}
    if [ $DoModules -eq 1 ]; then
	%{make} ARCH=$Arch KCFLAGS="$KCFLAGS" WITH_GCOV="%{?with_gcov}" %{?_smp_mflags} modules %{?sparse_mflags} || exit 1
    fi

    %{log_msg "Setup RPM_BUILD_ROOT directories"}
    mkdir -p $RPM_BUILD_ROOT/%{image_install_path}
    mkdir -p $RPM_BUILD_ROOT/lib/modules/$KernelVer
    mkdir -p $RPM_BUILD_ROOT/lib/modules/$KernelVer/systemtap
%if %{with_debuginfo}
    mkdir -p $RPM_BUILD_ROOT%{debuginfodir}/%{image_install_path}
%endif

%ifarch aarch64 riscv64
    %{log_msg "Build dtb kernel"}
    %{make} ARCH=$Arch dtbs INSTALL_DTBS_PATH=$RPM_BUILD_ROOT/%{image_install_path}/dtb-$KernelVer
    %{make} ARCH=$Arch dtbs_install INSTALL_DTBS_PATH=$RPM_BUILD_ROOT/%{image_install_path}/dtb-$KernelVer
    cp -r $RPM_BUILD_ROOT/%{image_install_path}/dtb-$KernelVer $RPM_BUILD_ROOT/lib/modules/$KernelVer/dtb
    find arch/$Arch/boot/dts -name '*.dtb' -type f -delete
%endif

    %{log_msg "Cleanup temp btf files"}
    # Remove large intermediate files we no longer need to save space
    # (-f required for zfcpdump builds that do not enable BTF)
    rm -f vmlinux.o .tmp_vmlinux.btf

    %{log_msg "Install files to RPM_BUILD_ROOT"}

    # Comment out specific config settings that may use resources not available
    # to the end user so that the packaged config file can be easily reused with
    # upstream make targets
    %if %{signkernel}%{signmodules}
      sed -i -e '/^CONFIG_SYSTEM_TRUSTED_KEYS/{
        i\# The kernel was built with
        s/^/# /
        a\# We are resetting this value to facilitate local builds
        a\CONFIG_SYSTEM_TRUSTED_KEYS=""
        }' .config
    %endif

    # Start installing the results
    install -m 644 .config $RPM_BUILD_ROOT/boot/config-$KernelVer
    install -m 644 .config $RPM_BUILD_ROOT/lib/modules/$KernelVer/config
    install -m 644 System.map $RPM_BUILD_ROOT/boot/System.map-$KernelVer
    install -m 644 System.map $RPM_BUILD_ROOT/lib/modules/$KernelVer/System.map

    %{log_msg "Create initrfamfs"}
    # We estimate the size of the initramfs because rpm needs to take this size
    # into consideration when performing disk space calculations. (See bz #530778)
    dd if=/dev/zero of=$RPM_BUILD_ROOT/boot/initramfs-$KernelVer.img bs=1M count=20

    if [ -f arch/$Arch/boot/zImage.stub ]; then
      %{log_msg "Copy zImage.stub to RPM_BUILD_ROOT"}
      cp arch/$Arch/boot/zImage.stub $RPM_BUILD_ROOT/%{image_install_path}/zImage.stub-$KernelVer || :
      cp arch/$Arch/boot/zImage.stub $RPM_BUILD_ROOT/lib/modules/$KernelVer/zImage.stub-$KernelVer || :
    fi

    %if %{signkernel}
    %{log_msg "Copy kernel for signing"}
    if [ "$KernelImage" = vmlinux ]; then
        # We can't strip and sign $KernelImage in place, because
        # we need to preserve original vmlinux for debuginfo.
        # Use a copy for signing.
        $CopyKernel $KernelImage $KernelImage.tosign
        KernelImage=$KernelImage.tosign
        CopyKernel=cp
    fi

    SignImage=$KernelImage

    %ifarch x86_64 aarch64
    %{log_msg "Sign kernel image"}
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
	%{log_msg "pesigning failed"}
        exit 1
    fi
    mv vmlinuz.signed $SignImage
    # signkernel
    %endif

    %{log_msg "copy signed kernel"}
    $CopyKernel $KernelImage \
                $RPM_BUILD_ROOT/%{image_install_path}/$InstallName-$KernelVer
    chmod 755 $RPM_BUILD_ROOT/%{image_install_path}/$InstallName-$KernelVer
    cp $RPM_BUILD_ROOT/%{image_install_path}/$InstallName-$KernelVer $RPM_BUILD_ROOT/lib/modules/$KernelVer/$InstallName

    # hmac sign the kernel for FIPS
    %{log_msg "hmac sign the kernel for FIPS"}
    %{log_msg "Creating hmac file: $RPM_BUILD_ROOT/%{image_install_path}/.vmlinuz-$KernelVer.hmac"}
    ls -l $RPM_BUILD_ROOT/%{image_install_path}/$InstallName-$KernelVer
    (cd $RPM_BUILD_ROOT/%{image_install_path} && sha512hmac $InstallName-$KernelVer) > $RPM_BUILD_ROOT/%{image_install_path}/.vmlinuz-$KernelVer.hmac;
    cp $RPM_BUILD_ROOT/%{image_install_path}/.vmlinuz-$KernelVer.hmac $RPM_BUILD_ROOT/lib/modules/$KernelVer/.vmlinuz.hmac

    if [ $DoModules -eq 1 ]; then
	%{log_msg "Install modules in RPM_BUILD_ROOT"}
	# Override $(mod-fw) because we don't want it to install any firmware
	# we'll get it from the linux-firmware package and we don't want conflicts
	%{make} %{?_smp_mflags} ARCH=$Arch INSTALL_MOD_PATH=$RPM_BUILD_ROOT %{?_smp_mflags} modules_install KERNELRELEASE=$KernelVer mod-fw=
    fi

%if %{with_gcov}
    %{log_msg "install gcov-needed files to $BUILDROOT/$BUILD/"}
    # install gcov-needed files to $BUILDROOT/$BUILD/...:
    #   gcov_info->filename is absolute path
    #   gcno references to sources can use absolute paths (e.g. in out-of-tree builds)
    #   sysfs symlink targets (set up at compile time) use absolute paths to BUILD dir
    find . \( -name '*.gcno' -o -name '*.[chS]' \) -exec install -D '{}' "$RPM_BUILD_ROOT/$(pwd)/{}" \;
%endif

    %{log_msg "Add VDSO files"}
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

    %{log_msg "Save headers/makefiles, etc. for kernel-headers"}
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
    %{log_msg "GENERATING kernel ABI metadata"}
    %compression --stdout %compression_flags < Module.symvers > $RPM_BUILD_ROOT/boot/symvers-$KernelVer.%compext
    cp $RPM_BUILD_ROOT/boot/symvers-$KernelVer.%compext $RPM_BUILD_ROOT/lib/modules/$KernelVer/symvers.%compext

%if %{with_kabichk}
    %{log_msg "kABI checking is enabled in kernel SPEC file."}
    chmod 0755 $RPM_SOURCE_DIR/check-kabi
    if [ -e $RPM_SOURCE_DIR/Module.kabi_%{_target_cpu}$Variant ]; then
        cp $RPM_SOURCE_DIR/Module.kabi_%{_target_cpu}$Variant $RPM_BUILD_ROOT/Module.kabi
        $RPM_SOURCE_DIR/check-kabi -k $RPM_BUILD_ROOT/Module.kabi -s Module.symvers || exit 1
        # for now, don't keep it around.
        rm $RPM_BUILD_ROOT/Module.kabi
    else
	%{log_msg "NOTE: Cannot find reference Module.kabi file."}
    fi
%endif

%if %{with_kabidupchk}
    %{log_msg "kABI DUP checking is enabled in kernel SPEC file."}
    if [ -e $RPM_SOURCE_DIR/Module.kabi_dup_%{_target_cpu}$Variant ]; then
        cp $RPM_SOURCE_DIR/Module.kabi_dup_%{_target_cpu}$Variant $RPM_BUILD_ROOT/Module.kabi
        $RPM_SOURCE_DIR/check-kabi -k $RPM_BUILD_ROOT/Module.kabi -s Module.symvers || exit 1
        # for now, don't keep it around.
        rm $RPM_BUILD_ROOT/Module.kabi
    else
	%{log_msg "NOTE: Cannot find DUP reference Module.kabi file."}
    fi
%endif

%if %{with_kabidw_base}
    # Don't build kabi base for debug kernels
    if [ "$Variant" != "zfcpdump" -a "$Variant" != "debug" ]; then
        mkdir -p $RPM_BUILD_ROOT/kabi-dwarf
        tar -xvf %{SOURCE301} -C $RPM_BUILD_ROOT/kabi-dwarf

        mkdir -p $RPM_BUILD_ROOT/kabi-dwarf/stablelists
        tar -xvf %{SOURCE300} -C $RPM_BUILD_ROOT/kabi-dwarf/stablelists

	%{log_msg "GENERATING DWARF-based kABI baseline dataset"}
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
        tar -xvf %{SOURCE301} -C $RPM_BUILD_ROOT/kabi-dwarf
        if [ -d "$RPM_BUILD_ROOT/kabi-dwarf/base/%{_target_cpu}${Variant:+.${Variant}}" ]; then
            mkdir -p $RPM_BUILD_ROOT/kabi-dwarf/stablelists
            tar -xvf %{SOURCE300} -C $RPM_BUILD_ROOT/kabi-dwarf/stablelists

	    %{log_msg "GENERATING DWARF-based kABI dataset"}
            chmod 0755 $RPM_BUILD_ROOT/kabi-dwarf/run_kabi-dw.sh
            $RPM_BUILD_ROOT/kabi-dwarf/run_kabi-dw.sh generate \
                "$RPM_BUILD_ROOT/kabi-dwarf/stablelists/kabi-current/kabi_stablelist_%{_target_cpu}" \
                "$(pwd)" \
                "$RPM_BUILD_ROOT/kabi-dwarf/base/%{_target_cpu}${Variant:+.${Variant}}.tmp" || :

	    %{log_msg "kABI DWARF-based comparison report"}
            $RPM_BUILD_ROOT/kabi-dwarf/run_kabi-dw.sh compare \
                "$RPM_BUILD_ROOT/kabi-dwarf/base/%{_target_cpu}${Variant:+.${Variant}}" \
                "$RPM_BUILD_ROOT/kabi-dwarf/base/%{_target_cpu}${Variant:+.${Variant}}.tmp" || :
	    %{log_msg "End of kABI DWARF-based comparison report"}
        else
	    %{log_msg "Baseline dataset for kABI DWARF-BASED comparison report not found"}
        fi

        rm -rf $RPM_BUILD_ROOT/kabi-dwarf
    fi
%endif

   %{log_msg "Cleanup Makefiles/Kconfig files"}
    # then drop all but the needed Makefiles/Kconfig files
    rm -rf $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/scripts
    rm -rf $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/include
    cp .config $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp -a scripts $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    rm -rf $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/scripts/tracing
    rm -f $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/scripts/spdxcheck.py

%ifarch s390x
    # CONFIG_EXPOLINE_EXTERN=y produces arch/s390/lib/expoline/expoline.o
    # which is needed during external module build.
    %{log_msg "Copy expoline.o"}
    if [ -f arch/s390/lib/expoline/expoline.o ]; then
      cp -a --parents arch/s390/lib/expoline/expoline.o $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    fi
%endif

    %{log_msg "Copy additional files for make targets"}
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
    cp --parents tools/build/fixdep.c $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp --parents tools/objtool/sync-check.sh $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp -a --parents tools/bpf/resolve_btfids $RPM_BUILD_ROOT/lib/modules/$KernelVer/build

    cp --parents security/selinux/include/policycap_names.h $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    cp --parents security/selinux/include/policycap.h $RPM_BUILD_ROOT/lib/modules/$KernelVer/build

    cp -a --parents tools/include/asm $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
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
    if [ -d tools/arch/%{asmarch}/include ]; then
      cp -a --parents tools/arch/%{asmarch}/include $RPM_BUILD_ROOT/lib/modules/$KernelVer/build
    fi
%ifarch aarch64
    # arch/arm64/include/asm/xen references arch/arm
    cp -a --parents arch/arm/include/asm/xen $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/
    # arch/arm64/include/asm/opcodes.h references arch/arm
    cp -a --parents arch/arm/include/asm/opcodes.h $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/
%endif
    cp -a include $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/include
    # Cross-reference from include/perf/events/sof.h
    cp -a sound/soc/sof/sof-audio.h $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/sound/soc/sof
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
    %{log_msg "Clean up intermediate tools files"}
    # Clean up intermediate tools files
    find $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/tools \( -iname "*.o" -o -iname "*.cmd" \) -exec rm -f {} +

    # Make sure the Makefile, version.h, and auto.conf have a matching
    # timestamp so that external modules can be built
    touch -r $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/Makefile \
        $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/include/generated/uapi/linux/version.h \
        $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/include/config/auto.conf

%if %{with_debuginfo}
    eu-readelf -n vmlinux | grep "Build ID" | awk '{print $NF}' > vmlinux.id
    cp vmlinux.id $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/vmlinux.id

    %{log_msg "Copy additional files for kernel-debuginfo rpm"}
    #
    # save the vmlinux file for kernel debugging into the kernel-debuginfo rpm
    # (use mv + symlink instead of cp to reduce disk space requirements)
    #
    mkdir -p $RPM_BUILD_ROOT%{debuginfodir}/lib/modules/$KernelVer
    mv vmlinux $RPM_BUILD_ROOT%{debuginfodir}/lib/modules/$KernelVer
    ln -s $RPM_BUILD_ROOT%{debuginfodir}/lib/modules/$KernelVer/vmlinux vmlinux
    if [ -n "%{?vmlinux_decompressor}" ]; then
	    eu-readelf -n  %{vmlinux_decompressor} | grep "Build ID" | awk '{print $NF}' > vmlinux.decompressor.id
	    # Without build-id the build will fail. But for s390 the build-id
	    # wasn't added before 5.11. In case it is missing prefer not
	    # packaging the debuginfo over a build failure.
	    if [ -s vmlinux.decompressor.id ]; then
		    cp vmlinux.decompressor.id $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/vmlinux.decompressor.id
		    cp %{vmlinux_decompressor} $RPM_BUILD_ROOT%{debuginfodir}/lib/modules/$KernelVer/vmlinux.decompressor
	    fi
    fi

    # build and copy the vmlinux-gdb plugin files into kernel-debuginfo
    %{make} ARCH=$Arch %{?_smp_mflags} scripts_gdb
    cp -a --parents scripts/gdb/{,linux/}*.py $RPM_BUILD_ROOT%{debuginfodir}/lib/modules/$KernelVer
    # this should be a relative symlink (Kbuild creates an absolute one)
    ln -s scripts/gdb/vmlinux-gdb.py $RPM_BUILD_ROOT%{debuginfodir}/lib/modules/$KernelVer/vmlinux-gdb.py
    %py_byte_compile %{python3} $RPM_BUILD_ROOT%{debuginfodir}/lib/modules/$KernelVer/scripts/gdb
%endif

    %{log_msg "Create modnames"}
    find $RPM_BUILD_ROOT/lib/modules/$KernelVer -name "*.ko" -type f >modnames

    # mark modules executable so that strip-to-file can strip them
    xargs --no-run-if-empty chmod u+x < modnames

    # Generate a list of modules for block and networking.
    %{log_msg "Generate a list of modules for block and networking"}
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

    %{log_msg "detect missing or incorrect license tags"}
    # detect missing or incorrect license tags
    ( find $RPM_BUILD_ROOT/lib/modules/$KernelVer -name '*.ko' | xargs /sbin/modinfo -l | \
        grep -E -v 'GPL( v2)?$|Dual BSD/GPL$|Dual MPL/GPL$|GPL and additional rights$' ) && exit 1


    if [ $DoModules -eq 0 ]; then
        %{log_msg "Create empty files for RPM packaging"}
        # Ensure important files/directories exist to let the packaging succeed
        echo '%%defattr(-,-,-)' > ../kernel${Variant:+-${Variant}}-modules-core.list
        echo '%%defattr(-,-,-)' > ../kernel${Variant:+-${Variant}}-modules.list
        echo '%%defattr(-,-,-)' > ../kernel${Variant:+-${Variant}}-modules-extra.list
        echo '%%defattr(-,-,-)' > ../kernel${Variant:+-${Variant}}-modules-internal.list
        echo '%%defattr(-,-,-)' > ../kernel${Variant:+-${Variant}}-modules-partner.list
        mkdir -p $RPM_BUILD_ROOT/lib/modules/$KernelVer/kernel
        # Add files usually created by make modules, needed to prevent errors
        # thrown by depmod during package installation
        touch $RPM_BUILD_ROOT/lib/modules/$KernelVer/modules.order
        touch $RPM_BUILD_ROOT/lib/modules/$KernelVer/modules.builtin
    fi

    # Copy the System.map file for depmod to use
    cp System.map $RPM_BUILD_ROOT/.

    if [[ "$Variant" == "rt" || "$Variant" == "rt-debug" || "$Variant" == "rt-64k" || "$Variant" == "rt-64k-debug" || "$Variant" == "automotive" || "$Variant" == "automotive-debug" ]]; then
	%{log_msg "Skipping efiuki build"}
    else
%if %{with_efiuki}
        %{log_msg "Setup the EFI UKI kernel"}

        # RHEL/CentOS specific .SBAT entries
%if 0%{?centos}
        SBATsuffix="rhel"
%else
        SBATsuffix="rhel"
%endif
        SBAT=$(cat <<- EOF
	linux,1,RESF,linux,$KernelVer,mailto:security@rockylinux.org
	linux.$SBATsuffix,1,Red Hat,linux,$KernelVer,mailto:secalert@redhat.com
	linux.rocky,1,RESF,linux,$KernelVer,mailto:security@rockylinux.org
	kernel-uki-virt.$SBATsuffix,1,Red Hat,kernel-uki-virt,$KernelVer,mailto:secalert@redhat.com
	kernel-uki-virt.rocky,1,RESF,kernel-uki-virt,$KernelVer,mailto:security@rockylinux.org
	EOF
	)

	KernelUnifiedImageDir="$RPM_BUILD_ROOT/lib/modules/$KernelVer"
    	KernelUnifiedImage="$KernelUnifiedImageDir/$InstallName-virt.efi"

    	mkdir -p $KernelUnifiedImageDir

    	dracut --conf=%{SOURCE86} \
           --confdir=$(mktemp -d) \
           --verbose \
           --kver "$KernelVer" \
           --kmoddir "$RPM_BUILD_ROOT/lib/modules/$KernelVer/" \
           --logfile=$(mktemp) \
           --uefi \
%if 0%{?rhel} && !0%{?eln}
           --sbat "$SBAT" \
%endif
           --kernel-image $(realpath $KernelImage) \
           --kernel-cmdline 'console=tty0 console=ttyS0' \
	   $KernelUnifiedImage

  KernelAddonsDirOut="$KernelUnifiedImage.extra.d"
  mkdir -p $KernelAddonsDirOut
  python3 %{SOURCE151} %{SOURCE152} $KernelAddonsDirOut virt %{primary_target} %{_target_cpu}

%if %{signkernel}
	%{log_msg "Sign the EFI UKI kernel"}
%if 0%{?fedora}%{?eln}
        %pesign -s -i $KernelUnifiedImage -o $KernelUnifiedImage.signed -a %{secureboot_ca_0} -c %{secureboot_key_0} -n %{pesign_name_0}
%else
%if 0%{?centos}
        UKI_secureboot_name=rockybootsigningcert
%else
        UKI_secureboot_name=rockybootsigningcert
%endif
        UKI_secureboot_cert=%{_datadir}/pki/sb-certs/secureboot-uki-virt-%{_arch}.cer

        %pesign -s -i $KernelUnifiedImage -o $KernelUnifiedImage.signed -a %{secureboot_ca_0} -c $UKI_secureboot_cert -n $UKI_secureboot_name
# 0%{?fedora}%{?eln}
%endif
        if [ ! -s $KernelUnifiedImage.signed ]; then
            echo "pesigning failed"
            exit 1
        fi
        mv $KernelUnifiedImage.signed $KernelUnifiedImage

      for addon in "$KernelAddonsDirOut"/*; do
        %pesign -s -i $addon -o $addon.signed -a %{secureboot_ca_0} -c %{secureboot_key_0} -n %{pesign_name_0}
        rm -f $addon
        mv $addon.signed $addon
      done

# signkernel
%endif

    # hmac sign the UKI for FIPS
    KernelUnifiedImageHMAC="$KernelUnifiedImageDir/.$InstallName-virt.efi.hmac"
    %{log_msg "hmac sign the UKI for FIPS"}
    %{log_msg "Creating hmac file: $KernelUnifiedImageHMAC"}
    (cd $KernelUnifiedImageDir && sha512hmac $InstallName-virt.efi) > $KernelUnifiedImageHMAC;

# with_efiuki
%endif
	:  # in case of empty block
    fi # "$Variant" == "rt" || "$Variant" == "rt-debug" || "$Variant" == "automotive" || "$Variant" == "automotive-debug"


    #
    # Generate the modules files lists
    #
    move_kmod_list()
    {
        local module_list="$1"
        local subdir_name="$2"

        mkdir -p "$RPM_BUILD_ROOT/lib/modules/$KernelVer/$subdir_name"

        set +x
        while read -r kmod; do
            local target_file="$RPM_BUILD_ROOT/lib/modules/$KernelVer/$subdir_name/$kmod"
            local target_dir="${target_file%/*}"
            mkdir -p "$target_dir"
            mv "$RPM_BUILD_ROOT/lib/modules/$KernelVer/kernel/$kmod" "$target_dir"
        done < <(sed -e 's|^kernel/||' "$module_list")
        set -x
    }

    create_module_file_list()
    {
        # subdirectory within /lib/modules/$KernelVer where kmods should go
        local module_subdir="$1"
        # kmod list with relative paths produced by filtermods.py
        local relative_kmod_list="$2"
        # list with absolute paths to kmods and other files to be included
        local absolute_file_list="$3"
        # if 1, this adds also all kmod directories to absolute_file_list
        local add_all_dirs="$4"
        local run_mod_deny="$5"

        if [ "$module_subdir" != "kernel" ]; then
            # move kmods into subdirs if needed (internal, partner, extra,..)
            move_kmod_list $relative_kmod_list $module_subdir
        fi

        # make kmod paths absolute
        sed -e 's|^kernel/|/lib/modules/'$KernelVer'/'$module_subdir'/|' $relative_kmod_list > $absolute_file_list

	if [ "$run_mod_deny" -eq 1 ]; then
            # run deny-mod script, this adds blacklist-* files to absolute_file_list
            %{SOURCE20} "$RPM_BUILD_ROOT" lib/modules/$KernelVer $absolute_file_list
	fi

%if %{zipmodules}
        # deny-mod script works with kmods as they are now (not compressed),
        # but if they will be we need to add compext to all
        sed -i %{?zipsed} $absolute_file_list
%endif
        # add also dir for the case when there are no kmods
        # "kernel" subdir is covered in %files section, skip it here
        if [ "$module_subdir" != "kernel" ]; then
                echo "%dir /lib/modules/$KernelVer/$module_subdir" >> $absolute_file_list
        fi

        if [ "$add_all_dirs" -eq 1 ]; then
            (cd $RPM_BUILD_ROOT; find lib/modules/$KernelVer/kernel -mindepth 1 -type d | sort -n) > ../module-dirs.list
            sed -e 's|^lib|%dir /lib|' ../module-dirs.list >> $absolute_file_list
        fi
    }

    if [ $DoModules -eq 1 ]; then
        # save modules.dep for debugging
        cp $RPM_BUILD_ROOT/lib/modules/$KernelVer/modules.dep ../

        %{log_msg "Create module list files for all kernel variants"}
        variants_param=""
        if [[ "$Variant" == "rt" || "$Variant" == "rt-debug" ]]; then
            variants_param="-r rt"
        fi
        if [[ "$Variant" == "rt-64k" || "$Variant" == "rt-64k-debug" ]]; then
            variants_param="-r rt-64k"
        fi
        if [[ "$Variant" == "automotive" || "$Variant" == "automotive-debug" ]]; then
            variants_param="-r automotive"
        fi
        # this creates ../modules-*.list output, where each kmod path is as it
        # appears in modules.dep (relative to lib/modules/$KernelVer)
        ret=0
        %{SOURCE22} -l "../filtermods-$KernelVer.log" sort -d $RPM_BUILD_ROOT/lib/modules/$KernelVer/modules.dep -c configs/def_variants.yaml $variants_param -o .. || ret=$?
        if [ $ret -ne 0 ]; then
            echo "8< --- filtermods-$KernelVer.log ---"
            cat "../filtermods-$KernelVer.log"
            echo "--- filtermods-$KernelVer.log --- >8"

            echo "8< --- modules.dep ---"
            cat $RPM_BUILD_ROOT/lib/modules/$KernelVer/modules.dep
            echo "--- modules.dep --- >8"
            exit 1
        fi

        create_module_file_list "kernel" ../modules-core.list ../kernel${Variant:+-${Variant}}-modules-core.list 1 0
        create_module_file_list "kernel" ../modules.list ../kernel${Variant:+-${Variant}}-modules.list 0 0
        create_module_file_list "internal" ../modules-internal.list ../kernel${Variant:+-${Variant}}-modules-internal.list 0 1
        create_module_file_list "kernel" ../modules-extra.list ../kernel${Variant:+-${Variant}}-modules-extra.list 0 1
        if [[ "$Variant" == "rt" || "$Variant" == "rt-debug" ]]; then
            create_module_file_list "kvm" ../modules-rt-kvm.list ../kernel${Variant:+-${Variant}}-modules-rt-kvm.list 0 1
        fi
        if [[ "$Variant" == "rt-64k" || "$Variant" == "rt-64k-debug" ]]; then
            create_module_file_list "kvm" ../modules-rt-64k-kvm.list ../kernel${Variant:+-${Variant}}-modules-rt-64k-kvm.list 0 1
        fi
%if 0%{!?fedora:1}
        create_module_file_list "partner" ../modules-partner.list ../kernel${Variant:+-${Variant}}-modules-partner.list 1 1
%endif
    fi # $DoModules -eq 1

    remove_depmod_files()
    {
        # remove files that will be auto generated by depmod at rpm -i time
        pushd $RPM_BUILD_ROOT/lib/modules/$KernelVer/
            # in case below list needs to be extended, remember to add a
            # matching ghost entry in the files section as well
            rm -f modules.{alias,alias.bin,builtin.alias.bin,builtin.bin} \
                  modules.{dep,dep.bin,devname,softdep,symbols,symbols.bin,weakdep}
        popd
    }

    # Cleanup
    %{log_msg "Cleanup build files"}
    rm -f $RPM_BUILD_ROOT/System.map
    %{log_msg "Remove depmod files"}
    remove_depmod_files

%if %{with_cross}
    make -C $RPM_BUILD_ROOT/lib/modules/$KernelVer/build M=scripts clean
    make -C $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/tools/bpf/resolve_btfids clean
    sed -i 's/REBUILD_SCRIPTS_FOR_CROSS:=0/REBUILD_SCRIPTS_FOR_CROSS:=1/' $RPM_BUILD_ROOT/lib/modules/$KernelVer/build/Makefile
%endif

    # Move the devel headers out of the root file system
    %{log_msg "Move the devel headers to RPM_BUILD_ROOT"}
    mkdir -p $RPM_BUILD_ROOT/usr/src/kernels
    mv $RPM_BUILD_ROOT/lib/modules/$KernelVer/build $RPM_BUILD_ROOT/$DevelDir

    # This is going to create a broken link during the build, but we don't use
    # it after this point.  We need the link to actually point to something
    # when kernel-devel is installed, and a relative link doesn't work across
    # the F17 UsrMove feature.
    ln -sf $DevelDir $RPM_BUILD_ROOT/lib/modules/$KernelVer/build

%if %{with_debuginfo}
    # Generate vmlinux.h and put it to kernel-devel path
    # zfcpdump build does not have btf anymore
    if [ "$Variant" != "zfcpdump" ]; then
	%{log_msg "Build the bootstrap bpftool to generate vmlinux.h"}
        # Build the bootstrap bpftool to generate vmlinux.h
        export BPFBOOTSTRAP_CFLAGS=$(echo "%{__global_compiler_flags}" | sed -r "s/\-specs=[^\ ]+\/redhat-annobin-cc1//")
        export BPFBOOTSTRAP_LDFLAGS=$(echo "%{__global_ldflags}" | sed -r "s/\-specs=[^\ ]+\/redhat-annobin-cc1//")
        CFLAGS="" LDFLAGS="" make EXTRA_CFLAGS="${BPFBOOTSTRAP_CFLAGS}" EXTRA_CXXFLAGS="${BPFBOOTSTRAP_CFLAGS}" EXTRA_LDFLAGS="${BPFBOOTSTRAP_LDFLAGS}" %{?make_opts} %{?clang_make_opts} V=1 -C tools/bpf/bpftool bootstrap

        tools/bpf/bpftool/bootstrap/bpftool btf dump file vmlinux format c > $RPM_BUILD_ROOT/$DevelDir/vmlinux.h
    fi
%endif

    %{log_msg "Cleanup kernel-devel and kernel-debuginfo files"}
    # prune junk from kernel-devel
    find $RPM_BUILD_ROOT/usr/src/kernels -name ".*.cmd" -delete
    # prune junk from kernel-debuginfo
    find $RPM_BUILD_ROOT/usr/src/kernels -name "*.mod.c" -delete

    # Red Hat UEFI Secure Boot CA cert, which can be used to authenticate the kernel
    %{log_msg "Install certs"}
    mkdir -p $RPM_BUILD_ROOT%{_datadir}/doc/kernel-keys/$KernelVer
%if %{signkernel}
    install -m 0644 %{secureboot_ca_0} $RPM_BUILD_ROOT%{_datadir}/doc/kernel-keys/$KernelVer/kernel-signing-ca.cer
    %ifarch s390x ppc64le
    if [ -x /usr/bin/rpm-sign ]; then
        install -m 0644 %{secureboot_key_0} $RPM_BUILD_ROOT%{_datadir}/doc/kernel-keys/$KernelVer/%{signing_key_filename}
    fi
    %endif
%endif

%if 0%{?rhel}
    # Red Hat IMA code-signing cert, which is used to authenticate package files
    install -m 0644 %{ima_signing_cert} $RPM_BUILD_ROOT%{_datadir}/doc/kernel-keys/$KernelVer/%{ima_cert_name}
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
    %{log_msg "install IPA clones"}
    MAXPROCS=$(echo %{?_smp_mflags} | sed -n 's/-j\s*\([0-9]\+\)/\1/p')
    if [ -z "$MAXPROCS" ]; then
        MAXPROCS=1
    fi
    if [ "$Variant" == "" ]; then
        mkdir -p $RPM_BUILD_ROOT/$DevelDir-ipaclones
        find . -name '*.ipa-clones' | xargs -i{} -r -n 1 -P $MAXPROCS install -m 644 -D "{}" "$RPM_BUILD_ROOT/$DevelDir-ipaclones/{}"
    fi
%endif

%if %{with_gcov}
    popd
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
%if %{with_realtime}
BuildKernel %make_target %kernel_image %{_use_vdso} rt-debug
%endif

%if %{with_realtime_arm64_64k}
BuildKernel %make_target %kernel_image %{_use_vdso} rt-64k-debug
%endif

%if %{with_automotive}
BuildKernel %make_target %kernel_image %{_use_vdso} automotive-debug
%endif

%if %{with_arm64_16k}
BuildKernel %make_target %kernel_image %{_use_vdso} 16k-debug
%endif

%if %{with_arm64_64k}
BuildKernel %make_target %kernel_image %{_use_vdso} 64k-debug
%endif

%if %{with_up}
BuildKernel %make_target %kernel_image %{_use_vdso} debug
%endif
%endif

%if %{with_zfcpdump}
BuildKernel %make_target %kernel_image %{_use_vdso} zfcpdump
%endif

%if %{with_arm64_16k_base}
BuildKernel %make_target %kernel_image %{_use_vdso} 16k
%endif

%if %{with_arm64_64k_base}
BuildKernel %make_target %kernel_image %{_use_vdso} 64k
%endif

%if %{with_realtime_base}
BuildKernel %make_target %kernel_image %{_use_vdso} rt
%endif

%if %{with_realtime_arm64_64k_base}
BuildKernel %make_target %kernel_image %{_use_vdso} rt-64k
%endif

%if %{with_automotive_base}
BuildKernel %make_target %kernel_image %{_use_vdso} automotive
%endif

%if %{with_up_base}
BuildKernel %make_target %kernel_image %{_use_vdso}
%endif

%ifnarch noarch i686 %{nobuildarches}
%if !%{with_debug} && !%{with_zfcpdump} && !%{with_up} && !%{with_arm64_16k} && !%{with_arm64_64k} && !%{with_realtime} && !%{with_realtime_arm64_64k} && !%{with_automotive}
# If only building the user space tools, then initialize the build environment
# and some variables so that the various userspace tools can be built.
%{log_msg "Initialize userspace tools build environment"}
InitBuildVars
# Some tests build also modules, and need Module.symvers
if ! [[ -e Module.symvers ]] && [[ -f $DevelDir/Module.symvers ]]; then
    %{log_msg "Found Module.symvers in DevelDir, copying to ."}
    cp "$DevelDir/Module.symvers" .
fi
%endif
%endif

%ifarch aarch64
%global perf_build_extra_opts CORESIGHT=1
%endif
%global perf_make \
  %{__make} %{?make_opts} EXTRA_CFLAGS="${RPM_OPT_FLAGS}" EXTRA_CXXFLAGS="${RPM_OPT_FLAGS}" LDFLAGS="%{__global_ldflags} -Wl,-E" %{?cross_opts} -C tools/perf V=1 NO_PERF_READ_VDSO32=1 NO_PERF_READ_VDSOX32=1 WERROR=0 NO_LIBUNWIND=1 HAVE_CPLUS_DEMANGLE=1 NO_GTK2=1 NO_STRLCPY=1 NO_BIONIC=1 LIBBPF_DYNAMIC=1 LIBTRACEEVENT_DYNAMIC=1 %{?perf_build_extra_opts} prefix=%{_prefix} PYTHON=%{__python3}
%if %{with_perf}
%{log_msg "Build perf"}
# perf
# make sure check-headers.sh is executable
chmod +x tools/perf/check-headers.sh
%{perf_make} DESTDIR=$RPM_BUILD_ROOT all
%endif

%if %{with_libperf}
%global libperf_make \
  %{__make} %{?make_opts} EXTRA_CFLAGS="${RPM_OPT_FLAGS}" LDFLAGS="%{__global_ldflags}" %{?cross_opts} -C tools/lib/perf V=1
  %{log_msg "build libperf"}
%{libperf_make} DESTDIR=$RPM_BUILD_ROOT
%endif

%global tools_make \
  CFLAGS="${RPM_OPT_FLAGS}" LDFLAGS="%{__global_ldflags}" EXTRA_CFLAGS="${RPM_OPT_FLAGS}" %{make} %{?make_opts}

%ifarch %{cpupowerarchs}
    # link against in-tree libcpupower for idle state support
    %global rtla_make %{tools_make} LDFLAGS="%{__global_ldflags} -L../../power/cpupower" INCLUDES="-I../../power/cpupower/lib"
%else
    %global rtla_make %{tools_make}
%endif

%if %{with_tools}

%if %{with_ynl}
pushd tools/net/ynl
export PIP_CONFIG_FILE=/tmp/pip.config
cat <<EOF > $PIP_CONFIG_FILE
[install]
no-index = true
no-build-isolation = false
EOF
%{tools_make} %{?_smp_mflags} DESTDIR=$RPM_BUILD_ROOT install
popd
%endif

%ifarch %{cpupowerarchs}
# cpupower
# make sure version-gen.sh is executable.
chmod +x tools/power/cpupower/utils/version-gen.sh
%{log_msg "build cpupower"}
%{tools_make} %{?_smp_mflags} -C tools/power/cpupower CPUFREQ_BENCH=false DEBUG=false
%ifarch x86_64
    pushd tools/power/cpupower/debug/x86_64
    %{log_msg "build centrino-decode powernow-k8-decode"}
    %{tools_make} %{?_smp_mflags} centrino-decode powernow-k8-decode
    popd
%endif
%ifarch x86_64
   pushd tools/power/x86/x86_energy_perf_policy/
   %{log_msg "build x86_energy_perf_policy"}
   %{tools_make}
   popd
   pushd tools/power/x86/turbostat
   %{log_msg "build turbostat"}
   %{tools_make}
   popd
   pushd tools/power/x86/intel-speed-select
   %{log_msg "build intel-speed-select"}
   %{tools_make}
   popd
   pushd tools/arch/x86/intel_sdsi
   %{log_msg "build intel_sdsi"}
   %{tools_make} CFLAGS="${RPM_OPT_FLAGS}"
   popd
%endif
%endif
pushd tools/thermal/tmon/
%{log_msg "build tmon"}
%{tools_make}
popd
pushd tools/bootconfig/
%{log_msg "build bootconfig"}
%{tools_make}
popd
pushd tools/iio/
%{log_msg "build iio"}
%{tools_make}
popd
pushd tools/gpio/
%{log_msg "build gpio"}
%{tools_make}
popd
# build VM tools
pushd tools/mm/
%{log_msg "build slabinfo page_owner_sort"}
%{tools_make} slabinfo page_owner_sort
popd
pushd tools/verification/rv/
%{log_msg "build rv"}
%{tools_make}
popd
pushd tools/tracing/rtla
%{log_msg "build rtla"}
%{rtla_make}
popd
%endif

if [ -f $DevelDir/vmlinux.h ]; then
  RPM_VMLINUX_H=$DevelDir/vmlinux.h
fi
echo "${RPM_VMLINUX_H}" > ../vmlinux_h_path

%if %{with_selftests}
%{log_msg "start build selftests"}
# Unfortunately, samples/bpf/Makefile expects that the headers are installed
# in the source tree. We installed them previously to $RPM_BUILD_ROOT/usr
# but there's no way to tell the Makefile to take them from there.
%{log_msg "install headers for selftests"}
%{make} %{?_smp_mflags} headers_install

# If we re building only tools without kernel, we need to generate config
# headers and prepare tree for modules building. The modules_prepare target
# will cover both.
if [ ! -f include/generated/autoconf.h ]; then
   %{log_msg "modules_prepare for selftests"}
   %{make} %{?_smp_mflags} modules_prepare
fi

%{log_msg "build samples/bpf"}
%{make} %{?_smp_mflags} EXTRA_CXXFLAGS="${RPM_OPT_FLAGS}" ARCH=$Arch V=1 M=samples/bpf/ VMLINUX_H="${RPM_VMLINUX_H}" || true

pushd tools/testing/selftests
# We need to install here because we need to call make with ARCH set which
# doesn't seem possible to do in the install section.
%if %{selftests_must_build}
  force_targets="FORCE_TARGETS=1"
%else
  force_targets=""
%endif

%{log_msg "main selftests compile"}

# Some selftests (especially bpf) do not build with source fortification.
# Since selftests are not shipped, disable source fortification for them.
%global _fortify_level_bak %{_fortify_level}
%undefine _fortify_level
export CFLAGS="%{build_cflags}"

TARGETS="bpf cgroup mm net net/forwarding net/mptcp net/netfilter tc-testing memfd drivers/net/bonding iommu cachestat"
%{make} %{?_smp_mflags} EXTRA_CFLAGS="${RPM_OPT_FLAGS}" EXTRA_CXXFLAGS="${RPM_OPT_FLAGS}" EXTRA_LDFLAGS="%{__global_ldflags}" ARCH=$Arch V=1 TARGETS="$TARGETS" SKIP_TARGETS="" $force_targets VMLINUX_H="${RPM_VMLINUX_H}"

# Restore the original level of source fortification
%define _fortify_level %{_fortify_level_bak}
export CFLAGS="%{build_cflags}"

%ifarch %{klptestarches}
	# kernel livepatching selftest test_modules will build against
	# /lib/modules/$(shell uname -r)/build tree unless KDIR is set
	export KDIR=$(realpath $(pwd)/../../..)
	%{make} %{?_smp_mflags} ARCH=$Arch V=1 TARGETS="livepatch" SKIP_TARGETS="" $force_targets VMLINUX_H="${RPM_VMLINUX_H}" && TARGETS="${TARGETS} livepatch" || true
%endif

# We must install all the targets in a single step as each `make install`
# command overrides the kselftest-list.txt file.
%{make} ARCH=$Arch TARGETS="${TARGETS}" SKIP_TARGETS="" $force_targets INSTALL_PATH=%{buildroot}%{_libexecdir}/kselftests install

# 'make install' for bpf is broken and upstream refuses to fix it.
# Install the needed files manually.
%{log_msg "install selftests"}
for dir in bpf bpf/no_alu32 bpf/progs; do
	# In ARK, the rpm build continues even if some of the selftests
	# cannot be built. It's not always possible to build selftests,
	# as upstream sometimes dependens on too new llvm version or has
	# other issues. If something did not get built, just skip it.
	test -d $dir || continue
	mkdir -p %{buildroot}%{_libexecdir}/kselftests/$dir
	find $dir -maxdepth 1 \( -type f  -o -type l \) \
        \( -executable -o -name '*.py' -o -name settings -o \
		-name 'btf_dump_test_case_*.c' -o -name '*.ko' -o \
		-name '*.o' -exec sh -c 'readelf -h "{}" | grep -q "^  Machine:.*BPF"' \; \) -print0 | \
	xargs -0 cp -t %{buildroot}%{_libexecdir}/kselftests/$dir || true
done

%buildroot_save_unstripped "usr/libexec/kselftests/bpf/test_progs"
%buildroot_save_unstripped "usr/libexec/kselftests/bpf/test_progs-no_alu32"

# The urandom_read binary doesn't pass the check-rpaths check and upstream
# refuses to fix it. So, we save it to buildroot_unstripped and delete it so it
# will be hidden from check-rpaths and will automatically get restored later.
%buildroot_save_unstripped "usr/libexec/kselftests/bpf/urandom_read"
%buildroot_save_unstripped "usr/libexec/kselftests/bpf/no_alu32/urandom_read"
rm -f %{buildroot}/usr/libexec/kselftests/bpf/urandom_read
rm -f %{buildroot}/usr/libexec/kselftests/bpf/no_alu32/urandom_read

popd
%{log_msg "end build selftests"}
%endif

%if %{with_doc}
%{log_msg "start install docs"}
# Make the HTML pages.
%{log_msg "build html docs"}
%{__make} PYTHON=/usr/bin/python3 htmldocs || %{doc_build_fail}

# sometimes non-world-readable files sneak into the kernel source tree
chmod -R a=rX Documentation
find Documentation -type d | xargs chmod u+w
%{log_msg "end install docs"}
%endif

# Module signing (modsign)
#
# This must be run _after_ find-debuginfo.sh runs, otherwise that will strip
# the signature off of the modules.
#
# Don't sign modules for the zfcpdump variant as it is monolithic.

%define __modsign_install_post \
  if [ "%{signmodules}" -eq "1" ]; then \
    %{log_msg "Signing kernel modules ..."} \
    modules_dirs="$(shopt -s nullglob; echo $RPM_BUILD_ROOT/lib/modules/%{KVERREL}*)" \
    for modules_dir in $modules_dirs; do \
        variant_suffix="${modules_dir#$RPM_BUILD_ROOT/lib/modules/%{KVERREL}}" \
        [ "$variant_suffix" == "+zfcpdump" ] && continue \
	%{log_msg "Signing modules for %{KVERREL}${variant_suffix}"} \
        %{modsign_cmd} certs/signing_key.pem.sign${variant_suffix} certs/signing_key.x509.sign${variant_suffix} $modules_dir/ \
    done \
  fi \
  if [ "%{zipmodules}" -eq "1" ]; then \
    %{log_msg "Compressing kernel modules ..."} \
    find $RPM_BUILD_ROOT/lib/modules/ -type f -name '*.ko' | xargs -n 16 -P${RPM_BUILD_NCPUS} -r %compression %compression_flags; \
  fi \
%{nil}

###
### Special hacks for debuginfo subpackages.
###

# This macro is used by %%install, so we must redefine it before that.
%define debug_package %{nil}

%if %{with_debuginfo}

%ifnarch noarch %{nobuildarches}
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
  %{__restore_unstripped_root_post}\
  %{__modsign_install_post}

###
### install
###

%install

cd linux-%{KVERREL}

# re-define RPM_VMLINUX_H, because it doesn't carry over from %build
RPM_VMLINUX_H="$(cat ../vmlinux_h_path)"

%if %{with_doc}
docdir=$RPM_BUILD_ROOT%{_datadir}/doc/kernel-doc-%{specversion}-%{pkgrelease}

# copy the source over
mkdir -p $docdir
tar -h -f - --exclude=man --exclude='.*' -c Documentation | tar xf - -C $docdir
cat %{SOURCE2} | xz > $docdir/kernel.changelog.xz
chmod 0644 $docdir/kernel.changelog.xz

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
HDR_ARCH_LIST='arm64 powerpc s390 x86 riscv'
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
tar -xvf %{SOURCE300} -C $INSTALL_KABI_PATH
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

%if %{with_libperf}
%{libperf_make} DESTDIR=%{buildroot} prefix=%{_prefix} libdir=%{_libdir} install install_headers
# This is installed on some arches and we don't want to ship it
rm -rf %{buildroot}%{_libdir}/libperf.a
%endif

%if %{with_tools}
%ifarch %{cpupowerarchs}
%{make} -C tools/power/cpupower DESTDIR=$RPM_BUILD_ROOT libdir=%{_libdir} mandir=%{_mandir} CPUFREQ_BENCH=false install
%find_lang cpupower
mv cpupower.lang ../
%ifarch x86_64
    pushd tools/power/cpupower/debug/x86_64
    install -m755 centrino-decode %{buildroot}%{_bindir}/centrino-decode
    install -m755 powernow-k8-decode %{buildroot}%{_bindir}/powernow-k8-decode
    popd
%endif
chmod 0755 %{buildroot}%{_libdir}/libcpupower.so*
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
   %{tools_make} DESTDIR=%{buildroot} install
   popd
   pushd tools/arch/x86/intel_sdsi
   %{tools_make} CFLAGS="${RPM_OPT_FLAGS}" DESTDIR=%{buildroot} install
   popd
%endif
pushd tools/thermal/tmon
%{tools_make} INSTALL_ROOT=%{buildroot} install
popd
pushd tools/bootconfig
%{tools_make} DESTDIR=%{buildroot} install
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
pushd tools/mm/
install -m755 slabinfo %{buildroot}%{_bindir}/slabinfo
install -m755 page_owner_sort %{buildroot}%{_bindir}/page_owner_sort
popd
pushd tools/verification/rv/
%{tools_make} DESTDIR=%{buildroot} install
popd
pushd tools/tracing/rtla/
%{tools_make} DESTDIR=%{buildroot} install
rm -f %{buildroot}%{_bindir}/hwnoise
rm -f %{buildroot}%{_bindir}/osnoise
rm -f %{buildroot}%{_bindir}/timerlat
(cd %{buildroot}

        ln -sf rtla ./%{_bindir}/hwnoise
        ln -sf rtla ./%{_bindir}/osnoise
        ln -sf rtla ./%{_bindir}/timerlat
)
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
# install mm selftests
pushd tools/testing/selftests/mm
find -type d -exec install -d %{buildroot}%{_libexecdir}/kselftests/mm/{} \;
find -type f -executable -exec install -D -m755 {} %{buildroot}%{_libexecdir}/kselftests/mm/{} \;
find -type f ! -executable -exec install -D -m644 {} %{buildroot}%{_libexecdir}/kselftests/mm/{} \;
popd
# install cgroup selftests
pushd tools/testing/selftests/cgroup
find -type d -exec install -d %{buildroot}%{_libexecdir}/kselftests/cgroup/{} \;
find -type f -executable -exec install -D -m755 {} %{buildroot}%{_libexecdir}/kselftests/cgroup/{} \;
find -type f ! -executable -exec install -D -m644 {} %{buildroot}%{_libexecdir}/kselftests/cgroup/{} \;
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
# install drivers/net/bonding selftests
pushd tools/testing/selftests/drivers/net/bonding
find -type d -exec install -d %{buildroot}%{_libexecdir}/kselftests/drivers/net/bonding/{} \;
find -type f -executable -exec install -D -m755 {} %{buildroot}%{_libexecdir}/kselftests/drivers/net/bonding/{} \;
find -type f ! -executable -exec install -D -m644 {} %{buildroot}%{_libexecdir}/kselftests/drivers/net/bonding/{} \;
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
# install net/netfilter selftests
pushd tools/testing/selftests/net/netfilter
find -type d -exec install -d %{buildroot}%{_libexecdir}/kselftests/net/netfilter/{} \;
find -type f -executable -exec install -D -m755 {} %{buildroot}%{_libexecdir}/kselftests/net/netfilter/{} \;
find -type f ! -executable -exec install -D -m644 {} %{buildroot}%{_libexecdir}/kselftests/net/netfilter/{} \;
popd

# install memfd selftests
pushd tools/testing/selftests/memfd
find -type d -exec install -d %{buildroot}%{_libexecdir}/kselftests/memfd/{} \;
find -type f -executable -exec install -D -m755 {} %{buildroot}%{_libexecdir}/kselftests/memfd/{} \;
find -type f ! -executable -exec install -D -m644 {} %{buildroot}%{_libexecdir}/kselftests/memfd/{} \;
popd
# install iommu selftests
pushd tools/testing/selftests/iommu
find -type d -exec install -d %{buildroot}%{_libexecdir}/kselftests/iommu/{} \;
find -type f -executable -exec install -D -m755 {} %{buildroot}%{_libexecdir}/kselftests/iommu/{} \;
find -type f ! -executable -exec install -D -m644 {} %{buildroot}%{_libexecdir}/kselftests/iommu/{} \;
popd
%endif

###
### clean
###

###
### scripts
###

%if %{with_tools}
%post -n %{package_name}-tools-libs
/sbin/ldconfig

%postun -n %{package_name}-tools-libs
/sbin/ldconfig
%endif

#
# This macro defines a %%post script for a kernel*-devel package.
#	%%kernel_devel_post [<subpackage>]
# Note we don't run hardlink if ostree is in use, as ostree is
# a far more sophisticated hardlink implementation.
# https://github.com/projectatomic/rpm-ostree/commit/58a79056a889be8814aa51f507b2c7a4dccee526
#
# The deletion of *.hardlink-temporary files is a temporary workaround
# for this bug in the hardlink binary (fixed in util-linux 2.38):
# https://github.com/util-linux/util-linux/issues/1602
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
     done;\
     /usr/bin/find /usr/src/kernels -type f -name '*.hardlink-temporary' -delete\
    )\
fi\
%if %{with_cross}\
    echo "Building scripts and resolve_btfids"\
    env --unset=ARCH make -C /usr/src/kernels/%{KVERREL}%{?1:+%{1}} prepare_after_cross\
%endif\
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
# This macro defines a %%post script for a kernel*-modules-partner package.
# It also defines a %%postun script that does the same thing.
#	%%kernel_modules_partner_post [<subpackage>]
#
%define kernel_modules_partner_post() \
%{expand:%%post %{?1:%{1}-}modules-partner}\
/sbin/depmod -a %{KVERREL}%{?1:+%{1}}\
%{nil}\
%{expand:%%postun %{?1:%{1}-}modules-partner}\
/sbin/depmod -a %{KVERREL}%{?1:+%{1}}\
%{nil}

%if %{with_realtime} || %{with_realtime_arm64_64k}
#
# This macro defines a %%post script for a kernel*-kvm package.
# It also defines a %%postun script that does the same thing.
#	%%kernel_kvm_post [<subpackage>]
#
%define kernel_kvm_post() \
%{expand:%%post %{?1:%{1}-}kvm}\
/sbin/depmod -a %{KVERREL}%{?1:+%{1}}\
%{nil}\
%{expand:%%postun %{?1:%{1}-}kvm}\
/sbin/depmod -a %{KVERREL}%{?1:+%{1}}\
%{nil}
%endif

#
# This macro defines a %%post script for a kernel*-modules package.
# It also defines a %%postun script that does the same thing.
#	%%kernel_modules_post [<subpackage>]
#
%define kernel_modules_post() \
%{expand:%%post %{?1:%{1}-}modules}\
/sbin/depmod -a %{KVERREL}%{?1:+%{1}}\
if [ ! -f %{_localstatedir}/lib/rpm-state/%{name}/installing_core_%{KVERREL}%{?1:+%{1}} ]; then\
	mkdir -p %{_localstatedir}/lib/rpm-state/%{name}\
	touch %{_localstatedir}/lib/rpm-state/%{name}/need_to_run_dracut_%{KVERREL}%{?1:+%{1}}\
fi\
%{nil}\
%{expand:%%postun %{?1:%{1}-}modules}\
/sbin/depmod -a %{KVERREL}%{?1:+%{1}}\
%{nil}\
%{expand:%%posttrans %{?1:%{1}-}modules}\
if [ -f %{_localstatedir}/lib/rpm-state/%{name}/need_to_run_dracut_%{KVERREL}%{?1:+%{1}} ]; then\
	rm -f %{_localstatedir}/lib/rpm-state/%{name}/need_to_run_dracut_%{KVERREL}%{?1:+%{1}}\
	echo "Running: dracut -f --kver %{KVERREL}%{?1:+%{1}}"\
	dracut -f --kver "%{KVERREL}%{?1:+%{1}}" || exit $?\
fi\
%{nil}

#
# This macro defines a %%post script for a kernel*-modules-core package.
#	%%kernel_modules_core_post [<subpackage>]
#
%define kernel_modules_core_post() \
%{expand:%%posttrans %{?1:%{1}-}modules-core}\
/sbin/depmod -a %{KVERREL}%{?1:+%{1}}\
%{nil}

# This macro defines a %%posttrans script for a kernel package.
#	%%kernel_variant_posttrans [-v <subpackage>] [-u uki-suffix]
# More text can follow to go at the end of this variant's %%post.
#
%define kernel_variant_posttrans(v:u:) \
%{expand:%%posttrans %{?-v:%{-v*}-}%{!?-u*:core}%{?-u*:uki-%{-u*}}}\
%if 0%{!?fedora:1}\
%if !%{with_automotive}\
if [ -x %{_sbindir}/weak-modules ]\
then\
    %{_sbindir}/weak-modules --add-kernel %{KVERREL}%{?-v:+%{-v*}} || exit $?\
fi\
%endif\
%endif\
rm -f %{_localstatedir}/lib/rpm-state/%{name}/installing_core_%{KVERREL}%{?-v:+%{-v*}}\
/bin/kernel-install add %{KVERREL}%{?-v:+%{-v*}} /lib/modules/%{KVERREL}%{?-v:+%{-v*}}/vmlinuz%{?-u:-%{-u*}.efi} || exit $?\
if [[ ! -e "/boot/symvers-%{KVERREL}%{?-v:+%{-v*}}.%compext" ]]; then\
    cp "/lib/modules/%{KVERREL}%{?-v:+%{-v*}}/symvers.%compext" "/boot/symvers-%{KVERREL}%{?-v:+%{-v*}}.%compext"\
    if command -v restorecon &>/dev/null; then\
        restorecon "/boot/symvers-%{KVERREL}%{?-v:+%{-v*}}.%compext"\
    fi\
fi\
%{nil}

#
# This macro defines a %%post script for a kernel package and its devel package.
#	%%kernel_variant_post [-v <subpackage>] [-r <replace>]
# More text can follow to go at the end of this variant's %%post.
#
%define kernel_variant_post(v:r:) \
%{expand:%%kernel_devel_post %{?-v*}}\
%{expand:%%kernel_modules_post %{?-v*}}\
%{expand:%%kernel_modules_core_post %{?-v*}}\
%{expand:%%kernel_modules_extra_post %{?-v*}}\
%{expand:%%kernel_modules_internal_post %{?-v*}}\
%if 0%{!?fedora:1}\
%{expand:%%kernel_modules_partner_post %{?-v*}}\
%endif\
%{expand:%%kernel_variant_posttrans %{?-v*:-v %{-v*}}}\
%{expand:%%post %{?-v*:%{-v*}-}core}\
%{-r:\
if [ `uname -i` == "x86_64" -o `uname -i` == "i386" ] &&\
   [ -f /etc/sysconfig/kernel ]; then\
  /bin/sed -r -i -e 's/^DEFAULTKERNEL=%{-r*}$/DEFAULTKERNEL=kernel%{?-v:-%{-v*}}/' /etc/sysconfig/kernel || exit $?\
fi}\
mkdir -p %{_localstatedir}/lib/rpm-state/%{name}\
touch %{_localstatedir}/lib/rpm-state/%{name}/installing_core_%{KVERREL}%{?-v:+%{-v*}}\
%{nil}

#
# This macro defines a %%preun script for a kernel package.
#	%%kernel_variant_preun [-v <subpackage>] -u [uki-suffix]
#
%define kernel_variant_preun(v:u:) \
%{expand:%%preun %{?-v:%{-v*}-}%{!?-u*:core}%{?-u*:uki-%{-u*}}}\
/bin/kernel-install remove %{KVERREL}%{?-v:+%{-v*}} || exit $?\
%if !%{with_automotive}\
if [ -x %{_sbindir}/weak-modules ]\
then\
    %{_sbindir}/weak-modules --remove-kernel %{KVERREL}%{?-v:+%{-v*}} || exit $?\
fi\
%endif\
%{nil}

%if %{with_up_base} && %{with_efiuki}
%kernel_variant_posttrans -u virt
%kernel_variant_preun -u virt
%endif

%if %{with_up_base}
%kernel_variant_preun
%kernel_variant_post
%endif

%if %{with_zfcpdump}
%kernel_variant_preun -v zfcpdump
%kernel_variant_post -v zfcpdump
%endif

%if %{with_up} && %{with_debug} && %{with_efiuki}
%kernel_variant_posttrans -v debug -u virt
%kernel_variant_preun -v debug -u virt
%endif

%if %{with_up} && %{with_debug}
%kernel_variant_preun -v debug
%kernel_variant_post -v debug
%endif

%if %{with_arm64_16k_base}
%kernel_variant_preun -v 16k
%kernel_variant_post -v 16k
%endif

%if %{with_debug} && %{with_arm64_16k}
%kernel_variant_preun -v 16k-debug
%kernel_variant_post -v 16k-debug
%endif

%if %{with_arm64_16k} && %{with_debug} && %{with_efiuki}
%kernel_variant_posttrans -v 16k-debug -u virt
%kernel_variant_preun -v 16k-debug -u virt
%endif

%if %{with_arm64_16k_base} && %{with_efiuki}
%kernel_variant_posttrans -v 16k -u virt
%kernel_variant_preun -v 16k -u virt
%endif

%if %{with_arm64_64k_base}
%kernel_variant_preun -v 64k
%kernel_variant_post -v 64k
%endif

%if %{with_debug} && %{with_arm64_64k}
%kernel_variant_preun -v 64k-debug
%kernel_variant_post -v 64k-debug
%endif

%if %{with_arm64_64k} && %{with_debug} && %{with_efiuki}
%kernel_variant_posttrans -v 64k-debug -u virt
%kernel_variant_preun -v 64k-debug -u virt
%endif

%if %{with_arm64_64k_base} && %{with_efiuki}
%kernel_variant_posttrans -v 64k -u virt
%kernel_variant_preun -v 64k -u virt
%endif

%if %{with_realtime_base}
%kernel_variant_preun -v rt
%kernel_variant_post -v rt -r kernel
%kernel_kvm_post rt
%endif

%if %{with_automotive_base}
%kernel_variant_preun -v automotive
%kernel_variant_post -v automotive -r kernel
%endif

%if %{with_realtime} && %{with_debug}
%kernel_variant_preun -v rt-debug
%kernel_variant_post -v rt-debug
%kernel_kvm_post rt-debug
%endif

%if %{with_realtime_arm64_64k_base}
%kernel_variant_preun -v rt-64k
%kernel_variant_post -v rt-64k
%kernel_kvm_post rt-64k
%endif

%if %{with_debug} && %{with_realtime_arm64_64k}
%kernel_variant_preun -v rt-64k-debug
%kernel_variant_post -v rt-64k-debug
%kernel_kvm_post rt-64k-debug
%endif

%if %{with_automotive} && %{with_debug}
%kernel_variant_preun -v automotive-debug
%kernel_variant_post -v automotive-debug
%endif

###
### file lists
###

%if %{with_headers}
%files headers
/usr/include/*
%exclude %{_includedir}/cpufreq.h
%endif

%if %{with_cross_headers}
%files cross-headers
/usr/*-linux-gnu/include/*
%endif

%if %{with_kernel_abi_stablelists}
%files -n %{package_name}-abi-stablelists
/lib/modules/kabi-*
%endif

%if %{with_kabidw_base}
%ifarch x86_64 s390x ppc64 ppc64le aarch64 riscv64
%files kernel-kabidw-base-internal
%defattr(-,root,root)
/kabidw-base/%{_target_cpu}/*
%endif
%endif

# only some architecture builds need kernel-doc
%if %{with_doc}
%files doc
%defattr(-,root,root)
%{_datadir}/doc/kernel-doc-%{specversion}-%{pkgrelease}/Documentation/*
%dir %{_datadir}/doc/kernel-doc-%{specversion}-%{pkgrelease}/Documentation
%dir %{_datadir}/doc/kernel-doc-%{specversion}-%{pkgrelease}
%{_datadir}/doc/kernel-doc-%{specversion}-%{pkgrelease}/kernel.changelog.xz
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

%if %{with_libperf}
%files -n libperf
%{_libdir}/libperf.so.0
%{_libdir}/libperf.so.0.0.1

%files -n libperf-devel
%{_libdir}/libperf.so
%{_libdir}/pkgconfig/libperf.pc
%{_includedir}/internal/*.h
%{_includedir}/perf/bpf_perf.h
%{_includedir}/perf/core.h
%{_includedir}/perf/cpumap.h
%{_includedir}/perf/perf_dlfilter.h
%{_includedir}/perf/event.h
%{_includedir}/perf/evlist.h
%{_includedir}/perf/evsel.h
%{_includedir}/perf/mmap.h
%{_includedir}/perf/threadmap.h
%{_mandir}/man3/libperf.3.gz
%{_mandir}/man7/libperf-counting.7.gz
%{_mandir}/man7/libperf-sampling.7.gz
%{_docdir}/libperf/examples/sampling.c
%{_docdir}/libperf/examples/counting.c
%{_docdir}/libperf/html/libperf.html
%{_docdir}/libperf/html/libperf-counting.html
%{_docdir}/libperf/html/libperf-sampling.html

%if %{with_debuginfo}
%files -f libperf-debuginfo.list -n libperf-debuginfo
%endif

# with_libperf
%endif


%if %{with_tools}
%ifnarch %{cpupowerarchs}
%files -n %{package_name}-tools
%else
%files -n %{package_name}-tools -f cpupower.lang
%{_bindir}/cpupower
%{_datadir}/bash-completion/completions/cpupower
%ifarch x86_64
%{_bindir}/centrino-decode
%{_bindir}/powernow-k8-decode
%endif
%{_mandir}/man[1-8]/cpupower*
%ifarch x86_64
%{_bindir}/x86_energy_perf_policy
%{_mandir}/man8/x86_energy_perf_policy*
%{_bindir}/turbostat
%{_mandir}/man8/turbostat*
%{_bindir}/intel-speed-select
%{_sbindir}/intel_sdsi
%endif
# cpupowerarchs
%endif
%{_bindir}/tmon
%{_bindir}/bootconfig
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
%if %{with_ynl}
%{_bindir}/ynl*
%{_docdir}/ynl
%{_datadir}/ynl
%{python3_sitelib}/pyynl*
%endif

%if %{with_debuginfo}
%files -f %{package_name}-tools-debuginfo.list -n %{package_name}-tools-debuginfo
%endif

%files -n %{package_name}-tools-libs
%ifarch %{cpupowerarchs}
%{_libdir}/libcpupower.so.1
%{_libdir}/libcpupower.so.0.0.1
%endif

%files -n %{package_name}-tools-libs-devel
%ifarch %{cpupowerarchs}
%{_libdir}/libcpupower.so
%{_includedir}/cpufreq.h
%{_includedir}/cpuidle.h
%{_includedir}/powercap.h
%endif
%if %{with_ynl}
%{_libdir}/libynl*
%{_includedir}/ynl
%endif

%files -n rtla
%{_bindir}/rtla
%{_bindir}/hwnoise
%{_bindir}/osnoise
%{_bindir}/timerlat
%{_mandir}/man1/rtla-hwnoise.1.gz
%{_mandir}/man1/rtla-osnoise-hist.1.gz
%{_mandir}/man1/rtla-osnoise-top.1.gz
%{_mandir}/man1/rtla-osnoise.1.gz
%{_mandir}/man1/rtla-timerlat-hist.1.gz
%{_mandir}/man1/rtla-timerlat-top.1.gz
%{_mandir}/man1/rtla-timerlat.1.gz
%{_mandir}/man1/rtla.1.gz

%files -n rv
%{_bindir}/rv
%{_mandir}/man1/rv-list.1.gz
%{_mandir}/man1/rv-mon-wip.1.gz
%{_mandir}/man1/rv-mon-wwnr.1.gz
%{_mandir}/man1/rv-mon.1.gz
%{_mandir}/man1/rv.1.gz

# with_tools
%endif

%if %{with_selftests}
%files selftests-internal
%{_libexecdir}/ksamples
%{_libexecdir}/kselftests
%endif

# empty meta-package
%if %{with_up_base}
%ifnarch %nobuildarches noarch
%files
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
%{expand:%%files %{?1:-f kernel-%{?3:%{3}-}ldsoconf.list} %{?3:%{3}-}core}\
%{!?_licensedir:%global license %%doc}\
%%license linux-%{KVERREL}/COPYING-%{version}-%{release}\
/lib/modules/%{KVERREL}%{?3:+%{3}}/%{?-k:%{-k*}}%{!?-k:vmlinuz}\
%ghost /%{image_install_path}/%{?-k:%{-k*}}%{!?-k:vmlinuz}-%{KVERREL}%{?3:+%{3}}\
/lib/modules/%{KVERREL}%{?3:+%{3}}/.vmlinuz.hmac \
%ghost /%{image_install_path}/.vmlinuz-%{KVERREL}%{?3:+%{3}}.hmac \
%ifarch aarch64 riscv64\
/lib/modules/%{KVERREL}%{?3:+%{3}}/dtb \
%ghost /%{image_install_path}/dtb-%{KVERREL}%{?3:+%{3}} \
%endif\
/lib/modules/%{KVERREL}%{?3:+%{3}}/System.map\
%ghost /boot/System.map-%{KVERREL}%{?3:+%{3}}\
%dir /lib/modules\
%dir /lib/modules/%{KVERREL}%{?3:+%{3}}\
/lib/modules/%{KVERREL}%{?3:+%{3}}/symvers.%compext\
/lib/modules/%{KVERREL}%{?3:+%{3}}/config\
/lib/modules/%{KVERREL}%{?3:+%{3}}/modules.builtin*\
%ghost %attr(0644, root, root) /boot/symvers-%{KVERREL}%{?3:+%{3}}.%compext\
%ghost %attr(0600, root, root) /boot/initramfs-%{KVERREL}%{?3:+%{3}}.img\
%ghost %attr(0644, root, root) /boot/config-%{KVERREL}%{?3:+%{3}}\
%{expand:%%files -f kernel-%{?3:%{3}-}modules-core.list %{?3:%{3}-}modules-core}\
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
/lib/modules/%{KVERREL}%{?3:+%{3}}/modules.block\
/lib/modules/%{KVERREL}%{?3:+%{3}}/modules.drm\
/lib/modules/%{KVERREL}%{?3:+%{3}}/modules.modesetting\
/lib/modules/%{KVERREL}%{?3:+%{3}}/modules.networking\
/lib/modules/%{KVERREL}%{?3:+%{3}}/modules.order\
%ghost %attr(0644, root, root) /lib/modules/%{KVERREL}%{?3:+%{3}}/modules.alias\
%ghost %attr(0644, root, root) /lib/modules/%{KVERREL}%{?3:+%{3}}/modules.alias.bin\
%ghost %attr(0644, root, root) /lib/modules/%{KVERREL}%{?3:+%{3}}/modules.builtin.alias.bin\
%ghost %attr(0644, root, root) /lib/modules/%{KVERREL}%{?3:+%{3}}/modules.builtin.bin\
%ghost %attr(0644, root, root) /lib/modules/%{KVERREL}%{?3:+%{3}}/modules.dep\
%ghost %attr(0644, root, root) /lib/modules/%{KVERREL}%{?3:+%{3}}/modules.dep.bin\
%ghost %attr(0644, root, root) /lib/modules/%{KVERREL}%{?3:+%{3}}/modules.devname\
%ghost %attr(0644, root, root) /lib/modules/%{KVERREL}%{?3:+%{3}}/modules.softdep\
%ghost %attr(0644, root, root) /lib/modules/%{KVERREL}%{?3:+%{3}}/modules.symbols\
%ghost %attr(0644, root, root) /lib/modules/%{KVERREL}%{?3:+%{3}}/modules.symbols.bin\
%ghost %attr(0644, root, root) /lib/modules/%{KVERREL}%{?3:+%{3}}/modules.weakdep\
%{expand:%%files -f kernel-%{?3:%{3}-}modules.list %{?3:%{3}-}modules}\
%{expand:%%files %{?3:%{3}-}devel}\
%defverify(not mtime)\
/usr/src/kernels/%{KVERREL}%{?3:+%{3}}\
%{expand:%%files %{?3:%{3}-}devel-matched}\
%{expand:%%files -f kernel-%{?3:%{3}-}modules-extra.list %{?3:%{3}-}modules-extra}\
%{expand:%%files -f kernel-%{?3:%{3}-}modules-internal.list %{?3:%{3}-}modules-internal}\
%if 0%{!?fedora:1}\
%{expand:%%files -f kernel-%{?3:%{3}-}modules-partner.list %{?3:%{3}-}modules-partner}\
%endif\
%if %{with_debuginfo}\
%ifnarch noarch\
%{expand:%%files -f debuginfo%{?3}.list %{?3:%{3}-}debuginfo}\
%endif\
%endif\
%if "%{3}" == "rt" || "%{3}" == "rt-debug" || "%{3}" == "rt-64k" || "%{3}" == "rt-64k-debug"\
%if "%{3}" == "rt" || "%{3}" == "rt-debug"\
%{expand:%%files -f kernel-%{?3:%{3}-}modules-rt-kvm.list %{?3:%{3}-}kvm}\
%else\
%{expand:%%files -f kernel-%{?3:%{3}-}modules-rt-64k-kvm.list %{?3:%{3}-}kvm}\
%endif\
%else\
%if %{with_efiuki}\
%{expand:%%files %{?3:%{3}-}uki-virt}\
%dir /lib/modules\
%dir /lib/modules/%{KVERREL}%{?3:+%{3}}\
/lib/modules/%{KVERREL}%{?3:+%{3}}/System.map\
/lib/modules/%{KVERREL}%{?3:+%{3}}/symvers.%compext\
/lib/modules/%{KVERREL}%{?3:+%{3}}/config\
/lib/modules/%{KVERREL}%{?3:+%{3}}/modules.builtin*\
%attr(0644, root, root) /lib/modules/%{KVERREL}%{?3:+%{3}}/%{?-k:%{-k*}}%{!?-k:vmlinuz}-virt.efi\
%attr(0644, root, root) /lib/modules/%{KVERREL}%{?3:+%{3}}/.%{?-k:%{-k*}}%{!?-k:vmlinuz}-virt.efi.hmac\
%ghost /%{image_install_path}/efi/EFI/Linux/%{?-k:%{-k*}}%{!?-k:*}-%{KVERREL}%{?3:+%{3}}.efi\
%{expand:%%files %{?3:%{3}-}uki-virt-addons}\
%dir /lib/modules/%{KVERREL}%{?3:+%{3}}/%{?-k:%{-k*}}%{!?-k:vmlinuz}-virt.efi.extra.d/ \
/lib/modules/%{KVERREL}%{?3:+%{3}}/%{?-k:%{-k*}}%{!?-k:vmlinuz}-virt.efi.extra.d/*.addon.efi\
%endif\
%endif\
%if %{?3:1} %{!?3:0}\
%{expand:%%files %{3}}\
%endif\
%if %{with_gcov}\
%ifnarch %nobuildarches noarch\
%{expand:%%files -f kernel-%{?3:%{3}-}gcov.list %{?3:%{3}-}gcov}\
%endif\
%endif\
%endif\
%{nil}

%kernel_variant_files %{_use_vdso} %{with_up_base}
%if %{with_up}
%kernel_variant_files %{_use_vdso} %{with_debug} debug
%endif
%if %{with_arm64_16k}
%kernel_variant_files %{_use_vdso} %{with_debug} 16k-debug
%endif
%if %{with_arm64_64k}
%kernel_variant_files %{_use_vdso} %{with_debug} 64k-debug
%endif
%kernel_variant_files %{_use_vdso} %{with_realtime_base} rt
%if %{with_realtime}
%kernel_variant_files %{_use_vdso} %{with_debug} rt-debug
%endif
%kernel_variant_files %{_use_vdso} %{with_automotive_base} automotive
%if %{with_automotive}
%kernel_variant_files %{_use_vdso} %{with_debug} automotive-debug
%endif
%if %{with_debug_meta}
%files debug
%files debug-core
%files debug-devel
%files debug-devel-matched
%files debug-modules
%files debug-modules-core
%files debug-modules-extra
%if %{with_arm64_16k}
%files 16k-debug
%files 16k-debug-core
%files 16k-debug-devel
%files 16k-debug-devel-matched
%files 16k-debug-modules
%files 16k-debug-modules-extra
%endif
%if %{with_arm64_64k}
%files 64k-debug
%files 64k-debug-core
%files 64k-debug-devel
%files 64k-debug-devel-matched
%files 64k-debug-modules
%files 64k-debug-modules-extra
%endif
%endif
%kernel_variant_files %{_use_vdso} %{with_zfcpdump} zfcpdump
%kernel_variant_files %{_use_vdso} %{with_arm64_16k_base} 16k
%kernel_variant_files %{_use_vdso} %{with_arm64_64k_base} 64k
%kernel_variant_files %{_use_vdso} %{with_realtime_arm64_64k_base} rt-64k
%if %{with_realtime_arm64_64k}
%kernel_variant_files %{_use_vdso} %{with_debug} rt-64k-debug
%endif

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

%kernel_variant_ipaclones %{with_up_base}

# plz don't put in a version string unless you're going to tag
# and build.
#
#
%changelog
* Mon May 19 2025 Release Engineering <releng@rockylinux.org> - 6.12.0-55.12.1
- Porting to Rocky Linux 10, debranding and Rocky Linux branding
- Add partial riscv64 support for build root
- Provide basic VisionFive 2 support

* Mon May 12 2025 Jan Stancek <jstancek@redhat.com> [6.12.0-55.12.1.el10_0]
- scsi: core: Fix command pass through retry regression (Ewan D. Milne) [RHEL-77121]
- dm-flakey: Fix memory corruption in optional corrupt_bio_byte feature (CKI Backport Bot) [RHEL-86903] {CVE-2025-21966}
- ice: stop storing XDP verdict within ice_rx_buf (Petr Oros) [RHEL-86860]
- ice: gather page_count()'s of each frag right before XDP prog call (Petr Oros) [RHEL-86860]
- ice: put Rx buffers after being done with current frame (Petr Oros) [RHEL-86860]
- iscsi_ibft: Fix UBSAN shift-out-of-bounds warning in ibft_attr_show_nic() (CKI Backport Bot) [RHEL-86847] {CVE-2025-21993}

* Thu Apr 24 2025 Jan Stancek <jstancek@redhat.com> [6.12.0-55.11.1.el10_0]
- smb: client: fix regression with guest option (Jay Shin) [RHEL-83861]
- pnfs/flexfiles: retry getting layout segment for reads (Benjamin Coddington) [RHEL-87770]
- nfs: fix incorrect error handling in LOCALIO (Benjamin Coddington) [RHEL-87770]
- nfs: probe for LOCALIO when v3 client reconnects to server (Benjamin Coddington) [RHEL-87770]
- nfs: probe for LOCALIO when v4 client reconnects to server (Benjamin Coddington) [RHEL-87770]
- nfs/localio: remove redundant code and simplify LOCALIO enablement (Benjamin Coddington) [RHEL-87770]
- nfs_common: add nfs_localio trace events (Benjamin Coddington) [RHEL-87770]
- nfs_common: track all open nfsd_files per LOCALIO nfs_client (Benjamin Coddington) [RHEL-87770]
- nfs_common: rename nfslocalio nfs_uuid_lock to nfs_uuids_lock (Benjamin Coddington) [RHEL-87770]
- nfsd: nfsd_file_acquire_local no longer returns GC'd nfsd_file (Benjamin Coddington) [RHEL-87770]
- nfsd: rename nfsd_serv_ prefixed methods and variables with nfsd_net_ (Benjamin Coddington) [RHEL-87770]
- nfsd: update percpu_ref to manage references on nfsd_net (Benjamin Coddington) [RHEL-87770]
- nfs: cache all open LOCALIO nfsd_file(s) in client (Benjamin Coddington) [RHEL-87770]
- nfs_common: move localio_lock to new lock member of nfs_uuid_t (Benjamin Coddington) [RHEL-87770]
- nfs_common: rename functions that invalidate LOCALIO nfs_clients (Benjamin Coddington) [RHEL-87770]
- nfsd: add nfsd_file_{get,put} to 'nfs_to' nfsd_localio_operations (Benjamin Coddington) [RHEL-87770]
- nfs/localio: add direct IO enablement with sync and async IO support (Benjamin Coddington) [RHEL-87770]
- ice: ensure periodic output start time is in the future (Petr Oros) [RHEL-86858]
- ice: fix PHY Clock Recovery availability check (Petr Oros) [RHEL-86858]
- ice: Drop auxbus use for PTP to finalize ice_adapter move (Petr Oros) [RHEL-86858]
- ice: Use ice_adapter for PTP shared data instead of auxdev (Petr Oros) [RHEL-86858]
- ice: Initial support for E825C hardware in ice_adapter (Petr Oros) [RHEL-86858]
- ice: Add ice_get_ctrl_ptp() wrapper to simplify the code (Petr Oros) [RHEL-86858]
- ice: Introduce ice_get_phy_model() wrapper (Petr Oros) [RHEL-86858]
- ice: Enable 1PPS out from CGU for E825C products (Petr Oros) [RHEL-86858]
- ice: Read SDP section from NVM for pin definitions (Petr Oros) [RHEL-86858]
- ice: Disable shared pin on E810 on setfunc (Petr Oros) [RHEL-86858]
- ice: Cache perout/extts requests and check flags (Petr Oros) [RHEL-86858]
- ice: Align E810T GPIO to other products (Petr Oros) [RHEL-86858]
- ice: Add SDPs support for E825C (Petr Oros) [RHEL-86858]
- ice: Implement ice_ptp_pin_desc (Petr Oros) [RHEL-86858]
- nvme-tcp: fix potential memory corruption in nvme_tcp_recv_pdu() (Chris Leech) [RHEL-86922] {CVE-2025-21927}
- scsi: storvsc: Set correct data length for sending SCSI command without payload (Cathy Avery) [RHEL-83216]
- smb: client: fix chmod(2) regression with ATTR_READONLY (Jan Stancek) [RHEL-82677]
- mm/hugetlb: fix hugepage allocation for interleaved memory nodes (CKI Backport Bot) [RHEL-85441]

* Thu Apr 17 2025 Jan Stancek <jstancek@redhat.com> [6.12.0-55.10.1.el10_0]
- net: mana: use ethtool string helpers (Maxim Levitsky) [RHEL-85943]
- net: mana: cleanup mana struct after debugfs_remove() (Maxim Levitsky) [RHEL-85943]
- net: mana: Cleanup "mana" debugfs dir after cleanup of all children (Maxim Levitsky) [RHEL-85943]
- net: mana: Fix irq_contexts memory leak in mana_gd_setup_irqs (Maxim Levitsky) [RHEL-85943]
- net: mana: Fix memory leak in mana_gd_setup_irqs (Maxim Levitsky) [RHEL-85943]
- net :mana :Request a V2 response version for MANA_QUERY_GF_STAT (Maxim Levitsky) [RHEL-85943]
- net: mana: Enable debugfs files for MANA device (Maxim Levitsky) [RHEL-85943]
- net: mana: Add get_link and get_link_ksettings in ethtool (Maxim Levitsky) [RHEL-85943]
- net: mana: Increase the DEF_RX_BUFFERS_PER_QUEUE to 1024 (Maxim Levitsky) [RHEL-85943]
- redhat: drop Y issues from changelog (Jan Stancek)

* Tue Mar 25 2025 Jan Stancek <jstancek@redhat.com> [6.12.0-55.9.1.el10_0]
- af_packet: fix vlan_get_protocol_dgram() vs MSG_PEEK (Davide Caratti) [RHEL-80306] {CVE-2024-57901}
- redhat: kabi: update stablelist checksums (Čestmír Kalina) [RHEL-80552]
- shrinker: include rh_kabi.h (Čestmír Kalina) [RHEL-80552]
- redhat: pad the folio_batch struct (Nico Pache) [RHEL-80552]
- redhat: pad the lruvec structure for the kabi (Nico Pache) [RHEL-80552]
- redhat: pad the zone structures for kabi (Nico Pache) [RHEL-80552]
- redhat: pad the wait_page_queue for the kabi (Nico Pache) [RHEL-80552]
- redhat: pad the lru_gen functions for kabi (Nico Pache) [RHEL-80552]
- redhat: pad the vmem_altmap struct for the kabi (Nico Pache) [RHEL-80552]
- redhat: pad the vm_fault structure (Nico Pache) [RHEL-80552]
- redhat: pad the tlbflush_unmap_batch struct for the KABI (Nico Pache) [RHEL-80552]
- redhat: pad the swap_cluster_info structure for KABI (Nico Pache) [RHEL-80552]
- redhat: pad the shrinker struct for KABI (Nico Pache) [RHEL-80552]
- redhat: pad the shrink_control structure for kabi (Nico Pache) [RHEL-80552]
- redhat: pad the readahead_control structure for kabi (Nico Pache) [RHEL-80552]
- redhat: pad the pglist_data structure for kabi (Nico Pache) [RHEL-80552]
- redhat: pad the percpu structures (Nico Pache) [RHEL-80552]
- redhat: pad the page_frag_cache for the kabi (Nico Pache) [RHEL-80552]
- redhat: pad the ns_common structure for kabi (Nico Pache) [RHEL-80552]
- redhat: pad mmu_notifier functions for kabi (Nico Pache) [RHEL-80552]
- redhat: pad the mm_struct for kabi (Nico Pache) [RHEL-80552]
- redhat: pad mempool_s structure for kabi (Nico Pache) [RHEL-80552]
- redhat: pad mempolicy struct for kabi (Nico Pache) [RHEL-80552]
- redhat: pad the memory_failure_stats for kabi (Nico Pache) [RHEL-80552]
- redhat: pad the kmem_cache_args struct (Nico Pache) [RHEL-80552]
- redhat: pad the kmem_cache structure (Nico Pache) [RHEL-80552]
- redhat: pad ip_conntrack_stat for kabi (Nico Pache) [RHEL-80552]
- redhat: pad the free_area struct (Nico Pache) [RHEL-80552]
- redhat: pad follow_pfnmap_args for kabi (Nico Pache) [RHEL-80552]
- redhat: pad anon_vma for kabi (Nico Pache) [RHEL-80552]
- redhat: pad access_coordinate for kabi (Nico Pache) [RHEL-80552]
- redhat: pad the deferred_split queue for the kabi checker (Nico Pache) [RHEL-80552]
- redhat: hide capture_control from kabi checker (Nico Pache) [RHEL-80552]
- mm/memcg: Exclude mem_cgroup/obj_cgroup pointer from kABI signature computation (Waiman Long) [RHEL-80552]
- net: stmmac: dwmac-tegra: Read iommu stream id from device tree (Izabela Bakollari) [RHEL-75653] {CVE-2025-21663}
- Revert "smb: client: fix chmod(2) regression with ATTR_READONLY" (Jan Stancek)

* Thu Mar 20 2025 Jan Stancek <jstancek@redhat.com> [6.12.0-55.8.1.el10_0]
- crypto: api - Fix larval relookup type and mask (Herbert Xu) [RHEL-78993]

* Mon Mar 17 2025 Jan Stancek <jstancek@redhat.com> [6.12.0-55.7.1.el10_0]
- Enable Intel VPU driver for RHEL (Fabien Dupont) [RHEL-38582]
- arm64: cacheinfo: Avoid out-of-bounds write to cacheinfo array (Radu Rendec) [RHEL-80226]
- smb: client: fix chmod(2) regression with ATTR_READONLY (Jay Shin) [RHEL-82677 RHEL-80534]
- kabi: enable check-kabi (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol zap_vma_ptes to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xsk_uses_need_wakeup to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xsk_tx_release to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xsk_tx_peek_release_desc_batch to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xsk_tx_peek_desc to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xsk_tx_completed to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xsk_set_tx_need_wakeup to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xsk_set_rx_need_wakeup to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xsk_get_pool_from_qid to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xsk_clear_rx_need_wakeup to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xp_set_rxq_info to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xp_raw_get_dma to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xp_free to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xp_fill_cb to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xp_dma_unmap to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xp_dma_map to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xp_can_alloc to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xp_alloc_batch to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xdp_warn to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xdp_set_features_flag to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xdp_rxq_info_unreg_mem_model to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xdp_rxq_info_unreg to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xdp_rxq_info_reg_mem_model to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __xdp_rxq_info_reg to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xdp_rxq_info_is_reg to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xdp_return_frame_rx_napi to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xdp_return_frame_bulk to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xdp_return_frame to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xdp_return_buff to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xdp_master_redirect to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xdp_flush_frame_bulk to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xdp_features_set_redirect_target to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xdp_features_clear_redirect_target to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xdp_do_redirect to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xdp_do_flush to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xdp_convert_zc_to_xdp_frame to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xa_store to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xa_load to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __xa_insert to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xa_find_after to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xa_find to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xa_erase to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol xa_destroy to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __xa_alloc to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __x86_return_thunk to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __x86_indirect_thunk_rsi to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __x86_indirect_thunk_rdx to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __x86_indirect_thunk_rdi to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __x86_indirect_thunk_rcx to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __x86_indirect_thunk_rbx to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __x86_indirect_thunk_rbp to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __x86_indirect_thunk_rax to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __x86_indirect_thunk_r9 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __x86_indirect_thunk_r8 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __x86_indirect_thunk_r15 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __x86_indirect_thunk_r14 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __x86_indirect_thunk_r13 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __x86_indirect_thunk_r12 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __x86_indirect_thunk_r11 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __x86_indirect_thunk_r10 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol x86_cpu_to_apicid to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __warn_printk to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol wake_up_process to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __wake_up to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol wait_for_completion_timeout to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol wait_for_completion_io_timeout to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol wait_for_completion_interruptible to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol wait_for_completion to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol vzalloc_noprof to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol vsprintf to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol vsnprintf to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol vscnprintf to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol vm_munmap to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol vm_mmap to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol vmemmap_base to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol vmalloc_noprof to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol vmalloc_node_noprof to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol vmalloc_base to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol vmalloc_array_noprof to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol vlan_dev_vlan_id to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol vlan_dev_real_dev to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __virt_addr_valid to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol vfs_unlink to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol vfs_mknod to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol vfs_mkdir to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol vfs_fsync_range to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol vfree to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol uv_undefined to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol uv_teardown_irq to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol uv_setup_irq to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol uv_possible_blades to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __uv_hub_info_list to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol uv_get_hubless_system to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __uv_cpu_info to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol uv_bios_obj_count to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol uv_bios_install_heap to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol uv_bios_get_pci_topology to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol uv_bios_get_master_nasid to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol uv_bios_get_heapsize to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol uv_bios_get_geoinfo to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol uv_bios_enum_ports to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol uv_bios_enum_objs to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol usleep_range_state to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol up_write to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol up_read to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol up to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol unregister_switchdev_notifier to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol unregister_switchdev_blocking_notifier to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol unregister_reboot_notifier to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol unregister_netevent_notifier to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol unregister_netdevice_notifier to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol unregister_netdev to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol unregister_kprobe to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol unregister_inetaddr_notifier to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol unregister_inet6addr_notifier to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol unregister_chrdev_region to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __unregister_chrdev to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol unregister_blkdev to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol udp_tunnel_nic_ops to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __udelay to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol tty_unregister_driver to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol tty_termios_encode_baud_rate to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol tty_std_termios to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol tty_register_driver to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol tty_port_link_device to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol tty_port_init to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol tty_port_destroy to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol tty_flip_buffer_push to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol tty_driver_kref_put to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol tty_buffer_request_room to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __tty_alloc_driver to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol tsc_khz to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol try_module_get to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __trace_trigger_soft_disabled to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol trace_raw_output_prep to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol trace_print_bitmask_seq to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __tracepoint_xdp_exception to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __tracepoint_mmap_lock_start_locking to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __tracepoint_mmap_lock_released to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __tracepoint_mmap_lock_acquire_returned to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol trace_handle_return to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol trace_event_reg to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol trace_event_raw_init to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol trace_event_printf to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol trace_event_ignore_this_pid to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol trace_event_buffer_reserve to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol trace_event_buffer_commit to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol trace_array_set_clr_event to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol trace_array_put to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol trace_array_get_by_name to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol touch_softlockup_watchdog to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol tls_validate_xmit_skb to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol tls_get_record to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol tls_encrypt_skb to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol tls_device_sk_destruct to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol timer_shutdown_sync to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol timer_shutdown to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol timer_delete_sync to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol timer_delete to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol timecounter_read to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol timecounter_init to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol timecounter_cyc2time to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol time64_to_tm to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol tcp_gro_complete to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __tasklet_schedule to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol tasklet_kill to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol tasklet_init to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sys_tz to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol system_wq to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol system_unbound_wq to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol system_state to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sysfs_streq to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sysfs_remove_group to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sysfs_remove_file_ns to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sysfs_remove_bin_file to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __sysfs_match_string to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sysfs_emit to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sysfs_create_group to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sysfs_create_file_ns to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sysfs_create_bin_file to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol synchronize_rcu to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol synchronize_net to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol synchronize_irq to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sync_blockdev to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __symbol_put to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __symbol_get to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol switchdev_handle_port_obj_del to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol switchdev_handle_port_obj_add to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol switchdev_handle_port_attr_set to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __sw_hweight64 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __sw_hweight32 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol submit_bio_noacct to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol strstr to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol strsep to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol strrchr to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol strnlen to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol strncpy_from_user to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol strncpy to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol strncmp to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol strncasecmp to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol strlen to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol strlcat to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol strim to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol strcspn to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol strcpy to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol strcmp to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol strchr to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol strcat to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol strcasecmp to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol static_key_slow_inc to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol static_key_slow_dec to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol static_key_enable to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol static_key_disable to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol static_key_count to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol starget_for_each_device to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __stack_chk_fail to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sscanf to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sprintf to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sort to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol softnet_data to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sock_gen_put to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sn_region_size to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol snprintf to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sn_partition_id to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol smp_call_function_single_async to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol smp_call_function_single to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol smp_call_function_many to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol slab_build_skb to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sk_skb_reason_drop to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sk_free to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol skb_tstamp_tx to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol skb_realloc_headroom to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol skb_queue_tail to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol skb_put to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol skb_push to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol skb_pull to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __skb_pad to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __skb_gso_segment to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __skb_flow_dissect to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol skb_dequeue to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol skb_copy_header to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol skb_copy_expand to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol skb_copy_bits to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol skb_copy to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol skb_clone_tx_timestamp to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol skb_clone to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol skb_checksum_help to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol skb_add_rx_frag_netmem to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sk_alloc to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sized_strscpy to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol single_release to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol single_open to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol simple_write_to_buffer to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol simple_strtoul to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol simple_strtol to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol simple_read_from_buffer to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol simple_open to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol simple_attr_release to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol simple_attr_open to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol si_meminfo to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sg_pcopy_to_buffer to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sg_pcopy_from_buffer to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sg_next to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sg_nents to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sg_miter_stop to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sg_miter_start to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sg_miter_next to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sg_copy_to_buffer to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sg_copy_from_buffer to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sg_copy_buffer to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol set_user_nice to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol set_normalized_timespec64 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol set_memory_wc to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol set_cpus_allowed_ptr to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol set_capacity to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol set_blocksize to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol seq_write to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol seq_release to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol seq_read to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __seq_puts to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol seq_putc to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol seq_printf to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol seq_open to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol seq_lseek to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol send_sig to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol secpath_set to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sdev_prefix_printk to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __SCT__tp_func_xdp_exception to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __SCT__preempt_schedule_notrace to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __SCT__preempt_schedule to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __SCT__might_resched to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __SCT__cond_resched to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_unblock_requests to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_scan_target to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_scan_host to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_sanitize_inquiry_string to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_rescan_device to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_remove_target to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_remove_host to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_remove_device to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_print_command to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_normalize_sense to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsilun_to_int to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __scsi_iterate_devices to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_is_sdev_device to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_is_host_device to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_is_fc_rport to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_host_put to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_host_get to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_host_busy to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_host_alloc to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_get_vpd_page to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_done to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_dma_unmap to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_dma_map to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_device_type to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_device_set_state to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_device_put to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_device_lookup to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_device_from_queue to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_change_queue_depth to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_build_sense_buffer to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_build_sense to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_block_requests to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_add_host_with_dma to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scsi_add_device to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scnprintf to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol scmd_printk to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __SCK__tp_func_xdp_exception to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol schedule_timeout_uninterruptible to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol schedule_timeout to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol schedule to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sched_clock to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sas_rphy_free to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sas_rphy_add to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sas_remove_host to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sas_release_transport to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sas_port_free to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sas_port_delete_phy to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sas_port_delete to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sas_port_alloc_num to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sas_port_add_phy to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sas_port_add to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sas_phy_free to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sas_phy_delete to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sas_phy_alloc to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sas_phy_add to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sas_expander_alloc to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sas_end_device_alloc to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sas_attach_transport to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol sas_ata_ncq_prio_supported to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol rtnl_unlock to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol rtnl_trylock to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol rtnl_lock to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol rtnl_is_locked to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol rps_may_expire_flow to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol round_jiffies to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol root_device_unregister to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __root_device_register to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol rht_bucket_nested_insert to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol rht_bucket_nested to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __rht_bucket_nested to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol rhashtable_walk_stop to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol rhashtable_walk_start_check to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol rhashtable_walk_next to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol rhashtable_walk_exit to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol rhashtable_walk_enter to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol rhashtable_insert_slow to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol rhashtable_init_noprof to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol rhashtable_destroy to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol reset_devices to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol request_threaded_irq to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __request_region to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __request_module to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol request_firmware_nowait to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol request_firmware to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol remove_wait_queue to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol remove_proc_entry to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol remap_pfn_range to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __release_region to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol release_firmware to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol register_switchdev_notifier to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol register_switchdev_blocking_notifier to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol register_reboot_notifier to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol register_netevent_notifier to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol register_netdevice_notifier to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol register_netdevice to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol register_netdev to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol register_kprobe to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol register_inetaddr_notifier to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol register_inet6addr_notifier to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol register_chrdev_region to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __register_chrdev to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __register_blkdev to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __refrigerator to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol refcount_warn_saturate to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol rcuref_get_slowpath to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __rcu_read_unlock to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __rcu_read_lock to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol rb_next to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol rb_first to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _raw_write_unlock_irqrestore to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _raw_write_unlock to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _raw_write_lock_irqsave to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _raw_write_lock to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _raw_spin_unlock_irqrestore to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _raw_spin_unlock_irq to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _raw_spin_unlock_bh to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _raw_spin_unlock to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _raw_spin_trylock to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _raw_spin_lock_irqsave to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _raw_spin_lock_irq to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _raw_spin_lock_bh to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _raw_spin_lock to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _raw_read_unlock_irqrestore to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _raw_read_unlock to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _raw_read_lock_irqsave to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _raw_read_lock to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ___ratelimit to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol radix_tree_lookup to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol queue_work_on to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol queue_limits_commit_update to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol queue_delayed_work_on to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol qdisc_reset to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __put_user_8 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __put_user_4 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __put_user_2 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol put_disk to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __put_devmap_managed_folio_refs to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol put_device to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ptrs_per_p4d to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ptp_schedule_worker to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ptp_parse_header to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ptp_find_pin to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ptp_clock_unregister to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ptp_clock_register to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ptp_clock_index to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ptp_clock_event to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ptp_classify_raw to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ___pskb_trim to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __pskb_pull_tail to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pskb_expand_head to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol proc_remove to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol proc_mkdir to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol proc_create_data to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol proc_create to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol priv_to_devlink to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __printk_ratelimit to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _printk to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol print_hex_dump to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol prepare_to_wait_event to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol prepare_to_wait to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol prepare_creds to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pm_schedule_suspend to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __pm_runtime_resume to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __pm_runtime_idle to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pldmfw_op_pci_match_record to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pldmfw_flash_image to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pid_task to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol phy_validate_pause to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol phy_support_asym_pause to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol phy_stop to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol phy_start_aneg to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol phy_start to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol physical_mask to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol phy_set_max_speed to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol phy_set_asym_pause to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol phys_base to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol phy_mii_ioctl to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol phy_ethtool_ksettings_set to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol phy_ethtool_ksettings_get to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol phy_disconnect to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol phy_connect to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol phy_attached_info to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pgdir_shift to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol perf_trace_run_bpf_submit to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol perf_trace_buf_alloc to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __per_cpu_offset to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pcpu_hot to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pcpu_alloc_noprof to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pcix_set_mmrbc to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_write_config_word to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_write_config_dword to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_write_config_byte to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_wake_from_d3 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_wait_for_pending_transaction to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_vpd_find_ro_info_keyword to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_vpd_check_csum to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_vpd_alloc to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_vfs_assigned to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_unregister_driver to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_try_set_mwi to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_sriov_set_totalvfs to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_set_power_state to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_set_mwi to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_set_master to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_select_bars to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_save_state to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_restore_state to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_restore_msi_state to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_reset_bus to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_request_selected_regions to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_request_regions to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_release_selected_regions to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_release_regions to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __pci_register_driver to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_read_vpd to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_read_config_word to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_read_config_dword to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_read_config_byte to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_prepare_to_sleep to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_num_vf to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_msix_free_irq to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_msix_can_alloc_dyn to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_msix_alloc_irq_at to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pcim_iomap_table to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pcim_iomap_regions to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pcim_enable_device to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_irq_vector to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_irq_get_affinity to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_iov_virtfn_devfn to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_iounmap to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_ioremap_bar to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_iomap to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_get_slot to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_get_dsn to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_get_domain_bus_and_slot to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_get_device to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_free_irq_vectors to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_find_ext_capability to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_find_capability to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pcie_set_readrq to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pcie_print_link_status to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_enable_wake to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_enable_sriov to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_enable_msix_range to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_enable_msi to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_enable_device_mem to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_enable_device to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pcie_get_readrq to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pcie_flr to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pcie_capability_write_word to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pcie_capability_read_word to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pcie_capability_read_dword to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pcie_capability_clear_and_set_word_unlocked to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pcie_capability_clear_and_set_word_locked to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_disable_sriov to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_disable_rom to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_disable_msix to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_disable_msi to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_disable_device to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_dev_put to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_dev_present to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_device_is_present to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_dev_get to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_clear_mwi to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_clear_master to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_choose_state to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_cfg_access_unlock to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_cfg_access_lock to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_bus_type to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_alloc_irq_vectors_affinity to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_alloc_irq_vectors to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol pci_aer_clear_nonfatal_status to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol path_put to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol param_ops_ushort to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol param_ops_ulong to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol param_ops_ullong to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol param_ops_uint to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol param_ops_long to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol param_ops_int to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol param_ops_charp to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol param_ops_byte to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol param_ops_bool to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol param_array_ops to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol panic_notifier_list to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol panic to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol page_pool_put_unrefed_netmem to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol page_pool_disable_direct_recycling to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol page_pool_destroy to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol page_pool_create to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol page_pool_alloc_pages to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol page_pool_alloc_frag to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol page_offset_base to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol page_frag_free to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __page_frag_cache_drain to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol nvmet_fc_unregister_targetport to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol nvmet_fc_register_targetport to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol nvmet_fc_rcv_ls_req to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol nvmet_fc_rcv_fcp_req to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol nvmet_fc_rcv_fcp_abort to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol nvmet_fc_invalidate_host to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol nvme_fc_unregister_remoteport to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol nvme_fc_unregister_localport to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol nvme_fc_set_remoteport_devloss to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol nvme_fc_rescan_remoteport to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol nvme_fc_register_remoteport to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol nvme_fc_register_localport to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol nvme_fc_rcv_ls_req to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol nvme_fc_io_getuuid to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __num_online_cpus to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol numa_node to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ns_to_timespec64 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol nr_cpu_ids to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol noop_llseek to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol node_to_cpumask_map to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol node_states to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __node_distance to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol nla_find to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol net_ratelimit to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netif_tx_wake_queue to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netif_tx_unlock to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netif_tx_stop_all_queues to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netif_tx_lock to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netif_set_xps_queue to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netif_set_tso_max_size to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netif_set_tso_max_segs to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netif_set_real_num_tx_queues to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netif_set_real_num_rx_queues to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netif_schedule_queue to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netif_rx to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netif_receive_skb to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netif_queue_set_napi to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __netif_napi_del to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netif_napi_add_weight to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netif_get_num_default_rss_queues to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netif_device_detach to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netif_device_attach to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netif_carrier_on to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netif_carrier_off to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol net_dim_get_rx_moderation to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol net_dim to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netdev_warn to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netdev_walk_all_upper_dev_rcu to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netdev_update_features to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netdev_unbind_sb_channel to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netdev_state_change to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netdev_set_tc_queue to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netdev_set_sb_channel to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netdev_set_num_tc to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netdev_rx_handler_unregister to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netdev_rx_handler_register to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netdev_rss_key_fill to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netdev_reset_tc to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netdev_refcnt_read to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netdev_printk to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netdev_port_same_parent_id to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netdev_pick_tx to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netdev_notice to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netdev_master_upper_dev_get_rcu to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netdev_master_upper_dev_get to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netdev_info to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netdev_features_change to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netdev_err to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netdev_crit to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netdev_core_stats_inc to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol netdev_bind_sb_channel_queue to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __netdev_alloc_skb to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __netdev_alloc_frag_align to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __neigh_event_send to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol neigh_destroy to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ndo_dflt_fdb_add to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ndo_dflt_bridge_getlink to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __ndelay to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol napi_schedule_prep to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __napi_schedule_irqoff to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __napi_schedule to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol napi_gro_receive to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol napi_enable to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol napi_disable to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol napi_consume_skb to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol napi_complete_done to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol napi_build_skb to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol napi_alloc_skb to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __napi_alloc_frag_align to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol names_cachep to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mutex_unlock to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mutex_trylock to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mutex_lock_interruptible to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mutex_lock to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mutex_is_locked to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __mutex_init to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol msleep_interruptible to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol msleep to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __msecs_to_jiffies to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mpi_read_raw_data to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mpi_powm to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mpi_get_buffer to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mpi_free to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mpi_alloc to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol module_put to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol module_layout to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __module_get to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mod_timer to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mod_delayed_work_on to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mmu_notifier_put to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mmu_notifier_get_locked to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mmput to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __mmap_lock_do_trace_start_locking to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __mmap_lock_do_trace_released to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __mmap_lock_do_trace_acquire_returned to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mlx5_core_uplink_netdev_event_replay to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mlx5_core_access_reg to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mlx5_blocking_notifier_unregister to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mlx5_blocking_notifier_register to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol misc_register to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol misc_deregister to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol metadata_dst_free to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol metadata_dst_alloc to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol memset to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mem_section to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mempool_kmalloc to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mempool_kfree to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mempool_free_slab to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mempool_free to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mempool_destroy to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mempool_create_node_noprof to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mempool_alloc_slab to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mempool_alloc_noprof to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol memory_read_from_buffer to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol memmove to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol memdup_user_nul to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol memdup_user to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol memcpy_toio to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol memcpy_fromio to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol memcpy to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol memcmp to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol memchr_inv to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol memchr to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mds_idle_clear to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mdio_mii_ioctl to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mdiobus_write to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mdiobus_unregister to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __mdiobus_register to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mdiobus_read to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mdiobus_get_phy to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mdiobus_free to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mdiobus_c45_write to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mdiobus_c45_read to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mdiobus_alloc_size to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol mdio45_probe to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol lookup_one_len to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol local_clock to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __local_bh_enable_ip to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __list_del_entry_valid_or_report to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __list_add_valid_or_report to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol libie_rx_pt_lut to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol libeth_rx_recycle_slow to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol libeth_rx_fq_destroy to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol libeth_rx_fq_create to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kvfree_call_rcu to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ktime_get_with_offset to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ktime_get_ts64 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ktime_get_seconds to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ktime_get_real_ts64 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ktime_get_real_seconds to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ktime_get_raw_ts64 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ktime_get to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kthread_use_mm to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kthread_unuse_mm to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kthread_stop to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kthread_should_stop to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kthread_queue_work to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kthread_queue_delayed_work to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kthread_destroy_worker to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kthread_delayed_work_timer_fn to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kthread_create_worker to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kthread_create_on_node to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kthread_complete_and_exit to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kthread_cancel_work_sync to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kthread_cancel_delayed_work_sync to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kthread_bind to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kstrtoull to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kstrtouint to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kstrtou8 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kstrtou16 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kstrtos16 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kstrtoll to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kstrtoint to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kstrtobool to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ksize to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol krealloc_noprof to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kobject_uevent_env to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kobject_uevent to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kobject_set_name to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kobject_put to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kobject_init_and_add to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kobject_get_unless_zero to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kobject_create_and_add to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kmemdup_noprof to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kmem_cache_free to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kmem_cache_destroy to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __kmem_cache_create_args to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kmem_cache_alloc_noprof to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kmalloc_size_roundup to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __kmalloc_noprof to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __kmalloc_node_noprof to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __kmalloc_large_noprof to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __kmalloc_large_node_noprof to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kmalloc_caches to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __kmalloc_cache_noprof to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __kmalloc_cache_node_noprof to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kill_pid to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kill_pgrp to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kill_fasync to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kfree_sensitive to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kfree to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kexec_crash_loaded to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kern_path_create to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kern_path to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kernel_write to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kernel_sigaction to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kernel_read to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol kasprintf to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol jiffies_to_usecs to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol jiffies_to_msecs to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol jiffies to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol iter_div_u64_rem to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol is_vmalloc_addr to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol is_uv_system to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol irq_set_affinity_notifier to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol irq_set_affinity to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol irq_poll_sched to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol irq_poll_init to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol irq_poll_enable to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol irq_poll_disable to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol irq_poll_complete to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol irq_modify_status to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol irq_cpu_rmap_add to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __irq_apply_affinity_hint to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ipv6_skip_exthdr to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ipv6_find_hdr to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ipv6_ext_hdr to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol iput to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ip_route_output_flow to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ip_queue_xmit to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ip_compute_csum to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ip6_route_output_flags to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ip6_dst_hoplimit to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __iowrite64_copy to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol iounmap to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ioremap_wc to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ioremap to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __ioread32_copy to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol iomem_resource to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol invalidate_bdev to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol int_to_scsilun to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __init_waitqueue_head to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol init_wait_entry to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol init_uts_ns to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol init_user_ns to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol init_timer_key to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __init_swait_queue_head to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __init_rwsem to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol init_net to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __inet_lookup_established to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol inet_del_protocol to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol inet_add_protocol to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __inet6_lookup_established to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ilookup to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol idr_remove to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol idr_find to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol idr_destroy to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol idr_alloc to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ida_free to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ida_destroy to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ida_alloc_range to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol I_BDEV to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol i2c_smbus_write_byte_data to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol i2c_smbus_read_byte_data to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol i2c_new_client_device to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol i2c_del_adapter to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol i2c_bit_add_bus to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol hwmon_notify_event to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol hwmon_device_unregister to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol hwmon_device_register_with_info to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol hwmon_device_register_with_groups to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol hwmon_device_register to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __hw_addr_unsync_dev to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __hw_addr_sync_dev to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __hw_addr_init to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol hugetlb_optimize_vmemmap_key to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol hrtimer_start_range_ns to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol hrtimer_init to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol hrtimer_forward to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol hrtimer_cancel to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol gnss_register_device to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol gnss_put_device to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol gnss_insert_raw to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol gnss_deregister_device to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol gnss_allocate_device to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol get_zeroed_page_noprof to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol get_user_pages_remote to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __get_user_4 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __get_user_2 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol get_random_u32 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol get_random_u16 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol get_random_bytes to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol get_free_pages_noprof to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol get_device_system_crosststamp to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol get_device to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol get_cpu_idle_time to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol generic_file_write_iter to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol generic_file_read_iter to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol fs_bio_set to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol freezing_slow_path to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol free_percpu to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol free_pages to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __free_pages to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol free_netdev to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol free_irq_cpu_rmap to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol free_irq to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol free_cpumask_var to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol fput to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __fortify_panic to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __folio_put to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __flush_workqueue to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol flush_work to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol flush_signals to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol flow_rule_match_vlan to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol flow_rule_match_tcp to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol flow_rule_match_pppoe to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol flow_rule_match_ports to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol flow_rule_match_l2tpv3 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol flow_rule_match_ipv6_addrs to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol flow_rule_match_ipv4_addrs to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol flow_rule_match_ip to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol flow_rule_match_icmp to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol flow_rule_match_eth_addrs to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol flow_rule_match_enc_ports to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol flow_rule_match_enc_opts to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol flow_rule_match_enc_keyid to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol flow_rule_match_enc_ipv6_addrs to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol flow_rule_match_enc_ipv4_addrs to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol flow_rule_match_enc_ip to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol flow_rule_match_enc_control to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol flow_rule_match_cvlan to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol flow_rule_match_control to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol flow_rule_match_basic to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol flow_keys_dissector to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol flow_indr_dev_unregister to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol flow_indr_dev_register to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol flow_indr_block_cb_alloc to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol flow_block_cb_setup_simple to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol flow_block_cb_lookup to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol fixed_size_llseek to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol firmware_request_nowarn to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol finish_wait to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol find_vma to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol find_pid_ns to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _find_next_zero_bit to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _find_next_bit to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _find_next_and_bit to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _find_last_bit to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _find_first_zero_bit to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _find_first_bit to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol filp_open to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol filp_close to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol file_ns_capable to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol file_bdev to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol fget to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __fentry__ to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol fc_vport_terminate to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol fc_vport_create to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol fc_remove_host to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol fc_remote_port_rolechg to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol fc_remote_port_delete to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol fc_remote_port_add to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol fc_release_transport to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol fc_host_post_vendor_event to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol fc_host_post_event to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol fc_host_fpin_rcv to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol fc_get_event_number to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol fc_eh_timed_out to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol fc_eh_should_retry_cmd to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol fc_block_scsi_eh to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol fc_block_rport to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol fc_attach_transport to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol fasync_helper to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol event_triggers_call to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol eth_validate_addr to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol eth_type_trans to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ethtool_sprintf to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ethtool_rxfh_context_lost to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ethtool_puts to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ethtool_params_from_link_mode to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ethtool_op_get_ts_info to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ethtool_op_get_link to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ethtool_intersect_link_masks to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ethtool_forced_speed_maps_init to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ethtool_convert_link_mode_to_legacy_u32 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ethtool_convert_legacy_u32_to_link_mode to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol eth_platform_get_mac_address to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol eth_get_headlen to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol ether_setup to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol enable_irq to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol empty_zero_page to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol emergency_restart to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol elfcorehdr_addr to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __dynamic_pr_debug to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __dynamic_netdev_dbg to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __dynamic_dev_dbg to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dump_stack to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dst_release to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol driver_remove_file to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol driver_for_each_device to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol driver_create_file to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dql_reset to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dql_completed to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dput to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dpll_pin_unregister to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dpll_pin_register to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dpll_pin_put to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dpll_pin_on_pin_unregister to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dpll_pin_on_pin_register to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dpll_pin_get to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dpll_pin_change_ntf to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dpll_netdev_pin_set to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dpll_netdev_pin_clear to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dpll_device_unregister to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dpll_device_register to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dpll_device_put to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dpll_device_get to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dpll_device_change_ntf to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol down_write_trylock to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol down_write to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol down_trylock to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol down_read_trylock to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol down_read to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol down_interruptible to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol downgrade_write to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol down to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol do_trace_netlink_extack to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol done_path_create to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dmi_get_system_info to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dmi_find_device to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dma_unmap_sg_attrs to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dma_unmap_page_attrs to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __dma_sync_single_for_device to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __dma_sync_single_for_cpu to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dma_set_mask to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dma_set_coherent_mask to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dma_pool_free to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dma_pool_destroy to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dma_pool_create to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dma_pool_alloc to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dmam_free_coherent to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dma_map_sg_attrs to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dma_map_page_attrs to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dmam_alloc_attrs to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dma_get_required_mask to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dma_free_attrs to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dma_alloc_attrs to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol disable_irq_nosync to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol disable_irq to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dget_parent to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _dev_warn to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dev_uc_del to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dev_uc_add_excl to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dev_uc_add to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dev_trans_start to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dev_set_promiscuity to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dev_set_name to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dev_set_mtu to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dev_set_mac_address to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dev_remove_pack to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __dev_queue_xmit to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _dev_printk to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dev_open to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _dev_notice to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devm_request_threaded_irq to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devm_mdiobus_alloc_size to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devm_kmemdup to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devm_kmalloc to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devm_kfree to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devm_kasprintf to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devm_hwmon_device_register_with_groups to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devm_free_irq to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dev_mc_del_global to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dev_mc_del to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dev_mc_add_global to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dev_mc_add_excl to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dev_mc_add to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devmap_managed_key to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __devm_add_action to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devl_unregister to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devl_unlock to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devl_register to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devl_region_destroy to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devl_region_create to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devl_rate_nodes_destroy to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devl_rate_node_create to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devl_rate_leaf_destroy to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devl_rate_leaf_create to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devl_port_unregister to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devl_port_register_with_ops to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devl_port_fn_devlink_set to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devl_params_unregister to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devl_params_register to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devl_nested_devlink_set to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devl_lock to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devlink_unregister to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devlink_remote_reload_actions_performed to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devlink_register to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devlink_priv to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devlink_port_unregister to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devlink_port_register_with_ops to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devlink_port_attrs_set to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devlink_params_unregister to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devlink_params_register to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devlink_info_version_stored_put to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devlink_info_version_running_put to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devlink_info_version_fixed_put to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devlink_info_serial_number_put to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devlink_info_board_serial_number_put to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devlink_health_reporter_state_update to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devlink_health_reporter_recovery_done to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devlink_health_reporter_priv to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devlink_health_reporter_destroy to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devlink_health_reporter_create to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devlink_health_report to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devlink_free to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devlink_fmsg_u32_pair_put to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devlink_fmsg_string_pair_put to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devlink_fmsg_pair_nest_start to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devlink_fmsg_pair_nest_end to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devlink_fmsg_binary_pair_put to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devlink_flash_update_timeout_notify to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devlink_flash_update_status_notify to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devlink_alloc_ns to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol devl_assert_locked to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dev_kfree_skb_irq_reason to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dev_kfree_skb_any_reason to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _dev_info to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol device_wakeup_disable to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol device_unregister to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol device_show_string to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol device_set_wakeup_enable to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol device_set_wakeup_capable to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol device_remove_file to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol device_register to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol device_initialize to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol device_destroy to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol device_del to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol device_create_file to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol device_create to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol device_add_disk to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol device_add to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dev_get_stats to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dev_get_by_name to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _dev_err to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dev_driver_string to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _dev_crit to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dev_close to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dev_addr_mod to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dev_addr_del to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dev_addr_add to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dev_add_pack to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol destroy_workqueue to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol del_gendisk to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol delayed_work_timer_fn to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol default_wake_function to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol default_llseek to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol debugfs_remove to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol debugfs_lookup to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol debugfs_create_u32 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol debugfs_create_file to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol debugfs_create_dir to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol debugfs_create_devm_seqfile to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol debugfs_attr_write to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol debugfs_attr_read to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dcbnl_ieee_notify to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dcb_ieee_setapp to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dcb_ieee_getapp_prio_dscp_mask_map to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dcb_ieee_getapp_mask to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dcb_ieee_delapp to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dcb_getapp to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dca_unregister_notify to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dca_remove_requester to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dca_register_notify to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dca_add_requester to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol dca3_get_tag to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol current_work to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _ctype to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol csum_partial to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol csum_ipv6_magic to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol crypto_shash_update to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol crypto_shash_final to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol crypto_destroy_tfm to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol crypto_alloc_shash to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol crc_t10dif to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol crc32_le to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol cpu_sibling_map to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __cpu_present_mask to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __cpu_possible_mask to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __cpu_online_mask to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol cpumask_next_wrap to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol cpumask_local_spread to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol cpu_khz to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol cpu_info to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __cpuhp_state_remove_instance to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __cpuhp_state_add_instance to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __cpuhp_setup_state to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __cpuhp_remove_state to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol cpufreq_quick_get to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol cpu_bit_bitmap to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _copy_to_user to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __copy_overflow to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _copy_from_user to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol consume_skb to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __const_udelay to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol const_pcpu_hot to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol complete_all to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol complete to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol commit_creds to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol clock_t_to_jiffies to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol class_unregister to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol class_register to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol class_destroy to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol class_create to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __check_object_size to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol cdev_init to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol cdev_del to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol cdev_alloc to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol cdev_add to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol cc_mkdec to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol capable to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol cancel_work_sync to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol cancel_delayed_work_sync to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol cancel_delayed_work to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol call_usermodehelper to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol call_switchdev_notifiers to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol call_netdevice_notifiers to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol cachemode2protval to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol byte_rev_table to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol build_skb to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol btree_update to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol btree_remove to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol btree_lookup to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol btree_last to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol btree_insert to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol btree_init to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol btree_get_prev to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol btree_geo64 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol btree_geo32 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol btree_destroy to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bsg_setup_queue to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bsg_remove_queue to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bsg_job_done to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __break_lease to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bpf_warn_invalid_xdp_action to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bpf_trace_run8 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bpf_trace_run4 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bpf_trace_run3 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bpf_trace_run2 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bpf_trace_run1 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bpf_stats_enabled_key to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bpf_prog_put to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bpf_prog_add to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bpf_master_redirect_enabled_key to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bpf_dispatcher_xdp_func to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol boot_cpu_data to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol blockdev_superblock to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol blk_status_to_errno to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol blk_start_plug to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol blk_stack_limits to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol blk_queue_rq_timeout to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol blk_mq_unique_tag to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol blk_mq_tagset_busy_iter to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol blk_mq_pci_map_queues to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol blk_mq_map_queues to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol blk_finish_plug to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol blkcg_get_fc_appid to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __blk_alloc_disk to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bitmap_zalloc to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __bitmap_xor to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __bitmap_weight to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __bitmap_subset to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __bitmap_set to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bitmap_print_to_pagebuf to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bitmap_parselist to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __bitmap_or to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __bitmap_intersects to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bitmap_from_arr32 to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bitmap_free to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bitmap_find_next_zero_area_off to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __bitmap_equal to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __bitmap_clear to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __bitmap_andnot to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __bitmap_and to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bioset_init to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bioset_exit to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bio_put to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bio_endio to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bio_clone_blkg_association to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bio_associate_blkg to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bio_alloc_clone to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bio_alloc_bioset to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _bin2bcd to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bdev_thaw to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bdev_freeze to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bdev_file_open_by_path to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol bdev_file_open_by_dev to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol auxiliary_driver_unregister to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __auxiliary_driver_register to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol auxiliary_device_init to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __auxiliary_device_add to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol autoremove_wake_function to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol atomic_notifier_chain_unregister to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol atomic_notifier_chain_register to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol _atomic_dec_and_lock to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol argv_split to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol argv_free to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol arch_touch_nmi_watchdog to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol alloc_workqueue to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __alloc_skb to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol alloc_pages_noprof to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol __alloc_pages_noprof to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol alloc_netdev_mqs to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol alloc_etherdev_mqs to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol alloc_cpu_rmap to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol alloc_cpumask_var_node to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol alloc_chrdev_region to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol add_wait_queue_exclusive to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol add_wait_queue to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol add_timer to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol acpi_get_table to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol acpi_disabled to stablelist (Čestmír Kalina) [RHEL-79881]
- kabi: add symbol abort_creds to stablelist (Čestmír Kalina) [RHEL-79881]

* Fri Mar 14 2025 Jan Stancek <jstancek@redhat.com> [6.12.0-55.6.1.el10_0]
- nfs: Fix oops in nfs_netfs_init_request() when copying to cache (Olga Kornievskaia) [RHEL-77295] {CVE-2024-57927}
- rhel_files: ensure all qdiscs are in modules-core (Davide Caratti) [RHEL-80112]
- wifi: mt76: mt7925: add handler to hif suspend/resume event (Jose Ignacio Tornos Martinez) [RHEL-79087]
- wifi: mt76: mt7925: fix CLC command timeout when suspend/resume (Jose Ignacio Tornos Martinez) [RHEL-79087]
- wifi: mt76: mt7925: fix the unfinished command of regd_notifier before suspend (Jose Ignacio Tornos Martinez) [RHEL-79087]
- configs: enable FW_CACHE on centos-stream/rhel 10 for nouveau (Dave Airlie) [RHEL-80281]

* Tue Mar 11 2025 Jan Stancek <jstancek@redhat.com> [6.12.0-55.5.1.el10_0]
- fs/proc: fix softlockup in __read_vmcore (part 2) (Baoquan He) [RHEL-79110] {CVE-2025-21694}
- phy: tegra: xusb: reset VBUS & ID OVERRIDE (Rupinderjit Singh) [RHEL-80387]
- kernel.spec: add missing tools-libs on s390x (Jan Stancek) [RHEL-81118]
- pps: Fix a use-after-free (Michal Schmidt) [RHEL-77270]

* Fri Mar 07 2025 Jan Stancek <jstancek@redhat.com> [6.12.0-55.4.1.el10_0]
- Bluetooth: btusb: Add new VID/PID 13d3/3628 for MT7925 (Bastien Nocera) [RHEL-79457]
- Bluetooth: btmtk: Fix failed to send func ctrl for MediaTek devices. (Bastien Nocera) [RHEL-79457]
- Bluetooth: btmtk: avoid UAF in btmtk_process_coredump (Bastien Nocera) [RHEL-79457] {CVE-2024-56653}
- Bluetooth: btmtk: adjust the position to init iso data anchor (Bastien Nocera) [RHEL-79457] {CVE-2024-53238}
- Bluetooth: btusb: mediatek: change the conditions for ISO interface (Bastien Nocera) [RHEL-79457]
- Bluetooth: btusb: mediatek: add intf release flow when usb disconnect (Bastien Nocera) [RHEL-79457] {CVE-2024-56757}
- Bluetooth: btusb: mediatek: add callback function in btusb_disconnect (Bastien Nocera) [RHEL-79457]
- Bluetooth: btusb: mediatek: move Bluetooth power off command position (Bastien Nocera) [RHEL-79457]
- redhat/configs: Enable Mediatek Bluetooth USB drivers (Bastien Nocera) [RHEL-79457]
- scsi: qla2xxx: Fix use after free on unload (Ewan D. Milne) [RHEL-76090] {CVE-2024-56623}
- scsi: sg: Fix slab-use-after-free read in sg_release() (Ewan D. Milne) [RHEL-76089] {CVE-2024-56631}
- CVE-2025-1272: security: Re-enable lockdown LSM in some setup_arch() (Lenny Szubowicz) [RHEL-78975] {CVE-2025-1272}

* Thu Mar 06 2025 Jan Stancek <jstancek@redhat.com> [6.12.0-55.3.1.el10_0]
- RDMA/mlx5: Fix a WARN during dereg_mr for DM type (Benjamin Poirier) [RHEL-41204]
- arm64: mm: Fix zone_dma_limit calculation (Luiz Capitulino) [RHEL-71568]
- uki: enable FIPS mode (Vitaly Kuznetsov) [RHEL-80149]

* Mon Mar 03 2025 Jan Stancek <jstancek@redhat.com> [6.12.0-55.2.1.el10_0]
- Documentation/powerpc/fadump: add additional parameter feature details (Mamatha Inamdar) [RHEL-70827]
- powerpc: increase MIN RMA size for CAS negotiation (Mamatha Inamdar) [RHEL-70827]
- powerpc/fadump: fix additional param memory reservation for HASH MMU (Mamatha Inamdar) [RHEL-70827]
- powerpc: export MIN RMA size (Mamatha Inamdar) [RHEL-70827]
- scsi: mpi3mr: Update driver version to 8.12.1.0.50 (Chandrakanth Patil) [RHEL-30789]
- scsi: mpi3mr: Synchronous access b/w reset and tm thread for reply queue (Chandrakanth Patil) [RHEL-30789]
- scsi: mpi3mr: Avoid reply queue full condition (Chandrakanth Patil) [RHEL-30789]
- scsi: mpi3mr: Fix possible crash when setting up bsg fails (Chandrakanth Patil) [RHEL-30789]
- scsi: mpi3mr: Handling of fault code for insufficient power (Chandrakanth Patil) [RHEL-30789]
- scsi: mpi3mr: Start controller indexing from 0 (Chandrakanth Patil) [RHEL-30789]
- scsi: mpi3mr: Fix corrupt config pages PHY state is switched in sysfs (Chandrakanth Patil) [RHEL-30789] {CVE-2024-57804}
- scsi: mpi3mr: Synchronize access to ioctl data buffer (Chandrakanth Patil) [RHEL-30789]
- redhat: regenerate self-test data for new RHDISTGIT_BRANCH (Patrick Talbert)

* Thu Feb 27 2025 Jan Stancek <jstancek@redhat.com> [6.12.0-55.1.1.el10_0]
- redhat: adjust rhel branch name (Jan Stancek)
- redhat: set defaults for RHEL 10.0 (Jan Stancek)
- Revert "x86/kvm: Override default caching mode for SEV-SNP and TDX" (Vitaly Kuznetsov) [RHEL-76109]

* Sun Feb 16 2025 Jan Stancek <jstancek@redhat.com> [6.12.0-55.el10]
- ovl: support encoding fid from inode with no alias (Miklos Szeredi) [RHEL-77301] {CVE-2025-21654}
- ovl: pass realinode to ovl_encode_real_fh() instead of realdentry (Miklos Szeredi) [RHEL-77301] {CVE-2025-21654}
- pmdomain: imx8mp-blk-ctrl: add missing loop break condition (CKI Backport Bot) [RHEL-77240] {CVE-2025-21668}
- io_uring/rsrc: require cloned buffers to share accounting contexts (Jeff Moyer) [RHEL-78677] {CVE-2025-21686}
- vsock: prevent null-ptr-deref in vsock_*[has_data|has_space] (CKI Backport Bot) [RHEL-77214] {CVE-2025-21666}
- USB: serial: quatech2: fix null-ptr-deref in qt2_process_read_urb() (CKI Backport Bot) [RHEL-78685] {CVE-2025-21689}
- lazy tlb: fix hotplug exit race with MMU_LAZY_TLB_SHOOTDOWN (Herton R. Krzesinski) [RHEL-58817]

* Fri Feb 14 2025 Jan Stancek <jstancek@redhat.com> [6.12.0-54.el10]
- mm/mempolicy: fix migrate_to_node() assuming there is at least one VMA in a MM (CKI Backport Bot) [RHEL-76120] {CVE-2024-56611}
- Revert "redhat: gating.yaml: drop unstable test" (Jan Stancek)
- nvme: remove multipath module parameter (Bryan Gurney) [RHEL-78133]
- NFSD: Fix CB_GETATTR status fix (Olga Kornievskaia) [RHEL-56888]
- irqchip/gic-v3-its: Don't enable interrupts in its_irq_set_vcpu_affinity() (CKI Backport Bot) [RHEL-78517] {CVE-2024-57949}
- erofs: promote to full support (Ian Kent) [RHEL-78322]
- rxrpc, afs: Fix peer hash locking vs RCU callback (Marc Dionne) [RHEL-78388]
- afs: Fix cleanup of immediately failed async calls (Marc Dionne) [RHEL-78388]
- afs: Fix directory format encoding struct (Marc Dionne) [RHEL-78388]
- afs: Fix EEXIST error returned from afs_rmdir() to be ENOTEMPTY (Marc Dionne) [RHEL-78388]
- afs: Fix the fallback handling for the YFS.RemoveFile2 RPC call (Marc Dionne) [RHEL-78388]
- rxrpc: Improve setsockopt() handling of malformed user input (Marc Dionne) [RHEL-78388]
- afs: Fix merge preference rule failure condition (Marc Dionne) [RHEL-78388]
- afs: Fix the maximum cell name length (Marc Dionne) [RHEL-78388]
- smb: client: get rid of kstrdup() in get_ses_refpath() (Paulo Alcantara) [RHEL-78152]
- smb: client: fix noisy when tree connecting to DFS interlink targets (Paulo Alcantara) [RHEL-78152]
- smb: client: don't trust DFSREF_STORAGE_SERVER bit (Paulo Alcantara) [RHEL-78152]
- smb: client: handle lack of EA support in smb2_query_path_info() (Paulo Alcantara) [RHEL-78152]
- smb: client: don't check for @leaf_fullpath in match_server() (Paulo Alcantara) [RHEL-78152]
- smb: client: get rid of TCP_Server_Info::refpath_lock (Paulo Alcantara) [RHEL-78152]
- cifs: Use cifs_autodisable_serverino() for disabling CIFS_MOUNT_SERVER_INUM in readdir.c (Paulo Alcantara) [RHEL-78152]
- smb3: add missing tracepoint for querying wsl EAs (Paulo Alcantara) [RHEL-78152]
- smb: client: fix order of arguments of tracepoints (Paulo Alcantara) [RHEL-78152]
- smb: client: fix oops due to unset link speed (Paulo Alcantara) [RHEL-78152]
- smb: client: correctly handle ErrorContextData as a flexible array (Paulo Alcantara) [RHEL-78152]
- smb: client: don't retry DFS targets on server shutdown (Paulo Alcantara) [RHEL-78152]
- smb: client: fix return value of parse_dfs_referrals() (Paulo Alcantara) [RHEL-78152]
- smb: client: optimize referral walk on failed link targets (Paulo Alcantara) [RHEL-78152]
- smb: client: provide dns_resolve_{unc,name} helpers (Paulo Alcantara) [RHEL-78152]
- smb: client: parse DNS domain name from domain= option (Paulo Alcantara) [RHEL-78152]
- smb: client: fix DFS mount against old servers with NTLMSSP (Paulo Alcantara) [RHEL-78152]
- smb: client: parse av pair type 4 in CHALLENGE_MESSAGE (Paulo Alcantara) [RHEL-78152]
- smb: client: introduce av_for_each_entry() helper (Paulo Alcantara) [RHEL-78152]
- cifs: support reconnect with alternate password for SMB1 (Paulo Alcantara) [RHEL-78152]
- smb: client: sync the root session and superblock context passwords before automounting (Paulo Alcantara) [RHEL-78152]
- cifs: Remove unused is_server_using_iface() (Paulo Alcantara) [RHEL-78152]
- smb: enable reuse of deferred file handles for write operations (Paulo Alcantara) [RHEL-78152]
- smb: fix bytes written value in /proc/fs/cifs/Stats (Paulo Alcantara) [RHEL-78152]
- smb: client: fix TCP timers deadlock after rmmod (Paulo Alcantara) [RHEL-78152] {CVE-2024-54680}
- smb: client: Deduplicate "select NETFS_SUPPORT" in Kconfig (Paulo Alcantara) [RHEL-78152]
- smb: use macros instead of constants for leasekey size and default cifsattrs value (Paulo Alcantara) [RHEL-78152]
- smb: client: destroy cfid_put_wq on module exit (Paulo Alcantara) [RHEL-78152]
- cifs: Use str_yes_no() helper in cifs_ses_add_channel() (Paulo Alcantara) [RHEL-78152]
- cifs: Fix rmdir failure due to ongoing I/O on deleted file (Paulo Alcantara) [RHEL-78152]
- smb3: fix compiler warning in reparse code (Paulo Alcantara) [RHEL-78152]
- smb: client: fix potential race in cifs_put_tcon() (Paulo Alcantara) [RHEL-78152]
- smb3.1.1: fix posix mounts to older servers (Paulo Alcantara) [RHEL-78152]
- fs/smb/client: cifs_prime_dcache() for SMB3 POSIX reparse points (Paulo Alcantara) [RHEL-78152]
- fs/smb/client: Implement new SMB3 POSIX type (Paulo Alcantara) [RHEL-78152]
- fs/smb/client: avoid querying SMB2_OP_QUERY_WSL_EA for SMB3 POSIX (Paulo Alcantara) [RHEL-78152]
- cifs: unlock on error in smb3_reconfigure() (Paulo Alcantara) [RHEL-78152]
- cifs: during remount, make sure passwords are in sync (Paulo Alcantara) [RHEL-78152]
- cifs: support mounting with alternate password to allow password rotation (Paulo Alcantara) [RHEL-78152]
- smb: Initialize cfid->tcon before performing network ops (Paulo Alcantara) [RHEL-78152] {CVE-2024-56729}
- smb: During unmount, ensure all cached dir instances drop their dentry (Paulo Alcantara) [RHEL-78152] {CVE-2024-53176}
- smb: client: fix noisy message when mounting shares (Paulo Alcantara) [RHEL-78152]
- smb: client: don't try following DFS links in cifs_tree_connect() (Paulo Alcantara) [RHEL-78152]
- smb: client: allow reconnect when sending ioctl (Paulo Alcantara) [RHEL-78152]
- smb: client: get rid of @nlsc param in cifs_tree_connect() (Paulo Alcantara) [RHEL-78152]
- smb: client: allow more DFS referrals to be cached (Paulo Alcantara) [RHEL-78152]
- cifs: Fix parsing reparse point with native symlink in SMB1 non-UNICODE session (Paulo Alcantara) [RHEL-78152]
- cifs: Validate content of WSL reparse point buffers (Paulo Alcantara) [RHEL-78152]
- cifs: Improve guard for excluding $LXDEV xattr (Paulo Alcantara) [RHEL-78152]
- cifs: Add support for parsing WSL-style symlinks (Paulo Alcantara) [RHEL-78152]
- cifs: Validate content of native symlink (Paulo Alcantara) [RHEL-78152]
- cifs: Fix parsing native symlinks relative to the export (Paulo Alcantara) [RHEL-78152]
- Update misleading comment in cifs_chan_update_iface (Paulo Alcantara) [RHEL-78152]
- smb: client: change return value in open_cached_dir_by_dentry() if !cfids (Paulo Alcantara) [RHEL-78152]
- smb: client: disable directory caching when dir_cache_timeout is zero (Paulo Alcantara) [RHEL-78152]
- smb: client: remove unnecessary checks in open_cached_dir() (Paulo Alcantara) [RHEL-78152]
- smb: prevent use-after-free due to open_cached_dir error paths (Paulo Alcantara) [RHEL-78152] {CVE-2024-53177}
- smb: Don't leak cfid when reconnect races with open_cached_dir (Paulo Alcantara) [RHEL-78152] {CVE-2024-53178}
- smb: client: handle max length for SMB symlinks (Paulo Alcantara) [RHEL-78152]
- smb: client: get rid of bounds check in SMB2_ioctl_init() (Paulo Alcantara) [RHEL-78152]
- smb: client: improve compound padding in encryption (Paulo Alcantara) [RHEL-78152]
- smb3: request handle caching when caching directories (Paulo Alcantara) [RHEL-78152]
- cifs: Recognize SFU char/block devices created by Windows NFS server on Windows Server <<2012 (Paulo Alcantara) [RHEL-78152]
- CIFS: New mount option for cifs.upcall namespace resolution (Paulo Alcantara) [RHEL-78152]
- smb/client: Prevent error pointer dereference (Paulo Alcantara) [RHEL-78152]
- fs/smb/client: implement chmod() for SMB3 POSIX Extensions (Paulo Alcantara) [RHEL-78152]
- smb: cached directories can be more than root file handle (Paulo Alcantara) [RHEL-78152]
- smb: client: Use str_yes_no() helper function (Paulo Alcantara) [RHEL-78152]
- smb: client: memcpy() with surrounding object base address (Paulo Alcantara) [RHEL-78152]
- cifs: Remove pre-historic unused CIFSSMBCopy (Paulo Alcantara) [RHEL-78152]
- bpf: tcp: Mark bpf_load_hdr_opt() arg2 as read-write (Viktor Malik) [RHEL-78209]
- clocksource: Use migrate_disable() to avoid calling get_random_u32() in atomic context (Waiman Long) [RHEL-77959]
- clocksource: Use pr_info() for "Checking clocksource synchronization" message (Waiman Long) [RHEL-77959]
- kasan: make kasan_record_aux_stack_noalloc() the default behaviour (Waiman Long) [RHEL-71050]
- workqueue: Do not warn when cancelling WQ_MEM_RECLAIM work from !WQ_MEM_RECLAIM worker (Waiman Long) [RHEL-74109] {CVE-2024-57888}
- smb: client: fix double free of TCP_Server_Info::hostname (CKI Backport Bot) [RHEL-77236] {CVE-2025-21673}
- arm64: Force CONFIG_ARCH_FORCE_MAX_ORDER of 4k kernel to 12 (Waiman Long) [RHEL-67530]
- Enable CONFIG_INTEL_MEI_PXP and CONFIG_DRM_I915_PXP on rhel (David Arcari) [RHEL-77048]
- KVM: nVMX: fix canonical check of vmcs12 HOST_RIP (Maxim Levitsky) [RHEL-44575]
- KVM: x86: model canonical checks more precisely (Maxim Levitsky) [RHEL-44575]
- KVM: x86: Add X86EMUL_F_MSR and X86EMUL_F_DT_LOAD to aid canonical checks (Maxim Levitsky) [RHEL-44575]
- KVM: x86: Route non-canonical checks in emulator through emulate_ops (Maxim Levitsky) [RHEL-44575]
- KVM: x86: drop x86.h include from cpuid.h (Maxim Levitsky) [RHEL-44575]
- ext4: force disable fscrypt feature (Brian Foster) [RHEL-64637]
- x86: KVM: Advertise CPUIDs for new instructions in Clearwater Forest (Paolo Bonzini) [RHEL-45114]
- iommufd: Fix struct iommu_hwpt_pgfault init and padding (Eder Zulian) [RHEL-75944]
- iommufd/fault: Use a separate spinlock to protect fault->deliver list (Eder Zulian) [RHEL-75944]
- iommufd/fault: Destroy response and mutex in iommufd_fault_destroy() (Eder Zulian) [RHEL-75944]
- iommufd/iova_bitmap: Fix shift-out-of-bounds in iova_bitmap_offset_to_index() (Eder Zulian) [RHEL-75944]
- iommu: iommufd: fix WARNING in iommufd_device_unbind (Eder Zulian) [RHEL-75944]
- smb: client: fix use-after-free of signing key (CKI Backport Bot) [RHEL-76126] {CVE-2024-53179}
- smb: client: fix NULL ptr deref in crypto_aead_setkey() (CKI Backport Bot) [RHEL-76124] {CVE-2024-53185}
- redhat: kernel.spec: add ynl to kernel-tools (Jan Stancek) [RHEL-63081]
- tools/net/ynl: ethtool: support spec load from install location (Jan Stancek) [RHEL-63081]
- tools/net/ynl: add support for --family and --list-families (Jan Stancek) [RHEL-63081]
- tools: ynl: add main install target (Jan Stancek) [RHEL-63081]
- tools: ynl: add install target for generated content (Jan Stancek) [RHEL-63081]
- tools: ynl: add initial pyproject.toml for packaging (Jan Stancek) [RHEL-63081]
- tools: ynl: move python code to separate sub-directory (Jan Stancek) [RHEL-63081]

* Tue Feb 11 2025 Jan Stancek <jstancek@redhat.com> [6.12.0-53.el10]
- libperf cpumap: Grow array of read CPUs in smaller increments (Michael Petlan) [RHEL-73893]
- libperf cpumap: Remove perf_cpu_map__read() (Michael Petlan) [RHEL-73893]
- libperf cpumap: Remove use of perf_cpu_map__read() (Michael Petlan) [RHEL-73893]
- perf pmu: Remove use of perf_cpu_map__read() (Michael Petlan) [RHEL-73893]
- libperf cpumap: Be tolerant of newline at the end of a cpumask (Michael Petlan) [RHEL-73893]
- libperf cpumap: Hide/reduce scope of MAX_NR_CPUS (Michael Petlan) [RHEL-73893]
- perf cpumap: Reduce transitive dependencies on libperf MAX_NR_CPUS (Michael Petlan) [RHEL-73893]
- perf: Increase MAX_NR_CPUS to 4096 (Michael Petlan) [RHEL-73893]
- redhat/configs: disable CONFIG_AF_UNIX_OOB on RHEL (Davide Caratti) [RHEL-76804]
- af_unix: Add a prompt to CONFIG_AF_UNIX_OOB (Davide Caratti) [RHEL-76804]
- KVM: x86: Cache CPUID.0xD XSTATE offsets+sizes during module init (Maxim Levitsky) [RHEL-71725]
- KVM: x86: Short-circuit all of kvm_apic_set_base() if MSR value is unchanged (Maxim Levitsky) [RHEL-71725]
- KVM: x86: Unpack msr_data structure prior to calling kvm_apic_set_base() (Maxim Levitsky) [RHEL-71725]
- KVM: x86: Make kvm_recalculate_apic_map() local to lapic.c (Maxim Levitsky) [RHEL-71725]
- KVM: x86: Rename APIC base setters to better capture their relationship (Maxim Levitsky) [RHEL-71725]
- KVM: x86: Move kvm_set_apic_base() implementation to lapic.c (from x86.c) (Maxim Levitsky) [RHEL-71725]
- KVM: x86: Inline kvm_get_apic_mode() in lapic.h (Maxim Levitsky) [RHEL-71725]
- KVM: x86: Get vcpu->arch.apic_base directly and drop kvm_get_apic_base() (Maxim Levitsky) [RHEL-71725]
- KVM: x86: Drop superfluous kvm_lapic_set_base() call when setting APIC state (Maxim Levitsky) [RHEL-71725]
- KVM: x86: Short-circuit all kvm_lapic_set_base() if MSR value isn't changing (Maxim Levitsky) [RHEL-71725]
- KVM: x86: Use '0' for guest RIP if PMI encounters protected guest state (Maxim Levitsky) [RHEL-71725]
- KVM: x86: Add lockdep-guarded asserts on register cache usage (Maxim Levitsky) [RHEL-71725]
- KVM: x86: Bypass register cache when querying CPL from kvm_sched_out() (Maxim Levitsky) [RHEL-71725]
- KVM: x86: Ensure vcpu->mode is loaded from memory in kvm_vcpu_exit_request() (Maxim Levitsky) [RHEL-71725]
- KVM: Allow calling kvm_release_page_{clean,dirty}() on a NULL page pointer (Maxim Levitsky) [RHEL-71725]
- KVM: Drop KVM_ERR_PTR_BAD_PAGE and instead return NULL to indicate an error (Maxim Levitsky) [RHEL-71725]
- perf/x86/intel: Add Arrow Lake U support (Michael Petlan) [RHEL-33308]
- wifi: ath12k: fix crash when unbinding (Jose Ignacio Tornos Martinez) [RHEL-70414]
- wifi: ath12k: fix warning when unbinding (Jose Ignacio Tornos Martinez) [RHEL-70414]
- nvmet: Don't overflow subsysnqn (Maurizio Lombardi) [RHEL-74084] {CVE-2024-53681}
- hugetlb: prioritize surplus allocation from current node (Aristeu Rozanski) [RHEL-74490]
- mm/vmscan: accumulate nr_demoted for accurate demotion statistics (Herton R. Krzesinski) [RHEL-71335]
- mm: vmscan : pgdemote vmstat is not getting updated when MGLRU is enabled. (Herton R. Krzesinski) [RHEL-71335]

* Sun Feb 09 2025 Jan Stancek <jstancek@redhat.com> [6.12.0-52.el10]
- x86/tdx: Enable CPU topology enumeration (Vitaly Kuznetsov) [RHEL-29350]
- x86/tdx: Dynamically disable SEPT violations from causing #VEs (Vitaly Kuznetsov) [RHEL-29350]
- x86/tdx: Rename tdx_parse_tdinfo() to tdx_setup() (Vitaly Kuznetsov) [RHEL-29350]
- x86/tdx: Introduce wrappers to read and write TD metadata (Vitaly Kuznetsov) [RHEL-29350]
- net/sctp: Prevent autoclose integer overflow in sctp_association_init() (Xin Long) [RHEL-75624] {CVE-2024-57938}
- tools: ynl: extend CFLAGS to keep options from environment (Hangbin Liu) [RHEL-50389]
- tools: ynl: add script dir to sys.path (Hangbin Liu) [RHEL-50389]
- ALSA: change configuration CONFIG_SND_HDA_SCODEC_TAS2781_SPI (Jaroslav Kysela) [RHEL-76330]
- ALSA: hda/realtek: fixup ASUS H7606W (Jaroslav Kysela) [RHEL-76330]
- ALSA: hda/realtek: fixup ASUS GA605W (Jaroslav Kysela) [RHEL-76330]
- ALSA: hda/realtek: Add support for Ayaneo System using CS35L41 HDA (Jaroslav Kysela) [RHEL-76330]
- ASoC: mediatek: disable buffer pre-allocation (Jaroslav Kysela) [RHEL-76330]
- ASoC: rt722: add delay time to wait for the calibration procedure (Jaroslav Kysela) [RHEL-76330]
- ALSA: hda: tas2781-spi: Delete some dead code (Jaroslav Kysela) [RHEL-76330]
- ALSA: hda: tas2781-spi: Fix bogus error handling in tas2781_hda_spi_probe() (Jaroslav Kysela) [RHEL-76330]
- ALSA: hda: tas2781-spi: Fix error code in tas2781_read_acpi() (Jaroslav Kysela) [RHEL-76330]
- ALSA: hda: tas2781-spi: Fix -Wsometimes-uninitialized in tasdevice_spi_switch_book() (Jaroslav Kysela) [RHEL-76330]
- ALSA: hda: tas2781-spi: select CRC32 instead of CRC32_SARWATE (Jaroslav Kysela) [RHEL-76330]
- ALSA: hda/tas2781: Add tas2781 hda SPI driver (Jaroslav Kysela) [RHEL-76330]
- ASoC: Intel: sof_sdw: Fix DMI match for Lenovo 83JX, 83MC and 83NM (Jaroslav Kysela) [RHEL-76330]
- ASoC: Intel: sof_sdw: Fix DMI match for Lenovo 83LC (Jaroslav Kysela) [RHEL-76330]
- Enable DRM_XE related kconfig options (Mika Penttilä) [RHEL-54134]
- wifi: nl80211: fix NL80211_ATTR_MLO_LINK_ID off-by-one (CKI Backport Bot) [RHEL-76137] {CVE-2024-56663}
- wifi: cfg80211: clear link ID from bitmap during link delete after clean up (Jose Ignacio Tornos Martinez) [RHEL-73819 RHEL-74091] {CVE-2024-57898}
- net: ieee802154: do not leave a dangling sk pointer in ieee802154_create() (Jose Ignacio Tornos Martinez) [RHEL-73819 RHEL-74052] {CVE-2024-56602}
- wifi: rtw89: coex: initialize local .dbcc_2g_phy in _set_btg_ctrl() (Jose Ignacio Tornos Martinez) [RHEL-73819]
- wifi: mac80211: wake the queues in case of failure in resume (Jose Ignacio Tornos Martinez) [RHEL-73819]
- wifi: rtw89: check return value of ieee80211_probereq_get() for RNR (Jose Ignacio Tornos Martinez) [RHEL-73819 RHEL-74044] {CVE-2024-48873}
- wifi: rtlwifi: Drastically reduce the attempts to read efuse in case of failures (Jose Ignacio Tornos Martinez) [RHEL-73819 RHEL-74051] {CVE-2024-53190}
- wifi: ath9k: add range check for conn_rsp_epid in htc_connect_service() (Jose Ignacio Tornos Martinez) [RHEL-73819 RHEL-74050] {CVE-2024-53156}
- wifi: iwlwifi: fix CRF name for Bz (Jose Ignacio Tornos Martinez) [RHEL-73819]
- wifi: cfg80211: sme: init n_channels before channels[] access (Jose Ignacio Tornos Martinez) [RHEL-73819]
- wifi: mac80211: init cnt before accessing elem in ieee80211_copy_mbssid_beacon (Jose Ignacio Tornos Martinez) [RHEL-73819]
- wifi: mac80211: fix a queue stall in certain cases of CSA (Jose Ignacio Tornos Martinez) [RHEL-73819]
- wifi: mac80211: fix station NSS capability initialization order (Jose Ignacio Tornos Martinez) [RHEL-73819]
- wifi: cfg80211: tests: Fix potential NULL dereference in test_cfg80211_parse_colocated_ap() (Jose Ignacio Tornos Martinez) [RHEL-73819]
- wifi: rtlwifi: rtl8821ae: phy: restore removed code to fix infinite loop (Jose Ignacio Tornos Martinez) [RHEL-73819]
- wifi: cfg80211: Remove the Medium Synchronization Delay validity check (Jose Ignacio Tornos Martinez) [RHEL-73819]
- wifi: rtw89: coex: check NULL return of kmalloc in btc_fw_set_monreg() (Jose Ignacio Tornos Martinez) [RHEL-73819 RHEL-74048] {CVE-2024-56535}
- wifi: nl80211: fix bounds checker error in nl80211_parse_sched_scan (Jose Ignacio Tornos Martinez) [RHEL-73819]
- wifi: iwlwifi: mvm: tell iwlmei when we finished suspending (Jose Ignacio Tornos Martinez) [RHEL-73819]
- wifi: iwlwifi: allow fast resume on ax200 (Jose Ignacio Tornos Martinez) [RHEL-73819]
- wifi: rtw89: Fix TX fail with A2DP after scanning (Jose Ignacio Tornos Martinez) [RHEL-73819]
- wifi: ath12k: remove msdu_end structure for WCN7850 (Jose Ignacio Tornos Martinez) [RHEL-73819]
- bus: mhi: host: Switch trace_mhi_gen_tre fields to native endian (Jose Ignacio Tornos Martinez) [RHEL-73819]
- wifi: ath12k: fix one more memcpy size error (Jose Ignacio Tornos Martinez) [RHEL-73819]
- wifi: ath12k: fix use-after-free in ath12k_dp_cc_cleanup() (Jose Ignacio Tornos Martinez) [RHEL-73819]
- wifi: rtl8xxxu: Perform update_beacon_work when beaconing is enabled (Jose Ignacio Tornos Martinez) [RHEL-73819]
- wifi: ath11k: Fix CE offset address calculation for WCN6750 in SSR (Jose Ignacio Tornos Martinez) [RHEL-73819]
- wifi: mwifiex: add missing locking for cfg80211 calls (Jose Ignacio Tornos Martinez) [RHEL-73819]
- wifi: cfg80211: check radio iface combination for multi radio per wiphy (Jose Ignacio Tornos Martinez) [RHEL-73819]
- wifi: ath12k: Skip Rx TID cleanup for self peer (Jose Ignacio Tornos Martinez) [RHEL-73819]
- wifi: iwlwifi: mvm: Fix __counted_by usage in cfg80211_wowlan_nd_* (Jose Ignacio Tornos Martinez) [RHEL-73819]
- idpf: trigger SW interrupt when exiting wb_on_itr mode (Michal Schmidt) [RHEL-29554]
- idpf: add support for SW triggered interrupts (Michal Schmidt) [RHEL-29554]
- idpf: set completion tag for "empty" bufs associated with a packet (Michal Schmidt) [RHEL-29554]
- idpf: Don't hard code napi_struct size (Michal Schmidt) [RHEL-29554]
- perf trace: Keep exited threads for summary (Michael Petlan) [RHEL-62340]
- block: Prevent potential deadlocks in zone write plug error recovery (Ming Lei) [RHEL-71495]
- dm: Fix dm-zoned-reclaim zone write pointer alignment (Ming Lei) [RHEL-71495]
- block: Ignore REQ_NOWAIT for zone reset and zone finish operations (Ming Lei) [RHEL-71495]
- block: Use a zone write plug BIO work for REQ_NOWAIT BIOs (Ming Lei) [RHEL-71495]
- block: Prevent potential deadlock in blk_revalidate_disk_zones() (Ming Lei) [RHEL-71495]
- block: Switch to using refcount_t for zone write plugs (Ming Lei) [RHEL-71495]
- block: Add a public bdev_zone_is_seq() helper (Ming Lei) [RHEL-71495]
- block: RCU protect disk->conv_zones_bitmap (Ming Lei) [RHEL-71495]
- redhat/configs: coresight: Clean up coresight configs (Mark Salter) [RHEL-78271]

* Fri Feb 07 2025 Jan Stancek <jstancek@redhat.com> [6.12.0-51.el10]
- redhat: fix build/install targets in netfilter kselftest (Hangbin Liu) [RHEL-58105]
- selftests: net/{lib,openvswitch}: extend CFLAGS to keep options from environment (Hangbin Liu) [RHEL-58105]
- selftests: mptcp: extend CFLAGS to keep options from environment (Hangbin Liu) [RHEL-58105]
- fs/nfs: fix missing declaration of nfs_idmap_cache_timeout (Olga Kornievskaia) [RHEL-74415]
- NFS/pnfs: Fix a live lock between recalled layouts and layoutget (Olga Kornievskaia) [RHEL-74415]
- nfsd: restore callback functionality for NFSv4.0 (Olga Kornievskaia) [RHEL-74415]
- NFSD: fix management of pending async copies (Olga Kornievskaia) [RHEL-74415]
- nfsd: Revert "nfsd: release svc_expkey/svc_export with rcu_work" (Olga Kornievskaia) [RHEL-74415]
- fs/nfs/io: make nfs_start_io_*() killable (Olga Kornievskaia) [RHEL-74415]
- nfs/blocklayout: Limit repeat device registration on failure (Olga Kornievskaia) [RHEL-74415]
- nfs/blocklayout: Don't attempt unregister for invalid block device (Olga Kornievskaia) [RHEL-74415]
- sunrpc: fix one UAF issue caused by sunrpc kernel tcp socket (Olga Kornievskaia) [RHEL-74415]
- SUNRPC: timeout and cancel TLS handshake with -ETIMEDOUT (Olga Kornievskaia) [RHEL-74415]
- sunrpc: clear XPRT_SOCK_UPD_TIMEOUT when reset transport (Olga Kornievskaia) [RHEL-74415]
- nfs: ignore SB_RDONLY when mounting nfs (Olga Kornievskaia) [RHEL-74415]
- Revert "nfs: don't reuse partially completed requests in nfs_lock_and_join_requests" (Olga Kornievskaia) [RHEL-74415]
- Revert "fs: nfs: fix missing refcnt by replacing folio_set_private by folio_attach_private" (Olga Kornievskaia) [RHEL-74415]
- nfs/localio: must clear res.replen in nfs_local_read_done (Olga Kornievskaia) [RHEL-74415]
- NFSv4.0: Fix a use-after-free problem in the asynchronous open() (Olga Kornievskaia) [RHEL-74415]
- NFSv4.0: Fix the wake up of the next waiter in nfs_release_seqid() (Olga Kornievskaia) [RHEL-74415]
- SUNRPC: Fix a hang in TLS sock_close if sk_write_pending (Olga Kornievskaia) [RHEL-74415]
- sunrpc: remove newlines from tracepoints (Olga Kornievskaia) [RHEL-74415]
- nfs: Annotate struct pnfs_commit_array with __counted_by() (Olga Kornievskaia) [RHEL-74415]
- nfs/localio: eliminate need for nfs_local_fsync_work forward declaration (Olga Kornievskaia) [RHEL-74415]
- nfs/localio: remove extra indirect nfs_to call to check {read,write}_iter (Olga Kornievskaia) [RHEL-74415]
- nfs/localio: eliminate unnecessary kref in nfs_local_fsync_ctx (Olga Kornievskaia) [RHEL-74415]
- nfs/localio: remove redundant suid/sgid handling (Olga Kornievskaia) [RHEL-74415]
- NFS: Implement get_nfs_version() (Olga Kornievskaia) [RHEL-74415]
- NFS: Clean up find_nfs_version() (Olga Kornievskaia) [RHEL-74415]
- NFS: Rename get_nfs_version() -> find_nfs_version() (Olga Kornievskaia) [RHEL-74415]
- NFS: Convert the NFS module list into an array (Olga Kornievskaia) [RHEL-74415]
- NFS: Clean up locking the nfs_versions list (Olga Kornievskaia) [RHEL-74415]
- nfsd: allow for up to 32 callback session slots (Olga Kornievskaia) [RHEL-74415]
- nfs_common: must not hold RCU while calling nfsd_file_put_local (Olga Kornievskaia) [RHEL-74415]
- nfsd: get rid of include ../internal.h (Olga Kornievskaia) [RHEL-74415]
- nfsd: fix nfs4_openowner leak when concurrent nfsd4_open occur (Olga Kornievskaia) [RHEL-74415]
- NFSD: Add nfsd4_copy time-to-live (Olga Kornievskaia) [RHEL-74415]
- NFSD: Add a laundromat reaper for async copy state (Olga Kornievskaia) [RHEL-74415]
- NFSD: Block DESTROY_CLIENTID only when there are ongoing async COPY operations (Olga Kornievskaia) [RHEL-74415]
- NFSD: Handle an NFS4ERR_DELAY response to CB_OFFLOAD (Olga Kornievskaia) [RHEL-74415]
- NFSD: Free async copy information in nfsd4_cb_offload_release() (Olga Kornievskaia) [RHEL-74415]
- NFSD: Fix nfsd4_shutdown_copy() (Olga Kornievskaia) [RHEL-74415]
- NFSD: Add a tracepoint to record canceled async COPY operations (Olga Kornievskaia) [RHEL-74415]
- nfsd: make nfsd4_session->se_flags a bool (Olga Kornievskaia) [RHEL-74415]
- nfsd: remove nfsd4_session->se_bchannel (Olga Kornievskaia) [RHEL-74415]
- nfsd: make use of warning provided by refcount_t (Olga Kornievskaia) [RHEL-74415]
- nfsd: Don't fail OP_SETCLIENTID when there are too many clients. (Olga Kornievskaia) [RHEL-74415]
- svcrdma: fix miss destroy percpu_counter in svc_rdma_proc_init() (Olga Kornievskaia) [RHEL-74415]
- xdrgen: Remove program_stat_to_errno() call sites (Olga Kornievskaia) [RHEL-74415]
- xdrgen: Update the files included in client-side source code (Olga Kornievskaia) [RHEL-74415]
- xdrgen: Remove check for "nfs_ok" in C templates (Olga Kornievskaia) [RHEL-74415]
- xdrgen: Remove tracepoint call site (Olga Kornievskaia) [RHEL-74415]
- nfsd: release svc_expkey/svc_export with rcu_work (Olga Kornievskaia) [RHEL-74415]
- SUNRPC: make sure cache entry active before cache_show (Olga Kornievskaia) [RHEL-74415]
- nfsd: make sure exp active before svc_export_show (Olga Kornievskaia) [RHEL-74415]
- lockd: Remove unneeded initialization of file_lock::c.flc_flags (Olga Kornievskaia) [RHEL-74415]
- lockd: Remove unused parameter to nlmsvc_testlock() (Olga Kornievskaia) [RHEL-74415]
- lockd: Remove some snippets of unfinished code (Olga Kornievskaia) [RHEL-74415]
- lockd: Remove unnecessary memset() (Olga Kornievskaia) [RHEL-74415]
- lockd: Remove unused typedef (Olga Kornievskaia) [RHEL-74415]
- NFSD: Cap the number of bytes copied by nfs4_reset_recoverydir() (Olga Kornievskaia) [RHEL-74415]
- NFSD: Remove unused values from nfsd4_encode_components_esc() (Olga Kornievskaia) [RHEL-74415]
- NFSD: Remove unused results in nfsd4_encode_pathname4() (Olga Kornievskaia) [RHEL-74415]
- NFSD: Prevent NULL dereference in nfsd4_process_cb_update() (Olga Kornievskaia) [RHEL-74415]
- NFSD: Remove a never-true comparison (Olga Kornievskaia) [RHEL-74415]
- NFSD: Remove dead code in nfsd4_create_session() (Olga Kornievskaia) [RHEL-74415]
- nfsd: refine and rename NFSD_MAY_LOCK (Olga Kornievskaia) [RHEL-74415]
- NFSD: Replace use of NFSD_MAY_LOCK in nfsd4_lock() (Olga Kornievskaia) [RHEL-74415]
- nfsd: replace call_rcu by kfree_rcu for simple kmem_cache_free callback (Olga Kornievskaia) [RHEL-74415]
- xdrgen: Add a utility for extracting XDR from RFCs (Olga Kornievskaia) [RHEL-74415]
- nfsd: Fix NFSD_MAY_BYPASS_GSS and NFSD_MAY_BYPASS_GSS_ON_ROOT (Olga Kornievskaia) [RHEL-74415]
- nfsd: Fill NFSv4.1 server implementation fields in OP_EXCHANGE_ID response (Olga Kornievskaia) [RHEL-74415]
- lockd: Fix comment about NLMv3 backwards compatibility (Olga Kornievskaia) [RHEL-74415]
- nfsd: new tracepoint for after op_func in compound processing (Olga Kornievskaia) [RHEL-74415]
- nfsd: have nfsd4_deleg_getattr_conflict pass back write deleg pointer (Olga Kornievskaia) [RHEL-74415]
- nfsd: drop the nfsd4_fattr_args "size" field (Olga Kornievskaia) [RHEL-74415]
- nfsd: drop the ncf_cb_bmap field (Olga Kornievskaia) [RHEL-74415]
- nfsd: drop inode parameter from nfsd4_change_attribute() (Olga Kornievskaia) [RHEL-74415]
- xdrgen: emit maxsize macros (Olga Kornievskaia) [RHEL-74415]
- xdrgen: Add generator code for XDR width macros (Olga Kornievskaia) [RHEL-74415]
- xdrgen: XDR width for union types (Olga Kornievskaia) [RHEL-74415]
- xdrgen: XDR width for pointer types (Olga Kornievskaia) [RHEL-74415]
- xdrgen: XDR width for struct types (Olga Kornievskaia) [RHEL-74415]
- xdrgen: XDR width for typedef (Olga Kornievskaia) [RHEL-74415]
- xdrgen: XDR width for optional_data type (Olga Kornievskaia) [RHEL-74415]
- xdrgen: XDR width for variable-length array (Olga Kornievskaia) [RHEL-74415]
- xdrgen: XDR width for fixed-length array (Olga Kornievskaia) [RHEL-74415]
- xdrgen: XDR width for a string (Olga Kornievskaia) [RHEL-74415]
- xdrgen: XDR width for variable-length opaque (Olga Kornievskaia) [RHEL-74415]
- xdrgen: XDR width for fixed-length opaque (Olga Kornievskaia) [RHEL-74415]
- xdrgen: XDR widths for enum types (Olga Kornievskaia) [RHEL-74415]
- xdrgen: Keep track of on-the-wire data type widths (Olga Kornievskaia) [RHEL-74415]
- xdrgen: Track constant values (Olga Kornievskaia) [RHEL-74415]
- xdrgen: Refactor transformer arms (Olga Kornievskaia) [RHEL-74415]
- xdrgen: Implement big-endian enums (Olga Kornievskaia) [RHEL-74415]
- xdrgen: Rename "enum yada" types as just "yada" (Olga Kornievskaia) [RHEL-74415]
- xdrgen: Rename enum's declaration Jinja2 template (Olga Kornievskaia) [RHEL-74415]
- xdrgen: Rename "variable-length strings" (Olga Kornievskaia) [RHEL-74415]
- xdrgen: Clean up type_specifier (Olga Kornievskaia) [RHEL-74415]
- xdrgen: Exit status should be zero on success (Olga Kornievskaia) [RHEL-74415]
- NFSD: Remove unused function parameter (Olga Kornievskaia) [RHEL-74415]
- NFSD: Remove unnecessary posix_acl_entry pointer initialization (Olga Kornievskaia) [RHEL-74415]
- svcrdma: Address an integer overflow (Olga Kornievskaia) [RHEL-74415]
- NFSD: Prevent a potential integer overflow (Olga Kornievskaia) [RHEL-74415]
- rhel-10: gate on kernel-qe tests results not cki ones (Bruno Goncalves)
- exfat: fix the infinite loop in exfat_readdir() (CKI Backport Bot) [RHEL-75669] {CVE-2024-57940}
- exfat: fix the new buffer was not zeroed before writing (CKI Backport Bot) [RHEL-75662] {CVE-2024-57943}
- redhat/configs: Enable Intel Bluetooth PCIE drivers (Bastien Nocera) [RHEL-76105]
- Bluetooth: Use str_enable_disable-like helpers (Bastien Nocera) [RHEL-76105]
- Bluetooth: btintel_pcie: Replace deprecated PCI functions (Bastien Nocera) [RHEL-76105]
- Bluetooth: btintel_pcie: remove redundant assignment to variable ret (Bastien Nocera) [RHEL-76105]
- Bluetooth: btintel: Do no pass vendor events to stack (Bastien Nocera) [RHEL-76105]
- Bluetooth: btintel_pcie: Remove deadcode (Bastien Nocera) [RHEL-76105]
- Bluetooth: btintel: Add DSBR support for BlazarIW, BlazarU and GaP (Bastien Nocera) [RHEL-76105]
- Bluetooth: btintel_pcie: Add recovery mechanism (Bastien Nocera) [RHEL-76105]
- Bluetooth: btintel_pcie: Add handshake between driver and firmware (Bastien Nocera) [RHEL-76105]
- bluetooth: Fix typos in the comments (Bastien Nocera) [RHEL-76105]
- net: atlantic: use irq_update_affinity_hint() (CKI Backport Bot) [RHEL-77809]
- tipc: fix NULL deref in cleanup_bearer() (Xin Long) [RHEL-77768]
- tipc: Fix use-after-free of kernel socket in cleanup_bearer(). (CKI Backport Bot) [RHEL-77768] {CVE-2024-56642}
- perf test: Remove cpu-list BPF cgroup counter test (Michael Petlan) [RHEL-70687]
- tg3: Disable tg3 PCIe AER on system reboot (Lenny Szubowicz) [RHEL-33859]
- build:  remove localversion-rt from git tree (Clark Williams) [RHEL-73163]
- net: Fix icmp host relookup triggering ip_rt_bug (CKI Backport Bot) [RHEL-77765] {CVE-2024-56647}
- redhat/configs: Default to batched invalidation on s390 (Jerry Snitselaar) [RHEL-75486]
- redhat/configs: disable CONFIG_TCP_AO (Sabrina Dubroca) [RHEL-77608]

* Wed Feb 05 2025 Jan Stancek <jstancek@redhat.com> [6.12.0-50.el10]
- redhat: set aarch64 variants of kernel-rt as Tech Preview (Luis Claudio R. Goncalves) [RHEL-77120]
- rtla/timerlat_top: Set OSNOISE_WORKLOAD for kernel threads (Tomas Glozar) [RHEL-72808]
- rtla/timerlat_hist: Set OSNOISE_WORKLOAD for kernel threads (Tomas Glozar) [RHEL-72808]
- rtla/osnoise: Distinguish missing workload option (Tomas Glozar) [RHEL-72808]
- drm/ast: Fix ast_dp connection status (Jocelyn Falempe) [RHEL-73063]
- NFSD: add cb opcode to WARN_ONCE on failed callback (Olga Kornievskaia) [RHEL-56888]
- NFSD: fix decoding in nfs4_xdr_dec_cb_getattr (Olga Kornievskaia) [RHEL-56888]
- wifi: iwlwifi: bump FW API to 94 for BZ/SC devices (CKI Backport Bot) [RHEL-75880]
- bpf, sockmap: Fix race between element replace and close() (Felix Maurer) [RHEL-72484]
- xsk: Free skb when TX metadata options are invalid (Felix Maurer) [RHEL-72484]
- xsk: always clear DMA mapping information when unmapping the pool (Felix Maurer) [RHEL-72484]
- bpf: fix OOB devmap writes when deleting elements (Felix Maurer) [RHEL-72484]
- xsk: fix OOB map writes when deleting elements (Felix Maurer) [RHEL-72484]
- rtla: Report missed event count (Tomas Glozar) [RHEL-67557]
- rtla: Add function to report missed events (Tomas Glozar) [RHEL-67557]
- rtla: Count all processed events (Tomas Glozar) [RHEL-67557]
- rtla: Count missed trace events (Tomas Glozar) [RHEL-67557]
- tools/rtla: Add osnoise_trace_is_off() (Tomas Glozar) [RHEL-67557]
- rtla/timerlat_top: Abort event processing on second signal (Tomas Glozar) [RHEL-67557]
- rtla/timerlat_hist: Abort event processing on second signal (Tomas Glozar) [RHEL-67557]
- rtla/timerlat_top: Stop timerlat tracer on signal (Tomas Glozar) [RHEL-67557]
- rtla/timerlat_hist: Stop timerlat tracer on signal (Tomas Glozar) [RHEL-67557]
- rtla: Add trace_instance_stop (Tomas Glozar) [RHEL-67557]
- netlink: typographical error in nlmsg_type constants definition (CKI Backport Bot) [RHEL-76481]
- net: sched: refine software bypass handling in tc_run (Xin Long) [RHEL-56246]

* Tue Feb 04 2025 Jan Stancek <jstancek@redhat.com> [6.12.0-49.el10]
- Bluetooth: fix use-after-free in device_for_each_child() (CKI Backport Bot) [RHEL-76122] {CVE-2024-53237}
- redhat/spec: Install all selftests in a single step (Viktor Malik) [RHEL-70889]
- Bluetooth: hci_core: Fix not checking skb length on hci_acldata_packet (CKI Backport Bot) [RHEL-74009] {CVE-2024-56590}
- net: usb: lan78xx: Fix double free issue with interrupt buffer allocation (CKI Backport Bot) [RHEL-74053] {CVE-2024-53213}
- mm/slub: Avoid list corruption when removing a slab from the full list (Rafael Aquini) [RHEL-73368] {CVE-2024-56566}
- selinux: ignore unknown extended permissions (Ondrej Mosnacek) [RHEL-75632] {CVE-2024-57931}
- drm: adv7511: Fix use-after-free in adv7533_attach_dsi() (Jocelyn Falempe) [RHEL-74282]
- drm: adv7511: Drop dsi single lane support (Jocelyn Falempe) [RHEL-74282]
- drm/xe: Wait for migration job before unmapping pages (Jocelyn Falempe) [RHEL-74282]
- drm/xe: Use non-interruptible wait when moving BO to system (Jocelyn Falempe) [RHEL-74282]
- drm/amdkfd: Correct the migration DMA map direction (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu: use sjt mec fw on gfx943 for sriov (Jocelyn Falempe) [RHEL-74282]
- drm/i915/dg1: Fix power gate sequence. (Jocelyn Falempe) [RHEL-74282]
- drm/i915/cx0_phy: Fix C10 pll programming sequence (Jocelyn Falempe) [RHEL-74282]
- drm/xe: Fix fault on fd close after unbind (Jocelyn Falempe) [RHEL-74282]
- drm/xe/pf: Use correct function to check LMEM provisioning (Jocelyn Falempe) [RHEL-74282]
- drm/xe: Revert some changes that break a mesa debug tool (Jocelyn Falempe) [RHEL-74282]
- drm/bridge: adv7511_audio: Update Audio InfoFrame properly (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu: fix backport of commit 73dae652dcac (Jocelyn Falempe) [RHEL-74282]
- drm/xe: Move the coredump registration to the worker thread (Jocelyn Falempe) [RHEL-74282]
- drm/xe: Take PM ref in delayed snapshot capture worker (Jocelyn Falempe) [RHEL-74282]
- drm/dp_mst: Ensure mst_primary pointer is valid in drm_dp_mst_handle_up_req() (Jocelyn Falempe) [RHEL-74282]
- udmabuf: also check for F_SEAL_FUTURE_WRITE (Jocelyn Falempe) [RHEL-74282]
- udmabuf: fix racy memfd sealing check (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu/mmhub4.1: fix IP version check (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu/gfx12: fix IP version check (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu/nbio7.0: fix IP version check (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu/smu14.0.2: fix IP version check (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu/nbio7.7: fix IP version check (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu/nbio7.11: fix IP version check (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu: don't access invalid sched (Jocelyn Falempe) [RHEL-74282]
- i915/guc: Accumulate active runtime on gt reset (Jocelyn Falempe) [RHEL-74282]
- i915/guc: Ensure busyness counter increases motonically (Jocelyn Falempe) [RHEL-74282]
- i915/guc: Reset engine utilization buffer before registration (Jocelyn Falempe) [RHEL-74282]
- drm/panel: synaptics-r63353: Fix regulator unbalance (Jocelyn Falempe) [RHEL-74282]
- drm/panel: st7701: Add prepare_prev_first flag to drm_panel (Jocelyn Falempe) [RHEL-74282]
- drm/panel: novatek-nt35950: fix return value check in nt35950_probe() (Jocelyn Falempe) [RHEL-74282]
- drm/panel: himax-hx83102: Add a check to prevent NULL pointer dereference (Jocelyn Falempe) [RHEL-74282]
- dma-buf: Fix __dma_buf_debugfs_list_del argument for !CONFIG_DEBUG_FS (Jocelyn Falempe) [RHEL-74282]
- udmabuf: fix memory leak on last export_udmabuf() error path (Jocelyn Falempe) [RHEL-74282]
- udmabuf: udmabuf_create pin folio codestyle cleanup (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu: Handle NULL bo->tbo.resource (again) in amdgpu_vm_bo_update (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu: fix amdgpu_coredump (Jocelyn Falempe) [RHEL-74282]
- drm/modes: Avoid divide by zero harder in drm_mode_vrefresh() (Jocelyn Falempe) [RHEL-74282]
- drm/amd: Update strapping for NBIO 2.5.0 (Jocelyn Falempe) [RHEL-74282]
- drm/display: use ERR_PTR on DP tunnel manager creation fail (Jocelyn Falempe) [RHEL-74282]
- drm/xe/reg_sr: Remove register pool (Jocelyn Falempe) [RHEL-74282]
- drm/xe: fix the ERR_PTR() returned on failure to allocate tiny pt (Jocelyn Falempe) [RHEL-74282]
- amdgpu/uvd: get ring reference from rq scheduler (Jocelyn Falempe) [RHEL-74282]
- drm/amdkfd: hard-code MALL cacheline size for gfx11, gfx12 (Jocelyn Falempe) [RHEL-74282]
- drm/amdkfd: hard-code cacheline size for gfx11 (Jocelyn Falempe) [RHEL-74282]
- drm/amdkfd: Dereference null return value (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu: fix when the cleaner shader is emitted (Jocelyn Falempe) [RHEL-74282]
- drm/amd/pm: Set SMU v13.0.7 default workload type (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu: fix UVD contiguous CS mapping problem (Jocelyn Falempe) [RHEL-74282]
- drm/i915: Fix NULL pointer dereference in capture_engine (Jocelyn Falempe) [RHEL-74282]
- drm/i915/color: Stop using non-posted DSB writes for legacy LUT (Jocelyn Falempe) [RHEL-74282]
- drm/i915: Fix memory leak by correcting cache object name in error handler (Jocelyn Falempe) [RHEL-74282]
- drm/amdkfd: pause autosuspend when creating pdd (Jocelyn Falempe) [RHEL-74282]
- drm/xe: Call invalidation_fence_fini for PT inval fences in error state (Jocelyn Falempe) [RHEL-74282]
- drm/panic: remove spurious empty line to clean warning (Jocelyn Falempe) [RHEL-74282]
- Revert "drm/amd/display: parse umc_info or vram_info based on ASIC" (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu: rework resume handling for display (v2) (Jocelyn Falempe) [RHEL-74282]
- drm/amd/display: Add option to retrieve detile buffer size (Jocelyn Falempe) [RHEL-74282]
- drm/xe/devcoredump: Update handling of xe_force_wake_get return (Jocelyn Falempe) [RHEL-74282]
- drm/xe/forcewake: Add a helper xe_force_wake_ref_has_domain() (Jocelyn Falempe) [RHEL-74282]
- drm/xe/guc: Copy GuC log prior to dumping (Jocelyn Falempe) [RHEL-74282]
- drm/xe/devcoredump: Add ASCII85 dump helper function (Jocelyn Falempe) [RHEL-74282]
- drm/xe/devcoredump: Improve section headings and add tile info (Jocelyn Falempe) [RHEL-74282]
- drm/xe/devcoredump: Use drm_puts and already cached local variables (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu/vcn: reset fw_shared when VCPU buffers corrupted on vcn v4.0.3 (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu: set the right AMDGPU sg segment limitation (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu: skip amdgpu_device_cache_pci_state under sriov (Jocelyn Falempe) [RHEL-74282]
- drm/amd/display: Prune Invalid Modes For HDMI Output (Jocelyn Falempe) [RHEL-74282]
- drm/amd/display: parse umc_info or vram_info based on ASIC (Jocelyn Falempe) [RHEL-74282]
- drm/amd/display: Remove hw w/a toggle if on DP2/HPO (Jocelyn Falempe) [RHEL-74282]
- drm/panic: Add ABGR2101010 support (Jocelyn Falempe) [RHEL-74282]
- drm/amd/display: Fix underflow when playing 8K video in full screen mode (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu: refine error handling in amdgpu_ttm_tt_pin_userptr (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu: Dereference the ATCS ACPI buffer (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu: clear RB_OVERFLOW bit when enabling interrupts for vega20_ih (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu/gfx9: Add cleaner shader for GFX9.4.2 (Jocelyn Falempe) [RHEL-74282]
- drm/amd/display: Adding array index check to prevent memory corruption (Jocelyn Falempe) [RHEL-74282]
- drm/sched: memset() 'job' in drm_sched_job_init() (Jocelyn Falempe) [RHEL-74282]
- drm/panel: simple: Add Microchip AC69T88A LVDS Display panel (Jocelyn Falempe) [RHEL-74282]
- drm/xe/guc/ct: Flush g2h worker in case of g2h response timeout (Jocelyn Falempe) [RHEL-74282]
- drm/amd/display: Full exit out of IPS2 when all allow signals have been cleared (Jocelyn Falempe) [RHEL-74282]
- drm/display: Fix building with GCC 15 (Jocelyn Falempe) [RHEL-74282]
- drm/xe/xe3: Add initial set of workarounds (Jocelyn Falempe) [RHEL-74282]
- drm/xe/ptl: L3bank mask is not available on the media GT (Jocelyn Falempe) [RHEL-74282]
- drm/amd/display: disable SG displays on cyan skillfish (Jocelyn Falempe) [RHEL-74282]
- drm/amd/display: Fix garbage or black screen when resetting otg (Jocelyn Falempe) [RHEL-74282]
- drm/amd/display: skip disable CRTC in seemless bootup case (Jocelyn Falempe) [RHEL-74282]
- drm/radeon/r600_cs: Fix possible int overflow in r600_packet3_check() (Jocelyn Falempe) [RHEL-74282]
- drm/amd/display: Fix out-of-bounds access in 'dcn21_link_encoder_create' (Jocelyn Falempe) [RHEL-74282]
- drm/bridge: it6505: Enable module autoloading (Jocelyn Falempe) [RHEL-74282]
- drm: panel-orientation-quirks: Add quirk for AYA NEO GEEK (Jocelyn Falempe) [RHEL-74282]
- drm: panel-orientation-quirks: Add quirk for AYA NEO Founder edition (Jocelyn Falempe) [RHEL-74282]
- drm: panel-orientation-quirks: Add quirk for AYA NEO 2 model (Jocelyn Falempe) [RHEL-74282]
- drm/xe/pciid: Add new PCI id for ARL (Jocelyn Falempe) [RHEL-74282]
- drm/xe/pciids: Add PVC's PCI device ID macros (Jocelyn Falempe) [RHEL-74282]
- drm/xe/pciids: separate ARL and MTL PCI IDs (Jocelyn Falempe) [RHEL-74282]
- drm/xe/pciids: separate RPL-U and RPL-P PCI IDs (Jocelyn Falempe) [RHEL-74282]
- dma-fence: Use kernel's sort for merging fences (Jocelyn Falempe) [RHEL-74282]
- dma-fence: Fix reference leak on fence merge failure path (Jocelyn Falempe) [RHEL-74282]
- dma-buf: fix dma_fence_array_signaled v4 (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu/hdp5.2: do a posting read when flushing HDP (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu/hdp7.0: do a posting read when flushing HDP (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu/hdp5.0: do a posting read when flushing HDP (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu/hdp4.0: do a posting read when flushing HDP (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu/hdp6.0: do a posting read when flushing HDP (Jocelyn Falempe) [RHEL-74282]
- drm/amd/display: Add a left edge pixel if in YCbCr422 or YCbCr420 and odm (Jocelyn Falempe) [RHEL-74282]
- drm/amd/display: Limit VTotal range to max hw cap minus fp (Jocelyn Falempe) [RHEL-74282]
- drm/amd/display: Correct prefetch calculation (Jocelyn Falempe) [RHEL-74282]
- drm/dp_mst: Fix resetting msg rx state after topology removal (Jocelyn Falempe) [RHEL-74282]
- drm/dp_mst: Verify request type in the corresponding down message reply (Jocelyn Falempe) [RHEL-74282]
- drm/amd/pm: fix and simplify workload handling (Jocelyn Falempe) [RHEL-74282]
- drm/amdkfd: add MEC version that supports no PCIe atomics for GFX12 (Jocelyn Falempe) [RHEL-74282]
- drm/dp_mst: Fix MST sideband message body length check (Jocelyn Falempe) [RHEL-74282]
- drm/amdkfd: hard-code cacheline for gc943,gc944 (Jocelyn Falempe) [RHEL-74282]
- drm/amd/display: Ignore scalar validation failure if pipe is phantom (Jocelyn Falempe) [RHEL-74282]
- drm/amd/display: calculate final viewport before TAP optimization (Jocelyn Falempe) [RHEL-74282]
- Revert "drm/xe/xe_guc_ads: save/restore OA registers and allowlist regs" (Jocelyn Falempe) [RHEL-74282]
- drm/amd/display: Remove PIPE_DTO_SRC_SEL programming from set_dtbclk_dto (Jocelyn Falempe) [RHEL-74282]
- drm/amd/display: update pipe selection policy to check head pipe (Jocelyn Falempe) [RHEL-74282]
- drm/amd/display: Fix handling of plane refcount (Jocelyn Falempe) [RHEL-74282]
- drm/amd/pm: Remove arcturus min power limit (Jocelyn Falempe) [RHEL-74282]
- drm/amd/pm: disable pcie speed switching on Intel platform for smu v14.0.2/3 (Jocelyn Falempe) [RHEL-74282]
- drm/amd/pm: update current_socclk and current_uclk in gpu_metrics on smu v13.0.7 (Jocelyn Falempe) [RHEL-74282]
- drm/amd: Fix initialization mistake for NBIO 7.11 devices (Jocelyn Falempe) [RHEL-74282]
- drm/amd/pm: skip setting the power source on smu v14.0.2/3 (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu: fix usage slab after free (Jocelyn Falempe) [RHEL-74282]
- drm/amd: Add some missing straps from NBIO 7.11.0 (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu/pm: add gen5 display to the user on smu v14.0.2/3 (Jocelyn Falempe) [RHEL-74282]
- drm/amdkfd: Use the correct wptr size (Jocelyn Falempe) [RHEL-74282]
- drm/xe/guc_submit: fix race around suspend_pending (Jocelyn Falempe) [RHEL-74282]
- drm/xe/migrate: use XE_BO_FLAG_PAGETABLE (Jocelyn Falempe) [RHEL-74282]
- Revert "drm/radeon: Delay Connector detecting when HPD singals is unstable" (Jocelyn Falempe) [RHEL-74282]
- drm/xe/migrate: fix pat index usage (Jocelyn Falempe) [RHEL-74282]
- drm/xe/xe_guc_ads: save/restore OA registers and allowlist regs (Jocelyn Falempe) [RHEL-74282]
- drm/bridge: it6505: Fix inverted reset polarity (Jocelyn Falempe) [RHEL-74282]
- drm/fbdev-dma: Select FB_DEFERRED_IO (Jocelyn Falempe) [RHEL-74282]
- drm: panel: jd9365da-h3: Remove unused num_init_cmds structure member (Jocelyn Falempe) [RHEL-74282]
- drm/sti: avoid potential dereference of error pointers in sti_gdp_atomic_check (Jocelyn Falempe) [RHEL-74282]
- drm/sti: avoid potential dereference of error pointers in sti_hqvdp_atomic_check (Jocelyn Falempe) [RHEL-74282]
- drm/panic: Fix uninitialized spinlock acquisition with CONFIG_DRM_PANIC=n (Jocelyn Falempe) [RHEL-74282]
- drm/xe/ufence: Wake up waiters after setting ufence->signalled (Jocelyn Falempe) [RHEL-74282]
- drm/amd/display: Fix null check for pipe_ctx->plane_state in hwss_setup_dpp (Jocelyn Falempe) [RHEL-74282]
- drm/amd/display: Fix null check for pipe_ctx->plane_state in dcn20_program_pipe (Jocelyn Falempe) [RHEL-74282]
- drm/radeon: Fix spurious unplug event on radeon HDMI (Jocelyn Falempe) [RHEL-74282]
- drm/amdkfd: Fix wrong usage of INIT_WORK() (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu: Fix map/unmap queue logic (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu: fix ACA bank count boundary check error (Jocelyn Falempe) [RHEL-74282]
- drm/panthor: Fix OPP refcnt leaks in devfreq initialisation (Jocelyn Falempe) [RHEL-74282]
- drm/panthor: record current and maximum device clock frequencies (Jocelyn Falempe) [RHEL-74282]
- drm/panthor: introduce job cycle and timestamp accounting (Jocelyn Falempe) [RHEL-74282]
- drm: use ATOMIC64_INIT() for atomic64_t (Jocelyn Falempe) [RHEL-74282]
- drm/amdkfd: Use dynamic allocation for CU occupancy array in 'kfd_get_cu_occupancy()' (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu: Fix the memory allocation issue in amdgpu_discovery_get_nps_info() (Jocelyn Falempe) [RHEL-74282]
- drm/vkms: Drop unnecessary call to drm_crtc_cleanup() (Jocelyn Falempe) [RHEL-74282]
- drm/nouveau/gr/gf100: Fix missing unlock in gf100_gr_chan_new() (Jocelyn Falempe) [RHEL-74282]
- drm/amd/display: Reduce HPD Detection Interval for IPS (Jocelyn Falempe) [RHEL-74282]
- drm/amd/display: Increase idle worker HPD detection time (Jocelyn Falempe) [RHEL-74282]
- drm/xe/hdcp: Fix gsc structure check in fw check status (Jocelyn Falempe) [RHEL-74282]
- drm: panel: nv3052c: correct spi_device_id for RG35XX panel (Jocelyn Falempe) [RHEL-74282]
- drm/panic: Select ZLIB_DEFLATE for DRM_PANIC_SCREEN_QR_CODE (Jocelyn Falempe) [RHEL-74282]
- drm/bridge: tc358767: Fix link properties discovery (Jocelyn Falempe) [RHEL-74282]
- drm/amd/display: fix a memleak issue when driver is removed (Jocelyn Falempe) [RHEL-74282]
- drm/bridge: it6505: Drop EDID cache on bridge power off (Jocelyn Falempe) [RHEL-74282]
- drm/bridge: anx7625: Drop EDID cache on bridge power off (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu/gfx9: Add Cleaner Shader Deinitialization in gfx_v9_0 Module (Jocelyn Falempe) [RHEL-74282]
- drm/amdgpu: Fix JPEG v4.0.3 register write (Jocelyn Falempe) [RHEL-74282]
- drm/panel: nt35510: Make new commands optional (Jocelyn Falempe) [RHEL-74282]
- udmabuf: fix vmap_udmabuf error page set (Jocelyn Falempe) [RHEL-74282]
- udmabuf: change folios array from kmalloc to kvmalloc (Jocelyn Falempe) [RHEL-74282]
- drm/mm: Mark drm_mm_interval_tree*() functions with __maybe_unused (Jocelyn Falempe) [RHEL-74282]
- drm/amd/display: Fix incorrect DSC recompute trigger (Jocelyn Falempe) [RHEL-74282]
- drm/amd/display: Skip Invalid Streams from DSC Policy (Jocelyn Falempe) [RHEL-74282]
- rcu/kvfree: Fix data-race in __mod_timer / kvfree_call_rcu (Rafael Aquini) [RHEL-73367] {CVE-2024-53160}
- not upstream: Set vdso is_ready later during boot process (Herbert Xu) [RHEL-76765]
- net: reenable NETIF_F_IPV6_CSUM offload for BIG TCP packets (CKI Backport Bot) [RHEL-74124] {CVE-2025-21629}
- cppc_cpufreq: Use desired perf if feedback ctrs are 0 or unchanged (Mark Langsdorf) [RHEL-66201]
- Bluetooth: hci_core: Fix sleeping function called from invalid context (CKI Backport Bot) [RHEL-74114] {CVE-2024-57894}
- cxl/pci: Check dport->regs.rcd_pcie_cap availability before accessing (Myron Stowe) [RHEL-70563]
- cxl/pci: Add sysfs attribute for CXL 1.1 device link status (Myron Stowe) [RHEL-70563]
- cxl/core/regs: Add rcd_pcie_cap initialization (Myron Stowe) [RHEL-70563]
- Bluetooth: MGMT: Fix slab-use-after-free Read in set_powered_sync (CKI Backport Bot) [RHEL-76123] {CVE-2024-53208}

* Fri Jan 31 2025 Jan Stancek <jstancek@redhat.com> [6.12.0-48.el10]
- ALSA: Intel AVS audio hardware enablement for RHEL 10 (Jaroslav Kysela) [RHEL-72802]
- gitlab-ci: remove superfluous test_debug/debug_architectures (Michael Hofmann)
- redhat: update brew target for RHEL scratch builds (Jan Stancek)
- iommu/vt-d: Fix qi_batch NULL pointer with nested parent domain (Jerry Snitselaar) [RHEL-73411] {CVE-2024-56668}
- iommu/vt-d: Remove cache tags before disabling ATS (Jerry Snitselaar) [RHEL-73411] {CVE-2024-56669}
- iommufd: Fix out_fput in iommufd_fault_alloc() (Jerry Snitselaar) [RHEL-73411] {CVE-2024-56624}
- iommu/vt-d: Fix checks and print in pgtable_walk() (Jerry Snitselaar) [RHEL-73411]
- iommu/vt-d: Fix checks and print in dmar_fault_dump_ptes() (Jerry Snitselaar) [RHEL-73411]
- iommu/amd/pgtbl_v2: Take protection domain lock before invalidating TLB (Jerry Snitselaar) [RHEL-73411]
- iommu/arm-smmu: Defer probe of clients after smmu device bound (Jerry Snitselaar) [RHEL-73411] {CVE-2024-56568}
- iommu/tegra241-cmdqv: Fix unused variable warning (Jerry Snitselaar) [RHEL-73411]
- iommu/tegra241-cmdqv: Staticize cmdqv_debugfs_dir (Jerry Snitselaar) [RHEL-73411]
- iommu/s390: Implement blocking domain (Jerry Snitselaar) [RHEL-73411] {CVE-2024-53232}
- dmaengine: tegra: Return correct DMA status when paused (Jerry Snitselaar) [RHEL-73412]
- dmaengine: dw: Select only supported masters for ACPI devices (Jerry Snitselaar) [RHEL-73412]
- xfs: eliminate lockdep false positives in xfs_attr_shortform_list (Bill O'Donnell) [RHEL-46697]
- RDMA/uverbs: Prevent integer overflow issue (CKI Backport Bot) [RHEL-74227] {CVE-2024-57890}
- ALSA: AMD audio hardware enablement for RHEL 10 (Jaroslav Kysela) [RHEL-64633]
- redhat/configs: enable iBFT parsing on aarch64 (Chris Leech) [RHEL-75491]

* Wed Jan 29 2025 Jan Stancek <jstancek@redhat.com> [6.12.0-47.el10]
- ipvlan: Support bonding events (Hangbin Liu) [RHEL-73828]
- dm array: fix releasing a faulty array block twice in dm_array_cursor_end (CKI Backport Bot) [RHEL-74443] {CVE-2024-57929}
- redhat/kernel.spec: work around find-debuginfo aborting cross builds (Jan Stancek) [RHEL-76454]
- crypto: aes-gcm-p10 - Use the correct bit to test for P10 (Mamatha Inamdar) [RHEL-62818]
- crypto: powerpc/p10-aes-gcm - Add dependency on CRYPTO_SIMDand re-enable CRYPTO_AES_GCM_P10 (Mamatha Inamdar) [RHEL-62818]
- crypto: powerpc/p10-aes-gcm - Register modules as SIMD (Mamatha Inamdar) [RHEL-62818]
- crypto: powerpc/p10-aes-gcm - Re-write AES/GCM stitched implementation (Mamatha Inamdar) [RHEL-62818]
- ASoC: Intel: soc-acpi: arl: Add match entries for new cs42l43 laptops (Jaroslav Kysela) [RHEL-73890]
- ASoC: Intel: soc-acpi: arl: Correct naming of a cs35l56 address struct (Jaroslav Kysela) [RHEL-73890]
- ALSA: seq: oss: Fix races at processing SysEx messages (Jaroslav Kysela) [RHEL-73890] {CVE-2024-57893}
- ALSA hda/realtek: Add quirk for Framework F111:000C (Jaroslav Kysela) [RHEL-73890]
- ALSA: seq: Check UMP support for midi_version change (Jaroslav Kysela) [RHEL-73890]
- Revert "ALSA: ump: Don't enumeration invalid groups for legacy rawmidi" (Jaroslav Kysela) [RHEL-73890]
- ASoC: audio-graph-card: Call of_node_put() on correct node (Jaroslav Kysela) [RHEL-73890]
- sound: usb: format: don't warn that raw DSD is unsupported (Jaroslav Kysela) [RHEL-73890]
- sound: usb: enable DSD output for ddHiFi TC44C (Jaroslav Kysela) [RHEL-73890]
- ALSA: hda/realtek: Add new alc2xx-fixup-headset-mic model (Jaroslav Kysela) [RHEL-73890]
- ALSA: hda/ca0132: Use standard HD-audio quirk matching helpers (Jaroslav Kysela) [RHEL-73890]
- ALSA: hda/realtek - Add support for ASUS Zen AIO 27 Z272SD_A272SD audio (Jaroslav Kysela) [RHEL-73890]
- ALSA: hda: cs35l56: Remove calls to cs35l56_force_sync_asp1_registers_from_cache() (Jaroslav Kysela) [RHEL-73890]
- ALSA: usb-audio: US16x08: Initialize array before use (Jaroslav Kysela) [RHEL-73890]
- ALSA: sh: Fix wrong argument order for copy_from_iter() (Jaroslav Kysela) [RHEL-73890]
- ALSA: ump: Shut up truncated string warning (Jaroslav Kysela) [RHEL-73890]
- ALSA: sh: Use standard helper for buffer accesses (Jaroslav Kysela) [RHEL-73890]
- ALSA: hda/conexant: fix Z60MR100 startup pop issue (Jaroslav Kysela) [RHEL-73890]
- ALSA: ump: Update legacy substream names upon FB info update (Jaroslav Kysela) [RHEL-73890]
- ALSA: ump: Indicate the inactive group in legacy substream names (Jaroslav Kysela) [RHEL-73890]
- ALSA: ump: Don't open legacy substream for an inactive group (Jaroslav Kysela) [RHEL-73890]
- ASoC: Intel: sof_sdw: Fix DMI match for Lenovo 21Q6 and 21Q7 (Jaroslav Kysela) [RHEL-73890]
- ASoC: Intel: sof_sdw: Fix DMI match for Lenovo 21QA and 21QB (Jaroslav Kysela) [RHEL-73890]
- ASoC: amd: ps: Fix for enabling DMIC on acp63 platform via _DSD entry (Jaroslav Kysela) [RHEL-73890]
- ASoC: SOF: Intel: hda-dai: Do not release the link DMA on STOP (Jaroslav Kysela) [RHEL-73890] {CVE-2024-57805}
- ALSA: memalloc: prefer dma_mapping_error() over explicit address checking (Jaroslav Kysela) [RHEL-73890] {CVE-2024-57800}
- firmware: arm_scmi: Fix i.MX build dependency (Jaroslav Kysela) [RHEL-73890]
- ASoC: Intel: sof_sdw: Add space for a terminator into DAIs array (Jaroslav Kysela) [RHEL-73890] {CVE-2024-57880}
- ASoC: fsl_spdif: change IFACE_PCM to IFACE_MIXER (Jaroslav Kysela) [RHEL-73890]
- ASoC: fsl_xcvr: change IFACE_PCM to IFACE_MIXER (Jaroslav Kysela) [RHEL-73890]
- ASoC: tas2781: Fix calibration issue in stress test (Jaroslav Kysela) [RHEL-73890]
- ASoC: amd: yc: Fix the wrong return value (Jaroslav Kysela) [RHEL-73890]
- ALSA: control: Avoid WARN() for symlink errors (Jaroslav Kysela) [RHEL-73890] {CVE-2024-56657}
- ALSA: hda/realtek: Fix headset mic on Acer Nitro 5 (Jaroslav Kysela) [RHEL-73890]
- ALSA: usb-audio: Add implicit feedback quirk for Yamaha THR5 (Jaroslav Kysela) [RHEL-73890]
- ALSA: hda/realtek: Fix spelling mistake "Firelfy" -> "Firefly" (Jaroslav Kysela) [RHEL-73890]
- ALSA: hda: Fix build error without CONFIG_SND_DEBUG (Jaroslav Kysela) [RHEL-73890]
- ASoC: Intel: avs: Fix return status of avs_pcm_hw_constraints_init() (Jaroslav Kysela) [RHEL-73890]
- ASoC: amd: yc: Add quirk for microphone on Lenovo Thinkpad T14s Gen 6 21M1CTO1WW (Jaroslav Kysela) [RHEL-73890]
- ASoC: amd: yc: fix internal mic on Redmi G 2022 (Jaroslav Kysela) [RHEL-73890]
- ASoC: hdmi-codec: reorder channel allocation list (Jaroslav Kysela) [RHEL-73890]
- ALSA: usb-audio: Make mic volume workarounds globally applicable (Jaroslav Kysela) [RHEL-73890]
- ASoC: Intel: soc-acpi-intel-arl-match: Add rt722 and rt1320 support (Jaroslav Kysela) [RHEL-73890]
- ASoC: sdw_utils: Add quirk to exclude amplifier function (Jaroslav Kysela) [RHEL-73890]
- ASoC: Intel: sof_sdw: Add quirks for some new Lenovo laptops (Jaroslav Kysela) [RHEL-73890]
- ASoC: Intel: sof_sdw: Add quirk for cs42l43 system using host DMICs (Jaroslav Kysela) [RHEL-73890]
- ASoC: sdw_utils: Add a quirk to allow the cs42l43 mic DAI to be ignored (Jaroslav Kysela) [RHEL-73890]
- ASoC: sdw_utils: Add support for exclusion DAI quirks (Jaroslav Kysela) [RHEL-73890]
- ALSA: hda/realtek: Use codec SSID matching for Lenovo devices (Jaroslav Kysela) [RHEL-73890]
- ALSA: hda/conexant: Use the new codec SSID matching (Jaroslav Kysela) [RHEL-73890]
- ALSA: hda: Use own quirk lookup helper (Jaroslav Kysela) [RHEL-73890]
- ASoC: Intel: sof_rt5682: Add HDMI-In capture with rt5682 support for MTL. (Jaroslav Kysela) [RHEL-73890]
- ALSA: hda/realtek: Add support for Samsung Galaxy Book3 360 (NP730QFG) (Jaroslav Kysela) [RHEL-73890]
- ALSA: hda/realtek: Enable mute and micmute LED on HP ProBook 430 G8 (Jaroslav Kysela) [RHEL-73890]
- ALSA: usb-audio: add mixer mapping for Corsair HS80 (Jaroslav Kysela) [RHEL-73890]
- ALSA: hda/realtek: fix micmute LEDs don't work on HP Laptops (Jaroslav Kysela) [RHEL-73890]
- ALSA: usb-audio: Add extra PID for RME Digiface USB (Jaroslav Kysela) [RHEL-73890]
- ALSA: usb-audio: Fix a DMA to stack memory bug (Jaroslav Kysela) [RHEL-73890]
- ASoC: mediatek: mt8188-mt6359: Remove hardcoded dmic codec (Jaroslav Kysela) [RHEL-73890]
- ASoC: SOF: ipc3-topology: fix resource leaks in sof_ipc3_widget_setup_comp_dai() (Jaroslav Kysela) [RHEL-73890]
- ASoC: SOF: ipc3-topology: Convert the topology pin index to ALH dai index (Jaroslav Kysela) [RHEL-73890]
- ALSA: usb-audio: Notify xrun for low-latency mode (Jaroslav Kysela) [RHEL-73890]
- ALSA: seq: ump: Fix seq port updates per FB info notify (Jaroslav Kysela) [RHEL-73890]
- ALSA: hda/realtek: Apply quirk for Medion E15433 (Jaroslav Kysela) [RHEL-73890]
- ALSA: hda/realtek: fix mute/micmute LEDs don't work for EliteBook X G1i (Jaroslav Kysela) [RHEL-73890]
- ALSA: hda/realtek: Fix Internal Speaker and Mic boost of Infinix Y4 Max (Jaroslav Kysela) [RHEL-73890]
- ALSA: hda/realtek: Set PCBeep to default value for ALC274 (Jaroslav Kysela) [RHEL-73890]
- ALSA: hda/realtek: Enable speaker pins for Medion E15443 platform (Jaroslav Kysela) [RHEL-73890]
- ALSA: hda/realtek: Update ALC225 depop procedure (Jaroslav Kysela) [RHEL-73890]
- ALSA: pcm: Add sanity NULL check for the default mmap fault handler (Jaroslav Kysela) [RHEL-73890] {CVE-2024-53180}
- ALSA: ump: Fix evaluation of MIDI 1.0 FB info (Jaroslav Kysela) [RHEL-73890]
- ALSA: rawmidi: Fix kvfree() call in spinlock (Jaroslav Kysela) [RHEL-73890]
- ASoC: da7213: Populate max_register to regmap_config (Jaroslav Kysela) [RHEL-73890]
- ASoC: codecs: Fix atomicity violation in snd_soc_component_get_drvdata() (Jaroslav Kysela) [RHEL-73890]
- ASoC: amd: yc: Add a quirk for microfone on Lenovo ThinkPad P14s Gen 5 21MES00B00 (Jaroslav Kysela) [RHEL-73890]
- ALSA: usb-audio: Fix out of bounds reads when finding clock sources (Jaroslav Kysela) [RHEL-73890] {CVE-2024-53150}
- ALSA: usb-audio: Fix potential out-of-bound accesses for Extigy and Mbox devices (Jaroslav Kysela) [RHEL-73890] {CVE-2024-53197}
- ASoC: mediatek: Check num_codecs is not zero to avoid panic during probe (Jaroslav Kysela) [RHEL-73890] {CVE-2024-56685}
- ASoC: amd: yc: Fix for enabling DMIC on acp6x via _DSD entry (Jaroslav Kysela) [RHEL-73890]
- ALSA: core: Fix possible NULL dereference caused by kunit_kzalloc() (Jaroslav Kysela) [RHEL-73890] {CVE-2024-56696}
- ASoC: imx-audmix: Add NULL check in imx_audmix_probe (Jaroslav Kysela) [RHEL-73890] {CVE-2024-53199}
- ALSA: hda/realtek: Update ALC256 depop procedure (Jaroslav Kysela) [RHEL-73890]
- ALSA: 6fire: Release resources at card release (Jaroslav Kysela) [RHEL-73890] {CVE-2024-53239}
- ALSA: caiaq: Use snd_card_free_when_closed() at disconnection (Jaroslav Kysela) [RHEL-73890] {CVE-2024-56531}
- ALSA: us122l: Use snd_card_free_when_closed() at disconnection (Jaroslav Kysela) [RHEL-73890] {CVE-2024-56532}
- ALSA: usx2y: Use snd_card_free_when_closed() at disconnection (Jaroslav Kysela) [RHEL-73890] {CVE-2024-56533}
- ASoC: rt722-sdca: Remove logically deadcode in rt722-sdca.c (Jaroslav Kysela) [RHEL-73890]
- ASoC: amd: acp: fix for cpu dai index logic (Jaroslav Kysela) [RHEL-73890]
- ASoC: amd: acp: fix for inconsistent indenting (Jaroslav Kysela) [RHEL-73890]
- ASoC: fsl-asoc-card: Add missing handling of {hp,mic}-dt-gpios (Jaroslav Kysela) [RHEL-73890]
- ASoC: fsl_micfil: fix regmap_write_bits usage (Jaroslav Kysela) [RHEL-73890]
- RDMA/bnxt_re: Fix error recovery sequence (Mohammad Heib) [RHEL-22876]
- RDMA/bnxt_re: Fix the locking while accessing the QP table (Mohammad Heib) [RHEL-22876]
- RDMA/bnxt_re: Disable use of reserved wqes (Mohammad Heib) [RHEL-22876]
- RDMA/bnxt_re: Fix max_qp_wrs reported (Mohammad Heib) [RHEL-22876]
- RDMA/bnxt_re: Fix reporting hw_ver in query_device (Mohammad Heib) [RHEL-22876]
- RDMA/bnxt_re: Add check for path mtu in modify_qp (Mohammad Heib) [RHEL-22876]
- RDMA/bnxt_re: Fix the check for 9060 condition (Mohammad Heib) [RHEL-22876]
- RDMA/bnxt_re: Avoid sending the modify QP workaround for latest adapters (Mohammad Heib) [RHEL-22876]
- RDMA/bnxt_re: Avoid initializing the software queue for user queues (Mohammad Heib) [RHEL-22876]
- RDMA/bnxt_re: Fix max SGEs for the Work Request (Mohammad Heib) [RHEL-22876]
- RDMA/bnxt_re: Remove always true dattr validity check (Mohammad Heib) [RHEL-22876]
- RDMA/bnxt_re: Correct the sequence of device suspend (Mohammad Heib) [RHEL-22876]
- RDMA/bnxt_re: Check cqe flags to know imm_data vs inv_irkey (Mohammad Heib) [RHEL-22876]
- CI: Enable pipelines for rt-64k variant (Juri Lelli) [RHEL-70288]
- redhat: Add kernel-rt-64k variant (Juri Lelli) [RHEL-70288]

* Mon Jan 27 2025 Jan Stancek <jstancek@redhat.com> [6.12.0-46.el10]
- redhat: hsr: Mark as tech preview (Felix Maurer) [RHEL-74748]
- xfs: Mark all experimental code as tech preview (Bill O'Donnell) [RHEL-64936]
- redhat: create 'debug' addon for UKI (Li Tian) [RHEL-70836]
- mptcp: disable by default (Davide Caratti) [RHEL-74247]
- initramfs: avoid filename buffer overrun (Rafael Aquini) [RHEL-73366] {CVE-2024-53142}
- redhat/configs: set new PKEY_UV option on s390 (Mete Durlu) [RHEL-24135]
- s390/crypto: Add hardware acceleration for full AES-XTS mode (Mete Durlu) [RHEL-24136]
- s390/crypto: Postpone the key split to key conversion (Mete Durlu) [RHEL-24136]
- s390/crypto: Introduce function for tokenize clearkeys (Mete Durlu) [RHEL-24136]
- s390/crypto: Generalize parameters for key conversion (Mete Durlu) [RHEL-24136]
- s390/crypto: Use module-local structures for protected keys (Mete Durlu) [RHEL-24136]
- s390/crypto: Convert to reverse x-mas tree, rename ret to rc (Mete Durlu) [RHEL-24136]
- s390/pkey: Tolerate larger key blobs (Mete Durlu) [RHEL-24136]
- s390/pkey: Add new pkey handler module pkey-uv (Mete Durlu) [RHEL-24135]
- s390/pkey: Build module name array selectively based on kernel config options (Mete Durlu) [RHEL-24135]
- s390/pkey: Fix checkpatch findings in pkey header file (Mete Durlu) [RHEL-24135]
- s390/pkey: Rework pkey verify for protected keys (Mete Durlu) [RHEL-24135]
- s390/pkey: Simplify protected key length calculation code (Mete Durlu) [RHEL-24135]
- s390/zcrypt: Cleanup include zcrypt_api.h (Mete Durlu) [RHEL-24135]
- ipvs: speed up reads from ip_vs_conn proc file (Florian Westphal) [RHEL-68933]
- PCI: Batch BAR sizing operations (Myron Stowe) [RHEL-76026]
- xfrm: mark packet offload as tech preview (Sabrina Dubroca) [RHEL-75472]
- mm/kmemleak: fix sleeping function called from invalid context at print message (CKI Backport Bot) [RHEL-74104] {CVE-2024-57885}
- mm: vmscan: account for free pages to prevent infinite Loop in throttle_direct_reclaim() (CKI Backport Bot) [RHEL-74099] {CVE-2024-57884}
- bnxt_en: Fix DIM shutdown (Michal Schmidt) [RHEL-73718]
- bnxt_en: Fix possible memory leak when hwrm_req_replace fails (Michal Schmidt) [RHEL-73718]
- bnxt_en: Fix aggregation ID mask to prevent oops on 5760X chips (Michal Schmidt) [RHEL-73718]
- bnxt_en: Fix GSO type for HW GRO packets on 5750X chips (Michal Schmidt) [RHEL-73718]
- selftests: drv-net: rss_ctx: Add test for ntuple rule (Michal Schmidt) [RHEL-73718]
- bnxt_en: ethtool: Supply ntuple rss context action (Michal Schmidt) [RHEL-73718]

* Fri Jan 24 2025 Jan Stancek <jstancek@redhat.com> [6.12.0-45.el10]
- netfilter: conntrack: clamp maximum hashtable size to INT_MAX (CKI Backport Bot) [RHEL-73620]
- netfilter: nf_tables: imbalance in flowtable binding (CKI Backport Bot) [RHEL-73620]
- netfilter: nft_set_hash: unaligned atomic read on struct nft_set_ext (CKI Backport Bot) [RHEL-73620]
- netfilter: nft_set_hash: skip duplicated elements pending gc run (CKI Backport Bot) [RHEL-73620]
- netfilter: nft_inner: incorrect percpu area handling under softirq (CKI Backport Bot) [RHEL-73620]
- netfilter: nft_socket: remove WARN_ON_ONCE on maximum cgroup level (CKI Backport Bot) [RHEL-73620]
- netfilter: x_tables: fix LED ID check in led_tg_check() (CKI Backport Bot) [RHEL-73620]
- ipvs: fix UB due to uninitialized stack access in ip_vs_protocol_init() (CKI Backport Bot) [RHEL-73620]
- netfilter: ipset: add missing range check in bitmap_ip_uadt (CKI Backport Bot) [RHEL-73620]
- netfilter: bpf: Pass string literal as format argument of request_module() (CKI Backport Bot) [RHEL-73620]
- netfilter: nf_tables: must hold rcu read lock while iterating object type list (CKI Backport Bot) [RHEL-73620]
- netfilter: nf_tables: must hold rcu read lock while iterating expression type list (CKI Backport Bot) [RHEL-73620]
- mptcp: fix TCP options overflow. (CKI Backport Bot) [RHEL-73495]
- mptcp: sysctl: sched: avoid using current->nsproxy (CKI Backport Bot) [RHEL-73495]
- mptcp: sysctl: blackhole timeout: avoid using current->nsproxy (CKI Backport Bot) [RHEL-73495]
- KVM: s390: add gen17 facilities to CPU model (Mete Durlu) [RHEL-24195]
- KVM: s390: add msa11 to cpu model (Mete Durlu) [RHEL-24195]
- KVM: s390: add concurrent-function facility to cpu model (Mete Durlu) [RHEL-24195]
- redhat/configs: Re-enable full ZRAM configuration and all backends (Neal Gompa) [RHEL-72036]
- wireguard: device: support big tcp GSO (CKI Backport Bot) [RHEL-74019]
- wireguard: selftests: load nf_conntrack if not present (CKI Backport Bot) [RHEL-74019]
- wireguard: allowedips: remove redundant selftest call (CKI Backport Bot) [RHEL-74019]
- wireguard: device: omit unnecessary memset of netdev private data (CKI Backport Bot) [RHEL-74019]
- bpf: Do not alloc arena on unsupported arches (Viktor Malik) [RHEL-68958]
- powerpc/pseries/eeh: Fix get PE state translation (Mamatha Inamdar) [RHEL-74254]
- MAINTAINERS: Make Kristen Accardi the IAA crypto driver maintainer (Vladis Dronov) [RHEL-58597]
- crypto: iaa - Remove potential infinite loop in check_completion() (Vladis Dronov) [RHEL-58597]
- s390/entry: Mark IRQ entries to fix stack depot warnings (Mete Durlu) [RHEL-74467]

* Wed Jan 22 2025 Jan Stancek <jstancek@redhat.com> [6.12.0-44.el10]
- s390/iucv: MSG_PEEK causes memory leak in iucv_sock_destruct() (Mete Durlu) [RHEL-74386]
- redhat/configs: Disable deprecated CONFIG_LCS option on s390 (Mete Durlu) [RHEL-68296]
- powerpc/pseries/iommu: Don't unset window if it was never set (Mamatha Inamdar) [RHEL-74222]
- selftests: net: local_termination: require mausezahn (CKI Backport Bot) [RHEL-74034]
- selftests: openvswitch: fix tcpdump execution (CKI Backport Bot) [RHEL-74034]
- selftests: rds: move test.py to TEST_FILES (CKI Backport Bot) [RHEL-74034]
- selftests: netfilter: Fix missing return values in conntrack_dump_flush (CKI Backport Bot) [RHEL-74034]
- selftests: net: include lib/sh/*.sh with lib.sh (CKI Backport Bot) [RHEL-74034]
- selftests: tls: add a selftest for wrapping rec_seq (CKI Backport Bot) [RHEL-74034]
- selftests: ETS: Use defer for test cleanup (CKI Backport Bot) [RHEL-74034]
- selftests: TBF: Use defer for test cleanup (CKI Backport Bot) [RHEL-74034]
- selftests: RED: Use defer for test cleanup (CKI Backport Bot) [RHEL-74034]
- selftests: forwarding: lib: Allow passing PID to stop_traffic() (CKI Backport Bot) [RHEL-74034]
- selftests: forwarding: Add a fallback cleanup() (CKI Backport Bot) [RHEL-74034]
- selftests: net: lib: Introduce deferred commands (CKI Backport Bot) [RHEL-74034]
- selftests: net: move EXTRA_CLEAN of libynl.a into ynl.mk (CKI Backport Bot) [RHEL-74034]
- selftests: net: rebuild YNL if dependencies changed (CKI Backport Bot) [RHEL-74034]
- ipmr: tune the ipmr_can_free_table() checks. (CKI Backport Bot) [RHEL-74037]
- ipmr: fix build with clang and DEBUG_NET disabled. (CKI Backport Bot) [RHEL-74037]
- net/ipv6: release expired exception dst cached in socket (CKI Backport Bot) [RHEL-74037]
- ipv6: avoid possible NULL deref in modify_prefix_route() (CKI Backport Bot) [RHEL-74037]
- ipmr: fix tables suspicious RCU usage (CKI Backport Bot) [RHEL-74037]
- ip6mr: fix tables suspicious RCU usage (CKI Backport Bot) [RHEL-74037]
- ipmr: add debug check for mr table cleanup (CKI Backport Bot) [RHEL-74037]
- selftests/rtnetlink.sh: add mngtempaddr test (CKI Backport Bot) [RHEL-74037]
- ipv6: Fix soft lockups in fib6_select_path under high next hop churn (CKI Backport Bot) [RHEL-74037]
- selftests: net: really check for bg process completion (CKI Backport Bot) [RHEL-74037]
- ipv6: release nexthop on device removal (CKI Backport Bot) [RHEL-74037]
- ipv6: switch inet6_acaddr_hash() to less predictable hash (CKI Backport Bot) [RHEL-74037]
- ipv6: switch inet6_addr_hash() to less predictable hash (CKI Backport Bot) [RHEL-74037]
- ptp: Add error handling for adjfine callback in ptp_clock_adjtime (CKI Backport Bot) [RHEL-74024]
- ptp_pch: Replace deprecated PCI functions (CKI Backport Bot) [RHEL-74024]
- wireguard: mark as Tech Preview (Hangbin Liu) [RHEL-74327]
- nbd: fix partial sending (Ming Lei) [RHEL-74229]
- scsi: lpfc: Fix spelling errors 'asynchronously' (Dick Kennedy) [RHEL-61740]
- scsi: lpfc: Copyright updates for 14.4.0.6 patches (Dick Kennedy) [RHEL-61740]
- scsi: lpfc: Update lpfc version to 14.4.0.6 (Dick Kennedy) [RHEL-61740]
- scsi: lpfc: Change lpfc_nodelist nlp_flag member into a bitmask (Dick Kennedy) [RHEL-61740]
- scsi: lpfc: Remove NLP_RELEASE_RPI flag from nodelist structure (Dick Kennedy) [RHEL-61740]
- scsi: lpfc: Prevent NDLP reference count underflow in dev_loss_tmo callback (Dick Kennedy) [RHEL-61740]
- scsi: lpfc: Add cleanup of nvmels_wq after HBA reset (Dick Kennedy) [RHEL-61740]
- scsi: lpfc: Check SLI_ACTIVE flag in FDMI cmpl before submitting follow up FDMI (Dick Kennedy) [RHEL-61740]
- scsi: lpfc: Update lpfc_els_flush_cmd() to check for SLI_ACTIVE before BSG flag (Dick Kennedy) [RHEL-61740]
- scsi: lpfc: Call lpfc_sli4_queue_unset() in restart and rmmod paths (Dick Kennedy) [RHEL-61740]
- scsi: lpfc: Check devloss callbk done flag for potential stale NDLP ptrs (Dick Kennedy) [RHEL-61740]
- scsi: lpfc: Modify CGN warning signal calculation based on EDC response (Dick Kennedy) [RHEL-61740]
- md: reintroduce md-linear (Nigel Croxon) [RHEL-74142]
- Revert "readahead: properly shorten readahead when falling back to do_page_cache_ra()" (Maxim Levitsky) [RHEL-55724 RHEL-56929] {CVE-2024-57839}
- i40e: add ability to reset VF for Tx and Rx MDD events (Michal Schmidt) [RHEL-73034]

* Mon Jan 20 2025 Jan Stancek <jstancek@redhat.com> [6.12.0-43.el10]
- net/ipv6: delete temporary address if mngtmpaddr is removed or unmanaged (CKI Backport Bot) [RHEL-39340]
- vfio/pci: Fallback huge faults for unaligned pfn (Alex Williamson) [RHEL-72822]
- iommu/tegra241-cmdqv: do not use smp_processor_id in preemptible context (Luis Claudio R. Goncalves) [RHEL-74342]
- net: sched: fix ordering of qlen adjustment (CKI Backport Bot) [RHEL-73395] {CVE-2024-53164}
- net_sched: sch_fq: don't follow the fast path if Tx is behind now (CKI Backport Bot) [RHEL-73395]
- s390/uvdevice: Support longer secret lists (Mete Durlu) [RHEL-25204]
- s390/uv: Retrieve UV secrets sysfs support (Mete Durlu) [RHEL-25204]
- s390/uvdevice: Increase indent in IOCTL definitions (Mete Durlu) [RHEL-25204]
- s390/uvdevice: Add Retrieve Secret IOCTL (Mete Durlu) [RHEL-25204]
- s390/uv: Retrieve UV secrets support (Mete Durlu) [RHEL-25204]
- s390/uv: Use a constant for more-data rc (Mete Durlu) [RHEL-25204]
- s390/uv: Provide host-key hashes in sysfs (Mete Durlu) [RHEL-47110]
- s390/uv: Refactor uv-sysfs creation (Mete Durlu) [RHEL-47110]
- net/l2tp: fix warning in l2tp_exit_net found by syzbot (Guillaume Nault) [RHEL-73846]
- geneve: do not assume mac header is set in geneve_xmit_skb() (Guillaume Nault) [RHEL-73846]
- net: Fix netns for ip_tunnel_init_flow() (Guillaume Nault) [RHEL-73846]
- futex: fix user access on powerpc (Waiman Long) [RHEL-70187]
- x86: fix off-by-one in access_ok() (Waiman Long) [RHEL-70187]
- futex: improve user space accesses (Waiman Long) [RHEL-70187]
- s390/pci: Add pci_msg debug view to PCI report (Mete Durlu) [RHEL-24144]
- s390/debug: Add a reverse mode for debug_dump() (Mete Durlu) [RHEL-24144]
- s390/debug: Add debug_dump() to write debug view to a string buffer (Mete Durlu) [RHEL-24144]
- s390/debug: Split private data alloc/free out of file operations (Mete Durlu) [RHEL-24144]
- s390/debug: Simplify and document debug_next_entry() logic (Mete Durlu) [RHEL-24144]
- s390/pci: Report PCI error recovery results via SCLP (Mete Durlu) [RHEL-24144]
- s390/debug: Pass in and enforce output buffer size for format handlers (Mete Durlu) [RHEL-24144]
- s390/sclp: Allow user-space to provide PCI reports for optical modules (Mete Durlu) [RHEL-71264]

* Wed Jan 15 2025 Jan Stancek <jstancek@redhat.com> [6.12.0-42.el10]
- net: sched: fix erspan_opt settings in cls_flower (Xin Long) [RHEL-73195]
- KVM: SVM: Allow guest writes to set MSR_AMD64_DE_CFG bits (Vitaly Kuznetsov) [RHEL-71416]
- redhat/configs: enable ARCH_TEGRA_241_SOC (Mark Salter) [RHEL-67684]
- x86/cpu: Add Lunar Lake to list of CPUs with a broken MONITOR implementation (Steve Best) [RHEL-68393]
- net: sysctl: allow dump_cpumask to handle higher numbers of CPUs (Antoine Tenart) [RHEL-73199]
- net: sysctl: do not reserve an extra char in dump_cpumask temporary buffer (Antoine Tenart) [RHEL-73199]
- net: sysctl: remove always-true condition (Antoine Tenart) [RHEL-73199]
- net: tcp: Add noinline_for_tracing annotation for tcp_drop_reason() (Antoine Tenart) [RHEL-73172]
- compiler_types: Add noinline_for_tracing annotation (Antoine Tenart) [RHEL-73172]
- net: vxlan: replace VXLAN_INVALID_HDR with VNI_NOT_FOUND (Antoine Tenart) [RHEL-73172]
- net: vxlan: use kfree_skb_reason() in encap_bypass_if_local() (Antoine Tenart) [RHEL-73172]
- net: vxlan: use kfree_skb_reason() in vxlan_encap_bypass() (Antoine Tenart) [RHEL-73172]
- net: vxlan: use kfree_skb_reason() in vxlan_mdb_xmit() (Antoine Tenart) [RHEL-73172]
- net: vxlan: add drop reasons support to vxlan_xmit_one() (Antoine Tenart) [RHEL-73172]
- net: vxlan: use kfree_skb_reason() in vxlan_xmit() (Antoine Tenart) [RHEL-73172]
- net: vxlan: make vxlan_set_mac() return drop reasons (Antoine Tenart) [RHEL-73172]
- net: vxlan: make vxlan_snoop() return drop reasons (Antoine Tenart) [RHEL-73172]
- net: vxlan: make vxlan_remcsum() return drop reasons (Antoine Tenart) [RHEL-73172]
- net: vxlan: add skb drop reasons to vxlan_rcv() (Antoine Tenart) [RHEL-73172]
- net: tunnel: make skb_vlan_inet_prepare() return drop reasons (Antoine Tenart) [RHEL-73172]
- net: tunnel: add pskb_inet_may_pull_reason() helper (Antoine Tenart) [RHEL-73172]
- net: skb: add pskb_network_may_pull_reason() helper (Antoine Tenart) [RHEL-73172]
- redhat: Install bpftool into BPF selftests dir (Viktor Malik) [RHEL-73480]
- redhat: Drop bpftool from kernel spec (Viktor Malik) [RHEL-73480]
- tools/power turbostat: Add initial support for GraniteRapids-D (Eddie Kovsky) [RHEL-29354]
- rtc: check if __rtc_read_time was successful in rtc_timer_do_work() (Steve Best) [RHEL-73490] {CVE-2024-56739}
- powerpc/mm/fault: Fix kfence page fault reporting (Mamatha Inamdar) [RHEL-73630]
- bonding: Fix feature propagation of NETIF_F_GSO_ENCAP_ALL (CKI Backport Bot) [RHEL-73198]
- bonding: Fix initial {vlan,mpls}_feature set in bond_compute_features (CKI Backport Bot) [RHEL-73198]
- net, team, bonding: Add netdev_base_features helper (CKI Backport Bot) [RHEL-73198]
- bonding: add ESP offload features when slaves support (CKI Backport Bot) [RHEL-73198]
- Documentation: bonding: add XDP support explanation (CKI Backport Bot) [RHEL-73198]
- bonding: return detailed error when loading native XDP fails (CKI Backport Bot) [RHEL-73198]

* Tue Jan 14 2025 Jan Stancek <jstancek@redhat.com> [6.12.0-41.el10]
- netfilter: IDLETIMER: Fix for possible ABBA deadlock (Phil Sutter) [RHEL-70301]
- tcp: Fix use-after-free of nreq in reqsk_timer_handler(). (Guillaume Nault) [RHEL-73194]
- netfilter: nf_tables: do not defer rule destruction via call_rcu (Florian Westphal) [RHEL-68691]
- sched/numa: fix memory leak due to the overwritten vma->numab_state (Phil Auld) [RHEL-67478]
- netfilter: ipset: Fix for recursive locking warning (Phil Sutter) [RHEL-71827]
- NFSD: Mark exports of NFS as unsupported (Benjamin Coddington) [RHEL-50656]
- netdev-genl: Hold rcu_read_lock in napi_get (Paolo Abeni) [RHEL-73205]
- net: avoid potential UAF in default_operstate() (Paolo Abeni) [RHEL-73205] {CVE-2024-56635}
- net: defer final 'struct net' free in netns dismantle (Paolo Abeni) [RHEL-73205] {CVE-2024-56658}
- net: restrict SO_REUSEPORT to inet sockets (Paolo Abeni) [RHEL-73205]
- Revert "rtnetlink: add guard for RTNL" (Paolo Abeni) [RHEL-73205]
- netlink: fix false positive warning in extack during dumps (Paolo Abeni) [RHEL-73205] {CVE-2024-53212}
- tcp: check space before adding MPTCP SYN options (Paolo Abeni) [RHEL-73143]
- net: fix memory leak in tcp_conn_request() (Paolo Abeni) [RHEL-73143]
- Revert "udp: avoid calling sock_def_readable() if possible" (Paolo Abeni) [RHEL-73132]
- netfilter: ipset: Hold module reference while requesting a module (Phil Sutter) [RHEL-69538]
- redhat: make kernel-debug-uki-virt installable without kernel-debug-core (Vitaly Kuznetsov) [RHEL-72983]
- KVM: arm64: Fix S1/S2 combination when FWB==1 and S2 has Device memory type (Shaoqin Huang) [RHEL-68039]
- KVM: arm64: Do not allow ID_AA64MMFR0_EL1.ASIDbits to be overridden (Shaoqin Huang) [RHEL-68039]
- KVM: arm64: vgic-its: Add error handling in vgic_its_cache_translation (Shaoqin Huang) [RHEL-68039]
- KVM: arm64: selftests: Add tests for MMIO external abort injection (Shaoqin Huang) [RHEL-68039]
- KVM: arm64: selftests: Convert to kernel's ESR terminology (Shaoqin Huang) [RHEL-68039]
- tools: arm64: Grab a copy of esr.h from kernel (Shaoqin Huang) [RHEL-68039]
- KVM: selftests: Don't bother deleting memslots in KVM when freeing VMs (Shaoqin Huang) [RHEL-68039]
- KVM: arm64: Ignore PMCNTENSET_EL0 while checking for overflow status (Shaoqin Huang) [RHEL-68039]
- KVM: arm64: vgic-its: Add stronger type-checking to the ITS entry sizes (Shaoqin Huang) [RHEL-68039]
- KVM: arm64: vgic: Kill VGIC_MAX_PRIVATE definition (Shaoqin Huang) [RHEL-68039]
- KVM: arm64: vgic: Make vgic_get_irq() more robust (Shaoqin Huang) [RHEL-68039]
- KVM: arm64: vgic-v3: Sanitise guest writes to GICR_INVLPIR (Shaoqin Huang) [RHEL-68039]
- KVM: arm64: Pass on SVE mapping failures (Shaoqin Huang) [RHEL-68039]
- KVM: arm64: Don't map 'kvm_vgic_global_state' at EL2 with pKVM (Shaoqin Huang) [RHEL-68039]
- KVM: arm64: Just advertise SEIS as 0 when emulating ICC_CTLR_EL1 (Shaoqin Huang) [RHEL-68039]
- KVM: arm64: vgic-its: Clear ITE when DISCARD frees an ITE (Shaoqin Huang) [RHEL-68039]
- KVM: arm64: vgic-its: Clear DTE when MAPD unmaps a device (Shaoqin Huang) [RHEL-68039]
- KVM: arm64: vgic-its: Add a data length check in vgic_its_save_* (Shaoqin Huang) [RHEL-68039]
- KVM: arm64: Don't retire aborted MMIO instruction (Shaoqin Huang) [RHEL-68039]
- KVM: arm64: Get rid of userspace_irqchip_in_use (Shaoqin Huang) [RHEL-68039]
- KVM: arm64: Initialize trap register values in hyp in pKVM (Shaoqin Huang) [RHEL-68039]
- KVM: arm64: Initialize the hypervisor's VM state at EL2 (Shaoqin Huang) [RHEL-68039]
- KVM: arm64: Refactor kvm_vcpu_enable_ptrauth() for hyp use (Shaoqin Huang) [RHEL-68039]
- KVM: arm64: Move pkvm_vcpu_init_traps() to init_pkvm_hyp_vcpu() (Shaoqin Huang) [RHEL-68039]
- KVM: arm64: Correctly access TCR2_EL1, PIR_EL1, PIRE0_EL1 with VHE (Shaoqin Huang) [RHEL-68039]

* Sun Jan 12 2025 Jan Stancek <jstancek@redhat.com> [6.12.0-40.el10]
- selftests: netfilter: Stabilize rpath.sh (Phil Sutter) [RHEL-71139]
- redhat/configs: automotive: disable CONFIG_AIO (Davide Caratti) [RHEL-71905]
- redhat/configs: enable CONFIG_USB_XHCI_PCI_RENESAS on RHEL (Desnes Nunes) [RHEL-73371]
- RHEL: Set correct config option for CRYPTO_HMAC_S390 (Mete Durlu) [RHEL-24137]
- redhat/configs: automotive: disable CONFIG_NET_DROP_MONITOR (Davide Caratti) [RHEL-70868]
- qed: put cond_resched() in qed_dmae_operation_wait() (CKI Backport Bot) [RHEL-71560]
- qed: allow the callee of qed_mcp_nvm_read() to sleep (CKI Backport Bot) [RHEL-71560]
- qed: put cond_resched() in qed_grc_dump_ctx_data() (CKI Backport Bot) [RHEL-71560]
- qed: make 'ethtool -d' 10 times faster (CKI Backport Bot) [RHEL-71560]
- x86/sev: Convert shared memory back to private on kexec (Vitaly Kuznetsov) [RHEL-68482]
- x86/mm: Refactor __set_clr_pte_enc() (Vitaly Kuznetsov) [RHEL-68482]
- x86/boot: Skip video memory access in the decompressor for SEV-ES/SNP (Vitaly Kuznetsov) [RHEL-68482]

* Thu Jan 09 2025 Jan Stancek <jstancek@redhat.com> [6.12.0-39.el10]
- platform/x86/intel/pmc: Disable C1 auto-demotion during suspend (Steve Best) [RHEL-66570]
- platform/x86/intel/pmc: Refactor platform resume functions to use cnl_resume() (Steve Best) [RHEL-66570]
- redhat/configs: Enable CONFIG_NETKIT for RHEL (Toke Høiland-Jørgensen) [RHEL-51429]
- bnxt_en: Unregister PTP during PCI shutdown and suspend (Michal Schmidt) [RHEL-54644 RHEL-69499]
- bnxt_en: Refactor bnxt_ptp_init() (Michal Schmidt) [RHEL-54644 RHEL-69499]
- bnxt_en: Fix receive ring space parameters when XDP is active (Michal Schmidt) [RHEL-54644]
- bnxt_en: Fix queue start to update vnic RSS table (Michal Schmidt) [RHEL-54644]
- bnxt_en: Set backplane link modes correctly for ethtool (Michal Schmidt) [RHEL-54644]
- bnxt_en: Reserve rings after PCIe AER recovery if NIC interface is down (Michal Schmidt) [RHEL-54644]
- bnxt_en: use irq_update_affinity_hint() (Michal Schmidt) [RHEL-54644]
- bnxt_en: ethtool: Support unset l4proto on ip4/ip6 ntuple rules (Michal Schmidt) [RHEL-54644]
- bnxt_en: ethtool: Remove ip4/ip6 ntuple support for IPPROTO_RAW (Michal Schmidt) [RHEL-54644]
- s390/cio: Externalize full CMG characteristics (Mete Durlu) [RHEL-24140]
- s390/pci: Expose FIDPARM attribute in sysfs (Mete Durlu) [RHEL-71374]
- perf machine: Initialize machine->env to address a segfault (Michael Petlan) [RHEL-70278]
- redhat/kernel.spec.template: Require kernel-tools-libs in rtla (Tomas Glozar) [RHEL-70863]
- rtla/timerlat: Fix histogram ALL for zero samples (Tomas Glozar) [RHEL-72691]
- s390/pci: Fix leak of struct zpci_dev when zpci_add_device() fails (Mete Durlu) [RHEL-24143]
- s390/pci: Ignore RID for isolated VFs (Mete Durlu) [RHEL-24143]
- s390/pci: Use topology ID for multi-function devices (Mete Durlu) [RHEL-24143]
- s390/pci: Sort PCI functions prior to creating virtual busses (Mete Durlu) [RHEL-24143]

* Mon Jan 06 2025 Jan Stancek <jstancek@redhat.com> [6.12.0-38.el10]
- virtio_ring: add a func argument 'recycle_done' to virtqueue_reset() (Cindy Lu) [RHEL-56981]
- virtio_net: ensure netdev_tx_reset_queue is called on tx ring resize (Cindy Lu) [RHEL-56981]
- virtio_ring: add a func argument 'recycle_done' to virtqueue_resize() (Cindy Lu) [RHEL-56981]
- virtio_net: correct netdev_tx_reset_queue() invocation point (Cindy Lu) [RHEL-56981]
- intel_idle: add Granite Rapids Xeon D support (David Arcari) [RHEL-68122]
- sched/dlserver: Fix dlserver time accounting (Phil Auld) [RHEL-68342]
- sched/dlserver: Fix dlserver double enqueue (Phil Auld) [RHEL-68342]
- sched/fair: Fix NEXT_BUDDY (Phil Auld) [RHEL-68342]
- sched/fair: Fix sched_can_stop_tick() for fair tasks (Phil Auld) [RHEL-68342]
- sched/eevdf: More PELT vs DELAYED_DEQUEUE (Phil Auld) [RHEL-68342]

* Fri Dec 20 2024 Jan Stancek <jstancek@redhat.com> [6.12.0-37.el10]
- vfio/mlx5: Fix unwind flows in mlx5vf_pci_save/resume_device_data() (Alex Williamson) [RHEL-69747]
- vfio/mlx5: Fix an unwind issue in mlx5vf_add_migration_pages() (Alex Williamson) [RHEL-69747]
- i40e: Fix handling changed priv flags (Kamal Heib) [RHEL-69737]
- RHEL-only: mark ublk as tech preview (Ming Lei) [RHEL-50740]
- Revert "block, bfq: merge bfq_release_process_ref() into bfq_put_cooperator()" (Ming Lei) [RHEL-67720]
- block: sed-opal: add ioctl IOC_OPAL_SET_SID_PW (Ming Lei) [RHEL-70861]
- loop: fix type of block size (Ming Lei) [RHEL-65631]
- x86/cpu/topology: Remove limit of CPUs due to disabled IO/APIC (Phil Auld) [RHEL-70901]
- sched/deadline: Fix warning in migrate_enable for boosted tasks (Phil Auld) [RHEL-70901]
- sched/core: Prevent wakeup of ksoftirqd during idle load balance (Phil Auld) [RHEL-70901]
- sched/fair: Check idle_cpu() before need_resched() to detect ilb CPU turning busy (Phil Auld) [RHEL-70901]
- sched/core: Remove the unnecessary need_resched() check in nohz_csd_func() (Phil Auld) [RHEL-70901]
- sched: fix warning in sched_setaffinity (Phil Auld) [RHEL-70901]
- softirq: Allow raising SCHED_SOFTIRQ from SMP-call-function on RT kernel (Phil Auld) [RHEL-70901]
- sched/deadline: Fix replenish_dl_new_period dl_server condition (Phil Auld) [RHEL-70901]
- vfio/mlx5: Align the page tracking max message size with the device capability (CKI Backport Bot) [RHEL-69932]
- tools/rtla: Improve exception handling in timerlat_load.py (Luis Claudio R. Goncalves) [RHEL-69739]
- tools/rtla: Enhance argument parsing in timerlat_load.py (Luis Claudio R. Goncalves) [RHEL-69739]
- tools/rtla: Improve code readability in timerlat_load.py (Luis Claudio R. Goncalves) [RHEL-69739]
- rtla/timerlat: Do not set params->user_workload with -U (Luis Claudio R. Goncalves) [RHEL-69739]
- rtla/timerlat: Make timerlat_hist_cpu->*_count unsigned long long (Luis Claudio R. Goncalves) [RHEL-69739]
- rtla/timerlat: Make timerlat_top_cpu->*_count unsigned long long (Luis Claudio R. Goncalves) [RHEL-69739]
- tools/rtla: fix collision with glibc sched_attr/sched_set_attr (Luis Claudio R. Goncalves) [RHEL-69739]
- tools/rtla: drop __NR_sched_getattr (Luis Claudio R. Goncalves) [RHEL-69739]
- rtla: Fix consistency in getopt_long for timerlat_hist (Luis Claudio R. Goncalves) [RHEL-69739]
- rtla: use the definition for stdout fd when calling isatty() (Luis Claudio R. Goncalves) [RHEL-69739]
- x86/cacheinfo: Delete global num_cache_leaves (David Arcari) [RHEL-22703]
- cacheinfo: Allocate memory during CPU hotplug if not done from the primary CPU (David Arcari) [RHEL-22703]

* Tue Dec 17 2024 Jan Stancek <jstancek@redhat.com> [6.12.0-36.el10]
- configs: synchronize CONFIG_HP_ILO between flavors & enable on x86/arm (Charles Mirabile) [RHEL-65590]
- crypto: rng - Fix extrng EFAULT handling (Herbert Xu) [RHEL-70652]
- s390/virtio_ccw: Fix dma_parm pointer not set up (Thomas Huth) [RHEL-69815]
- fsnotify: fix sending inotify event with unexpected filename (Ian Kent) [RHEL-68847]
- Revert "nvme: Return BLK_STS_TARGET if the DNR bit is set" (Benjamin Marzinski) [RHEL-68140]
- Revert "nvme: allow local retry and proper failover for REQ_FAILFAST_TRANSPORT" (Benjamin Marzinski) [RHEL-68140]
- Revert "nvme: decouple basic ANA log page re-read support from native multipathing" (Benjamin Marzinski) [RHEL-68140]
- Revert "nvme: nvme_mpath_init remove multipath check" (Benjamin Marzinski) [RHEL-68140]

* Fri Dec 13 2024 Jan Stancek <jstancek@redhat.com> [6.12.0-35.el10]
- redhat: gating.yaml: drop unstable test (Jan Stancek)
- CI: provide pipelines for automotive variant (Julio Faracco)
- fadump: reserve param area if below boot_mem_top (Mamatha Inamdar) [RHEL-67986]
- powerpc/fadump: allocate memory for additional parameters early (Mamatha Inamdar) [RHEL-67986]
- cpufreq: intel_pstate: Update Balance-performance EPP for Granite Rapids (Steve Best) [RHEL-70009]
- scsi: storvsc: Do not flag MAINTENANCE_IN return of SRB_STATUS_DATA_OVERRUN as an error (Cathy Avery) [RHEL-60525]
- RHEL: disable the btt driver (Jeff Moyer) [RHEL-68504]
- vfio/pci: Properly hide first-in-list PCIe extended capability (Alex Williamson) [RHEL-69745]
- xfs: fix sparse inode limits on runt AG (Pavel Reichl) [RHEL-68542]

* Tue Dec 10 2024 Jan Stancek <jstancek@redhat.com> [6.12.0-34.el10]
- iommu/tegra241-cmdqv: Fix alignment failure at max_n_shift (Jerry Snitselaar) [RHEL-67995]
- crypto: qat - Fix missing destroy_workqueue in adf_init_aer() (Vladis Dronov) [RHEL-23197]
- crypto: qat - Fix typo "accelaration" (Vladis Dronov) [RHEL-23197]
- crypto: qat - Constify struct pm_status_row (Vladis Dronov) [RHEL-23197]
- crypto: qat - remove faulty arbiter config reset (Vladis Dronov) [RHEL-23197]
- crypto: qat - remove unused adf_devmgr_get_first (Vladis Dronov) [RHEL-23197]
- crypto: qat/qat_4xxx - fix off by one in uof_get_name() (Vladis Dronov) [RHEL-23197]
- crypto: qat/qat_420xx - fix off by one in uof_get_name() (Vladis Dronov) [RHEL-23197]
- crypto: qat - remove check after debugfs_create_dir() (Vladis Dronov) [RHEL-23197]
- redhat/kernel.spec.template: Link rtla against in-tree libcpupower (Tomas Glozar) [RHEL-40744]
- rtla: Documentation: Mention --deepest-idle-state (Tomas Glozar) [RHEL-40744]
- rtla/timerlat: Add --deepest-idle-state for hist (Tomas Glozar) [RHEL-40744]
- rtla/timerlat: Add --deepest-idle-state for top (Tomas Glozar) [RHEL-40744]
- rtla/utils: Add idle state disabling via libcpupower (Tomas Glozar) [RHEL-40744]
- rtla: Add optional dependency on libcpupower (Tomas Glozar) [RHEL-40744]
- tools/build: Add libcpupower dependency detection (Tomas Glozar) [RHEL-40744]
- mm/memcg: Free percpu stats memory of dying memcg's (Waiman Long) [RHEL-67445]

* Fri Dec 06 2024 Jan Stancek <jstancek@redhat.com> [6.12.0-33.el10]
- redhat: Re-enable CONFIG_INFINIBAND_VMWARE_PVRDMA for x86 (Vitaly Kuznetsov) [RHEL-41133]
- HID: hyperv: streamline driver probe to avoid devres issues (Vitaly Kuznetsov) [RHEL-67329]
- powerpc: security: Lock down the kernel if booted in secure boot mode (Mamatha Inamdar) [RHEL-57024]

* Mon Dec 02 2024 Jan Stancek <jstancek@redhat.com> [6.12.0-32.el10]
- selftests/bpf: Remove ksyms_weak_lskel test (Artem Savkov) [RHEL-48593]
- redhat/spec: Add libxml2-devel dependency for selftests build (Viktor Malik) [RHEL-48593]
- redhat/spec: Bypass check-rpaths for kselftests/bpf/urandom_read (Viktor Malik) [RHEL-48593]
- redhat/spec: Do not use source fortification for selftests (Viktor Malik) [RHEL-48593]
- redhat/spec: Fix BPF selftests build with PIE (Viktor Malik) [RHEL-48593]
- redhat/spec: Add EXTRA_CXXFLAGS to bpf samples and selftests make (Artem Savkov) [RHEL-48593]
- selftests/bpf: Allow building with extra flags (Viktor Malik) [RHEL-48593]
- selftests/bpf: Disable warnings on unused flags for Clang builds (Viktor Malik) [RHEL-48593]
- bpftool: Prevent setting duplicate _GNU_SOURCE in Makefile (Viktor Malik) [RHEL-48593]

* Mon Nov 25 2024 Jan Stancek <jstancek@redhat.com> [6.12.0-31.el10]
- RHEL-only: mark io_uring tech preview and disable by default (Jeff Moyer) [RHEL-65347]

* Mon Nov 18 2024 Jan Stancek <jstancek@redhat.com> [6.12.0-30.el10]
- Linux 6.12 (Linus Torvalds)
- x86/mm: Fix a kdump kernel failure on SME system when CONFIG_IMA_KEXEC=y (Baoquan He)
- x86/stackprotector: Work around strict Clang TLS symbol requirements (Ard Biesheuvel)
- x86/CPU/AMD: Clear virtualized VMLOAD/VMSAVE on Zen4 client (Mario Limonciello)
- redhat/configs: cleanup CONFIG_DEV_DAX (David Hildenbrand)
- redhat/configs: cleanup CONFIG_TRANSPARENT_HUGEPAGE_MADVISE for Fedora (David Hildenbrand)
- redhat/configs: cleanup CONFIG_TRANSPARENT_HUGEPAGE (David Hildenbrand)
- redhat/configs: enable CONFIG_TRANSPARENT_HUGEPAGE on s390x in Fedora (David Hildenbrand)
- redhat/configs: automotive: Enable j784s4evm am3359 tscadc configs (Joel Slebodnick)
- mm: revert "mm: shmem: fix data-race in shmem_getattr()" (Andrew Morton)
- ocfs2: uncache inode which has failed entering the group (Dmitry Antipov)
- mm: fix NULL pointer dereference in alloc_pages_bulk_noprof (Jinjiang Tu)
- mm, doc: update read_ahead_kb for MADV_HUGEPAGE (Yafang Shao)
- fs/proc/task_mmu: prevent integer overflow in pagemap_scan_get_args() (Dan Carpenter)
- sched/task_stack: fix object_is_on_stack() for KASAN tagged pointers (Qun-Wei Lin)
- crash, powerpc: default to CRASH_DUMP=n on PPC_BOOK3S_32 (Dave Vasilevsky)
- mm/mremap: fix address wraparound in move_page_tables() (Jann Horn)
- tools/mm: fix compile error (Motiejus JakÅ`tys)
- mm, swap: fix allocation and scanning race with swapoff (Kairui Song)
- ARM: fix cacheflush with PAN (Russell King (Oracle))
- ARM: 9435/1: ARM/nommu: Fix typo "absence" (WangYuli)
- ARM: 9434/1: cfi: Fix compilation corner case (Linus Walleij)
- ARM: 9420/1: smp: Fix SMP for xip kernels (Harith G)
- ARM: 9419/1: mm: Fix kernel memory mapping for xip kernels (Harith G)
- Revert "drm/amd/pm: correct the workload setting" (Alex Deucher)
- tracing/ring-buffer: Clear all memory mapped CPU ring buffers on first recording (Steven Rostedt)
- Revert: "ring-buffer: Do not have boot mapped buffers hook to CPU hotplug" (Steven Rostedt)
- drivers: perf: Fix wrong put_cpu() placement (Alexandre Ghiti)
- drm/xe/oa: Fix "Missing outer runtime PM protection" warning (Ashutosh Dixit)
- drm/xe: handle flat ccs during hibernation on igpu (Matthew Auld)
- drm/xe: improve hibernation on igpu (Matthew Auld)
- drm/xe: Restore system memory GGTT mappings (Matthew Brost)
- drm/xe: Ensure all locks released in exec IOCTL (Matthew Brost)
- drm/amd: Fix initialization mistake for NBIO 7.7.0 (Vijendar Mukunda)
- Revert "drm/amd/display: parse umc_info or vram_info based on ASIC" (Alex Deucher)
- drm/amd/display: Fix failure to read vram info due to static BP_RESULT (Hamish Claxton)
- drm/amdgpu: enable GTT fallback handling for dGPUs only (Christian König)
- drm/amdgpu/mes12: correct kiq unmap latency (Jack Xiao)
- drm/amdgpu: fix check in gmc_v9_0_get_vm_pte() (Christian König)
- drm/amd/pm: print pp_dpm_mclk in ascending order on SMU v14.0.0 (Tim Huang)
- drm/amdgpu: Fix video caps for H264 and HEVC encode maximum size (David Rosca)
- drm/amd/display: Adjust VSDB parser for replay feature (Rodrigo Siqueira)
- drm/amd/display: Require minimum VBlank size for stutter optimization (Dillon Varone)
- drm/amd/display: Handle dml allocation failure to avoid crash (Ryan Seto)
- drm/amd/display: Fix Panel Replay not update screen correctly (Tom Chung)
- drm/amd/display: Change some variable name of psr (Tom Chung)
- drm/bridge: tc358768: Fix DSI command tx (Francesco Dolcini)
- drm/vmwgfx: avoid null_ptr_deref in vmw_framebuffer_surface_create_handle (Chen Ridong)
- nouveau/dp: handle retries for AUX CH transfers with GSP. (Dave Airlie)
- nouveau: handle EBUSY and EAGAIN for GSP aux errors. (Dave Airlie)
- nouveau: fw: sync dma after setup is called. (Dave Airlie)
- drm/panthor: Fix handling of partial GPU mapping of BOs (Akash Goel)
- drm/rockchip: vop: Fix a dereferenced before check warning (Andy Yan)
- drm/i915: Grab intel_display from the encoder to avoid potential oopsies (Ville Syrjälä)
- drm/i915/gsc: ARL-H and ARL-U need a newer GSC FW. (Daniele Ceraolo Spurio)
- Revert "RDMA/core: Fix ENODEV error for iWARP test over vlan" (Leon Romanovsky)
- RDMA/bnxt_re: Remove some dead code (Christophe JAILLET)
- RDMA/bnxt_re: Fix some error handling paths in bnxt_re_probe() (Christophe JAILLET)
- mailbox: qcom-cpucp: Mark the irq with IRQF_NO_SUSPEND flag (Sibi Sankar)
- firmware: arm_scmi: Report duplicate opps as firmware bugs (Sibi Sankar)
- firmware: arm_scmi: Skip opp duplicates (Cristian Marussi)
- pmdomain: imx93-blk-ctrl: correct remove path (Peng Fan)
- pmdomain: arm: Use FLAG_DEV_NAME_FW to ensure unique names (Sibi Sankar)
- pmdomain: core: Add GENPD_FLAG_DEV_NAME_FW flag (Sibi Sankar)
- Revert "mmc: dw_mmc: Fix IDMAC operation with pages bigger than 4K" (Aurelien Jarno)
- mmc: sunxi-mmc: Fix A100 compatible description (Andre Przywara)
- ASoC: max9768: Fix event generation for playback mute (Mark Brown)
- ASoC: intel: sof_sdw: add quirk for Dell SKU (Deep Harsora)
- ASoC: audio-graph-card2: Purge absent supplies for device tree nodes (John Watts)
- ALSA: hda/realtek - update set GPIO3 to default for Thinkpad with ALC1318 (Kailang Yang)
- ALSA: hda/realtek: fix mute/micmute LEDs for a HP EliteBook 645 G10 (Maksym Glubokiy)
- ALSA: hda/realtek - Fixed Clevo platform headset Mic issue (Kailang Yang)
- ALSA: usb-audio: Fix Yamaha P-125 Quirk Entry (Eryk Zagorski)
- crypto: mips/crc32 - fix the CRC32C implementation (Eric Biggers)
- sched_ext: ops.cpu_acquire() should be called with SCX_KF_REST (Tejun Heo)
- btrfs: fix incorrect comparison for delayed refs (Josef Bacik)
- redhat/configs: delete renamed CONFIG_MLX5_EN_MACSEC (Michal Schmidt)
- rhel: disable DELL_RBU and cleanup related deps (Peter Robinson)
- crypto: rng - Ensure stdrng is tested before user-space starts (Herbert Xu)
- gitlab-ci: Add CKI_RETRIGGER_PIPELINE (Tales da Aparecida)
- redhat: configs: disable the qla4xxx iSCSI driver (Chris Leech) [RHEL-1242]
- Remove duplicated CONFIGs between automotive and RHEL (Julio Faracco)
- redhat: update self-test data for addition of automotive (Scott Weaver)
- gitlab-ci: enable automotive pipeline (Scott Weaver)
- automotive: move pending configs to automotive/generic (Scott Weaver)
- redhat/configs: change Renesas eMMC driver and dependencies to built-in (Radu Rendec)
- redhat/configs: automotive: Remove automotive specific override CONFIG_OMAP2PLUS_MBOX
- Config enablement of the Renesas R-Car S4 SoC (Radu Rendec) [RHEL-44306]
- redhat/configs: automotive: Enable USB_CDNS3_TI for TI platforms (Andrew Halaney)
- redhat/configs: automotive: Enable j784s4evm SPI configs (Joel Slebodnick)
- redhat/configs: automotive: Enable TPS6594 MFD (Joel Slebodnick)
- redhat/configs: automotive: stop overriding CRYPTO_ECDH (Andrew Halaney)
- redhat/configs: automotive: Enable PCI_J721E (Andrew Halaney)
- redhat/configs: change some TI platform drivers to built-in (Enric Balletbo i Serra)
- redhat/configs: automotive: Enable TI j784s4evm display dependencies (Andrew Halaney)
- redhat/configs: automotive: match ark configs to cs9 main-automotive (Shawn Doherty) [RHEL-35995]
- redhat/configs: automotive: Enable TI's watchdog driver (Andrew Halaney)
- redhat/configs: automotive: Enable TI's UFS controller (Andrew Halaney)
- redhat/configs: automotive: Enable networking on the J784S4EVM (Andrew Halaney) [RHEL-29245]
- Disable unsupported kernel variants for automotive (Don Zickus)
- Disable CONFIG_RTW88_22BU (Don Zickus)
- redhat: Delete CONFIG_EFI_ZBOOT to use the common CONFIG (Julio Faracco)
- redhat: Update automotive SPEC file with new standards (Julio Faracco)
- redhat: Disable WERROR for automotive temporarily (Julio Faracco)
- redhat: Update spec file with automotive macros (Julio Faracco)
- redhat: Add automotive CONFIGs (Julio Faracco)
- net: sched: u32: Add test case for systematic hnode IDR leaks (Alexandre Ferrieux)
- selftests: bonding: add ns multicast group testing (Hangbin Liu)
- bonding: add ns target multicast address to slave device (Hangbin Liu)
- net: ti: icssg-prueth: Fix 1 PPS sync (Meghana Malladi)
- stmmac: dwmac-intel-plat: fix call balance of tx_clk handling routines (Vitalii Mordan)
- net: Make copy_safe_from_sockptr() match documentation (Michal Luczaj)
- net: stmmac: dwmac-mediatek: Fix inverted handling of mediatek,mac-wol (Nícolas F. R. A. Prado)
- ipmr: Fix access to mfc_cache_list without lock held (Breno Leitao)
- samples: pktgen: correct dev to DEV (Wei Fang)
- net: phylink: ensure PHY momentary link-fails are handled (Russell King (Oracle))
- mptcp: pm: use _rcu variant under rcu_read_lock (Matthieu Baerts (NGI0))
- mptcp: hold pm lock when deleting entry (Geliang Tang)
- mptcp: update local address flags when setting it (Geliang Tang)
- net: sched: cls_u32: Fix u32's systematic failure to free IDR entries for hnodes. (Alexandre Ferrieux)
- MAINTAINERS: Re-add cancelled Renesas driver sections (Geert Uytterhoeven)
- Revert "igb: Disable threaded IRQ for igb_msix_other" (Wander Lairson Costa)
- Bluetooth: btintel: Direct exception event to bluetooth stack (Kiran K)
- Bluetooth: hci_core: Fix calling mgmt_device_connected (Luiz Augusto von Dentz)
- virtio/vsock: Improve MSG_ZEROCOPY error handling (Michal Luczaj)
- vsock: Fix sk_error_queue memory leak (Michal Luczaj)
- virtio/vsock: Fix accept_queue memory leak (Michal Luczaj)
- net/mlx5e: Disable loopback self-test on multi-PF netdev (Carolina Jubran)
- net/mlx5e: CT: Fix null-ptr-deref in add rule err flow (Moshe Shemesh)
- net/mlx5e: clear xdp features on non-uplink representors (William Tu)
- net/mlx5e: kTLS, Fix incorrect page refcounting (Dragos Tatulea)
- net/mlx5: fs, lock FTE when checking if active (Mark Bloch)
- net/mlx5: Fix msix vectors to respect platform limit (Parav Pandit)
- net/mlx5: E-switch, unload IB representors when unloading ETH representors (Chiara Meiohas)
- mptcp: cope racing subflow creation in mptcp_rcv_space_adjust (Paolo Abeni)
- mptcp: error out earlier on disconnect (Paolo Abeni)
- net: clarify SO_DEVMEM_DONTNEED behavior in documentation (Mina Almasry)
- net: fix SO_DEVMEM_DONTNEED looping too long (Mina Almasry)
- net: fix data-races around sk->sk_forward_alloc (Wang Liang)
- selftests: net: add netlink-dumps to .gitignore (Jakub Kicinski)
- net: vertexcom: mse102x: Fix tx_bytes calculation (Stefan Wahren)
- sctp: fix possible UAF in sctp_v6_available() (Eric Dumazet)
- selftests: net: add a test for closing a netlink socket ith dump in progress (Jakub Kicinski)
- netlink: terminate outstanding dump on socket close (Jakub Kicinski)
- bcachefs: Fix assertion pop in bch2_ptr_swab() (Kent Overstreet)
- bcachefs: Fix journal_entry_dev_usage_to_text() overrun (Kent Overstreet)
- bcachefs: Allow for unknown key types in backpointers fsck (Kent Overstreet)
- bcachefs: Fix assertion pop in topology repair (Kent Overstreet)
- bcachefs: Fix hidden btree errors when reading roots (Kent Overstreet)
- bcachefs: Fix validate_bset() repair path (Kent Overstreet)
- bcachefs: Fix missing validation for bch_backpointer.level (Kent Overstreet)
- bcachefs: Fix bch_member.btree_bitmap_shift validation (Kent Overstreet)
- bcachefs: bch2_btree_write_buffer_flush_going_ro() (Kent Overstreet)
- cpufreq: intel_pstate: Rearrange locking in hybrid_init_cpu_capacity_scaling() (Rafael J. Wysocki)
- tpm: Disable TPM on tpm2_create_primary() failure (Jarkko Sakkinen)
- tpm: Opt-in in disable PCR integrity protection (Jarkko Sakkinen)
- bpf: Fix mismatched RCU unlock flavour in bpf_out_neigh_v6 (Jiawei Ye)
- bpf: Add sk_is_inet and IS_ICSK check in tls_sw_has_ctx_tx/rx (Zijian Zhang)
- selftests/bpf: Use -4095 as the bad address for bits iterator (Hou Tao)
- LoongArch: Fix AP booting issue in VM mode (Bibo Mao)
- LoongArch: Add WriteCombine shadow mapping in KASAN (Kanglong Wang)
- LoongArch: Disable KASAN if PGDIR_SIZE is too large for cpu_vabits (Huacai Chen)
- LoongArch: Make KASAN work with 5-level page-tables (Huacai Chen)
- LoongArch: Define a default value for VM_DATA_DEFAULT_FLAGS (Yuli Wang)
- LoongArch: Fix early_numa_add_cpu() usage for FDT systems (Huacai Chen)
- LoongArch: For all possible CPUs setup logical-physical CPU mapping (Huacai Chen)
- mm: swapfile: fix cluster reclaim work crash on rotational devices (Johannes Weiner)
- selftests: hugetlb_dio: fixup check for initial conditions to skip in the start (Donet Tom)
- mm/thp: fix deferred split queue not partially_mapped: fix (Hugh Dickins)
- mm/gup: avoid an unnecessary allocation call for FOLL_LONGTERM cases (John Hubbard)
- nommu: pass NULL argument to vma_iter_prealloc() (Hajime Tazaki)
- ocfs2: fix UBSAN warning in ocfs2_verify_volume() (Dmitry Antipov)
- nilfs2: fix null-ptr-deref in block_dirty_buffer tracepoint (Ryusuke Konishi)
- nilfs2: fix null-ptr-deref in block_touch_buffer tracepoint (Ryusuke Konishi)
- mm: page_alloc: move mlocked flag clearance into free_pages_prepare() (Roman Gushchin)
- mm: count zeromap read and set for swapout and swapin (Barry Song)
- Fedora configs for 6.12 (Justin M. Forbes)
- redhat/configs: Add CONFIG_CRYPTO_HMAC_S390 config (Mete Durlu) [RHEL-50799]
- vdpa/mlx5: Fix PA offset with unaligned starting iotlb map (Si-Wei Liu)
- KVM: VMX: Bury Intel PT virtualization (guest/host mode) behind CONFIG_BROKEN (Sean Christopherson)
- KVM: x86: Unconditionally set irr_pending when updating APICv state (Sean Christopherson)
- kvm: svm: Fix gctx page leak on invalid inputs (Dionna Glaze)
- KVM: selftests: use X86_MEMTYPE_WB instead of VMX_BASIC_MEM_TYPE_WB (John Sperbeck)
- KVM: SVM: Propagate error from snp_guest_req_init() to userspace (Sean Christopherson)
- KVM: nVMX: Treat vpid01 as current if L2 is active, but with VPID disabled (Sean Christopherson)
- KVM: selftests: Don't force -march=x86-64-v2 if it's unsupported (Sean Christopherson)
- KVM: selftests: Disable strict aliasing (Sean Christopherson)
- KVM: selftests: fix unintentional noop test in guest_memfd_test.c (Patrick Roy)
- KVM: selftests: memslot_perf_test: increase guest sync timeout (Maxim Levitsky)
- dm-cache: fix warnings about duplicate slab caches (Mikulas Patocka)
- dm-bufio: fix warnings about duplicate slab caches (Mikulas Patocka)
- integrity: Use static_assert() to check struct sizes (Gustavo A. R. Silva)
- evm: stop avoidably reading i_writecount in evm_file_release (Mateusz Guzik)
- ima: fix buffer overrun in ima_eventdigest_init_common (Samasth Norway Ananda)
- landlock: Optimize scope enforcement (Mickaël Salaün)
- landlock: Refactor network access mask management (Mickaël Salaün)
- landlock: Refactor filesystem access mask management (Mickaël Salaün)
- samples/landlock: Clarify option parsing behaviour (Matthieu Buffet)
- samples/landlock: Refactor help message (Matthieu Buffet)
- samples/landlock: Fix port parsing in sandboxer (Matthieu Buffet)
- landlock: Fix grammar issues in documentation (Daniel Burgener)
- landlock: Improve documentation of previous limitations (Mickaël Salaün)
- sched_ext: Handle cases where pick_task_scx() is called without preceding balance_scx() (Tejun Heo)
- sched_ext: Update scx_show_state.py to match scx_ops_bypass_depth's new type (Tejun Heo)
- sched_ext: Add a missing newline at the end of an error message (Tejun Heo)
- vdpa/mlx5: Fix error path during device add (Dragos Tatulea)
- vp_vdpa: fix id_table array not null terminated error (Xiaoguang Wang)
- virtio_pci: Fix admin vq cleanup by using correct info pointer (Feng Liu)
- vDPA/ifcvf: Fix pci_read_config_byte() return code handling (Yuan Can)
- Fix typo in vringh_test.c (Shivam Chaudhary)
- vdpa: solidrun: Fix UB bug with devres (Philipp Stanner)
- vsock/virtio: Initialization of the dangling pointer occurring in vsk->trans (Hyunwoo Kim)
- redhat: configs: common: generic: Clean up EM28XX that are masked behind CONFIG_VIDEO_EM28XX (Kate Hsuan)
- redhat/configs: Update powerpc NR_CPUS config (Mamatha Inamdar)
- redhat: use stricter rule for kunit.ko (Jan Stancek)
- filtermod: fix clk kunit test and kunit location (Nico Pache)
- redhat/configs: enable xr_serial on rhel (Desnes Nunes)
- redhat/configs: enable ATH12K for rhel (Jose Ignacio Tornos Martinez)
- Linux 6.12-rc7 (Linus Torvalds)
- clk: qcom: gcc-x1e80100: Fix USB MP SS1 PHY GDSC pwrsts flags (Abel Vesa)
- clk: qcom: gcc-x1e80100: Fix halt_check for pipediv2 clocks (Qiang Yu)
- clk: qcom: clk-alpha-pll: Fix pll post div mask when width is not set (Barnabás Czémán)
- clk: qcom: videocc-sm8350: use HW_CTRL_TRIGGER for vcodec GDSCs (Johan Hovold)
- i2c: designware: do not hold SCL low when I2C_DYNAMIC_TAR_UPDATE is not set (Liu Peibao)
- i2c: muxes: Fix return value check in mule_i2c_mux_probe() (Yang Yingliang)
- filemap: Fix bounds checking in filemap_read() (Trond Myklebust)
- irqchip/gic-v3: Force propagation of the active state with a read-back (Marc Zyngier)
- mailmap: add entry for Thorsten Blum (Thorsten Blum)
- ocfs2: remove entry once instead of null-ptr-dereference in ocfs2_xa_remove() (Andrew Kanner)
- signal: restore the override_rlimit logic (Roman Gushchin)
- fs/proc: fix compile warning about variable 'vmcore_mmap_ops' (Qi Xi)
- ucounts: fix counter leak in inc_rlimit_get_ucounts() (Andrei Vagin)
- selftests: hugetlb_dio: check for initial conditions to skip in the start (Muhammad Usama Anjum)
- mm: fix docs for the kernel parameter ``thp_anon=`` (Maíra Canal)
- mm/damon/core: avoid overflow in damon_feed_loop_next_input() (SeongJae Park)
- mm/damon/core: handle zero schemes apply interval (SeongJae Park)
- mm/damon/core: handle zero {aggregation,ops_update} intervals (SeongJae Park)
- mm/mlock: set the correct prev on failure (Wei Yang)
- objpool: fix to make percpu slot allocation more robust (Masami Hiramatsu (Google))
- mm/page_alloc: keep track of free highatomic (Yu Zhao)
- mm: resolve faulty mmap_region() error path behaviour (Lorenzo Stoakes)
- mm: refactor arch_calc_vm_flag_bits() and arm64 MTE handling (Lorenzo Stoakes)
- mm: refactor map_deny_write_exec() (Lorenzo Stoakes)
- mm: unconditionally close VMAs on error (Lorenzo Stoakes)
- mm: avoid unsafe VMA hook invocation when error arises on mmap hook (Lorenzo Stoakes)
- mm/thp: fix deferred split unqueue naming and locking (Hugh Dickins)
- mm/thp: fix deferred split queue not partially_mapped (Hugh Dickins)
- USB: serial: qcserial: add support for Sierra Wireless EM86xx (Jack Wu)
- USB: serial: io_edgeport: fix use after free in debug printk (Dan Carpenter)
- USB: serial: option: add Quectel RG650V (Benoît Monin)
- USB: serial: option: add Fibocom FG132 0x0112 composition (Reinhard Speyerer)
- thunderbolt: Fix connection issue with Pluggable UD-4VPD dock (Mika Westerberg)
- thunderbolt: Add only on-board retimers when !CONFIG_USB4_DEBUGFS_MARGINING (Mika Westerberg)
- usb: typec: fix potential out of bounds in ucsi_ccg_update_set_new_cam_cmd() (Dan Carpenter)
- usb: dwc3: fix fault at system suspend if device was already runtime suspended (Roger Quadros)
- usb: typec: qcom-pmic: init value of hdr_len/txbuf_len earlier (Rex Nie)
- usb: musb: sunxi: Fix accessing an released usb phy (Zijun Hu)
- staging: vchiq_arm: Use devm_kzalloc() for drv_mgmt allocation (Umang Jain)
- staging: vchiq_arm: Use devm_kzalloc() for vchiq_arm_state allocation (Umang Jain)
- redhat: configs: rhel: generic: x86: Enable IPU6 based MIPI cameras (Kate Hsuan)
- os-build: enable CONFIG_SCHED_CLASS_EXT for RHEL (Phil Auld)
- NFSD: Fix READDIR on NFSv3 mounts of ext4 exports (Chuck Lever)
- smb: client: Fix use-after-free of network namespace. (Kuniyuki Iwashima)
- nvme/host: Fix RCU list traversal to use SRCU primitive (Breno Leitao)
- thermal/of: support thermal zones w/o trips subnode (Icenowy Zheng)
- tools/lib/thermal: Remove the thermal.h soft link when doing make clean (zhang jiao)
- tools/lib/thermal: Fix sampling handler context ptr (Emil Dahl Juhl)
- thermal/drivers/qcom/lmh: Remove false lockdep backtrace (Dmitry Baryshkov)
- cpufreq: intel_pstate: Update asym capacity for CPUs that were offline initially (Rafael J. Wysocki)
- cpufreq: intel_pstate: Clear hybrid_max_perf_cpu before driver registration (Rafael J. Wysocki)
- ACPI: processor: Move arch_init_invariance_cppc() call later (Mario Limonciello)
- ksmbd: check outstanding simultaneous SMB operations (Namjae Jeon)
- ksmbd: fix slab-use-after-free in smb3_preauth_hash_rsp (Namjae Jeon)
- ksmbd: fix slab-use-after-free in ksmbd_smb2_session_create (Namjae Jeon)
- ksmbd: Fix the missing xa_store error check (Jinjie Ruan)
- scsi: ufs: core: Start the RTC update work later (Bart Van Assche)
- scsi: sd_zbc: Use kvzalloc() to allocate REPORT ZONES buffer (Johannes Thumshirn)
- drm/xe: Stop accumulating LRC timestamp on job_free (Lucas De Marchi)
- drm/xe/pf: Fix potential GGTT allocation leak (Michal Wajdeczko)
- drm/xe: Drop VM dma-resv lock on xe_sync_in_fence_get failure in exec IOCTL (Matthew Brost)
- drm/xe: Fix possible exec queue leak in exec IOCTL (Matthew Brost)
- drm/xe/guc/tlb: Flush g2h worker in case of tlb timeout (Nirmoy Das)
- drm/xe/ufence: Flush xe ordered_wq in case of ufence timeout (Nirmoy Das)
- drm/xe: Move LNL scheduling WA to xe_device.h (Nirmoy Das)
- drm/xe: Use the filelist from drm for ccs_mode change (Balasubramani Vivekanandan)
- drm/xe: Set mask bits for CCS_MODE register (Balasubramani Vivekanandan)
- drm/panthor: Be stricter about IO mapping flags (Jann Horn)
- drm/panthor: Lock XArray when getting entries for the VM (Liviu Dudau)
- drm: panel-orientation-quirks: Make Lenovo Yoga Tab 3 X90F DMI match less strict (Hans de Goede)
- drm/imagination: Break an object reference loop (Brendan King)
- drm/imagination: Add a per-file PVR context list (Brendan King)
- drm/amdgpu: add missing size check in amdgpu_debugfs_gprwave_read() (Alex Deucher)
- drm/amdgpu: Adjust debugfs eviction and IB access permissions (Alex Deucher)
- drm/amdgpu: Adjust debugfs register access permissions (Alex Deucher)
- drm/amdgpu: Fix DPX valid mode check on GC 9.4.3 (Lijo Lazar)
- drm/amd/pm: correct the workload setting (Kenneth Feng)
- drm/amd/pm: always pick the pptable from IFWI (Kenneth Feng)
- drm/amdgpu: prevent NULL pointer dereference if ATIF is not supported (Antonio Quartulli)
- drm/amd/display: parse umc_info or vram_info based on ASIC (Aurabindo Pillai)
- drm/amd/display: Fix brightness level not retained over reboot (Tom Chung)
- ASoC: SOF: sof-client-probes-ipc4: Set param_size extension bits (Jyri Sarha)
- ASoC: stm: Prevent potential division by zero in stm32_sai_get_clk_div() (Luo Yifan)
- ASoC: stm: Prevent potential division by zero in stm32_sai_mclk_round_rate() (Luo Yifan)
- ASoC: amd: yc: Support dmic on another model of Lenovo Thinkpad E14 Gen 6 (Markus Petri)
- ASoC: SOF: amd: Fix for incorrect DMA ch status register offset (Venkata Prasad Potturu)
- ASoC: amd: yc: fix internal mic on Xiaomi Book Pro 14 2022 (Mingcong Bai)
- ASoC: stm32: spdifrx: fix dma channel release in stm32_spdifrx_remove (Amelie Delaunay)
- MAINTAINERS: Generic Sound Card section (Kuninori Morimoto)
- ASoC: tas2781: Add new driver version for tas2563 & tas2781 qfn chip (Shenghao Ding)
- ALSA: usb-audio: Add quirk for HP 320 FHD Webcam (Takashi Iwai)
- ALSA: firewire-lib: fix return value on fail in amdtp_tscm_init() (Murad Masimov)
- ALSA: ump: Don't enumeration invalid groups for legacy rawmidi (Takashi Iwai)
- Revert "ALSA: hda/conexant: Mute speakers at suspend / shutdown" (Jarosław Janik)
- media: videobuf2-core: copy vb planes unconditionally (Tudor Ambarus)
- media: dvbdev: fix the logic when DVB_DYNAMIC_MINORS is not set (Mauro Carvalho Chehab)
- media: vivid: fix buffer overwrite when using > 32 buffers (Hans Verkuil)
- media: pulse8-cec: fix data timestamp at pulse8_setup() (Mauro Carvalho Chehab)
- media: cec: extron-da-hd-4k-plus: don't use -1 as an error code (Mauro Carvalho Chehab)
- media: stb0899_algo: initialize cfr before using it (Mauro Carvalho Chehab)
- media: adv7604: prevent underflow condition when reporting colorspace (Mauro Carvalho Chehab)
- media: cx24116: prevent overflows on SNR calculus (Mauro Carvalho Chehab)
- media: ar0521: don't overflow when checking PLL values (Mauro Carvalho Chehab)
- media: s5p-jpeg: prevent buffer overflows (Mauro Carvalho Chehab)
- media: av7110: fix a spectre vulnerability (Mauro Carvalho Chehab)
- media: mgb4: protect driver against spectre (Mauro Carvalho Chehab)
- media: dvb_frontend: don't play tricks with underflow values (Mauro Carvalho Chehab)
- media: dvbdev: prevent the risk of out of memory access (Mauro Carvalho Chehab)
- media: v4l2-tpg: prevent the risk of a division by zero (Mauro Carvalho Chehab)
- media: v4l2-ctrls-api: fix error handling for v4l2_g_ctrl() (Mauro Carvalho Chehab)
- media: dvb-core: add missing buffer index check (Hans Verkuil)
- mm/slab: fix warning caused by duplicate kmem_cache creation in kmem_buckets_create (Koichiro Den)
- btrfs: fix the length of reserved qgroup to free (Haisu Wang)
- btrfs: reinitialize delayed ref list after deleting it from the list (Filipe Manana)
- btrfs: fix per-subvolume RO/RW flags with new mount API (Qu Wenruo)
- bcachefs: Fix UAF in __promote_alloc() error path (Kent Overstreet)
- bcachefs: Change OPT_STR max to be 1 less than the size of choices array (Piotr Zalewski)
- bcachefs: btree_cache.freeable list fixes (Kent Overstreet)
- bcachefs: check the invalid parameter for perf test (Hongbo Li)
- bcachefs: add check NULL return of bio_kmalloc in journal_read_bucket (Pei Xiao)
- bcachefs: Ensure BCH_FS_may_go_rw is set before exiting recovery (Kent Overstreet)
- bcachefs: Fix topology errors on split after merge (Kent Overstreet)
- bcachefs: Ancient versions with bad bkey_formats are no longer supported (Kent Overstreet)
- bcachefs: Fix error handling in bch2_btree_node_prefetch() (Kent Overstreet)
- bcachefs: Fix null ptr deref in bucket_gen_get() (Kent Overstreet)
- arm64: Kconfig: Make SME depend on BROKEN for now (Mark Rutland)
- arm64: smccc: Remove broken support for SMCCCv1.3 SVE discard hint (Mark Rutland)
- arm64/sve: Discard stale CPU state when handling SVE traps (Mark Brown)
- KVM: PPC: Book3S HV: Mask off LPCR_MER for a vCPU before running it to avoid spurious interrupts (Gautam Menghani)
- Fedora 6.12 configs part 1 (Justin M. Forbes)
- MAINTAINERS: update AMD SPI maintainer (Raju Rangoju)
- regulator: rk808: Add apply_bit for BUCK3 on RK809 (Mikhail Rudenko)
- regulator: rtq2208: Fix uninitialized use of regulator_config (ChiYuan Huang)
- drivers: net: ionic: add missed debugfs cleanup to ionic_probe() error path (Wentao Liang)
- net/smc: do not leave a dangling sk pointer in __smc_create() (Eric Dumazet)
- rxrpc: Fix missing locking causing hanging calls (David Howells)
- net/smc: Fix lookup of netdev by using ib_device_get_netdev() (Wenjia Zhang)
- netfilter: nf_tables: wait for rcu grace period on net_device removal (Pablo Neira Ayuso)
- net: arc: rockchip: fix emac mdio node support (Johan Jonker)
- net: arc: fix the device for dma_map_single/dma_unmap_single (Johan Jonker)
- virtio_net: Update rss when set queue (Philo Lu)
- virtio_net: Sync rss config to device when virtnet_probe (Philo Lu)
- virtio_net: Add hash_key_length check (Philo Lu)
- virtio_net: Support dynamic rss indirection table size (Philo Lu)
- net: stmmac: Fix unbalanced IRQ wake disable warning on single irq case (Nícolas F. R. A. Prado)
- net: vertexcom: mse102x: Fix possible double free of TX skb (Stefan Wahren)
- e1000e: Remove Meteor Lake SMBUS workarounds (Vitaly Lifshits)
- i40e: fix race condition by adding filter's intermediate sync state (Aleksandr Loktionov)
- idpf: fix idpf_vc_core_init error path (Pavan Kumar Linga)
- idpf: avoid vport access in idpf_get_link_ksettings (Pavan Kumar Linga)
- ice: change q_index variable type to s16 to store -1 value (Mateusz Polchlopek)
- ice: Fix use after free during unload with ports in bridge (Marcin Szycik)
- mptcp: use sock_kfree_s instead of kfree (Geliang Tang)
- mptcp: no admin perm to list endpoints (Matthieu Baerts (NGI0))
- net: phy: ti: add PHY_RST_AFTER_CLK_EN flag (Diogo Silva)
- net: ethernet: ti: am65-cpsw: fix warning in am65_cpsw_nuss_remove_rx_chns() (Roger Quadros)
- net: ethernet: ti: am65-cpsw: Fix multi queue Rx on J7 (Roger Quadros)
- net: hns3: fix kernel crash when uninstalling driver (Peiyang Wang)
- Revert "Merge branch 'there-are-some-bugfix-for-the-hns3-ethernet-driver'" (Jakub Kicinski)
- can: mcp251xfd: mcp251xfd_get_tef_len(): fix length calculation (Marc Kleine-Budde)
- can: mcp251xfd: mcp251xfd_ring_alloc(): fix coalescing configuration when switching CAN modes (Marc Kleine-Budde)
- can: rockchip_canfd: Drop obsolete dependency on COMPILE_TEST (Jean Delvare)
- can: rockchip_canfd: CAN_ROCKCHIP_CANFD should depend on ARCH_ROCKCHIP (Geert Uytterhoeven)
- can: c_can: fix {rx,tx}_errors statistics (Dario Binacchi)
- can: m_can: m_can_close(): don't call free_irq() for IRQ-less devices (Marc Kleine-Budde)
- can: {cc770,sja1000}_isa: allow building on x86_64 (Thomas Mühlbacher)
- can: j1939: fix error in J1939 documentation. (Alexander Hölzl)
- net: xilinx: axienet: Enqueue Tx packets in dql before dmaengine starts (Suraj Gupta)
- MAINTAINERS: Remove self from DSA entry (Florian Fainelli)
- net: enetc: allocate vf_state during PF probes (Wei Fang)
- sctp: properly validate chunk size in sctp_sf_ootb() (Xin Long)
- net: wwan: t7xx: Fix off-by-one error in t7xx_dpmaif_rx_buf_alloc() (Jinjie Ruan)
- dt-bindings: net: xlnx,axi-ethernet: Correct phy-mode property value (Suraj Gupta)
- net: dpaa_eth: print FD status in CPU endianness in dpaa_eth_fd tracepoint (Vladimir Oltean)
- net: enetc: set MAC address to the VF net_device (Wei Fang)
- MAINTAINERS: add self as reviewer for AXI PWM GENERATOR (Trevor Gamblin)
- pwm: imx-tpm: Use correct MODULO value for EPWM mode (Erik Schumacher)
- proc/softirqs: replace seq_printf with seq_put_decimal_ull_width (David Wang)
- nfs: avoid i_lock contention in nfs_clear_invalid_mapping (Mike Snitzer)
- nfs_common: fix localio to cope with racing nfs_local_probe() (Mike Snitzer)
- NFS: Further fixes to attribute delegation a/mtime changes (Trond Myklebust)
- NFS: Fix attribute delegation behaviour on exclusive create (Trond Myklebust)
- nfs: Fix KMSAN warning in decode_getfattr_attrs() (Roberto Sassu)
- NFSv3: only use NFS timeout for MOUNT when protocols are compatible (NeilBrown)
- sunrpc: handle -ENOTCONN in xs_tcp_setup_socket() (NeilBrown)
- KEYS: trusted: dcp: fix NULL dereference in AEAD crypto operation (David Gstir)
- security/keys: fix slab-out-of-bounds in key_task_permission (Chen Ridong)
- tracing/selftests: Add tracefs mount options test (Kalesh Singh)
- tracing: Document tracefs gid mount option (Kalesh Singh)
- tracing: Fix tracefs mount options (Kalesh Singh)
- platform/x86: thinkpad_acpi: Fix for ThinkPad's with ECFW showing incorrect fan speed (Vishnu Sankar)
- platform/x86: ideapad-laptop: add missing Ideapad Pro 5 fn keys (Renato Caldas)
- platform/x86: dell-wmi-base: Handle META key Lock/Unlock events (Kurt Borja)
- platform/x86: dell-smbios-base: Extends support to Alienware products (Kurt Borja)
- platform/x86/amd/pmc: Detect when STB is not available (Corey Hickey)
- platform/x86/amd/pmf: Add SMU metrics table support for 1Ah family 60h model (Shyam Sundar S K)
- dm cache: fix potential out-of-bounds access on the first resume (Ming-Hung Tsai)
- dm cache: optimize dirty bit checking with find_next_bit when resizing (Ming-Hung Tsai)
- dm cache: fix out-of-bounds access to the dirty bitset when resizing (Ming-Hung Tsai)
- dm cache: fix flushing uninitialized delayed_work on cache_ctr error (Ming-Hung Tsai)
- dm cache: correct the number of origin blocks to match the target length (Ming-Hung Tsai)
- dm-verity: don't crash if panic_on_corruption is not selected (Mikulas Patocka)
- dm-unstriped: cast an operand to sector_t to prevent potential uint32_t overflow (Zichen Xie)
- dm: fix a crash if blk_alloc_disk fails (Mikulas Patocka)
- HID: core: zero-initialize the report buffer (Jiri Kosina)
- redhat: set new gcov configs (Jan Stancek)
- Don't ignore gitkeep files for ark-infra (Don Zickus)
- redhat/kernel.spec: don't clear entire libdir when building tools (Jan Stancek)
- redhat/configs: enable usbip for rhel (Jose Ignacio Tornos Martinez)
- redhat: create 'crashkernel=' addons for UKI (Vitaly Kuznetsov)
- redhat: avoid superfluous quotes in UKI cmdline addones (Vitaly Kuznetsov)
- fedora: arm: updates for 6.12 (Peter Robinson)
- soc: qcom: pmic_glink: Handle GLINK intent allocation rejections (Bjorn Andersson)
- rpmsg: glink: Handle rejected intent request better (Bjorn Andersson)
- soc: qcom: socinfo: fix revision check in qcom_socinfo_probe() (Manikanta Mylavarapu)
- firmware: qcom: scm: Return -EOPNOTSUPP for unsupported SHM bridge enabling (Qingqing Zhou)
- EDAC/qcom: Make irq configuration optional (Rajendra Nayak)
- firmware: qcom: scm: fix a NULL-pointer dereference (Bartosz Golaszewski)
- firmware: qcom: scm: suppress download mode error (Johan Hovold)
- soc: qcom: Add check devm_kasprintf() returned value (Charles Han)
- MAINTAINERS: Qualcomm SoC: Match reserved-memory bindings (Simon Horman)
- arm64: dts: qcom: x1e80100: fix PCIe5 interconnect (Johan Hovold)
- arm64: dts: qcom: x1e80100: fix PCIe4 interconnect (Johan Hovold)
- arm64: dts: qcom: x1e80100: Fix up BAR spaces (Konrad Dybcio)
- arm64: dts: qcom: x1e80100-qcp: fix nvme regulator boot glitch (Johan Hovold)
- arm64: dts: qcom: x1e80100-microsoft-romulus: fix nvme regulator boot glitch (Johan Hovold)
- arm64: dts: qcom: x1e80100-yoga-slim7x: fix nvme regulator boot glitch (Johan Hovold)
- arm64: dts: qcom: x1e80100-vivobook-s15: fix nvme regulator boot glitch (Johan Hovold)
- arm64: dts: qcom: x1e80100-crd: fix nvme regulator boot glitch (Johan Hovold)
- arm64: dts: qcom: x1e78100-t14s: fix nvme regulator boot glitch (Johan Hovold)
- arm64: dts: qcom: x1e80100-crd Rename "Twitter" to "Tweeter" (Maya Matuszczyk)
- arm64: dts: qcom: x1e80100: Fix PCIe 6a lanes description (Abel Vesa)
- arm64: dts: qcom: sm8450 fix PIPE clock specification for pcie1 (Dmitry Baryshkov)
- arm64: dts: qcom: x1e80100: Add Broadcast_AND region in LLCC block (Abel Vesa)
- arm64: dts: qcom: x1e80100: fix PCIe5 PHY clocks (Johan Hovold)
- arm64: dts: qcom: x1e80100: fix PCIe4 and PCIe6a PHY clocks (Johan Hovold)
- arm64: dts: qcom: msm8939: revert use of APCS mbox for RPM (Fabien Parent)
- firmware: arm_scmi: Use vendor string in max-rx-timeout-ms (Cristian Marussi)
- dt-bindings: firmware: arm,scmi: Add missing vendor string (Cristian Marussi)
- firmware: arm_scmi: Reject clear channel request on A2P (Cristian Marussi)
- firmware: arm_scmi: Fix slab-use-after-free in scmi_bus_notifier() (Xinqi Zhang)
- MAINTAINERS: invert Misc RISC-V SoC Support's pattern (Conor Dooley)
- riscv: dts: starfive: Update ethernet phy0 delay parameter values for Star64 (E Shattow)
- riscv: dts: starfive: disable unused csi/camss nodes (Conor Dooley)
- firmware: microchip: auto-update: fix poll_complete() to not report spurious timeout errors (Conor Dooley)
- arm64: dts: rockchip: Correct GPIO polarity on brcm BT nodes (Diederik de Haas)
- arm64: dts: rockchip: Drop invalid clock-names from es8388 codec nodes (Cristian Ciocaltea)
- ARM: dts: rockchip: Fix the realtek audio codec on rk3036-kylin (Heiko Stuebner)
- ARM: dts: rockchip: Fix the spi controller on rk3036 (Heiko Stuebner)
- ARM: dts: rockchip: drop grf reference from rk3036 hdmi (Heiko Stuebner)
- ARM: dts: rockchip: fix rk3036 acodec node (Heiko Stuebner)
- arm64: dts: rockchip: remove orphaned pinctrl-names from pinephone pro (Heiko Stuebner)
- arm64: dts: rockchip: remove num-slots property from rk3328-nanopi-r2s-plus (Heiko Stuebner)
- arm64: dts: rockchip: Fix LED triggers on rk3308-roc-cc (Heiko Stuebner)
- arm64: dts: rockchip: Remove #cooling-cells from fan on Theobroma lion (Heiko Stuebner)
- arm64: dts: rockchip: Remove undocumented supports-emmc property (Heiko Stuebner)
- arm64: dts: rockchip: Fix bluetooth properties on Rock960 boards (Heiko Stuebner)
- arm64: dts: rockchip: Fix bluetooth properties on rk3566 box demo (Heiko Stuebner)
- arm64: dts: rockchip: Drop regulator-init-microvolt from two boards (Heiko Stuebner)
- arm64: dts: rockchip: fix i2c2 pinctrl-names property on anbernic-rg353p/v (Heiko Stuebner)
- arm64: dts: rockchip: Fix reset-gpios property on brcm BT nodes (Diederik de Haas)
- arm64: dts: rockchip: Fix wakeup prop names on PineNote BT node (Diederik de Haas)
- arm64: dts: rockchip: Remove hdmi's 2nd interrupt on rk3328 (Diederik de Haas)
- arm64: dts: rockchip: Designate Turing RK1's system power controller (Sam Edwards)
- arm64: dts: rockchip: Start cooling maps numbering from zero on ROCK 5B (Dragan Simic)
- arm64: dts: rockchip: Move L3 cache outside CPUs in RK3588(S) SoC dtsi (Dragan Simic)
- arm64: dts: rockchip: Fix rt5651 compatible value on rk3399-sapphire-excavator (Geert Uytterhoeven)
- arm64: dts: rockchip: Fix rt5651 compatible value on rk3399-eaidk-610 (Geert Uytterhoeven)
- riscv: dts: Replace deprecated snps,nr-gpios property for snps,dw-apb-gpio-port devices (Uwe Kleine-König)
- arm64: dts: imx8mp-phyboard-pollux: Set Video PLL1 frequency to 506.8 MHz (Marek Vasut)
- arm64: dts: imx8mp: correct sdhc ipg clk (Peng Fan)
- arm64: dts: imx8mp-skov-revb-mi1010ait-1cp1: Assign "media_isp" clock rate (Liu Ying)
- arm64: dts: imx8: Fix lvds0 device tree (Diogo Silva)
- arm64: dts: imx8ulp: correct the flexspi compatible string (Haibo Chen)
- arm64: dts: imx8-ss-vpu: Fix imx8qm VPU IRQs (Alexander Stein)
- mmc: sdhci-pci-gli: GL9767: Fix low power mode in the SD Express process (Ben Chuang)
- mmc: sdhci-pci-gli: GL9767: Fix low power mode on the set clock function (Ben Chuang)
- tpm: Lock TPM chip in tpm_pm_suspend() first (Jarkko Sakkinen)
- Make setting of cma_pernuma tech preview (Chris von Recklinghausen) [RHEL-59621]
- gitlab-ci: provide consistent kcidb_tree_name (Michael Hofmann)
- Linux 6.12-rc6 (Linus Torvalds)
- mm: multi-gen LRU: use {ptep,pmdp}_clear_young_notify() (Yu Zhao)
- mm: multi-gen LRU: remove MM_LEAF_OLD and MM_NONLEAF_TOTAL stats (Yu Zhao)
- mm, mmap: limit THP alignment of anonymous mappings to PMD-aligned sizes (Vlastimil Babka)
- mm: shrinker: avoid memleak in alloc_shrinker_info (Chen Ridong)
- .mailmap: update e-mail address for Eugen Hristev (Eugen Hristev)
- vmscan,migrate: fix page count imbalance on node stats when demoting pages (Gregory Price)
- mailmap: update Jarkko's email addresses (Jarkko Sakkinen)
- mm: allow set/clear page_type again (Yu Zhao)
- nilfs2: fix potential deadlock with newly created symlinks (Ryusuke Konishi)
- Squashfs: fix variable overflow in squashfs_readpage_block (Phillip Lougher)
- kasan: remove vmalloc_percpu test (Andrey Konovalov)
- tools/mm: -Werror fixes in page-types/slabinfo (Wladislav Wiebe)
- mm, swap: avoid over reclaim of full clusters (Kairui Song)
- mm: fix PSWPIN counter for large folios swap-in (Barry Song)
- mm: avoid VM_BUG_ON when try to map an anon large folio to zero page. (Zi Yan)
- mm/codetag: fix null pointer check logic for ref and tag (Hao Ge)
- mm/gup: stop leaking pinned pages in low memory conditions (John Hubbard)
- phy: tegra: xusb: Add error pointer check in xusb.c (Dipendra Khadka)
- dt-bindings: phy: qcom,sc8280xp-qmp-pcie-phy: Fix X1E80100 resets entries (Abel Vesa)
- phy: freescale: imx8m-pcie: Do CMN_RST just before PHY PLL lock check (Richard Zhu)
- phy: phy-rockchip-samsung-hdptx: Depend on CONFIG_COMMON_CLK (Cristian Ciocaltea)
- phy: ti: phy-j721e-wiz: fix usxgmii configuration (Siddharth Vadapalli)
- phy: starfive: jh7110-usb: Fix link configuration to controller (Jan Kiszka)
- phy: qcom: qmp-pcie: drop bogus x1e80100 qref supplies (Johan Hovold)
- phy: qcom: qmp-combo: move driver data initialisation earlier (Johan Hovold)
- phy: qcom: qmp-usbc: fix NULL-deref on runtime suspend (Johan Hovold)
- phy: qcom: qmp-usb-legacy: fix NULL-deref on runtime suspend (Johan Hovold)
- phy: qcom: qmp-usb: fix NULL-deref on runtime suspend (Johan Hovold)
- dt-bindings: phy: qcom,sc8280xp-qmp-pcie-phy: add missing x1e80100 pipediv2 clocks (Johan Hovold)
- phy: usb: disable COMMONONN for dual mode (Justin Chen)
- phy: cadence: Sierra: Fix offset of DEQ open eye algorithm control register (Bartosz Wawrzyniak)
- phy: usb: Fix missing elements in BCM4908 USB init array (Sam Edwards)
- dmaengine: ti: k3-udma: Set EOP for all TRs in cyclic BCDMA transfer (Jai Luthra)
- dmaengine: sh: rz-dmac: handle configs where one address is zero (Wolfram Sang)
- Revert "driver core: Fix uevent_show() vs driver detach race" (Greg Kroah-Hartman)
- usb: typec: tcpm: restrict SNK_WAIT_CAPABILITIES_TIMEOUT transitions to non self-powered devices (Amit Sunil Dhamne)
- usb: phy: Fix API devm_usb_put_phy() can not release the phy (Zijun Hu)
- usb: typec: use cleanup facility for 'altmodes_node' (Javier Carrasco)
- usb: typec: fix unreleased fwnode_handle in typec_port_register_altmodes() (Javier Carrasco)
- usb: typec: qcom-pmic-typec: fix missing fwnode removal in error path (Javier Carrasco)
- usb: typec: qcom-pmic-typec: use fwnode_handle_put() to release fwnodes (Javier Carrasco)
- usb: acpi: fix boot hang due to early incorrect 'tunneled' USB3 device links (Mathias Nyman)
- Revert "usb: dwc2: Skip clock gating on Broadcom SoCs" (Stefan Wahren)
- xhci: Fix Link TRB DMA in command ring stopped completion event (Faisal Hassan)
- xhci: Use pm_runtime_get to prevent RPM on unsupported systems (Basavaraj Natikar)
- usbip: tools: Fix detach_port() invalid port error path (Zongmin Zhou)
- thunderbolt: Honor TMU requirements in the domain when setting TMU mode (Gil Fine)
- thunderbolt: Fix KASAN reported stack out-of-bounds read in tb_retimer_scan() (Mika Westerberg)
- iio: dac: Kconfig: Fix build error for ltc2664 (Jinjie Ruan)
- iio: adc: ad7124: fix division by zero in ad7124_set_channel_odr() (Zicheng Qu)
- staging: iio: frequency: ad9832: fix division by zero in ad9832_calc_freqreg() (Zicheng Qu)
- docs: iio: ad7380: fix supply for ad7380-4 (Julien Stephan)
- iio: adc: ad7380: fix supplies for ad7380-4 (Julien Stephan)
- iio: adc: ad7380: add missing supplies (Julien Stephan)
- iio: adc: ad7380: use devm_regulator_get_enable_read_voltage() (Julien Stephan)
- dt-bindings: iio: adc: ad7380: fix ad7380-4 reference supply (Julien Stephan)
- iio: light: veml6030: fix microlux value calculation (Javier Carrasco)
- iio: gts-helper: Fix memory leaks for the error path of iio_gts_build_avail_scale_table() (Jinjie Ruan)
- iio: gts-helper: Fix memory leaks in iio_gts_build_avail_scale_table() (Jinjie Ruan)
- mei: use kvmalloc for read buffer (Alexander Usyskin)
- MAINTAINERS: add netup_unidvb maintainer (Abylay Ospan)
- Input: fix regression when re-registering input handlers (Dmitry Torokhov)
- Input: adp5588-keys - do not try to disable interrupt 0 (Dmitry Torokhov)
- Input: edt-ft5x06 - fix regmap leak when probe fails (Dmitry Torokhov)
- modpost: fix input MODULE_DEVICE_TABLE() built for 64-bit on 32-bit host (Masahiro Yamada)
- modpost: fix acpi MODULE_DEVICE_TABLE built with mismatched endianness (Masahiro Yamada)
- kconfig: show sub-menu entries even if the prompt is hidden (Masahiro Yamada)
- kbuild: deb-pkg: add pkg.linux-upstream.nokerneldbg build profile (Masahiro Yamada)
- kbuild: deb-pkg: add pkg.linux-upstream.nokernelheaders build profile (Masahiro Yamada)
- kbuild: rpm-pkg: disable kernel-devel package when cross-compiling (Masahiro Yamada)
- sumversion: Fix a memory leak in get_src_version() (Elena Salomatkina)
- x86/amd_nb: Fix compile-testing without CONFIG_AMD_NB (Arnd Bergmann)
- posix-cpu-timers: Clear TICK_DEP_BIT_POSIX_TIMER on clone (Benjamin Segall)
- sched/ext: Fix scx vs sched_delayed (Peter Zijlstra)
- sched: Pass correct scheduling policy to __setscheduler_class (Aboorva Devarajan)
- sched/numa: Fix the potential null pointer dereference in task_numa_work() (Shawn Wang)
- sched: Fix pick_next_task_fair() vs try_to_wake_up() race (Peter Zijlstra)
- perf: Fix missing RCU reader protection in perf_event_clear_cpumask() (Kan Liang)
- irqchip/gic-v4: Correctly deal with set_affinity on lazily-mapped VPEs (Marc Zyngier)
- genirq/msi: Fix off-by-one error in msi_domain_alloc() (Jinjie Ruan)
- redhat/configs: add bootconfig to kernel-tools package (Brian Masney)
- Enable CONFIG_SECURITY_LANDLOCK for RHEL (Zbigniew Jędrzejewski-Szmek) [RHEL-8810]
- rpcrdma: Always release the rpcrdma_device's xa_array (Chuck Lever)
- NFSD: Never decrement pending_async_copies on error (Chuck Lever)
- NFSD: Initialize struct nfsd4_copy earlier (Chuck Lever)
- xfs: streamline xfs_filestream_pick_ag (Christoph Hellwig)
- xfs: fix finding a last resort AG in xfs_filestream_pick_ag (Christoph Hellwig)
- xfs: Reduce unnecessary searches when searching for the best extents (Chi Zhiling)
- xfs: Check for delayed allocations before setting extsize (Ojaswin Mujoo)
- selftests/watchdog-test: Fix system accidentally reset after watchdog-test (Li Zhijian)
- selftests/intel_pstate: check if cpupower is installed (Alessandro Zanni)
- selftests/intel_pstate: fix operand expected error (Alessandro Zanni)
- selftests/mount_setattr: fix idmap_mount_tree_invalid failed to run (zhouyuhang)
- cfi: tweak llvm version for HAVE_CFI_ICALL_NORMALIZE_INTEGERS (Alice Ryhl)
- kbuild: rust: avoid errors with old `rustc`s without LLVM patch version (Miguel Ojeda)
- PCI: Fix pci_enable_acs() support for the ACS quirks (Jason Gunthorpe)
- drm/xe: Don't short circuit TDR on jobs not started (Matthew Brost)
- drm/xe: Add mmio read before GGTT invalidate (Matthew Brost)
- drm/xe/display: Add missing HPD interrupt enabling during non-d3cold RPM resume (Imre Deak)
- drm/xe/display: Separate the d3cold and non-d3cold runtime PM handling (Imre Deak)
- drm/xe: Remove runtime argument from display s/r functions (Maarten Lankhorst)
- dt-bindings: display: mediatek: split: add subschema property constraints (Moudy Ho)
- dt-bindings: display: mediatek: dpi: correct power-domains property (Macpaul Lin)
- drm/mediatek: Fix potential NULL dereference in mtk_crtc_destroy() (Dan Carpenter)
- drm/mediatek: Fix get efuse issue for MT8188 DPTX (Liankun Yang)
- drm/mediatek: Fix color format MACROs in OVL (Hsin-Te Yuan)
- drm/mediatek: Add blend_modes to mtk_plane_init() for different SoCs (Jason-JH.Lin)
- drm/mediatek: ovl: Add blend_modes to driver data (Jason-JH.Lin)
- drm/mediatek: ovl: Remove the color format comment for ovl_fmt_convert() (Jason-JH.Lin)
- drm/mediatek: ovl: Refine ignore_pixel_alpha comment and placement (Jason-JH.Lin)
- drm/mediatek: ovl: Fix XRGB format breakage for blend_modes unsupported SoCs (Jason-JH.Lin)
- drm/amdgpu/smu13: fix profile reporting (Alex Deucher)
- drm/amd/pm: Vangogh: Fix kernel memory out of bounds write (Tvrtko Ursulin)
- Revert "drm/amd/display: update DML2 policy EnhancedPrefetchScheduleAccelerationFinal DCN35" (Ovidiu Bunea)
- drm/tests: hdmi: Fix memory leaks in drm_display_mode_from_cea_vic() (Jinjie Ruan)
- drm/connector: hdmi: Fix memory leak in drm_display_mode_from_cea_vic() (Jinjie Ruan)
- drm/tests: helpers: Add helper for drm_display_mode_from_cea_vic() (Jinjie Ruan)
- drm/panthor: Report group as timedout when we fail to properly suspend (Boris Brezillon)
- drm/panthor: Fail job creation when the group is dead (Boris Brezillon)
- drm/panthor: Fix firmware initialization on systems with a page size > 4k (Boris Brezillon)
- accel/ivpu: Fix NOC firewall interrupt handling (Andrzej Kacprowski)
- drm/sched: Mark scheduler work queues with WQ_MEM_RECLAIM (Matthew Brost)
- drm/tegra: Fix NULL vs IS_ERR() check in probe() (Dan Carpenter)
- cxl/test: Improve init-order fidelity relative to real-world systems (Dan Williams)
- cxl/port: Prevent out-of-order decoder allocation (Dan Williams)
- cxl/port: Fix use-after-free, permit out-of-order decoder shutdown (Dan Williams)
- cxl/acpi: Ensure ports ready at cxl_acpi_probe() return (Dan Williams)
- cxl/port: Fix cxl_bus_rescan() vs bus_rescan_devices() (Dan Williams)
- cxl/port: Fix CXL port initialization order when the subsystem is built-in (Dan Williams)
- cxl/events: Fix Trace DRAM Event Record (Shiju Jose)
- cxl/core: Return error when cxl_endpoint_gather_bandwidth() handles a non-PCI device (Li Zhijian)
- nvme: re-fix error-handling for io_uring nvme-passthrough (Keith Busch)
- nvmet-auth: assign dh_key to NULL after kfree_sensitive (Vitaliy Shevtsov)
- nvme: module parameter to disable pi with offsets (Keith Busch)
- nvme: enhance cns version checking (Keith Busch)
- block: fix queue limits checks in blk_rq_map_user_bvec for real (Christoph Hellwig)
- io_uring/rw: fix missing NOWAIT check for O_DIRECT start write (Jens Axboe)
- ACPI: CPPC: Make rmw_lock a raw_spin_lock (Pierre Gondois)
- gpiolib: fix debugfs dangling chip separator (Johan Hovold)
- gpiolib: fix debugfs newline separators (Johan Hovold)
- gpio: sloppy-logic-analyzer: Check for error code from devm_mutex_init() call (Andy Shevchenko)
- gpio: fix uninit-value in swnode_find_gpio (Suraj Sonawane)
- riscv: vdso: Prevent the compiler from inserting calls to memset() (Alexandre Ghiti)
- riscv: Remove duplicated GET_RM (Chunyan Zhang)
- riscv: Remove unused GENERATING_ASM_OFFSETS (Chunyan Zhang)
- riscv: Use '%%u' to format the output of 'cpu' (WangYuli)
- riscv: Prevent a bad reference count on CPU nodes (Miquel Sabaté Solà)
- riscv: efi: Set NX compat flag in PE/COFF header (Heinrich Schuchardt)
- RISC-V: disallow gcc + rust builds (Conor Dooley)
- riscv: Do not use fortify in early code (Alexandre Ghiti)
- RISC-V: ACPI: fix early_ioremap to early_memremap (Yunhui Cui)
- arm64: signal: Improve POR_EL0 handling to avoid uaccess failures (Kevin Brodsky)
- firmware: arm_sdei: Fix the input parameter of cpuhp_remove_state() (Xiongfeng Wang)
- Revert "kasan: Disable Software Tag-Based KASAN with GCC" (Marco Elver)
- kasan: Fix Software Tag-Based KASAN with GCC (Marco Elver)
- iomap: turn iomap_want_unshare_iter into an inline function (Christoph Hellwig)
- fsdax: dax_unshare_iter needs to copy entire blocks (Darrick J. Wong)
- fsdax: remove zeroing code from dax_unshare_iter (Darrick J. Wong)
- iomap: share iomap_unshare_iter predicate code with fsdax (Darrick J. Wong)
- xfs: don't allocate COW extents when unsharing a hole (Darrick J. Wong)
- iov_iter: fix copy_page_from_iter_atomic() if KMAP_LOCAL_FORCE_MAP (Hugh Dickins)
- autofs: fix thinko in validate_dev_ioctl() (Ian Kent)
- iov_iter: Fix iov_iter_get_pages*() for folio_queue (David Howells)
- afs: Fix missing subdir edit when renamed between parent dirs (David Howells)
- doc: correcting the debug path for cachefiles (Hongbo Li)
- erofs: use get_tree_bdev_flags() to avoid misleading messages (Gao Xiang)
- fs/super.c: introduce get_tree_bdev_flags() (Gao Xiang)
- btrfs: fix defrag not merging contiguous extents due to merged extent maps (Filipe Manana)
- btrfs: fix extent map merging not happening for adjacent extents (Filipe Manana)
- btrfs: fix use-after-free of block device file in __btrfs_free_extra_devids() (Zhihao Cheng)
- btrfs: fix error propagation of split bios (Naohiro Aota)
- MIPS: export __cmpxchg_small() (David Sterba)
- bcachefs: Fix NULL ptr dereference in btree_node_iter_and_journal_peek (Piotr Zalewski)
- bcachefs: fix possible null-ptr-deref in __bch2_ec_stripe_head_get() (Gaosheng Cui)
- bcachefs: Fix deadlock on -ENOSPC w.r.t. partial open buckets (Kent Overstreet)
- bcachefs: Don't filter partial list buckets in open_buckets_to_text() (Kent Overstreet)
- bcachefs: Don't keep tons of cached pointers around (Kent Overstreet)
- bcachefs: init freespace inited bits to 0 in bch2_fs_initialize (Piotr Zalewski)
- bcachefs: Fix unhandled transaction restart in fallocate (Kent Overstreet)
- bcachefs: Fix UAF in bch2_reconstruct_alloc() (Kent Overstreet)
- bcachefs: fix null-ptr-deref in have_stripes() (Jeongjun Park)
- bcachefs: fix shift oob in alloc_lru_idx_fragmentation (Jeongjun Park)
- bcachefs: Fix invalid shift in validate_sb_layout() (Gianfranco Trad)
- RDMA/bnxt_re: synchronize the qp-handle table array (Selvin Xavier)
- RDMA/bnxt_re: Fix the usage of control path spin locks (Selvin Xavier)
- RDMA/mlx5: Round max_rd_atomic/max_dest_rd_atomic up instead of down (Patrisious Haddad)
- RDMA/cxgb4: Dump vendor specific QP details (Leon Romanovsky)
- bpf, test_run: Fix LIVE_FRAME frame update after a page has been recycled (Toke Høiland-Jørgensen)
- selftests/bpf: Add three test cases for bits_iter (Hou Tao)
- bpf: Use __u64 to save the bits in bits iterator (Hou Tao)
- bpf: Check the validity of nr_words in bpf_iter_bits_new() (Hou Tao)
- bpf: Add bpf_mem_alloc_check_size() helper (Hou Tao)
- bpf: Free dynamically allocated bits in bpf_iter_bits_destroy() (Hou Tao)
- bpf: disallow 40-bytes extra stack for bpf_fastcall patterns (Eduard Zingerman)
- selftests/bpf: Add test for trie_get_next_key() (Byeonguk Jeong)
- bpf: Fix out-of-bounds write in trie_get_next_key() (Byeonguk Jeong)
- selftests/bpf: Test with a very short loop (Eduard Zingerman)
- bpf: Force checkpoint when jmp history is too long (Eduard Zingerman)
- bpf: fix filed access without lock (Jiayuan Chen)
- sock_map: fix a NULL pointer dereference in sock_map_link_update_prog() (Cong Wang)
- netfilter: nft_payload: sanitize offset and length before calling skb_checksum() (Pablo Neira Ayuso)
- netfilter: nf_reject_ipv6: fix potential crash in nf_send_reset6() (Eric Dumazet)
- netfilter: Fix use-after-free in get_info() (Dong Chenchen)
- selftests: netfilter: remove unused parameter (Liu Jing)
- Bluetooth: hci: fix null-ptr-deref in hci_read_supported_codecs (Sungwoo Kim)
- net: hns3: fix kernel crash when 1588 is sent on HIP08 devices (Jie Wang)
- net: hns3: fixed hclge_fetch_pf_reg accesses bar space out of bounds issue (Hao Lan)
- net: hns3: initialize reset_timer before hclgevf_misc_irq_init() (Jian Shen)
- net: hns3: don't auto enable misc vector (Jian Shen)
- net: hns3: Resolved the issue that the debugfs query result is inconsistent. (Hao Lan)
- net: hns3: fix missing features due to dev->features configuration too early (Hao Lan)
- net: hns3: fixed reset failure issues caused by the incorrect reset type (Hao Lan)
- net: hns3: add sync command to sync io-pgtable (Jian Shen)
- net: hns3: default enable tx bounce buffer when smmu enabled (Peiyang Wang)
- net: ethernet: mtk_wed: fix path of MT7988 WO firmware (Daniel Golle)
- selftests: forwarding: Add IPv6 GRE remote change tests (Ido Schimmel)
- mlxsw: spectrum_ipip: Fix memory leak when changing remote IPv6 address (Ido Schimmel)
- mlxsw: pci: Sync Rx buffers for device (Amit Cohen)
- mlxsw: pci: Sync Rx buffers for CPU (Amit Cohen)
- mlxsw: spectrum_ptp: Add missing verification before pushing Tx header (Amit Cohen)
- net: skip offload for NETIF_F_IPV6_CSUM if ipv6 header contains extension (Benoît Monin)
- wifi: mac80211: ieee80211_i: Fix memory corruption bug in struct ieee80211_chanctx (Gustavo A. R. Silva)
- wifi: iwlwifi: mvm: fix 6 GHz scan construction (Johannes Berg)
- wifi: cfg80211: clear wdev->cqm_config pointer on free (Johannes Berg)
- mac80211: fix user-power when emulating chanctx (Ben Greear)
- Revert "wifi: iwlwifi: remove retry loops in start" (Emmanuel Grumbach)
- wifi: iwlwifi: mvm: don't add default link in fw restart flow (Emmanuel Grumbach)
- wifi: iwlwifi: mvm: Fix response handling in iwl_mvm_send_recovery_cmd() (Daniel Gabay)
- wifi: iwlwifi: mvm: SAR table alignment (Anjaneyulu)
- wifi: iwlwifi: mvm: Use the sync timepoint API in suspend (Daniel Gabay)
- wifi: iwlwifi: mvm: really send iwl_txpower_constraints_cmd (Miri Korenblit)
- wifi: iwlwifi: mvm: don't leak a link on AP removal (Emmanuel Grumbach)
- net: fix crash when config small gso_max_size/gso_ipv4_max_size (Wang Liang)
- net: usb: qmi_wwan: add Quectel RG650V (Benoît Monin)
- net/sched: sch_api: fix xa_insert() error path in tcf_block_get_ext() (Vladimir Oltean)
- netdevsim: Add trailing zero to terminate the string in nsim_nexthop_bucket_activity_write() (Zichen Xie)
- net/sched: stop qdisc_tree_reduce_backlog on TC_H_ROOT (Pedro Tammela)
- selftests: netfilter: nft_flowtable.sh: make first pass deterministic (Florian Westphal)
- gtp: allow -1 to be specified as file description from userspace (Pablo Neira Ayuso)
- mctp i2c: handle NULL header address (Matt Johnston)
- ipv4: ip_tunnel: Fix suspicious RCU usage warning in ip_tunnel_find() (Ido Schimmel)
- ipv4: ip_tunnel: Fix suspicious RCU usage warning in ip_tunnel_init_flow() (Ido Schimmel)
- ice: fix crash on probe for DPLL enabled E810 LOM (Arkadiusz Kubalewski)
- ice: block SF port creation in legacy mode (Michal Swiatkowski)
- igb: Disable threaded IRQ for igb_msix_other (Wander Lairson Costa)
- net: stmmac: TSO: Fix unbalanced DMA map/unmap for non-paged SKB data (Furong Xu)
- net: stmmac: dwmac4: Fix high address display by updating reg_space[] from register values (Ley Foon Tan)
- usb: add support for new USB device ID 0x17EF:0x3098 for the r8152 driver (Benjamin Große)
- macsec: Fix use-after-free while sending the offloading packet (Jianbo Liu)
- selftests: mptcp: list sysctl data (Matthieu Baerts (NGI0))
- mptcp: init: protect sched with rcu_read_lock (Matthieu Baerts (NGI0))
- docs: networking: packet_mmap: replace dead links with archive.org links (Levi Zim)
- wifi: ath11k: Fix invalid ring usage in full monitor mode (Remi Pommarel)
- wifi: ath10k: Fix memory leak in management tx (Manikanta Pubbisetty)
- wifi: rtlwifi: rtl8192du: Don't claim USB ID 0bda:8171 (Bitterblue Smith)
- wifi: rtw88: Fix the RX aggregation in USB 3 mode (Bitterblue Smith)
- wifi: brcm80211: BRCM_TRACING should depend on TRACING (Geert Uytterhoeven)
- wifi: rtw89: pci: early chips only enable 36-bit DMA on specific PCI hosts (Ping-Ke Shih)
- wifi: mac80211: skip non-uploaded keys in ieee80211_iter_keys (Felix Fietkau)
- wifi: radiotap: Avoid -Wflex-array-member-not-at-end warnings (Gustavo A. R. Silva)
- wifi: mac80211: do not pass a stopped vif to the driver in .get_txpower (Felix Fietkau)
- wifi: mac80211: Convert color collision detection to wiphy work (Remi Pommarel)
- wifi: cfg80211: Add wiphy_delayed_work_pending() (Remi Pommarel)
- wifi: cfg80211: Do not create BSS entries for unsupported channels (Chenming Huang)
- wifi: mac80211: Fix setting txpower with emulate_chanctx (Ben Greear)
- mac80211: MAC80211_MESSAGE_TRACING should depend on TRACING (Geert Uytterhoeven)
- wifi: iwlegacy: Clear stale interrupts before resuming device (Ville Syrjälä)
- wifi: iwlegacy: Fix "field-spanning write" warning in il_enqueue_hcmd() (Ben Hutchings)
- wifi: mt76: do not increase mcu skb refcount if retry is not supported (Felix Fietkau)
- wifi: rtw89: coex: add debug message of link counts on 2/5GHz bands for wl_info v7 (Ping-Ke Shih)
- ALSA: hda/realtek: Fix headset mic on TUXEDO Stellaris 16 Gen6 mb1 (Christoffer Sandberg)
- ALSA: hda/realtek: Fix headset mic on TUXEDO Gemini 17 Gen3 (Christoffer Sandberg)
- ALSA: usb-audio: Add quirks for Dell WD19 dock (Jan Schär)
- ASoC: codecs: wcd937x: relax the AUX PDM watchdog (Alexey Klimov)
- ASoC: codecs: wcd937x: add missing LO Switch control (Alexey Klimov)
- ASoC: dt-bindings: rockchip,rk3308-codec: add port property (Dmitry Yashin)
- ASoC: dapm: fix bounds checker error in dapm_widget_list_create (Aleksei Vetrov)
- ASoC: Intel: sst: Fix used of uninitialized ctx to log an error (Hans de Goede)
- ASoC: cs42l51: Fix some error handling paths in cs42l51_probe() (Christophe JAILLET)
- ASoC: Intel: sst: Support LPE0F28 ACPI HID (Hans de Goede)
- ASoC: Intel: bytcr_rt5640: Add DMI quirk for Vexia Edu Atla 10 tablet (Hans de Goede)
- ASoC: Intel: bytcr_rt5640: Add support for non ACPI instantiated codec (Hans de Goede)
- ASoC: codecs: rt5640: Always disable IRQs from rt5640_cancel_work() (Hans de Goede)
- ALSA: hda/realtek: Add subwoofer quirk for Infinix ZERO BOOK 13 (Piyush Raj Chouhan)
- ALSA: hda/realtek: Limit internal Mic boost on Dell platform (Kailang Yang)
- redhat: configs: Drop CONFIG_MEMSTICK_REALTEK_PCI config option (Desnes Nunes)
- x86/uaccess: Avoid barrier_nospec() in 64-bit copy_from_user() (Linus Torvalds)
- perf cap: Add __NR_capget to arch/x86 unistd (Ian Rogers)
- tools headers: Update the linux/unaligned.h copy with the kernel sources (Arnaldo Carvalho de Melo)
- tools headers arm64: Sync arm64's cputype.h with the kernel sources (Arnaldo Carvalho de Melo)
- tools headers: Synchronize {uapi/}linux/bits.h with the kernel sources (Arnaldo Carvalho de Melo)
- tools arch x86: Sync the msr-index.h copy with the kernel sources (Arnaldo Carvalho de Melo)
- perf python: Fix up the build on architectures without HAVE_KVM_STAT_SUPPORT (Arnaldo Carvalho de Melo)
- perf test: Handle perftool-testsuite_probe failure due to broken DWARF (Veronika Molnarova)
- tools headers UAPI: Sync kvm headers with the kernel sources (Arnaldo Carvalho de Melo)
- perf trace: Fix non-listed archs in the syscalltbl routines (Jiri Slaby)
- perf build: Change the clang check back to 12.0.1 (Howard Chu)
- perf trace augmented_raw_syscalls: Add more checks to pass the verifier (Howard Chu)
- perf trace augmented_raw_syscalls: Add extra array index bounds checking to satisfy some BPF verifiers (Arnaldo Carvalho de Melo)
- perf trace: The return from 'write' isn't a pid (Arnaldo Carvalho de Melo)
- tools headers UAPI: Sync linux/const.h with the kernel headers (Arnaldo Carvalho de Melo)
- scsi: ufs: core: Fix another deadlock during RTC update (Peter Wang)
- scsi: scsi_debug: Fix do_device_access() handling of unexpected SG copy length (John Garry)
- Update the RHEL_DIFFERENCES help string (Don Zickus)
- Put build framework for RT kernel in place for Fedora (Clark Williams)
- cgroup: Fix potential overflow issue when checking max_depth (Xiu Jianfeng)
- cgroup/bpf: use a dedicated workqueue for cgroup bpf destruction (Chen Ridong)
- sched_ext: Fix enq_last_no_enq_fails selftest (Tejun Heo)
- sched_ext: Make cast_mask() inline (Tejun Heo)
- scx: Fix raciness in scx_ops_bypass() (David Vernet)
- scx: Fix exit selftest to use custom DSQ (David Vernet)
- sched_ext: Fix function pointer type mismatches in BPF selftests (Vishal Chourasia)
- selftests/sched_ext: add order-only dependency of runner.o on BPFOBJ (Ihor Solodrai)
- mm: krealloc: Fix MTE false alarm in __do_krealloc (Qun-Wei Lin)
- slub/kunit: fix a WARNING due to unwrapped __kmalloc_cache_noprof (Pei Xiao)
- mm: avoid unconditional one-tick sleep when swapcache_prepare fails (Barry Song)
- mseal: update mseal.rst (Jeff Xu)
- mm: split critical region in remap_file_pages() and invoke LSMs in between (Kirill A. Shutemov)
- selftests/mm: fix deadlock for fork after pthread_create with atomic_bool (Edward Liaw)
- Revert "selftests/mm: replace atomic_bool with pthread_barrier_t" (Edward Liaw)
- Revert "selftests/mm: fix deadlock for fork after pthread_create on ARM" (Edward Liaw)
- tools: testing: add expand-only mode VMA test (Lorenzo Stoakes)
- mm/vma: add expand-only VMA merge mode and optimise do_brk_flags() (Lorenzo Stoakes)
- resource,kexec: walk_system_ram_res_rev must retain resource flags (Gregory Price)
- nilfs2: fix kernel bug due to missing clearing of checked flag (Ryusuke Konishi)
- mm: numa_clear_kernel_node_hotplug: Add NUMA_NO_NODE check for node id (Nobuhiro Iwamatsu)
- ocfs2: pass u64 to ocfs2_truncate_inline maybe overflow (Edward Adam Davis)
- mm: shmem: fix data-race in shmem_getattr() (Jeongjun Park)
- mm: mark mas allocation in vms_abort_munmap_vmas as __GFP_NOFAIL (Jann Horn)
- x86/traps: move kmsan check after instrumentation_begin (Sabyrzhan Tasbolatov)
- resource: remove dependency on SPARSEMEM from GET_FREE_REGION (Huang Ying)
- mm/mmap: fix race in mmap_region() with ftruncate() (Liam R. Howlett)
- mm/page_alloc: let GFP_ATOMIC order-0 allocs access highatomic reserves (Matt Fleming)
- fork: only invoke khugepaged, ksm hooks if no error (Lorenzo Stoakes)
- fork: do not invoke uffd on fork if error occurs (Lorenzo Stoakes)
- mm/pagewalk: fix usage of pmd_leaf()/pud_leaf() without present check (David Hildenbrand)
- tpm: Lazily flush the auth session (Jarkko Sakkinen)
- tpm: Rollback tpm2_load_null() (Jarkko Sakkinen)
- tpm: Return tpm2_sessions_init() when null key creation fails (Jarkko Sakkinen)
- spi: spi-fsl-dspi: Fix crash when not using GPIO chip select (Frank Li)
- spi: geni-qcom: Fix boot warning related to pm_runtime and devres (Georgi Djakov)
- spi: mtk-snfi: fix kerneldoc for mtk_snand_is_page_ops() (Bartosz Golaszewski)
- spi: stm32: fix missing device mode capability in stm32mp25 (Alain Volmat)
- Linux 6.12-rc5 (Linus Torvalds)
- x86/sev: Ensure that RMP table fixups are reserved (Ashish Kalra)
- x86/microcode/AMD: Split load_microcode_amd() (Borislav Petkov (AMD))
- x86/microcode/AMD: Pay attention to the stepping dynamically (Borislav Petkov (AMD))
- x86/lam: Disable ADDRESS_MASKING in most cases (Pawan Gupta)
- fgraph: Change the name of cpuhp state to "fgraph:online" (Steven Rostedt)
- fgraph: Fix missing unlock in register_ftrace_graph() (Li Huafei)
- platform/x86: asus-wmi: Fix thermal profile initialization (Armin Wolf)
- platform/x86: dell-wmi: Ignore suspend notifications (Armin Wolf)
- platform/x86/intel/pmc: Fix pmc_core_iounmap to call iounmap for valid addresses (Vamsi Krishna Brahmajosyula)
- platform/x86:intel/pmc: Revert "Enable the ACPI PM Timer to be turned off when suspended" (Marek Maslanka)
- firewire: core: fix invalid port index for parent device (Takashi Sakamoto)
- block: fix sanity checks in blk_rq_map_user_bvec (Xinyu Zhang)
- md/raid10: fix null ptr dereference in raid10_size() (Yu Kuai)
- md: ensure child flush IO does not affect origin bio->bi_status (Li Nan)
- xfs: update the pag for the last AG at recovery time (Christoph Hellwig)
- xfs: don't use __GFP_RETRY_MAYFAIL in xfs_initialize_perag (Christoph Hellwig)
- xfs: error out when a superblock buffer update reduces the agcount (Christoph Hellwig)
- xfs: update the file system geometry after recoverying superblock buffers (Christoph Hellwig)
- xfs: merge the perag freeing helpers (Christoph Hellwig)
- xfs: pass the exact range to initialize to xfs_initialize_perag (Christoph Hellwig)
- xfs: don't fail repairs on metadata files with no attr fork (Darrick J. Wong)
- generic: enable RPMB for all configs that enable MMC (Peter Robinson)
- fedora: riscv: Don't override MMC platform defaults (Peter Robinson)
- common: only enable on MMC_DW_BLUEFIELD (Peter Robinson)
- fedora: aarch64: Stop overriding CONFIG_MMC defaults (Peter Robinson)
- commong: The KS7010 driver has been removed (Peter Robinson)
- Revert "fs/9p: simplify iget to remove unnecessary paths" (Dominique Martinet)
- Revert "fs/9p: fix uaf in in v9fs_stat2inode_dotl" (Dominique Martinet)
- Revert "fs/9p: remove redundant pointer v9ses" (Dominique Martinet)
- Revert " fs/9p: mitigate inode collisions" (Dominique Martinet)
- cifs: fix warning when destroy 'cifs_io_request_pool' (Ye Bin)
- smb: client: Handle kstrdup failures for passwords (Henrique Carvalho)
- fuse: remove stray debug line (Miklos Szeredi)
- Revert "fuse: move initialization of fuse_file to fuse_writepages() instead of in callback" (Miklos Szeredi)
- fuse: update inode size after extending passthrough write (Amir Goldstein)
- fs: pass offset and result to backing_file end_write() callback (Amir Goldstein)
- nfsd: cancel nfsd_shrinker_work using sync mode in nfs4_state_shutdown_net (Yang Erkun)
- nfsd: fix race between laundromat and free_stateid (Olga Kornievskaia)
- ACPI: button: Add DMI quirk for Samsung Galaxy Book2 to fix initial lid detection issue (Shubham Panwar)
- ACPI: resource: Add LG 16T90SP to irq1_level_low_skip_override[] (Christian Heusel)
- ACPI: PRM: Clean up guid type in struct prm_handler_info (Dan Carpenter)
- ACPI: PRM: Find EFI_MEMORY_RUNTIME block for PRM handler and context (Koba Ko)
- powercap: dtpm_devfreq: Fix error check against dev_pm_qos_add_request() (Yuan Can)
- cpufreq: CPPC: fix perf_to_khz/khz_to_perf conversion exception (liwei)
- cpufreq: docs: Reflect latency changes in docs (Christian Loehle)
- PCI/pwrctl: Abandon QCom WCN probe on pre-pwrseq device-trees (Bartosz Golaszewski)
- PCI: Hold rescan lock while adding devices during host probe (Bartosz Golaszewski)
- fbdev: wm8505fb: select CONFIG_FB_IOMEM_FOPS (Arnd Bergmann)
- fbdev: da8xx: remove the driver (Bartosz Golaszewski)
- fbdev: Constify struct sbus_mmap_map (Christophe JAILLET)
- fbdev: nvidiafb: fix inconsistent indentation warning (SurajSonawane2415)
- fbdev: sstfb: Make CONFIG_FB_DEVICE optional (Gonzalo Silvalde Blanco)
- MAINTAINERS: add a keyword entry for the GPIO subsystem (Bartosz Golaszewski)
- ata: libata: Set DID_TIME_OUT for commands that actually timed out (Niklas Cassel)
- ASoC: qcom: sc7280: Fix missing Soundwire runtime stream alloc (Krzysztof Kozlowski)
- ASoC: fsl_micfil: Add sample rate constraint (Shengjiu Wang)
- ASoC: rt722-sdca: increase clk_stop_timeout to fix clock stop issue (Jack Yu)
- ASoC: SOF: Intel: hda: Always clean up link DMA during stop (Ranjani Sridharan)
- soundwire: intel_ace2x: Send PDI stream number during prepare (Ranjani Sridharan)
- ASoC: SOF: Intel: hda: Handle prepare without close for non-HDA DAI's (Ranjani Sridharan)
- ASoC: SOF: ipc4-topology: Do not set ALH node_id for aggregated DAIs (Ranjani Sridharan)
- ASoC: fsl_micfil: Add a flag to distinguish with different volume control types (Chancel Liu)
- ASoC: codecs: lpass-rx-macro: fix RXn(rx,n) macro for DSM_CTL and SEC7 regs (Alexey Klimov)
- ASoC: Change my e-mail to gmail (Kirill Marinushkin)
- ASoC: Intel: soc-acpi: lnl: Add match entry for TM2 laptops (Derek Fang)
- ASoC: amd: yc: Fix non-functional mic on ASUS E1404FA (Ilya Dudikov)
- MAINTAINERS: Update maintainer list for MICROCHIP ASOC, SSC and MCP16502 drivers (Andrei Simion)
- ASoC: qcom: Select missing common Soundwire module code on SDM845 (Krzysztof Kozlowski)
- ASoC: fsl_esai: change dev_warn to dev_dbg in irq handler (Shengjiu Wang)
- ASoC: rsnd: Fix probe failure on HiHope boards due to endpoint parsing (Lad Prabhakar)
- ASoC: max98388: Fix missing increment of variable slot_found (Colin Ian King)
- ASoC: amd: yc: Add quirk for ASUS Vivobook S15 M3502RA (Christian Heusel)
- ASoC: topology: Bump minimal topology ABI version (Amadeusz Sławiński)
- ASoC: codecs: Fix error handling in aw_dev_get_dsp_status function (Zhu Jun)
- ASoC: qcom: sdm845: add missing soundwire runtime stream alloc (Alexey Klimov)
- ASoC: loongson: Fix component check failed on FDT systems (Binbin Zhou)
- ASoC: dapm: avoid container_of() to get component (Benjamin Bara)
- ASoC: SOF: Intel: hda-loader: do not wait for HDaudio IOC (Kai Vehmanen)
- ASoC: SOF: amd: Fix for ACP SRAM addr for acp7.0 platform (Venkata Prasad Potturu)
- ASoC: SOF: amd: Add error log for DSP firmware validation failure (Venkata Prasad Potturu)
- ASoC: Intel: avs: Update stream status in a separate thread (Amadeusz Sławiński)
- ASoC: dt-bindings: davinci-mcasp: Fix interrupt properties (Miquel Raynal)
- ASoC: qcom: Fix NULL Dereference in asoc_qcom_lpass_cpu_platform_probe() (Zichen Xie)
- ALSA: hda/realtek: Update default depop procedure (Kailang Yang)
- ALSA: hda/tas2781: select CRC32 instead of CRC32_SARWATE (Eric Biggers)
- ALSA: hda/realtek: Add subwoofer quirk for Acer Predator G9-593 (José Relvas)
- ALSA: firewire-lib: Avoid division by zero in apply_constraint_to_size() (Andrey Shumilin)
- drm/xe: Don't restart parallel queues multiple times on GT reset (Nirmoy Das)
- drm/xe/ufence: Prefetch ufence addr to catch bogus address (Nirmoy Das)
- drm/xe: Handle unreliable MMIO reads during forcewake (Shuicheng Lin)
- drm/xe/guc/ct: Flush g2h worker in case of g2h response timeout (Badal Nilawar)
- drm/xe: Enlarge the invalidation timeout from 150 to 500 (Shuicheng Lin)
- drm/bridge: tc358767: fix missing of_node_put() in for_each_endpoint_of_node() (Javier Carrasco)
- drm/bridge: Fix assignment of the of_node of the parent to aux bridge (Abel Vesa)
- i915: fix DRM_I915_GVT_KVMGT dependencies (Arnd Bergmann)
- drm/amdgpu: handle default profile on on devices without fullscreen 3D (Alex Deucher)
- drm/amd/display: Disable PSR-SU on Parade 08-01 TCON too (Mario Limonciello)
- drm/amdgpu: fix random data corruption for sdma 7 (Frank Min)
- drm/amd/display: temp w/a for DP Link Layer compliance (Aurabindo Pillai)
- drm/amd/display: temp w/a for dGPU to enter idle optimizations (Aurabindo Pillai)
- drm/amd/pm: update deep sleep status on smu v14.0.2/3 (Kenneth Feng)
- drm/amd/pm: update overdrive function on smu v14.0.2/3 (Kenneth Feng)
- drm/amd/pm: update the driver-fw interface file for smu v14.0.2/3 (Kenneth Feng)
- drm/amd: Guard against bad data for ATIF ACPI method (Mario Limonciello)
- x86: fix whitespace in runtime-const assembler output (Linus Torvalds)
- x86: fix user address masking non-canonical speculation issue (Linus Torvalds)
- v6.12-rc4-rt6 (Sebastian Andrzej Siewior)
- sched: Update the lazy-preempt bits. (Sebastian Andrzej Siewior)
- timer: Update the ktimersd series. (Sebastian Andrzej Siewior)
- v6.12-rc4-rt5 (Sebastian Andrzej Siewior)
- bpf: Check validity of link->type in bpf_link_show_fdinfo() (Hou Tao)
- bpf: Add the missing BPF_LINK_TYPE invocation for sockmap (Hou Tao)
- bpf: fix do_misc_fixups() for bpf_get_branch_snapshot() (Andrii Nakryiko)
- bpf,perf: Fix perf_event_detach_bpf_prog error handling (Jiri Olsa)
- selftests/bpf: Add test for passing in uninit mtu_len (Daniel Borkmann)
- selftests/bpf: Add test for writes to .rodata (Daniel Borkmann)
- bpf: Remove MEM_UNINIT from skb/xdp MTU helpers (Daniel Borkmann)
- bpf: Fix overloading of MEM_UNINIT's meaning (Daniel Borkmann)
- bpf: Add MEM_WRITE attribute (Daniel Borkmann)
- bpf: Preserve param->string when parsing mount options (Hou Tao)
- bpf, arm64: Fix address emission with tag-based KASAN enabled (Peter Collingbourne)
- net: dsa: mv88e6xxx: support 4000ps cycle counter period (Shenghao Yang)
- net: dsa: mv88e6xxx: read cycle counter period from hardware (Shenghao Yang)
- net: dsa: mv88e6xxx: group cycle counter coefficients (Shenghao Yang)
- net: usb: qmi_wwan: add Fibocom FG132 0x0112 composition (Reinhard Speyerer)
- hv_netvsc: Fix VF namespace also in synthetic NIC NETDEV_REGISTER event (Haiyang Zhang)
- net: dsa: microchip: disable EEE for KSZ879x/KSZ877x/KSZ876x (Tim Harvey)
- Bluetooth: ISO: Fix UAF on iso_sock_timeout (Luiz Augusto von Dentz)
- Bluetooth: SCO: Fix UAF on sco_sock_timeout (Luiz Augusto von Dentz)
- Bluetooth: hci_core: Disable works on hci_unregister_dev (Luiz Augusto von Dentz)
- xfrm: fix one more kernel-infoleak in algo dumping (Petr Vaganov)
- xfrm: validate new SA's prefixlen using SA family when sel.family is unset (Sabrina Dubroca)
- xfrm: policy: remove last remnants of pernet inexact list (Florian Westphal)
- xfrm: respect ip protocols rules criteria when performing dst lookups (Eyal Birger)
- xfrm: extract dst lookup parameters into a struct (Eyal Birger)
- posix-clock: posix-clock: Fix unbalanced locking in pc_clock_settime() (Jinjie Ruan)
- r8169: avoid unsolicited interrupts (Heiner Kallweit)
- net: sched: use RCU read-side critical section in taprio_dump() (Dmitry Antipov)
- net: sched: fix use-after-free in taprio_change() (Dmitry Antipov)
- net/sched: act_api: deny mismatched skip_sw/skip_hw flags for actions created by classifiers (Vladimir Oltean)
- net: usb: usbnet: fix name regression (Oliver Neukum)
- mlxsw: spectrum_router: fix xa_store() error checking (Yuan Can)
- netfilter: xtables: fix typo causing some targets not to load on IPv6 (Pablo Neira Ayuso)
- netfilter: bpf: must hold reference on net namespace (Florian Westphal)
- virtio_net: fix integer overflow in stats (Michael S. Tsirkin)
- net: fix races in netdev_tx_sent_queue()/dev_watchdog() (Eric Dumazet)
- net: wwan: fix global oob in wwan_rtnl_policy (Lin Ma)
- fsl/fman: Fix refcount handling of fman-related devices (Aleksandr Mishin)
- fsl/fman: Save device references taken in mac_probe() (Aleksandr Mishin)
- MAINTAINERS: add samples/pktgen to NETWORKING [GENERAL] (Hangbin Liu)
- mailmap: update entry for Jesper Dangaard Brouer (Jesper Dangaard Brouer)
- net: dsa: mv88e6xxx: Fix error when setting port policy on mv88e6393x (Peter Rashleigh)
- octeon_ep: Add SKB allocation failures handling in __octep_oq_process_rx() (Aleksandr Mishin)
- octeon_ep: Implement helper for iterating packets in Rx queue (Aleksandr Mishin)
- bnxt_en: replace ptp_lock with irqsave variant (Vadim Fedorenko)
- net: phy: dp83822: Fix reset pin definitions (Michel Alex)
- MAINTAINERS: add Simon as an official reviewer (Jakub Kicinski)
- net: plip: fix break; causing plip to never transmit (Jakub Boehm)
- be2net: fix potential memory leak in be_xmit() (Wang Hai)
- net/sun3_82586: fix potential memory leak in sun3_82586_send_packet() (Wang Hai)
- net: pse-pd: Fix out of bound for loop (Kory Maincent)
- HID: lenovo: Add support for Thinkpad X1 Tablet Gen 3 keyboard (Hans de Goede)
- HID: multitouch: Add quirk for Logitech Bolt receiver w/ Casa touchpad (Kenneth Albanowski)
- HID: i2c-hid: Delayed i2c resume wakeup for 0x0d42 Goodix touchpad (Bartłomiej Maryńczak)
- LoongArch: KVM: Mark hrtimer to expire in hard interrupt context (Huacai Chen)
- LoongArch: Make KASAN usable for variable cpu_vabits (Huacai Chen)
- LoongArch: Set initial pte entry with PAGE_GLOBAL for kernel space (Bibo Mao)
- LoongArch: Don't crash in stack_top() for tasks without vDSO (Thomas Weißschuh)
- LoongArch: Set correct size for vDSO code mapping (Huacai Chen)
- LoongArch: Enable IRQ if do_ale() triggered in irq-enabled context (Huacai Chen)
- LoongArch: Get correct cores_per_package for SMT systems (Huacai Chen)
- LoongArch: Use "Exception return address" to comment ERA (Yanteng Si)
- tracing: Consider the NULL character when validating the event length (Leo Yan)
- tracing/probes: Fix MAX_TRACE_ARGS limit handling (Mikel Rychliski)
- objpool: fix choosing allocation for percpu slots (Viktor Malik)
- btrfs: fix passing 0 to ERR_PTR in btrfs_search_dir_index_item() (Yue Haibing)
- btrfs: reject ro->rw reconfiguration if there are hard ro requirements (Qu Wenruo)
- btrfs: fix read corruption due to race with extent map merging (Boris Burkov)
- btrfs: fix the delalloc range locking if sector size < page size (Qu Wenruo)
- btrfs: qgroup: set a more sane default value for subtree drop threshold (Qu Wenruo)
- btrfs: clear force-compress on remount when compress mount option is given (Filipe Manana)
- btrfs: zoned: fix zone unusable accounting for freed reserved extent (Naohiro Aota)
- jfs: Fix sanity check in dbMount (Dave Kleikamp)
- bcachefs: Set bch_inode_unpacked.bi_snapshot in old inode path (Kent Overstreet)
- bcachefs: Mark more errors as AUTOFIX (Kent Overstreet)
- bcachefs: Workaround for kvmalloc() not supporting > INT_MAX allocations (Kent Overstreet)
- bcachefs: Don't use wait_event_interruptible() in recovery (Kent Overstreet)
- bcachefs: Fix __bch2_fsck_err() warning (Kent Overstreet)
- bcachefs: fsck: Improve hash_check_key() (Kent Overstreet)
- bcachefs: bch2_hash_set_or_get_in_snapshot() (Kent Overstreet)
- bcachefs: Repair mismatches in inode hash seed, type (Kent Overstreet)
- bcachefs: Add hash seed, type to inode_to_text() (Kent Overstreet)
- bcachefs: INODE_STR_HASH() for bch_inode_unpacked (Kent Overstreet)
- bcachefs: Run in-kernel offline fsck without ratelimit errors (Kent Overstreet)
- bcachefs: skip mount option handle for empty string. (Hongbo Li)
- bcachefs: fix incorrect show_options results (Hongbo Li)
- bcachefs: Fix data corruption on -ENOSPC in buffered write path (Kent Overstreet)
- bcachefs: bch2_folio_reservation_get_partial() is now better behaved (Kent Overstreet)
- bcachefs: fix disk reservation accounting in bch2_folio_reservation_get() (Kent Overstreet)
- bcachefS: ec: fix data type on stripe deletion (Kent Overstreet)
- bcachefs: Don't use commit_do() unnecessarily (Kent Overstreet)
- bcachefs: handle restarts in bch2_bucket_io_time_reset() (Kent Overstreet)
- bcachefs: fix restart handling in __bch2_resume_logged_op_finsert() (Kent Overstreet)
- bcachefs: fix restart handling in bch2_alloc_write_key() (Kent Overstreet)
- bcachefs: fix restart handling in bch2_do_invalidates_work() (Kent Overstreet)
- bcachefs: fix missing restart handling in bch2_read_retry_nodecode() (Kent Overstreet)
- bcachefs: fix restart handling in bch2_fiemap() (Kent Overstreet)
- bcachefs: fix bch2_hash_delete() error path (Kent Overstreet)
- bcachefs: fix restart handling in bch2_rename2() (Kent Overstreet)
- Revert "9p: Enable multipage folios" (Dominique Martinet)
- Trim Changelog for 6.12 (Justin M. Forbes)
- Enable CONFIG_SECURITY_IPE for Fedora (Zbigniew Jędrzejewski-Szmek)
- redhat: allow to override VERSION_ON_UPSTREAM from command line (Jan Stancek)
- redhat: configs: Enable CONFIG_SECURITY_TOMOYO in Fedora kernels (Tetsuo Handa)
- redhat: drop ARK changelog (Jan Stancek) [RHEL-56700]
- redhat: regenerate test-data (Jan Stancek) [RHEL-56700]
- redhat: rpminspect.yaml: more tests to ignore in selftests (Jan Stancek) [RHEL-56700]
- redhat/Makefile.variables: don't set DISTRO (Jan Stancek) [RHEL-56700]
- redhat/Makefile.variables: set PATCHLIST_URL to none (Jan Stancek) [RHEL-56700]
- redhat: gitlab-ci: add initial version (Jan Stancek) [RHEL-56700]
- redhat: update rpminspect with c9s one (Jan Stancek) [RHEL-56700]
- redhat: remove fedora configs and files (Jan Stancek) [RHEL-56700]
- redhat: init RHEL10.0 beta variables and dist tag (Jan Stancek) [RHEL-56700]
- redhat: set release version (Jan Stancek) [RHEL-56700]
- redhat: fix CONFIG_PREEMPT config (Jan Stancek) [RHEL-56700]
- KVM: selftests: Fix build on on non-x86 architectures (Mark Brown)
- 9p: fix slab cache name creation for real (Linus Torvalds)
- KVM: arm64: Ensure vgic_ready() is ordered against MMIO registration (Oliver Upton)
- KVM: arm64: vgic: Don't check for vgic_ready() when setting NR_IRQS (Oliver Upton)
- KVM: arm64: Fix shift-out-of-bounds bug (Ilkka Koskinen)
- KVM: arm64: Shave a few bytes from the EL2 idmap code (Marc Zyngier)
- KVM: arm64: Don't eagerly teardown the vgic on init error (Marc Zyngier)
- KVM: arm64: Expose S1PIE to guests (Mark Brown)
- KVM: arm64: nv: Clarify safety of allowing TLBI unmaps to reschedule (Oliver Upton)
- KVM: arm64: nv: Punt stage-2 recycling to a vCPU request (Oliver Upton)
- KVM: arm64: nv: Do not block when unmapping stage-2 if disallowed (Oliver Upton)
- KVM: arm64: nv: Keep reference on stage-2 MMU when scheduled out (Oliver Upton)
- KVM: arm64: Unregister redistributor for failed vCPU creation (Oliver Upton)
- KVM: selftests: aarch64: Add writable test for ID_AA64PFR1_EL1 (Shaoqin Huang)
- KVM: arm64: Allow userspace to change ID_AA64PFR1_EL1 (Shaoqin Huang)
- KVM: arm64: Use kvm_has_feat() to check if FEAT_SSBS is advertised to the guest (Shaoqin Huang)
- KVM: arm64: Disable fields that KVM doesn't know how to handle in ID_AA64PFR1_EL1 (Shaoqin Huang)
- KVM: arm64: Make the exposed feature bits in AA64DFR0_EL1 writable from userspace (Shameer Kolothum)
- RISCV: KVM: use raw_spinlock for critical section in imsic (Cyan Yang)
- KVM: selftests: Fix out-of-bounds reads in CPUID test's array lookups (Sean Christopherson)
- KVM: selftests: x86: Avoid using SSE/AVX instructions (Vitaly Kuznetsov)
- KVM: nSVM: Ignore nCR3[4:0] when loading PDPTEs from memory (Sean Christopherson)
- KVM: VMX: reset the segment cache after segment init in vmx_vcpu_reset() (Maxim Levitsky)
- KVM: x86: Clean up documentation for KVM_X86_QUIRK_SLOT_ZAP_ALL (Sean Christopherson)
- KVM: x86/mmu: Add lockdep assert to enforce safe usage of kvm_unmap_gfn_range() (Sean Christopherson)
- KVM: x86/mmu: Zap only SPs that shadow gPTEs when deleting memslot (Sean Christopherson)
- x86/kvm: Override default caching mode for SEV-SNP and TDX (Kirill A. Shutemov)
- KVM: Remove unused kvm_vcpu_gfn_to_pfn_atomic (Dr. David Alan Gilbert)
- KVM: Remove unused kvm_vcpu_gfn_to_pfn (Dr. David Alan Gilbert)
- uprobe: avoid out-of-bounds memory access of fetching args (Qiao Ma)
- proc: Fix W=1 build kernel-doc warning (Thorsten Blum)
- afs: Fix lock recursion (David Howells)
- fs: Fix uninitialized value issue in from_kuid and from_kgid (Alessandro Zanni)
- fs: don't try and remove empty rbtree node (Christian Brauner)
- netfs: Downgrade i_rwsem for a buffered write (David Howells)
- nilfs2: fix kernel bug due to missing clearing of buffer delay flag (Ryusuke Konishi)
- openat2: explicitly return -E2BIG for (usize > PAGE_SIZE) (Aleksa Sarai)
- netfs: fix documentation build error (Jonathan Corbet)
- netfs: In readahead, put the folio refs as soon extracted (David Howells)
- crypto: lib/mpi - Fix an "Uninitialized scalar variable" issue (Qianqiang Liu)
- Revert "Merge branch 'enablement/gpio-expander' into 'os-build'" (Justin M. Forbes)
- Linux 6.12-rc4 (Linus Torvalds)
- Bluetooth: btusb: Fix regression with fake CSR controllers 0a12:0001 (Luiz Augusto von Dentz)
- Bluetooth: bnep: fix wild-memory-access in proto_unregister (Ye Bin)
- Bluetooth: btusb: Fix not being able to reconnect after suspend (Luiz Augusto von Dentz)
- Bluetooth: Remove debugfs directory on module init failure (Aaron Thompson)
- Bluetooth: Call iso_exit() on module unload (Aaron Thompson)
- Bluetooth: ISO: Fix multiple init when debugfs is disabled (Aaron Thompson)
- pinctrl: ocelot: fix system hang on level based interrupts (Sergey Matsievskiy)
- pinctrl: nuvoton: fix a double free in ma35_pinctrl_dt_node_to_map_func() (Harshit Mogalapalli)
- pinctrl: sophgo: fix double free in cv1800_pctrl_dt_node_to_map() (Harshit Mogalapalli)
- pinctrl: intel: platform: Add Panther Lake to the list of supported (Andy Shevchenko)
- pinctrl: intel: platform: use semicolon instead of comma in ncommunities assignment (Javier Carrasco)
- pinctrl: intel: platform: fix error path in device_for_each_child_node() (Javier Carrasco)
- pinctrl: aw9523: add missing mutex_destroy (Rosen Penev)
- pinctrl: stm32: check devm_kasprintf() returned value (Ma Ke)
- pinctrl: apple: check devm_kasprintf() returned value (Ma Ke)
- misc: rtsx: list supported models in Kconfig help (Yo-Jung (Leo) Lin)
- MAINTAINERS: Remove some entries due to various compliance requirements. (Greg Kroah-Hartman)
- misc: microchip: pci1xxxx: add support for NVMEM_DEVID_AUTO for OTP device (Heiko Thiery)
- misc: microchip: pci1xxxx: add support for NVMEM_DEVID_AUTO for EEPROM device (Heiko Thiery)
- parport: Proper fix for array out-of-bounds access (Takashi Iwai)
- iio: frequency: admv4420: fix missing select REMAP_SPI in Kconfig (Javier Carrasco)
- iio: frequency: {admv4420,adrf6780}: format Kconfig entries (Javier Carrasco)
- iio: adc: ad4695: Add missing Kconfig select (David Lechner)
- iio: adc: ti-ads8688: add missing select IIO_(TRIGGERED_)BUFFER in Kconfig (Javier Carrasco)
- iio: hid-sensors: Fix an error handling path in _hid_sensor_set_report_latency() (Christophe JAILLET)
- iioc: dac: ltc2664: Fix span variable usage in ltc2664_channel_config() (Mohammed Anees)
- iio: dac: stm32-dac-core: add missing select REGMAP_MMIO in Kconfig (Javier Carrasco)
- iio: dac: ltc1660: add missing select REGMAP_SPI in Kconfig (Javier Carrasco)
- iio: dac: ad5770r: add missing select REGMAP_SPI in Kconfig (Javier Carrasco)
- iio: amplifiers: ada4250: add missing select REGMAP_SPI in Kconfig (Javier Carrasco)
- iio: frequency: adf4377: add missing select REMAP_SPI in Kconfig (Javier Carrasco)
- iio: resolver: ad2s1210: add missing select (TRIGGERED_)BUFFER in Kconfig (Javier Carrasco)
- iio: resolver: ad2s1210 add missing select REGMAP in Kconfig (Javier Carrasco)
- iio: proximity: mb1232: add missing select IIO_(TRIGGERED_)BUFFER in Kconfig (Javier Carrasco)
- iio: pressure: bm1390: add missing select IIO_(TRIGGERED_)BUFFER in Kconfig (Javier Carrasco)
- iio: magnetometer: af8133j: add missing select IIO_(TRIGGERED_)BUFFER in Kconfig (Javier Carrasco)
- iio: light: bu27008: add missing select IIO_(TRIGGERED_)BUFFER in Kconfig (Javier Carrasco)
- iio: chemical: ens160: add missing select IIO_(TRIGGERED_)BUFFER in Kconfig (Javier Carrasco)
- iio: dac: ad5766: add missing select IIO_(TRIGGERED_)BUFFER in Kconfig (Javier Carrasco)
- iio: dac: ad3552r: add missing select IIO_(TRIGGERED_)BUFFER in Kconfig (Javier Carrasco)
- iio: adc: ti-lmp92064: add missing select IIO_(TRIGGERED_)BUFFER in Kconfig (Javier Carrasco)
- iio: adc: ti-lmp92064: add missing select REGMAP_SPI in Kconfig (Javier Carrasco)
- iio: adc: ti-ads124s08: add missing select IIO_(TRIGGERED_)BUFFER in Kconfig (Javier Carrasco)
- iio: adc: ad7944: add missing select IIO_(TRIGGERED_)BUFFER in Kconfig (Javier Carrasco)
- iio: accel: kx022a: add missing select IIO_(TRIGGERED_)BUFFER in Kconfig (Javier Carrasco)
- iio: pressure: sdp500: Add missing select CRC8 (Jonathan Cameron)
- iio: light: veml6030: fix ALS sensor resolution (Javier Carrasco)
- iio: bmi323: fix reversed if statement in bmi323_core_runtime_resume() (Dan Carpenter)
- iio: bmi323: fix copy and paste bugs in suspend resume (Dan Carpenter)
- iio: bmi323: Drop CONFIG_PM guards around runtime functions (Nathan Chancellor)
- dt-bindings: iio: dac: adi,ad56xx: Fix duplicate compatible strings (Rob Herring (Arm))
- iio: light: opt3001: add missing full-scale range value (Emil Gedenryd)
- iio: light: veml6030: fix IIO device retrieval from embedded device (Javier Carrasco)
- iio: accel: bma400: Fix uninitialized variable field_value in tap event handling. (Mikhail Lobanov)
- serial: qcom-geni: rename suspend functions (Johan Hovold)
- serial: qcom-geni: drop unused receive parameter (Johan Hovold)
- serial: qcom-geni: drop flip buffer WARN() (Johan Hovold)
- serial: qcom-geni: fix rx cancel dma status bit (Johan Hovold)
- serial: qcom-geni: fix receiver enable (Johan Hovold)
- serial: qcom-geni: fix dma rx cancellation (Johan Hovold)
- serial: qcom-geni: fix shutdown race (Johan Hovold)
- serial: qcom-geni: revert broken hibernation support (Johan Hovold)
- serial: qcom-geni: fix polled console initialisation (Johan Hovold)
- serial: imx: Update mctrl old_status on RTSD interrupt (Marek Vasut)
- tty: n_gsm: Fix use-after-free in gsm_cleanup_mux (Longlong Xia)
- vt: prevent kernel-infoleak in con_font_get() (Jeongjun Park)
- USB: serial: option: add Telit FN920C04 MBIM compositions (Daniele Palmas)
- USB: serial: option: add support for Quectel EG916Q-GL (Benjamin B. Frost)
- xhci: dbc: honor usb transfer size boundaries. (Mathias Nyman)
- usb: xhci: Fix handling errors mid TD followed by other errors (Michal Pecio)
- xhci: Mitigate failed set dequeue pointer commands (Mathias Nyman)
- xhci: Fix incorrect stream context type macro (Mathias Nyman)
- USB: gadget: dummy-hcd: Fix "task hung" problem (Alan Stern)
- usb: gadget: f_uac2: fix return value for UAC2_ATTRIBUTE_STRING store (Kevin Groeneveld)
- usb: dwc3: core: Fix system suspend on TI AM62 platforms (Roger Quadros)
- xhci: tegra: fix checked USB2 port number (Henry Lin)
- usb: dwc3: Wait for EndXfer completion before restoring GUSB2PHYCFG (Prashanth K)
- usb: typec: qcom-pmic-typec: fix sink status being overwritten with RP_DEF (Jonathan Marek)
- usb: typec: altmode should keep reference to parent (Thadeu Lima de Souza Cascardo)
- MAINTAINERS: usb: raw-gadget: add bug tracker link (Andrey Konovalov)
- MAINTAINERS: Add an entry for the LJCA drivers (Sakari Ailus)
- x86/apic: Always explicitly disarm TSC-deadline timer (Zhang Rui)
- x86/CPU/AMD: Only apply Zenbleed fix for Zen2 during late microcode load (John Allen)
- x86/bugs: Use code segment selector for VERW operand (Pawan Gupta)
- x86/entry_32: Clear CPU buffers after register restore in NMI return (Pawan Gupta)
- x86/entry_32: Do not clobber user EFLAGS.ZF (Pawan Gupta)
- x86/resctrl: Annotate get_mem_config() functions as __init (Nathan Chancellor)
- x86/resctrl: Avoid overflow in MB settings in bw_validate() (Martin Kletzander)
- x86/amd_nb: Add new PCI ID for AMD family 1Ah model 20h (Richard Gong)
- irqchip/renesas-rzg2l: Fix missing put_device (Fabrizio Castro)
- irqchip/riscv-intc: Fix SMP=n boot with ACPI (Sunil V L)
- irqchip/sifive-plic: Unmask interrupt in plic_irq_enable() (Nam Cao)
- irqchip/gic-v4: Don't allow a VMOVP on a dying VPE (Marc Zyngier)
- irqchip/sifive-plic: Return error code on failure (Charlie Jenkins)
- irqchip/riscv-imsic: Fix output text of base address (Andrew Jones)
- irqchip/ocelot: Comment sticky register clearing code (Sergey Matsievskiy)
- irqchip/ocelot: Fix trigger register address (Sergey Matsievskiy)
- irqchip: Remove obsolete config ARM_GIC_V3_ITS_PCI (Lukas Bulwahn)
- MAINTAINERS: Add an entry for PREEMPT_RT. (Sebastian Andrzej Siewior)
- sched/fair: Fix external p->on_rq users (Peter Zijlstra)
- sched/psi: Fix mistaken CPU pressure indication after corrupted task state bug (Johannes Weiner)
- sched/core: Dequeue PSI signals for blocked tasks that are delayed (Peter Zijlstra)
- sched: Fix delayed_dequeue vs switched_from_fair() (Peter Zijlstra)
- sched/core: Disable page allocation in task_tick_mm_cid() (Waiman Long)
- sched/deadline: Use hrtick_enabled_dl() before start_hrtick_dl() (Phil Auld)
- sched/eevdf: Fix wakeup-preempt by checking cfs_rq->nr_running (Chen Yu)
- sched: Fix sched_delayed vs cfs_bandwidth (Mike Galbraith)
- xen: Remove dependency between pciback and privcmd (Jiqian Chen)
- dma-mapping: fix tracing dma_alloc/free with vmalloc'd memory (Sean Anderson)
- io_uring/rw: fix wrong NOWAIT check in io_rw_init_file() (Jens Axboe)
- scsi: target: core: Fix null-ptr-deref in target_alloc_device() (Wang Hai)
- scsi: mpi3mr: Validate SAS port assignments (Ranjan Kumar)
- scsi: ufs: core: Set SDEV_OFFLINE when UFS is shut down (Seunghwan Baek)
- scsi: ufs: core: Requeue aborted request (Peter Wang)
- scsi: ufs: core: Fix the issue of ICU failure (Peter Wang)
- fgraph: Allocate ret_stack_list with proper size (Steven Rostedt)
- fgraph: Use CPU hotplug mechanism to initialize idle shadow stacks (Steven Rostedt)
- MAINTAINERS: update IPE tree url and Fan Wu's email (Fan Wu)
- ipe: fallback to platform keyring also if key in trusted keyring is rejected (Luca Boccassi)
- ipe: allow secondary and platform keyrings to install/update policies (Luca Boccassi)
- ipe: also reject policy updates with the same version (Luca Boccassi)
- ipe: return -ESTALE instead of -EINVAL on update when new policy has a lower version (Luca Boccassi)
- Input: zinitix - don't fail if linux,keycodes prop is absent (Nikita Travkin)
- Input: xpad - add support for MSI Claw A1M (John Edwards)
- Input: xpad - add support for 8BitDo Ultimate 2C Wireless Controller (Stefan Kerkmann)
- 9p: Avoid creating multiple slab caches with the same name (Pedro Falcato)
- 9p: Enable multipage folios (David Howells)
- 9p: v9fs_fid_find: also lookup by inode if not found dentry (Dominique Martinet)
- cfi: fix conditions for HAVE_CFI_ICALL_NORMALIZE_INTEGERS (Alice Ryhl)
- kbuild: rust: add `CONFIG_RUSTC_LLVM_VERSION` (Gary Guo)
- kbuild: fix issues with rustc-option (Alice Ryhl)
- kbuild: refactor cc-option-yn, cc-disable-warning, rust-option-yn macros (Masahiro Yamada)
- lib/Kconfig.debug: fix grammar in RUST_BUILD_ASSERT_ALLOW (Timo Grautstueck)
- lib/buildid: Handle memfd_secret() files in build_id_parse() (Andrii Nakryiko)
- selftests/bpf: Add test case for delta propagation (Daniel Borkmann)
- bpf: Fix print_reg_state's constant scalar dump (Daniel Borkmann)
- bpf: Fix incorrect delta propagation between linked registers (Daniel Borkmann)
- bpf: Properly test iter/task tid filtering (Jordan Rome)
- bpf: Fix iter/task tid filtering (Jordan Rome)
- riscv, bpf: Make BPF_CMPXCHG fully ordered (Andrea Parri)
- bpf, vsock: Drop static vsock_bpf_prot initialization (Michal Luczaj)
- vsock: Update msg_count on read_skb() (Michal Luczaj)
- vsock: Update rx_bytes on read_skb() (Michal Luczaj)
- bpf, sockmap: SK_DROP on attempted redirects of unsupported af_vsock (Michal Luczaj)
- selftests/bpf: Add asserts for netfilter link info (Tyrone Wu)
- bpf: Fix link info netfilter flags to populate defrag flag (Tyrone Wu)
- selftests/bpf: Add test for sign extension in coerce_subreg_to_size_sx() (Dimitar Kanaliev)
- selftests/bpf: Add test for truncation after sign extension in coerce_reg_to_size_sx() (Dimitar Kanaliev)
- bpf: Fix truncation bug in coerce_reg_to_size_sx() (Dimitar Kanaliev)
- selftests/bpf: Assert link info uprobe_multi count & path_size if unset (Tyrone Wu)
- bpf: Fix unpopulated path_size when uprobe_multi fields unset (Tyrone Wu)
- selftests/bpf: Fix cross-compiling urandom_read (Tony Ambardar)
- selftests/bpf: Add test for kfunc module order (Simon Sundberg)
- selftests/bpf: Provide a generic [un]load_module helper (Simon Sundberg)
- bpf: fix kfunc btf caching for modules (Toke Høiland-Jørgensen)
- selftests/bpf: Fix error compiling cgroup_ancestor.c with musl libc (Tony Ambardar)
- riscv, bpf: Fix possible infinite tailcall when CONFIG_CFI_CLANG is enabled (Pu Lehui)
- selftests/bpf: fix perf_event link info name_len assertion (Tyrone Wu)
- bpf: fix unpopulated name_len field in perf_event link info (Tyrone Wu)
- bpf: use kvzmalloc to allocate BPF verifier environment (Rik van Riel)
- selftests/bpf: Add more test case for field flattening (Hou Tao)
- bpf: Check the remaining info_cnt before repeating btf fields (Hou Tao)
- bpf, lsm: Remove bpf_lsm_key_free hook (Thomas Weißschuh)
- bpf: Fix memory leak in bpf_core_apply (Jiri Olsa)
- bpf: selftests: send packet to devmap redirect XDP (Florian Kauer)
- bpf: devmap: provide rxq after redirect (Florian Kauer)
- bpf: Sync uapi bpf.h header to tools directory (Daniel Borkmann)
- bpf: Make sure internal and UAPI bpf_redirect flags don't overlap (Toke Høiland-Jørgensen)
- selftests/bpf: Verify that sync_linked_regs preserves subreg_def (Eduard Zingerman)
- bpf: sync_linked_regs() must preserve subreg_def (Eduard Zingerman)
- bpf: Use raw_spinlock_t in ringbuf (Wander Lairson Costa)
- selftest: hid: add the missing tests directory (Yun Lu)
- cdrom: Avoid barrier_nospec() in cdrom_ioctl_media_changed() (Josh Poimboeuf)
- nvme: use helper nvme_ctrl_state in nvme_keep_alive_finish function (Nilay Shroff)
- nvme: make keep-alive synchronous operation (Nilay Shroff)
- nvme-loop: flush off pending I/O while shutting down loop controller (Nilay Shroff)
- nvme-pci: fix race condition between reset and nvme_dev_disable() (Maurizio Lombardi)
- nvme-multipath: defer partition scanning (Keith Busch)
- nvme: disable CC.CRIME (NVME_CC_CRIME) (Greg Joyce)
- nvme: delete unnecessary fallthru comment (Tokunori Ikegami)
- nvmet-rdma: use sbitmap to replace rsp free list (Guixin Liu)
- nvme: tcp: avoid race between queue_lock lock and destroy (Hannes Reinecke)
- nvmet-passthru: clear EUID/NGUID/UUID while using loop target (Nilay Shroff)
- block: fix blk_rq_map_integrity_sg kernel-doc (Keith Busch)
- ublk: don't allow user copy for unprivileged device (Ming Lei)
- blk-rq-qos: fix crash on rq_qos_wait vs. rq_qos_wake_function race (Omar Sandoval)
- blk-mq: setup queue ->tag_set before initializing hctx (Ming Lei)
- elevator: Remove argument from elevator_find_get (Breno Leitao)
- elevator: do not request_module if elevator exists (Breno Leitao)
- drbd: Remove unused conn_lowest_minor (Dr. David Alan Gilbert)
- block: Fix elevator_get_default() checking for NULL q->tag_set (SurajSonawane2415)
- io_uring/sqpoll: ensure task state is TASK_RUNNING when running task_work (Jens Axboe)
- io_uring/rsrc: ignore dummy_ubuf for buffer cloning (Jens Axboe)
- io_uring/sqpoll: close race on waiting for sqring entries (Jens Axboe)
- cifs: Remove unused functions (Dr. David Alan Gilbert)
- smb/client: Fix logically dead code (Advait Dhamorikar)
- smb: client: fix OOBs when building SMB2_IOCTL request (Paulo Alcantara)
- smb: client: fix possible double free in smb2_set_ea() (Su Hui)
- xfs: punch delalloc extents from the COW fork for COW writes (Christoph Hellwig)
- xfs: set IOMAP_F_SHARED for all COW fork allocations (Christoph Hellwig)
- xfs: share more code in xfs_buffered_write_iomap_begin (Christoph Hellwig)
- xfs: support the COW fork in xfs_bmap_punch_delalloc_range (Christoph Hellwig)
- xfs: IOMAP_ZERO and IOMAP_UNSHARE already hold invalidate_lock (Christoph Hellwig)
- xfs: take XFS_MMAPLOCK_EXCL xfs_file_write_zero_eof (Christoph Hellwig)
- xfs: factor out a xfs_file_write_zero_eof helper (Christoph Hellwig)
- iomap: move locking out of iomap_write_delalloc_release (Christoph Hellwig)
- iomap: remove iomap_file_buffered_write_punch_delalloc (Christoph Hellwig)
- iomap: factor out a iomap_last_written_block helper (Christoph Hellwig)
- xfs: fix integer overflow in xrep_bmap (Darrick J. Wong)
- cpufreq/amd-pstate: Use nominal perf for limits when boost is disabled (Mario Limonciello)
- cpufreq/amd-pstate: Fix amd_pstate mode switch on shared memory systems (Dhananjay Ugwekar)
- powercap: intel_rapl_msr: Add PL4 support for ArrowLake-H (Srinivas Pandruvada)
- [PATCH} hwmon: (jc42) Properly detect TSE2004-compliant devices again (Jean Delvare)
- drm/i915/display: Don't allow tile4 framebuffer to do hflip on display20 or greater (Juha-Pekka Heikkila)
- drm/xe/bmg: improve cache flushing behaviour (Matthew Auld)
- drm/xe/xe_sync: initialise ufence.signalled (Matthew Auld)
- drm/xe/ufence: ufence can be signaled right after wait_woken (Nirmoy Das)
- drm/xe: Use bookkeep slots for external BO's in exec IOCTL (Matthew Brost)
- drm/xe/query: Increase timestamp width (Lucas De Marchi)
- drm/xe: Don't free job in TDR (Matthew Brost)
- drm/xe: Take job list lock in xe_sched_add_pending_job (Matthew Brost)
- drm/xe: fix unbalanced rpm put() with declare_wedged() (Matthew Auld)
- drm/xe: fix unbalanced rpm put() with fence_fini() (Matthew Auld)
- drm/xe/xe2lpg: Extend Wa_15016589081 for xe2lpg (Aradhya Bhatia)
- drm/ast: vga: Clear EDID if no display is connected (Thomas Zimmermann)
- drm/ast: sil164: Clear EDID if no display is connected (Thomas Zimmermann)
- Revert "drm/mgag200: Add vblank support" (Thomas Zimmermann)
- gpu: host1x: Set up device DMA parameters (Thierry Reding)
- gpu: host1x: Fix boot regression for Tegra (Jon Hunter)
- drm/panel: himax-hx83102: Adjust power and gamma to optimize brightness (Cong Yang)
- accel/qaic: Fix the for loop used to walk SG table (Pranjal Ramajor Asha Kanojiya)
- drm/vmwgfx: Remove unnecessary NULL checks before kvfree() (Thorsten Blum)
- drm/vmwgfx: Handle surface check failure correctly (Nikolay Kuratov)
- drm/vmwgfx: Cleanup kms setup without 3d (Zack Rusin)
- drm/vmwgfx: Handle possible ENOMEM in vmw_stdu_connector_atomic_check (Ian Forbes)
- drm/vmwgfx: Limit display layout ioctl array size to VMWGFX_NUM_DISPLAY_UNITS (Ian Forbes)
- drm/i915/dp_mst: Don't require DSC hblank quirk for a non-DSC compatible mode (Imre Deak)
- drm/i915/dp_mst: Handle error during DSC BW overhead/slice calculation (Imre Deak)
- drm/amdgpu/swsmu: default to fullscreen 3D profile for dGPUs (Alex Deucher)
- drm/amdgpu/swsmu: Only force workload setup on init (Alex Deucher)
- drm/radeon: Fix encoder->possible_clones (Ville Syrjälä)
- drm/amdgpu/smu13: always apply the powersave optimization (Alex Deucher)
- drm/amdkfd: Accounting pdd vram_usage for svm (Philip Yang)
- drm/amd/amdgpu: Fix double unlock in amdgpu_mes_add_ring (Srinivasan Shanmugam)
- drm/amdgpu/mes: fix issue of writing to the same log buffer from 2 MES pipes (Michael Chen)
- drm/amdgpu: prevent BO_HANDLES error from being overwritten (Mohammed Anees)
- drm/amdgpu: enable enforce_isolation sysfs node on VFs (Alex Deucher)
- drm/msm/a6xx+: Insert a fence wait before SMMU table update (Rob Clark)
- drm/msm/dpu: don't always program merge_3d block (Jessica Zhang)
- drm/msm/dpu: Don't always set merge_3d pending flush (Jessica Zhang)
- drm/msm: Allocate memory for disp snapshot with kvzalloc() (Douglas Anderson)
- drm/msm: Avoid NULL dereference in msm_disp_state_print_regs() (Douglas Anderson)
- drm/msm/dsi: fix 32-bit signed integer extension in pclk_rate calculation (Jonathan Marek)
- drm/msm/dsi: improve/fix dsc pclk calculation (Jonathan Marek)
- drm/msm/hdmi: drop pll_cmp_to_fdata from hdmi_phy_8998 (Dmitry Baryshkov)
- drm/msm/dpu: check for overflow in _dpu_crtc_setup_lm_bounds() (Dmitry Baryshkov)
- drm/msm/dpu: move CRTC resource assignment to dpu_encoder_virt_atomic_check (Dmitry Baryshkov)
- drm/msm/dpu: make sure phys resources are properly initialized (Dmitry Baryshkov)
- mm: fix follow_pfnmap API lockdep assert (Linus Torvalds)
- iommu/vt-d: Fix incorrect pci_for_each_dma_alias() for non-PCI devices (Lu Baolu)
- iommu/arm-smmu-v3: Convert comma to semicolon (Chen Ni)
- iommu/arm-smmu-v3: Fix last_sid_idx calculation for sid_bits==32 (Daniel Mentz)
- iommu/arm-smmu: Clarify MMU-500 CPRE workaround (Robin Murphy)
- powerpc/powernv: Free name on error in opal_event_init() (Michael Ellerman)
- s390: Update defconfigs (Heiko Carstens)
- s390: Initialize psw mask in perf_arch_fetch_caller_regs() (Heiko Carstens)
- s390/sclp_vt220: Convert newlines to CRLF instead of LFCR (Thomas Weißschuh)
- s390/sclp: Deactivate sclp after all its users (Thomas Weißschuh)
- s390/pkey_pckmo: Return with success for valid protected key types (Holger Dengler)
- KVM: s390: Change virtual to physical address access in diag 0x258 handler (Michael Mueller)
- KVM: s390: gaccess: Check if guest address is in memslot (Nico Boehr)
- s390/ap: Fix CCA crypto card behavior within protected execution environment (Harald Freudenberger)
- s390/pci: Handle PCI error codes other than 0x3a (Niklas Schnelle)
- x86/bugs: Do not use UNTRAIN_RET with IBPB on entry (Johannes Wikner)
- x86/bugs: Skip RSB fill at VMEXIT (Johannes Wikner)
- x86/entry: Have entry_ibpb() invalidate return predictions (Johannes Wikner)
- x86/cpufeatures: Add a IBPB_NO_RET BUG flag (Johannes Wikner)
- x86/cpufeatures: Define X86_FEATURE_AMD_IBPB_RET (Jim Mattson)
- maple_tree: add regression test for spanning store bug (Lorenzo Stoakes)
- maple_tree: correct tree corruption on spanning store (Lorenzo Stoakes)
- mm/mglru: only clear kswapd_failures if reclaimable (Wei Xu)
- mm/swapfile: skip HugeTLB pages for unuse_vma (Liu Shixin)
- selftests: mm: fix the incorrect usage() info of khugepaged (Nanyong Sun)
- MAINTAINERS: add Jann as memory mapping/VMA reviewer (Jann Horn)
- mm: swap: prevent possible data-race in __try_to_reclaim_swap (Jeongjun Park)
- mm: khugepaged: fix the incorrect statistics when collapsing large file folios (Baolin Wang)
- MAINTAINERS: kasan, kcov: add bugzilla links (Andrey Konovalov)
- mm: don't install PMD mappings when THPs are disabled by the hw/process/vma (David Hildenbrand)
- mm: huge_memory: add vma_thp_disabled() and thp_disabled_by_hw() (Kefeng Wang)
- Docs/damon/maintainer-profile: update deprecated awslabs GitHub URLs (SeongJae Park)
- Docs/damon/maintainer-profile: add missing '_' suffixes for external web links (SeongJae Park)
- maple_tree: check for MA_STATE_BULK on setting wr_rebalance (Sidhartha Kumar)
- mm: khugepaged: fix the arguments order in khugepaged_collapse_file trace point (Yang Shi)
- mm/damon/tests/sysfs-kunit.h: fix memory leak in damon_sysfs_test_add_targets() (Jinjie Ruan)
- mm: remove unused stub for can_swapin_thp() (Andy Shevchenko)
- mailmap: add an entry for Andy Chiu (Andy Chiu)
- MAINTAINERS: add memory mapping/VMA co-maintainers (Lorenzo Stoakes)
- fs/proc: fix build with GCC 15 due to -Werror=unterminated-string-initialization (Brahmajit Das)
- lib: alloc_tag_module_unload must wait for pending kfree_rcu calls (Florian Westphal)
- mm/mremap: fix move_normal_pmd/retract_page_tables race (Jann Horn)
- mm: percpu: increase PERCPU_DYNAMIC_SIZE_SHIFT on certain builds. (Sebastian Andrzej Siewior)
- selftests/mm: fix deadlock for fork after pthread_create on ARM (Edward Liaw)
- selftests/mm: replace atomic_bool with pthread_barrier_t (Edward Liaw)
- fat: fix uninitialized variable (OGAWA Hirofumi)
- nilfs2: propagate directory read errors from nilfs_find_entry() (Ryusuke Konishi)
- mm/mmap: correct error handling in mmap_region() (Lorenzo Stoakes)
- clk: test: Fix some memory leaks (Jinjie Ruan)
- clk: samsung: Fix out-of-bound access of of_match_node() (Jinjie Ruan)
- clk: rockchip: fix finding of maximum clock ID (Yao Zi)
- kasan: Disable Software Tag-Based KASAN with GCC (Will Deacon)
- Documentation/protection-keys: add AArch64 to documentation (Joey Gouly)
- arm64: set POR_EL0 for kernel threads (Joey Gouly)
- arm64: probes: Fix uprobes for big-endian kernels (Mark Rutland)
- arm64: probes: Fix simulate_ldr*_literal() (Mark Rutland)
- arm64: probes: Remove broken LDR (literal) uprobe support (Mark Rutland)
- firmware: arm_scmi: Queue in scmi layer for mailbox implementation (Justin Chen)
- firmware: arm_scmi: Give SMC transport precedence over mailbox (Florian Fainelli)
- firmware: arm_scmi: Fix the double free in scmi_debugfs_common_setup() (Su Hui)
- firmware: arm_ffa: Avoid string-fortify warning caused by memcpy() (Gavin Shan)
- firmware: arm_ffa: Avoid string-fortify warning in export_uuid() (Arnd Bergmann)
- arm64: dts: marvell: cn9130-sr-som: fix cp0 mdio pin numbers (Josua Mayer)
- reset: starfive: jh71x0: Fix accessing the empty member on JH7110 SoC (Changhuang Liang)
- reset: npcm: convert comma to semicolon (Yan Zhen)
- ARM: dts: bcm2837-rpi-cm3-io3: Fix HDMI hpd-gpio pin (Florian Klink)
- soc: fsl: cpm1: qmc: Fix unused data compilation warning (Herve Codina)
- soc: fsl: cpm1: qmc: Do not use IS_ERR_VALUE() on error pointers (Geert Uytterhoeven)
- Documentation/process: maintainer-soc: clarify submitting patches (Krzysztof Kozlowski)
- dmaengine: cirrus: check that output may be truncated (Alexander Sverdlin)
- dmaengine: cirrus: ERR_CAST() ioremap error (Alexander Sverdlin)
- MAINTAINERS: use the canonical soc mailing list address and mark it as L: (Konstantin Ryabitsev)
- ALSA: hda/conexant - Use cached pin control for Node 0x1d on HP EliteOne 1000 G2 (Vasiliy Kovalev)
- ALSA/hda: intel-sdw-acpi: add support for sdw-manager-list property read (Pierre-Louis Bossart)
- ALSA/hda: intel-sdw-acpi: simplify sdw-master-count property read (Pierre-Louis Bossart)
- ALSA/hda: intel-sdw-acpi: fetch fwnode once in sdw_intel_scan_controller() (Pierre-Louis Bossart)
- ALSA/hda: intel-sdw-acpi: cleanup sdw_intel_scan_controller (Pierre-Louis Bossart)
- ALSA: hda/tas2781: Add new quirk for Lenovo, ASUS, Dell projects (Baojun Xu)
- ALSA: scarlett2: Add error check after retrieving PEQ filter values (Zhu Jun)
- ALSA: hda/cs8409: Fix possible NULL dereference (Murad Masimov)
- sound: Make CONFIG_SND depend on INDIRECT_IOMEM instead of UML (Julian Vetter)
- ALSA: line6: update contact information (Markus Grabner)
- ALSA: usb-audio: Fix NULL pointer deref in snd_usb_power_domain_set() (Karol Kosik)
- ALSA: hda/conexant - Fix audio routing for HP EliteOne 1000 G2 (Vasiliy Kovalev)
- ALSA: hda: Sound support for HP Spectre x360 16 inch model 2024 (christoph.plattner)
- net/mlx5e: Don't call cleanup on profile rollback failure (Cosmin Ratiu)
- net/mlx5: Unregister notifier on eswitch init failure (Cosmin Ratiu)
- net/mlx5: Fix command bitmask initialization (Shay Drory)
- net/mlx5: Check for invalid vector index on EQ creation (Maher Sanalla)
- net/mlx5: HWS, use lock classes for bwc locks (Cosmin Ratiu)
- net/mlx5: HWS, don't destroy more bwc queue locks than allocated (Cosmin Ratiu)
- net/mlx5: HWS, fixed double free in error flow of definer layout (Yevgeny Kliteynik)
- net/mlx5: HWS, removed wrong access to a number of rules variable (Yevgeny Kliteynik)
- mptcp: pm: fix UaF read in mptcp_pm_nl_rm_addr_or_subflow (Matthieu Baerts (NGI0))
- net: ethernet: mtk_eth_soc: fix memory corruption during fq dma init (Felix Fietkau)
- vmxnet3: Fix packet corruption in vmxnet3_xdp_xmit_frame (Daniel Borkmann)
- net: dsa: vsc73xx: fix reception from VLAN-unaware bridges (Vladimir Oltean)
- net: ravb: Only advertise Rx/Tx timestamps if hardware supports it (Niklas Söderlund)
- net: microchip: vcap api: Fix memory leaks in vcap_api_encode_rule_test() (Jinjie Ruan)
- net: phy: mdio-bcm-unimac: Add BCM6846 support (Linus Walleij)
- dt-bindings: net: brcm,unimac-mdio: Add bcm6846-mdio (Linus Walleij)
- udp: Compute L4 checksum as usual when not segmenting the skb (Jakub Sitnicki)
- genetlink: hold RCU in genlmsg_mcast() (Eric Dumazet)
- net: dsa: mv88e6xxx: Fix the max_vid definition for the MV88E6361 (Peter Rashleigh)
- tcp/dccp: Don't use timer_pending() in reqsk_queue_unlink(). (Kuniyuki Iwashima)
- net: bcmasp: fix potential memory leak in bcmasp_xmit() (Wang Hai)
- net: systemport: fix potential memory leak in bcm_sysport_xmit() (Wang Hai)
- net: ethernet: rtsn: fix potential memory leak in rtsn_start_xmit() (Wang Hai)
- net: xilinx: axienet: fix potential memory leak in axienet_start_xmit() (Wang Hai)
- selftests: mptcp: join: test for prohibited MPC to port-based endp (Paolo Abeni)
- mptcp: prevent MPC handshake on port-based signal endpoints (Paolo Abeni)
- net/smc: Fix searching in list of known pnetids in smc_pnet_add_pnetid (Li RongQing)
- net: macb: Avoid 20s boot delay by skipping MDIO bus registration for fixed-link PHY (Oleksij Rempel)
- net: ethernet: aeroflex: fix potential memory leak in greth_start_xmit_gbit() (Wang Hai)
- netdevsim: use cond_resched() in nsim_dev_trap_report_work() (Eric Dumazet)
- macsec: don't increment counters for an unrelated SA (Sabrina Dubroca)
- octeontx2-af: Fix potential integer overflows on integer shifts (Colin Ian King)
- net: stmmac: dwmac-tegra: Fix link bring-up sequence (Paritosh Dixit)
- net: usb: usbnet: fix race in probe failure (Oliver Neukum)
- net/smc: Fix memory leak when using percpu refs (Kai Shen)
- net: lan743x: Remove duplicate check (Jinjie Ruan)
- posix-clock: Fix missing timespec64 check in pc_clock_settime() (Jinjie Ruan)
- MAINTAINERS: add Andrew Lunn as a co-maintainer of all networking drivers (Jakub Kicinski)
- selftests: drivers: net: fix name not defined (Alessandro Zanni)
- selftests: net/rds: add module not found (Alessandro Zanni)
- net: enetc: add missing static descriptor and inline keyword (Wei Fang)
- net: enetc: disable NAPI after all rings are disabled (Wei Fang)
- net: enetc: disable Tx BD rings after they are empty (Wei Fang)
- net: enetc: block concurrent XDP transmissions during ring reconfiguration (Wei Fang)
- net: enetc: remove xdp_drops statistic from enetc_xdp_drop() (Wei Fang)
- net: sparx5: fix source port register when mirroring (Daniel Machon)
- ipv4: give an IPv4 dev to blackhole_netdev (Xin Long)
- RDMA/bnxt_re: Fix the GID table length (Kalesh AP)
- RDMA/bnxt_re: Fix a bug while setting up Level-2 PBL pages (Bhargava Chenna Marreddy)
- RDMA/bnxt_re: Change the sequence of updating the CQ toggle value (Chandramohan Akula)
- RDMA/bnxt_re: Fix an error path in bnxt_re_add_device (Kalesh AP)
- RDMA/bnxt_re: Avoid CPU lockups due fifo occupancy check loop (Selvin Xavier)
- RDMA/bnxt_re: Fix a possible NULL pointer dereference (Kalesh AP)
- RDMA/bnxt_re: Return more meaningful error (Kalesh AP)
- RDMA/bnxt_re: Fix incorrect dereference of srq in async event (Kashyap Desai)
- RDMA/bnxt_re: Fix out of bound check (Kalesh AP)
- RDMA/bnxt_re: Fix the max CQ WQEs for older adapters (Abhishek Mohapatra)
- RDMA/srpt: Make slab cache names unique (Bart Van Assche)
- RDMA/irdma: Fix misspelling of "accept*" (Alexander Zubkov)
- RDMA/cxgb4: Fix RDMA_CM_EVENT_UNREACHABLE error for iWARP (Anumula Murali Mohan Reddy)
- RDMA/siw: Add sendpage_ok() check to disable MSG_SPLICE_PAGES (Showrya M N)
- RDMA/core: Fix ENODEV error for iWARP test over vlan (Anumula Murali Mohan Reddy)
- RDMA/nldev: Fix NULL pointer dereferences issue in rdma_nl_notify_event (Qianqiang Liu)
- RDMA/bnxt_re: Fix the max WQEs used in Static WQE mode (Selvin Xavier)
- RDMA/bnxt_re: Add a check for memory allocation (Kalesh AP)
- RDMA/bnxt_re: Fix incorrect AVID type in WQE structure (Saravanan Vajravel)
- RDMA/bnxt_re: Fix a possible memory leak (Kalesh AP)
- btrfs: fix uninitialized pointer free on read_alloc_one_name() error (Roi Martin)
- btrfs: send: cleanup unneeded return variable in changed_verity() (Christian Heusel)
- btrfs: fix uninitialized pointer free in add_inode_ref() (Roi Martin)
- btrfs: use sector numbers as keys for the dirty extents xarray (Filipe Manana)
- ksmbd: add support for supplementary groups (Namjae Jeon)
- ksmbd: fix user-after-free from session log off (Namjae Jeon)
- crypto: marvell/cesa - Disable hash algorithms (Herbert Xu)
- crypto: testmgr - Hide ENOENT errors better (Herbert Xu)
- crypto: api - Fix liveliness check in crypto_alg_tested (Herbert Xu)
- sched_ext: Remove unnecessary cpu_relax() (David Vernet)
- sched_ext: Don't hold scx_tasks_lock for too long (Tejun Heo)
- sched_ext: Move scx_tasks_lock handling into scx_task_iter helpers (Tejun Heo)
- sched_ext: bypass mode shouldn't depend on ops.select_cpu() (Tejun Heo)
- sched_ext: Move scx_buildin_idle_enabled check to scx_bpf_select_cpu_dfl() (Tejun Heo)
- sched_ext: Start schedulers with consistent p->scx.slice values (Tejun Heo)
- Revert "sched_ext: Use shorter slice while bypassing" (Tejun Heo)
- sched_ext: use correct function name in pick_task_scx() warning message (Honglei Wang)
- selftests: sched_ext: Add sched_ext as proper selftest target (Björn Töpel)
- ring-buffer: Fix reader locking when changing the sub buffer order (Petr Pavlu)
- ring-buffer: Fix refcount setting of boot mapped buffers (Steven Rostedt)
- bcachefs: Fix sysfs warning in fstests generic/730,731 (Kent Overstreet)
- bcachefs: Handle race between stripe reuse, invalidate_stripe_to_dev (Kent Overstreet)
- bcachefs: Fix kasan splat in new_stripe_alloc_buckets() (Kent Overstreet)
- bcachefs: Add missing validation for bch_stripe.csum_granularity_bits (Kent Overstreet)
- bcachefs: Fix missing bounds checks in bch2_alloc_read() (Kent Overstreet)
- bcachefs: fix uaf in bch2_dio_write_done() (Kent Overstreet)
- bcachefs: Improve check_snapshot_exists() (Kent Overstreet)
- bcachefs: Fix bkey_nocow_lock() (Kent Overstreet)
- bcachefs: Fix accounting replay flags (Kent Overstreet)
- bcachefs: Fix invalid shift in member_to_text() (Kent Overstreet)
- bcachefs: Fix bch2_have_enough_devs() for BCH_SB_MEMBER_INVALID (Kent Overstreet)
- bcachefs: __wait_for_freeing_inode: Switch to wait_bit_queue_entry (Kent Overstreet)
- bcachefs: Check if stuck in journal_res_get() (Kent Overstreet)
- closures: Add closure_wait_event_timeout() (Kent Overstreet)
- bcachefs: Fix state lock involved deadlock (Alan Huang)
- bcachefs: Fix NULL pointer dereference in bch2_opt_to_text (Mohammed Anees)
- bcachefs: Release transaction before wake up (Alan Huang)
- bcachefs: add check for btree id against max in try read node (Piotr Zalewski)
- bcachefs: Disk accounting device validation fixes (Kent Overstreet)
- bcachefs: bch2_inode_or_descendents_is_open() (Kent Overstreet)
- bcachefs: Kill bch2_propagate_key_to_snapshot_leaves() (Kent Overstreet)
- bcachefs: bcachefs_metadata_version_inode_has_child_snapshots (Kent Overstreet)
- bcachefs: Delete vestigal check_inode() checks (Kent Overstreet)
- bcachefs: btree_iter_peek_upto() now handles BTREE_ITER_all_snapshots (Kent Overstreet)
- bcachefs: reattach_inode() now correctly handles interior snapshot nodes (Kent Overstreet)
- bcachefs: Split out check_unreachable_inodes() pass (Kent Overstreet)
- bcachefs: Fix lockdep splat in bch2_accounting_read (Kent Overstreet)
- f2fs: allow parallel DIO reads (Jaegeuk Kim)
- erofs: get rid of kaddr in `struct z_erofs_maprecorder` (Gao Xiang)
- erofs: get rid of z_erofs_try_to_claim_pcluster() (Gao Xiang)
- erofs: ensure regular inodes for file-backed mounts (Gao Xiang)
- redhat: configs: decrease CONFIG_PCP_BATCH_SCALE_MAX (Rafael Aquini)
- redhat/configs: Enable CONFIG_RCU_TRACE in Fedora/REHL kernels (Waiman Long)
- HID: wacom: Hardcode (non-inverted) AES pens as BTN_TOOL_PEN (Jason Gerecke)
- HID: amd_sfh: Switch to device-managed dmam_alloc_coherent() (Basavaraj Natikar)
- HID: multitouch: Add quirk for HONOR MagicBook Art 14 touchpad (WangYuli)
- HID: multitouch: Add support for B2402FVA track point (Stefan Blum)
- HID: plantronics: Workaround for an unexcepted opposite volume key (Wade Wang)
- hid: intel-ish-hid: Fix uninitialized variable 'rv' in ish_fw_xfer_direct_dma (SurajSonawane2415)
- Linux 6.12-rc3 (Linus Torvalds)
- cifs: Fix creating native symlinks pointing to current or parent directory (Pali Rohár)
- cifs: Improve creating native symlinks pointing to directory (Pali Rohár)
- net/9p/usbg: Fix build error (Jinjie Ruan)
- USB: yurex: kill needless initialization in yurex_read (Oliver Neukum)
- Revert "usb: yurex: Replace snprintf() with the safer scnprintf() variant" (Oliver Neukum)
- usb: xhci: Fix problem with xhci resume from suspend (Jose Alberto Reguero)
- usb: misc: onboard_usb_dev: introduce new config symbol for usb5744 SMBus support (Radhey Shyam Pandey)
- usb: dwc3: core: Stop processing of pending events if controller is halted (Selvarasu Ganesan)
- usb: dwc3: re-enable runtime PM after failed resume (Roy Luo)
- usb: storage: ignore bogus device raised by JieLi BR21 USB sound chip (Icenowy Zheng)
- usb: gadget: core: force synchronous registration (John Keeping)
- mailmap: update mail for Fiona Behrens (Fiona Behrens)
- rust: device: change the from_raw() function (Guilherme Giacomo Simoes)
- powerpc/8xx: Fix kernel DTLB miss on dcbz (Christophe Leroy)
- scsi: scsi_transport_fc: Allow setting rport state to current state (Benjamin Marzinski)
- scsi: wd33c93: Don't use stale scsi_pointer value (Daniel Palmer)
- scsi: fnic: Move flush_work initialization out of if block (Martin Wilck)
- scsi: ufs: Use pre-calculated offsets in ufshcd_init_lrb() (Avri Altman)
- hwmon: (max1668) Add missing dependency on REGMAP_I2C (Javier Carrasco)
- hwmon: (ltc2991) Add missing dependency on REGMAP_I2C (Javier Carrasco)
- hwmon: (adt7470) Add missing dependency on REGMAP_I2C (Javier Carrasco)
- hwmon: (adm9240) Add missing dependency on REGMAP_I2C (Javier Carrasco)
- hwmon: (mc34vr500) Add missing dependency on REGMAP_I2C (Javier Carrasco)
- hwmon: (tmp513) Add missing dependency on REGMAP_I2C (Guenter Roeck)
- hwmon: (adt7475) Fix memory leak in adt7475_fan_pwm_config() (Javier Carrasco)
- hwmon: intel-m10-bmc-hwmon: relabel Columbiaville to CVL Die Temperature (Peter Colberg)
- ftrace/selftest: Test combination of function_graph tracer and function profiler (Steven Rostedt)
- selftests/rseq: Fix mm_cid test failure (Mathieu Desnoyers)
- selftests: vDSO: Explicitly include sched.h (Yu Liao)
- selftests: vDSO: improve getrandom and chacha error messages (Jason A. Donenfeld)
- selftests: vDSO: unconditionally build getrandom test (Jason A. Donenfeld)
- selftests: vDSO: unconditionally build chacha test (Jason A. Donenfeld)
- of: Skip kunit tests when arm64+ACPI doesn't populate root node (Stephen Boyd)
- of: Fix unbalanced of node refcount and memory leaks (Jinjie Ruan)
- dt-bindings: interrupt-controller: fsl,ls-extirq: workaround wrong interrupt-map number (Frank Li)
- dt-bindings: misc: fsl,qoriq-mc: remove ref for msi-parent (Frank Li)
- dt-bindings: display: elgin,jg10309-01: Add own binding (Fabio Estevam)
- fbdev: Switch back to struct platform_driver::remove() (Uwe Kleine-König)
- gpio: aspeed: Use devm_clk api to manage clock source (Billy Tsai)
- gpio: aspeed: Add the flush write to ensure the write complete. (Billy Tsai)
- NFS: remove revoked delegation from server's delegation list (Dai Ngo)
- nfsd/localio: fix nfsd_file tracepoints to handle NULL rqstp (Mike Snitzer)
- nfs_common: fix Kconfig for NFS_COMMON_LOCALIO_SUPPORT (Mike Snitzer)
- nfs_common: fix race in NFS calls to nfsd_file_put_local() and nfsd_serv_put() (Mike Snitzer)
- NFSv4: Prevent NULL-pointer dereference in nfs42_complete_copies() (Yanjun Zhang)
- SUNRPC: Fix integer overflow in decode_rc_list() (Dan Carpenter)
- sunrpc: fix prog selection loop in svc_process_common (NeilBrown)
- nfs: Remove duplicated include in localio.c (Yang Li)
- rcu/nocb: Fix rcuog wake-up from offline softirq (Frederic Weisbecker)
- x86/xen: mark boot CPU of PV guest in MSR_IA32_APICBASE (Juergen Gross)
- io_uring/rw: allow pollable non-blocking attempts for !FMODE_NOWAIT (Jens Axboe)
- io_uring/rw: fix cflags posting for single issue multishot read (Jens Axboe)
- thermal: intel: int340x: processor: Add MMIO RAPL PL4 support (Zhang Rui)
- thermal: intel: int340x: processor: Remove MMIO RAPL CPU hotplug support (Zhang Rui)
- powercap: intel_rapl_msr: Add PL4 support for Arrowlake-U (Sumeet Pawnikar)
- powercap: intel_rapl_tpmi: Ignore minor version change (Zhang Rui)
- thermal: intel: int340x: processor: Fix warning during module unload (Zhang Rui)
- powercap: intel_rapl_tpmi: Fix bogus register reading (Zhang Rui)
- thermal: core: Free tzp copy along with the thermal zone (Rafael J. Wysocki)
- thermal: core: Reference count the zone in thermal_zone_get_by_id() (Rafael J. Wysocki)
- ACPI: resource: Fold Asus Vivobook Pro N6506M* DMI quirks together (Hans de Goede)
- ACPI: resource: Fold Asus ExpertBook B1402C* and B1502C* DMI quirks together (Hans de Goede)
- ACPI: resource: Make Asus ExpertBook B2502 matches cover more models (Hans de Goede)
- ACPI: resource: Make Asus ExpertBook B2402 matches cover more models (Hans de Goede)
- PM: domains: Fix alloc/free in dev_pm_domain_attach|detach_list() (Ulf Hansson)
- Revert "drm/tegra: gr3d: Convert into dev_pm_domain_attach|detach_list()" (Ulf Hansson)
- pmdomain: qcom-cpr: Fix the return of uninitialized variable (Zhang Zekun)
- OPP: fix error code in dev_pm_opp_set_config() (Dan Carpenter)
- mmc: sdhci-of-dwcmshc: Prevent stale command interrupt handling (Michal Wilczynski)
- Revert "mmc: mvsdio: Use sg_miter for PIO" (Linus Walleij)
- mmc: core: Only set maximum DMA segment size if DMA is supported (Guenter Roeck)
- ata: libata: Update MAINTAINERS file (Damien Le Moal)
- ata: libata: avoid superfluous disk spin down + spin up during hibernation (Niklas Cassel)
- drm/xe: Make wedged_mode debugfs writable (Matt Roper)
- drm/xe: Restore GT freq on GSC load error (Vinay Belgaumkar)
- drm/xe/guc_submit: fix xa_store() error checking (Matthew Auld)
- drm/xe/ct: fix xa_store() error checking (Matthew Auld)
- drm/xe/ct: prevent UAF in send_recv() (Matthew Auld)
- drm/fbdev-dma: Only cleanup deferred I/O if necessary (Janne Grunau)
- nouveau/dmem: Fix vulnerability in migrate_to_ram upon copy error (Yonatan Maman)
- nouveau/dmem: Fix privileged error in copy engine channel (Yonatan Maman)
- drm/vc4: Stop the active perfmon before being destroyed (Maíra Canal)
- drm/v3d: Stop the active perfmon before being destroyed (Maíra Canal)
- drm/nouveau/gsp: remove extraneous ; after mutex (Colin Ian King)
- drm/xe: Drop GuC submit_wq pool (Matthew Brost)
- drm/sched: Use drm sched lockdep map for submit_wq (Matthew Brost)
- drm/i915/hdcp: fix connector refcounting (Jani Nikula)
- drm/radeon: always set GEM function pointer (Christian König)
- drm/amd/display: fix hibernate entry for DCN35+ (Hamza Mahfooz)
- drm/amd/display: Clear update flags after update has been applied (Josip Pavic)
- drm/amdgpu: partially revert powerplay `__counted_by` changes (Alex Deucher)
- drm/radeon: add late_register for connector (Wu Hoi Pok)
- drm/amdkfd: Fix an eviction fence leak (Lang Yu)
- fedora: distable RTL8192E wifi driver (Peter Robinson)
- common: arm64: Fixup and cleanup some SCMI options (Peter Robinson)
- common: Cleanup ARM_SCMI_TRANSPORT options (Peter Robinson)
- v6.12-rc2-rt4 (Sebastian Andrzej Siewior)
- sched: Replace PREEMPT_AUTO with LAZY_PREEMPT. (Sebastian Andrzej Siewior)
- softirq: Clean white space. (Sebastian Andrzej Siewior)
- mm: percpu: Increase PERCPU_DYNAMIC_SIZE_SHIFT on certain builds. (Sebastian Andrzej Siewior)
- ARM: vfp: Rename the locking functions. (Sebastian Andrzej Siewior)
- v6.12-rc2-rt3 (Sebastian Andrzej Siewior)
- MAINTAINERS: Add headers and mailing list to UDP section (Simon Horman)
- MAINTAINERS: consistently exclude wireless files from NETWORKING [GENERAL] (Simon Horman)
- slip: make slhc_remember() more robust against malicious packets (Eric Dumazet)
- net/smc: fix lacks of icsk_syn_mss with IPPROTO_SMC (D. Wythe)
- ppp: fix ppp_async_encode() illegal access (Eric Dumazet)
- docs: netdev: document guidance on cleanup patches (Simon Horman)
- phonet: Handle error of rtnl_register_module(). (Kuniyuki Iwashima)
- mpls: Handle error of rtnl_register_module(). (Kuniyuki Iwashima)
- mctp: Handle error of rtnl_register_module(). (Kuniyuki Iwashima)
- bridge: Handle error of rtnl_register_module(). (Kuniyuki Iwashima)
- vxlan: Handle error of rtnl_register_module(). (Kuniyuki Iwashima)
- rtnetlink: Add bulk registration helpers for rtnetlink message handlers. (Kuniyuki Iwashima)
- selftests: netfilter: conntrack_vrf.sh: add fib test case (Florian Westphal)
- netfilter: fib: check correct rtable in vrf setups (Florian Westphal)
- netfilter: xtables: avoid NFPROTO_UNSPEC where needed (Florian Westphal)
- net: do not delay dst_entries_add() in dst_release() (Eric Dumazet)
- e1000e: change I219 (19) devices to ADP (Vitaly Lifshits)
- igb: Do not bring the device up after non-fatal error (Mohamed Khalfella)
- i40e: Fix macvlan leak by synchronizing access to mac_filter_hash (Aleksandr Loktionov)
- ice: Fix increasing MSI-X on VF (Marcin Szycik)
- ice: Flush FDB entries before reset (Wojciech Drewek)
- ice: Fix netif_is_ice() in Safe Mode (Marcin Szycik)
- ice: Fix entering Safe Mode (Marcin Szycik)
- mptcp: pm: do not remove closing subflows (Matthieu Baerts (NGI0))
- mptcp: fallback when MPTCP opts are dropped after 1st data (Matthieu Baerts (NGI0))
- tcp: fix mptcp DSS corruption due to large pmtu xmit (Paolo Abeni)
- mptcp: handle consistently DSS corruption (Paolo Abeni)
- net: netconsole: fix wrong warning (Breno Leitao)
- net: dsa: refuse cross-chip mirroring operations (Vladimir Oltean)
- net: fec: don't save PTP state if PTP is unsupported (Wei Fang)
- net: ibm: emac: mal: add dcr_unmap to _remove (Rosen Penev)
- net: ftgmac100: fixed not check status from fixed phy (Jacky Chou)
- net: hns3/hns: Update the maintainer for the HNS3/HNS ethernet driver (Jijie Shao)
- sctp: ensure sk_state is set to CLOSED if hashing fails in sctp_listen_start (Xin Long)
- net: amd: mvme147: Fix probe banner message (Daniel Palmer)
- net: phy: realtek: Fix MMD access on RTL8126A-integrated PHY (Heiner Kallweit)
- net: ti: icssg-prueth: Fix race condition for VLAN table access (MD Danish Anwar)
- net: ibm: emac: mal: fix wrong goto (Rosen Penev)
- net/sched: accept TCA_STAB only for root qdisc (Eric Dumazet)
- selftests: make kselftest-clean remove libynl outputs (Greg Thelen)
- selftests: net: rds: add gitignore file for include.sh (Javier Carrasco)
- selftests: net: rds: add include.sh to EXTRA_CLEAN (Javier Carrasco)
- selftests: net: add msg_oob to gitignore (Javier Carrasco)
- net: dsa: b53: fix jumbo frames on 10/100 ports (Jonas Gorski)
- net: dsa: b53: allow lower MTUs on BCM5325/5365 (Jonas Gorski)
- net: dsa: b53: fix max MTU for BCM5325/BCM5365 (Jonas Gorski)
- net: dsa: b53: fix max MTU for 1g switches (Jonas Gorski)
- net: dsa: b53: fix jumbo frame mtu check (Jonas Gorski)
- net: ethernet: ti: am65-cpsw: avoid devm_alloc_etherdev, fix module removal (Nicolas Pitre)
- net: ethernet: ti: am65-cpsw: prevent WARN_ON upon module removal (Nicolas Pitre)
- net: airoha: Update tx cpu dma ring idx at the end of xmit loop (Lorenzo Bianconi)
- net: phy: Remove LED entry from LEDs list on unregister (Christian Marangi)
- Bluetooth: btusb: Don't fail external suspend requests (Luiz Augusto von Dentz)
- Bluetooth: hci_conn: Fix UAF in hci_enhanced_setup_sync (Luiz Augusto von Dentz)
- Bluetooth: RFCOMM: FIX possible deadlock in rfcomm_sk_state_change (Luiz Augusto von Dentz)
- net: ethernet: adi: adin1110: Fix some error handling path in adin1110_read_fifo() (Christophe JAILLET)
- Revert "net: stmmac: set PP_FLAG_DMA_SYNC_DEV only if XDP is enabled" (Jakub Kicinski)
- net: dsa: lan9303: ensure chip reset and wait for READY status (Anatolij Gustschin)
- net: explicitly clear the sk pointer, when pf->create fails (Ignat Korchagin)
- net: phy: bcm84881: Fix some error handling paths (Christophe JAILLET)
- net: Fix an unsafe loop on the list (Anastasia Kovaleva)
- net: pse-pd: Fix enabled status mismatch (Kory Maincent)
- selftests: net: no_forwarding: fix VID for $swp2 in one_bridge_two_pvids() test (Kacper Ludwinski)
- ibmvnic: Inspect header requirements before using scrq direct (Nick Child)
- selftests: add regression test for br_netfilter panic (Andy Roulin)
- netfilter: br_netfilter: fix panic with metadata_dst skb (Andy Roulin)
- net: dsa: sja1105: fix reception from VLAN-unaware bridges (Vladimir Oltean)
- idpf: deinit virtchnl transaction manager after vport and vectors (Larysa Zaremba)
- idpf: use actual mbx receive payload length (Joshua Hay)
- idpf: fix VF dynamic interrupt ctl register initialization (Ahmed Zaki)
- ice: fix VLAN replay after reset (Dave Ertman)
- ice: disallow DPLL_PIN_STATE_SELECTABLE for dpll output pins (Arkadiusz Kubalewski)
- ice: fix memleak in ice_init_tx_topology() (Przemek Kitszel)
- ice: clear port vlan config during reset (Michal Swiatkowski)
- ice: Fix improper handling of refcount in ice_sriov_set_msix_vec_count() (Gui-Dong Han)
- ice: Fix improper handling of refcount in ice_dpll_init_rclk_pins() (Gui-Dong Han)
- ice: set correct dst VSI in only LAN filters (Michal Swiatkowski)
- Documentation: networking/tcp_ao: typo and grammar fixes (Leo Stone)
- rxrpc: Fix uninitialised variable in rxrpc_send_data() (David Howells)
- rxrpc: Fix a race between socket set up and I/O thread creation (David Howells)
- tcp: fix TFO SYN_RECV to not zero retrans_stamp with retransmits out (Neal Cardwell)
- tcp: fix tcp_enter_recovery() to zero retrans_stamp when it's safe (Neal Cardwell)
- tcp: fix to allow timestamp undo if no retransmits were sent (Neal Cardwell)
- net: phy: aquantia: remove usage of phy_set_max_speed (Abhishek Chauhan)
- net: phy: aquantia: AQR115c fix up PMA capabilities (Abhishek Chauhan)
- sfc: Don't invoke xdp_do_flush() from netpoll. (Sebastian Andrzej Siewior)
- net: phy: dp83869: fix memory corruption when enabling fiber (Ingo van Lil)
- ring-buffer: Do not have boot mapped buffers hook to CPU hotplug (Steven Rostedt)
- btrfs: fix clear_dirty and writeback ordering in submit_one_sector() (Naohiro Aota)
- btrfs: zoned: fix missing RCU locking in error message when loading zone info (Filipe Manana)
- btrfs: fix missing error handling when adding delayed ref with qgroups enabled (Filipe Manana)
- btrfs: add cancellation points to trim loops (Luca Stefani)
- btrfs: split remaining space to discard in chunks (Luca Stefani)
- nfsd: fix possible badness in FREE_STATEID (Olga Kornievskaia)
- nfsd: nfsd_destroy_serv() must call svc_destroy() even if nfsd_startup_net() failed (NeilBrown)
- NFSD: Mark filecache "down" if init fails (Chuck Lever)
- xfs: fix a typo (Andrew Kreimer)
- xfs: don't free cowblocks from under dirty pagecache on unshare (Brian Foster)
- xfs: skip background cowblock trims on inodes open for write (Brian Foster)
- xfs: support lowmode allocations in xfs_bmap_exact_minlen_extent_alloc (Christoph Hellwig)
- xfs: call xfs_bmap_exact_minlen_extent_alloc from xfs_bmap_btalloc (Christoph Hellwig)
- xfs: don't ifdef around the exact minlen allocations (Christoph Hellwig)
- xfs: fold xfs_bmap_alloc_userdata into xfs_bmapi_allocate (Christoph Hellwig)
- xfs: distinguish extra split from real ENOSPC from xfs_attr_node_try_addname (Christoph Hellwig)
- xfs: distinguish extra split from real ENOSPC from xfs_attr3_leaf_split (Christoph Hellwig)
- xfs: return bool from xfs_attr3_leaf_add (Christoph Hellwig)
- xfs: merge xfs_attr_leaf_try_add into xfs_attr_leaf_addname (Christoph Hellwig)
- xfs: Use try_cmpxchg() in xlog_cil_insert_pcp_aggregate() (Uros Bizjak)
- xfs: scrub: convert comma to semicolon (Yan Zhen)
- xfs: Remove empty declartion in header file (Zhang Zekun)
- MAINTAINERS: add Carlos Maiolino as XFS release manager (Chandan Babu R)
- configs: fedora/x86: Set CONFIG_CRYPTO_DEV_CCP_DD=y (Hans de Goede)
- mm: zswap: delete comments for "value" member of 'struct zswap_entry'. (Kanchana P Sridhar)
- CREDITS: sort alphabetically by name (Krzysztof Kozlowski)
- secretmem: disable memfd_secret() if arch cannot set direct map (Patrick Roy)
- .mailmap: update Fangrui's email (Fangrui Song)
- mm/huge_memory: check pmd_special() only after pmd_present() (David Hildenbrand)
- resource, kunit: fix user-after-free in resource_test_region_intersects() (Huang Ying)
- fs/proc/kcore.c: allow translation of physical memory addresses (Alexander Gordeev)
- selftests/mm: fix incorrect buffer->mirror size in hmm2 double_map test (Donet Tom)
- device-dax: correct pgoff align in dax_set_mapping() (Kun(llfl))
- kthread: unpark only parked kthread (Frederic Weisbecker)
- Revert "mm: introduce PF_MEMALLOC_NORECLAIM, PF_MEMALLOC_NOWARN" (Michal Hocko)
- bcachefs: do not use PF_MEMALLOC_NORECLAIM (Michal Hocko)
- misc: sgi-gru: Don't disable preemption in GRU driver (Dimitri Sivanich)
- unicode: Don't special case ignorable code points (Gabriel Krisman Bertazi)
- sched_ext: Documentation: Update instructions for running example schedulers (Devaansh-Kumar)
- sched_ext, scx_qmap: Add and use SCX_ENQ_CPU_SELECTED (Tejun Heo)
- sched/core: Add ENQUEUE_RQ_SELECTED to indicate whether ->select_task_rq() was called (Tejun Heo)
- sched/core: Make select_task_rq() take the pointer to wake_flags instead of value (Tejun Heo)
- sched_ext: scx_cgroup_exit() may be called without successful scx_cgroup_init() (Tejun Heo)
- sched_ext: Improve error reporting during loading (Tejun Heo)
- sched_ext: Add __weak markers to BPF helper function decalarations (Vishal Chourasia)
- fs/ntfs3: Format output messages like others fs in kernel (Konstantin Komarov)
- fs/ntfs3: Additional check in ntfs_file_release (Konstantin Komarov)
- fs/ntfs3: Fix general protection fault in run_is_mapped_full (Konstantin Komarov)
- fs/ntfs3: Sequential field availability check in mi_enum_attr() (Konstantin Komarov)
- fs/ntfs3: Additional check in ni_clear() (Konstantin Komarov)
- fs/ntfs3: Fix possible deadlock in mi_read (Konstantin Komarov)
- ntfs3: Change to non-blocking allocation in ntfs_d_hash (Diogo Jahchan Koike)
- fs/ntfs3: Remove unused al_delete_le (Dr. David Alan Gilbert)
- fs/ntfs3: Rename ntfs3_setattr into ntfs_setattr (Konstantin Komarov)
- fs/ntfs3: Replace fsparam_flag_no -> fsparam_flag (Konstantin Komarov)
- fs/ntfs3: Add support for the compression attribute (Konstantin Komarov)
- fs/ntfs3: Implement fallocate for compressed files (Konstantin Komarov)
- fs/ntfs3: Make checks in run_unpack more clear (Konstantin Komarov)
- fs/ntfs3: Add rough attr alloc_size check (Konstantin Komarov)
- fs/ntfs3: Stale inode instead of bad (Konstantin Komarov)
- fs/ntfs3: Refactor enum_rstbl to suppress static checker (Konstantin Komarov)
- fs/ntfs3: Fix sparse warning in ni_fiemap (Konstantin Komarov)
- fs/ntfs3: Fix warning possible deadlock in ntfs_set_state (Konstantin Komarov)
- fs/ntfs3: Fix sparse warning for bigendian (Konstantin Komarov)
- fs/ntfs3: Separete common code for file_read/write iter/splice (Konstantin Komarov)
- fs/ntfs3: Optimize large writes into sparse file (Konstantin Komarov)
- fs/ntfs3: Do not call file_modified if collapse range failed (Konstantin Komarov)
- fs/ntfs3: Check if more than chunk-size bytes are written (Andrew Ballance)
- ntfs3: Add bounds checking to mi_enum_attr() (lei lu)
- fs/ntfs3: Use swap() to improve code (Thorsten Blum)
- perf cs-etm: Fix the assert() to handle captured and unprocessed cpu trace (Ilkka Koskinen)
- perf build: Fix build feature-dwarf_getlocations fail for old libdw (Yang Jihong)
- perf build: Fix static compilation error when libdw is not installed (Yang Jihong)
- perf dwarf-aux: Fix build with !HAVE_DWARF_GETLOCATIONS_SUPPORT (James Clark)
- tools headers arm64: Sync arm64's cputype.h with the kernel sources (Arnaldo Carvalho de Melo)
- perf tools: Cope with differences for lib/list_sort.c copy from the kernel (Arnaldo Carvalho de Melo)
- tools check_headers.sh: Add check variant that excludes some hunks (Arnaldo Carvalho de Melo)
- perf beauty: Update copy of linux/socket.h with the kernel sources (Arnaldo Carvalho de Melo)
- tools headers UAPI: Sync the linux/in.h with the kernel sources (Arnaldo Carvalho de Melo)
- perf trace beauty: Update the arch/x86/include/asm/irq_vectors.h copy with the kernel sources (Arnaldo Carvalho de Melo)
- tools arch x86: Sync the msr-index.h copy with the kernel sources (Arnaldo Carvalho de Melo)
- tools include UAPI: Sync linux/fcntl.h copy with the kernel sources (Arnaldo Carvalho de Melo)
- tools include UAPI: Sync linux/sched.h copy with the kernel sources (Arnaldo Carvalho de Melo)
- tools include UAPI: Sync sound/asound.h copy with the kernel sources (Arnaldo Carvalho de Melo)
- perf vdso: Missed put on 32-bit dsos (Ian Rogers)
- perf symbol: Set binary_type of dso when loading (Namhyung Kim)
- Turn on ZRAM_WRITEBACK for Fedora (Justin M. Forbes)
- vhost/scsi: null-ptr-dereference in vhost_scsi_get_req() (Haoran Zhang)
- vsock/virtio: use GFP_ATOMIC under RCU read lock (Michael S. Tsirkin)
- virtio_console: fix misc probe bugs (Michael S. Tsirkin)
- virtio_ring: tag event_triggered as racy for KCSAN (Michael S. Tsirkin)
- vdpa/octeon_ep: Fix format specifier for pointers in debug messages (Srujana Challa)
- configs: rhel: Fix designware I2C controllers related config settings (Hans de Goede)
- Enable CONFIG_DMA_NUMA_CMA for x86_64 and aarch64 (Chris von Recklinghausen)
- new config in drivers/phy (Izabela Bakollari)
- configs: fedora: Unset CONFIG_I2C_DESIGNWARE_CORE on s390x (Hans de Goede)
- configs: fedora: Drop duplicate CONFIG_I2C_DESIGNWARE_CORE for x86_64 and aarch64 (Hans de Goede)
- Enable DESIGNWARE_CORE for ppc as well (Justin M. Forbes)
- Fix up I2C_DESIGNWARE_CORE config for Fedora (Justin M. Forbes)
- Linux 6.12-rc2 (Linus Torvalds)
- kbuild: deb-pkg: Remove blank first line from maint scripts (Aaron Thompson)
- kbuild: fix a typo dt_binding_schema -> dt_binding_schemas (Xu Yang)
- scripts: import more list macros (Sami Tolvanen)
- kconfig: qconf: fix buffer overflow in debug links (Masahiro Yamada)
- kconfig: qconf: move conf_read() before drawing tree pain (Masahiro Yamada)
- kconfig: clear expr::val_is_valid when allocated (Masahiro Yamada)
- kconfig: fix infinite loop in sym_calc_choice() (Masahiro Yamada)
- kbuild: move non-boot built-in DTBs to .rodata section (Masahiro Yamada)
- platform/x86: x86-android-tablets: Fix use after free on platform_device_register() errors (Hans de Goede)
- platform/x86: wmi: Update WMI driver API documentation (Armin Wolf)
- platform/x86: dell-ddv: Fix typo in documentation (Anaswara T Rajan)
- platform/x86: dell-sysman: add support for alienware products (Crag Wang)
- platform/x86/intel: power-domains: Add Diamond Rapids support (Srinivas Pandruvada)
- platform/x86: ISST: Add Diamond Rapids to support list (Srinivas Pandruvada)
- platform/x86:intel/pmc: Disable ACPI PM Timer disabling on Sky and Kaby Lake (Hans de Goede)
- platform/x86: dell-laptop: Do not fail when encountering unsupported batteries (Armin Wolf)
- MAINTAINERS: Update Intel In Field Scan(IFS) entry (Jithu Joseph)
- platform/x86: ISST: Fix the KASAN report slab-out-of-bounds bug (Zach Wade)
- KVM: arm64: Fix kvm_has_feat*() handling of negative features (Marc Zyngier)
- KVM: arm64: Another reviewer reshuffle (Marc Zyngier)
- KVM: arm64: Constrain the host to the maximum shared SVE VL with pKVM (Mark Brown)
- KVM: arm64: Fix __pkvm_init_vcpu cptr_el2 error path (Vincent Donnefort)
- x86/reboot: emergency callbacks are now registered by common KVM code (Paolo Bonzini)
- KVM: x86: leave kvm.ko out of the build if no vendor module is requested (Paolo Bonzini)
- KVM: x86/mmu: fix KVM_X86_QUIRK_SLOT_ZAP_ALL for shadow MMU (Paolo Bonzini)
- KVM: selftests: Fix build on architectures other than x86_64 (Mark Brown)
- powerpc/vdso: allow r30 in vDSO code generation of getrandom (Jason A. Donenfeld)
- bcachefs: Rework logged op error handling (Kent Overstreet)
- bcachefs: Add warn param to subvol_get_snapshot, peek_inode (Kent Overstreet)
- bcachefs: Kill snapshot arg to fsck_write_inode() (Kent Overstreet)
- bcachefs: Check for unlinked, non-empty dirs in check_inode() (Kent Overstreet)
- bcachefs: Check for unlinked inodes with dirents (Kent Overstreet)
- bcachefs: Check for directories with no backpointers (Kent Overstreet)
- bcachefs: Kill alloc_v4.fragmentation_lru (Kent Overstreet)
- bcachefs: minor lru fsck fixes (Kent Overstreet)
- bcachefs: Mark more errors AUTOFIX (Kent Overstreet)
- bcachefs: Make sure we print error that causes fsck to bail out (Kent Overstreet)
- bcachefs: bkey errors are only AUTOFIX during read (Kent Overstreet)
- bcachefs: Create lost+found in correct snapshot (Kent Overstreet)
- bcachefs: Fix reattach_inode() (Kent Overstreet)
- bcachefs: Add missing wakeup to bch2_inode_hash_remove() (Kent Overstreet)
- bcachefs: Fix trans_commit disk accounting revert (Kent Overstreet)
- bcachefs: Fix bch2_inode_is_open() check (Kent Overstreet)
- bcachefs: Fix return type of dirent_points_to_inode_nowarn() (Kent Overstreet)
- bcachefs: Fix bad shift in bch2_read_flag_list() (Kent Overstreet)
- xen: Fix config option reference in XEN_PRIVCMD definition (Lukas Bulwahn)
- ext4: fix off by one issue in alloc_flex_gd() (Baokun Li)
- ext4: mark fc as ineligible using an handle in ext4_xattr_set() (Luis Henriques (SUSE))
- ext4: use handle to mark fc as ineligible in __track_dentry_update() (Luis Henriques (SUSE))
- EINJ, CXL: Fix CXL device SBDF calculation (Ben Cheatham)
- i2c: stm32f7: Do not prepare/unprepare clock during runtime suspend/resume (Marek Vasut)
- spi: spi-cadence: Fix missing spi_controller_is_target() check (Jinjie Ruan)
- spi: spi-cadence: Fix pm_runtime_set_suspended() with runtime pm enabled (Jinjie Ruan)
- spi: spi-imx: Fix pm_runtime_set_suspended() with runtime pm enabled (Jinjie Ruan)
- spi: s3c64xx: fix timeout counters in flush_fifo (Ben Dooks)
- spi: atmel-quadspi: Fix wrong register value written to MR (Alexander Dahl)
- MAINTAINERS: Add security/Kconfig.hardening to hardening section (Nathan Chancellor)
- hardening: Adjust dependencies in selection of MODVERSIONS (Nathan Chancellor)
- MAINTAINERS: Add unsafe_memcpy() to the FORTIFY review list (Kees Cook)
- tomoyo: revert CONFIG_SECURITY_TOMOYO_LKM support (Paul Moore)
- selftests: breakpoints: use remaining time to check if suspend succeed (Yifei Liu)
- kselftest/devices/probe: Fix SyntaxWarning in regex strings for Python3 (Alessandro Zanni)
- selftest: hid: add missing run-hid-tools-tests.sh (Yun Lu)
- selftests: vDSO: align getrandom states to cache line (Jason A. Donenfeld)
- selftests: exec: update gitignore for load_address (Javier Carrasco)
- selftests: core: add unshare_test to gitignore (Javier Carrasco)
- clone3: clone3_cap_checkpoint_restore: remove unused MAX_PID_NS_LEVEL macro (Ba Jing)
- selftests:timers: posix_timers: Fix warn_unused_result in __fatal_error() (Shuah Khan)
- selftest: rtc: Check if could access /dev/rtc0 before testing (Joseph Jang)
- arm64: Subscribe Microsoft Azure Cobalt 100 to erratum 3194386 (Easwar Hariharan)
- arm64: fix selection of HAVE_DYNAMIC_FTRACE_WITH_ARGS (Mark Rutland)
- arm64: errata: Expand speculative SSBS workaround once more (Mark Rutland)
- arm64: cputype: Add Neoverse-N3 definitions (Mark Rutland)
- arm64: Force position-independent veneers (Mark Rutland)
- riscv: Fix kernel stack size when KASAN is enabled (Alexandre Ghiti)
- drivers/perf: riscv: Align errno for unsupported perf event (Pu Lehui)
- tracing/hwlat: Fix a race during cpuhp processing (Wei Li)
- tracing/timerlat: Fix a race during cpuhp processing (Wei Li)
- tracing/timerlat: Drop interface_lock in stop_kthread() (Wei Li)
- tracing/timerlat: Fix duplicated kthread creation due to CPU online/offline (Wei Li)
- x86/ftrace: Include <asm/ptrace.h> (Sami Tolvanen)
- rtla: Fix the help text in osnoise and timerlat top tools (Eder Zulian)
- tools/rtla: Fix installation from out-of-tree build (Ben Hutchings)
- tracing: Fix trace_check_vprintf() when tp_printk is used (Steven Rostedt)
- slub/kunit: skip test_kfree_rcu when the slub kunit test is built-in (Vlastimil Babka)
- mm, slab: suppress warnings in test_leak_destroy kunit test (Vlastimil Babka)
- rcu/kvfree: Refactor kvfree_rcu_queue_batch() (Uladzislau Rezki (Sony))
- mm, slab: fix use of SLAB_SUPPORTS_SYSFS in kmem_cache_release() (Nilay Shroff)
- ACPI: battery: Fix possible crash when unregistering a battery hook (Armin Wolf)
- ACPI: battery: Simplify battery hook locking (Armin Wolf)
- ACPI: video: Add backlight=native quirk for Dell OptiPlex 5480 AIO (Hans de Goede)
- ACPI: resource: Add Asus ExpertBook B2502CVA to irq1_level_low_skip_override[] (Hans de Goede)
- ACPI: resource: Add Asus Vivobook X1704VAP to irq1_level_low_skip_override[] (Hans de Goede)
- ACPI: resource: Loosen the Asus E1404GAB DMI match to also cover the E1404GA (Hans de Goede)
- ACPI: resource: Remove duplicate Asus E1504GAB IRQ override (Hans de Goede)
- cpufreq: Avoid a bad reference count on CPU node (Miquel Sabaté Solà)
- cpufreq: intel_pstate: Make hwp_notify_lock a raw spinlock (Uwe Kleine-König)
- gpiolib: Fix potential NULL pointer dereference in gpiod_get_label() (Lad Prabhakar)
- gpio: davinci: Fix condition for irqchip registration (Vignesh Raghavendra)
- gpio: davinci: fix lazy disable (Emanuele Ghidoli)
- ALSA: hda/conexant: Fix conflicting quirk for System76 Pangolin (Takashi Iwai)
- ALSA: line6: add hw monitor volume control to POD HD500X (Hans P. Moller)
- ALSA: gus: Fix some error handling paths related to get_bpos() usage (Christophe JAILLET)
- ALSA: hda: Add missing parameter description for snd_hdac_stream_timecounter_init() (Takashi Iwai)
- ALSA: usb-audio: Add native DSD support for Luxman D-08u (Jan Lalinsky)
- ALSA: core: add isascii() check to card ID generator (Jaroslav Kysela)
- MAINTAINERS: ALSA: use linux-sound@vger.kernel.org list (Jaroslav Kysela)
- ASoC: qcom: sm8250: add qrb4210-rb2-sndcard compatible string (Alexey Klimov)
- ASoC: dt-bindings: qcom,sm8250: add qrb4210-rb2-sndcard (Alexey Klimov)
- ASoC: intel: sof_sdw: Add check devm_kasprintf() returned value (Charles Han)
- ASoC: imx-card: Set card.owner to avoid a warning calltrace if SND=m (Hui Wang)
- ASoC: dt-bindings: davinci-mcasp: Fix interrupts property (Miquel Raynal)
- ASoC: Intel: soc-acpi: arl: Fix some missing empty terminators (Charles Keepax)
- ASoC: Intel: soc-acpi-intel-rpl-match: add missing empty item (Bard Liao)
- ASoC: fsl_sai: Enable 'FIFO continue on error' FCONT bit (Shengjiu Wang)
- ASoC: dt-bindings: renesas,rsnd: correct reg-names for R-Car Gen1 (Wolfram Sang)
- ASoC: codecs: lpass-rx-macro: add missing CDC_RX_BCL_VBAT_RF_PROC2 to default regs values (Alexey Klimov)
- ASoC: atmel: mchp-pdmc: Skip ALSA restoration if substream runtime is uninitialized (Andrei Simion)
- ASoC: cs35l45: Corrects cs35l45_get_clk_freq_id function data type (Ricardo Rivera-Matos)
- ASoC: topology: Fix incorrect addressing assignments (Tang Bin)
- ASoC: amd: yc: Add quirk for HP Dragonfly pro one (David Lawrence Glanzman)
- ASoC: amd: acp: don't set card long_name (Vijendar Mukunda)
- Revert "ALSA: hda: Conditionally use snooping for AMD HDMI" (Takashi Iwai)
- ALSA: hda: fix trigger_tstamp_latched (Jaroslav Kysela)
- ALSA: hda/realtek: Add a quirk for HP Pavilion 15z-ec200 (Abhishek Tamboli)
- ALSA: hda/generic: Drop obsoleted obey_preferred_dacs flag (Takashi Iwai)
- ALSA: hda/generic: Unconditionally prefer preferred_dacs pairs (Takashi Iwai)
- ALSA: silence integer wrapping warning (Dan Carpenter)
- ALSA: Reorganize kerneldoc parameter names (Julia Lawall)
- ALSA: hda/realtek: Fix the push button function for the ALC257 (Oder Chiou)
- ALSA: hda/conexant: fix some typos (Oldherl Oh)
- ALSA: mixer_oss: Remove some incorrect kfree_const() usages (Christophe JAILLET)
- ALSA: hda/realtek: Add quirk for Huawei MateBook 13 KLV-WX9 (Ai Chao)
- ALSA: usb-audio: Add delay quirk for VIVO USB-C HEADSET (Lianqin Hu)
- ALSA: Fix typos in comments across various files (Yu Jiaoliang)
- selftest: alsa: check if user has alsa installed (Abdul Rahim)
- ALSA: Drop explicit initialization of struct i2c_device_id::driver_data to 0 (Uwe Kleine-König)
- ALSA: hda/tas2781: Add new quirk for Lenovo Y990 Laptop (Baojun Xu)
- ALSA: hda/realtek: fix mute/micmute LED for HP mt645 G8 (Nikolai Afanasenkov)
- drm/xe: Fix memory leak when aborting binds (Matthew Brost)
- drm/xe: Prevent null pointer access in xe_migrate_copy (Zhanjun Dong)
- drm/xe/oa: Don't reset OAC_CONTEXT_ENABLE on OA stream close (José Roberto de Souza)
- drm/xe/queue: move xa_alloc to prevent UAF (Matthew Auld)
- drm/xe/vm: move xa_alloc to prevent UAF (Matthew Auld)
- drm/xe: Clean up VM / exec queue file lock usage. (Matthew Brost)
- drm/xe: Resume TDR after GT reset (Matthew Brost)
- drm/xe/xe2: Add performance tuning for L3 cache flushing (Gustavo Sousa)
- drm/xe/xe2: Extend performance tuning to media GT (Gustavo Sousa)
- drm/xe/mcr: Use Xe2_LPM steering tables for Xe2_HPM (Gustavo Sousa)
- drm/xe: Use helper for ASID -> VM in GPU faults and access counters (Matthew Brost)
- drm/xe: Convert to USM lock to rwsem (Matthew Brost)
- drm/xe: use devm_add_action_or_reset() helper (He Lugang)
- drm/xe: fix UAF around queue destruction (Matthew Auld)
- drm/xe/guc_submit: add missing locking in wedged_fini (Matthew Auld)
- drm/xe: Restore pci state upon resume (Rodrigo Vivi)
- drm/i915/gem: fix bitwise and logical AND mixup (Jani Nikula)
- drm/panthor: Don't add write fences to the shared BOs (Boris Brezillon)
- drm/panthor: Don't declare a queue blocked if deferred operations are pending (Boris Brezillon)
- drm/panthor: Fix access to uninitialized variable in tick_ctx_cleanup() (Boris Brezillon)
- drm/panthor: Lock the VM resv before calling drm_gpuvm_bo_obtain_prealloc() (Boris Brezillon)
- drm/panthor: Add FOP_UNSIGNED_OFFSET to fop_flags (Liviu Dudau)
- drm/sched: revert "Always increment correct scheduler score" (Christian König)
- drm/sched: Always increment correct scheduler score (Tvrtko Ursulin)
- drm/sched: Always wake up correct scheduler in drm_sched_entity_push_job (Tvrtko Ursulin)
- drm/sched: Add locking to drm_sched_entity_modify_sched (Tvrtko Ursulin)
- drm/amd/display: Fix system hang while resume with TBT monitor (Tom Chung)
- drm/amd/display: Enable idle workqueue for more IPS modes (Leo Li)
- drm/amd/display: Add HDR workaround for specific eDP (Alex Hung)
- drm/amd/display: avoid set dispclk to 0 (Charlene Liu)
- drm/amd/display: Restore Optimized pbn Value if Failed to Disable DSC (Fangzhi Zuo)
- drm/amd/display: update DML2 policy EnhancedPrefetchScheduleAccelerationFinal DCN35 (Yihan Zhu)
- firmware/sysfb: Disable sysfb for firmware buffers with unknown parent (Thomas Zimmermann)
- drm: Consistently use struct drm_mode_rect for FB_DAMAGE_CLIPS (Thomas Zimmermann)
- drm/connector: hdmi: Fix writing Dynamic Range Mastering infoframes (Derek Foreman)
- drm/sched: Fix dynamic job-flow control race (Rob Clark)
- MAINTAINERS: drm/sched: Add new maintainers (Philipp Stanner)
- drm/panthor: Fix race when converting group handle to group object (Steven Price)
- drm/vboxvideo: Replace fake VLA at end of vbva_mouse_pointer_shape with real VLA (Hans de Goede)
- drm/display: fix kerneldocs references (Dmitry Baryshkov)
- drm/dp_mst: Fix DSC decompression detection in Synaptics branch devices (Imre Deak)
- aoe: fix the potential use-after-free problem in more places (Chun-Yi Lee)
- blk_iocost: remove some duplicate irq disable/enables (Dan Carpenter)
- block: fix blk_rq_map_integrity_sg kernel-doc (Keith Busch)
- io_uring/net: harden multishot termination case for recv (Jens Axboe)
- io_uring: fix casts to io_req_flags_t (Min-Hua Chen)
- io_uring: fix memory leak when cache init fail (Guixin Liu)
- inotify: Fix possible deadlock in fsnotify_destroy_mark (Lizhi Xu)
- fsnotify: Avoid data race between fsnotify_recalc_mask() and fsnotify_object_watched() (Jan Kara)
- udf: fix uninit-value use in udf_get_fileshortad (Gianfranco Trad)
- udf: refactor inode_bmap() to handle error (Zhao Mengmeng)
- udf: refactor udf_next_aext() to handle error (Zhao Mengmeng)
- udf: refactor udf_current_aext() to handle error (Zhao Mengmeng)
- ceph: fix cap ref leak via netfs init_request (Patrick Donnelly)
- ceph: use struct_size() helper in __ceph_pool_perm_get() (Thorsten Blum)
- btrfs: disable rate limiting when debug enabled (Leo Martins)
- btrfs: wait for fixup workers before stopping cleaner kthread during umount (Filipe Manana)
- btrfs: fix a NULL pointer dereference when failed to start a new trasacntion (Qu Wenruo)
- btrfs: send: fix invalid clone operation for file that got its size decreased (Filipe Manana)
- btrfs: tracepoints: end assignment with semicolon at btrfs_qgroup_extent event class (Filipe Manana)
- btrfs: drop the backref cache during relocation if we commit (Josef Bacik)
- btrfs: also add stripe entries for NOCOW writes (Johannes Thumshirn)
- btrfs: send: fix buffer overflow detection when copying path to cache entry (Filipe Manana)
- cifs: Do not convert delimiter when parsing NFS-style symlinks (Pali Rohár)
- cifs: Validate content of NFS reparse point buffer (Pali Rohár)
- cifs: Fix buffer overflow when parsing NFS reparse points (Pali Rohár)
- smb: client: Correct typos in multiple comments across various files (Shen Lichuan)
- smb: client: use actual path when queryfs (wangrong)
- cifs: Remove intermediate object of failed create reparse call (Pali Rohár)
- Revert "smb: client: make SHA-512 TFM ephemeral" (Steve French)
- smb: Update comments about some reparse point tags (Pali Rohár)
- cifs: Check for UTF-16 null codepoint in SFU symlink target location (Pali Rohár)
- close_range(): fix the logics in descriptor table trimming (Al Viro)
- v6.12-rc1-rt2 (Sebastian Andrzej Siewior)
- Revert "time: Allow to preempt after a callback." + dependencies. (Sebastian Andrzej Siewior)
- Revert "sched/rt: Don't try push tasks if there are none." (Sebastian Andrzej Siewior)
- Add localversion for -RT release (Thomas Gleixner)
- sysfs: Add /sys/kernel/realtime entry (Clark Williams)
- riscv: add PREEMPT_AUTO support (Jisheng Zhang)
- POWERPC: Allow to enable RT (Sebastian Andrzej Siewior)
- powerpc/stackprotector: work around stack-guard init from atomic (Sebastian Andrzej Siewior)
- powerpc/kvm: Disable in-kernel MPIC emulation for PREEMPT_RT (Bogdan Purcareata)
- powerpc/pseries: Select the generic memory allocator. (Sebastian Andrzej Siewior)
- powerpc/pseries/iommu: Use a locallock instead local_irq_save() (Sebastian Andrzej Siewior)
- powerpc: traps: Use PREEMPT_RT (Sebastian Andrzej Siewior)
- ARM: Allow to enable RT (Sebastian Andrzej Siewior)
- ARM: vfp: Move sending signals outside of vfp_lock()ed section. (Sebastian Andrzej Siewior)
- ARM: vfp: Use vfp_lock() in vfp_support_entry(). (Sebastian Andrzej Siewior)
- ARM: vfp: Use vfp_lock() in vfp_sync_hwstate(). (Sebastian Andrzej Siewior)
- ARM: vfp: Provide vfp_lock() for VFP locking. (Sebastian Andrzej Siewior)
- arm: Disable FAST_GUP on PREEMPT_RT if HIGHPTE is also enabled. (Sebastian Andrzej Siewior)
- ARM: enable irq in translation/section permission fault handlers (Yadi.hu)
- arm: Disable jump-label on PREEMPT_RT. (Thomas Gleixner)
- sched: define TIF_ALLOW_RESCHED (Thomas Gleixner)
- Revert "drm/i915: Depend on !PREEMPT_RT." (Sebastian Andrzej Siewior)
- drm/i915/guc: Consider also RCU depth in busy loop. (Sebastian Andrzej Siewior)
- drm/i915: Drop the irqs_disabled() check (Sebastian Andrzej Siewior)
- drm/i915/gt: Use spin_lock_irq() instead of local_irq_disable() + spin_lock() (Sebastian Andrzej Siewior)
- drm/i915: Disable tracing points on PREEMPT_RT (Sebastian Andrzej Siewior)
- drm/i915: Don't check for atomic context on PREEMPT_RT (Sebastian Andrzej Siewior)
- drm/i915: Don't disable interrupts on PREEMPT_RT during atomic updates (Mike Galbraith)
- drm/i915: Use preempt_disable/enable_rt() where recommended (Mike Galbraith)
- time: Allow to preempt after a callback. (Sebastian Andrzej Siewior)
- softirq: Add function to preempt serving softirqs. (Sebastian Andrzej Siewior)
- sched/core: Provide a method to check if a task is PI-boosted. (Sebastian Andrzej Siewior)
- softirq: Wake ktimers thread also in softirq. (Junxiao Chang)
- tick: Fix timer storm since introduction of timersd (Frederic Weisbecker)
- rcutorture: Also force sched priority to timersd on boosting test. (Frederic Weisbecker)
- softirq: Use a dedicated thread for timer wakeups. (Sebastian Andrzej Siewior)
- locking/rt: Annotate unlock followed by lock for sparse. (Sebastian Andrzej Siewior)
- locking/rt: Add sparse annotation for RCU. (Sebastian Andrzej Siewior)
- locking/rt: Remove one __cond_lock() in RT's spin_trylock_irqsave() (Sebastian Andrzej Siewior)
- locking/rt: Add sparse annotation PREEMPT_RT's sleeping locks. (Sebastian Andrzej Siewior)
- sched/rt: Don't try push tasks if there are none. (Sebastian Andrzej Siewior)
- serial: 8250: Revert "drop lockdep annotation from serial8250_clear_IER()" (John Ogness)
- serial: 8250: Switch to nbcon console (John Ogness)

* Mon Nov 11 2024 Jan Stancek <jstancek@redhat.com> [6.11.0-29.el10]
- redhat/configs: enable xr_serial on rhel (Desnes Nunes)
- redhat/configs: enable ATH12K for rhel (Jose Ignacio Tornos Martinez)
- Linux 6.12-rc7 (Linus Torvalds)
- clk: qcom: gcc-x1e80100: Fix USB MP SS1 PHY GDSC pwrsts flags (Abel Vesa)
- clk: qcom: gcc-x1e80100: Fix halt_check for pipediv2 clocks (Qiang Yu)
- clk: qcom: clk-alpha-pll: Fix pll post div mask when width is not set (Barnabás Czémán)
- clk: qcom: videocc-sm8350: use HW_CTRL_TRIGGER for vcodec GDSCs (Johan Hovold)
- i2c: designware: do not hold SCL low when I2C_DYNAMIC_TAR_UPDATE is not set (Liu Peibao)
- i2c: muxes: Fix return value check in mule_i2c_mux_probe() (Yang Yingliang)
- filemap: Fix bounds checking in filemap_read() (Trond Myklebust)
- irqchip/gic-v3: Force propagation of the active state with a read-back (Marc Zyngier)
- mailmap: add entry for Thorsten Blum (Thorsten Blum)
- ocfs2: remove entry once instead of null-ptr-dereference in ocfs2_xa_remove() (Andrew Kanner)
- signal: restore the override_rlimit logic (Roman Gushchin)
- fs/proc: fix compile warning about variable 'vmcore_mmap_ops' (Qi Xi)
- ucounts: fix counter leak in inc_rlimit_get_ucounts() (Andrei Vagin)
- selftests: hugetlb_dio: check for initial conditions to skip in the start (Muhammad Usama Anjum)
- mm: fix docs for the kernel parameter ``thp_anon=`` (Maíra Canal)
- mm/damon/core: avoid overflow in damon_feed_loop_next_input() (SeongJae Park)
- mm/damon/core: handle zero schemes apply interval (SeongJae Park)
- mm/damon/core: handle zero {aggregation,ops_update} intervals (SeongJae Park)
- mm/mlock: set the correct prev on failure (Wei Yang)
- objpool: fix to make percpu slot allocation more robust (Masami Hiramatsu (Google))
- mm/page_alloc: keep track of free highatomic (Yu Zhao)
- mm: resolve faulty mmap_region() error path behaviour (Lorenzo Stoakes)
- mm: refactor arch_calc_vm_flag_bits() and arm64 MTE handling (Lorenzo Stoakes)
- mm: refactor map_deny_write_exec() (Lorenzo Stoakes)
- mm: unconditionally close VMAs on error (Lorenzo Stoakes)
- mm: avoid unsafe VMA hook invocation when error arises on mmap hook (Lorenzo Stoakes)
- mm/thp: fix deferred split unqueue naming and locking (Hugh Dickins)
- mm/thp: fix deferred split queue not partially_mapped (Hugh Dickins)
- USB: serial: qcserial: add support for Sierra Wireless EM86xx (Jack Wu)
- USB: serial: io_edgeport: fix use after free in debug printk (Dan Carpenter)
- USB: serial: option: add Quectel RG650V (Benoît Monin)
- USB: serial: option: add Fibocom FG132 0x0112 composition (Reinhard Speyerer)
- thunderbolt: Fix connection issue with Pluggable UD-4VPD dock (Mika Westerberg)
- thunderbolt: Add only on-board retimers when !CONFIG_USB4_DEBUGFS_MARGINING (Mika Westerberg)
- usb: typec: fix potential out of bounds in ucsi_ccg_update_set_new_cam_cmd() (Dan Carpenter)
- usb: dwc3: fix fault at system suspend if device was already runtime suspended (Roger Quadros)
- usb: typec: qcom-pmic: init value of hdr_len/txbuf_len earlier (Rex Nie)
- usb: musb: sunxi: Fix accessing an released usb phy (Zijun Hu)
- staging: vchiq_arm: Use devm_kzalloc() for drv_mgmt allocation (Umang Jain)
- staging: vchiq_arm: Use devm_kzalloc() for vchiq_arm_state allocation (Umang Jain)
- redhat: configs: rhel: generic: x86: Enable IPU6 based MIPI cameras (Kate Hsuan)
- os-build: enable CONFIG_SCHED_CLASS_EXT for RHEL (Phil Auld)
- NFSD: Fix READDIR on NFSv3 mounts of ext4 exports (Chuck Lever)
- smb: client: Fix use-after-free of network namespace. (Kuniyuki Iwashima)
- nvme/host: Fix RCU list traversal to use SRCU primitive (Breno Leitao)
- thermal/of: support thermal zones w/o trips subnode (Icenowy Zheng)
- tools/lib/thermal: Remove the thermal.h soft link when doing make clean (zhang jiao)
- tools/lib/thermal: Fix sampling handler context ptr (Emil Dahl Juhl)
- thermal/drivers/qcom/lmh: Remove false lockdep backtrace (Dmitry Baryshkov)
- cpufreq: intel_pstate: Update asym capacity for CPUs that were offline initially (Rafael J. Wysocki)
- cpufreq: intel_pstate: Clear hybrid_max_perf_cpu before driver registration (Rafael J. Wysocki)
- ACPI: processor: Move arch_init_invariance_cppc() call later (Mario Limonciello)
- ksmbd: check outstanding simultaneous SMB operations (Namjae Jeon)
- ksmbd: fix slab-use-after-free in smb3_preauth_hash_rsp (Namjae Jeon)
- ksmbd: fix slab-use-after-free in ksmbd_smb2_session_create (Namjae Jeon)
- ksmbd: Fix the missing xa_store error check (Jinjie Ruan)
- scsi: ufs: core: Start the RTC update work later (Bart Van Assche)
- scsi: sd_zbc: Use kvzalloc() to allocate REPORT ZONES buffer (Johannes Thumshirn)
- drm/xe: Stop accumulating LRC timestamp on job_free (Lucas De Marchi)
- drm/xe/pf: Fix potential GGTT allocation leak (Michal Wajdeczko)
- drm/xe: Drop VM dma-resv lock on xe_sync_in_fence_get failure in exec IOCTL (Matthew Brost)
- drm/xe: Fix possible exec queue leak in exec IOCTL (Matthew Brost)
- drm/xe/guc/tlb: Flush g2h worker in case of tlb timeout (Nirmoy Das)
- drm/xe/ufence: Flush xe ordered_wq in case of ufence timeout (Nirmoy Das)
- drm/xe: Move LNL scheduling WA to xe_device.h (Nirmoy Das)
- drm/xe: Use the filelist from drm for ccs_mode change (Balasubramani Vivekanandan)
- drm/xe: Set mask bits for CCS_MODE register (Balasubramani Vivekanandan)
- drm/panthor: Be stricter about IO mapping flags (Jann Horn)
- drm/panthor: Lock XArray when getting entries for the VM (Liviu Dudau)
- drm: panel-orientation-quirks: Make Lenovo Yoga Tab 3 X90F DMI match less strict (Hans de Goede)
- drm/imagination: Break an object reference loop (Brendan King)
- drm/imagination: Add a per-file PVR context list (Brendan King)
- drm/amdgpu: add missing size check in amdgpu_debugfs_gprwave_read() (Alex Deucher)
- drm/amdgpu: Adjust debugfs eviction and IB access permissions (Alex Deucher)
- drm/amdgpu: Adjust debugfs register access permissions (Alex Deucher)
- drm/amdgpu: Fix DPX valid mode check on GC 9.4.3 (Lijo Lazar)
- drm/amd/pm: correct the workload setting (Kenneth Feng)
- drm/amd/pm: always pick the pptable from IFWI (Kenneth Feng)
- drm/amdgpu: prevent NULL pointer dereference if ATIF is not supported (Antonio Quartulli)
- drm/amd/display: parse umc_info or vram_info based on ASIC (Aurabindo Pillai)
- drm/amd/display: Fix brightness level not retained over reboot (Tom Chung)
- ASoC: SOF: sof-client-probes-ipc4: Set param_size extension bits (Jyri Sarha)
- ASoC: stm: Prevent potential division by zero in stm32_sai_get_clk_div() (Luo Yifan)
- ASoC: stm: Prevent potential division by zero in stm32_sai_mclk_round_rate() (Luo Yifan)
- ASoC: amd: yc: Support dmic on another model of Lenovo Thinkpad E14 Gen 6 (Markus Petri)
- ASoC: SOF: amd: Fix for incorrect DMA ch status register offset (Venkata Prasad Potturu)
- ASoC: amd: yc: fix internal mic on Xiaomi Book Pro 14 2022 (Mingcong Bai)
- ASoC: stm32: spdifrx: fix dma channel release in stm32_spdifrx_remove (Amelie Delaunay)
- MAINTAINERS: Generic Sound Card section (Kuninori Morimoto)
- ASoC: tas2781: Add new driver version for tas2563 & tas2781 qfn chip (Shenghao Ding)
- ALSA: usb-audio: Add quirk for HP 320 FHD Webcam (Takashi Iwai)
- ALSA: firewire-lib: fix return value on fail in amdtp_tscm_init() (Murad Masimov)
- ALSA: ump: Don't enumeration invalid groups for legacy rawmidi (Takashi Iwai)
- Revert "ALSA: hda/conexant: Mute speakers at suspend / shutdown" (Jarosław Janik)
- media: videobuf2-core: copy vb planes unconditionally (Tudor Ambarus)
- media: dvbdev: fix the logic when DVB_DYNAMIC_MINORS is not set (Mauro Carvalho Chehab)
- media: vivid: fix buffer overwrite when using > 32 buffers (Hans Verkuil)
- media: pulse8-cec: fix data timestamp at pulse8_setup() (Mauro Carvalho Chehab)
- media: cec: extron-da-hd-4k-plus: don't use -1 as an error code (Mauro Carvalho Chehab)
- media: stb0899_algo: initialize cfr before using it (Mauro Carvalho Chehab)
- media: adv7604: prevent underflow condition when reporting colorspace (Mauro Carvalho Chehab)
- media: cx24116: prevent overflows on SNR calculus (Mauro Carvalho Chehab)
- media: ar0521: don't overflow when checking PLL values (Mauro Carvalho Chehab)
- media: s5p-jpeg: prevent buffer overflows (Mauro Carvalho Chehab)
- media: av7110: fix a spectre vulnerability (Mauro Carvalho Chehab)
- media: mgb4: protect driver against spectre (Mauro Carvalho Chehab)
- media: dvb_frontend: don't play tricks with underflow values (Mauro Carvalho Chehab)
- media: dvbdev: prevent the risk of out of memory access (Mauro Carvalho Chehab)
- media: v4l2-tpg: prevent the risk of a division by zero (Mauro Carvalho Chehab)
- media: v4l2-ctrls-api: fix error handling for v4l2_g_ctrl() (Mauro Carvalho Chehab)
- media: dvb-core: add missing buffer index check (Hans Verkuil)
- mm/slab: fix warning caused by duplicate kmem_cache creation in kmem_buckets_create (Koichiro Den)
- btrfs: fix the length of reserved qgroup to free (Haisu Wang)
- btrfs: reinitialize delayed ref list after deleting it from the list (Filipe Manana)
- btrfs: fix per-subvolume RO/RW flags with new mount API (Qu Wenruo)
- bcachefs: Fix UAF in __promote_alloc() error path (Kent Overstreet)
- bcachefs: Change OPT_STR max to be 1 less than the size of choices array (Piotr Zalewski)
- bcachefs: btree_cache.freeable list fixes (Kent Overstreet)
- bcachefs: check the invalid parameter for perf test (Hongbo Li)
- bcachefs: add check NULL return of bio_kmalloc in journal_read_bucket (Pei Xiao)
- bcachefs: Ensure BCH_FS_may_go_rw is set before exiting recovery (Kent Overstreet)
- bcachefs: Fix topology errors on split after merge (Kent Overstreet)
- bcachefs: Ancient versions with bad bkey_formats are no longer supported (Kent Overstreet)
- bcachefs: Fix error handling in bch2_btree_node_prefetch() (Kent Overstreet)
- bcachefs: Fix null ptr deref in bucket_gen_get() (Kent Overstreet)
- arm64: Kconfig: Make SME depend on BROKEN for now (Mark Rutland)
- arm64: smccc: Remove broken support for SMCCCv1.3 SVE discard hint (Mark Rutland)
- arm64/sve: Discard stale CPU state when handling SVE traps (Mark Brown)
- KVM: PPC: Book3S HV: Mask off LPCR_MER for a vCPU before running it to avoid spurious interrupts (Gautam Menghani)
- Fedora 6.12 configs part 1 (Justin M. Forbes)
- MAINTAINERS: update AMD SPI maintainer (Raju Rangoju)
- regulator: rk808: Add apply_bit for BUCK3 on RK809 (Mikhail Rudenko)
- regulator: rtq2208: Fix uninitialized use of regulator_config (ChiYuan Huang)
- drivers: net: ionic: add missed debugfs cleanup to ionic_probe() error path (Wentao Liang)
- net/smc: do not leave a dangling sk pointer in __smc_create() (Eric Dumazet)
- rxrpc: Fix missing locking causing hanging calls (David Howells)
- net/smc: Fix lookup of netdev by using ib_device_get_netdev() (Wenjia Zhang)
- netfilter: nf_tables: wait for rcu grace period on net_device removal (Pablo Neira Ayuso)
- net: arc: rockchip: fix emac mdio node support (Johan Jonker)
- net: arc: fix the device for dma_map_single/dma_unmap_single (Johan Jonker)
- virtio_net: Update rss when set queue (Philo Lu)
- virtio_net: Sync rss config to device when virtnet_probe (Philo Lu)
- virtio_net: Add hash_key_length check (Philo Lu)
- virtio_net: Support dynamic rss indirection table size (Philo Lu)
- net: stmmac: Fix unbalanced IRQ wake disable warning on single irq case (Nícolas F. R. A. Prado)
- net: vertexcom: mse102x: Fix possible double free of TX skb (Stefan Wahren)
- e1000e: Remove Meteor Lake SMBUS workarounds (Vitaly Lifshits)
- i40e: fix race condition by adding filter's intermediate sync state (Aleksandr Loktionov)
- idpf: fix idpf_vc_core_init error path (Pavan Kumar Linga)
- idpf: avoid vport access in idpf_get_link_ksettings (Pavan Kumar Linga)
- ice: change q_index variable type to s16 to store -1 value (Mateusz Polchlopek)
- ice: Fix use after free during unload with ports in bridge (Marcin Szycik)
- mptcp: use sock_kfree_s instead of kfree (Geliang Tang)
- mptcp: no admin perm to list endpoints (Matthieu Baerts (NGI0))
- net: phy: ti: add PHY_RST_AFTER_CLK_EN flag (Diogo Silva)
- net: ethernet: ti: am65-cpsw: fix warning in am65_cpsw_nuss_remove_rx_chns() (Roger Quadros)
- net: ethernet: ti: am65-cpsw: Fix multi queue Rx on J7 (Roger Quadros)
- net: hns3: fix kernel crash when uninstalling driver (Peiyang Wang)
- Revert "Merge branch 'there-are-some-bugfix-for-the-hns3-ethernet-driver'" (Jakub Kicinski)
- can: mcp251xfd: mcp251xfd_get_tef_len(): fix length calculation (Marc Kleine-Budde)
- can: mcp251xfd: mcp251xfd_ring_alloc(): fix coalescing configuration when switching CAN modes (Marc Kleine-Budde)
- can: rockchip_canfd: Drop obsolete dependency on COMPILE_TEST (Jean Delvare)
- can: rockchip_canfd: CAN_ROCKCHIP_CANFD should depend on ARCH_ROCKCHIP (Geert Uytterhoeven)
- can: c_can: fix {rx,tx}_errors statistics (Dario Binacchi)
- can: m_can: m_can_close(): don't call free_irq() for IRQ-less devices (Marc Kleine-Budde)
- can: {cc770,sja1000}_isa: allow building on x86_64 (Thomas Mühlbacher)
- can: j1939: fix error in J1939 documentation. (Alexander Hölzl)
- net: xilinx: axienet: Enqueue Tx packets in dql before dmaengine starts (Suraj Gupta)
- MAINTAINERS: Remove self from DSA entry (Florian Fainelli)
- net: enetc: allocate vf_state during PF probes (Wei Fang)
- sctp: properly validate chunk size in sctp_sf_ootb() (Xin Long)
- net: wwan: t7xx: Fix off-by-one error in t7xx_dpmaif_rx_buf_alloc() (Jinjie Ruan)
- dt-bindings: net: xlnx,axi-ethernet: Correct phy-mode property value (Suraj Gupta)
- net: dpaa_eth: print FD status in CPU endianness in dpaa_eth_fd tracepoint (Vladimir Oltean)
- net: enetc: set MAC address to the VF net_device (Wei Fang)
- MAINTAINERS: add self as reviewer for AXI PWM GENERATOR (Trevor Gamblin)
- pwm: imx-tpm: Use correct MODULO value for EPWM mode (Erik Schumacher)
- proc/softirqs: replace seq_printf with seq_put_decimal_ull_width (David Wang)
- nfs: avoid i_lock contention in nfs_clear_invalid_mapping (Mike Snitzer)
- nfs_common: fix localio to cope with racing nfs_local_probe() (Mike Snitzer)
- NFS: Further fixes to attribute delegation a/mtime changes (Trond Myklebust)
- NFS: Fix attribute delegation behaviour on exclusive create (Trond Myklebust)
- nfs: Fix KMSAN warning in decode_getfattr_attrs() (Roberto Sassu)
- NFSv3: only use NFS timeout for MOUNT when protocols are compatible (NeilBrown)
- sunrpc: handle -ENOTCONN in xs_tcp_setup_socket() (NeilBrown)
- KEYS: trusted: dcp: fix NULL dereference in AEAD crypto operation (David Gstir)
- security/keys: fix slab-out-of-bounds in key_task_permission (Chen Ridong)
- tracing/selftests: Add tracefs mount options test (Kalesh Singh)
- tracing: Document tracefs gid mount option (Kalesh Singh)
- tracing: Fix tracefs mount options (Kalesh Singh)
- platform/x86: thinkpad_acpi: Fix for ThinkPad's with ECFW showing incorrect fan speed (Vishnu Sankar)
- platform/x86: ideapad-laptop: add missing Ideapad Pro 5 fn keys (Renato Caldas)
- platform/x86: dell-wmi-base: Handle META key Lock/Unlock events (Kurt Borja)
- platform/x86: dell-smbios-base: Extends support to Alienware products (Kurt Borja)
- platform/x86/amd/pmc: Detect when STB is not available (Corey Hickey)
- platform/x86/amd/pmf: Add SMU metrics table support for 1Ah family 60h model (Shyam Sundar S K)
- dm cache: fix potential out-of-bounds access on the first resume (Ming-Hung Tsai)
- dm cache: optimize dirty bit checking with find_next_bit when resizing (Ming-Hung Tsai)
- dm cache: fix out-of-bounds access to the dirty bitset when resizing (Ming-Hung Tsai)
- dm cache: fix flushing uninitialized delayed_work on cache_ctr error (Ming-Hung Tsai)
- dm cache: correct the number of origin blocks to match the target length (Ming-Hung Tsai)
- dm-verity: don't crash if panic_on_corruption is not selected (Mikulas Patocka)
- dm-unstriped: cast an operand to sector_t to prevent potential uint32_t overflow (Zichen Xie)
- dm: fix a crash if blk_alloc_disk fails (Mikulas Patocka)
- HID: core: zero-initialize the report buffer (Jiri Kosina)
- redhat: set new gcov configs (Jan Stancek)
- Don't ignore gitkeep files for ark-infra (Don Zickus)
- redhat/kernel.spec: don't clear entire libdir when building tools (Jan Stancek)
- redhat/configs: enable usbip for rhel (Jose Ignacio Tornos Martinez)
- redhat: create 'crashkernel=' addons for UKI (Vitaly Kuznetsov)
- redhat: avoid superfluous quotes in UKI cmdline addones (Vitaly Kuznetsov)
- fedora: arm: updates for 6.12 (Peter Robinson)
- soc: qcom: pmic_glink: Handle GLINK intent allocation rejections (Bjorn Andersson)
- rpmsg: glink: Handle rejected intent request better (Bjorn Andersson)
- soc: qcom: socinfo: fix revision check in qcom_socinfo_probe() (Manikanta Mylavarapu)
- firmware: qcom: scm: Return -EOPNOTSUPP for unsupported SHM bridge enabling (Qingqing Zhou)
- EDAC/qcom: Make irq configuration optional (Rajendra Nayak)
- firmware: qcom: scm: fix a NULL-pointer dereference (Bartosz Golaszewski)
- firmware: qcom: scm: suppress download mode error (Johan Hovold)
- soc: qcom: Add check devm_kasprintf() returned value (Charles Han)
- MAINTAINERS: Qualcomm SoC: Match reserved-memory bindings (Simon Horman)
- arm64: dts: qcom: x1e80100: fix PCIe5 interconnect (Johan Hovold)
- arm64: dts: qcom: x1e80100: fix PCIe4 interconnect (Johan Hovold)
- arm64: dts: qcom: x1e80100: Fix up BAR spaces (Konrad Dybcio)
- arm64: dts: qcom: x1e80100-qcp: fix nvme regulator boot glitch (Johan Hovold)
- arm64: dts: qcom: x1e80100-microsoft-romulus: fix nvme regulator boot glitch (Johan Hovold)
- arm64: dts: qcom: x1e80100-yoga-slim7x: fix nvme regulator boot glitch (Johan Hovold)
- arm64: dts: qcom: x1e80100-vivobook-s15: fix nvme regulator boot glitch (Johan Hovold)
- arm64: dts: qcom: x1e80100-crd: fix nvme regulator boot glitch (Johan Hovold)
- arm64: dts: qcom: x1e78100-t14s: fix nvme regulator boot glitch (Johan Hovold)
- arm64: dts: qcom: x1e80100-crd Rename "Twitter" to "Tweeter" (Maya Matuszczyk)
- arm64: dts: qcom: x1e80100: Fix PCIe 6a lanes description (Abel Vesa)
- arm64: dts: qcom: sm8450 fix PIPE clock specification for pcie1 (Dmitry Baryshkov)
- arm64: dts: qcom: x1e80100: Add Broadcast_AND region in LLCC block (Abel Vesa)
- arm64: dts: qcom: x1e80100: fix PCIe5 PHY clocks (Johan Hovold)
- arm64: dts: qcom: x1e80100: fix PCIe4 and PCIe6a PHY clocks (Johan Hovold)
- arm64: dts: qcom: msm8939: revert use of APCS mbox for RPM (Fabien Parent)
- firmware: arm_scmi: Use vendor string in max-rx-timeout-ms (Cristian Marussi)
- dt-bindings: firmware: arm,scmi: Add missing vendor string (Cristian Marussi)
- firmware: arm_scmi: Reject clear channel request on A2P (Cristian Marussi)
- firmware: arm_scmi: Fix slab-use-after-free in scmi_bus_notifier() (Xinqi Zhang)
- MAINTAINERS: invert Misc RISC-V SoC Support's pattern (Conor Dooley)
- riscv: dts: starfive: Update ethernet phy0 delay parameter values for Star64 (E Shattow)
- riscv: dts: starfive: disable unused csi/camss nodes (Conor Dooley)
- firmware: microchip: auto-update: fix poll_complete() to not report spurious timeout errors (Conor Dooley)
- arm64: dts: rockchip: Correct GPIO polarity on brcm BT nodes (Diederik de Haas)
- arm64: dts: rockchip: Drop invalid clock-names from es8388 codec nodes (Cristian Ciocaltea)
- ARM: dts: rockchip: Fix the realtek audio codec on rk3036-kylin (Heiko Stuebner)
- ARM: dts: rockchip: Fix the spi controller on rk3036 (Heiko Stuebner)
- ARM: dts: rockchip: drop grf reference from rk3036 hdmi (Heiko Stuebner)
- ARM: dts: rockchip: fix rk3036 acodec node (Heiko Stuebner)
- arm64: dts: rockchip: remove orphaned pinctrl-names from pinephone pro (Heiko Stuebner)
- arm64: dts: rockchip: remove num-slots property from rk3328-nanopi-r2s-plus (Heiko Stuebner)
- arm64: dts: rockchip: Fix LED triggers on rk3308-roc-cc (Heiko Stuebner)
- arm64: dts: rockchip: Remove #cooling-cells from fan on Theobroma lion (Heiko Stuebner)
- arm64: dts: rockchip: Remove undocumented supports-emmc property (Heiko Stuebner)
- arm64: dts: rockchip: Fix bluetooth properties on Rock960 boards (Heiko Stuebner)
- arm64: dts: rockchip: Fix bluetooth properties on rk3566 box demo (Heiko Stuebner)
- arm64: dts: rockchip: Drop regulator-init-microvolt from two boards (Heiko Stuebner)
- arm64: dts: rockchip: fix i2c2 pinctrl-names property on anbernic-rg353p/v (Heiko Stuebner)
- arm64: dts: rockchip: Fix reset-gpios property on brcm BT nodes (Diederik de Haas)
- arm64: dts: rockchip: Fix wakeup prop names on PineNote BT node (Diederik de Haas)
- arm64: dts: rockchip: Remove hdmi's 2nd interrupt on rk3328 (Diederik de Haas)
- arm64: dts: rockchip: Designate Turing RK1's system power controller (Sam Edwards)
- arm64: dts: rockchip: Start cooling maps numbering from zero on ROCK 5B (Dragan Simic)
- arm64: dts: rockchip: Move L3 cache outside CPUs in RK3588(S) SoC dtsi (Dragan Simic)
- arm64: dts: rockchip: Fix rt5651 compatible value on rk3399-sapphire-excavator (Geert Uytterhoeven)
- arm64: dts: rockchip: Fix rt5651 compatible value on rk3399-eaidk-610 (Geert Uytterhoeven)
- riscv: dts: Replace deprecated snps,nr-gpios property for snps,dw-apb-gpio-port devices (Uwe Kleine-König)
- arm64: dts: imx8mp-phyboard-pollux: Set Video PLL1 frequency to 506.8 MHz (Marek Vasut)
- arm64: dts: imx8mp: correct sdhc ipg clk (Peng Fan)
- arm64: dts: imx8mp-skov-revb-mi1010ait-1cp1: Assign "media_isp" clock rate (Liu Ying)
- arm64: dts: imx8: Fix lvds0 device tree (Diogo Silva)
- arm64: dts: imx8ulp: correct the flexspi compatible string (Haibo Chen)
- arm64: dts: imx8-ss-vpu: Fix imx8qm VPU IRQs (Alexander Stein)
- mmc: sdhci-pci-gli: GL9767: Fix low power mode in the SD Express process (Ben Chuang)
- mmc: sdhci-pci-gli: GL9767: Fix low power mode on the set clock function (Ben Chuang)
- tpm: Lock TPM chip in tpm_pm_suspend() first (Jarkko Sakkinen)
- Make setting of cma_pernuma tech preview (Chris von Recklinghausen) [RHEL-59621]
- gitlab-ci: provide consistent kcidb_tree_name (Michael Hofmann)

* Mon Nov 04 2024 Jan Stancek <jstancek@redhat.com> [6.11.0-28.el10]
- Linux 6.12-rc6 (Linus Torvalds)
- mm: multi-gen LRU: use {ptep,pmdp}_clear_young_notify() (Yu Zhao)
- mm: multi-gen LRU: remove MM_LEAF_OLD and MM_NONLEAF_TOTAL stats (Yu Zhao)
- mm, mmap: limit THP alignment of anonymous mappings to PMD-aligned sizes (Vlastimil Babka)
- mm: shrinker: avoid memleak in alloc_shrinker_info (Chen Ridong)
- .mailmap: update e-mail address for Eugen Hristev (Eugen Hristev)
- vmscan,migrate: fix page count imbalance on node stats when demoting pages (Gregory Price)
- mailmap: update Jarkko's email addresses (Jarkko Sakkinen)
- mm: allow set/clear page_type again (Yu Zhao)
- nilfs2: fix potential deadlock with newly created symlinks (Ryusuke Konishi)
- Squashfs: fix variable overflow in squashfs_readpage_block (Phillip Lougher)
- kasan: remove vmalloc_percpu test (Andrey Konovalov)
- tools/mm: -Werror fixes in page-types/slabinfo (Wladislav Wiebe)
- mm, swap: avoid over reclaim of full clusters (Kairui Song)
- mm: fix PSWPIN counter for large folios swap-in (Barry Song)
- mm: avoid VM_BUG_ON when try to map an anon large folio to zero page. (Zi Yan)
- mm/codetag: fix null pointer check logic for ref and tag (Hao Ge)
- mm/gup: stop leaking pinned pages in low memory conditions (John Hubbard)
- phy: tegra: xusb: Add error pointer check in xusb.c (Dipendra Khadka)
- dt-bindings: phy: qcom,sc8280xp-qmp-pcie-phy: Fix X1E80100 resets entries (Abel Vesa)
- phy: freescale: imx8m-pcie: Do CMN_RST just before PHY PLL lock check (Richard Zhu)
- phy: phy-rockchip-samsung-hdptx: Depend on CONFIG_COMMON_CLK (Cristian Ciocaltea)
- phy: ti: phy-j721e-wiz: fix usxgmii configuration (Siddharth Vadapalli)
- phy: starfive: jh7110-usb: Fix link configuration to controller (Jan Kiszka)
- phy: qcom: qmp-pcie: drop bogus x1e80100 qref supplies (Johan Hovold)
- phy: qcom: qmp-combo: move driver data initialisation earlier (Johan Hovold)
- phy: qcom: qmp-usbc: fix NULL-deref on runtime suspend (Johan Hovold)
- phy: qcom: qmp-usb-legacy: fix NULL-deref on runtime suspend (Johan Hovold)
- phy: qcom: qmp-usb: fix NULL-deref on runtime suspend (Johan Hovold)
- dt-bindings: phy: qcom,sc8280xp-qmp-pcie-phy: add missing x1e80100 pipediv2 clocks (Johan Hovold)
- phy: usb: disable COMMONONN for dual mode (Justin Chen)
- phy: cadence: Sierra: Fix offset of DEQ open eye algorithm control register (Bartosz Wawrzyniak)
- phy: usb: Fix missing elements in BCM4908 USB init array (Sam Edwards)
- dmaengine: ti: k3-udma: Set EOP for all TRs in cyclic BCDMA transfer (Jai Luthra)
- dmaengine: sh: rz-dmac: handle configs where one address is zero (Wolfram Sang)
- Revert "driver core: Fix uevent_show() vs driver detach race" (Greg Kroah-Hartman)
- usb: typec: tcpm: restrict SNK_WAIT_CAPABILITIES_TIMEOUT transitions to non self-powered devices (Amit Sunil Dhamne)
- usb: phy: Fix API devm_usb_put_phy() can not release the phy (Zijun Hu)
- usb: typec: use cleanup facility for 'altmodes_node' (Javier Carrasco)
- usb: typec: fix unreleased fwnode_handle in typec_port_register_altmodes() (Javier Carrasco)
- usb: typec: qcom-pmic-typec: fix missing fwnode removal in error path (Javier Carrasco)
- usb: typec: qcom-pmic-typec: use fwnode_handle_put() to release fwnodes (Javier Carrasco)
- usb: acpi: fix boot hang due to early incorrect 'tunneled' USB3 device links (Mathias Nyman)
- Revert "usb: dwc2: Skip clock gating on Broadcom SoCs" (Stefan Wahren)
- xhci: Fix Link TRB DMA in command ring stopped completion event (Faisal Hassan)
- xhci: Use pm_runtime_get to prevent RPM on unsupported systems (Basavaraj Natikar)
- usbip: tools: Fix detach_port() invalid port error path (Zongmin Zhou)
- thunderbolt: Honor TMU requirements in the domain when setting TMU mode (Gil Fine)
- thunderbolt: Fix KASAN reported stack out-of-bounds read in tb_retimer_scan() (Mika Westerberg)
- iio: dac: Kconfig: Fix build error for ltc2664 (Jinjie Ruan)
- iio: adc: ad7124: fix division by zero in ad7124_set_channel_odr() (Zicheng Qu)
- staging: iio: frequency: ad9832: fix division by zero in ad9832_calc_freqreg() (Zicheng Qu)
- docs: iio: ad7380: fix supply for ad7380-4 (Julien Stephan)
- iio: adc: ad7380: fix supplies for ad7380-4 (Julien Stephan)
- iio: adc: ad7380: add missing supplies (Julien Stephan)
- iio: adc: ad7380: use devm_regulator_get_enable_read_voltage() (Julien Stephan)
- dt-bindings: iio: adc: ad7380: fix ad7380-4 reference supply (Julien Stephan)
- iio: light: veml6030: fix microlux value calculation (Javier Carrasco)
- iio: gts-helper: Fix memory leaks for the error path of iio_gts_build_avail_scale_table() (Jinjie Ruan)
- iio: gts-helper: Fix memory leaks in iio_gts_build_avail_scale_table() (Jinjie Ruan)
- mei: use kvmalloc for read buffer (Alexander Usyskin)
- MAINTAINERS: add netup_unidvb maintainer (Abylay Ospan)
- Input: fix regression when re-registering input handlers (Dmitry Torokhov)
- Input: adp5588-keys - do not try to disable interrupt 0 (Dmitry Torokhov)
- Input: edt-ft5x06 - fix regmap leak when probe fails (Dmitry Torokhov)
- modpost: fix input MODULE_DEVICE_TABLE() built for 64-bit on 32-bit host (Masahiro Yamada)
- modpost: fix acpi MODULE_DEVICE_TABLE built with mismatched endianness (Masahiro Yamada)
- kconfig: show sub-menu entries even if the prompt is hidden (Masahiro Yamada)
- kbuild: deb-pkg: add pkg.linux-upstream.nokerneldbg build profile (Masahiro Yamada)
- kbuild: deb-pkg: add pkg.linux-upstream.nokernelheaders build profile (Masahiro Yamada)
- kbuild: rpm-pkg: disable kernel-devel package when cross-compiling (Masahiro Yamada)
- sumversion: Fix a memory leak in get_src_version() (Elena Salomatkina)
- x86/amd_nb: Fix compile-testing without CONFIG_AMD_NB (Arnd Bergmann)
- posix-cpu-timers: Clear TICK_DEP_BIT_POSIX_TIMER on clone (Benjamin Segall)
- sched/ext: Fix scx vs sched_delayed (Peter Zijlstra)
- sched: Pass correct scheduling policy to __setscheduler_class (Aboorva Devarajan)
- sched/numa: Fix the potential null pointer dereference in task_numa_work() (Shawn Wang)
- sched: Fix pick_next_task_fair() vs try_to_wake_up() race (Peter Zijlstra)
- perf: Fix missing RCU reader protection in perf_event_clear_cpumask() (Kan Liang)
- irqchip/gic-v4: Correctly deal with set_affinity on lazily-mapped VPEs (Marc Zyngier)
- genirq/msi: Fix off-by-one error in msi_domain_alloc() (Jinjie Ruan)
- redhat/configs: add bootconfig to kernel-tools package (Brian Masney)
- Enable CONFIG_SECURITY_LANDLOCK for RHEL (Zbigniew Jędrzejewski-Szmek) [RHEL-8810]
- rpcrdma: Always release the rpcrdma_device's xa_array (Chuck Lever)
- NFSD: Never decrement pending_async_copies on error (Chuck Lever)
- NFSD: Initialize struct nfsd4_copy earlier (Chuck Lever)
- xfs: streamline xfs_filestream_pick_ag (Christoph Hellwig)
- xfs: fix finding a last resort AG in xfs_filestream_pick_ag (Christoph Hellwig)
- xfs: Reduce unnecessary searches when searching for the best extents (Chi Zhiling)
- xfs: Check for delayed allocations before setting extsize (Ojaswin Mujoo)
- selftests/watchdog-test: Fix system accidentally reset after watchdog-test (Li Zhijian)
- selftests/intel_pstate: check if cpupower is installed (Alessandro Zanni)
- selftests/intel_pstate: fix operand expected error (Alessandro Zanni)
- selftests/mount_setattr: fix idmap_mount_tree_invalid failed to run (zhouyuhang)
- cfi: tweak llvm version for HAVE_CFI_ICALL_NORMALIZE_INTEGERS (Alice Ryhl)
- kbuild: rust: avoid errors with old `rustc`s without LLVM patch version (Miguel Ojeda)
- PCI: Fix pci_enable_acs() support for the ACS quirks (Jason Gunthorpe)
- drm/xe: Don't short circuit TDR on jobs not started (Matthew Brost)
- drm/xe: Add mmio read before GGTT invalidate (Matthew Brost)
- drm/xe/display: Add missing HPD interrupt enabling during non-d3cold RPM resume (Imre Deak)
- drm/xe/display: Separate the d3cold and non-d3cold runtime PM handling (Imre Deak)
- drm/xe: Remove runtime argument from display s/r functions (Maarten Lankhorst)
- dt-bindings: display: mediatek: split: add subschema property constraints (Moudy Ho)
- dt-bindings: display: mediatek: dpi: correct power-domains property (Macpaul Lin)
- drm/mediatek: Fix potential NULL dereference in mtk_crtc_destroy() (Dan Carpenter)
- drm/mediatek: Fix get efuse issue for MT8188 DPTX (Liankun Yang)
- drm/mediatek: Fix color format MACROs in OVL (Hsin-Te Yuan)
- drm/mediatek: Add blend_modes to mtk_plane_init() for different SoCs (Jason-JH.Lin)
- drm/mediatek: ovl: Add blend_modes to driver data (Jason-JH.Lin)
- drm/mediatek: ovl: Remove the color format comment for ovl_fmt_convert() (Jason-JH.Lin)
- drm/mediatek: ovl: Refine ignore_pixel_alpha comment and placement (Jason-JH.Lin)
- drm/mediatek: ovl: Fix XRGB format breakage for blend_modes unsupported SoCs (Jason-JH.Lin)
- drm/amdgpu/smu13: fix profile reporting (Alex Deucher)
- drm/amd/pm: Vangogh: Fix kernel memory out of bounds write (Tvrtko Ursulin)
- Revert "drm/amd/display: update DML2 policy EnhancedPrefetchScheduleAccelerationFinal DCN35" (Ovidiu Bunea)
- drm/tests: hdmi: Fix memory leaks in drm_display_mode_from_cea_vic() (Jinjie Ruan)
- drm/connector: hdmi: Fix memory leak in drm_display_mode_from_cea_vic() (Jinjie Ruan)
- drm/tests: helpers: Add helper for drm_display_mode_from_cea_vic() (Jinjie Ruan)
- drm/panthor: Report group as timedout when we fail to properly suspend (Boris Brezillon)
- drm/panthor: Fail job creation when the group is dead (Boris Brezillon)
- drm/panthor: Fix firmware initialization on systems with a page size > 4k (Boris Brezillon)
- accel/ivpu: Fix NOC firewall interrupt handling (Andrzej Kacprowski)
- drm/sched: Mark scheduler work queues with WQ_MEM_RECLAIM (Matthew Brost)
- drm/tegra: Fix NULL vs IS_ERR() check in probe() (Dan Carpenter)
- cxl/test: Improve init-order fidelity relative to real-world systems (Dan Williams)
- cxl/port: Prevent out-of-order decoder allocation (Dan Williams)
- cxl/port: Fix use-after-free, permit out-of-order decoder shutdown (Dan Williams)
- cxl/acpi: Ensure ports ready at cxl_acpi_probe() return (Dan Williams)
- cxl/port: Fix cxl_bus_rescan() vs bus_rescan_devices() (Dan Williams)
- cxl/port: Fix CXL port initialization order when the subsystem is built-in (Dan Williams)
- cxl/events: Fix Trace DRAM Event Record (Shiju Jose)
- cxl/core: Return error when cxl_endpoint_gather_bandwidth() handles a non-PCI device (Li Zhijian)
- nvme: re-fix error-handling for io_uring nvme-passthrough (Keith Busch)
- nvmet-auth: assign dh_key to NULL after kfree_sensitive (Vitaliy Shevtsov)
- nvme: module parameter to disable pi with offsets (Keith Busch)
- nvme: enhance cns version checking (Keith Busch)
- block: fix queue limits checks in blk_rq_map_user_bvec for real (Christoph Hellwig)
- io_uring/rw: fix missing NOWAIT check for O_DIRECT start write (Jens Axboe)
- ACPI: CPPC: Make rmw_lock a raw_spin_lock (Pierre Gondois)
- gpiolib: fix debugfs dangling chip separator (Johan Hovold)
- gpiolib: fix debugfs newline separators (Johan Hovold)
- gpio: sloppy-logic-analyzer: Check for error code from devm_mutex_init() call (Andy Shevchenko)
- gpio: fix uninit-value in swnode_find_gpio (Suraj Sonawane)
- riscv: vdso: Prevent the compiler from inserting calls to memset() (Alexandre Ghiti)
- riscv: Remove duplicated GET_RM (Chunyan Zhang)
- riscv: Remove unused GENERATING_ASM_OFFSETS (Chunyan Zhang)
- riscv: Use '%%u' to format the output of 'cpu' (WangYuli)
- riscv: Prevent a bad reference count on CPU nodes (Miquel Sabaté Solà)
- riscv: efi: Set NX compat flag in PE/COFF header (Heinrich Schuchardt)
- RISC-V: disallow gcc + rust builds (Conor Dooley)
- riscv: Do not use fortify in early code (Alexandre Ghiti)
- RISC-V: ACPI: fix early_ioremap to early_memremap (Yunhui Cui)
- arm64: signal: Improve POR_EL0 handling to avoid uaccess failures (Kevin Brodsky)
- firmware: arm_sdei: Fix the input parameter of cpuhp_remove_state() (Xiongfeng Wang)
- Revert "kasan: Disable Software Tag-Based KASAN with GCC" (Marco Elver)
- kasan: Fix Software Tag-Based KASAN with GCC (Marco Elver)
- iomap: turn iomap_want_unshare_iter into an inline function (Christoph Hellwig)
- fsdax: dax_unshare_iter needs to copy entire blocks (Darrick J. Wong)
- fsdax: remove zeroing code from dax_unshare_iter (Darrick J. Wong)
- iomap: share iomap_unshare_iter predicate code with fsdax (Darrick J. Wong)
- xfs: don't allocate COW extents when unsharing a hole (Darrick J. Wong)
- iov_iter: fix copy_page_from_iter_atomic() if KMAP_LOCAL_FORCE_MAP (Hugh Dickins)
- autofs: fix thinko in validate_dev_ioctl() (Ian Kent)
- iov_iter: Fix iov_iter_get_pages*() for folio_queue (David Howells)
- afs: Fix missing subdir edit when renamed between parent dirs (David Howells)
- doc: correcting the debug path for cachefiles (Hongbo Li)
- erofs: use get_tree_bdev_flags() to avoid misleading messages (Gao Xiang)
- fs/super.c: introduce get_tree_bdev_flags() (Gao Xiang)
- btrfs: fix defrag not merging contiguous extents due to merged extent maps (Filipe Manana)
- btrfs: fix extent map merging not happening for adjacent extents (Filipe Manana)
- btrfs: fix use-after-free of block device file in __btrfs_free_extra_devids() (Zhihao Cheng)
- btrfs: fix error propagation of split bios (Naohiro Aota)
- MIPS: export __cmpxchg_small() (David Sterba)
- bcachefs: Fix NULL ptr dereference in btree_node_iter_and_journal_peek (Piotr Zalewski)
- bcachefs: fix possible null-ptr-deref in __bch2_ec_stripe_head_get() (Gaosheng Cui)
- bcachefs: Fix deadlock on -ENOSPC w.r.t. partial open buckets (Kent Overstreet)
- bcachefs: Don't filter partial list buckets in open_buckets_to_text() (Kent Overstreet)
- bcachefs: Don't keep tons of cached pointers around (Kent Overstreet)
- bcachefs: init freespace inited bits to 0 in bch2_fs_initialize (Piotr Zalewski)
- bcachefs: Fix unhandled transaction restart in fallocate (Kent Overstreet)
- bcachefs: Fix UAF in bch2_reconstruct_alloc() (Kent Overstreet)
- bcachefs: fix null-ptr-deref in have_stripes() (Jeongjun Park)
- bcachefs: fix shift oob in alloc_lru_idx_fragmentation (Jeongjun Park)
- bcachefs: Fix invalid shift in validate_sb_layout() (Gianfranco Trad)
- RDMA/bnxt_re: synchronize the qp-handle table array (Selvin Xavier)
- RDMA/bnxt_re: Fix the usage of control path spin locks (Selvin Xavier)
- RDMA/mlx5: Round max_rd_atomic/max_dest_rd_atomic up instead of down (Patrisious Haddad)
- RDMA/cxgb4: Dump vendor specific QP details (Leon Romanovsky)
- bpf, test_run: Fix LIVE_FRAME frame update after a page has been recycled (Toke Høiland-Jørgensen)
- selftests/bpf: Add three test cases for bits_iter (Hou Tao)
- bpf: Use __u64 to save the bits in bits iterator (Hou Tao)
- bpf: Check the validity of nr_words in bpf_iter_bits_new() (Hou Tao)
- bpf: Add bpf_mem_alloc_check_size() helper (Hou Tao)
- bpf: Free dynamically allocated bits in bpf_iter_bits_destroy() (Hou Tao)
- bpf: disallow 40-bytes extra stack for bpf_fastcall patterns (Eduard Zingerman)
- selftests/bpf: Add test for trie_get_next_key() (Byeonguk Jeong)
- bpf: Fix out-of-bounds write in trie_get_next_key() (Byeonguk Jeong)
- selftests/bpf: Test with a very short loop (Eduard Zingerman)
- bpf: Force checkpoint when jmp history is too long (Eduard Zingerman)
- bpf: fix filed access without lock (Jiayuan Chen)
- sock_map: fix a NULL pointer dereference in sock_map_link_update_prog() (Cong Wang)
- netfilter: nft_payload: sanitize offset and length before calling skb_checksum() (Pablo Neira Ayuso)
- netfilter: nf_reject_ipv6: fix potential crash in nf_send_reset6() (Eric Dumazet)
- netfilter: Fix use-after-free in get_info() (Dong Chenchen)
- selftests: netfilter: remove unused parameter (Liu Jing)
- Bluetooth: hci: fix null-ptr-deref in hci_read_supported_codecs (Sungwoo Kim)
- net: hns3: fix kernel crash when 1588 is sent on HIP08 devices (Jie Wang)
- net: hns3: fixed hclge_fetch_pf_reg accesses bar space out of bounds issue (Hao Lan)
- net: hns3: initialize reset_timer before hclgevf_misc_irq_init() (Jian Shen)
- net: hns3: don't auto enable misc vector (Jian Shen)
- net: hns3: Resolved the issue that the debugfs query result is inconsistent. (Hao Lan)
- net: hns3: fix missing features due to dev->features configuration too early (Hao Lan)
- net: hns3: fixed reset failure issues caused by the incorrect reset type (Hao Lan)
- net: hns3: add sync command to sync io-pgtable (Jian Shen)
- net: hns3: default enable tx bounce buffer when smmu enabled (Peiyang Wang)
- net: ethernet: mtk_wed: fix path of MT7988 WO firmware (Daniel Golle)
- selftests: forwarding: Add IPv6 GRE remote change tests (Ido Schimmel)
- mlxsw: spectrum_ipip: Fix memory leak when changing remote IPv6 address (Ido Schimmel)
- mlxsw: pci: Sync Rx buffers for device (Amit Cohen)
- mlxsw: pci: Sync Rx buffers for CPU (Amit Cohen)
- mlxsw: spectrum_ptp: Add missing verification before pushing Tx header (Amit Cohen)
- net: skip offload for NETIF_F_IPV6_CSUM if ipv6 header contains extension (Benoît Monin)
- wifi: mac80211: ieee80211_i: Fix memory corruption bug in struct ieee80211_chanctx (Gustavo A. R. Silva)
- wifi: iwlwifi: mvm: fix 6 GHz scan construction (Johannes Berg)
- wifi: cfg80211: clear wdev->cqm_config pointer on free (Johannes Berg)
- mac80211: fix user-power when emulating chanctx (Ben Greear)
- Revert "wifi: iwlwifi: remove retry loops in start" (Emmanuel Grumbach)
- wifi: iwlwifi: mvm: don't add default link in fw restart flow (Emmanuel Grumbach)
- wifi: iwlwifi: mvm: Fix response handling in iwl_mvm_send_recovery_cmd() (Daniel Gabay)
- wifi: iwlwifi: mvm: SAR table alignment (Anjaneyulu)
- wifi: iwlwifi: mvm: Use the sync timepoint API in suspend (Daniel Gabay)
- wifi: iwlwifi: mvm: really send iwl_txpower_constraints_cmd (Miri Korenblit)
- wifi: iwlwifi: mvm: don't leak a link on AP removal (Emmanuel Grumbach)
- net: fix crash when config small gso_max_size/gso_ipv4_max_size (Wang Liang)
- net: usb: qmi_wwan: add Quectel RG650V (Benoît Monin)
- net/sched: sch_api: fix xa_insert() error path in tcf_block_get_ext() (Vladimir Oltean)
- netdevsim: Add trailing zero to terminate the string in nsim_nexthop_bucket_activity_write() (Zichen Xie)
- net/sched: stop qdisc_tree_reduce_backlog on TC_H_ROOT (Pedro Tammela)
- selftests: netfilter: nft_flowtable.sh: make first pass deterministic (Florian Westphal)
- gtp: allow -1 to be specified as file description from userspace (Pablo Neira Ayuso)
- mctp i2c: handle NULL header address (Matt Johnston)
- ipv4: ip_tunnel: Fix suspicious RCU usage warning in ip_tunnel_find() (Ido Schimmel)
- ipv4: ip_tunnel: Fix suspicious RCU usage warning in ip_tunnel_init_flow() (Ido Schimmel)
- ice: fix crash on probe for DPLL enabled E810 LOM (Arkadiusz Kubalewski)
- ice: block SF port creation in legacy mode (Michal Swiatkowski)
- igb: Disable threaded IRQ for igb_msix_other (Wander Lairson Costa)
- net: stmmac: TSO: Fix unbalanced DMA map/unmap for non-paged SKB data (Furong Xu)
- net: stmmac: dwmac4: Fix high address display by updating reg_space[] from register values (Ley Foon Tan)
- usb: add support for new USB device ID 0x17EF:0x3098 for the r8152 driver (Benjamin Große)
- macsec: Fix use-after-free while sending the offloading packet (Jianbo Liu)
- selftests: mptcp: list sysctl data (Matthieu Baerts (NGI0))
- mptcp: init: protect sched with rcu_read_lock (Matthieu Baerts (NGI0))
- docs: networking: packet_mmap: replace dead links with archive.org links (Levi Zim)
- wifi: ath11k: Fix invalid ring usage in full monitor mode (Remi Pommarel)
- wifi: ath10k: Fix memory leak in management tx (Manikanta Pubbisetty)
- wifi: rtlwifi: rtl8192du: Don't claim USB ID 0bda:8171 (Bitterblue Smith)
- wifi: rtw88: Fix the RX aggregation in USB 3 mode (Bitterblue Smith)
- wifi: brcm80211: BRCM_TRACING should depend on TRACING (Geert Uytterhoeven)
- wifi: rtw89: pci: early chips only enable 36-bit DMA on specific PCI hosts (Ping-Ke Shih)
- wifi: mac80211: skip non-uploaded keys in ieee80211_iter_keys (Felix Fietkau)
- wifi: radiotap: Avoid -Wflex-array-member-not-at-end warnings (Gustavo A. R. Silva)
- wifi: mac80211: do not pass a stopped vif to the driver in .get_txpower (Felix Fietkau)
- wifi: mac80211: Convert color collision detection to wiphy work (Remi Pommarel)
- wifi: cfg80211: Add wiphy_delayed_work_pending() (Remi Pommarel)
- wifi: cfg80211: Do not create BSS entries for unsupported channels (Chenming Huang)
- wifi: mac80211: Fix setting txpower with emulate_chanctx (Ben Greear)
- mac80211: MAC80211_MESSAGE_TRACING should depend on TRACING (Geert Uytterhoeven)
- wifi: iwlegacy: Clear stale interrupts before resuming device (Ville Syrjälä)
- wifi: iwlegacy: Fix "field-spanning write" warning in il_enqueue_hcmd() (Ben Hutchings)
- wifi: mt76: do not increase mcu skb refcount if retry is not supported (Felix Fietkau)
- wifi: rtw89: coex: add debug message of link counts on 2/5GHz bands for wl_info v7 (Ping-Ke Shih)
- ALSA: hda/realtek: Fix headset mic on TUXEDO Stellaris 16 Gen6 mb1 (Christoffer Sandberg)
- ALSA: hda/realtek: Fix headset mic on TUXEDO Gemini 17 Gen3 (Christoffer Sandberg)
- ALSA: usb-audio: Add quirks for Dell WD19 dock (Jan Schär)
- ASoC: codecs: wcd937x: relax the AUX PDM watchdog (Alexey Klimov)
- ASoC: codecs: wcd937x: add missing LO Switch control (Alexey Klimov)
- ASoC: dt-bindings: rockchip,rk3308-codec: add port property (Dmitry Yashin)
- ASoC: dapm: fix bounds checker error in dapm_widget_list_create (Aleksei Vetrov)
- ASoC: Intel: sst: Fix used of uninitialized ctx to log an error (Hans de Goede)
- ASoC: cs42l51: Fix some error handling paths in cs42l51_probe() (Christophe JAILLET)
- ASoC: Intel: sst: Support LPE0F28 ACPI HID (Hans de Goede)
- ASoC: Intel: bytcr_rt5640: Add DMI quirk for Vexia Edu Atla 10 tablet (Hans de Goede)
- ASoC: Intel: bytcr_rt5640: Add support for non ACPI instantiated codec (Hans de Goede)
- ASoC: codecs: rt5640: Always disable IRQs from rt5640_cancel_work() (Hans de Goede)
- ALSA: hda/realtek: Add subwoofer quirk for Infinix ZERO BOOK 13 (Piyush Raj Chouhan)
- ALSA: hda/realtek: Limit internal Mic boost on Dell platform (Kailang Yang)
- redhat: configs: Drop CONFIG_MEMSTICK_REALTEK_PCI config option (Desnes Nunes)
- x86/uaccess: Avoid barrier_nospec() in 64-bit copy_from_user() (Linus Torvalds)
- perf cap: Add __NR_capget to arch/x86 unistd (Ian Rogers)
- tools headers: Update the linux/unaligned.h copy with the kernel sources (Arnaldo Carvalho de Melo)
- tools headers arm64: Sync arm64's cputype.h with the kernel sources (Arnaldo Carvalho de Melo)
- tools headers: Synchronize {uapi/}linux/bits.h with the kernel sources (Arnaldo Carvalho de Melo)
- tools arch x86: Sync the msr-index.h copy with the kernel sources (Arnaldo Carvalho de Melo)
- perf python: Fix up the build on architectures without HAVE_KVM_STAT_SUPPORT (Arnaldo Carvalho de Melo)
- perf test: Handle perftool-testsuite_probe failure due to broken DWARF (Veronika Molnarova)
- tools headers UAPI: Sync kvm headers with the kernel sources (Arnaldo Carvalho de Melo)
- perf trace: Fix non-listed archs in the syscalltbl routines (Jiri Slaby)
- perf build: Change the clang check back to 12.0.1 (Howard Chu)
- perf trace augmented_raw_syscalls: Add more checks to pass the verifier (Howard Chu)
- perf trace augmented_raw_syscalls: Add extra array index bounds checking to satisfy some BPF verifiers (Arnaldo Carvalho de Melo)
- perf trace: The return from 'write' isn't a pid (Arnaldo Carvalho de Melo)
- tools headers UAPI: Sync linux/const.h with the kernel headers (Arnaldo Carvalho de Melo)
- scsi: ufs: core: Fix another deadlock during RTC update (Peter Wang)
- scsi: scsi_debug: Fix do_device_access() handling of unexpected SG copy length (John Garry)
- Update the RHEL_DIFFERENCES help string (Don Zickus)
- Put build framework for RT kernel in place for Fedora (Clark Williams)
- cgroup: Fix potential overflow issue when checking max_depth (Xiu Jianfeng)
- cgroup/bpf: use a dedicated workqueue for cgroup bpf destruction (Chen Ridong)
- sched_ext: Fix enq_last_no_enq_fails selftest (Tejun Heo)
- sched_ext: Make cast_mask() inline (Tejun Heo)
- scx: Fix raciness in scx_ops_bypass() (David Vernet)
- scx: Fix exit selftest to use custom DSQ (David Vernet)
- sched_ext: Fix function pointer type mismatches in BPF selftests (Vishal Chourasia)
- selftests/sched_ext: add order-only dependency of runner.o on BPFOBJ (Ihor Solodrai)
- mm: krealloc: Fix MTE false alarm in __do_krealloc (Qun-Wei Lin)
- slub/kunit: fix a WARNING due to unwrapped __kmalloc_cache_noprof (Pei Xiao)
- mm: avoid unconditional one-tick sleep when swapcache_prepare fails (Barry Song)
- mseal: update mseal.rst (Jeff Xu)
- mm: split critical region in remap_file_pages() and invoke LSMs in between (Kirill A. Shutemov)
- selftests/mm: fix deadlock for fork after pthread_create with atomic_bool (Edward Liaw)
- Revert "selftests/mm: replace atomic_bool with pthread_barrier_t" (Edward Liaw)
- Revert "selftests/mm: fix deadlock for fork after pthread_create on ARM" (Edward Liaw)
- tools: testing: add expand-only mode VMA test (Lorenzo Stoakes)
- mm/vma: add expand-only VMA merge mode and optimise do_brk_flags() (Lorenzo Stoakes)
- resource,kexec: walk_system_ram_res_rev must retain resource flags (Gregory Price)
- nilfs2: fix kernel bug due to missing clearing of checked flag (Ryusuke Konishi)
- mm: numa_clear_kernel_node_hotplug: Add NUMA_NO_NODE check for node id (Nobuhiro Iwamatsu)
- ocfs2: pass u64 to ocfs2_truncate_inline maybe overflow (Edward Adam Davis)
- mm: shmem: fix data-race in shmem_getattr() (Jeongjun Park)
- mm: mark mas allocation in vms_abort_munmap_vmas as __GFP_NOFAIL (Jann Horn)
- x86/traps: move kmsan check after instrumentation_begin (Sabyrzhan Tasbolatov)
- resource: remove dependency on SPARSEMEM from GET_FREE_REGION (Huang Ying)
- mm/mmap: fix race in mmap_region() with ftruncate() (Liam R. Howlett)
- mm/page_alloc: let GFP_ATOMIC order-0 allocs access highatomic reserves (Matt Fleming)
- fork: only invoke khugepaged, ksm hooks if no error (Lorenzo Stoakes)
- fork: do not invoke uffd on fork if error occurs (Lorenzo Stoakes)
- mm/pagewalk: fix usage of pmd_leaf()/pud_leaf() without present check (David Hildenbrand)
- tpm: Lazily flush the auth session (Jarkko Sakkinen)
- tpm: Rollback tpm2_load_null() (Jarkko Sakkinen)
- tpm: Return tpm2_sessions_init() when null key creation fails (Jarkko Sakkinen)
- spi: spi-fsl-dspi: Fix crash when not using GPIO chip select (Frank Li)
- spi: geni-qcom: Fix boot warning related to pm_runtime and devres (Georgi Djakov)
- spi: mtk-snfi: fix kerneldoc for mtk_snand_is_page_ops() (Bartosz Golaszewski)
- spi: stm32: fix missing device mode capability in stm32mp25 (Alain Volmat)

* Tue Oct 29 2024 Jan Stancek <jstancek@redhat.com> [6.11.0-27.el10]
- Linux 6.12-rc5 (Linus Torvalds)
- x86/sev: Ensure that RMP table fixups are reserved (Ashish Kalra)
- x86/microcode/AMD: Split load_microcode_amd() (Borislav Petkov (AMD))
- x86/microcode/AMD: Pay attention to the stepping dynamically (Borislav Petkov (AMD))
- x86/lam: Disable ADDRESS_MASKING in most cases (Pawan Gupta)
- fgraph: Change the name of cpuhp state to "fgraph:online" (Steven Rostedt)
- fgraph: Fix missing unlock in register_ftrace_graph() (Li Huafei)
- platform/x86: asus-wmi: Fix thermal profile initialization (Armin Wolf)
- platform/x86: dell-wmi: Ignore suspend notifications (Armin Wolf)
- platform/x86/intel/pmc: Fix pmc_core_iounmap to call iounmap for valid addresses (Vamsi Krishna Brahmajosyula)
- platform/x86:intel/pmc: Revert "Enable the ACPI PM Timer to be turned off when suspended" (Marek Maslanka)
- firewire: core: fix invalid port index for parent device (Takashi Sakamoto)
- block: fix sanity checks in blk_rq_map_user_bvec (Xinyu Zhang)
- md/raid10: fix null ptr dereference in raid10_size() (Yu Kuai)
- md: ensure child flush IO does not affect origin bio->bi_status (Li Nan)
- xfs: update the pag for the last AG at recovery time (Christoph Hellwig)
- xfs: don't use __GFP_RETRY_MAYFAIL in xfs_initialize_perag (Christoph Hellwig)
- xfs: error out when a superblock buffer update reduces the agcount (Christoph Hellwig)
- xfs: update the file system geometry after recoverying superblock buffers (Christoph Hellwig)
- xfs: merge the perag freeing helpers (Christoph Hellwig)
- xfs: pass the exact range to initialize to xfs_initialize_perag (Christoph Hellwig)
- xfs: don't fail repairs on metadata files with no attr fork (Darrick J. Wong)
- generic: enable RPMB for all configs that enable MMC (Peter Robinson)
- fedora: riscv: Don't override MMC platform defaults (Peter Robinson)
- common: only enable on MMC_DW_BLUEFIELD (Peter Robinson)
- fedora: aarch64: Stop overriding CONFIG_MMC defaults (Peter Robinson)
- commong: The KS7010 driver has been removed (Peter Robinson)
- Revert "fs/9p: simplify iget to remove unnecessary paths" (Dominique Martinet)
- Revert "fs/9p: fix uaf in in v9fs_stat2inode_dotl" (Dominique Martinet)
- Revert "fs/9p: remove redundant pointer v9ses" (Dominique Martinet)
- Revert " fs/9p: mitigate inode collisions" (Dominique Martinet)
- cifs: fix warning when destroy 'cifs_io_request_pool' (Ye Bin)
- smb: client: Handle kstrdup failures for passwords (Henrique Carvalho)
- fuse: remove stray debug line (Miklos Szeredi)
- Revert "fuse: move initialization of fuse_file to fuse_writepages() instead of in callback" (Miklos Szeredi)
- fuse: update inode size after extending passthrough write (Amir Goldstein)
- fs: pass offset and result to backing_file end_write() callback (Amir Goldstein)
- nfsd: cancel nfsd_shrinker_work using sync mode in nfs4_state_shutdown_net (Yang Erkun)
- nfsd: fix race between laundromat and free_stateid (Olga Kornievskaia)
- ACPI: button: Add DMI quirk for Samsung Galaxy Book2 to fix initial lid detection issue (Shubham Panwar)
- ACPI: resource: Add LG 16T90SP to irq1_level_low_skip_override[] (Christian Heusel)
- ACPI: PRM: Clean up guid type in struct prm_handler_info (Dan Carpenter)
- ACPI: PRM: Find EFI_MEMORY_RUNTIME block for PRM handler and context (Koba Ko)
- powercap: dtpm_devfreq: Fix error check against dev_pm_qos_add_request() (Yuan Can)
- cpufreq: CPPC: fix perf_to_khz/khz_to_perf conversion exception (liwei)
- cpufreq: docs: Reflect latency changes in docs (Christian Loehle)
- PCI/pwrctl: Abandon QCom WCN probe on pre-pwrseq device-trees (Bartosz Golaszewski)
- PCI: Hold rescan lock while adding devices during host probe (Bartosz Golaszewski)
- fbdev: wm8505fb: select CONFIG_FB_IOMEM_FOPS (Arnd Bergmann)
- fbdev: da8xx: remove the driver (Bartosz Golaszewski)
- fbdev: Constify struct sbus_mmap_map (Christophe JAILLET)
- fbdev: nvidiafb: fix inconsistent indentation warning (SurajSonawane2415)
- fbdev: sstfb: Make CONFIG_FB_DEVICE optional (Gonzalo Silvalde Blanco)
- MAINTAINERS: add a keyword entry for the GPIO subsystem (Bartosz Golaszewski)
- ata: libata: Set DID_TIME_OUT for commands that actually timed out (Niklas Cassel)
- ASoC: qcom: sc7280: Fix missing Soundwire runtime stream alloc (Krzysztof Kozlowski)
- ASoC: fsl_micfil: Add sample rate constraint (Shengjiu Wang)
- ASoC: rt722-sdca: increase clk_stop_timeout to fix clock stop issue (Jack Yu)
- ASoC: SOF: Intel: hda: Always clean up link DMA during stop (Ranjani Sridharan)
- soundwire: intel_ace2x: Send PDI stream number during prepare (Ranjani Sridharan)
- ASoC: SOF: Intel: hda: Handle prepare without close for non-HDA DAI's (Ranjani Sridharan)
- ASoC: SOF: ipc4-topology: Do not set ALH node_id for aggregated DAIs (Ranjani Sridharan)
- ASoC: fsl_micfil: Add a flag to distinguish with different volume control types (Chancel Liu)
- ASoC: codecs: lpass-rx-macro: fix RXn(rx,n) macro for DSM_CTL and SEC7 regs (Alexey Klimov)
- ASoC: Change my e-mail to gmail (Kirill Marinushkin)
- ASoC: Intel: soc-acpi: lnl: Add match entry for TM2 laptops (Derek Fang)
- ASoC: amd: yc: Fix non-functional mic on ASUS E1404FA (Ilya Dudikov)
- MAINTAINERS: Update maintainer list for MICROCHIP ASOC, SSC and MCP16502 drivers (Andrei Simion)
- ASoC: qcom: Select missing common Soundwire module code on SDM845 (Krzysztof Kozlowski)
- ASoC: fsl_esai: change dev_warn to dev_dbg in irq handler (Shengjiu Wang)
- ASoC: rsnd: Fix probe failure on HiHope boards due to endpoint parsing (Lad Prabhakar)
- ASoC: max98388: Fix missing increment of variable slot_found (Colin Ian King)
- ASoC: amd: yc: Add quirk for ASUS Vivobook S15 M3502RA (Christian Heusel)
- ASoC: topology: Bump minimal topology ABI version (Amadeusz Sławiński)
- ASoC: codecs: Fix error handling in aw_dev_get_dsp_status function (Zhu Jun)
- ASoC: qcom: sdm845: add missing soundwire runtime stream alloc (Alexey Klimov)
- ASoC: loongson: Fix component check failed on FDT systems (Binbin Zhou)
- ASoC: dapm: avoid container_of() to get component (Benjamin Bara)
- ASoC: SOF: Intel: hda-loader: do not wait for HDaudio IOC (Kai Vehmanen)
- ASoC: SOF: amd: Fix for ACP SRAM addr for acp7.0 platform (Venkata Prasad Potturu)
- ASoC: SOF: amd: Add error log for DSP firmware validation failure (Venkata Prasad Potturu)
- ASoC: Intel: avs: Update stream status in a separate thread (Amadeusz Sławiński)
- ASoC: dt-bindings: davinci-mcasp: Fix interrupt properties (Miquel Raynal)
- ASoC: qcom: Fix NULL Dereference in asoc_qcom_lpass_cpu_platform_probe() (Zichen Xie)
- ALSA: hda/realtek: Update default depop procedure (Kailang Yang)
- ALSA: hda/tas2781: select CRC32 instead of CRC32_SARWATE (Eric Biggers)
- ALSA: hda/realtek: Add subwoofer quirk for Acer Predator G9-593 (José Relvas)
- ALSA: firewire-lib: Avoid division by zero in apply_constraint_to_size() (Andrey Shumilin)
- drm/xe: Don't restart parallel queues multiple times on GT reset (Nirmoy Das)
- drm/xe/ufence: Prefetch ufence addr to catch bogus address (Nirmoy Das)
- drm/xe: Handle unreliable MMIO reads during forcewake (Shuicheng Lin)
- drm/xe/guc/ct: Flush g2h worker in case of g2h response timeout (Badal Nilawar)
- drm/xe: Enlarge the invalidation timeout from 150 to 500 (Shuicheng Lin)
- drm/bridge: tc358767: fix missing of_node_put() in for_each_endpoint_of_node() (Javier Carrasco)
- drm/bridge: Fix assignment of the of_node of the parent to aux bridge (Abel Vesa)
- i915: fix DRM_I915_GVT_KVMGT dependencies (Arnd Bergmann)
- drm/amdgpu: handle default profile on on devices without fullscreen 3D (Alex Deucher)
- drm/amd/display: Disable PSR-SU on Parade 08-01 TCON too (Mario Limonciello)
- drm/amdgpu: fix random data corruption for sdma 7 (Frank Min)
- drm/amd/display: temp w/a for DP Link Layer compliance (Aurabindo Pillai)
- drm/amd/display: temp w/a for dGPU to enter idle optimizations (Aurabindo Pillai)
- drm/amd/pm: update deep sleep status on smu v14.0.2/3 (Kenneth Feng)
- drm/amd/pm: update overdrive function on smu v14.0.2/3 (Kenneth Feng)
- drm/amd/pm: update the driver-fw interface file for smu v14.0.2/3 (Kenneth Feng)
- drm/amd: Guard against bad data for ATIF ACPI method (Mario Limonciello)
- x86: fix whitespace in runtime-const assembler output (Linus Torvalds)
- x86: fix user address masking non-canonical speculation issue (Linus Torvalds)
- v6.12-rc4-rt6 (Sebastian Andrzej Siewior)
- sched: Update the lazy-preempt bits. (Sebastian Andrzej Siewior)
- timer: Update the ktimersd series. (Sebastian Andrzej Siewior)
- v6.12-rc4-rt5 (Sebastian Andrzej Siewior)
- bpf: Check validity of link->type in bpf_link_show_fdinfo() (Hou Tao)
- bpf: Add the missing BPF_LINK_TYPE invocation for sockmap (Hou Tao)
- bpf: fix do_misc_fixups() for bpf_get_branch_snapshot() (Andrii Nakryiko)
- bpf,perf: Fix perf_event_detach_bpf_prog error handling (Jiri Olsa)
- selftests/bpf: Add test for passing in uninit mtu_len (Daniel Borkmann)
- selftests/bpf: Add test for writes to .rodata (Daniel Borkmann)
- bpf: Remove MEM_UNINIT from skb/xdp MTU helpers (Daniel Borkmann)
- bpf: Fix overloading of MEM_UNINIT's meaning (Daniel Borkmann)
- bpf: Add MEM_WRITE attribute (Daniel Borkmann)
- bpf: Preserve param->string when parsing mount options (Hou Tao)
- bpf, arm64: Fix address emission with tag-based KASAN enabled (Peter Collingbourne)
- net: dsa: mv88e6xxx: support 4000ps cycle counter period (Shenghao Yang)
- net: dsa: mv88e6xxx: read cycle counter period from hardware (Shenghao Yang)
- net: dsa: mv88e6xxx: group cycle counter coefficients (Shenghao Yang)
- net: usb: qmi_wwan: add Fibocom FG132 0x0112 composition (Reinhard Speyerer)
- hv_netvsc: Fix VF namespace also in synthetic NIC NETDEV_REGISTER event (Haiyang Zhang)
- net: dsa: microchip: disable EEE for KSZ879x/KSZ877x/KSZ876x (Tim Harvey)
- Bluetooth: ISO: Fix UAF on iso_sock_timeout (Luiz Augusto von Dentz)
- Bluetooth: SCO: Fix UAF on sco_sock_timeout (Luiz Augusto von Dentz)
- Bluetooth: hci_core: Disable works on hci_unregister_dev (Luiz Augusto von Dentz)
- xfrm: fix one more kernel-infoleak in algo dumping (Petr Vaganov)
- xfrm: validate new SA's prefixlen using SA family when sel.family is unset (Sabrina Dubroca)
- xfrm: policy: remove last remnants of pernet inexact list (Florian Westphal)
- xfrm: respect ip protocols rules criteria when performing dst lookups (Eyal Birger)
- xfrm: extract dst lookup parameters into a struct (Eyal Birger)
- posix-clock: posix-clock: Fix unbalanced locking in pc_clock_settime() (Jinjie Ruan)
- r8169: avoid unsolicited interrupts (Heiner Kallweit)
- net: sched: use RCU read-side critical section in taprio_dump() (Dmitry Antipov)
- net: sched: fix use-after-free in taprio_change() (Dmitry Antipov)
- net/sched: act_api: deny mismatched skip_sw/skip_hw flags for actions created by classifiers (Vladimir Oltean)
- net: usb: usbnet: fix name regression (Oliver Neukum)
- mlxsw: spectrum_router: fix xa_store() error checking (Yuan Can)
- netfilter: xtables: fix typo causing some targets not to load on IPv6 (Pablo Neira Ayuso)
- netfilter: bpf: must hold reference on net namespace (Florian Westphal)
- virtio_net: fix integer overflow in stats (Michael S. Tsirkin)
- net: fix races in netdev_tx_sent_queue()/dev_watchdog() (Eric Dumazet)
- net: wwan: fix global oob in wwan_rtnl_policy (Lin Ma)
- fsl/fman: Fix refcount handling of fman-related devices (Aleksandr Mishin)
- fsl/fman: Save device references taken in mac_probe() (Aleksandr Mishin)
- MAINTAINERS: add samples/pktgen to NETWORKING [GENERAL] (Hangbin Liu)
- mailmap: update entry for Jesper Dangaard Brouer (Jesper Dangaard Brouer)
- net: dsa: mv88e6xxx: Fix error when setting port policy on mv88e6393x (Peter Rashleigh)
- octeon_ep: Add SKB allocation failures handling in __octep_oq_process_rx() (Aleksandr Mishin)
- octeon_ep: Implement helper for iterating packets in Rx queue (Aleksandr Mishin)
- bnxt_en: replace ptp_lock with irqsave variant (Vadim Fedorenko)
- net: phy: dp83822: Fix reset pin definitions (Michel Alex)
- MAINTAINERS: add Simon as an official reviewer (Jakub Kicinski)
- net: plip: fix break; causing plip to never transmit (Jakub Boehm)
- be2net: fix potential memory leak in be_xmit() (Wang Hai)
- net/sun3_82586: fix potential memory leak in sun3_82586_send_packet() (Wang Hai)
- net: pse-pd: Fix out of bound for loop (Kory Maincent)
- HID: lenovo: Add support for Thinkpad X1 Tablet Gen 3 keyboard (Hans de Goede)
- HID: multitouch: Add quirk for Logitech Bolt receiver w/ Casa touchpad (Kenneth Albanowski)
- HID: i2c-hid: Delayed i2c resume wakeup for 0x0d42 Goodix touchpad (Bartłomiej Maryńczak)
- LoongArch: KVM: Mark hrtimer to expire in hard interrupt context (Huacai Chen)
- LoongArch: Make KASAN usable for variable cpu_vabits (Huacai Chen)
- LoongArch: Set initial pte entry with PAGE_GLOBAL for kernel space (Bibo Mao)
- LoongArch: Don't crash in stack_top() for tasks without vDSO (Thomas Weißschuh)
- LoongArch: Set correct size for vDSO code mapping (Huacai Chen)
- LoongArch: Enable IRQ if do_ale() triggered in irq-enabled context (Huacai Chen)
- LoongArch: Get correct cores_per_package for SMT systems (Huacai Chen)
- LoongArch: Use "Exception return address" to comment ERA (Yanteng Si)
- tracing: Consider the NULL character when validating the event length (Leo Yan)
- tracing/probes: Fix MAX_TRACE_ARGS limit handling (Mikel Rychliski)
- objpool: fix choosing allocation for percpu slots (Viktor Malik)
- btrfs: fix passing 0 to ERR_PTR in btrfs_search_dir_index_item() (Yue Haibing)
- btrfs: reject ro->rw reconfiguration if there are hard ro requirements (Qu Wenruo)
- btrfs: fix read corruption due to race with extent map merging (Boris Burkov)
- btrfs: fix the delalloc range locking if sector size < page size (Qu Wenruo)
- btrfs: qgroup: set a more sane default value for subtree drop threshold (Qu Wenruo)
- btrfs: clear force-compress on remount when compress mount option is given (Filipe Manana)
- btrfs: zoned: fix zone unusable accounting for freed reserved extent (Naohiro Aota)
- jfs: Fix sanity check in dbMount (Dave Kleikamp)
- bcachefs: Set bch_inode_unpacked.bi_snapshot in old inode path (Kent Overstreet)
- bcachefs: Mark more errors as AUTOFIX (Kent Overstreet)
- bcachefs: Workaround for kvmalloc() not supporting > INT_MAX allocations (Kent Overstreet)
- bcachefs: Don't use wait_event_interruptible() in recovery (Kent Overstreet)
- bcachefs: Fix __bch2_fsck_err() warning (Kent Overstreet)
- bcachefs: fsck: Improve hash_check_key() (Kent Overstreet)
- bcachefs: bch2_hash_set_or_get_in_snapshot() (Kent Overstreet)
- bcachefs: Repair mismatches in inode hash seed, type (Kent Overstreet)
- bcachefs: Add hash seed, type to inode_to_text() (Kent Overstreet)
- bcachefs: INODE_STR_HASH() for bch_inode_unpacked (Kent Overstreet)
- bcachefs: Run in-kernel offline fsck without ratelimit errors (Kent Overstreet)
- bcachefs: skip mount option handle for empty string. (Hongbo Li)
- bcachefs: fix incorrect show_options results (Hongbo Li)
- bcachefs: Fix data corruption on -ENOSPC in buffered write path (Kent Overstreet)
- bcachefs: bch2_folio_reservation_get_partial() is now better behaved (Kent Overstreet)
- bcachefs: fix disk reservation accounting in bch2_folio_reservation_get() (Kent Overstreet)
- bcachefS: ec: fix data type on stripe deletion (Kent Overstreet)
- bcachefs: Don't use commit_do() unnecessarily (Kent Overstreet)
- bcachefs: handle restarts in bch2_bucket_io_time_reset() (Kent Overstreet)
- bcachefs: fix restart handling in __bch2_resume_logged_op_finsert() (Kent Overstreet)
- bcachefs: fix restart handling in bch2_alloc_write_key() (Kent Overstreet)
- bcachefs: fix restart handling in bch2_do_invalidates_work() (Kent Overstreet)
- bcachefs: fix missing restart handling in bch2_read_retry_nodecode() (Kent Overstreet)
- bcachefs: fix restart handling in bch2_fiemap() (Kent Overstreet)
- bcachefs: fix bch2_hash_delete() error path (Kent Overstreet)
- bcachefs: fix restart handling in bch2_rename2() (Kent Overstreet)
- Revert "9p: Enable multipage folios" (Dominique Martinet)
- Trim Changelog for 6.12 (Justin M. Forbes)
- Enable CONFIG_SECURITY_IPE for Fedora (Zbigniew Jędrzejewski-Szmek)
- redhat: allow to override VERSION_ON_UPSTREAM from command line (Jan Stancek)
- redhat: configs: Enable CONFIG_SECURITY_TOMOYO in Fedora kernels (Tetsuo Handa)

* Wed Oct 23 2024 Jan Stancek <jstancek@redhat.com> [6.11.0-26.el10]
- redhat: drop ARK changelog (Jan Stancek) [RHEL-56700]
- redhat: regenerate test-data (Jan Stancek) [RHEL-56700]
- redhat: rpminspect.yaml: more tests to ignore in selftests (Jan Stancek) [RHEL-56700]
- redhat/Makefile.variables: don't set DISTRO (Jan Stancek) [RHEL-56700]
- redhat/Makefile.variables: set PATCHLIST_URL to none (Jan Stancek) [RHEL-56700]
- redhat: gitlab-ci: add initial version (Jan Stancek) [RHEL-56700]
- redhat: update rpminspect with c9s one (Jan Stancek) [RHEL-56700]
- redhat: remove fedora configs and files (Jan Stancek) [RHEL-56700]
- redhat: init RHEL10.0 beta variables and dist tag (Jan Stancek) [RHEL-56700]
- redhat: set release version (Jan Stancek) [RHEL-56700]
- redhat: fix CONFIG_PREEMPT config (Jan Stancek) [RHEL-56700]
- KVM: selftests: Fix build on on non-x86 architectures (Mark Brown)
- 9p: fix slab cache name creation for real (Linus Torvalds)
- KVM: arm64: Ensure vgic_ready() is ordered against MMIO registration (Oliver Upton)
- KVM: arm64: vgic: Don't check for vgic_ready() when setting NR_IRQS (Oliver Upton)
- KVM: arm64: Fix shift-out-of-bounds bug (Ilkka Koskinen)
- KVM: arm64: Shave a few bytes from the EL2 idmap code (Marc Zyngier)
- KVM: arm64: Don't eagerly teardown the vgic on init error (Marc Zyngier)
- KVM: arm64: Expose S1PIE to guests (Mark Brown)
- KVM: arm64: nv: Clarify safety of allowing TLBI unmaps to reschedule (Oliver Upton)
- KVM: arm64: nv: Punt stage-2 recycling to a vCPU request (Oliver Upton)
- KVM: arm64: nv: Do not block when unmapping stage-2 if disallowed (Oliver Upton)
- KVM: arm64: nv: Keep reference on stage-2 MMU when scheduled out (Oliver Upton)
- KVM: arm64: Unregister redistributor for failed vCPU creation (Oliver Upton)
- KVM: selftests: aarch64: Add writable test for ID_AA64PFR1_EL1 (Shaoqin Huang)
- KVM: arm64: Allow userspace to change ID_AA64PFR1_EL1 (Shaoqin Huang)
- KVM: arm64: Use kvm_has_feat() to check if FEAT_SSBS is advertised to the guest (Shaoqin Huang)
- KVM: arm64: Disable fields that KVM doesn't know how to handle in ID_AA64PFR1_EL1 (Shaoqin Huang)
- KVM: arm64: Make the exposed feature bits in AA64DFR0_EL1 writable from userspace (Shameer Kolothum)
- RISCV: KVM: use raw_spinlock for critical section in imsic (Cyan Yang)
- KVM: selftests: Fix out-of-bounds reads in CPUID test's array lookups (Sean Christopherson)
- KVM: selftests: x86: Avoid using SSE/AVX instructions (Vitaly Kuznetsov)
- KVM: nSVM: Ignore nCR3[4:0] when loading PDPTEs from memory (Sean Christopherson)
- KVM: VMX: reset the segment cache after segment init in vmx_vcpu_reset() (Maxim Levitsky)
- KVM: x86: Clean up documentation for KVM_X86_QUIRK_SLOT_ZAP_ALL (Sean Christopherson)
- KVM: x86/mmu: Add lockdep assert to enforce safe usage of kvm_unmap_gfn_range() (Sean Christopherson)
- KVM: x86/mmu: Zap only SPs that shadow gPTEs when deleting memslot (Sean Christopherson)
- x86/kvm: Override default caching mode for SEV-SNP and TDX (Kirill A. Shutemov)
- KVM: Remove unused kvm_vcpu_gfn_to_pfn_atomic (Dr. David Alan Gilbert)
- KVM: Remove unused kvm_vcpu_gfn_to_pfn (Dr. David Alan Gilbert)
- uprobe: avoid out-of-bounds memory access of fetching args (Qiao Ma)
- proc: Fix W=1 build kernel-doc warning (Thorsten Blum)
- afs: Fix lock recursion (David Howells)
- fs: Fix uninitialized value issue in from_kuid and from_kgid (Alessandro Zanni)
- fs: don't try and remove empty rbtree node (Christian Brauner)
- netfs: Downgrade i_rwsem for a buffered write (David Howells)
- nilfs2: fix kernel bug due to missing clearing of buffer delay flag (Ryusuke Konishi)
- openat2: explicitly return -E2BIG for (usize > PAGE_SIZE) (Aleksa Sarai)
- netfs: fix documentation build error (Jonathan Corbet)
- netfs: In readahead, put the folio refs as soon extracted (David Howells)
- crypto: lib/mpi - Fix an "Uninitialized scalar variable" issue (Qianqiang Liu)
- Revert "Merge branch 'enablement/gpio-expander' into 'os-build'" (Justin M. Forbes)
- v6.12-rc2-rt4 (Sebastian Andrzej Siewior)
- sched: Replace PREEMPT_AUTO with LAZY_PREEMPT. (Sebastian Andrzej Siewior)
- softirq: Clean white space. (Sebastian Andrzej Siewior)
- mm: percpu: Increase PERCPU_DYNAMIC_SIZE_SHIFT on certain builds. (Sebastian Andrzej Siewior)
- ARM: vfp: Rename the locking functions. (Sebastian Andrzej Siewior)
- v6.12-rc2-rt3 (Sebastian Andrzej Siewior)
- v6.12-rc1-rt2 (Sebastian Andrzej Siewior)
- Revert "time: Allow to preempt after a callback." + dependencies. (Sebastian Andrzej Siewior)
- Revert "sched/rt: Don't try push tasks if there are none." (Sebastian Andrzej Siewior)
- Add localversion for -RT release (Thomas Gleixner)
- sysfs: Add /sys/kernel/realtime entry (Clark Williams)
- riscv: add PREEMPT_AUTO support (Jisheng Zhang)
- POWERPC: Allow to enable RT (Sebastian Andrzej Siewior)
- powerpc/stackprotector: work around stack-guard init from atomic (Sebastian Andrzej Siewior)
- powerpc/kvm: Disable in-kernel MPIC emulation for PREEMPT_RT (Bogdan Purcareata)
- powerpc/pseries: Select the generic memory allocator. (Sebastian Andrzej Siewior)
- powerpc/pseries/iommu: Use a locallock instead local_irq_save() (Sebastian Andrzej Siewior)
- powerpc: traps: Use PREEMPT_RT (Sebastian Andrzej Siewior)
- ARM: Allow to enable RT (Sebastian Andrzej Siewior)
- ARM: vfp: Move sending signals outside of vfp_lock()ed section. (Sebastian Andrzej Siewior)
- ARM: vfp: Use vfp_lock() in vfp_support_entry(). (Sebastian Andrzej Siewior)
- ARM: vfp: Use vfp_lock() in vfp_sync_hwstate(). (Sebastian Andrzej Siewior)
- ARM: vfp: Provide vfp_lock() for VFP locking. (Sebastian Andrzej Siewior)
- arm: Disable FAST_GUP on PREEMPT_RT if HIGHPTE is also enabled. (Sebastian Andrzej Siewior)
- ARM: enable irq in translation/section permission fault handlers (Yadi.hu)
- arm: Disable jump-label on PREEMPT_RT. (Thomas Gleixner)
- sched: define TIF_ALLOW_RESCHED (Thomas Gleixner)
- Revert "drm/i915: Depend on !PREEMPT_RT." (Sebastian Andrzej Siewior)
- drm/i915/guc: Consider also RCU depth in busy loop. (Sebastian Andrzej Siewior)
- drm/i915: Drop the irqs_disabled() check (Sebastian Andrzej Siewior)
- drm/i915/gt: Use spin_lock_irq() instead of local_irq_disable() + spin_lock() (Sebastian Andrzej Siewior)
- drm/i915: Disable tracing points on PREEMPT_RT (Sebastian Andrzej Siewior)
- drm/i915: Don't check for atomic context on PREEMPT_RT (Sebastian Andrzej Siewior)
- drm/i915: Don't disable interrupts on PREEMPT_RT during atomic updates (Mike Galbraith)
- drm/i915: Use preempt_disable/enable_rt() where recommended (Mike Galbraith)
- time: Allow to preempt after a callback. (Sebastian Andrzej Siewior)
- softirq: Add function to preempt serving softirqs. (Sebastian Andrzej Siewior)
- sched/core: Provide a method to check if a task is PI-boosted. (Sebastian Andrzej Siewior)
- softirq: Wake ktimers thread also in softirq. (Junxiao Chang)
- tick: Fix timer storm since introduction of timersd (Frederic Weisbecker)
- rcutorture: Also force sched priority to timersd on boosting test. (Frederic Weisbecker)
- softirq: Use a dedicated thread for timer wakeups. (Sebastian Andrzej Siewior)
- locking/rt: Annotate unlock followed by lock for sparse. (Sebastian Andrzej Siewior)
- locking/rt: Add sparse annotation for RCU. (Sebastian Andrzej Siewior)
- locking/rt: Remove one __cond_lock() in RT's spin_trylock_irqsave() (Sebastian Andrzej Siewior)
- locking/rt: Add sparse annotation PREEMPT_RT's sleeping locks. (Sebastian Andrzej Siewior)
- sched/rt: Don't try push tasks if there are none. (Sebastian Andrzej Siewior)
- serial: 8250: Revert "drop lockdep annotation from serial8250_clear_IER()" (John Ogness)
- serial: 8250: Switch to nbcon console (John Ogness)
- Linux v6.12-rc4


###
# The following Emacs magic makes C-c C-e use UTC dates.
# Local Variables:
# rpm-change-log-uses-utc: t
# End:
###
