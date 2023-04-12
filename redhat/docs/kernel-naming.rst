.. _kernel-naming:

=============
Kernel Naming
=============

The kernel NVR looks like, for example,
kernel-5.17.0-0.rc8.551acdc3c3d2.124.test.fc35.  This string contains
information about the upstream release, a unique build number, and information
about the distribution the RPM was targeted for.  An explanation of each of the
fields and how the fields are used in the kernel NVR, is below.

**PACKAGE_NAME**: This is the name of the package.  By default this is
'kernel', but a well-known variant is kernel-rt.

**SPECKVERSION**: This is the VERSION variable defined in the top-level linux
Makefile.

**SPECKPATCHLEVEL**: This is the PATCHLEVEL variable defined in the top-level
linux Makefile.

**SPECKSUBLEVEL**: This is the SUBLEVEL variable defined in the top-level linux
Makefile.

**UPSTREAMBUILD**: This is a representation of the upstream build information.
It includes the EXTRAVERSION variable (defined in the top-level Makefile) or
'rc0' if the tree is based on an a specific upstream release.  If the tree is
not based on a specific "rc" release, this field also contains a git hash
reference to the top of tree commit.

**BUILD**: This is the RHEL_RELEASE variable defined in the top-level linux
Makefile.rhelver.

**DISTLOCALVERSION**: By default, this variable is set to ".test".  This value can
be overriden by defining a string in redhat/localversion.

**DIST**:  This is the dist release suffix used in the package release, eg.
.fc34 or .el9.

The kernel name is constructed as

$(PACKAGE_NAME)-$(SPECKVERSION).$(SPECKPATCHLEVEL).$(SPECKSUBLEVEL)-$(UPSTREAMBUILD)$(BUILD)$(DISTLOCALVERSION)$(DIST)

In general, the kernel follows the Fedora Naming Guidelines, `https://fedoraproject.org/wiki/Packaging:Naming?rd=Packaging:NamingGuidelines <https://fedoraproject.org/wiki/Packaging:Naming?rd=Packaging:NamingGuidelines>`__.
