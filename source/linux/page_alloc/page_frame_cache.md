# page frame cache

linux源码为2.6.11

在系统运行过程中，Kernel经常会有单个页面的申请和释放操作。为了进一步提高性能, Kernel采用了这样一种cache机制：

Memory zone为每个CPU定义了page frame cache。Kernel会在适当的时机提前从buddy system中分配好若干单页，放在这些cache中。以后Kernel若要申请单个页面，直接从cache中拿一个就可以了，不用再去和buddy system打交道。

实际上，memory zone为每个CPU定义了两个page frame cache。一个hot cache，一个cold cache。hot还是cold，主要是相对于CPU的缓存来说的。

一般来说，从hot cache中分配页面可以提高系统性能，因为该页面的内容很可能还保存在CPU缓存中。

那cold cache有什么用呢？这个cache中的page frame一般用在DMA操作中。我们知道，DMA操作不涉及CPU，所以也就不涉及CPU缓存，因此用于DMA操作的page frame就没必要从hot cache中分配。从cold cache中为DMA分配page frame有助于保持hot cache中的页面还是hot的。

好了，让我们来看一看这个cache机制是如何实现的。

## 数据结构

memory zone的描述符中，有这样一个成员变量

```c
struct zone {
    ...
    
    struct per_cpu_pageset  pageset[NR_CPUS];   
    ...
}
```
这个就是为每个CPU准备的page frame cache。

```c
 53 struct per_cpu_pageset {
 54         struct per_cpu_pages pcp[2];    /* 0: hot.  1: cold */
 55 #ifdef CONFIG_NUMA
 56         unsigned long numa_hit;         /* allocated in intended node */
 57         unsigned long numa_miss;        /* allocated in non intended node */
 58         unsigned long numa_foreign;     /* was intended here, hit elsewhere */
 59         unsigned long interleave_hit;   /* interleaver prefered this zone */
 60         unsigned long local_node;       /* allocation from local node */
 61         unsigned long other_node;       /* allocation from other node */
 62 #endif
 63 }____cacheline_aligned_in_smp;
```
可见每个CPU有两个cache: hot and cold。

```c
 45 struct per_cpu_pages {
 46         int count;              /* number of pages in the list */
 47         int low;                /* low watermark, refill needed */
 48         int high;               /* high watermark, emptying needed */
 49         int batch;              /* chunk size for buddy add/remove */
 50         struct list_head list;  /* the list of pages */
 51 };
```

每个cache的结构非常简单。Kernel提前从buddy system中分配好的单个页面放在list中，list里包含的页面个数保存在count中。

每次申请和释放单个页面时，Kernel都会check一下count值：在申请单个页面时，如果发现count的值为0，则会填充cache；在释放单个页面后，如果发现count的值大于等于high watermark，则会缩减cache。每次填充或缩减一个batch的量。

之前讲过了buddy system算法是如何分配和释放一个页块的。那么增加了per-cpu page frame cache之后，分配和释放页块时会有哪些不同呢？

## 分配page

分配一个page是由函数buffered_rmqueue来完成的。它主要利用__rmqueue来从buddy system中申请内存页块，不过当申请单个页面时，它会利用per-cpu page frame cache。

如果申请的是单个页面，那么Kernel就会使用per-cpu page frame cache。当然在从cache中拿page frame之前，会check一下，如果cache已经空了，就需要先填充cache。填充的工作由函数rmqueue_bulk来完成。这个函数非常简单，就是利用__rmqueue从buddy system中申请batch个单个页面放进cache中。如果填充过后cache依旧为空，说明内存已经非常短缺，返回NULL。
如果cache不为空，则从cache中拿出一个page frame。

__alloc_pages --> buffered_rmqueue

```c
 616 static struct page *
 617 buffered_rmqueue(struct zone *zone, int order, int gfp_flags)
 618 {
 619         unsigned long flags;
 620         struct page *page = NULL;
 621         int cold = !!(gfp_flags & __GFP_COLD); /* 使用hot cache还是cold cache是由__GFP_COLD位来决定的 */
 622
 623         if (order == 0) {
 624                 struct per_cpu_pages *pcp;
 625				 /* 拿到对应的pcp指针,注意：get_cpu会关抢占，确保不会被调度出去 */
 626                 pcp = &zone->pageset[get_cpu()].pcp[cold];  
 627                 local_irq_save(flags);            /* 关中断 */
 628                 if (pcp->count <= pcp->low)       /* pcp中的页数量低于low水线则填充pagelist */
 629                         pcp->count += rmqueue_bulk(zone, 0,
 630                                                 pcp->batch, &pcp->list);
 631                 if (pcp->count) {
 632                         page = list_entry(pcp->list.next, struct page, lru);
 633                         list_del(&page->lru);
 634                         pcp->count--;
 635                 }
 636                 local_irq_restore(flags);         /* 恢复中断 */
 637                 put_cpu();                        /* 恢复抢占 */
 638         }
 639         /* 上面是针对申请单个页面的情况。如果申请多个页面，则利用__rmqueue从buddy system中申请。 */
 640         if (page == NULL) {
 641                 spin_lock_irqsave(&zone->lock, flags);
 642                 page = __rmqueue(zone, order);
 643                 spin_unlock_irqrestore(&zone->lock, flags);
 644         }
 645         
 646         if (page != NULL) {
 647                 BUG_ON(bad_range(zone, page));
 648                 mod_page_state_zone(zone, pgalloc, 1 << order);
 649                 prep_new_page(page, order);
 650
 651                 if (gfp_flags & __GFP_ZERO)
 652                         prep_zero_page(page, order, gfp_flags);  /* 零页则清零操作 */
 653
 654                 if (order && (gfp_flags & __GFP_COMP))
 655                         prep_compound_page(page, order);
 656         }
 657         return page;
 658 }
```

## 释放page

释放一个page是由函数__free_pages来完成的。它主要利用我们讲过的__free_one_page来把内存页块放回到buddy system中，不过当释放单个页面时，它会把页面放回per-cpu page frame cache。

```c
 900 fastcall void __free_pages(struct page *page, unsigned int order)
 901 {
 902         if (!PageReserved(page) && put_page_testzero(page)) {
 903                 if (order == 0)
 904                         free_hot_page(page);
 905                 else
 906                         __free_pages_ok(page, order);
 907         }
 908 }
```

与per-cpu page frame cache打交道的是函数free_hot_page。

```c
 568 static void FASTCALL(free_hot_cold_page(struct page *page, int cold));
 569 static void fastcall free_hot_cold_page(struct page *page, int cold)
 570 {
 571         struct zone *zone = page_zone(page);
 572         struct per_cpu_pages *pcp;
 573         unsigned long flags;
 574
 575         arch_free_page(page, 0);
 576
 577         kernel_map_pages(page, 1, 0);
 578         inc_page_state(pgfree);
 579         if (PageAnon(page))
 580                 page->mapping = NULL;
 581         free_pages_check(__FUNCTION__, page);
 582         pcp = &zone->pageset[get_cpu()].pcp[cold];  /* 获取pcp */
 583         local_irq_save(flags);
 584         if (pcp->count >= pcp->high)   /* cache的pagelist中的页数量大于high水线则缩减cache */
 585                 pcp->count -= free_pages_bulk(zone, pcp->batch, &pcp->list, 0);
 586         list_add(&page->lru, &pcp->list);
 587         pcp->count++;
 588         local_irq_restore(flags);
 589         put_cpu();
 590 }
 591
 592 void fastcall free_hot_page(struct page *page)
 593 {
 594         free_hot_cold_page(page, 0);   /* free到hot pagelist */
 595 }
 596
```

这个函数逻辑非常简单，把要释放的页面放到cache中。然后检查cache的大小。

如果cache的count值大于等于high watermark, 则利用函数free_pages_bulk来缩减cache。free_pages_bulk利用__free_one_page把batch个单个页面放回到buddy system中。

在操作per-cpu page frame cache时，有个小细节很有意思。**在cache的list中拿出和放回一个page frame都是从链表的头部进行的，这样就形成了一个LIFO的stack。而free_pages_bulk缩减cache时，是从链表的尾部开始的，这个很像LRU的思想。这个小的细节可以尽量保证cache中page frame的hot。**

## **什么是冷热页？** 

冷页表示该空闲页已经不再高速缓存中了(一般是指L2 Cache)，**热页表示该空闲页仍然在高速缓存中。冷热页是针对于每CPU的，每个zone中，都会针对于所有的CPU初始化一个冷热页的per-cpu-pageset.** 

### **为什么要有冷热页？** 

**作用有3点：**

- Buddy Allocator在分配order为0的空闲页的时候，**如果分配一个热页，那么由于该页已经存在于L2 Cache中了。CPU写访问的时候，不需要先把内存中的内容读到Cache中，然后再写。**如果分配一个冷页，说明该页不在L2 Cache中。一般情况下，尽可能用热页，是容易理解的。什么时候用冷页呢？While allocating a physical page frame, there is a bit specifying whether we would like a hot or a cold page (that is, a page likely to be in the CPU cache, or a page not likely to be there). If the page will be used by the CPU, a hot page will be faster. If the page will be used for device DMA the CPU cache would be invalidated anyway, and a cold page does not waste precious cache contents.  简单翻译一下：当内核分配一个物理页框时，有一些规范来约束我们是分配热页还是冷页。当页框是CPU使用的，则分配热页。当页框是DMA设备使用的，则分配冷页。因为DMA设备不会用到CPU高速缓存，所以没必要使用热页。

- Buddy System在给某个进程分配某个zone中空闲页的时候，首先需要用自旋锁锁住该zone,然后分配页。**如果多个CPU上的进程同时进行分配页，便会竞争。**引入了per-cpu-set后，当多个CPU上的进程同时分配页的时候，竞争便不会发生，提高了效率。**另外当释放单个页面时，空闲页面首先放回到per-cpu-pageset中，以减少zone中自旋锁的使用。**当页面缓存中的页面数量超过阀值时，再将页面放回到伙伴系统中。

- 使用每CPU冷热页还有一个好处是，**能保证某个页一直黏在1个CPU上，这有助于提高Cache的命中率**。

### **冷热页的数据结构**

以下为linux4.19源码：

```c
 struct per_cpu_pages {
  int count;    // number of pages in the list
  int high;     // high watermark, emptying needed
  int batch;    // chunk size for buddy add/remove
   // Lists of pages, one per migrate type stored on the pcp-lists
   /* 每个CPU在每个zone上都有MIGRATE_PCPTYPES个冷热页链表（根据迁移类型划分）*/
   struct list_head lists[MIGRATE_PCPTYPES];
 }; 
```

在Linux中，对于UMA的架构，**冷热页是在一条链表上进行管理**。热页在前，冷页在后。CPU每释放一个order为0的页，如果per-cpu-pageset中的页数少于其指定的阈值，便会将释放的页插入到冷热页链表的开始处。这样，之前插入的热页便会随着其后热页源源不断的插入向后移动，其页由热变冷的几率便大大增加。

### **怎样分配冷热页** 

在分配order为0页的时候(冷热页机制只处理单页分配的情况)，先找到合适的zone,然后根据需要的migratetype类型定位冷热页链表（每个zone，对于每个cpu,有3条冷热页链表，对应于：MIGRATE_UNMOVABLE、MIGRATE_RECLAIMABLE、MIGRATE_MOVABLE）。若需要热页，则从链表头取下一页（此页最“热”）；若需要冷页，则从链表尾取下一页（此页最“冷”）。
