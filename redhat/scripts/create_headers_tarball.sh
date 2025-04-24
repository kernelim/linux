#!/bin/bash
# shellcheck disable=SC2035
# shellcheck disable=SC2038
# shellcheck disable=SC3044
# This script is aimed at generating the headers from the kernel sources.

set -e

# ARCH_LIST below has the default list of supported architectures
# (the architectures names may be different from rpm, you list here the
# names of arch/<arch> directories in the kernel sources)
ARCH_LIST="arm arm64 powerpc riscv s390 x86"

headers_dir=$(mktemp -d)
trap 'rm -rf "$headers_dir"' SIGHUP SIGINT SIGTERM EXIT

archs=${ARCH_LIST:-$(ls arch)}

# Upstream rmeoved the headers_install_all target so do it manually
for arch in $archs; do
	cd "$TOPDIR"
	mkdir "$headers_dir/arch-$arch"
	make ARCH="$arch" INSTALL_HDR_PATH="$headers_dir/arch-$arch" KBUILD_HEADERS=install headers_install
done
find "$headers_dir" \
	\( -name .install -o -name .check -o \
	-name ..install.cmd -o -name ..check.cmd \) | xargs rm -f

TARBALL="$SOURCES/kernel-headers-$UPSTREAM_TARBALL_NAME.tar.xz"
pushd "$headers_dir"
	tar -Jcf "$TARBALL" *
popd

echo wrote "$TARBALL"
