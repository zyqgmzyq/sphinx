# Fork

二者区别？
fork要创建一个新的进程空间，拷贝父进程的进程环境；而vfork直接使用父进程的虚拟空间，物理页也共享，在子进程没有调用exec和exit之前，子进程与父进程共享进程环境，相当于线程的概念，此时父进程阻塞等待；
vfork保证子进程先运行，在它调用exec或exit之后父进程才可能被调度运行。如果在调用这两个函数之前子进程依赖于父进程的进一步动作，则会导致死锁。

为什么会引入vfork?
使用fork（还未实现COW时）创建一个子进程时，将会创建一个新的地址空间，并且拷贝父进程的资源，然后紧接着调用一个exec执行一个新的代码段，使得之前fork复制的空间全部变成了无用功；
当进程调用exec函数时，一个新程序替换了当前进程的数据，堆和栈段。这样，前面的拷贝工作就是白费力气了 ->  引出vfork
vfork并不复制父进程的进程环境，子进程在父进程的地址空间中运行，所以子进程不能进行写操作，并且在子进程使用父进程的地址空间时，父进程只能被挂起；一旦子进程执行了exec后，相当于创建一个新进程来代替调用进程自身；
因此，如果创建子进程是为了调用exec执行一个新的程序的时候，就应该使用vfork

(v)fork + exec：fork产生一个新进程，exec将这个由fork产生的进程替换为我们需要的进程。
B调用exec系列系统调用，通过load_elf_binary将B进程对应的可执行文件加载到B的内存空间中执行

exec是一组函数：
包含 p 的函数（execvp, execlp）会在 PATH 路径下面寻找程序；
不包含 p 的函数需要输入程序的全路径；
包含 v 的函数（execv, execvp, execve）以数组的形式接收参；
包含 l 的函数（execl, execlp, execle）以列表的形式接收参数
包含 e 的函数（execve, execle）以数组的形式接收环境变量。

clone是fork的升级版本，不仅可以创建进程或者线程，还可以指定创建新的命名空间（namespace）、有选择的继承父进程的内存资源、甚至可以将创建出来的进程变成父进程的兄弟进程
 int clone(int (*fn)(void *), void *child_stack, int flags, void *arg);
1）fn：指向想要创建进程的静态程序
2）child_stack：给子进程分配系统堆栈的指针（8k堆栈空间，低地址放task_struct）
3）flags为要复制资源的标志：描述需要从父进程继承那些资源


clone与fork的区别？
1）clone需要传入一个函数，该函数在子进程中执行；
2）clone不再复制父进程的栈空间，而是自己创建一个新的

标志

含义

CLONE_PARENT

创建的子进程的父进程是调用者的父进程，新进程与创建它的进程成了“兄弟”而不是“父子”

CLONE_FS

子进程与父进程共享相同的文件系统，包括root、当前目录、umask

CLONE_FILES

子进程与父进程共享相同的文件描述符（file descriptor）表

CLONE_NEWNS

在新的namespace启动子进程，namespace描述了进程的文件hierarchy

CLONE_SIGHAND

 子进程与父进程共享相同的信号处理（signal handler）表

CLONE_PTRACE

若父进程被trace，子进程也被trace

CLONE_VFORK

父进程被挂起，直至子进程释放虚拟内存资源

CLONE_VM

子进程与父进程运行于相同的内存空间

CLONE_PID 

子进程在创建时PID与父进程一致

CLONE_THREAD

Linux 2.4中增加以支持POSIX线程标准，子进程与父进程共享相同的线程群

## Fork

​        fork子进程完全复制父进程的栈空间，也复制了页表，但没有复制物理页面，所以这时虚拟地址相同，物理地址也相同，但是会把父子共享的页面标记为“只读”（类似mmap的private的方式），如果父子进程一直对这个页面是同一个页面，知道其中任何一个进程要对共享的页面“写操作”，这时内核会复制一个物理页面给这个进程使用，同时修改页表。而把原来的只读页面标记为“可写”，留给另外一个进程使用。

​        fork会产生一个和父进程完全相同的子进程，但子进程在此后多会exec系统调用，出于效率考虑，linux中引入了“写时复制“技术，也就是只有进程空间的各段的内容要发生变化时，才会将父进程的内容复制一份给子进程。由于写时复制，在fork之后exec之前两个进程有独立的虚拟地址空间，共享物理内存。只有其中一方需要写操作时，再为子进程的数据段、栈、堆分配物理空间。但在子进程上调用exec时，会清空栈、堆，以及和父进程共享的空间，重新加载新的代码段，这样避免了“写时复制”拷贝共享页面的机会，父进程也同时独自拥有了原来共享的物理内存（可对其读写操作）。

　　fork出来子进程之后，父子进程哪个先调度直接决定了是否需要拷贝的问题？内核一般会先调度子进程，因为很多情况下子进程是要马上执行exec，而避免无用的复制。如果父进程先调度很可能写共享页面，会产生“写时复制”的无用功。所以，一般是子进程先调度。

![img](https://pic1.zhimg.com/v2-5bad788d99c8dd17fc795e6a7de25608_r.jpg)

## _do_fork

fork中构建了内存管理相关的基础设施如mm_struct ,vma,pgd页等，以及拷贝父进程的vma和拷贝父进程的页表来达到和父进程共享地址空间的目的，可以看到处理这种共享并不是像共享内存那种纯粹意义上的共享，而是让子进程能够使用父进程的内存资源，而且在写的时候能够让父子进程开来创造了条件（写保护）。当然这种方式并**没有拷贝父进程的任何物理页，只是通过页表来共享**而已，当然这种内存开销也是很大的，如果子进程fork之后立马进程exec加载自己的程序，这种写时复制意义并不大，但是试想，如果不通过页表共享，则子进程寸步难行，甚至连exec都无法调用。

### dup_task_struct

```c
static struct task_struct *dup_task_struct(struct task_struct *orig)
{
	struct task_struct *tsk;
	struct thread_info *ti;
	unsigned long *stackend;
 
	prepare_to_copy(orig);
 
	tsk = alloc_task_struct();             /* 创建新的子进程结构体 */
	ti = alloc_thread_info(tsk);
 	err = arch_dup_task_struct(tsk, orig); /* 把orig中的内容完全复制给tsk,相当于*tsk = *orig */
 
	tsk->stack = ti;
 
	err = prop_local_init_single(&tsk->dirties);
 
	setup_thread_stack(tsk, orig);   
   /*为整个thread_info结构复制，并设置指针指向
   thread_info里面有一个指向task_struct的指针 ，子进程指向子进程的，父进程指向父进程的，而现在，
   这两个thread_info中的某个指针，都指向了父进程的task_struct，所以还要使得子进程thread_info的指针指向tsk的task_struct，
   而不是 父进程的task_struct：task_thread_info(p)->task = p;
   */
 
    clear_user_return_notifier(tsk);
	stackend = end_of_stack(tsk);
	*stackend = STACK_END_MAGIC;	/* for overflow detection */
 
#ifdef CONFIG_CC_STACKPROTECTOR
	tsk->stack_canary = get_random_int();
#endif
 
	/* One for us, one for whoever does the "release_task()" (usually parent) */
	atomic_set(&tsk->usage,2);
	atomic_set(&tsk->fs_excl, 0);
#ifdef CONFIG_BLK_DEV_IO_TRACE
	tsk->btrace_seq = 0;
#endif
	tsk->splice_pipe = NULL;
 
	account_kernel_stack(ti, 1);
	return tsk;
}
```

### copy_mm

其主要做了以下几件事情

- 如果是内核线程，也就是当前进程地址空间为空，就不需要为子进程做内存复制，直接退出；

- 在创建的时候，会根据fork参数的clone_flags来决定，

  - 如果是CLONE_VM标志位就会被置位，子进程的mm指针指向父进程的内存描述符的mm即可, 

  - 如果CLONE_VM没有被置位，那么调用dump_mm来复制父进程的进程地址空间

```c
1295 static int copy_mm(unsigned long clone_flags, struct task_struct *tsk)
1296 {
1297         struct mm_struct *mm, *oldmm;
1306
1307         tsk->mm = NULL;                     /* 初始化task的mm_struct和VMA为空 */
1308         tsk->active_mm = NULL;
1309
1310         /*
1311          * Are we cloning a kernel thread?
1312          *
1313          * We need to steal a active VM for that..
1314          */
1315         oldmm = current->mm; /* current宏表明当前进程，即父进程 */
1316         if (!oldmm)          /* 如果父进程是一个没有进程地址空间的内核线程，不需要为子进程做内存复制，直接退出 */
1317                 return 0;
1318
1319         /* initialize the new vmacache entries */
1320         vmacache_flush(tsk); /* 初始化vma cache */
1321         /* 
			  * 如果调用vfork创建子进程，那么CLONE_VM标志位就会被置位，
			  * vfork子进程不需要创建自己的进程地址空间，
			  * 因此子进程进程的mm直接指向父进程的内存描述符 。
			  */
1322         if (clone_flags & CLONE_VM) {
1323                 mmget(oldmm); 
1324                 mm = oldmm;
1325                 goto good_mm;
1326         }
1327
1328         retval = -ENOMEM;
1329         mm = dup_mm(tsk); /* 如果CLONE_VM没有置位，那么调用dump_mm来复制父进程的进程地址空间 */
1332
1333 good_mm:
1334         tsk->mm = mm;
1335         tsk->active_mm = mm;
1336         return 0;
1340 }
```

#### dup_mm

首先会分配属于自己进程的mm_struct结构来管理自己的地址空间，并通过拷贝父进程的mm_struct来初始化它；

然后通过mm_init来初始化mm_struct中相关成员，

接着通过dup_mmap来复制父进程的地址空间 ；

```c
1260 static struct mm_struct *dup_mm(struct task_struct *tsk)
1261 {
1262         struct mm_struct *mm, *oldmm = current->mm;
1263         int err;
1264
1265         mm = allocate_mm(); /* 通过allocate_mm分配属于进程自己的mm_struct结构来管理自己的地址空间 */
1268
1269         memcpy(mm, oldmm, sizeof(*mm));     /* 拷贝父进程的mm_struct */
1270
1271         if (!mm_init(mm, tsk, mm->user_ns)) /* 通过mm_init来初始化mm_struct中相关成员 */
1272                 goto fail_nomem;
1273
1274         err = dup_mmap(mm, oldmm);          /* 通过dup_mmap来复制父进程的地址空间 */
1275         .......
1284         return mm;
1293 }
```

##### mm_init

```C
mm_init
    /* 
     * 对于像amr64这种处理器架构来说，只不过是分配一个进程私有pge页而已，
     * 当va->pa转换的时候，查找属于当前进程的pgd表项。 
     */
    if (mm_alloc_pgd(mm)) ->  mm->pgd = pgd_alloc(mm) -> __get_free_page
        goto fail_nopgd;      
	/*
	 * 置了mm->context.id为0，这点很重要，当进程调度的时候进行地址空间切换，
	 * 如果mm->context.id为0就为进程分配新的ASID（ASID技术为了在进程地址
	 * 空间切换的时候防止频繁刷tlb的一种优化）
	 */
    if (init_new_context(p, mm))  -> atomic64_set(&mm->context.id, 0)  
    	goto fail_nocontext;
```

##### dup_mmap

对父子进程的写保护处理，也就是当发现父进程的vma的属性为私有可写的时候，就**设置父进程和子进程的相关的页表项为只读**。

这点很重要，因为这样既保证了父子进程的地址空间的共享（读的时候），又保证了他们有独立的地址空间（写的时候）。

```c
dup_mmap
    vm_area_dup /* 拷贝父进程的vma */
    /* 
     * 遍历vma中每一个虚拟页，然后拷贝父进程的页表到子进程（虚拟页对应的页表存在的话），
     * 这里主要是页表遍历的代码，从pgd->pud->pmd->pte
     */
    copy_page_range 
    	is_cow = is_cow_mapping(src_vma->vm_flags)   /* 判断当前vma是否为私有可写的属性 VM_MAYWRITE */
    		copy_p4d_range
    			p4d_alloc
    			copy_pud_range
    				pud_alloc
    				copy_pmd_range
    					pmd_alloc
    					copy_pte_range
    						copy_one_pte
    							 /*
                                  * If it's a COW mapping, write protect it both
                                  * in the parent and the child
                                  */
                                if (is_cow_mapping(vm_flags) && pte_write(pte)) {
                                    ptep_set_wrprotect(src_mm, addr, src_pte);
                                    pte = pte_wrprotect(pte);
                                }
								set_pte_at
```

## 各级页表创建

对于用户进程来说，内核并不是马上满足进程对于物理页的请求，而仅仅是为他分配虚拟页，内核采用一种惰性的内存分配的方式，知道访问的最后一刻才为进程分配物理页，这既是所谓的内核的按需分配/掉页机制。进程fork的时候，仅仅分配了一级页表页也就是私有的pgd页，其他的各级页表并没有分配，当进程第一次访问虚拟页时，发生缺页异常来分配；缺页异常中分配各级页表路径如下：

```c
handle_mm_fault
	__handle_mm_fault
    	pgd = pgd_offset(mm, address)       /* 根据发生缺页的地址和mm->pgd计算出pgd表项 */
    	p4d = p4d_alloc(mm, pgd, address)   /* 获得p4d表项  arm64没有使用p4d    直接(p4d_t *)pgd */
    	vmf.pud = pud_alloc(mm, p4d, address)      /* 获得pud项  没有pud页则创建 */
    	vmf.pmd = pmd_alloc(mm, vmf.pud, address)  /* 获得pmd项  没有pm页则创建 */
   			handle_pte_fault
        		do_anonymous_page                      /* 匿名映射缺页异常为例 */
            		pte_alloc(vma->vm_mm, vmf->pmd)    /* 获得pte  没有pte页则创建 */
    				alloc_zeroed_user_highpage_movable /* 分配物理页，可能是highmem */
    				entry = mk_pte(page, vma->vm_page_prot);
					set_pte_at(vma->vm_mm, vmf->address, vmf->pte, entry); /* 页表填充 */
```



## COW

fork创建完子进程后，通过复制父进程的页表来共享父进程的地址空间，我们知道对于私有的可写的页，设置了父子进程的相应页表为只读，这样就为写实复制创造了页表层面上的条件。**当父进程或者子进程，写保护的页时触发访问权限异常**：

处理器架构捕获异常后，进入通用的缺页异常处理路径：

```c
handle_pte_fault
	if (vmf->flags & FAULT_FLAG_WRITE) {
         if (!pte_write(entry))
             return do_wp_page(vmf);
         entry = pte_mkdirty(entry);
     }
```

在匿名页缺页异常处理路径中，判断这个页错误是写保护错误（也就是**判断虚拟页可写可是对应的页表为只读**）时，就会调用do_wp_page做写实复制处理：

```c
do_wp_page
	wp_page_copy
		new_page = alloc_page_vma(GFP_HIGHUSER_MOVABLE, vma, vmf->address); /* 分配新的页面 */          
    	cow_user_page(new_page, old_page, vmf)                /* 拷贝原来共享的页面到新页面 */
    	entry = mk_pte(new_page, vma->vm_page_prot);                     
    	entry = maybe_mkwrite(pte_mkdirty(entry), vma);       /* 设置为可写 */
    	set_pte_at_notify(mm, vmf->address, vmf->pte, entry)  /* 页表属性设置到进程对应的页表项中 */
```

由上可见，fork时对私有可写的页面做写保护的准备，在父子进程有一方发生写操作时触发了处理器的访问权限缺页异常，异常处理程序重新分配了新的页面给了发起写操作的进程，父子进程对应这个页面的引用就此分道扬镳。

