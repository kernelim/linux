# SPDX-License-Identifier: GPL-2.0
OBJECT_FILES_NON_STANDARD := y

purgatory-y := purgatory.o stack.o setup-x86_$(BITS).o sha256.o entry64.o string.o

targets += $(purgatory-y)
PURGATORY_OBJS = $(addprefix $(obj)/,$(purgatory-y))

$(obj)/string.o: $(srctree)/arch/x86/boot/compressed/string.c FORCE
	$(call if_changed_rule,cc_o_c)

$(obj)/sha256.o: $(srctree)/lib/crypto/sha256.c FORCE
	$(call if_changed_rule,cc_o_c)

CFLAGS_sha256.o := -D__DISABLE_EXPORTS

# When linking purgatory.ro with -r unresolved symbols are not checked,
# also link a purgatory.chk binary without -r to check for unresolved symbols.
PURGATORY_LDFLAGS := -e purgatory_start -nostdlib -z nodefaultlib
LDFLAGS_purgatory.ro := -r $(PURGATORY_LDFLAGS)
LDFLAGS_purgatory.chk := $(PURGATORY_LDFLAGS)
targets += purgatory.ro purgatory.chk

# Sanitizer, etc. runtimes are unavailable and cannot be linked here.
GCOV_PROFILE   := n
KASAN_SANITIZE	:= n
KCSAN_SANITIZE	:= n
UBSAN_SANITIZE := n
KCOV_INSTRUMENT := n

# Default KBUILD_CFLAGS can have -pg option set when FTRACE is enabled. That
# in turn leaves some undefined symbols like __fentry__ in purgatory and not
# sure how to relocate those. Like kexec-tools, use custom flags.

KBUILD_CFLAGS := -fno-strict-aliasing -Wall -Wstrict-prototypes -fno-zero-initialized-in-bss -fno-builtin -ffreestanding -c -Os -mcmodel=large
KBUILD_CFLAGS += -m$(BITS)
KBUILD_CFLAGS += $(call cc-option,-fno-PIE)
KBUILD_CFLAGS += -DDISABLE_BRANCH_PROFILING
KBUILD_CFLAGS += $(call cc-option,-fno-stack-protector)

$(obj)/purgatory.ro: $(PURGATORY_OBJS) FORCE
		$(call if_changed,ld)

$(obj)/purgatory.chk: $(obj)/purgatory.ro FORCE
		$(call if_changed,ld)

targets += kexec-purgatory.c

CMD_BIN2C = $(objtree)/scripts/basic/bin2c
quiet_cmd_bin2c = BIN2C   $@
      cmd_bin2c = $(CMD_BIN2C) kexec_purgatory < $< > $@

$(obj)/kexec-purgatory.c: $(obj)/purgatory.ro $(obj)/purgatory.chk FORCE
	$(call if_changed,bin2c)

obj-$(CONFIG_KEXEC_FILE)	+= kexec-purgatory.o
