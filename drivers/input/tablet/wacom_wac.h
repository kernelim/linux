/*
 * drivers/input/tablet/wacom_wac.h
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 */
#ifndef WACOM_WAC_H
#define WACOM_WAC_H

/* maximum packet length for USB devices */
#define WACOM_PKGLEN_MAX	192
#define WACOM_MAX_REMOTES	5
#define WACOM_STATUS_UNKNOWN	255

/* packet length for individual models */
#define WACOM_PKGLEN_PENPRTN	 7
#define WACOM_PKGLEN_GRAPHIRE	 8
#define WACOM_PKGLEN_BBFUN	 9
#define WACOM_PKGLEN_INTUOS	10
#define WACOM_PKGLEN_PENABLED	 8
#define WACOM_PKGLEN_TPC1FG	 5
#define WACOM_PKGLEN_TPC2FG	14
#define WACOM_PKGLEN_BBPEN	10
#define WACOM_PKGLEN_BBTOUCH3	64
#define WACOM_PKGLEN_WIRELESS	32
#define WACOM_PKGLEN_MTOUCH	62

/* wacom data size per MT contact */
#define WACOM_BYTES_PER_MT_PACKET	11
#define WACOM_BYTES_PER_24HDT_PACKET	14
#define WACOM_BYTES_PER_QHDTHID_PACKET	 6

/* device IDs */
#define STYLUS_DEVICE_ID	0x02
#define TOUCH_DEVICE_ID		0x03
#define CURSOR_DEVICE_ID	0x06
#define ERASER_DEVICE_ID	0x0A
#define PAD_DEVICE_ID		0x0F

#define WACOM_REPORT_PENABLED		2
#define WACOM_REPORT_TPCMT		13
#define WACOM_REPORT_24HDT		1
#define WACOM_REPORT_WL			128
#define WACOM_REPORT_CINTIQ		16
#define WACOM_REPORT_CINTIQPAD		17
#define WACOM_REPORT_DEVICE_LIST	16
#define WACOM_REPORT_REMOTE		17

/* device quirks */
#define WACOM_QUIRK_MULTI_INPUT		0x0001
#define WACOM_QUIRK_NO_INPUT		0x0004
#define WACOM_QUIRK_MONITOR		0x0008

enum {
	PENPARTNER = 0,
	GRAPHIRE,
	WACOM_G4,
	PTU,
	PL,
	DTU,
	INTUOS,
	INTUOS3S,
	INTUOS3,
	INTUOS3L,
	INTUOS4S,
	INTUOS4,
	INTUOS4L,
	INTUOS5S,
	INTUOS5,
	INTUOS5L,
	INTUOSPS,
	INTUOSPM,
	INTUOSPL,
	INTUOSHT,
	WACOM_21UX2,
	WACOM_22HD,
	WACOM_24HD,
	WACOM_27QHD,
	CINTIQ,
	WACOM_BEE,
	WACOM_MO,
	WIRELESS,
	BAMBOO_PT,
	WACOM_24HDT,
	WACOM_27QHDT,
	REMOTE,
	TABLETPC,
	TABLETPC2FG,
	MTSCREEN,
	MAX_TYPE
};

struct wacom_features {
	const char *name;
	int pktlen;
	int x_max;
	int y_max;
	int pressure_max;
	int distance_max;
	int type;
	int device_type;
	int x_phy;
	int y_phy;
	unsigned char unit;
	unsigned char unitExpo;
	unsigned quirks;
	unsigned touch_max;
	int oVid;
	int oPid;
	int x_min;
	int y_min;
};

struct wacom_shared {
	bool stylus_in_proximity;
	bool touch_down;
};

struct wacom_wac {
	char name[64];
	unsigned char *data;
	int tool[2];
	int id[2];
	__u32 serial[5];
	struct wacom_features features;
	struct wacom_shared *shared;
	int pid;
	int num_contacts_left;
};

#endif
