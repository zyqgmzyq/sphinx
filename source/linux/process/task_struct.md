## task_struct

PCB通常记载进程之相关信息，包括：

- 进程状态：可以是new、ready、running、waiting或 blocked等。
- 程序计数器：接着要运行的指令地址。
- CPU寄存器：如累加器、变址寄存器、堆栈指针以及一般用途寄存器、状况代码等， 主要用途在于中断时暂时存储数据，以便稍后继续利用；其数量及类别因计算机体系结构有所差异。
- CPU排班法：优先级、排班队列等指针以及其他参数。
- 存储器管理：如标签页表等。
- 会计信息：如CPU与实际时间之使用数量、时限、账号、工作或进程号码。
- 输入输出状态：配置进程使用I/O设备，如磁带机。
  总言之，PCB如其名，内容不脱离各进程相关信息。

**内核使用双向循环链表的任务队列来存放进程，使用结构体task_struct来描述进程所有信息。**

```c
struct task_struct
{
	struct thread_info		thread_info; /* 必须是第一个元素 */
	volatile long state;    /* 这个是进程的运行时状态，-1代表不可运行，0代表可运行，>0 代表已停止。 */
	/* 
	flags是进程当前的状态标志，具体的如：
	0x00000002表示进程正在被创建； 通过宏定义实现
	0x00000004表示进程正准备退出； 
	0x00000040 表示此进程被fork出，但是并没有执行exec；
	0x00000400表示此进程由于其他进程发送相关信号而被杀死 。
	*/
	unsigned int flags;
	void *stack;    /* 指向内核栈的指针,通过他就可以找到thread_info */
	
	pid_t pid;      /* 进程号 */
	
	struct mm_struct *mm; /* 该结构体描述了虚拟内存的当前状态 */
	......
};
```

这个图有点不对，thread_info应该放在第一个
![image-20221030205729140](D:\work\sphinx-master\source\linux\process\figs\task_struct.assets\image-20221030205729140.png)

### 内核栈和thread_info

当进程由于中断或系统调用从用户态转换到内核态时，**进程所使用的栈也要从用户栈切换到内核栈**

内核空间就使用这个内核栈。因为内核控制路径使用很少的栈空间，所以只需要几千个字节的内核态堆栈。

thread_info是体系结构相关的（内核中的PCB），结构的定义在thread_info.h中，保存了进程所有依赖于体系结构的信息, 同时也保存了一个指向进程描述符task_struct的指针。

![image-20221030211438682](D:\work\sphinx-master\source\linux\process\figs\task_struct.assets\image-20221030211438682.png)

