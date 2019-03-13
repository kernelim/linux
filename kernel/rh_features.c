#include <linux/kernel.h>
#include <linux/list.h>
#include <linux/proc_fs.h>
#include <linux/seq_file.h>
#include <linux/slab.h>
#include <linux/spinlock.h>
#include <linux/rh_features.h>

#define RH_FEATURE_NAME_LEN	32

struct rh_feature {
	struct list_head list;
	char name[RH_FEATURE_NAME_LEN];
};

static LIST_HEAD(rh_feature_list);
static DEFINE_SPINLOCK(rh_feature_lock);

bool __rh_mark_used_feature(const char *feature_name)
{
	struct rh_feature *feat, *iter;

	BUG_ON(in_interrupt());
	feat = kzalloc(sizeof(*feat), GFP_KERNEL);
	if (WARN(!feat, "Using feature %s.\n", feature_name))
		return false;
	strlcpy(feat->name, feature_name, RH_FEATURE_NAME_LEN);

	spin_lock(&rh_feature_lock);
	list_for_each_entry_rcu(iter, &rh_feature_list, list) {
		if (!strcmp(iter->name, feature_name)) {
			kfree(feat);
			feat = NULL;
			break;
		}
	}
	if (feat)
		list_add_rcu(&feat->list, &rh_feature_list);
	spin_unlock(&rh_feature_lock);

	if (feat)
		pr_info("Using feature %s.\n", feature_name);
	return true;
}
EXPORT_SYMBOL(__rh_mark_used_feature);

void rh_print_used_features(void)
{
	struct rh_feature *feat;

	/*
	 * This function cannot do any locking, we're oopsing. Traversing
	 * rh_feature_list is okay, though, even without the rcu_read_lock
	 * taken: we never delete from that list and thus don't need the
	 * delayed free. All we need are the smp barriers invoked by the rcu
	 * list manipulation routines.
	 */
	if (list_empty(&rh_feature_list))
		return;
	printk(KERN_DEFAULT "Features:");
	list_for_each_entry_rcu(feat, &rh_feature_list, list) {
		pr_cont(" %s", feat->name);
	}
	pr_cont("\n");
}
EXPORT_SYMBOL(rh_print_used_features);

static int rh_features_show(struct seq_file *seq, void *unused)
{
	struct rh_feature *feat;
	bool space = false;

	if (list_empty(&rh_feature_list))
		return 0;
	rcu_read_lock();
	list_for_each_entry_rcu(feat, &rh_feature_list, list) {
		if (space)
			seq_puts(seq, " ");
		seq_puts(seq, feat->name);
		space = true;
	}
	rcu_read_unlock();
	seq_puts(seq, "\n");
	return 0;
}

static __init int rh_features_init(void)
{
	struct proc_dir_entry *ent;

	ent = proc_create_single("driver/rh_features", 0, NULL, rh_features_show);
	WARN_ON(!ent);
	return 0;
}
subsys_initcall(rh_features_init);
