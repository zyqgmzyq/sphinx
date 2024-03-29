# 开启mmu切换到虚拟地址

```c
__primary_switch:
#ifdef CONFIG_RANDOMIZE_BASE
	/*
	 * 保存x0(开启MMU时需要写入sctlr_el1的值, 保存sctlr_el1的当前值)
	 * 这两条汇编的作用是为了在开启MMU, 内核发现运行地址和链接地址是一致的时候再次关闭
	 * MMU, 然后通过获取设备树的`kaslr-seed`来将内核移动到一个随机地址运行, 当然如果
	 * 设备树没有`kaslr-seed`或者command line指定了`nokaslr`则就不启动kaslr(也就
	 * 不用返回重启MMU, 重新建立页表了)
	 */
	mov	x19, x0			      	// preserve new SCTLR_EL1 value
	mrs	x20, sctlr_el1			// preserve old SCTLR_EL1 value
#endif
	/* 开启MMU */
	bl	__enable_mmu
#ifdef CONFIG_RELOCATABLE
	/* 如果因为kaslr的关系, 目前内核的运行地址和链接地址是不同的, 前面的code能正常运行
	 * 是因为所有的指令和数据都是PIC(代码位置无关)的, 后面的code是不能保证的, 所以需要
	 * 用内核的`.rela`段来修复这个问题
	 */
	bl	__relocate_kernel
#ifdef CONFIG_RANDOMIZE_BASE
	/* 在这里准备swapper的初始化环境, 后面正式跳入C code进行内核初始化, 这个下篇再说 */
	ldr	x8, =__primary_switched
	adrp	x0, __PHYS_OFFSET
	blr	x8

	/*
	 * If we return here, we have a KASLR displacement in x23 which we need
	 * to take into account by discarding the current kernel mapping and
	 * creating a new one.
	 */
	/*
	 * 如果返回到这里表示使用设备树的`kaslr-seed`来启动kaslr, 这里内核已经被重新copy
	 * 到(0xffff_0000_0000_0000 + 128M(module) + kaslr-seed + TEXT_OFFSET的
	 * 位置, 因此内核的页表, 符号都需要重新进行设定. 所以下面的code关闭MMU, 重建页表,
	 * 修复内核符号, 再次跳入__primary_switched
	 */
	pre_disable_mmu_workaround
	msr	sctlr_el1, x20			    // disable the MMU
	isb
	bl	__create_page_tables		// recreate kernel mapping

	tlbi	vmalle1				    // Remove any stale TLB entries
	dsb	nsh

	msr	sctlr_el1, x19			    // re-enable the MMU
	isb
	ic	iallu				        // flush instructions fetched
	dsb	nsh				            // via old mapping
	isb

	bl	__relocate_kernel
#endif
#endif
	ldr	x8, =__primary_switched
	adrp	x0, __PHYS_OFFSET
	br	x8
ENDPROC(__primary_switch)
```

## enable_mmu

先是`__enable_mmu`

```c
ENTRY(__enable_mmu)
	/*
	 * 下面4条代码判断硬件是否实际支持4K页表映射, 如果不支持, 就跳入
	 * `__no_granule_support`, 表明启动失败, CPU调用wfe, wfi进入idle状态
	 */
	mrs	x1, ID_AA64MMFR0_EL1
	ubfx	x2, x1, #ID_AA64MMFR0_TGRAN_SHIFT, 4
	cmp	x2, #ID_AA64MMFR0_TGRAN_SUPPORTED
	b.ne	__no_granule_support
	/* 在`__early_cpu_boot_status`存入0表明CPU状态正常 */
	update_early_cpu_boot_status 0, x1, x2
	/*
	 * 设定TTBR0, TTBR1, TTBR0用于虚拟地址MSB都为0时(在这里对应与物理地址相
	 * 等的虚拟地址)的页表映射, TTBR1用于虚拟地址MSB都为1时(在这里对应与物理地
	 * 址相等的虚拟地址)的页表映射. 在正常状态下TTBR0用于用户空间页表映射,
	 * TTBR1用于内核空间页表映射, 分成两个可以在切换进程时, 内核页表不用做切换
	 */
	adrp	x1, idmap_pg_dir
	adrp	x2, swapper_pg_dir
	msr	ttbr0_el1, x1			// load TTBR0
	msr	ttbr1_el1, x2			// load TTBR1
	/*
	 * 两条isb内存屏障保证中间的指令执行的顺序, isb还需flush cpu的pipe line,
	 * 这样CPU就会在开启MMU之后重新取指令, 可以保证去到的指令的正确性.
	 */
	isb
	msr	sctlr_el1, x0
	isb
	/*
	 * Invalidate the local I-cache so that any instructions fetched
	 * speculatively from the PoC are discarded, since they may have
	 * been dynamically patched at the PoU.
	 */
	/*
	 * iallu = invalidate + all + PoU
	 * 清空左右的icache到PoU保证cpu core的各个模块看到的内容的一致性, dsb nsh
	 * 保证上面的动作在CORE本地(non-sharable)完成. 最后清空CPU pipeline, 返回
	 */
	ic	iallu
	dsb	nsh
	isb
	ret
ENDPROC(__enable_mmu)
```

## relocate kernel

然后是`___relocate_kernel`

```c
__relocate_kernel:
	/*
	 * Iterate over each entry in the relocation table, and apply the
	 * relocations in place.
	 */
	ldr	w9, =__rela_offset		// offset to reloc table
	ldr	w10, =__rela_size		// size of reloc table

	mov_q	x11, KIMAGE_VADDR   // default virtual offset
	add	x11, x11, x23			// actual virtual offset
	add	x9, x9, x11			    // __va(.rela)
	add	x10, x9, x10			// __va(.rela) + sizeof(.rela)

0:	cmp	x9, x10
	b.hs	1f
	ldp	x11, x12, [x9], #24
	ldr	x13, [x9, #-8]
	cmp	w12, #R_AARCH64_RELATIVE
	b.ne	0b
	add	x13, x13, x23			// relocate
	str	x13, [x11, x23]
	b	0b
1:	ret
ENDPROC(__relocate_kernel)
```

`__rela_offset`定义在链接文件中, 如下:

```c
.rela : ALIGN(8) {
		*(.rela .rela*)
	}

	__rela_offset	= ABSOLUTE(ADDR(.rela) - KIMAGE_VADDR);
	__rela_size	= SIZEOF(.rela);
```

可以看出`__rela_offset`是`.rela`段相对KERNEL起始地址的偏移. `__rela_size`是`.rela`段的偏移.
通过对汇编代码的阅读, 我们大致可以看出`.rela`段的内容如下:

```c
|     64 bit     |      64 bit     |      64 bit     |     ...
+----------------+-----------------------------------+-----------------
| sym0 link addr | sym0 reloc flag | sym0 link value | sym1 link ...
+----------------+-----------------------------------+-----------------
```

每个relocable symbol有三个entry, 每个entry都是32bit, 分别为link addr, relocation flag, link value. 

对于需要重定位内核运行位置的情况, 我们需要把所有FLAG为R_AARCH64_RELATIVE的的entry指定的symbol进行修正, 修正方法为将link addr + offset的值修改为link value + offset. 

其实这个段的含义就是说在IMAGE中, link addr的位置中存放的值是地址相关地值, 如果IMAGE发生了整体偏移, 那么link addr的位置实际在link addr + offset, 要把实际位置上的value修正, 这样说不知道是不是更清晰一些.
