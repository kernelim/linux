/*
 *  lzodefs.h -- architecture, OS and compiler specific defines
 *
 *  Copyright (C) 1996-2012 Markus F.X.J. Oberhumer <markus@oberhumer.com>
 *
 *  The full LZO package can be found at:
 *  http://www.oberhumer.com/opensource/lzo/
 *
 *  Changed for Linux kernel use by:
 *  Nitin Gupta <nitingupta910@gmail.com>
 *  Richard Purdie <rpurdie@openedhand.com>
 */


#define COPY4(dst, src)	\
		put_unaligned(get_unaligned((const u32 *)(src)), (u32 *)(dst))
#if defined(__x86_64__)
#define COPY8(dst, src)	\
		put_unaligned(get_unaligned((const u64 *)(src)), (u64 *)(dst))
#else
#define COPY8(dst, src)	\
		COPY4(dst, src); COPY4((dst) + 4, (src) + 4)
#endif

#define M1_MAX_OFFSET	0x0400
#define M2_MAX_OFFSET	0x0800
#define M3_MAX_OFFSET	0x4000
#define M4_MAX_OFFSET	0xbfff

#define M1_MIN_LEN	2
#define M1_MAX_LEN	2
#define M2_MIN_LEN	3
#define M2_MAX_LEN	8
#define M3_MIN_LEN	3
#define M3_MAX_LEN	33
#define M4_MIN_LEN	3
#define M4_MAX_LEN	9

#define M1_MARKER	0
#define M2_MARKER	64
#define M3_MARKER	32
#define M4_MARKER	16

#define D_BITS		14
#define D_MASK		((1u << D_BITS) - 1)
#define D_HIGH		((D_MASK >> 1) + 1)

#define DX2(p, s1, s2)	(((((size_t)((p)[2]) << (s2)) ^ (p)[1]) \
							<< (s1)) ^ (p)[0])
#define DX3(p, s1, s2, s3)	((DX2((p)+1, s2, s3) << (s1)) ^ (p)[0])
