# swap

## swap整体架构

Linux Swap 机制的整体层级架构如下图所示
![层级架构](https://img-blog.csdnimg.cn/20190321155035900.png?x-oss-process=image/watermark,type_ZmFuZ3poZW5naGVpdGk,shadow_10,text_aHR0cHM6Ly9ibG9nLmNzZG4ubmV0L3FraGh5Z2EyMDE2,size_16,color_FFFFFF,t_70)
整套机制是基于内存管理之下建立的，由于swap会对磁盘进行读写，所以设计上与pagecache 相类似地建立了一个 swap cache 的缓存，提高swap的读写效率。这里的swap core 指的是swap的核心层，主要完成管理各个swap分区，决策内存数据需要交换到哪个磁盘上，以及发起读写请求的工作。

当内存管理模块需要回收一个匿名页面的时候，首先先通过swap core 选择合适的swap 分区，并修改pte，指向swap entry的pte，同时把该页面加入到 swap cache 缓存起来，然后再通过swap core 发起回写请求进行回写，等待回写结束后，内存管理模块释放该页面。当用户需要访问处于swap分区的数据时，首先先通过内存管理模块确定pte的swap entry，然后在swap cache 中快速地查找swap entry 对应的物理页面，如果这时物理页面仍末被回收，就能找到对应的页面，则直接修改pte，指向该page，重新建立映射，如果没找到对应的页面，表明物理页面已经被回收了，则在swap core 中通过 swap entry 查找对应的swap 分区和数据地址，最后申请一个page并发起读操作，等待读操作完成后，修改pte，指向该page，重新建立映射。

以上描述的两个过程中，关键点有以下几个：

1. Swap entry 的数据结构，也就是说 swap core 是怎么组织 swap entry ，又是怎么通过swap entry找到对应在swap分区的数据的。
2. Swap cache 存储结构，即swap cache 是如何存储各个匿名页面的
3. Page 的几个标志位，PG_writeback, PG_swapcache, PG_locked，这些标志位在交换过程中有着非常重要的作用，决定了page的生命周期。

带着以上几个关键点，我们来从细节上了解整个swap世界。

## 与内存管理的联系

在内核线程中，有一个专门用来回收物理页面的线程叫kswapd，它主要的工作之一就是寻找满足回收条件的匿名页面和文件页面，然后回收它们，当然回收他们之前就需要把物理页面的数据保存起来，这个过程称之为交换（以下称swap），文件页面自然而然地就有对应的磁盘保存位置，而对于匿名页面来说，即其数据原本不在磁盘上的情况，我们就需要用到swap分区去保存。所以swap分区只适合交换匿名页面的数据。

从整个 linux 系统内存回收的角度来看的话，我们可以这么认为，如果系统开启了 swap 机制并且用户通过 swapon 指定了 swap 分区，那么内存回收时将会回收匿名页面，否则只会回收文件页面。
我们先初步来了解一下内存回收的入口，所有的内存回收路径最终都会走到以下函数

```
shrink_page_list(struct list_head *page_list, struct pglist_data *pgdat, struct scan_control *sc, enum ttu_flags ttu_flags, struct reclaim_stat *stat, bool force_reclaim)
```

初步被选出来的系统认为满足条件的页面放在 `page_list` 这个链表中，至于如何选择满足条件的页面，是由内存回收算法LRU决定，这是内存管理方面的知识，这里不作详细地描述。在这个函数中会对 `page_list` 链表中所有的页面逐一处理，若是匿名的并且没有被 swap cache 缓存的页面，通过 `add_to_swap` 函数通知 swap core 和 swap cache 把该页面的数据交换出内存，随后在 `try_to_unmap` 函数中修改该 page 对应的 `pte`，使其指向 swap entry 的 `pte`。因此 `add_to_swap` 函数则是 swap core 和 swap cache 与内存回收之间的桥梁。

而另外的桥梁则是发生在缺页中断中，当进程访问的数据不在物理内存时会进入到缺页中断中，在该中断里，先去判断产生缺页中断的 `pte` 是否是 swap entry，如果是则调用 `do_swap_page` 函数把数据从磁盘上交换回内存中。

因此swap core 和 swap cache 与 memory management 之间的桥梁主要有两个，如下表所述

| 函数         | 功能                                                         | 调用时机   |
| ------------ | ------------------------------------------------------------ | ---------- |
| add_to_swap  | 把一个page放入swap cache 的缓存中，并分配一个 swp_entry_t 类型的swap entry，然后绑定该page | 内存回收时 |
| do_swap_page | 在 swap cache 缓存中寻找对应 swap entry 的page，如果找不到则从swap分区中读出数据，并与虚拟内存地址进行映射 | 缺页中断时 |


