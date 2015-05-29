#include <linux/skbuff.h>
#include <linux/netdevice.h>
#include <linux/if_vlan.h>
#include <linux/netpoll.h>
#include "vlan.h"

bool vlan_do_receive(struct sk_buff **skbp)
{
	struct sk_buff *skb = *skbp;
	u16 vlan_id = vlan_tx_tag_get_id(skb);
	struct net_device *vlan_dev;
	struct vlan_pcpu_stats *rx_stats;

	vlan_dev = vlan_find_dev(skb->dev, vlan_id);
	if (!vlan_dev)
		return false;

	skb = *skbp = skb_share_check(skb, GFP_ATOMIC);
	if (unlikely(!skb))
		return false;

	skb->dev = vlan_dev;
	if (skb->pkt_type == PACKET_OTHERHOST) {
		/* Our lower layer thinks this is not local, let's make sure.
		 * This allows the VLAN to have a different MAC than the
		 * underlying device, and still route correctly. */
		if (!compare_ether_addr(eth_hdr(skb)->h_dest,
					vlan_dev->dev_addr))
			skb->pkt_type = PACKET_HOST;
	}

	if (!(vlan_dev_info(vlan_dev)->flags & VLAN_FLAG_REORDER_HDR)) {
		unsigned int offset = skb->data - skb_mac_header(skb);

		/*
		 * vlan_insert_tag expect skb->data pointing to mac header.
		 * So change skb->data before calling it and change back to
		 * original position later
		 */
		skb_push(skb, offset);
		skb = *skbp = vlan_insert_tag(skb, skb->vlan_tci);
		if (!skb)
			return false;
		skb_pull(skb, offset + VLAN_HLEN);
		skb_reset_mac_len(skb);
	}

	skb->priority = vlan_get_ingress_priority(vlan_dev, skb->vlan_tci);
	skb->vlan_tci = 0;

	rx_stats = this_cpu_ptr(vlan_dev_info(vlan_dev)->vlan_pcpu_stats);

	u64_stats_update_begin(&rx_stats->syncp);
	rx_stats->rx_packets++;
	rx_stats->rx_bytes += skb->len;
	if (skb->pkt_type == PACKET_MULTICAST)
		rx_stats->rx_multicast++;
	u64_stats_update_end(&rx_stats->syncp);
	return true;
}

/* VLAN rx hw acceleration helper.  This acts like netif_{rx,receive_skb}(). */
int __vlan_hwaccel_rx(struct sk_buff *skb, struct vlan_group *grp,
		      u16 vlan_tci, int polling)
{
	__vlan_hwaccel_put_tag(skb, vlan_tci);
	return polling ? netif_receive_skb(skb) : netif_rx(skb);
}
EXPORT_SYMBOL(__vlan_hwaccel_rx);

struct net_device *vlan_dev_real_dev(const struct net_device *dev)
{
	return vlan_dev_info(dev)->real_dev;
}
EXPORT_SYMBOL(vlan_dev_real_dev);

u16 vlan_dev_vlan_id(const struct net_device *dev)
{
	return vlan_dev_info(dev)->vlan_id;
}
EXPORT_SYMBOL(vlan_dev_vlan_id);

static inline gro_result_t __vlan_gro_receive_gr(struct napi_struct *napi,
				                 struct vlan_group *grp,
				                 unsigned int vlan_tci,
						 struct sk_buff *skb)
{
	__vlan_hwaccel_put_tag(skb, vlan_tci);

	return napi_gro_receive_gr(napi, skb);
}

gro_result_t vlan_gro_receive_gr(struct napi_struct *napi,
				 struct vlan_group *grp,
				 unsigned int vlan_tci, struct sk_buff *skb)
{
	return __vlan_gro_receive_gr(napi, grp, vlan_tci, skb);
}
EXPORT_SYMBOL(vlan_gro_receive_gr);

int vlan_gro_receive(struct napi_struct *napi, struct vlan_group *grp,
		     unsigned int vlan_tci, struct sk_buff *skb)
{
	return __vlan_gro_receive_gr(napi, grp, vlan_tci, skb) == GRO_DROP
		? NET_RX_DROP : NET_RX_SUCCESS;
}
EXPORT_SYMBOL(vlan_gro_receive);

static inline gro_result_t __vlan_gro_frags_gr(struct napi_struct *napi,
					       struct vlan_group *grp,
					       unsigned int vlan_tci)
{
	__vlan_hwaccel_put_tag(napi->skb, vlan_tci);
	return napi_gro_frags_gr(napi);
}
gro_result_t vlan_gro_frags_gr(struct napi_struct *napi,
			       struct vlan_group *grp, unsigned int vlan_tci)
{
	return __vlan_gro_frags_gr(napi, grp, vlan_tci);
}
EXPORT_SYMBOL(vlan_gro_frags_gr);

int vlan_gro_frags(struct napi_struct *napi, struct vlan_group *grp,
		   unsigned int vlan_tci)
{
	return __vlan_gro_frags_gr(napi, grp, vlan_tci) == GRO_DROP
		? NET_RX_DROP : NET_RX_SUCCESS;
}
EXPORT_SYMBOL(vlan_gro_frags);
