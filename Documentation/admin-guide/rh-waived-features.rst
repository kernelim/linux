.. _rh_waived_features:

=======================
Red Hat Waived Features
=======================

Red Hat waived features are features considered unmaintained, insecure, rudimentary, or
deprecated and are shipped in RHEL only for customer convenience. These features are disabled
by default but can be enabled on demand via the ``rh_waived`` kernel boot parameter. To allow
a set of waived features, append ``rh_waived=<feature name>,...,<feature name>`` to the kernel
cmdline. Appending only ``rh_waived`` (with no arguments) will enable all waived features
listed below.

The waived features listed in the next session follow the pattern below:

- feature name
        feature description

List of Red Hat Waived Features
===============================

