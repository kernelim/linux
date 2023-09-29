// SPDX-License-Identifier: GPL-2.0
/**
 * Device connections
 *
 * Copyright (C) 2018 Intel Corporation
 * Author: Heikki Krogerus <heikki.krogerus@linux.intel.com>
 */

#include <linux/device.h>
#include <linux/property.h>

static unsigned int fwnode_graph_devcon_matches(const struct fwnode_handle *fwnode,
						const char *con_id, void *data,
						devcon_match_fn_t match,
						void **matches,
						unsigned int matches_len)
{
	struct fwnode_handle *node;
	struct fwnode_handle *ep;
	unsigned int count = 0;
	void *ret;

	fwnode_graph_for_each_endpoint(fwnode, ep) {
		if (matches && count >= matches_len) {
			fwnode_handle_put(ep);
			break;
		}

		node = fwnode_graph_get_remote_port_parent(ep);
		if (!fwnode_device_is_available(node)) {
			fwnode_handle_put(node);
			continue;
		}

		ret = match(node, con_id, data);
		fwnode_handle_put(node);
		if (ret) {
			if (matches)
				matches[count] = ret;
			count++;
		}
	}
	return count;
}

static unsigned int fwnode_devcon_matches(const struct fwnode_handle *fwnode,
					  const char *con_id, void *data,
					  devcon_match_fn_t match,
					  void **matches,
					  unsigned int matches_len)
{
	struct fwnode_handle *node;
	unsigned int count = 0;
	unsigned int i;
	void *ret;

	for (i = 0; ; i++) {
		if (matches && count >= matches_len)
			break;

		node = fwnode_find_reference(fwnode, con_id, i);
		if (IS_ERR(node))
			break;

		ret = match(node, NULL, data);
		fwnode_handle_put(node);
		if (ret) {
			if (matches)
				matches[count] = ret;
			count++;
		}
	}

	return count;
}

/**
 * fwnode_connection_find_match - Find connection from a device node
 * @fwnode: Device node with the connection
 * @con_id: Identifier for the connection
 * @data: Data for the match function
 * @match: Function to check and convert the connection description
 *
 * Find a connection with unique identifier @con_id between @fwnode and another
 * device node. @match will be used to convert the connection description to
 * data the caller is expecting to be returned.
 */
void *fwnode_connection_find_match(const struct fwnode_handle *fwnode,
				   const char *con_id, void *data,
				   devcon_match_fn_t match)
{
	unsigned int count;
	void *ret;

	if (!fwnode || !match)
		return NULL;

	count = fwnode_graph_devcon_matches(fwnode, con_id, data, match, &ret, 1);
	if (count)
		return ret;

	count = fwnode_devcon_matches(fwnode, con_id, data, match, &ret, 1);
	return count ? ret : NULL;
}
EXPORT_SYMBOL_GPL(fwnode_connection_find_match);

/**
 * fwnode_connection_find_matches - Find connections from a device node
 * @fwnode: Device node with the connection
 * @con_id: Identifier for the connection
 * @data: Data for the match function
 * @match: Function to check and convert the connection description
 * @matches: (Optional) array of pointers to fill with matches
 * @matches_len: Length of @matches
 *
 * Find up to @matches_len connections with unique identifier @con_id between
 * @fwnode and other device nodes. @match will be used to convert the
 * connection description to data the caller is expecting to be returned
 * through the @matches array.
 * If @matches is NULL @matches_len is ignored and the total number of resolved
 * matches is returned.
 *
 * Return: Number of matches resolved, or negative errno.
 */
int fwnode_connection_find_matches(const struct fwnode_handle *fwnode,
				   const char *con_id, void *data,
				   devcon_match_fn_t match,
				   void **matches, unsigned int matches_len)
{
	unsigned int count_graph;
	unsigned int count_ref;

	if (!fwnode || !match)
		return -EINVAL;

	count_graph = fwnode_graph_devcon_matches(fwnode, con_id, data, match,
						  matches, matches_len);

	if (matches) {
		matches += count_graph;
		matches_len -= count_graph;
	}

	count_ref = fwnode_devcon_matches(fwnode, con_id, data, match,
					  matches, matches_len);

	return count_graph + count_ref;
}
EXPORT_SYMBOL_GPL(fwnode_connection_find_matches);

/**
 * device_connection_find_match - Find physical connection to a device
 * @dev: Device with the connection
 * @con_id: Identifier for the connection
 * @data: Data for the match function
 * @match: Function to check and convert the connection description
 *
 * Find a connection with unique identifier @con_id between @dev and another
 * device. @match will be used to convert the connection description to data the
 * caller is expecting to be returned.
 */
void *device_connection_find_match(const struct device *dev, const char *con_id,
				   void *data, devcon_match_fn_t match)
{
	return fwnode_connection_find_match(dev_fwnode(dev), con_id, data, match);
}
EXPORT_SYMBOL_GPL(device_connection_find_match);
