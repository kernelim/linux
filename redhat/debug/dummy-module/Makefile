ifneq ($(KERNELRELEASE),)

obj-m	:= dummy-module.o

else

KDIR	:= /lib/modules/$(shell uname -r)/build
PWD	:= $(shell pwd)

default:
	$(MAKE) -C $(KDIR) M=$(PWD)
endif

clean:
	rm -rf *o .*.cmd .tmp* *.mod.c
