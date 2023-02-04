接下来进入`__cpu_setup`函数

```c
ENTRY(__cpu_setup)
	/* 清空当前CORE所有的tlb, vm + all + el1, 这条指令需要对non-sharable区域加内存屏障 */
	tlbi	vmalle1				// Invalidate local TLB
	dsb	nsh

	/* 开启CPU的FP/SIMD, debug功能, 关闭PMU等 */
	mov	x0, #3 << 20
	msr	cpacr_el1, x0			// Enable FP/ASIMD
	mov	x0, #1 << 12			// Reset mdscr_el1 and disable
	msr	mdscr_el1, x0			// access to the DCC from EL0
	isb					        // Unmask debug exceptions now,
	enable_dbg				    // since this is per-cpu
	reset_pmuserenr_el0 x0	    // Disable PMU access from EL0
	/*
	 * 上面内容我们说到了, 页表entry表明内存是普通内存, 就是结合这里的初始化来指明的,
	 * PMD_ATTRINDX(MT_NORMAL)是4, 这其实是一个index, 指向MAIR寄存器的[4*8+7:4*8],
	 * MAIR寄存器一共有8组, KERNEL用了6组, 每组有8bit, 每个bit都有相应的含义.
	 * 具体参考手册, 这里就不细说了, 点到为止
	 */
	/*
	 * Memory region attributes for LPAE:
	 *
	 *   n = AttrIndx[2:0]
	 *			n	MAIR
	 *   DEVICE_nGnRnE	000	00000000
	 *   DEVICE_nGnRE	001	00000100
	 *   DEVICE_GRE		010	00001100
	 *   NORMAL_NC		011	01000100
	 *   NORMAL		    100	11111111
	 *   NORMAL_WT		101	10111011
	 */
	ldr	x5, =MAIR(0x00, MT_DEVICE_nGnRnE) | \
		     MAIR(0x04, MT_DEVICE_nGnRE) | \
		     MAIR(0x0c, MT_DEVICE_GRE) | \
		     MAIR(0x44, MT_NORMAL_NC) | \
		     MAIR(0xff, MT_NORMAL) | \
		     MAIR(0xbb, MT_NORMAL_WT)
	msr	mair_el1, x5
	/*
	 * Prepare SCTLR
	 */
	mov_q	x0, SCTLR_EL1_SET
	/*
	 * Set/prepare TCR and TTBR. We use 512GB (39-bit) address range for
	 * both user and kernel.
	 */
	ldr	x10, =TCR_TxSZ(VA_BITS) | TCR_CACHE_FLAGS | TCR_SMP_FLAGS | \
			TCR_TG_FLAGS | TCR_KASLR_FLAGS | TCR_ASID16 | \
			TCR_TBI0 | TCR_A1
	tcr_set_idmap_t0sz	x10, x9

	/*
	 * Set the IPS bits in TCR_EL1.
	 */
	tcr_compute_pa_size x10, #TCR_IPS_SHIFT, x5, x6
#ifdef CONFIG_ARM64_HW_AFDBM
	/*
	 * Enable hardware update of the Access Flags bit.
	 * Hardware dirty bit management is enabled later,
	 * via capabilities.
	 */
	mrs	x9, ID_AA64MMFR1_EL1
	and	x9, x9, #0xf
	cbz	x9, 1f
	orr	x10, x10, #TCR_HA		// hardware Access flag update
1:
#endif	/* CONFIG_ARM64_HW_AFDBM */
	msr	tcr_el1, x10
	ret					// return to head.S
ENDPROC(__cpu_setup)
```

这段汇编代码初始化了CPU的一些寄存器, 如tcr_el1(translation control register)配置虚拟地址的大小, PAGE大小, ASID, share属性, TAG等, 并准备了开启MMU时需要写入sctlr_el1的值

