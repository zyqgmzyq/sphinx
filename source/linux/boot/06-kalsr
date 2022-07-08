# kalsr

这篇内容主要是说一下KASLR

KASLR是让内核在一个随机的地址上运行的技术, 就是说内核的运行时地址是随机的, 每次启动会变化. 这样内核的符号对应的地址会变化并不是链接地址从而加强安全性. 这里画一个图

```c
+---------------+-------+-------------+----------------------
|               |       |             |
| 2M align resv | KASLR | TEXT_OFFSET | KERNEL IMAGE
|               |       |             |
+---------------+-------+-------------+----------------------
|                       |             |
|                       |             +----内核在DDR中的位置.
|                       +----------------- ARM64规定的KERNEL运行前必须放在 2M对齐地址+TEXT_OFFSET 的地方
|                                          这里是经过KASLR技术relocate之后的位置.
+----------------------------------------- DDR起始地址.
```

目前开启KASLR的内核启动有两种办法:

1. bootloader在设备树中添加一个`kaslr-seed`的节点. 并赋予一个随机的偏移, 将KERNEL放在ARM64规定的2M对齐地址+TEXT_OFFSET的地方, 然后启动内核, 之后内核会将自己relocate到2M对齐地址+KASLR offset+TEXT_OFFSET的地方运行
2. bootloader把将KERNEL放在2M对齐地址+KASLR offset+TEXT_OFFSET的地方(KASLR offset小于2M), 然后启动内核, 之后内核会修复symbol, 然后在原地运行.

在前面的文章中, 我们放了一段code没说

```c
adrp	x23, __PHYS_OFFSET
and	x23, x23, MIN_KIMG_ALIGN - 1	// KASLR offset, defaults to 0
#define __PHYS_OFFSET	(KERNEL_START - TEXT_OFFSET)
#define KERNEL_START        _text
#define MIN_KIMG_ALIGN		SZ_2M
```

我们假设使用第二种启动办法, 那么`__PHYS_OFFSET`指向KASLR区域的最后面所在的物理地址. 第二条汇编就会计算出KASLR区域的大小然后保存在x23寄存器中. 对这个寄存器多加留意, 在调用`start_kernel`之前还会再用到.

对于KASLR的BOOT后面还需继续降到, 这里先放放, 我们先在下篇接着往下说
