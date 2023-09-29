/*******************************************************************************
 * This file contains the iSCSI Virtual Device and Disk Transport
 * agnostic related functions.
 *
 * (c) Copyright 2007-2013 Datera, Inc.
 *
 * Author: Nicholas A. Bellinger <nab@linux-iscsi.org>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 ******************************************************************************/

#include <target/target_core_base.h>
#include <target/target_core_fabric.h>

#include <target/iscsi/iscsi_target_core.h>
#include <target/iscsi/iscsi_transport.h>
#include "iscsi_target_device.h"
#include "iscsi_target_tpg.h"
#include "iscsi_target_util.h"

#define iscsit_needs_delayed_maxcmdsn_increment(conn) \
	(conn->conn_transport->transport_type == ISCSI_INFINIBAND)

void iscsit_determine_maxcmdsn(struct iscsit_session *sess)
{
	struct se_node_acl *se_nacl;

	/*
	 * This is a discovery session, the single queue slot was already
	 * assigned in iscsi_login_zero_tsih().  Since only Logout and
	 * Text Opcodes are allowed during discovery we do not have to worry
	 * about the HBA's queue depth here.
	 */
	if (sess->sess_ops->SessionType)
		return;

	se_nacl = sess->se_sess->se_node_acl;

	/*
	 * This is a normal session, set the Session's CmdSN window to the
	 * struct se_node_acl->queue_depth.  The value in struct se_node_acl->queue_depth
	 * has already been validated as a legal value in
	 * core_set_queue_depth_for_node().
	 */
	sess->cmdsn_window = se_nacl->queue_depth;
	atomic_add(se_nacl->queue_depth - 1, &sess->max_cmd_sn);
}

void __iscsit_increment_maxcmdsn(struct iscsit_cmd *cmd, struct iscsit_session *sess)
{
	u32 max_cmd_sn;

	if (cmd->immediate_cmd || cmd->maxcmdsn_inc)
		return;

	cmd->maxcmdsn_inc = 1;

	max_cmd_sn = atomic_inc_return(&sess->max_cmd_sn);
	pr_debug("Updated MaxCmdSN to 0x%08x\n", max_cmd_sn);
}

void iscsit_increment_maxcmdsn(struct iscsit_cmd *cmd, struct iscsit_session *sess)
{
	if (!iscsit_needs_delayed_maxcmdsn_increment(cmd->conn))
		__iscsit_increment_maxcmdsn(cmd, sess);
}
EXPORT_SYMBOL(iscsit_increment_maxcmdsn);



void iscsit_increment_maxcmdsn_on_release(struct iscsit_cmd *cmd, struct iscsit_session *sess)
{
	if (iscsit_needs_delayed_maxcmdsn_increment(cmd->conn) && !cmd->no_maxcmdsn_release) {
		__iscsit_increment_maxcmdsn(cmd, sess);
		if ((u32)atomic_read(&sess->max_cmd_sn) -
		     READ_ONCE(sess->last_max_cmd_sn)
		     > sess->cmdsn_window / 2) {
			/*
			 * Prevent nopin races if one may be needed by using
			 * a lock and rechecking after grabbing the lock
			 */
			spin_lock_bh(&cmd->conn->nopin_timer_lock);
			if ((u32)atomic_read(&sess->max_cmd_sn) -
			    READ_ONCE(sess->last_max_cmd_sn)
			    > sess->cmdsn_window / 2)
				iscsit_add_nopin(cmd->conn, 0);
			spin_unlock_bh(&cmd->conn->nopin_timer_lock);
		}
	}
}
