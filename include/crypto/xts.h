/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _CRYPTO_XTS_H
#define _CRYPTO_XTS_H

#include <crypto/b128ops.h>
#include <crypto/internal/skcipher.h>
#include <linux/fips.h>

#define XTS_BLOCK_SIZE 16

#define XTS_TWEAK_CAST(x) ((void (*)(void *, u8*, const u8*))(x))

static inline int xts_check_key(struct crypto_tfm *tfm,
				const u8 *key, unsigned int keylen)
{
	/*
	 * key consists of keys of equal size concatenated, therefore
	 * the length must be even.
	 */
	if (keylen % 2) {
		crypto_tfm_set_flags(tfm, CRYPTO_TFM_RES_BAD_KEY_LEN);
		return -EINVAL;
	}

	/*
	 * In FIPS mode only a combined key length of either 256 or
	 * 512 bits is allowed, c.f. FIPS 140-3 IG C.I.
	 */
	if (fips_enabled && keylen != 32 && keylen != 64) {
		crypto_tfm_set_flags(tfm, CRYPTO_TFM_RES_BAD_KEY_LEN);
		return -EINVAL;
	}

	/*
	 * Ensure that the AES and tweak key are not identical when
	 * in FIPS mode or the CRYPTO_TFM_REQ_WEAK_KEY flag is set.
	 */
	if ((fips_enabled || (crypto_tfm_get_flags(tfm) &
			      CRYPTO_TFM_REQ_WEAK_KEY)) &&
	    !crypto_memneq(key, key + (keylen / 2), keylen / 2)) {
		crypto_tfm_set_flags(tfm, CRYPTO_TFM_RES_WEAK_KEY);
		return -EINVAL;
	}

	return 0;
}

static inline int xts_verify_key(struct crypto_skcipher *tfm,
				 const u8 *key, unsigned int keylen)
{
	return xts_check_key(crypto_skcipher_tfm(tfm), key, keylen);
}

#endif  /* _CRYPTO_XTS_H */
