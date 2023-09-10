# 常用算法

## 最大公约数（greatest common divisor）

```c
int gcd(int a,int b) {
    int r;
    while(b > 0) {
        r = a % b;
        a = b;
        b = r;
    }
    return a;
}

#include <algorithm>
int gcd(int a,int b) {
	return __gcd(a,b);
}
```

## 最小公倍数（least common multiple）

```c
int lcm(int a, int b) {
	return a * b / __gcd(a, b);
}
```

### vector数组用法

```c
/* 查找[first, last)区域中第一个大于 val 的元素的迭代器 */
auto it = upper_bound(nums.begin(), nums.end(), val);
if (it != nums.end())
{
	ret = *it;
}
/* 查找[first, last)区域中第一个大于等于 val 的元素的迭代器 */
auto it = lower_bound(nums.begin(), nums.end(), val);
if (it != nums.end())
{
	ret = *it;
}
```

### 排列

```c
/* 下一个排列 */
next_permutation(nums.begin(), nums.end());
```

### 优先级队列

```c
/* 对于基础类型 默认是大顶堆 */
priority_queue<int> a; 
priority_queue<int, vector<int>, less<int> > a;

/* 小顶堆 */
priority_queue<int, vector<int>, greater<int> > c;
```

## bitset

```c
bitset<8> foo ("10011011");

cout << foo.count() << endl;// 5　　（count函数用来求bitset中1的位数，foo中共有５个１
cout << foo.size() << endl; // 8　　（size函数用来求bitset的大小，一共有８位

cout << foo.test(0) << endl; // true   查下标处的元素是０还是１，并返回false或true，此处foo[0]为１，返回true
cout << foo.test(2) << endl; // false　同理，foo[2]为０，返回false

cout << foo.any() << endl;　　// true　any函数检查bitset中是否有１
cout << foo.none() << endl;　// false　none函数检查bitset中是否没有１
cout << foo.all() << endl;　　// false　all函数检查bitset中是全部为１    
```

