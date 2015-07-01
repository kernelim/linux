#
# Makefile for the drm device driver.  This driver provides support for the
# Direct Rendering Infrastructure (DRI) in XFree86 4.1.0 and higher.

ccflags-y := -Iinclude/drm
ccflags-y += -include drm/drm_backport.h
i810-y := i810_drv.o i810_dma.o

obj-$(CONFIG_DRM_I810)	+= i810.o
