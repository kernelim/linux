# mpt2-3sas makefile

obj-$(CONFIG_SCSI_MPT2SAS)     += mpt2sas.o
obj-$(CONFIG_SCSI_MPT3SAS)     += mpt3sas.o
 
obj-m += mpt3sas.o
mpt3sas-y +=  mpt3sas_base.o     \
		mpt3sas_config.o \
		mpt3sas_scsih.o      \
		mpt3sas_transport.o     \
		mpt3sas_ctl.o	\
		mpt3sas_trigger_diag.o \
		mpt3sas_warpdrive.o

obj-m += mpt2sas.o
mpt2sas-y +=  mpt3sas_base.o     \
		mpt3sas_config.o \
		wrapper_mpt3sas_scsih.o      \
		mpt3sas_transport.o     \
		mpt3sas_ctl.o	\
		mpt3sas_trigger_diag.o \
		mpt3sas_warpdrive.o
