## 重要数据结构

### swap_info_struct

这个结构体描述的是一个 swap 分区的具体信息(以下称之为 swap 分区描述符)，一个 swap 分区对应一个 `swap_info_struct` 结构体，该结构体中具体的内容如下：

```c
/*
 * The in-memory structure used to track swap areas.
 */
struct swap_info_struct {
	unsigned long	flags;		/* SWP_USED etc: see above */
	signed short	prio;		/* swap priority of this type */
	struct plist_node list;		/* swap_active_head 链表中的节点 */
	struct plist_node avail_lists[MAX_NUMNODES];/* entry in swap_avail_heads */
    /* 
     * 该变量指的是第几个 swap 分区，系统一共只允许创建 MAX_SWAPFILES 个 swap 分区，
     * 如果该swap 分区是第一个创建的，那么type 就是0，该变量同时也是 swap_info[] 全
     * 局变量的索引，即swap_info[0] 就是第一个 swap 分区的 swap_info_struct 结构体。
     * swap_info[] 数组保存着系统中所有swap 分区描述符，即 swap_info_struct 结构体。 
     */
	signed char	type;		    /* strange name for an index */
	unsigned int	max;		/* extent of the swap_map */
	unsigned char *swap_map;	/* vmalloc'ed array of usage counts */
	struct swap_cluster_info *cluster_info; /* cluster info. Only for SSD */
	struct swap_cluster_list free_clusters; /* free clusters list */
	unsigned int lowest_bit;	/* index of first free in swap_map */
	unsigned int highest_bit;	/* index of last free in swap_map */
	unsigned int pages;		    /* total of usable pages of swap */
	unsigned int inuse_pages;	/* number of those currently in use */
	unsigned int cluster_next;	/* likely index for next allocation */
	unsigned int cluster_nr;	/* countdown to next cluster search */
	struct percpu_cluster __percpu *percpu_cluster; /* per cpu's swap location */
	struct swap_extent *curr_swap_extent;
	struct swap_extent first_swap_extent;
	struct block_device *bdev;	/* swap device or bdev of swap file */
	struct file *swap_file;		/* 指向 swap 分区的 struct file 结构体*/
	unsigned int old_block_size;	/* seldom referenced */
#ifdef CONFIG_FRONTSWAP
	unsigned long *frontswap_map;	/* frontswap in-use, one bit per page */
	atomic_t frontswap_pages;	   /* frontswap pages in-use counter */
#endif
	spinlock_t lock;		/*
					 * protect map scan related fields like
					 * swap_map, lowest_bit, highest_bit,
					 * inuse_pages, cluster_next,
					 * cluster_nr, lowest_alloc,
					 * highest_alloc, free/discard cluster
					 * list. other fields are only changed
					 * at swapon/swapoff, so are protected
					 * by swap_lock. changing flags need
					 * hold this lock and swap_lock. If
					 * both locks need hold, hold swap_lock
					 * first.
					 */
	spinlock_t cont_lock;		     /* protect swap count continuation page list. */
	struct work_struct discard_work; /* discard worker */
	struct swap_cluster_list discard_clusters;   /* discard clusters list */
};
```

该结构体包含的内容非常多，这里总结一下，不管 swap 分区是一整个块设备还是一个在块设备上创建的文件，主要是把它划分成多个以一个页面为单位的存储块，并用 `swap_map` 来描述各个存储块的使用情况。然后以高低优先级的顺序保存在 `swap_active_head` 链表中。

### swap_entry

思考一个问题，如果现在把一个物理页面的数据回写到 swap 分区中的其中一个存储块，然后释放该物理页面，在下次应用进程再需要读回刚刚被回写的数据时，如何快速地寻找到那个存储块？

我们可以第一时间想到 `pte`，那么 linux swap 机制就需要在回收物理页面之前修改该虚拟地址对应的 `pte`，使之指向一个 `swp_entry_t` 类型的变量，在下次访问该虚拟地址时进入缺页中断，然后通过 `swp_entry_t` 来找到 swap 分区中的存储块位置，并从中读回数据，最后再修改 `pte` 重新指向物理页面。
`swap_entry_t` 变量就是在整体架构章节中提到的 swap entry 的 `pte`。以下是该变量的定义

```c
typedef struct {
	unsigned long val;
} swp_entry_t;
```

该变量可通过 `set_page_private` 函数保存在 `page-> private` 中，跟随 `page` 进行传递，所以如果需要该 page 的swap entry，直接访问该 page 的 `private` 就能得到，其实它就是一个 `unsigned long` 类型的值，在这个数值中包含了两个信息，一个是 swap 分区的 type（以下称 `swap type`），另一个是存储块的编号，即 offset (以下称 `swap offset`)，第2到第7位存放 `swap type`，第8位到第57位存放 `swap offset`，最低两位保留不用，第58位必须等于0，因为该位置1是代表无效的pte，可参见源码注释

```
 *	bits 0-1:	present (must be zero)
 *	bits 2-7:	swap type
 *	bits 8-57:  swap offset
 *	bit  58:	PTE_PROT_NONE (must be zero)
```

得到 `swap type` 和 `swap offset` 之后，我们就可以通过全局数组变量 `swap_info[swap type]` 来得到swap 分区描述符 `swap_info_struct`，再通过 `swap offset` 找到对应的存储块描述符 `swap_extent`，再把`swap_extent->start_block` 转换成 bio 所需的扇区号，然后通过 `submit_bio` 函数来发起读请求，最后等待block io层完成读操作。这一过程的关键在于bio的组建，即如何得到扇区号。

### swap_extent

存储块描述符，用于描述多个连续的存储块，以及描述与块设备中扇区的映射关系。其数据结构如下

```c
struct swap_extent {
	struct list_head list; /* 链表节点，其链表头是 swap 分区描述符的 first_swap_extent 变量 */
	pgoff_t start_page;    /* 描述的第一个存储块编号 */
	pgoff_t nr_pages;      /* 描述存储块个数 */
	sector_t start_block;  /* 描述该第一个存储块对应的扇区编号 */
};
```

