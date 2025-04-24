ifeq ($(filter dist-% distg-%,$(MAKECMDGOALS)),)
	include Makefile
endif

_OUTPUT := "."
# this section is needed in order to make O= to work
ifeq ("$(origin O)", "command line")
  _OUTPUT := "$(abspath $(O))"
  _EXTRA_ARGS := O=$(_OUTPUT)
endif
dist-%::
	$(MAKE) -C redhat $(@) $(_EXTRA_ARGS)

distg-%::
	$(MAKE) -C redhat $(@) $(_EXTRA_ARGS)

ifeq (,$(filter $(ARCH), x86 x86_64 powerpc s390 aarch64))
  ifneq ($(KBUILD_EXTMOD),)
    # always strip out error flags for external modules
    KBUILD_CPPFLAGS := $(filter-out -Werror,$(KBUILD_CPPFLAGS))
    KBUILD_RUSTFLAGS := $(filter-out -Dwarnings,$(KBUILD_RUSTFLAGS))
  endif
endif
