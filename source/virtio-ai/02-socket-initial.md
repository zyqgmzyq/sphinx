# socket 文件系统的初始化

一切从 net/socket.c 文件中的以下这行代码开始

```c
core_initcall(sock_init);	/* early initcall */
```

这段代码是一个宏定义的扩展，它最终的效果是在编译的过程中把一个指向 `sock_init` 这个函数的指针放入到一个初始化段中去，这个段的名称是`.initcall1.init`。

内核启动函数 `kernel_init()` 最终会调用这些初始化段中的函数来完成初始化工作。也 就是说在内核初始化的过程中最终会调用 sock_init 这个函数，而这个函数最终完成 socket layer 这一层的初始化工作。

在 `sock_init` 这个函数的尾部有下面这段代码：

```c
sock_init
    init_inodecache();
    register_filesystem(&sock_fs_type);
    sock_mnt = kern_mount(&sock_fs_type);
```

`init_inodecache` 这个函数作用是用来建立一个 socket 结构以及它对应的 inode 节点 的 SLAB缓存。 `register_filesystem(&sock_fs_type)` 的作用则是把 `sock_fs_type` 加入到内核的文件系统列表中。这个列表定义在 fs/filesystem.c 中，它的定义如下。

```c
static struct file_system_type *file_systems;
```

所有在内核中注册的文件系统都会添加到这个列表中去，因为这个列表是一个指针列表，所 以注册的文件系统需要保证内存不被释放，否则会发生非法指针访问错误。比如这里的 `sock_fs_type` 它定义在 net/socket.c 文件下，它的定义如下。

```c
static struct file_system_type sock_fs_type = {
    .name =		"sockfs",
    .get_sb =	sockfs_get_sb,
    .kill_sb =	kill_anon_super,
};c
```

因为它是一个静态的全局变量，所以不用担心内存被释放掉。

最后一条语句 `sock_mnt = kern_mount(&sock_fs_type);` 则真正的完成了对 socket 文 件系统的初始化工作。 

`kern_mount` 函数首先创建一个 `vfsmount`，然后调用的是 `file_system_type` 的 `mount` 函数来得到文件系统的 `super block` 并进行初始化， 


最后用初始化过后的 `super block` 设置 `vfsmount` 中的参数，从上面的 `sock_fs_type` 的定义我们可以看出，对于 socket 文件系统来说 `mount` 是 `sockfs_mount`，而 `sockfs_mount` 最终调用了 `mount_pseudo_xattr` 这个函数。 `mount_pseudo_xattr` 主要完成了下面几件事情：

1. 调用 sget_userns为 socket 文件系统创建一个新的`super block`。 sget 则是通过调用 `alloc_super` 分配空间。

2. 根据 `file_system_type` 对 sget 得到的`super block`进行初始化。其中最主要的是设置它的操作函数（如何创建 inode 和销毁 inode 等等）：

    ```c
    s->s_op = ops ? ops : &simple_super_operations;
    ```

    对于我们的 socket 文件系统来说，传递给 ops 的值是 sockfs_ops，也就是下面这个 结构：

    ```c
    static const struct super_operations sockfs_ops = {
        .alloc_inode =	sock_alloc_inode,
        .destroy_inode =sock_destroy_inode,
        .statfs =	simple_statfs,
    };
    ```

    所以对于 socket 文件系统来说，最终我们创建一个 inode 调用的是 `sock_alloc_inode` 这个函数。

3. 创建一个新的 root inode，因为这是第一个 inode，所以它的 inode 号被设置成了 1 。我们刚刚说过对于 socket 文件系统来说，它最终调用`sock_alloc_inode`函数。这 个函数的具体代码如下：

    ```C
    sock_alloc_inode
        struct socket_alloc *ei;
        ei = kmem_cache_alloc(sock_inode_cachep, GFP_KERNEL);
    ```

    也就是说它在前面通过 sock_init 中的 `init_inodecache();`建立的 inode 缓存中分 配了一块合适的空间。

    值得一提的是，它分配的并不是 inode 结构，而是一个 struct socket_alloc 结构。 这个结构的定义如下：

    ```C
    struct socket_alloc {
        struct socket socket;
        struct inode vfs_inode;
    };
    ```

    它是 socket 结构体和 inode 结构体的结合体。也就是说一个 socket 结构就有一个 inode 结构和它一一对应。需要面向文件系统进行操作的时候使用这个 inode，而需要 面向 socket layer 进行处理的时候使用 socket。在内核中还提供来这两个成员相互转 换到辅助函数

    ```c
    static inline struct socket *SOCKET_I(struct inode *inode)
    static inline struct inode *SOCK_INODE(struct socket *socket)
    ```

4. 创建一个目录项，用刚刚的 inode 实例化这个目录项，也就是说设置这个目录项的 inode 为前面创建的 inode。并把这个新的目录项作为前面新建的`super block`的根目 录。

整个处理流程到这来就算是结束了。最终返回一个设置好的 `vfsmount` 给 `socket_init` 函数。这个 `vfsmount` 最终被存储在了 `sock_mnt` 中。这个变量也是定义在 net/socket.c 中的一个静态变量，定义如下：

```
static struct vfsmount *sock_mnt __read_mostly;
```

所以最终在 `sock_init` 执行之后，就可以通过 `sock_mnt` 的来访问这个 socket 文件 系统了。

[^1]: 传统的进程间通信技术，比如信号、管道、信号量、共享内存等等。这些技术都是用于同一机器上到进程。当然 socket 也可以用于本机上的进程通信。
[^2]: 你可以使用 `lsof -U` 命令来查看打开的 socket 文件，一般来说在 /tmp 目录下会有很多这类文件。
