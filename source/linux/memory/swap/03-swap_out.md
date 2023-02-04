## Swapout

Swapout 的入口是在shrink_page_list, 即当系统需要回收物理内存时发生swapout 的动作，先来看一下一个匿名页面回收的整个过程框图
![swapout](https://img-blog.csdnimg.cn/20190322113007908.png?x-oss-process=image/watermark,type_ZmFuZ3poZW5naGVpdGk,shadow_10,text_aHR0cHM6Ly9ibG9nLmNzZG4ubmV0L3FraGh5Z2EyMDE2,size_16,color_FFFFFF,t_70)
整个回收过程分为两次 shrink，这里面的原因是因为IO的写速度会很慢，不能阻塞内存回收的进程，所以第一次shrink只是发起了一个回写请求然后就返回了，等待IO的回写操作完成后，第二次回收该匿名页面时，再把它回收掉。
先来看一下第一次shrink的过程，以及page的状态变化过程

```c
static unsigned long shrink_page_list(struct list_head *page_list,
				      struct pglist_data *pgdat,
				      struct scan_control *sc,
				      enum ttu_flags ttu_flags,
				      struct reclaim_stat *stat,
				      bool force_reclaim)
{
	LIST_HEAD(ret_pages); //初始化返回的链表，即把此次shrink无法回收的页面放入该链表中
	LIST_HEAD(free_pages); //初始化回收的链表，即把此次shrink 可以回收的页面放入该链表中
…
	while (!list_empty(page_list)) {
…
		page = lru_to_page(page_list); 
		list_del(&page->lru); // 从 page_list 中取出一个 page，page_list 需要回收的page链表

		if (!trylock_page(page))  //先判断是用否有别的进程在使用该页面，如果没有则设置PG_lock，并返回1, 这个flag多用于io读, 但此时第一次shrink时大多数情况下是没有别的进程在使用该页面的，所以接着往下走
			goto keep;

		may_enter_fs = (sc->gfp_mask & __GFP_FS) ||
			(PageSwapCache(page) && (sc->gfp_mask & __GFP_IO));

		if (PageAnon(page) && PageSwapBacked(page)) { //判断是否是匿名页面并且不是lazyfree的页面，显然这个条件是满足的
			if (!PageSwapCache(page)) { //判断该匿名页面是否是 swapcache ，即通过page的 PG_swapcache 的flag 来判断，此时该页面第一次 shrink，所以这里是否，进入if里面的流程
                  …
				if (!add_to_swap(page)) //为该匿名页面创建swp_entry_t，并存放到page->private变量中，把page放入 swap cache，设置page的PG_swapcache和PG_dirty的flag，并更新swap_info_struct的页槽信息，该函数是通往 swap core 和swap cache的接口函数，下面会分析
				{
                            …
						goto activate_locked; // 失败后返回
				}
…
				/* Adding to swap updated mapping */
				mapping = page_mapping(page); // 根据page中的swp_entry_t获取对应的swapper_spaces[type][offset]，这里可回顾一下数据结构章节中的swapper_spaces的介绍。
			}
		} else if (unlikely(PageTransHuge(page))) {
			/* Split file THP */
			if (split_huge_page_to_list(page, page_list))
				goto keep_locked;
		}

		/*
		 * The page is mapped into the page tables of one or more
		 * processes. Try to unmap it here.
		 */
		if (page_mapped(page)) {
			enum ttu_flags flags = ttu_flags | TTU_BATCH_FLUSH;

			if (unlikely(PageTransHuge(page)))
				flags |= TTU_SPLIT_HUGE_PMD;
			if (!try_to_unmap(page, flags, sc->target_vma)) { // unmap， 即与上层的虚拟地址解除映射关系，并修改pte，使其值等于 page->private，即swp_entry_t变量，等到swapin 时就直接把pte强制类型转换成swp_entry_t 类型的值，就可以得到entry了。
				nr_unmap_fail++;
				goto activate_locked;
			}
		}

		if (PageDirty(page)) { //由于add_to_swap 函数最后把该页面设置为脏页面，所以该if成立，进入if里面
			…
						/*
			 * Page is dirty. Flush the TLB if a writable entry
			 * potentially exists to avoid CPU writes after IO
			 * starts and then write it out here.
			 */
			try_to_unmap_flush_dirty();
			switch (pageout(page, mapping, sc)) { // 发起 io 回写请求，并把该page 的flag 设置为PG_writeback，然后把PG_dirty清除掉
		    ……
			case PAGE_SUCCESS: //如果请求成功，返回 PAGE_SUCCESS
				if (PageWriteback(page))  //该条件成立，跳转到 keep
					goto keep;
                   ……
			}
		}
……
keep:
		list_add(&page->lru, &ret_pages); //把该页面放到 ret_pages链表里，返回时会把该链表中的所有页面都放回收lru 链表中，即不回收页面
		VM_BUG_ON_PAGE(PageLRU(page) || PageUnevictable(page), page);
	}
……

	list_splice(&ret_pages, page_list);
……
	return nr_reclaimed;
}
接下来再看一下add_to_swap函数实现
int add_to_swap(struct page *page)
{
	swp_entry_t entry;
	int err;
     ……
	entry = get_swap_page(page); //为该页面分配一个swp_entry_t，并更新swap_info_struct的页槽信息
	if (!entry.val)
		return 0;
    ……
	err = add_to_swap_cache(page, entry,
			__GFP_HIGH|__GFP_NOMEMALLOC|__GFP_NOWARN); //把页面加入到swap cache 中，设置PG_swapcache，并把entry 保存到page->private变量中，跟随page传递
	/* -ENOMEM radix-tree allocation failure */
	
	set_page_dirty(page); // 设置该页面为脏页

	return 1;
     ……
}
```

再来看一下 `get_swap_page` 函数，分析一下 `swp_entry_t` 是如何分配出来的，页槽信息怎么更新。kernel 4.14的内核在实现该函数时因为增加了槽缓存的机制，会比较复杂，其实即是预先分配好几个`swp_entry_t` 缓存起来，需要时从缓存分配，不过我们抓住关键几个步骤就可以了，先不考虑槽缓存

```c
swp_entry_t get_swap_page(struct page *page)
{
	swp_entry_t entry, *pentry;
	struct swap_slots_cache *cache;

	entry.val = 0;
     ……
	get_swap_pages(1, false, &entry); // 1代表需要分配一个存储块，false 代表

	return entry;
}
```

直接跳到 `get_swap_pages` 函数，该函数的目的有两个，一个是找出一个合适的 swap 分区，另一个是从 swap 分区中快速地找到合适的存储块，即 swap offset。

```c
int get_swap_pages(int n_goal, bool cluster, swp_entry_t swp_entries[])
{
…

start_over:
	node = numa_node_id(); //获取numa 节点号
	plist_for_each_entry_safe(si, next, &swap_avail_heads[node], avail_lists[node]) { //以优先级高到低遍历所有swap分区
         ……
start:
		spin_lock(&si->lock);
		if (!si->highest_bit || !(si->flags & SWP_WRITEOK)) { //判断该swap分区是否还有空闲页槽，以及判断该swap分区是否可写的，SWP_WRITEOK这个flag是在swapon 的时候设置的，一般都带这个flag
			spin_lock(&swap_avail_lock);
			if (plist_node_empty(&si->avail_lists[node])) {
				spin_unlock(&si->lock);
				goto nextsi;
			}
			WARN(!si->highest_bit,
			     "swap_info %d in list but !highest_bit\n",
			     si->type);
			WARN(!(si->flags & SWP_WRITEOK),
			     "swap_info %d in list but !SWP_WRITEOK\n",
			     si->type);
			__del_from_avail_list(si);  //如果没有空闲页槽，则直接从swap_avail_heads链表中删除掉
			spin_unlock(&si->lock);
			goto nextsi; //跳到下一个swap分区
		}
		if (cluster) { // 这里是false ,因此走else路径，当内核的CONFIG_THP_SWAP的功能打开时，这里才是true
			if (!(si->flags & SWP_FILE))
				n_ret = swap_alloc_cluster(si, swp_entries);
		} else
			n_ret = scan_swap_map_slots(si, SWAP_HAS_CACHE,
						    n_goal, swp_entries);  //走到这里，说明已经找到合适的swap分区，即第一个目的已经完成，接下来通过该函数去寻找合适的 offset，最终把两者合并后返回swp_entries。
		……
nextsi:
		if (plist_node_empty(&next->avail_lists[node])) 
			goto start_over;
	}

	spin_unlock(&swap_avail_lock);

check_out:
	if (n_ret < n_goal)
		atomic_long_add((long)(n_goal - n_ret) * nr_pages,
				&nr_swap_pages);
noswap:
	return n_ret;
}
```

`scan_swap_map_slots` 比较复杂，其做法是通过 `ssd算法` 快速地查找到可用页槽编号。

```c
static int scan_swap_map_slots(struct swap_info_struct *si,
			       unsigned char usage, int nr,
			       swp_entry_t slots[])
{
     ……
	scan_base = offset = si->cluster_next; //获取下一个可用存储块的编号，即空闲页槽的编号

	/* SSD algorithm */
	if (si->cluster_info) {
		if (scan_swap_map_try_ssd_cluster(si, &offset, &scan_base)) //通过簇来辅助查找空闲页槽的编号，并重新设置offset变量
			goto checks; //如果找到则跳到下面的 checks
		else
			goto scan; //如果找不到，则跳到scan，全局地遍历 swap_map 看还有没有空闲的页槽
	}
     ……
checks:
	if (si->cluster_info) {  //这个if代码段中主要的功能是确保 offset 所处属的簇必须是空闲簇链表free_cluster的第一个簇
		while (scan_swap_map_ssd_cluster_conflict(si, offset)) {
		/* take a break if we already got some slots */
			if (n_ret)
				goto done;
			if (!scan_swap_map_try_ssd_cluster(si, &offset,
							&scan_base))
				goto scan;
		}
	}
	
	ci = lock_cluster(si, offset);   //获取簇的spin_lock
	/* reuse swap entry of cache-only swap if not busy. */
	if (vm_swap_full() && si->swap_map[offset] == SWAP_HAS_CACHE) { //如果该swap分区已经满了，则尝试回收部分页槽
		int swap_was_freed;
		unlock_cluster(ci);
		spin_unlock(&si->lock);
		swap_was_freed = __try_to_reclaim_swap(si, offset); //回收页槽
		spin_lock(&si->lock);
		/* entry was freed successfully, try to use this again */
		if (swap_was_freed)
			goto checks;  //如果回收到了页槽，则返回check 继续分配页槽
		goto scan; /* check next one */
	}
     ……
	si->swap_map[offset] = usage;  //更新页槽的第6位，即SWAP_HAS_CACHE
	inc_cluster_info_page(si, si->cluster_info, offset);  //把该页槽对应的簇从free_clusters的链表中取出来，并更新其data字段，即为1
	unlock_cluster(ci);  //解锁 spin_lock

	swap_range_alloc(si, offset, 1);  //更新swap_info_struct中的inuse_pages 变量，即加1
	si->cluster_next = offset + 1;  //更新下一个可用页槽的编号，即往后移一位
	slots[n_ret++] = swp_entry(si->type, offset);  //把 swap分区的type 和页槽篇号offset合并成swp_entry_t保存在slots[]中，返回给该函数调用者

	/* got enough slots or reach max slots? */
	if ((n_ret == nr) || (offset >= si->highest_bit))
		goto done;  //slot[] 填满后直接返回，这里在不考虑页槽缓存的情况下，slot[]数组中只需要一个swp_entry_t就可以了
……

done:
	si->flags -= SWP_SCANNING;
	return n_ret;

scan:
	spin_unlock(&si->lock);
	while (++offset <= si->highest_bit) {  //从当前的页槽号往后查找
		if (!si->swap_map[offset]) {  //页槽值为0，代表该页槽是空闲状态
			spin_lock(&si->lock);
			goto checks;   //找到后跳到 checks 更新页槽信息后直接返回
		}
		if (vm_swap_full() && si->swap_map[offset] == SWAP_HAS_CACHE) {
			spin_lock(&si->lock);
			goto checks;  //如果swap 分区满了，则跳回checks 回收页槽
		}
          ……
	}
	offset = si->lowest_bit;
	while (offset < scan_base) {  //从当前的页槽号往前查找，下面的逻辑与上面的while 逻辑一样
		if (!si->swap_map[offset]) {
			spin_lock(&si->lock);
			goto checks;
		}
		if (vm_swap_full() && si->swap_map[offset] == SWAP_HAS_CACHE) {
			spin_lock(&si->lock);
			goto checks;
		}
		if (unlikely(--latency_ration < 0)) {
			cond_resched();
			latency_ration = LATENCY_LIMIT;
		}
		offset++;
	}
	spin_lock(&si->lock);
    // 两个while循环已经代表了全局地扫描了swap_map数组，如果程序走到这，说明该swap分区里已经没有了可用页槽
no_page:
	si->flags -= SWP_SCANNING;
	return n_ret;
}
```

我们再来看一下`ssd算法`的核心函数 `scan_swap_map_try_ssd_cluster`，先来看一下它的参数

- *struct swap_info_struct* **si*
  指向swap分区描述符
- *unsigned long* **offset*
  ssd算法查找到的空闲页槽编号
- *unsigned long* **scan_base*
  ssd算法查找到的空闲页槽编号

函数的返回值是个bool类型，true代表已经找到空闲页槽编号，false 代表没有找到。

```
static bool scan_swap_map_try_ssd_cluster(struct swap_info_struct *si,
	unsigned long *offset, unsigned long *scan_base)
{
    ……
new_cluster:
	cluster = this_cpu_ptr(si->percpu_cluster);
	if (cluster_is_null(&cluster->index)) {  //这个if代码段主要是从free_clusters链表中获取第一个空闲簇，并赋值到per_cpu变量si->percpu_cluster，之后会对这个空闲簇进行可用页槽的查找
		if (!cluster_list_empty(&si->free_clusters)) {
			cluster->index = si->free_clusters.head;
			cluster->next = cluster_next(&cluster->index) *
					SWAPFILE_CLUSTER;
		} else if (!cluster_list_empty(&si->discard_clusters)) {
			/*
			 * we don't have free cluster but have some clusters in
			 * discarding, do discard now and reclaim them
			 */
			swap_do_scheduled_discard(si);
			*scan_base = *offset = si->cluster_next;
			goto new_cluster;
		} else
			return false;
	}

	found_free = false;

	/*
	 * Other CPUs can use our cluster if they can't find a free cluster,
	 * check if there is still free entry in the cluster
	 */
	tmp = cluster->next;  //获取当前可分配的簇
	max = min_t(unsigned long, si->max,
		    (cluster_next(&cluster->index) + 1) * SWAPFILE_CLUSTER);  //获取该簇的最大页槽索引
	if (tmp >= max) {
		cluster_set_null(&cluster->index);
		goto new_cluster;
	}
	ci = lock_cluster(si, tmp);  //加锁，保护该簇对应的256个页槽
	while (tmp < max) {
		if (!si->swap_map[tmp]) {
			found_free = true;  //找到一个空闲的页槽，跳出循环
			break;
		}
		tmp++;
	}
	unlock_cluster(ci);  //解锁
	if (!found_free) {
		cluster_set_null(&cluster->index);
		goto new_cluster;  //如果仍然没找到页槽，则返回new_cluster，从free_clusters链表中取出新的空闲簇再进行查找
	}
	cluster->next = tmp + 1;  //更新下一个可分配的簇
	*offset = tmp;  //把已经找到的页槽更新到offset 变量
	*scan_base = tmp; //把已经找到的页槽更新到scan_base 变量
	return found_free;
}
```

到此，基本的`ssd算法`已经分析完毕，读者可能会感觉到有些吃力，但只要抓住减少 `spin_lock` 竞争这一条主要目的去阅读这部分的代码，是比较好理解的。后面内核版本中还有一些针对提高 swap 页槽查找以及分配效率的修改，有兴趣的读可以看一下附录文章[1](https://string.quest/read/5553465#fn1) ，相信可以加深对本文的理解。
以上是第一次 shrink 的流程，至此，page 只是发起了 io 回写申请，然后就直接返回到 lru 链表中，并没有真正地回收页面。
在第一次 shrink 流程执行完后，其 `page` 的 `flag` 状态如下

| PG_writeback | PG_swapcache | PG_dirty | PG_active |
| ------------ | ------------ | -------- | --------- |
| 1            | 1            | 0        | 0         |

真正的回收页面发生在第二次shrink到该page时，即io回写完成之后，我们先来看一下 `bio->bi_end_io` 回调函数，即io回写完成后的回调函数，请注意`page`的`flag`状态变换

```
void end_swap_bio_write(struct bio *bio)
{
	struct page *page = bio->bi_io_vec[0].bv_page;  //从bio中获取page，即发起io回写的page

	if (bio->bi_status) {  //bio发生错误会进入该if代码段，在些分析中省略
		…
	}
	end_page_writeback(page);  //核心函数
	bio_put(bio);
}
```

再来看 end_page_writeback 函数

```
void end_page_writeback(struct page *page)
{
	/*
	 * TestClearPageReclaim could be used here but it is an atomic
	 * operation and overkill in this particular case. Failing to
	 * shuffle a page marked for immediate reclaim is too mild to
	 * justify taking an atomic operation penalty at the end of
	 * ever page writeback.
	 */
	if (PageReclaim(page)) {
		ClearPageReclaim(page);  //清除PG_reclaim标记位
		rotate_reclaimable_page(page);
	}

	if (!test_clear_page_writeback(page))  //清除PG_writeback标记位
		BUG();

	smp_mb__after_atomic();
	wake_up_page(page, PG_writeback);  //唤醒正在等该page的PG_writeback标记位的进程
}
```

所以，当page的io回写完成后，其PG_writeback和PG_reclaim两个标记位会被清除掉，那么当page 第二次shrink时，其flag状态应该就是如下表所示

| PG_writeback | PG_swapcache | PG_dirty | PG_active |
| ------------ | ------------ | -------- | --------- |
| 0            | 1            | 0        | 0         |

我们再来看一下第二次shrink的流程，其实可以跳过很多if判断，直接进入到回收流程

```
static unsigned long shrink_page_list(struct list_head *page_list,
				      struct pglist_data *pgdat,
				      struct scan_control *sc,
				      enum ttu_flags ttu_flags,
				      struct reclaim_stat *stat,
				      bool force_reclaim)
{
	……
	while (!list_empty(page_list)) {
	     ……
		if (PageWriteback(page)) {  //跳过该判断
			……
		}

		
		if (PageAnon(page) && PageSwapBacked(page)) { 
			if (!PageSwapCache(page)) {   //跳过该判断
				
			}
		} 

		if (page_mapped(page)) {  //由于在第一次shrink的时候unmap了，所以此时page_mapped等于0，跳过该判断
             ……
		}

		if (PageDirty(page)) {  //跳过该判断
			……
		}
		……
		if (PageAnon(page) && !PageSwapBacked(page)) {   //非lazyfree的页面，走else
	        ……
		} else if (!mapping || !__remove_mapping(mapping, page, true)) //这里进入到__remove_mapping中，把page从swapcache 中移除掉，并清除页槽的第6位，即SWAP_HAS_CACHE
			goto keep_locked;
		……
free_it:
    ……
		list_add(&page->lru, &free_pages);  //把该page加入到free_pages 链表中等待回收
    ……  //接下来的事情就是回收free_pages链表中的所有page，
	return nr_reclaimed;
}
```

以上是整个`swapout`的流程，这里总结一下，第一次去shrink匿名页面时，会先为`page`里的数据分配一块swap分区的存储块，然后发起一个io写请求，请求把`page`的数据写入到这块存储块中，同时把该`page`放入`swap cache` 中，接着返回，并等待io写操作完成，第二次去shrink该`page`时，从`swap cache` 中删除该`page`，并回收它。