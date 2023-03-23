---
title: A Kernel Developer's Guide to kABI
weight: 100
---
Contained within is a "guiding document" that can be used for people who need to understand kABI.

There can be a prohibitively restrictive burden associated with maintaining RHEL's kABI (Kernel Application Binary Interface) commitment that persists throughout the release's entire lifecycle if subsystem maintainers don't proactively accommodate for upstream back-ports.  RHEL kernel developers need to be aware of, and fully comprehend, such restrictions, which is the focus of this document.

## Pre-requisites

You will need to have these LaTeX packages installed to be able to generate this document in PDF format.

```dnf install -y texlive texlive-listingsutf8```

Running `make installdependencies` will execute this command for you.

<sub>Note: The texlive-listingsutf8 package is provided in supported Fedora releases, but not available in RHEL.</sub>

## Building the document

Running this command will create a number of files in the current working directory, but the most important of which is kABI.pdf.

```pdflatex kABI.tex```

Or simply running `make` will build it as well.