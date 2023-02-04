# 内核虚拟空间地址段运行

相信一些细心的读者有注意到, 到目前位置, 内核仍然在低地址段运行, 虽然我们已经启动了MMU, 但是仍然运行在等于物理地址的虚拟地址上, 下面我们就要正式的切换到内核态的高地址空间来运行.

```c
ldr	x8, =__primary_switched
adrp	x0, __PHYS_OFFSET
blr	x8
```

这段code是上篇遗留的一点内容, 现在来进行分析. 第一条指令是arm的伪指令, 将`__primary_switched`标签的链接地址放在x8中, 第二条将`__PHYS_OFFSET`对应的运行时地址存在在x0中, `__PHYS_OFFSET`虽然名字有PHYS, 但是实际他是指`_text - TEXT_OFFSET`的链接地址. 它等于0xffff_0000_0000_0000 + 128M(module) + kaslr, 那现在x0存放的应该就是 DDR起始地址 + 2M align预留内存 + kaslr, 然后跳转到x8执行

这里有一点需要注意, 第一条指令加载的是链接地址, 我们现在放置的位置和链接地址是有kaslr的偏移的, 他是如何跳对的呢?

第一条指令实际上变汇编成一条指令加一个内存池, 如:

```c
	ldr x8 __priary_switched_addr
__priary_switched_addr:
	0xffff_xxxx_xxxx_xxxx(也就是__primary_switched的链接地址)
```

这个内存池实际上就会导致上一篇内容讲的`.rela`段增加3条内容. 因此在上篇的relocate运行时, 这个地址就已经被修正了. 自然就能跳转到正确的位置了.

来看看`__primary_switched`的内容(特别注意, 从跳转发生开始, 内核就开始运行到高的虚拟地址上了):

```c
__primary_switched:
	/*
	 * 把current SP指到`init_thread_union`的最高位置(ARM64和thread_info和
	 * stack不共用, thread_info放在task_strcut里面, init_thread_union只是用
	 * 于内核堆栈)
	 */
	adrp	x4, init_thread_union
	add	sp, x4, #THREAD_SIZE
	/*
	 * 把EL0的sp放在init_task下面, 原因不明, 暂时放着, 目前看起来kernel好像
	 * 有把sp_el0设定在task_struct下面, 这样current实现起来会很容易直接把
	 * sp_el0类型转换一下就能返回进程的task_struct, 另外把thread_info也放在
	 * task_struct的第一个元素, 这个current_thread_info()也就是将current直接
	 * 强制类型转换一下就OK.
	 */
	adr_l	x5, init_task
	msr	sp_el0, x5			// Save thread_info

	/* 初始化内核的异常向量表, 关于向量表的内容后续还会在分析 */
	adr_l	x8, vectors			// load VBAR_EL1 with virtual
	msr	vbar_el1, x8			// vector table address
	isb

	/*
	 * 这一段code就是满足AARCH64 PCS(AArch64 Procedure Call Standard)来写的,
	 * PCS规定x29是FP寄存器, x30是lr寄存器, 在函数被调用时, 首先将fp和lr压
	 * 栈, 然后将sp保存在fp寄存器中. 这里就是完成了这样一个过程, 从而如果调
	 * 用了C code(kaslr就可能会调用设备树相关的C code), C code返回时, 能正确
	 * 的恢复sp, 从而我们也还能正常的返回到前面的`__primary_switch`函数中去,
	 * 由于这里fp没有的, 因此用xzr代替了
	 */
	stp	xzr, x30, [sp, #-16]!
	mov	x29, sp

	/* 把设备树的物理地址存到`__fdt_pointer`中. */
	str_l	x21, __fdt_pointer, x5		// Save FDT pointer

	/*
	 * kimage_vaddr就是`.quad		_text - TEXT_OFFSET`, 这个值已经
	 * 被relocate修正了kaslr, 所以就是内核目前起始虚拟地址-TEXT_OFFSET,
	 * 也就是0xffff_0000_0000_0000 + 128M(module) + kaslr,
	 * 减掉x0之后就是内核虚拟地址和当前所在的物理地址的offset, 将其存放在
	 * kimage_voffset中.
	 */
	ldr_l	x4, kimage_vaddr		// Save the offset between
	sub	x4, x4, x0			        // the kernel virtual and
	str_l	x4, kimage_voffset, x5	// physical mappings

	// Clear BSS
	adr_l	x0, __bss_start
	mov	x1, xzr
	adr_l	x2, __bss_stop
	sub	x2, x2, x0
	/* 这里的`__pi_memset`定义在哪里还没搞清楚 */
	bl	__pi_memset
	dsb	ishst				// Make zero page visible to PTW

#ifdef CONFIG_KASAN
	/* KASAN是一个中调试技术, 用来标记内存, 没细致研究 */
	bl	kasan_early_init
#endif
#ifdef CONFIG_RANDOMIZE_BASE
	/*
	 * 在第4篇文章中, 我们说到x23保存的是KASLR区域的大小. 如果这里判断如果
	 * x23为0, 那么表示内核没有被放在一个随机地址, 也就是前面说的第二种kaslr
	 * 启动方式没有被 使用, 那么将调用C code `kaslr_early_init`来获取
	 * `kaslr-seed`并搬运内核之后返回`__primary_switch`继续执行 关闭MMU
	 * relocate 开启MMU, 再调过来的过程, 就不细说了
	 */
	tst	x23, ~(MIN_KIMG_ALIGN - 1)	// already running randomized?
	b.ne	0f
	mov	x0, x21				    // pass FDT address in x0
	bl	kaslr_early_init		// parse FDT for KASLR options
	cbz	x0, 0f				    // KASLR disabled? just proceed
	orr	x23, x23, x0			// record KASLR offset
	ldp	x29, x30, [sp], #16		// we must enable KASLR, return
	ret					        // to __primary_switch()
0:
#endif
	/*
	 * 这里对sp出栈(增加sp)的上面的出栈只有一个会运行, 要么出栈返回, 要么在
	 * 这里假装出栈, 最后调用`start_kernel`, 由于此处`start_kernel`不会返回,
	 * 我们也无须返回, 所以可以把lr和fp的内容直接抹掉了.
	 */
	add	sp, sp, #16
	mov	x29, #0
	mov	x30, #0
	/* 欢快的进入`start_kernel` C code取执行KERNEL初始化了. */
	b	start_kernel
ENDPROC(__primary_switched)
```

以上就是arm64 linux启动过程的汇编部分的分析

