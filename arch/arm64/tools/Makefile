# SPDX-License-Identifier: GPL-2.0

gen := arch/$(ARCH)/include/generated
kapi := $(gen)/asm

kapi-hdrs-y := $(kapi)/cpucaps.h $(kapi)/sysreg-defs.h

targets += $(addprefix ../../../,$(gen-y) $(kapi-hdrs-y))

PHONY += kapi

kapi:   $(kapi-hdrs-y) $(gen-y)

# Create output directory if not already present
_dummy := $(shell [ -d '$(kapi)' ] || mkdir -p '$(kapi)')

quiet_cmd_gen_cpucaps = GEN     $@
      cmd_gen_cpucaps = mkdir -p $(dir $@) && \
                     $(AWK) -f $(filter-out $(PHONY),$^) > $@

quiet_cmd_gen_sysreg = GEN     $@
      cmd_gen_sysreg = mkdir -p $(dir $@); $(AWK) -f $(real-prereqs) > $@

$(kapi)/cpucaps.h: $(src)/gen-cpucaps.awk $(src)/cpucaps FORCE
	$(call if_changed,gen_cpucaps)

$(kapi)/sysreg-defs.h: $(src)/gen-sysreg.awk $(src)/sysreg FORCE
	$(call if_changed,gen_sysreg)
