# memory init

参考： https://www.cnblogs.com/LoyenWang/p/11440957.html

简单来说，`Fixed map`指的是虚拟地址中的一段区域，在该区域中所有的线性地址是在编译阶段就确定好的，这些虚拟地址需要在`boot`阶段去映射到物理地址上。
来张图片看看虚拟地址空间：
![img](https://img2018.cnblogs.com/blog/1771657/201908/1771657-20190831230820193-922578847.png)

图中`fixed: 0xffffffbefe7fd000 - 0xffffffbefec00000`，描述的就是`Fixed map`的区域。

那么这段区域中的详细一点的布局是怎样呢？看看`arch/arm64/include/asm/fixmap.h`中的`enum fixed_address`结构就清晰了，图来了：
![img](https://img2018.cnblogs.com/blog/1771657/201908/1771657-20190831230833457-192209033.png)

从图中可以看出，如果要访问`DTB`所在的物理地址，那么需要将该物理地址映射到`Fixed map`中的区域，然后访问该区域中的虚拟地址即可。访问`IO`空间也是一样的道理，下文也会讲述到。

那么来看看`early_fixmap_init`函数的关键代码吧：

```c
void __init early_fixmap_init(void)
{
	pgd_t *pgd;
	pud_t *pud;
	pmd_t *pmd;
	unsigned long addr = FIXADDR_START;              /* (1) */

	pgd = pgd_offset_k(addr);                        /* (2) */
	if (CONFIG_PGTABLE_LEVELS > 3 &&
	    !(pgd_none(*pgd) || pgd_page_paddr(*pgd) == __pa_symbol(bm_pud))) {
		/*
		 * We only end up here if the kernel mapping and the fixmap
		 * share the top level pgd entry, which should only happen on
		 * 16k/4 levels configurations.
		 */
		BUG_ON(!IS_ENABLED(CONFIG_ARM64_16K_PAGES));
		pud = pud_offset_kimg(pgd, addr);
	} else {
		if (pgd_none(*pgd))
			__pgd_populate(pgd, __pa_symbol(bm_pud), PUD_TYPE_TABLE);          /* (3) */
		pud = fixmap_pud(addr);
	}
	if (pud_none(*pud))
		__pud_populate(pud, __pa_symbol(bm_pmd), PMD_TYPE_TABLE);    /* (4) */
	pmd = fixmap_pmd(addr);
	__pmd_populate(pmd, __pa_symbol(bm_pte), PMD_TYPE_TABLE);        /* (5) */
......
}
```

关键点：

1. `FIXADDR_START`，定义了`Fixed map`区域的起始地址，位于`arch/arm64/include/asm/fixmap.h`中；
2. `pgd_offset_k(addr)`，获取`addr`地址对应pgd全局页表中的`entry`，而这个pgd全局页表正是`swapper_pg_dir`全局页表；
3. 将`bm_pud`的物理地址写到pgd全局页目录表中；
4. 将`bm_pmd`的物理地址写到pud页目录表中；
5. 将`bm_pte`的物理地址写到pmd页表目录表中；

`bm_pud/bm_pmd/bm_pte`是三个全局数组，相当于是中间的页表，存放各级页表的`entry`，定义如下：

```c
static pte_t bm_pte[PTRS_PER_PTE] __page_aligned_bss;
static pmd_t bm_pmd[PTRS_PER_PMD] __page_aligned_bss __maybe_unused;
static pud_t bm_pud[PTRS_PER_PUD] __page_aligned_bss __maybe_unused;
```

事实上，`early_fixmap_init`只是建立了一个映射的框架，具体的物理地址和虚拟地址的映射没有去填充，这个是由使用者具体在使用时再去填充对应的`pte entry`。比如像`fixmap_remap_fdt()`函数，就是典型的填充`pte entry`的过程，完成最后的一步映射，然后才能读取`dtb`文件。

来一张图片就懂了，是透彻的懂了：
![img](https://img2018.cnblogs.com/blog/1771657/201908/1771657-20190831230908465-1716112257.png)

# early_ioremap_init

如果在boot早期需要操作`IO设备`的话，那么

如果在boot早期需要操作`IO设备`的话，那么`ioremap`就用上场了，由于跟实际的内存管理关系不太大，不再太深入的分析。
![img](https://img2018.cnblogs.com/blog/1771657/201908/1771657-20190831230921079-800174381.png)

简单来说，`ioremap`的空间为`7 * 256K`的区域，保存在`slot_vir[]`数组中，当需要进行IO操作的时候，最终会调用到`__early_ioremap`函数，在该函数中去填充对应的`pte entry`，从而完成最终的虚拟地址和物理地址的映射。

# 4. memblock

上文讲的内容都只是铺垫，为了能正确访问`DTB`文件并且解析得到物理地址信息。从入口到最终添加的调用过程如下图：
![img](https://img2018.cnblogs.com/blog/1771657/201908/1771657-20190831230939571-1284272879.png)

所以，这个章节的重点就是`memblock`模块，这个是早期的内存分配管理器，我不禁想起了之前在`Nuttx`中的内存池实现了，细节已然不太清晰了，但是框架性的思维都大同小异。

## 4.1 结构体

![img](https://img2018.cnblogs.com/blog/1771657/201908/1771657-20190831230951533-1144378625.png)

总共由三个数据结构来描述：

- `struct memblock`定义了一个全局变量，用来维护所有的物理内存；
- `struct memblock_type`代表系统中的内存类型，包括实际使用的内存和保留的内存；
- `struct memblock_region`用来描述具体的内存区域，包含在`struct memblock_type`中的`regions`数组中，最多可以存放128个。

直接上个代码吧：

```c
static struct memblock_region memblock_memory_init_regions[INIT_MEMBLOCK_REGIONS] __initdata_memblock;
static struct memblock_region memblock_reserved_init_regions[INIT_MEMBLOCK_REGIONS] __initdata_memblock;
#ifdef CONFIG_HAVE_MEMBLOCK_PHYS_MAP
static struct memblock_region memblock_physmem_init_regions[INIT_PHYSMEM_REGIONS] __initdata_memblock;
#endif

struct memblock memblock __initdata_memblock = {
	.memory.regions		= memblock_memory_init_regions,
	.memory.cnt		= 1,	/* empty dummy entry */
	.memory.max		= INIT_MEMBLOCK_REGIONS,
	.memory.name		= "memory",

	.reserved.regions	= memblock_reserved_init_regions,
	.reserved.cnt		= 1,	/* empty dummy entry */
	.reserved.max		= INIT_MEMBLOCK_REGIONS,
	.reserved.name		= "reserved",

#ifdef CONFIG_HAVE_MEMBLOCK_PHYS_MAP
	.physmem.regions	= memblock_physmem_init_regions,
	.physmem.cnt		= 1,	/* empty dummy entry */
	.physmem.max		= INIT_PHYSMEM_REGIONS,
	.physmem.name		= "physmem",
#endif

	.bottom_up		= false,
	.current_limit		= MEMBLOCK_ALLOC_ANYWHERE,
};
```

定义的`memblock`为全局变量，在定义的时候就进行了初始化。初始化的时候，`regions`指向的也是静态全局的数组，其中数组的大小为`INIT_MEMBLOCK_REGIONS`，也就是128个，限制了这些内存块的个数了，实际在代码中可以看到，当超过这个数值时，数组会以2倍的速度动态扩大。

初始化完了后，大体是这个样子的：
![img](https://img2018.cnblogs.com/blog/1771657/201908/1771657-20190831231009959-359564492.png)

## 4.2 memblock_add/memblock_remove

`memblock`子模块，基本的逻辑都是围绕内存的添加和移除操作来展开，最终是通过调用`memblock_add_range/memblock_remove_range`来实现的。

- `memblock_add_range`：
  ![img](https://img2018.cnblogs.com/blog/1771657/201908/1771657-20190831231022912-53426271.png)

图中的左侧是函数的执行流程图，执行效果是右侧部分。右侧部分画的是一个典型的情况，实际的情况可能有多种，但是核心的逻辑都是对插入的`region`进行判断，如果出现了物理地址范围重叠的部分，那就进行`split`操作，最终对具有相同`flag`的`region`进行`merge`操作。

- `memblock_remove_range`
  该函数执行的一个典型case效果如下图所示：
  ![img](https://img2018.cnblogs.com/blog/1771657/201908/1771657-20190831231035612-804455093.png)

假如现在需要移除掉一片区域，而该区域跨越了多个`region`，则会先调用`memblock_isolate_range`来对这片区域进行切分，最后再调用`memblock_remove_region`对区域范围内的`region`进行移除操作。

当调用`memblock_alloc`函数进行地址分配时，最后也是调用`memblock_add_range`来实现的，申请的这部分内存最终会添加到`reserved`类型中，**毕竟已经分配出去了**，其他人也不应该使用了。

## 5. arm64_memblock_init

当物理内存都添加进系统之后，`arm64_memblock_init`会对整个物理内存进行整理，主要的工作就是将一些特殊的区域添加进`reserved`内存中。函数执行完后，如下图所示：
![img](https://img2018.cnblogs.com/blog/1771657/201908/1771657-20190831231053115-543452290.png)

- 其中浅绿色的框表示的都是保留的内存区域， 剩下的部分就是可以实际去使用的内存了。

物理内存大体面貌就有了，后续就需要进行内存的页表映射，完成实际的物理地址到虚拟地址的映射了。