# swap cache

`swap cache` 指的是交换缓存区，它的作用类似 `page cache`，主要是提高读写效率。`swap cache` 的数据结构是基数树，其根节点是 `address_space->page_tree`，基数树的数据结构在这里不展开描述，以下列出与 `page cache` 增，删，查的操作函数，以及什么时候会加入到 `swap cache`，什么时候会从中删除，即增加和删除的时机。

| __add_to_swap_cache(struct page *page, swp_entry_t entry)    | 增加一个page 到swap cache 中，并把entry 保存到page->private变量中 |
| ------------------------------------------------------------ | ------------------------------------------------------------ |
| __delete_from_swap_cache(struct page *page)                  | 从page cache 中删掉page                                      |
| lookup_swap_cache(swp_entry_t entry, struct vm_area_struct *vma, unsigned long addr) | 从swap cache查找entry 指定的page                             |

把page加入交换缓存区的时机：

1. 本来在物理内存没有数据，需要从 swap 分区中把数据读回时，即 swapin，需要加入到 `swap cache` 中。
2. 系统回收内存时，选择一个匿名页面进行回收，则先把该page 放入`swap cache`

把 page 从交换缓存区中删除掉的时机：

1. 该 page 已经没有进程需要了，根据 `page_swapped(page)` 来判断。
2. 该 page 的 `PG_writeback` 和 `PG_dirty` 都为 0 时，并且系统急需回收内存时。
3. 该 page 发生了写时复制，或者发生写访问异常时,并且只一本进程使用该 page， 即写访问的方式调用 `do_swap_page`。