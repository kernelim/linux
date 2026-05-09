# SPDX-License-Identifier: GPL-2.0-only
ccflags-$(CONFIG_ARCH_MULTIPLATFORM) := -I$(src)/include

obj-$(CONFIG_SMP) += headsmp.o platsmp.o
obj-$(CONFIG_HOTPLUG_CPU)		+= hotplug.o
