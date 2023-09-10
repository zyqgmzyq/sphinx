# linux页表映射

为了kernel运行速度加快, 我们需要启动cache, 启动cache需要先启动MMU让CPU运行到虚拟地址上, 那么我们就需要启动一个能覆盖KERNEL内存区域的页表

- idmap_pg_dir是identity mapping使用的页表，也就是物理地址和虚拟地址是相等的，主要是解决打开MMU后，从物理地址转换成虚拟地址，防止MMU开启后，无法获取页表
- swapper_pg_dir是kernel image mapping初始阶段使用的页表，swapper_pg_dir ，Linux内核编译后，kernel image是需要进行映射的，包括text，data等各种。请注意，这里的内存是一段连续内存。也就是说页表（PGD/PUD/PMD）都是连在一起的，地址相差PAGE_SIZE（4k）

## __create_page_tables

在idmap_pg区域为kernel创建恒等映射，在init_pg区域为kernel创建映射，这两块区域都位于vmlinux的data段，执行完__create_page_tables后得到地址映射关系如下：

![在这里插入图片描述](https://img-blog.csdnimg.cn/3ca9f5fc4bd945948854026010c103e5.png?x-oss-process=image/watermark,type_d3F5LXplbmhlaQ,shadow_50,text_Q1NETiBASFplcm8uY2hlbg==,size_20,color_FFFFFF,t_70,g_se,x_16)

```c
/*
 * Setup the initial page tables. We only setup the barest amount which is
 * required to get the kernel running. The following sections are required:
 *   - identity mapping to enable the MMU (low address, TTBR0)
 *   - first few MB of the kernel linear mapping to jump to once the MMU has
 *     been enabled
 */
__create_page_tables:
    mov x28, lr
    /*
     * Invalidate the idmap and swapper page tables to avoid potential
     * dirty cache lines being evicted.
     */
    adrp    x0, idmap_pg_dir     /* x0保存idmap_pg_dir当前所在的物理地址. */
    adrp    x1, swapper_pg_end   /* x1保存idmap_pg_dir和swapper_pg_dir的大小. */
    sub     x1, x1, x0
    bl      __inval_dcache_area  /* 清掉cache */
    /*
     * 将idmap_pg_dir赋值给x0，将swapper_pg_dir + SWAPPER_DIR_SIZE赋值给x6，然后将这段空间的页表的内容设置为0。
     */
    adrp    x0, idmap_pg_dir
    adrp    x1, swapper_pg_end
    sub x1, x1, x0
1:  stp xzr, xzr, [x0], #16
    stp xzr, xzr, [x0], #16
    stp xzr, xzr, [x0], #16
    stp xzr, xzr, [x0], #16
    subs    x1, x1, #64
    b.ne    1b
    
    /*
 	 * x7保存level3页表的entry的flags, 表明是普通内存,是一个block的entry, 
	 * 要映射的内存属性，通过一些flags表示这段内存比如共享属性、读写属性、cache一致性、属于内核空间等等
 	 */
    mov x7, SWAPPER_MM_MMUFLAGS    
	/*
     * Create the identity mapping. 创建idmap.
     */
    adrp    x0, idmap_pg_dir            /* x0保存idmap_pg_dir的物理地址,也就是idmap的页表地址 */
    adrp    x3, __idmap_text_start      /* 线性映射（idmap）的起始物理地址 */
    /*
     * VA_BITS may be too small to allow for an ID mapping to be created
     * that covers system RAM if that is located sufficiently high in the
     * physical address space. So for the ID map, use an extended virtual
     * range in that case, and configure an additional translation level
     * if needed.
     *
     * Calculate the maximum allowed value for TCR_EL1.T0SZ so that the
     * entire ID map region can be mapped. As T0SZ == (64 - #bits used),
     * this number conveniently equals the number of leading zeroes in
     * the physical address of __idmap_text_end.
     */
    adrp    x5, __idmap_text_end        /* 线性映射（idmap）的结束物理地址 */
    /* 
     * CLZ指令返回操作数二进制数中最高符号位与第一个1之间的0的个数。
     * 如果操作数为0，则指令返回64；
     * 如果操作数二进制编码第63位为1，指令返回0.
     */
    clz x5, x5 
    /* TCR_T0SZ计算给定虚拟地址数目下，前导0的个数。
     * 如果虚拟地址是48位，那么前导0就是16个，
     * 如果 x5 存在前导0小于虚拟地址前导0的情况，则表明需要地址扩展
     * 否则不需要扩展跳转到标号处
     */
    cmp x5, TCR_T0SZ(VA_BITS)   /* default T0SZ small enough? */
    b.ge    1f                  /* then skip VA range extension 不需要扩展跳转到标号处 */

    adr_l   x6, idmap_t0sz      /* x6保存idmap_t0sz变量的物理地址 */
    str x5, [x6]                /* 将x5前导0的个数存入idmap_t0sz变量中 */
    dmb sy                      /* 内存屏障 */
    dc  ivac, x6                /* 使cache无效*/

/* 如果物理地址的位置非常高，比如超过了第43bit的为1 ，
 * 但是虚拟地址配置的是42bit的，而identity mapping虚拟地址等于物理地址，
 * 那么就无法表示了，启动虚拟地址扩展，扩展到48位（armv8最高支持），
 * 增加的一个level叫做EXTRA，EXTRA_SHIFT位PGDIR_SHIFT + PAGE_SHIFT - 3，
 * EXTRA_SHIFT中的entry数目为1 << (48 - EXTRA_SHIFT)
 */
#if (VA_BITS < 48)
    /* 正常建立最高level mapping的时候， shift是PGDIR_SHIFT，
     * 但是，由于物理地址位置太高，需要额外的映射，因此这里需要再加上一个level的mapping，
     * 因此shift需要PGDIR_SHIFT ＋ （PAGE_SHIFT - 3）。 
     */
#define EXTRA_SHIFT (PGDIR_SHIFT + PAGE_SHIFT - 3)
    /* 增加了一个level的Translation table，我们需要确定这个增加level的Translation table中
     * 包含的描述符的数目，EXTRA_PTRS给出了这个参数。 
     */
#define EXTRA_PTRS  (1 << (PHYS_MASK_SHIFT - EXTRA_SHIFT))
    /*
     * If VA_BITS < 48, we have to configure an additional table level.
     * First, we have to verify our assumption that the current value of
     * VA_BITS was chosen such that all translation levels are fully
     * utilised, and that lowering T0SZ will always result in an additional
     * translation level to be configured.
     */
#if VA_BITS != EXTRA_SHIFT /* kernel要求正确配置情况下这两值必定相等，否则就是配置有问题 */
#error "Mismatch between VA_BITS and page size/number of translation levels"
#endif
    mov x4, EXTRA_PTRS
    /* 创建extea level的entry，以上部分是地址扩展部分 参数：页表地址，虚拟地址，页表shift, 页表entry数量*/
    create_table_entry x0, x3, EXTRA_SHIFT, x4, x5, x6  
#else
    /*
     * If VA_BITS == 48, we don't have to configure an additional
     * translation level, but the top-level table has more entries.
     */
    mov x4, #1 << (PHYS_MASK_SHIFT - PGDIR_SHIFT)
    str_l   x4, idmap_ptrs_per_pgd, x5
#endif
1:
    ldr_l   x4, idmap_ptrs_per_pgd      /* 每个pgd有多少个page entry  512个 */
    mov x5, x3                          // __pa(__idmap_text_start)
    adr_l   x6, __idmap_text_end        // __pa(__idmap_text_end)
    /* 创建idmap的映射  
     * 参数：idmap页表地址
     *		x1表示啥？
     *      idmap虚拟起始地址
     *		idmap虚拟结束地址
     *      页表entry的属性
     *      idmap物理起始地址
     *      pgd entry的个数
     */
    map_memory x0, x1, x3, x6, x7, x3, x4, x10, x11, x12, x13, x14
    /*
     * Map the kernel image (starting with PHYS_OFFSET).
     */
    adrp    x0, swapper_pg_dir              /* x0指向内核地址空间PGD基地址 */
    mov_q   x5, KIMAGE_VADDR + TEXT_OFFSET  /* x5指向内核image的首地址, compile time __va(_text) */
    add x5, x5, x23                         /* 添加内核地址空间布局随机化的偏移， x23是在前面保存的 */
    mov x4, PTRS_PER_PGD
    adrp    x6, _end        // runtime __pa(_end)    kernel image的结束地址
    adrp    x3, _text       // runtime __pa(_text)   kernel image的起始地址
    sub x6, x6, x3          // _end - _text              获得kernel image的size
    add x6, x6, x5          // runtime __va(_end)        加上随机va_pa的offset，得到kernel image结束地址的va
    /* 创建swapper_pg_dir映射 */
    map_memory x0, x1, x5, x6, x7, x3, x4, x10, x11, x12, x13, x14
        
    /*
	 * Since the page tables have been populated with non-cacheable
	 * accesses (MMU disabled), invalidate the idmap and swapper page
	 * tables again to remove any speculatively loaded cache lines.
	 */
	adrp	x0, idmap_pg_dir
	adrp	x1, swapper_pg_end
	sub	x1, x1, x0
	dmb	sy
	bl	__inval_dcache_area

	ret	x28
ENDPROC(__create_page_tables)

```

上面第一个调用map_memory宏的地方实现： 将虚拟地址[x3, x6]映射到(__idmap_text_start当前在物理内存中的地址)~(__**idmap_text_end当前在物理内存中的地址**)，table从idmap_pg_dir当前所在的物理地址处开始存放。目的是保证在开启MMU后，程序还可以正常运行。该段映射va==pa。

上面最后一行调用map_memory宏的地方实现：**将kernel镜像占用的虚拟地址空间[_text, _end]映射到当前kernel镜像当前所在的物理内存地址空间上**，table存放到swapper_pg_dir当前所在的物理内存地址处。

## create_table_entry

宏用来创建level0和和level1的页表. 虚拟地址的[47:39]在level0页表中进行索引, 索引到的entry指向level1的页表, 这里level1的页表就是level0页表的下一个PAGE. 对应的[38:30]在level1页表中进行索引, 索引的entry指向level2的页表. 也就是再下一个PAGE. 这里来分析下`create_table_entry`宏，这个宏定义主要是用来创建一个中间level的translation table中的描述符。如果用linux的术语，就是创建PGD、PUD或者PMD的描述符。如果用ARM64术语，就是创建L0、L1或者L2的描述符。具体创建哪一个level的Translation table descriptor是由tbl参数指定的，tbl指向了该translation table的内存。
其处理流程如下：

- tmp1中保存virt地址对应在Translation table中的entry index

- 初始阶段的页表（PGD/PUD/PMD/PTE）都是排列在一起的，每一个占用一个page。也就是说，如果create_table_entry当前操作的是PGD，那么tmp2这时候保存了下一个level的页表，也就是PUD了。

- 光有下一级translation table的地址不行，还要告知该描述符是否有效（bit 0），该描述符的类型是哪一种类型（bit 1）。对于中间level的页表，该描述符不可能是block entry，只能是table type的描述符，因此该描述符的最低两位是0b11。

  #define PMD_TYPE_TABLE (_AT(pmdval_t, 3) << 0)

- 把页表项内容放到指定的页表项当中,之所以有“lsl #3”操作，是因为一个描述符占据8个Byte，结束的时候tbl会加上一个PAGE_SIZE，也就是tbl变成了下一级页表的地址

```c
/*
 * Macro to create a table entry to the next page.
 *
 *	tbl:	指向了该translation table的内存，决定了具体创建哪一个level的Translation table descriptor
 *	virt:	要创建地址映射的那个虚拟地址
 *	shift:	表示这一级页表的在虚拟地址中的偏移
 *	ptrs:	表示这一级页表是几位的
 *
 * Preserves:	virt
 * Corrupts:	tmp1, tmp2
 * Returns:	tbl -> next level table page address
 */
.macro	create_table_entry, tbl, virt, shift, ptrs, tmp1, tmp2
	/* 下面两条指令取出虚拟地址(virt)的[shift+9:shift], 作为index */
	lsr	\tmp1, \virt, #\shift
	and	\tmp1, \tmp1, #\ptrs - 1	// table index
	/*
	 * 下面两条指令计算出这一级页表对应virt的entry的值, 第一条指令计算entry指向的下一级
	 * 页表的物理地址, 第二条指令指定当前entry是PMD_TYPE_TABLE, 也就是表示当前entry
     * 指向的仍然是一个页目录, 具体看arm的architecture reference manual.
	 */
	add	\tmp2, \tbl, #PAGE_SIZE
	orr	\tmp2, \tmp2, #PMD_TYPE_TABLE	// address of next table and entry type
	/*
	 * 使用之前计算的index来得到virt对应的entry的位置(tbl + index * 8 byte), 然后把
	 * 页表entry存到那个位置
	 * /
	str	\tmp2, [\tbl, \tmp1, lsl #3]
	/* tbl指向下一级页表, 方便下一次计算 */
	add	\tbl, \tbl, #PAGE_SIZE		   // next level table page
	.endm
/* 上述函数创建页表项，并且返回下一个Level的页表地址。 */
```

## idmap_pg_dir和swapper_pg_dir

```c
. = ALIGN(SZ_4K);				            \
VMLINUX_SYMBOL(__idmap_text_start) = .;		\
*(.idmap.text)					            \
VMLINUX_SYMBOL(__idmap_text_end) = .;
```

`idmap_pg_dir`对应的页表是用来将与KERNEL所在物理地址相等的虚拟地址映射到相同的物理地址. 从而保证开启MMU时, 不会发生无法获取页表的情况. 而`swapper_pg_dir`如其名是swapper进程运行所需的页表, 是内核初始化过程所用的页表.

```c
#define SWAPPER_DIR_SIZE	(SWAPPER_PGTABLE_LEVELS * PAGE_SIZE)
#define IDMAP_DIR_SIZE		(IDMAP_PGTABLE_LEVELS * PAGE_SIZE)
```

通过对宏的观察, 我们了解到`idmap_pg_dir`和`swapper_pg_dir`都是3个PAGE_SIZE(12K), 我们知道使用4K页加48bit虚拟地址需要4级页表才能满足, 每级页表都是一个PAGE

- level0 [47:39] 512个entry, 每个8byte, 一共4K
- level1 [38:30] 512个entry, 每个8byte, 一共4K
- level2 [29:21] 512个entry, 每个8byte, 一共4K
- level3 [20:13] 512个entry, 每个8byte, 一共4K

剩下的11:0地址用level3的内容拼接得到最终的物理地址.

**而这里`idmap_pg_dir`和`swapper_pg_dir`都只有3个PAGE是如何来映射的呢? 其实这里KERNEL在早期的临时页表为了节省内存, 并没有使用标准的4级映射, 而是使用的MMU中的block来直接描述2M(使用低21bit)内存区, 而不是用entry来描述4K页, 从而节省了level3的页表.**

**也就是说上面的level2页表中, 每条entry指向的不是level3页表, 而是一个2M的内存区.** 这在上面SWAPPER_MM_MMUFLAGS的flag里面定义的。

可知idmap的映射规则是其虚拟地址值等于物理地址值。之所以需要**idmap映射**是因为现代处理器存在流水线，分支预测等功能，在MMU开启时，打开MMU指令执行时，其后的指令可能已经取指完成，且其地址还是物理地址。而MMU使能完成后，实际上系统已经运行于虚拟地址模式下，若不采取相应措施，此时这些已经取指完成的指令可能会执行错误。故内核采用了将idmap映射的物理地址和虚拟地址设为相等，从而规避了以上问题。

**另外ARM64有TTBR0, TTBR1(Translation Table Base Register)分别用来指示内核空间和用户空间页表所在的物理地址, 而在这个时候, TTBR0不是用来指示用户空间地址, 而是用来指示与物理地址相等的虚拟地址所用的页表. 所以TTBR0里面是`.idmap.text`的物理地址, TTBR1里面是`swapper_pg_dir`的物理地址.**

![image-20230204163437715](D:\wsl\rootfs\root\work\sphinx\source\linux\boot\figs\image-20230204163437715.png)

下面结合kernel img的映射分析一下map_memory是如何做到的：

```c
    adrp    x0, swapper_pg_dir              /* x0指向内核地址空间PGD基地址 */
    mov_q   x5, KIMAGE_VADDR + TEXT_OFFSET  /* x5指向内核image的首地址, compile time __va(_text) */
    add x5, x5, x23                         /* 添加内核地址空间布局随机化的偏移， x23是在前面保存的 */
    mov x4, PTRS_PER_PGD
    adrp    x6, _end        // runtime __pa(_end)    kernel image的结束地址
    adrp    x3, _text       // runtime __pa(_text)   kernel image的起始地址
    sub x6, x6, x3          // _end - _text              获得kernel image的size
    add x6, x6, x5          // runtime __va(_end)        加上随机va_pa的offset，得到kernel image结束地址的va
    /* 创建映射 */
    map_memory x0, x1, x5, x6, x7, x3, x4, x10, x11, x12, x13, x14
```

结合注释，x5和x6分别存放需要映射的虚拟地址的起始和结束地址，x7表示表项的flags，x3存放需要被映射的物理起始地址，x4存放一个level0 table包含的表项的个数(1<<9)。

由于后面kernel会自己重新再建立页表，所以这里采用的映射比较粗糙，在level2 table里使用的是Block descriptor，每个block descriptor可以映射2MB物理地址，这样只需要3个页来就可以放下用于映射kernel镜像的table（level0、level1和level2），如下图：

![image-20230204163508756](D:\wsl\rootfs\root\work\sphinx\source\linux\boot\figs\image-20230204163508756.png)

上面的map_memory就负责建立上图中level0到level2的数据结构关系，没有用到level3

ARM64提供了四种不同的descriptor type：

![img](https://pic.ikafan.com/imgp/L3Byb3h5L2h0dHBzL3M4LjUxY3RvLmNvbS9pbWFnZXMvYmxvZy8yMDIxMDcvMzEvNmI3MDQ3ZjJlZDg2ODY0OGU4ODQ1NjBkNDhlMzY3YWMucG5n.jpg)

这里用到了Table descriptor和Block entry两种。

##  map_memory

```c
235 /*
236  * Map memory for specified virtual address range. Each level of page table needed supports
237  * multiple entries. If a level requires n entries the next page table level is assumed to be
238  * formed from n pages.
239  *
240  *      tbl:    location of page table
241  *      rtbl:   address to be used for first level page table entry (typically tbl + PAGE_SIZE)
242  *      vstart: start address to map
243  *      vend:   end address to map - we map [vstart, vend]
244  *      flags:  flags to use to map last level entries
245  *      phys:   physical address corresponding to vstart - physical memory is contiguous
246  *      pgds:   the number of pgd entries
247  *
248  * Temporaries: istart, iend, tmp, count, sv - these need to be different registers
249  * Preserves:   vstart, vend, flags
250  * Corrupts:    tbl, rtbl, istart, iend, tmp, count, sv
251  */
252         .macro map_memory, tbl, rtbl, vstart, vend, flags, phys, pgds, istart, iend, tmp, count, sv
253         add \rtbl, \tbl, #PAGE_SIZE
254         mov \sv, \rtbl
255         mov \count, #0           /* PGD */
256         compute_indices \vstart, \vend, #PGDIR_SHIFT, \pgds, \istart, \iend, \count
257         populate_entries \tbl, \rtbl, \istart, \iend, #PMD_TYPE_TABLE, #PAGE_SIZE, \tmp
258         mov \tbl, \sv
259         mov \sv, \rtbl
260
261 #if SWAPPER_PGTABLE_LEVELS > 3   /* PUD */
262         compute_indices \vstart, \vend, #PUD_SHIFT, #PTRS_PER_PUD, \istart, \iend, \count
263         populate_entries \tbl, \rtbl, \istart, \iend, #PMD_TYPE_TABLE, #PAGE_SIZE, \tmp
264         mov \tbl, \sv
265         mov \sv, \rtbl
266 #endif
267
268 #if SWAPPER_PGTABLE_LEVELS > 2  /* PMD*/
269         compute_indices \vstart, \vend, #SWAPPER_TABLE_SHIFT, #PTRS_PER_PMD, \istart, \iend, \count
270         populate_entries \tbl, \rtbl, \istart, \iend, #PMD_TYPE_TABLE, #PAGE_SIZE, \tmp
271         mov \tbl, \sv
272 #endif
273                                 /* PTE */
274         compute_indices \vstart, \vend, #SWAPPER_BLOCK_SHIFT, #PTRS_PER_PTE, \istart, \iend, \count
275         bic \count, \phys, #SWAPPER_BLOCK_SIZE - 1
276         populate_entries \tbl, \count, \istart, \iend, \flags, #SWAPPER_BLOCK_SIZE, \tmp
277         .endm
```

其中涉及到两个宏compute_indices和populate_entries，前者计算需要占用某个level的表项的索引范围，后者用于填充被占用的那些表项。

下面是compute_indices实现：

```c
199 /*
200  * Compute indices of table entries from virtual address range. If multiple entries
201  * were needed in the previous page table level then the next page table level is assumed
202  * to be composed of multiple pages. (This effectively scales the end index).
203  *
204  *      vstart: virtual address of start of range
205  *      vend:   virtual address of end of range
206  *      shift:  shift used to transform virtual address into index
207  *      ptrs:   number of entries in page table
208  *      istart: index in table corresponding to vstart
209  *      iend:   index in table corresponding to vend
210  *      count:  On entry: how many extra entries were required in previous level, scales
211  *                        our end index.
212  *              On exit: returns how many extra entries required for next page table level
213  *
214  * Preserves:   vstart, vend, shift, ptrs
215  * Returns:     istart, iend, count
216  */
217         .macro compute_indices, vstart, vend, shift, ptrs, istart, iend, count
218         lsr     \iend, \vend, \shift
219         mov     \istart, \ptrs
220         sub     \istart, \istart, #1
221         and     \iend, \iend, \istart   // iend = (vend >> shift) & (ptrs - 1)
222         mov     \istart, \ptrs
223         mul     \istart, \istart, \count
224         add     \iend, \iend, \istart   // iend += (count - 1) * ptrs
225                                         // our entries span multiple tables
226
227         lsr     \istart, \vstart, \shift
228         mov     \count, \ptrs
229         sub     \count, \count, #1
230         and     \istart, \istart, \count
231
232         sub     \count, \iend, \istart
233         .endm
```



```c
173 /*
174  * Macro to populate page table entries, these entries can be pointers to the next level
175  * or last level entries pointing to physical memory.
176  *
177  *      tbl:    page table address
178  *      rtbl:   pointer to page table or physical memory
179  *      index:  start index to write
180  *      eindex: end index to write - [index, eindex] written to
181  *      flags:  flags for pagetable entry to or in
182  *      inc:    increment to rtbl between each entry
183  *      tmp1:   temporary variable
184  *
185  * Preserves:   tbl, eindex, flags, inc
186  * Corrupts:    index, tmp1
187  * Returns:     rtbl
188  */
189         .macro populate_entries, tbl, rtbl, index, eindex, flags, inc, tmp1
190 .Lpe\@: phys_to_pte \tmp1, \rtbl
191         orr     \tmp1, \tmp1, \flags    // tmp1 = table entry
192         str     \tmp1, [\tbl, \index, lsl #3]
193         add     \rtbl, \rtbl, \inc      // rtbl = pa next level
194         add     \index, \index, #1
195         cmp     \index, \eindex
196         b.ls    .Lpe\@
197         .endm
```

如果将上面的操作转换成C语言，就容易理解了：

```c
void populate_entries(char *tbl, char **rtbl, int index, int eindex,
    int flags, int inc, char *tmp1)
{
    while (index <= eindex) {
        tmp1 = *rtbl;
        tmp1 = tmp1 | flags;
        *(tbl + index*8) = tmp1;
 
        *rtbl = *rtbl + inc;
        index++;
    }
}
 
void compute_indices (uint64_t vstart, uint64_t vend, int shift, int ptrs,
    int *istart, int *iend, int *count)
{
    *iend = vend >> shift;
    *istart = ptrs;
    *istart = *istart - 1;
    *iend = *iend & *istart; // 计算end index
 
    *istart = ptrs;
    *istart = (*istart) * (*count);
    *iend = *iend + *istart; // 由于*count是0，这里end index没变变化
 
    *istart = vstart >> shift;
    *count = ptrs;
    *count = *count - 1;
    *istart = *istart & *count;  // 计算start index
 
    *count = *iend - *istart;    // 计算需要的index的数量
}
 
void map_memory(char *tbl, char *rtbl, uint64_t vstart, uint64_t vend, int flags,
    uint64_t phys, int pgds, int istart, int iend, int tmp, int count, char *sv)
{
#define PAGE_SIZE (1 << 12)
 
    tbl = (char *)malloc(PAGE_SIZE * 3); // 用于存放level0~level2的table的缓冲区
 
    rtbl = tbl + PAGE_SIZE; // rtbl指向下一个level的table
    sv = rtbl;
    count = 0;
 
#define PGDIR_SHIFT (39)
#define PMD_TYPE_TABLE (0x3 << 0)  // 表示table descriptor
#define PGDS (1 << 9)
 
    compute_indices(vstart, vend, PGDIR_SHIFT, PGDS, &istart, &iend, &count);
    populate_entries(tbl, &rtbl, istart, iend, PMD_TYPE_TABLE, PAGE_SIZE, tmp);
 
    tbl = sv;
    sv = rtbl;
 
#define SWAPPER_TABLE_SHIFT (30)
#define PTRS_PER_PMD (1<<9)
 
    compute_indices(vstart, vend, SWAPPER_TABLE_SHIFT, PTRS_PER_PMD, &istart, &iend, &count);
    populate_entries(tbl, &rtbl, istart, iend, PMD_TYPE_TABLE, PAGE_SIZE, tmp); //table descriptor
 
    tbl = sv;
 
#define SWAPPER_BLOCK_SHIFT (21)
#define PTRS_PER_PTE (1 << 9)      //512
#define SWAPPER_BLOCK_SIZE (1<<21) //2MB
// 这里的flags是SWAPPER_MM_MMUFLAGS，为((4<<2) | ((1<<0) | (1<<10) | (3<<8))), 类型Block entry
 
    compute_indices(vstart, vend, SWAPPER_BLOCK_SHIFT, PTRS_PER_PTE, &istart, &iend, &count);
    count = phys ^ (SWAPPER_BLOCK_SIZE - 1);
    populate_entries(tbl, &count, istart, iend, flags, SWAPPER_BLOCK_SIZE, tmp);
}
```

由于我们编译出来的kernel大概有20.7MB左右，所以用level0 table需要一项（512G），level1 table需要一项（1GB），level2 block需要11个（22MB）。

 ![img](https://pic.ikafan.com/imgp/L3Byb3h5L2h0dHBzL3M4LjUxY3RvLmNvbS9pbWFnZXMvYmxvZy8yMDIxMDcvMzEvMTMwOWJjYjBmMDI0ZDliMzA2N2IyMzA2ZTc2Y2JmMTAucG5n.jpg)

其实还是没有特别搞懂map_memmory宏，先搁置吧，以后再来看。
