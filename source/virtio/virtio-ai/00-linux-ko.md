# Linux ko

## 内核态

```c
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/module.h>
#include <linux/miscdevice.h>
#include <linux/fs.h>
#include <linux/device.h>
#include <linux/sysfs.h>
#include <linux/types.h>
#include <linux/uaccess.h>
#include "aosai.h"
#define AI_NAME     "aos_ai"
#define MPIDR_GUEST_BITMASK (0x1U << 25)

static long is_guest(ulong arg)
{
    long ret = 0;
    struct msg my_msg;
    uint64_t mpidr = read_sysreg(mpidr_el1);
    my_msg.isGuest = mpidr & MPIDR_GUEST_BITMASK;

    ret = copy_to_user((struct msg __user *)arg, \
            &my_msg, sizeof(my_msg));
    if (ret) {
        return -EFAULT;
    }
    return ret;
}

static long ai_cmd_ioctl(
        struct file *filp, uint32_t cmd, ulong arg)
{
    long ret = -EFAULT;

    if ((_IOC_TYPE(cmd) != IOC_MAGIC) || (_IOC_NR(cmd) > IOC_MAXNR)) {
        return -EINVAL;
    }
    switch(cmd) {
    case AOSAI_IOC_ISGUEST:
        ret = is_guest(arg);
        break;
    default:
        printk("invalid ioctl\n");
    }
    return ret;
}

static const struct file_operations g_ai_ops = {
    .owner = THIS_MODULE,
    .unlocked_ioctl = ai_cmd_ioctl,
    .compat_ioctl = ai_cmd_ioctl,
};

static struct miscdevice g_ai_device = {
    .name = AI_NAME,
    .minor = MISC_DYNAMIC_MINOR,
    .fops = &g_ai_ops,
};

static int32_t __init ai_cmd_init(void)
{
    int32_t retval;

    retval = misc_register(&g_ai_device);
    if (retval != 0) {
        (void)pr_info("Unable to register device\n");
    } else {
        (void)printk("AOS ai ko Registered\n");
    }

    return retval;
}

static void ai_cmd_exit(void)
{
  printk(KERN_ALERT "Goodbye, cruel world\n");
}

module_init(ai_cmd_init);
module_exit(ai_cmd_exit);
MODULE_LICENSE("GPL");
```



## 用户态

```c
static bool CheckVirt()
{
   int32_t fd = open("/dev/aos_ai", O_RDWR);
   struct msg my_msg;
   memset_s(&my_msg, sizeof(my_msg), 0, sizeof(my_msg));
 
   int ret = ioctl(fd, AOSAI_IOC_ISGUEST, &my_msg);
   if (ret) {
     std::cerr << "IOCTL ISVIRT failed" << std::endl;
   }
 
   return my_msg.isGuest;
}

```



## 头文件

```c
#ifndef __IOCTL_AOS_AI_H__
#define __IOCTL_AOS_AI_H__

#include <linux/ioctl.h>
//  #include <sys/ioctl.h>  用户态

/* define device type */
#define IOC_MAGIC  'A'

/* read current os is guest os */
#define AOSAI_IOC_ISGUEST     _IOW(IOC_MAGIC, 1, int)

#define IOC_MAXNR  1

struct msg {
    bool isGuest;
};

#endif
```
