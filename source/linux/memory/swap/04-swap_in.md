## Swap核心调用

![image-20220731180623450](D:\work\sphinx-master\source\linux\swap\figs\04-swap_in.assets\image-20220731180623450.png)

当CPU检查一个页目录项/页表项的Present标志位时，如果发现该标志位为0，则表示相应的物理页面不在内存。此时，CPU会被激发“页面异常”（中断中的fault），而去执行一段代码。

**至于到底是这个内存页面需要重新构建、还是页面的内容是存储到磁盘上去了，CPU本身是不关心的，CPU只知道中断条件发生了，要根据中断描述符跳转到另外一段代码去执行，而真正的swap或者是真的缺页的智能判断是在这段中断服务程序里做的——真正的技术是在这段中断服务程序里**。

pte_present()函数会检查当前页面的描述entry的present标志位，查看该page是否在内存中。如果不在内存中，调用pte_none()判断是否建立了页目录、页表映射。如果连映射都没建立，说明是“真没在内存中”，需要从头建立映射关系。如果建立了映射关系，说明此时，该页面被暂时存储到磁盘上去了，应该到磁盘上去把该page取回来放到内存里。

## Swapin

swapin 的入口是`do_swap_page`，由于物理页面被回收了，所以进程再次访问一块虚拟地址时，就会产生缺页中断，最终进入到 `do_swap_page`，在这个函数中会重新分配新的页面，然后再从swap分区读回这块虚拟地址对应的数据。具体请看以下代码分析

```c
int do_swap_page(struct vm_fault *vmf)
{
	……
    // 从pte中获取swap entry，即把orig_pte 强制类型转换成swp_entry_t类型
	entry = pte_to_swp_entry(vmf->orig_pte);  
    ……
    // 在 swap cache 中查找entry 对应的page
	page = lookup_swap_cache(entry, vma, vmf->address);  
	swapcache = page;
    // 如果在swap cache中没找到，则进入if代码段
	if (!page) {  
        // 获取swap分区描述符
		struct swap_info_struct *si = swp_swap_info(entry);  
          ……
			page = swapin_readahead(entry, GFP_HIGHUSER_MOVABLE, vmf);  //分配一个page，并从swap分区中读出数据填充到page中，再把page放入swap cache中缓存，此时page的PG_lock被置位了，需要等待IO读操作完成才清零，即page被lock住，如果别人想lock该page，则需要等待该page被unlock
			swapcache = page;
		……
	}

	locked = lock_page_or_retry(page, vma->vm_mm, vmf->flags);  //此时尝试去lock该page，成功则返回1，失败则返回0
    ….
	if (!locked) {  //显然此时返回是0，即page的IO读操作仍末完成。
		ret |= VM_FAULT_RETRY;  //设置返回标记为retry
		goto out_release; //返回重新尝试 do_swap_page，但在重新尝试do_swap_page时则可以从page cache 中直接获取到该page，不需要再从swap分区中读数据了
	}
     //程序走到这表明该page的IO读操作已经完成

	……
	pte = mk_pte(page, vmf->vma_page_prot);  //根据page的物理地址，以及该page的保护位生成pte
	if ((vmf->flags & FAULT_FLAG_WRITE) && reuse_swap_page(page, NULL)) {  //如果该缺页中断为写访问异常时，并且page只有一个进程使用，则把该page从swap cache 中删除，并清除对应在swap分区中的数据，下面会分析reuse_swap_page函数
		pte = maybe_mkwrite(pte_mkdirty(pte), vmf->vma_flags);  //设置pte中的可写保护位和PTE_DIRTY位
		vmf->flags &= ~FAULT_FLAG_WRITE;
		ret |= VM_FAULT_WRITE;
		exclusive = RMAP_EXCLUSIVE;
	}
	……
	set_pte_at(vma->vm_mm, vmf->address, vmf->pte, pte);  更新该虚拟地址对应的pte
	……
		do_page_add_anon_rmap(page, vma, vmf->address, exclusive);  //建立新的匿名映射
		mem_cgroup_commit_charge(page, memcg, true, false);
		activate_page(page);  //把该page放入active anonymouns lru链表中
	……

	swap_free(entry);  //更新页槽的counter，即减一，如果counter等于0，说明需要该存储块数据的人已经全部读回到内存，并且该page也不在swap cache 中，那么直接清除存储块数据，即回收页槽，释放更多的swap空间
	if (mem_cgroup_swap_full(page) ||
	    (vmf->vma_flags & VM_LOCKED) || PageMlocked(page))
		try_to_free_swap(page);  //如果swap分区满了，则尝试回收无用页槽
	unlock_page(page);  //解锁 PG_lock
	……
out:
	return ret;
   ……
}
```

接下来分析一下两个核心函数 `swapin_readahead` 和 `reuse_swap_page`
`swapin_readahead` 最终会进入`swap_cluster_readahead`函数或者`swap_vma_readahead`函数，两者的区别在于预读的方式，前者是预读 `page` 对应的物理地址前后范围的数据，后者是预读虚拟地址前后范围的数据，其实现上相差不大，所以我们先来分析 `swap_cluster_readahead`，至于另一个函数有兴趣的读者可参考此分析自行查阅代码。

```c
struct page *swap_cluster_readahead(swp_entry_t entry, gfp_t gfp_mask,
				struct vm_fault *vmf)
{
	……
	mask = swapin_nr_pages(offset) - 1;  // 获取需要预读的页槽个数
	if (!mask) 
		goto skip;  //如果不需要预读，则只读当前entry指向的页槽，跳到skip

	do_poll = false;
	/* Read a page_cluster sized and aligned cluster around offset. */
	start_offset = offset & ~mask;  //得到预读开始的页槽
	end_offset = offset | mask;  //得到预读结束的页槽
     ……
	for (offset = start_offset; offset <= end_offset ; offset++) { 从开始的页槽一个个地预读
		/* Ok, do the async read-ahead now */
		page = __read_swap_cache_async(
			swp_entry(swp_type(entry), offset),
			gfp_mask, vma, addr, &page_allocated);  //分配新的page，并放入swap cache，设置PG_swapcache，把entry 保存到page->private变量中，跟随page传递，置位页槽的第6位，即SWAP_HAS_CACHE
……
		if (page_allocated) { //该变量为true，代表page cache中没有页槽对应的page，是重新分配的page，则需要把页槽所指向的swap分区中的数据读出来放到page中。
			swap_readpage(page, false);  //发起io读请求，该实现与swapout时调用的swap_writepage类似，这里不再分析，这里再提醒一下，等待io读操作完成后该page的PG_lock才会被清零，具体的清零操作是在bio的回调函数end_swap_bio_read中完成。读者可回忆一下io写操作完成后清零page的PG_writeback位。
			……
		}
		put_page(page);
	}
     ……
skip:
	return read_swap_cache_async(entry, gfp_mask, vma, addr, do_poll);  //这里只读一个页槽的数据，其实现与上面预读多个页槽的逻辑基本一样，这里不再分析
}
```

`__read_swap_cache_async` 这个函数主要完成以下几个工作

1. 再次从 `swap cache` 查找页槽对应的 `page`，若找到，则直接返回
2. 若仍没有找到，则分配一个新的 `page`，并设置页槽第6位，即 `SWAP_HAS_CACHE`
3. 设置 `page` 的 `PG_lock`，`PG_swapback`，并把`page`加入到 `swap cache` 中
4. 把`page`存入 `inactive anonymouns lru` 链表中
5. 返回`page`的指针

```
struct page *__read_swap_cache_async(swp_entry_t entry, gfp_t gfp_mask,
			struct vm_area_struct *vma, unsigned long addr,
			bool *new_page_allocated)
{
	do {
		found_page = find_get_page(swapper_space, swp_offset(entry));  //第一步
		if (found_page)
			break;
         ……
		if (!new_page) {
			new_page = alloc_page_vma(gfp_mask, vma, addr);   //第二步中分配新的page
			if (!new_page)
				break;		/* Out of memory */
		}

		……
		err = swapcache_prepare(entry);  //第二步中的设置页槽第6位
		……
		/* May fail (-ENOMEM) if radix-tree node allocation failed. */
		__SetPageLocked(new_page);   //第三步
		__SetPageSwapBacked(new_page);  //第三步
		err = __add_to_swap_cache(new_page, entry);  //第三步中的加入page到swap cache中
		if (likely(!err)) {
              ……
			lru_cache_add_anon(new_page);  //第四步
			*new_page_allocated = true;
			return new_page;  //第5步,返回page指针
		}
		……
	} while (err != -ENOMEM);

	if (new_page)
		put_page(new_page);
	return found_page;
}
```

接下来看另一个核心函数 `reuse_swap_page`，该函数的作用是尝试把只有一个进程使用的页槽回收掉。

```
bool reuse_swap_page(struct page *page, int *total_map_swapcount)
{
	……
	count = page_trans_huge_map_swapcount(page, &total_mapcount, &total_swapcount); //获取所有使用该paga的进程数量，返回count为总数量，total_mapcount为已经与虚拟地址map 的进程数量，total_swapcount 为还没与虚拟地址map 的数量
	if (total_map_swapcount)
		*total_map_swapcount = total_mapcount + total_swapcount;  //更新形参total_map_swapcount
	if (count == 1 && PageSwapCache(page) &&
	    (likely(!PageTransCompound(page)) ||
	     /* The remaining swap count will be freed soon */
	     total_swapcount == page_swapcount(page))) {  //这里的判断有三个，分别是使用该page的进程总数为1，即只有一个进程使用; 该page是在swap cache 中; 当前进程的虚拟地址仍没有与该page建立映射，即仍未map。当这三个条件都满足时则认为该页槽指向的存储块数据再也不需要了，可以清除掉。
		if (!PageWriteback(page)) {  //该page是否正在回写磁盘，如果已经回写完成则回收页槽，否则走else，返回false，表明页槽没回收成功。
			page = compound_head(page); 
			delete_from_swap_cache(page);  //从swap cache中删除，并回收页槽
			SetPageDirty(page);  //把page的PG_dirty位置1
		} else {
			swp_entry_t entry;
			struct swap_info_struct *p;

			entry.val = page_private(page);
			p = swap_info_get(entry);
			if (p->flags & SWP_STABLE_WRITES) {
				spin_unlock(&p->lock);
				return false;
			}
			spin_unlock(&p->lock);
		}
	}

	return count <= 1;
}
```

`delete_from_swap_cache` 这个函数其实有两部分组成，`__delete_from_swap_cache`和put_swap_page，`__delete_from_swap_cache`函数是从`swap cache` 中删除一个`page`的核心函数，`put_swap_page`功能是把页槽所指向的存储块数据清除。