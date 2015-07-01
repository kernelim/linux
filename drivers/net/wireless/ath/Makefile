obj-$(CONFIG_ATH5K)		+= ath5k/
obj-$(CONFIG_ATH9K_HW)		+= ath9k/
obj-$(CONFIG_CARL9170)		+= carl9170/

obj-$(CONFIG_ATH_COMMON)	+= ath.o

ath-objs :=	main.o \
		regd.o \
		hw.o \
		key.o \
		dfs_pattern_detector.o \
		dfs_pri_detector.o

ath-$(CONFIG_ATH_DEBUG) += debug.o
ath-$(CONFIG_ATH_TRACEPOINTS) += trace.o

ccflags-y += -D__CHECK_ENDIAN__

CFLAGS_trace.o := -I$(src)
