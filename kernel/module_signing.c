/* Module signature checker
 *
 * Copyright (C) 2012 Red Hat, Inc. All Rights Reserved.
 * Written by David Howells (dhowells@redhat.com)
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public Licence
 * as published by the Free Software Foundation; either version
 * 2 of the Licence, or (at your option) any later version.
 */

#include <linux/kernel.h>
#include <linux/errno.h>
#include <linux/module.h>
#include <linux/module_signature.h>
#include <linux/string.h>
#include <linux/verification.h>
#include <crypto/public_key.h>
#include "module-internal.h"

/*
 * Verify the signature on a module.
 */
int mod_verify_sig(const void *mod, struct load_info *info)
{
	struct module_signature ms;
	size_t sig_len, modlen = info->len;
	int err;
	int ret;

	pr_devel("==>%s(,%zu)\n", __func__, modlen);

	if (modlen <= sizeof(ms))
		return -EBADMSG;

	memcpy(&ms, mod + (modlen - sizeof(ms)), sizeof(ms));

	ret = mod_check_sig(&ms, modlen, info->name);
	if (ret)
		return ret;

	sig_len = be32_to_cpu(ms.sig_len);
	modlen -= sig_len + sizeof(ms);
	info->len = modlen;

	/*
	 * Check signature using built-in trusted keys and, if configured,
	 * secondary trusted keys.
	 */
	err =  verify_pkcs7_signature(mod, modlen, mod + modlen, sig_len,
				      VERIFY_USE_SECONDARY_KEYRING,
				      VERIFYING_MODULE_SIGNATURE,
				      NULL, NULL);
	if (IS_ENABLED(CONFIG_INTEGRITY_PLATFORM_KEYRING) && err) {
		/*
		 * Check signature using platform trusted keys. This does
		 * not consider the built-in keys, so must be done separately
		 * from above, if possible and necessary.
		 */
		err =  verify_pkcs7_signature(mod, modlen, mod + modlen,
					      sig_len,
					      VERIFY_USE_PLATFORM_KEYRING,
					      VERIFYING_MODULE_SIGNATURE,
					      NULL, NULL);
	}
	return err;
}
