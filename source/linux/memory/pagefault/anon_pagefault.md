# do_anonymous_page

```c
3115 /*
3116  * We enter with non-exclusive mmap_sem (to exclude vma changes,
3117  * but allow concurrent faults), and pte mapped but not yet locked.
3118  * We return with mmap_sem still held, but pte unmapped and unlocked.
3119  */
3120 static vm_fault_t do_anonymous_page(struct vm_fault *vmf)
3121 {
3122     struct vm_area_struct *vma = vmf->vma;
3123     struct mem_cgroup *memcg;
3124     struct page *page;
3125     vm_fault_t ret = 0;
3126     pte_t entry;
3127
3128     /* File mapping without ->vm_ops ? */
         /* 如果是共享的匿名映射，但是没有提供vma->vm_ops则返回VM_FAULT_SIGBUS错误 */
3129     if (vma->vm_flags & VM_SHARED)   
3130         return VM_FAULT_SIGBUS;
3131
3132     /*
3133      * Use pte_alloc() instead of pte_alloc_map().  We can't run
3134      * pte_offset_map() on pmds where a huge pmd might be created
3135      * from a different thread.
3136      *                                                                                                  3137      * pte_alloc_map() is safe to use under down_write(mmap_sem) or when                               3138      * parallel threads are excluded by other means.
3139      *                                                                                                  3140      * Here we only have down_read(mmap_sem).        
3141      */ 
         /* 如果pte不存在，则分配pte。建立pmd和pte的关系 */
3142     if (pte_alloc(vma->vm_mm, vmf->pmd, vmf->address))
3143         return VM_FAULT_OOM;
3144
3145     /* See the comment in pte_alloc_one_map() */
3146     if (unlikely(pmd_trans_unstable(vmf->pmd)))
3147         return 0;                                                                                       3148
3149     /* 如果是读操作触发的缺页且未禁止使用零页，则映射到全局零页 */
3150     if (!(vmf->flags & FAULT_FLAG_WRITE) &&
3151             !mm_forbids_zeropage(vma->vm_mm)) {
         /* 调用pte_mkspecial生成一个特殊页表项，映射到全局零页 */
3152         entry = pte_mkspecial(pfn_pte(my_zero_pfn(vmf->address),
3153                         vma->vm_page_prot));
         /* 根据pmd,address找到pte表对应的一个表项，并且lock住 */
3154         vmf->pte = pte_offset_map_lock(vma->vm_mm, vmf->pmd, 
3155                 vmf->address, &vmf->ptl);
         /* 如果页表项不为空。我们第一次访问，不可能有值的，所以可能别的进程在使用此物理地址，跳unlock */
3156         if (!pte_none(*vmf->pte))
3157             goto unlock;
3158         ret = check_stable_address_space(vma->vm_mm);
3159         if (ret)
3160             goto unlock;
3161         /* Deliver the page fault to userland, check inside PT lock */
3162         if (userfaultfd_missing(vma)) {
3163             pte_unmap_unlock(vmf->pte, vmf->ptl);
3164             return handle_userfault(vmf, VM_UFFD_MISSING);
3165         }
3166         goto setpte;
3167     }
3168
3169     /* 分配一个匿名的anon_vma */
3170     if (unlikely(anon_vma_prepare(vma)))
3171         goto oom;
3172     page = alloc_zeroed_user_highpage_movable(vma, vmf->address);
3173     if (!page)
3174         goto oom;
3175
3176     if (mem_cgroup_try_charge_delay(page, vma->vm_mm, GFP_KERNEL, &memcg,
3177                     false))
3178         goto oom_free_page;
3179
```

