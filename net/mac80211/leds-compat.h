#ifndef LEDS_COMPAT_H
#define LEDS_COMPAT_H

#include <linux/version.h>

#include "leds-compat.h"
#include <linux/leds.h>

extern void led_blink_set(struct led_classdev *led_cdev,
			  unsigned long *delay_on,
			  unsigned long *delay_off);

#define led_classdev_unregister compat_led_classdev_unregister
extern void compat_led_classdev_unregister(struct led_classdev *led_cdev);

#define led_brightness_set compat_led_brightness_set
extern void compat_led_brightness_set(struct led_classdev *led_cdev,
				      enum led_brightness brightness);

#endif /* LEDS_COMPAT_H */
