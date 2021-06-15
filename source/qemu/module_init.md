# module type的构造函数

## module_init

QEMU中使用了很多构造函数，这些构造函数会在执行main()函数之前就执行，初始化一些数据结构。module_init()就是典型代表。

这个函数有两个版本的 define，一个版本适用于普通设备，一个版本适用于 DSO 设备，然后对应的 function 和 type，function 对应类型的初始化函数，type 的值为 MODULE_INIT_QOM。

然后这里的 constructor 是编译器属性，编译器会把带有这个属性的函数 do_qemu_init_ ## function 放到特殊的段中，**带有这个属性的函数还会早于 main 函数执行**。

参考： http://123.57.146.8/2020/10/05/QEMU%20KVM%20Note%20%E2%85%A2/

```shell
#ifdef BUILD_DSO
void DSO_STAMP_FUN(void);
/* This is a dummy symbol to identify a loaded DSO as a QEMU module, so we can
 * distinguish "version mismatch" from "not a QEMU module", when the stamp
 * check fails during module loading */
void qemu_module_dummy(void);

#define module_init(function, type)                                         \
static void __attribute__((constructor)) do_qemu_init_ ## function(void)    \
{                                                                           \
    register_dso_module_init(function, type);                               \
}
#else
/* This should not be used directly.  Use block_init etc. instead.  */
#define module_init(function, type)                                         \
static void __attribute__((constructor)) do_qemu_init_ ## function(void)    \
{                                                                           \
    register_module_init(function, type);                                   \
}
#endif

#define type_init(function) module_init(function, MODULE_INIT_QOM)
type_init(machvirt_machine_init);
```

```c
static void init_lists(void)
{
    static int inited;
    int i;

    if (inited) {
        return;
    }

    for (i = 0; i < MODULE_INIT_MAX; i++) {
        QTAILQ_INIT(&init_type_list[i]);    // 在init_type_list中把当前的位置插入进去
    }

    QTAILQ_INIT(&dso_init_list);             // 在dso_init_last中把当前位置插入进去,最后形成这样的效果
    inited = 1;                              // 设置flag位,代表这个类型已经被注册过了
}

static ModuleTypeList *find_type(module_init_type type)
{
    init_lists();   // 初始化init_type_list和dso_init_list列表

    return &init_type_list[type];
}

void register_module_init(void (*fn)(void), module_init_type type)
{
    ModuleEntry *e;
    ModuleTypeList *l;

    e = g_malloc0(sizeof(*e));        // 给ModuleEntry结构体分配内存
    e->init = fn;                     // 这里fn指向的是类型初始化函数,所以这里就是让init指向类型初始化函数
    e->type = type;                   // 这里是把类型的type赋给ModuleEntry结构体中的type

    l = find_type(type);              // find_type会返回type在init_type_list列表中的位置
                                      // MODULE_INIT_BLOCK的值为1
    QTAILQ_INSERT_TAIL(l, e, node);   // 把ModuleEntry *e插入到init_type_list列表中
}
```

module_init的作用就是指定function为type类型的init函数，这种挂接关系会存储在这个type的QTAIL链表中。（每种type有各自的一个链表，而不是所有type都在一个链表中）。

QTAIL链表的每一个节点node就记录了一种type和其init函数的挂接关系。

后面调用module_call_init(type) 时，就会查这个type的QTAIL链表，找到其对应的所有init函数，就开始执行所有与其挂接的init函数。


## type_init

```shell
#define type_init(function) module_init(function, MODULE_INIT_QOM)
type_init(machvirt_machine_init);
	type_register_static(&virt_machine_info);
		type_register(info);
			type_register_internal(info);
				ti = type_new(info);   // 根据info信息，创建一个TypeImpl对象
				type_table_add(ti);    // 将ti插入一个hash表中(第一次调用会新建hash表)。这个表中就存储了各种不同类型cpu的信息:name, parent,class_init,instance_init
```



```c
struct TypeImpl
{
    const char *name;

    size_t class_size;

    size_t instance_size;
    size_t instance_align;

    void (*class_init)(ObjectClass *klass, void *data);
    void (*class_base_init)(ObjectClass *klass, void *data);

    void *class_data;

    void (*instance_init)(Object *obj);
    void (*instance_post_init)(Object *obj);
    void (*instance_finalize)(Object *obj);

    bool abstract;

    const char *parent;
    TypeImpl *parent_type;

    ObjectClass *class;

    int num_interfaces;
    InterfaceImpl interfaces[MAX_INTERFACES];
};
```



# 附录：QTAILQ数据结构

### HEAD

```c
/*
 * Tail queue definitions.  The union acts as a poor man template, as if
 * it were QTailQLink<type>.
 */
#define QTAILQ_HEAD(name, type)                                         \
union name {                                                            \
	struct type *tqh_first;       /* first element */               \
	QTailQLink tqh_circ;          /* link for circular backwards list */ \  // 循环后向链表
}

typedef struct QTailQLink {
    void *tql_next;
    struct QTailQLink *tql_prev; 
} QTailQLink;
```

HEAD 静态初始化

```c
#define QTAILQ_HEAD_INITIALIZER(head)             \ 
	{ .tqh_circ = { NULL, &(head).tqh_circ } }
```

HEAD 动态初始化

```c
/*
 * Tail queue functions.
 */
#define QTAILQ_INIT(head) do {                                          \
        (head)->tqh_first = NULL;                                       \
        (head)->tqh_circ.tql_prev = &(head)->tqh_circ;                  \
} while (/*CONSTCOND*/0)
```

### ENTRY

```
#define QTAILQ_ENTRY(type)                                              \
union {                                                                 \
        struct type *tqe_next;        /* next element */                \
        QTailQLink tqe_circ;          /* link for circular backwards list */ \
}
```

tqe_next表示list entry next，tqe_circ表示list entry prev

在head后面插入一个elm：

```c
#define QTAILQ_INSERT_HEAD(head, elm, field) do {                       \
        if (((elm)->field.tqe_next = (head)->tqh_first) != NULL)        \
            (head)->tqh_first->field.tqe_circ.tql_prev =                \
                &(elm)->field.tqe_circ;                                 \
        else                                                            \
            (head)->tqh_circ.tql_prev = &(elm)->field.tqe_circ;         \
        (head)->tqh_first = (elm);                                      \
        (elm)->field.tqe_circ.tql_prev = &(head)->tqh_circ;             \
} while (/*CONSTCOND*/0)
    
/* elm是包含entry的结构体，比如：*/

typedef struct elm {
    QLIST_ENTRY(type) field;
    // other fields
} elm;
```

看代码可能一时还搞不清楚，看下这张图就懂了，然后往head后面插入，或者前面插入或者删除都差不多。

![image](https://user-images.githubusercontent.com/36949881/122063096-8c1f3f00-ce22-11eb-9833-328d095bcb0e.png)














