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

