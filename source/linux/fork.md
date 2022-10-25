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

