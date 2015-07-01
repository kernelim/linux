/* Nehalem/SandBridge/Haswell uncore support */
#include "perf_event_intel_uncore.h"

/* SNB event control */
#define SNB_UNC_CTL_EV_SEL_MASK			0x000000ff
#define SNB_UNC_CTL_UMASK_MASK			0x0000ff00
#define SNB_UNC_CTL_EDGE_DET			(1 << 18)
#define SNB_UNC_CTL_EN				(1 << 22)
#define SNB_UNC_CTL_INVERT			(1 << 23)
#define SNB_UNC_CTL_CMASK_MASK			0x1f000000
#define NHM_UNC_CTL_CMASK_MASK			0xff000000
#define NHM_UNC_FIXED_CTR_CTL_EN		(1 << 0)

#define SNB_UNC_RAW_EVENT_MASK			(SNB_UNC_CTL_EV_SEL_MASK | \
						 SNB_UNC_CTL_UMASK_MASK | \
						 SNB_UNC_CTL_EDGE_DET | \
						 SNB_UNC_CTL_INVERT | \
						 SNB_UNC_CTL_CMASK_MASK)

#define NHM_UNC_RAW_EVENT_MASK			(SNB_UNC_CTL_EV_SEL_MASK | \
						 SNB_UNC_CTL_UMASK_MASK | \
						 SNB_UNC_CTL_EDGE_DET | \
						 SNB_UNC_CTL_INVERT | \
						 NHM_UNC_CTL_CMASK_MASK)

/* SNB global control register */
#define SNB_UNC_PERF_GLOBAL_CTL                 0x391
#define SNB_UNC_FIXED_CTR_CTRL                  0x394
#define SNB_UNC_FIXED_CTR                       0x395

/* SNB uncore global control */
#define SNB_UNC_GLOBAL_CTL_CORE_ALL             ((1 << 4) - 1)
#define SNB_UNC_GLOBAL_CTL_EN                   (1 << 29)

/* SNB Cbo register */
#define SNB_UNC_CBO_0_PERFEVTSEL0               0x700
#define SNB_UNC_CBO_0_PER_CTR0                  0x706
#define SNB_UNC_CBO_MSR_OFFSET                  0x10

/* NHM global control register */
#define NHM_UNC_PERF_GLOBAL_CTL                 0x391
#define NHM_UNC_FIXED_CTR                       0x394
#define NHM_UNC_FIXED_CTR_CTRL                  0x395

/* NHM uncore global control */
#define NHM_UNC_GLOBAL_CTL_EN_PC_ALL            ((1ULL << 8) - 1)
#define NHM_UNC_GLOBAL_CTL_EN_FC                (1ULL << 32)

/* NHM uncore register */
#define NHM_UNC_PERFEVTSEL0                     0x3c0
#define NHM_UNC_UNCORE_PMC0                     0x3b0

DEFINE_UNCORE_FORMAT_ATTR(event, event, "config:0-7");
DEFINE_UNCORE_FORMAT_ATTR(umask, umask, "config:8-15");
DEFINE_UNCORE_FORMAT_ATTR(edge, edge, "config:18");
DEFINE_UNCORE_FORMAT_ATTR(inv, inv, "config:23");
DEFINE_UNCORE_FORMAT_ATTR(cmask5, cmask, "config:24-28");
DEFINE_UNCORE_FORMAT_ATTR(cmask8, cmask, "config:24-31");

/* Sandy Bridge uncore support */
static void snb_uncore_msr_enable_event(struct intel_uncore_box *box, struct perf_event *event)
{
	struct hw_perf_event *hwc = &event->hw;

	if (hwc->idx < UNCORE_PMC_IDX_FIXED)
		wrmsrl(hwc->config_base, hwc->config | SNB_UNC_CTL_EN);
	else
		wrmsrl(hwc->config_base, SNB_UNC_CTL_EN);
}

static void snb_uncore_msr_disable_event(struct intel_uncore_box *box, struct perf_event *event)
{
	wrmsrl(event->hw.config_base, 0);
}

static void snb_uncore_msr_init_box(struct intel_uncore_box *box)
{
	if (box->pmu->pmu_idx == 0) {
		wrmsrl(SNB_UNC_PERF_GLOBAL_CTL,
			SNB_UNC_GLOBAL_CTL_EN | SNB_UNC_GLOBAL_CTL_CORE_ALL);
	}
}

static struct uncore_event_desc snb_uncore_events[] = {
	INTEL_UNCORE_EVENT_DESC(clockticks, "event=0xff,umask=0x00"),
	{ /* end: all zeroes */ },
};

static struct attribute *snb_uncore_formats_attr[] = {
	&format_attr_event.attr,
	&format_attr_umask.attr,
	&format_attr_edge.attr,
	&format_attr_inv.attr,
	&format_attr_cmask5.attr,
	NULL,
};

static struct attribute_group snb_uncore_format_group = {
	.name		= "format",
	.attrs		= snb_uncore_formats_attr,
};

static struct intel_uncore_ops snb_uncore_msr_ops = {
	.init_box	= snb_uncore_msr_init_box,
	.disable_event	= snb_uncore_msr_disable_event,
	.enable_event	= snb_uncore_msr_enable_event,
	.read_counter	= uncore_msr_read_counter,
};

static struct event_constraint snb_uncore_cbox_constraints[] = {
	UNCORE_EVENT_CONSTRAINT(0x80, 0x1),
	UNCORE_EVENT_CONSTRAINT(0x83, 0x1),
	EVENT_CONSTRAINT_END
};

static struct intel_uncore_type snb_uncore_cbox = {
	.name		= "cbox",
	.num_counters   = 2,
	.num_boxes	= 4,
	.perf_ctr_bits	= 44,
	.fixed_ctr_bits	= 48,
	.perf_ctr	= SNB_UNC_CBO_0_PER_CTR0,
	.event_ctl	= SNB_UNC_CBO_0_PERFEVTSEL0,
	.fixed_ctr	= SNB_UNC_FIXED_CTR,
	.fixed_ctl	= SNB_UNC_FIXED_CTR_CTRL,
	.single_fixed	= 1,
	.event_mask	= SNB_UNC_RAW_EVENT_MASK,
	.msr_offset	= SNB_UNC_CBO_MSR_OFFSET,
	.constraints	= snb_uncore_cbox_constraints,
	.ops		= &snb_uncore_msr_ops,
	.format_group	= &snb_uncore_format_group,
	.event_descs	= snb_uncore_events,
};

static struct intel_uncore_type *snb_msr_uncores[] = {
	&snb_uncore_cbox,
	NULL,
};

void snb_uncore_cpu_init(void)
{
	uncore_msr_uncores = snb_msr_uncores;
	if (snb_uncore_cbox.num_boxes > boot_cpu_data.x86_max_cores)
		snb_uncore_cbox.num_boxes = boot_cpu_data.x86_max_cores;
}

/* Nehalem uncore support */
static void nhm_uncore_msr_disable_box(struct intel_uncore_box *box)
{
	wrmsrl(NHM_UNC_PERF_GLOBAL_CTL, 0);
}

static void nhm_uncore_msr_enable_box(struct intel_uncore_box *box)
{
	wrmsrl(NHM_UNC_PERF_GLOBAL_CTL, NHM_UNC_GLOBAL_CTL_EN_PC_ALL | NHM_UNC_GLOBAL_CTL_EN_FC);
}

static void nhm_uncore_msr_enable_event(struct intel_uncore_box *box, struct perf_event *event)
{
	struct hw_perf_event *hwc = &event->hw;

	if (hwc->idx < UNCORE_PMC_IDX_FIXED)
		wrmsrl(hwc->config_base, hwc->config | SNB_UNC_CTL_EN);
	else
		wrmsrl(hwc->config_base, NHM_UNC_FIXED_CTR_CTL_EN);
}

static struct attribute *nhm_uncore_formats_attr[] = {
	&format_attr_event.attr,
	&format_attr_umask.attr,
	&format_attr_edge.attr,
	&format_attr_inv.attr,
	&format_attr_cmask8.attr,
	NULL,
};

static struct attribute_group nhm_uncore_format_group = {
	.name = "format",
	.attrs = nhm_uncore_formats_attr,
};

static struct uncore_event_desc nhm_uncore_events[] = {
	INTEL_UNCORE_EVENT_DESC(clockticks,                "event=0xff,umask=0x00"),
	INTEL_UNCORE_EVENT_DESC(qmc_writes_full_any,       "event=0x2f,umask=0x0f"),
	INTEL_UNCORE_EVENT_DESC(qmc_normal_reads_any,      "event=0x2c,umask=0x0f"),
	INTEL_UNCORE_EVENT_DESC(qhl_request_ioh_reads,     "event=0x20,umask=0x01"),
	INTEL_UNCORE_EVENT_DESC(qhl_request_ioh_writes,    "event=0x20,umask=0x02"),
	INTEL_UNCORE_EVENT_DESC(qhl_request_remote_reads,  "event=0x20,umask=0x04"),
	INTEL_UNCORE_EVENT_DESC(qhl_request_remote_writes, "event=0x20,umask=0x08"),
	INTEL_UNCORE_EVENT_DESC(qhl_request_local_reads,   "event=0x20,umask=0x10"),
	INTEL_UNCORE_EVENT_DESC(qhl_request_local_writes,  "event=0x20,umask=0x20"),
	{ /* end: all zeroes */ },
};

static struct intel_uncore_ops nhm_uncore_msr_ops = {
	.disable_box	= nhm_uncore_msr_disable_box,
	.enable_box	= nhm_uncore_msr_enable_box,
	.disable_event	= snb_uncore_msr_disable_event,
	.enable_event	= nhm_uncore_msr_enable_event,
	.read_counter	= uncore_msr_read_counter,
};

static struct intel_uncore_type nhm_uncore = {
	.name		= "",
	.num_counters   = 8,
	.num_boxes	= 1,
	.perf_ctr_bits	= 48,
	.fixed_ctr_bits	= 48,
	.event_ctl	= NHM_UNC_PERFEVTSEL0,
	.perf_ctr	= NHM_UNC_UNCORE_PMC0,
	.fixed_ctr	= NHM_UNC_FIXED_CTR,
	.fixed_ctl	= NHM_UNC_FIXED_CTR_CTRL,
	.event_mask	= NHM_UNC_RAW_EVENT_MASK,
	.event_descs	= nhm_uncore_events,
	.ops		= &nhm_uncore_msr_ops,
	.format_group	= &nhm_uncore_format_group,
};

static struct intel_uncore_type *nhm_msr_uncores[] = {
	&nhm_uncore,
	NULL,
};

void nhm_uncore_cpu_init(void)
{
	uncore_msr_uncores = nhm_msr_uncores;
}

/* end of Nehalem uncore support */
