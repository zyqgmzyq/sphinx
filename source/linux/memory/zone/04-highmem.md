

## page_address_init

linux-2.6.11

start_kernel --> page_address_init

在支持高端内存的体系结构中，page_address_init()函数初始化高端内存页表池的链表 struct list_head page_address_pool变量,将内存页地址映射表 struct page_address_map page_address_maps[LIST_PKMAP]中的每一个页地址映射结构 page_address_maps[n]都通过其list成员加入到链表page_address_pool中。初始化内存地址槽结构数组static struct page_address_slot page_address_htable[1<<PA_HASH_ORDER(=7)]中的每一个结构变量的链表1h和自旋锁lock，最后初始化高端内存池全局自旋锁pool_lock。

```c

591 void __init page_address_init(void)
592 {
593         int i;
594
595         INIT_LIST_HEAD(&page_address_pool);
596         for (i = 0; i < ARRAY_SIZE(page_address_maps); i++)
597                 list_add(&page_address_maps[i].list, &page_address_pool);
598         for (i = 0; i < ARRAY_SIZE(page_address_htable); i++) {
599                 INIT_LIST_HEAD(&page_address_htable[i].lh);
600                 spin_lock_init(&page_address_htable[i].lock);
601         }
602         spin_lock_init(&pool_lock);
603 }
```

### page_address_pool

第一句代码INIT_LIST_HEAD就是将page_address_pool的前向指针和后续指针都指向了自己。防止指向NULL。

```c
static struct list_head page_address_pool;      /* freelist 静态的双向全局链表，相当于一个全局变量 */
```

### page_address_maps

然后下面是一个for循环，循环的次数就是数组page_address_maps中元素的个数，这个for循环就是将数组page_address_maps中的每一个元素的成员.list添加到全局链表page_address_pool这个全局链表中。

page_address_maps的定义如下：

```c
static struct page_address_map page_address_maps[LAST_PKMAP];
```

struct page_address_map定义如下：

```c
/*
 * Describes one page->virtual association
 */
struct page_address_map {
__struct page *page;
__void *virtual;
__struct list_head list;
};
```

### page_address_htable

page_address_htable也是一个全局变量数组，数组中的每一个元素的格式就是page_address_slot这个结构的格式

```c
505 /*
506  * Hash table bucket
507  */
508 static struct page_address_slot { 
509         struct list_head lh;                    /* List of page_address_maps */
510         spinlock_t lock;                        /* Protect this bucket's list */
511 } ____cacheline_aligned_in_smp page_address_htable[1<<PA_HASH_ORDER];
```

这里__cacheline_aligned_in_smp的定义如下：

```c
#ifndef ____cacheline_aligned_in_smp
#ifdef CONFIG_SMP
#define ____cacheline_aligned_in_smp ____cacheline_aligned
#else
#define ____cacheline_aligned_in_smp
#endif /* CONFIG_SMP */
#endif
```

被它修改的代码段表示在编译的时候地址采用cache访问最快的对其方式来编译，具体多少个字节对齐才是cache访问最快的方式在具体的CPU架构中不一致，cache的设计也不同，因此在不同的架构中其对齐的字节书并不完全相同。**在ARM32中cache line的大小就是32位，因此读写内存都采用的是一个cache line的长度，因此要求4字节对齐，而在ARM64中，则采用16字节对齐。**

现在回到上面的for循环中，这个for循环的主要作用就是依次初始化page_address_htable[i]元素中的自旋锁变量和链表，最后将整个内存池的大自旋锁初始化。这样这个函数就运行结束，主要做了内存池相关的初始化工作。

