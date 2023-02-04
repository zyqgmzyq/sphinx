# Linux中匿名页的反向映射

参考：

 https://lwn.net/Articles/383162/

http://liujunming.top/2017/09/03/Linux%E4%B8%AD%E5%8C%BF%E5%90%8D%E9%A1%B5%E7%9A%84%E5%8F%8D%E5%90%91%E6%98%A0%E5%B0%84/

Linux提供了内存映射这一特性，它实现了把物理内存页映射(map)到进程的地址空间中, 以实现高效的数据操作或传输。内核在处理这一特性时, 使用了`struct vm_area_struct`, `struct anon_vma`和`struct anon_vma_chain`这三个重要数据结构, 所以理解这三个数据结构是重中之重,　本文试图厘清这三者的来历与联系。

## vma

[struct vm_area_struct](http://elixir.free-electrons.com/linux/v2.6.35.14/source/include/linux/mm_types.h#L130) 在内核代码中常被简称为`vma`, 所以下文以`vma`指称这一结构。

`vma`是内存映射的单位, 它表示进程地址空间中的一个连续的区间, 其中字段`vm_start`和`vm_end`标明这块连续区间的起始虚拟地址。在使用`mmap`系统调用创建映射时, 用户指定**起始地址(可选)**和**长度**, 内核将据此寻找进程地址空间中符合条件的合法`vma`以供映射。`cat /proc/<pid>/maps`可以查看某一进程的所有映射区间。

```c
struct vm_area_struct {
    unsigned long vm_start;     /* Our start address within vm_mm. */
	unsigned long vm_end;       /* The first byte after our end address within vm_mm. */
    struct rb_node vm_rb;
    struct mm_struct *vm_mm;    /* The address space we belong to. */
	pgprot_t vm_page_prot;      /* Access permissions of this VMA. */
	unsigned long vm_flags;     /* Flags, see mm.h. */
    /*
      * For areas with an address space and backing store,
      * linkage into the address_space->i_mmap interval tree.
      */
     struct {
         struct rb_node rb;
         unsigned long rb_subtree_last;
     } shared; /* shared是用于文件页的反向映射 */

     /*
      * A file's MAP_PRIVATE vma can be in both i_mmap tree and anon_vma
      * list, after a COW of one of the file pages.  A MAP_SHARED vma
      * can only be in the i_mmap tree.  An anonymous MAP_PRIVATE, stack
      * or brk vma (with NULL file) can only be in an anon_vma list.
      * anno_vma_node和anon_vma用于管理源自匿名映射的共享页
      */
     struct list_head anon_vma_chain; /* Serialized by mmap_sem & page_table_lock */
     struct anon_vma *anon_vma;       /* Serialized by page_table_lock */

     /* Function pointers to deal with this struct. */
     const struct vm_operations_struct *vm_ops;
}
```

## anon_vma

```c
 29 struct anon_vma {
 30     struct anon_vma *root;      /* Root of this anon_vma tree */
 31     struct rw_semaphore rwsem;  /* W: modification, R: walking the list */
 32     /*
 33      * The refcount is taken on an anon_vma when there is no
 34      * guarantee that the vma of page tables will exist for
 35      * the duration of the operation. A caller that takes
 36      * the reference is responsible for clearing up the
 37      * anon_vma if they are the last user on release
 38      */
 39     atomic_t refcount;
 40
 41     /*
 42      * Count of child anon_vmas and VMAs which points to this anon_vma.
 43      *
 44      * This counter is used for making decision about reusing anon_vma
 45      * instead of forking new one. See comments in function anon_vma_clone.
 46      */
 47     unsigned degree;
 48
 49     struct anon_vma *parent;    /* Parent of this anon_vma */
 50
 51     /*
 52      * NOTE: the LSB of the rb_root.rb_node is set by
 53      * mm_take_all_locks() _after_ taking the above lock. So the
 54      * rb_root must only be read/written after taking the above lock
 55      * to be sure to see a valid next pointer. The LSB bit itself
 56      * is serialized by a system wide lock only visible to
 57      * mm_take_all_locks() (mm_all_locks_mutex).
 58      */
 59
 60     /* Interval tree of private "related" vmas  */
 61     struct rb_root_cached rb_root; /* rb_root链接了所有与这个anon_vma相关的vma，反向映射时只要遍历它即可 */
 62 };
```

[anon_vma](http://elixir.free-electrons.com/linux/v2.6.35.14/source/include/linux/rmap.h#L27)的引入需要一番解释。

### 反向映射的引入

当Linux系统内存不足时, swap子系统会释放一些页面, 交换到交换设备中, 以空出多余的内存页。虚拟内存的理念就是通过**页表**来维护虚拟地址到物理地址的映射。但是, **页表**是种**单向映射**, 即通过虚拟地址查找物理地址很容易,　但反之通过物理地址查找虚拟地址则很麻烦。这种问题在共享内存的情况下更加严重。而swap子系统在释放页面时就遇到这个问题, 对于特定页面(物理地址), 要找到映射到它的`页表项(PTE)`, 并修改**PTE**, 以使其指向交换设备中的该页的位置。在2.4之前的内核中, 这是件费时的工作, 因为内核需要遍历每一个进程的所有页表, 以找出所有映射该页的页表项。

解决这一问题的做法是引入**反向映射(reverse mapping)**这一概念。该做法就是为每一个内存页(`struct page`)维护一个数据结构, 其中包含所有映射到该页的`PTE`, 这样在寻找一个内存页的反向映射时只要扫描这个结构即可, 大大提高了效率。这正是Rik van Riel的做法, 他在`struct page`中增加了一个`pte_chain`的字段, 它是一个指向所有映射到该页的PTE的链表指针。

当然, 它是有代价的。

- 每个`struct page`都增加了一个字段, 而系统中每个内存页都对应一个`struct page`结构, 这意味着相当数量的内存被用来维护这个字段。而`struct page`是重要的内核数据结构, 存放在有限的低端内存中, 增加一个字段浪费了大量的保贵低端内存, 而且, 当物理内存很大时, 这种情况更突出, 这引起了**伸缩性(scalability)**问题。
- 其它一些需要操作大量页面的函数慢下来了。`fork()`系统调用就是一个。由于Linux采取**写时复制(COW, Copy On Write)**的语义, 意味着新进程共享父进程的页表, 这样, 进程地址空间内的所有页都新增了一个PTE指向它, 因此, 需要为每个页新增一个反向映射, 这显著地拖慢了速度。

### 基于对象的反向映射

这种代价显然是不能容忍的, 于是, Dave McCracken提出了一个叫做**基于对象的反向映射(object-based reverse mapping)**的解决方案。他的观察是, 前面所述的代价来源于反向映射字段的引入, 而如果存在可以从`struct page`中获取映射到该页面的所有页表项, 这个字段就不需要了, 自然不需要付出这些代价。他确实找到了一种方法。

Linux的用户态内存页大致分**两种使用情况**:

- 其中一大部分叫做**文件后备页(file-backed page)**, 顾名思义, 这种内存页的内容关联着后备存储系统中的文件, 比如程序的代码, 比如普通的文本文件, 这种内存页使用时一般通过上述的`mmap`系统调用映射到地址空间中, 并且, 在内存紧张时, 可以简单地丢弃, 因为可以从后备文件中轻易的恢复。
- 一种叫**匿名页(anonymous page)**, 这是一种普通的内存页, 比如栈或堆内存就属于这种, 这种内存页没有后备文件, 这也是其称为**匿名**的缘故。

Dave的方案中的**对象**指的就是第一种内存页的**后备文件**。他通过**后备文件对象**, 以迂回的方式算出PTE,在本文中就不做过多的介绍。

### 匿名页的反向映射

Dave的方案只解决了第一种内存页的反向映射, 于是, Andrea Arcangeli顺着Dave的思路, 给出了匿名页的反向映射解决方案。

如前所述, 匿名页没有所谓的**后备文件**, 但是, 匿名页有个特点, 就是它们都是私有的, 而非共享的(比如栈, 椎内存都是独立每个进程的, 非共享的)。这意味着, **每一个匿名内存页, 只有一个PTE关联着它, 也就是只有一个vma关联着它**。Andrea的方案是复用`struct page`的`mapping`字段, 因为对于匿名页, `mapping`为`null`, 不指向后备空间。复用方法是利用C语言的`union`, 在匿名页的情况下,`mapping`字段不是指向`struct address_space`的指针, 而是指向关联该内存页的唯一的`vma`。由此, 也可以方便地计算出PTE来。

但是, 事情并不是如此简单。当进程被fork复制时, 前面已经说过, 由于COW的语义, 新进程只是复制父进程的页表, 这意味着现在**一个匿名页有两个页表指向它了**, 这样, 上面的简单复用`mapping`字段的做法不适用了, 因为一个指针, 如何表示两个vma呢。

Andrea的做法就是**多加一层**。新创建一个`struct anon_vma`结构, 现在`mapping`字段是指向它了, 而`anon_vma`中, 不出意料的, 包含一个链表, 链接起所有的`vma`。每当进程fork一个子进程, 子进程由于COW机制会复制父进程的`vma`, 这个新`vma`就链接到父进程中的`anon_vma`中。这样, 每次unmap一个内存页时, 通过`mapping`字段指向的`anon_vma`, 就可以找到可能关联该页的`vma`链表, 遍历该链表, 就可以找到所有映射到该匿名页的PTE。

[![img](http://liujunming.top/images/2017/9/1.png)](http://liujunming.top/images/2017/9/1.png)

这也有代价, 那就是

- 每个`struct vm_area_struct`结构多了一个`list_head`结构字段用以串起所有的`vma`。
- 需要额外为`anon_vma`结构分配内存。

但是, 这种方案所需要的内存远小于前面所提的在每个`struct page`中增加一个反向映射字段来得少, 因此是可以接受的。

以上, 便介绍完了`anon_vma`结构的来由和作用。

总结一下，其实就是每个page上有一个anon_vma树，存了所有可能映射了该page的VMA.

为什么是可能映射了呢？  因为假设fork场景下，vma1只读映射了page1, 但是faultin时发生了COW，那么VMA1就会重新映射到page2. 但是此时也不会把VMA1从page1的anon_vma中移除。

## anon_vma_chain

`anon_vma`结构的提出, 完善了反向映射机制, 一路看来, 无论是效率还是内存使用, 都有了提升, 应该说是很完美的一套解决方案。但现实不断提出难题。一开始提到的Rik van Riel就举了一种工作负载(workload)的[例子](http://git.kernel.org/cgit/linux/kernel/git/torvalds/linux.git/commit/?id=5beb49305251e5669852ed541e8e2f2f7696c53e)来反驳说该方案有缺陷。

前面的匿名页反向映射机制在解除一页映射时, 通过访问`anon_vma`访问`vma`链表, 遍历整个`vma`链表, 以查找可能映射到该页的PTE。但是, 这种方法忽略了一点: **当进程fork而复制产生的子进程中的`vma`如果发生了写访问, 将会分配新的匿名页, 把该`vma`指向这个新的匿名页, 这个`vma`就跟原来的那个匿名页没有关系了, 但原来的`vma`链表却没反映出这种变化, 从而导致了对该`vma`不必要的检查。** Rik举的例子正是对这种极端情况的描述。

Rik采取的方案是又增加一层, 新增了一个结构叫[anon_vma_chain](http://elixir.free-electrons.com/linux/v2.6.35.14/source/include/linux/rmap.h#L65):

```c
 64 /*
 65  * The copy-on-write semantics of fork mean that an anon_vma
 66  * can become associated with multiple processes. Furthermore,
 67  * each child process will have its own anon_vma, where new
 68  * pages for that process are instantiated.
 69  *
 70  * This structure allows us to find the anon_vmas associated
 71  * with a VMA, or the VMAs associated with an anon_vma.
 72  * The "same_vma" list contains the anon_vma_chains linking
 73  * all the anon_vmas associated with this VMA.
 74  * The "rb" field indexes on an interval tree the anon_vma_chains
 75  * which link all the VMAs associated with this anon_vma.
 76  */
 77 struct anon_vma_chain {
 78     struct vm_area_struct *vma;
 79     struct anon_vma *anon_vma;
 80     struct list_head same_vma;   /* locked by mmap_sem & page_table_lock */
 81     struct rb_node rb;           /* locked by anon_vma->rwsem */
 82     unsigned long rb_subtree_last;
 83 #ifdef CONFIG_DEBUG_VM_RB
 84     unsigned long cached_vma_start, cached_vma_last;
 85 #endif
 86 };
```

每个`anon_vma_chain`（AVC）维护两个链表

- same_vma：与给定`vma`相关联的所有`anon_vma`
- rb：线段树上的index, 能够找到与给定`anon_vma`相关联的所有`vma`，2.6 版本上实现是same_anon_vma链表



一般struct anon_vma称为AV，struct anon_vma_chain称为AVC，struct vm_area_struct称为VMA，page找到VMA的路径一般如下：page->AV->AVC->VMA，其中AVC起到桥梁作用，至于为何需要AVC，主要考虑当父进程和多个子进程同时拥有共同的page时的查询效率，具体对比2.6版本时的实现方式。

page通过mapping找到VMA，VMA 遍历自己管理的红黑树rb_root，找到树上的每个节点AVC，AVC通过成员指针anon_vma找到对应的VMA，这个过程就完成了页表映射查找。需要注意的几点：

1.VMA中也有链表anon_vma_chain管理各个AVC，这里主要用在父子进程之间的管理，下文会详细介绍。

2.VMA中有成员指针成员anon_vma，同时AVC中也有成员指针anon_vma，VAC起到桥梁作用所以可以指向VMA和AVC，那VMA中为何又需要指向AV呢？进程创建的流程中一般都是新建AV，然后创建AVC及AMV，然后调用anon_vma_chain_link建立三者之间的关系，但是当一个VMA没有对应页的时候，此时触发pagefault，这里可以快速判断VMA有没有对应的page。



![image-20221113175454280](D:\work\sphinx-master\source\linux\memory\vma\figs\vma, anon_vma和anon_vma_chain.assets\image-20221113175454280.png)

## do_anonymous_page

首先出场的是函数do_anonymous_page，这个函数是在匿名页缺页中断时会调用的函数。

```c
do_anonymous_page(vmf)
    /* 调用 anon_vma_prepare 分配anon_vma和anon_vma_chain结构 */
    anon_vma_prepare
		__anon_vma_prepare(vma)
            avc = anon_vma_chain_alloc()             /* alloc a avc */
            anon_vma = find_mergeable_anon_vma(vma)  /* find or alloc a anon_vma */
            anon_vma = anon_vma_alloc()
            vma->anon_vma = anon_vma                 /* 把vma的anon_vma指针指向anon_vma  */
            anon_vma_chain_link(vma, avc, anon_vma)
    /* 
     * 接着调用 page_add_new_anon_rmap，
     * 这个函数内又会调用__page_set_anon_rmap为page页建立反向映射关系，
     * 主要就是设置page页的mapping和index两个字段 
     */
    page_add_new_anon_rmap
    	__page_set_anon_rmap
    		anon_vma = (void *) anon_vma + PAGE_MAPPING_ANON;
			page->mapping = (struct address_space *) anon_vma;
			page->index = linear_page_index(vma, address);
```

从上面的流程可以看出，当发生缺页中断时，内核会给对应的vma构造anon_vma，并且利用avc去链接这两者。这种可以说是系统中最简单的例子。

细心的人可能已经看到了，上面有一种情况是find_mergeable_anon_vma。如果这个函数返回一个可以重用的anon_vma，那么内核就可以利用原有的anon_vma了。

anon_vma_chain_link函数用于建立anon_vma、anon_vma_chain、vma三者之间的关系，主要就是把avc->same_vma挂入vma->anon_vma_chain链表中，把avc->rb挂入anon_vma->rb_root树中

```c
 137 static void anon_vma_chain_link(struct vm_area_struct *vma,
 138                 struct anon_vma_chain *avc,
 139                 struct anon_vma *anon_vma)
 140 {
 141     avc->vma = vma;
 142     avc->anon_vma = anon_vma;
 143     list_add(&avc->same_vma, &vma->anon_vma_chain);
 144     anon_vma_interval_tree_insert(avc, &anon_vma->rb_root);
 145 }
```

![image-20221113185048709](D:\work\sphinx-master\source\linux\memory\vma\figs\vma, anon_vma和anon_vma_chain.assets\image-20221113185048709.png)

## anon_vma_fork

看过了在单个进程中的情况，接下来我们来看看创建一个子进程时如何调整这个数据结构。这个过程由anon_vma_fork处理。

```javascript
    anon_vma_fork(vma, pvma)
        anon_vma_clone(vma, pvma)
        anon_vma = anon_vma_alloc()
        avc = anon_vma_chain_alloc()
        anon_vma->root = pvma->anon_vma->root
        anon_vma->parent = pvma->anon_vma
        vma->anon_vma = anon_vma
        anon_vma_chain_link(vma, avc, anon_vma)
```

这个函数很有意思，我还真是花了些时间去理解它。最开始有点看不清，所以我干脆退回到最简单的状态，也就是当前进程是根进程的时候。此时我才大致的了解了一点fork时究竟发生了什么。