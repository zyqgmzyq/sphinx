# Math

## [2507. 使用质因数之和替换后可以取到的最小值](https://leetcode.cn/problems/smallest-value-after-replacing-with-sum-of-prime-factors/)

### 题目描述

给你一个正整数 `n` 。

请你将 `n` 的值替换为 `n` 的 **质因数** 之和，重复这一过程。

- 注意，如果 `n` 能够被某个质因数多次整除，则在求和时，应当包含这个质因数同样次数。

返回 `n` 可以取到的最小值。

**示例 ：**

```
输入：n = 15
输出：5
解释：最开始，n = 15 。
15 = 3 * 5 ，所以 n 替换为 3 + 5 = 8 。
8 = 2 * 2 * 2 ，所以 n 替换为 2 + 2 + 2 = 6 。
6 = 2 * 3 ，所以 n 替换为 2 + 3 = 5 。
5 是 n 可以取到的最小值。
```

### 解题思路

将数字进行质因数分解，然后相加，重复这一操作，直到无法变化
两层循环，内循环质因数分解，然后求和，外循环重复操作，直到无法变化到更小

### 代码

```c
class Solution {
public:
    int smallestValue(int n) {
		int pre = 0;
		while (n != pre) {
			pre = n;
			int sum = 0;
			for (size_t i = 2; i <= n; ++i) {
				while (n % i == 0) {
					sum += i;
                    n /= i;
				}
			}
			sum += n > 1 ? n : 0;
			n = sum;
		}
		return n;
    }
};
```

## [6309. 分割数组使乘积互质](https://leetcode.cn/problems/split-the-array-to-make-coprime-products/)

### 题目描述

给你一个长度为 `n` 的整数数组 `nums` ，下标从 **0** 开始。

如果在下标 `i` 处 **分割** 数组，其中 `0 <= i <= n - 2` ，使前 `i + 1` 个元素的乘积和剩余元素的乘积互质，则认为该分割 **有效** 。

- 例如，如果 `nums = [2, 3, 3]` ，那么在下标 `i = 0` 处的分割有效，因为 `2` 和 `9` 互质，而在下标 `i = 1` 处的分割无效，因为 `6` 和 `3` 不互质。在下标 `i = 2` 处的分割也无效，因为 `i == n - 1` 。

返回可以有效分割数组的最小下标 `i` ，如果不存在有效分割，则返回 `-1` 。

当且仅当 `gcd(val1, val2) == 1` 成立时，`val1` 和 `val2` 这两个值才是互质的，其中 `gcd(val1, val2)` 表示 `val1` 和 `val2` 的最大公约数。

 

**示例 1：**

![img](https://assets.leetcode.com/uploads/2022/12/14/second.PNG)

```
输入：nums = [4,7,8,15,3,5]
输出：2
解释：上表展示了每个下标 i 处的前 i + 1 个元素的乘积、剩余元素的乘积和它们的最大公约数的值。
唯一一个有效分割位于下标 2 。
```

### 解题思路

比赛中写的都超时了    呜呜呜

看看大佬们怎么写的把！！！

### 代码

```c
bool init = false;

vector<vector<int>> p(1000000 + 1);   // p[i]存放i的所有质因数
class Solution {
public:
    int findValidSplit(vector<int>& nums) {
        //猜测：由于LeetCode的机制，全局变量不会被改变（即受前面的测试用例和过程影响）
        //如果是第一次，求2到1000000的质因数。如果不是，可以直接使用，减少运行时间
        if (not init) {
            //质因数添加顺序从小到大（后面会再次提到）
            for (int i = 2; i <= 1000000; i += 1) {
                //如果p[i]为空，说明p[i]是质数
                //将所有是p[i]的倍数的数的质因数数组里加上p[i]
                if (p[i].empty()) {
                    //j = n*i 所以j是i的倍数
                    for (int j = i; j <= 1000000; j += i) {
                        p[j].push_back(i);
                    }
                }
            }
            init = true;
        }
        
        int n = nums.size();
        map<int, vector<int>> mp;
        for (int i = 0; i < n; i += 1) {
            //pi是nums[i]的质因数。将是pi的倍数的下标存入数组里。
            //以为下标从小到大遍历，所以pi的下标数组也是从小到大的。
            for (int pi : p[nums[i]]) mp[pi].push_back(i);
        }
        vector<int> ans(n);
        //map<key,value>
        //[_,v]是键值对。即[key,value]。可以直接使用key和value这两个变量
        for (auto& [_, v] : mp) {
            if (v.size() > 1) {
                //因为下标数组是从小到大有序，所以直接取出首尾。
                int l = v[0], r = v.back();
                //这个题目的本质是求一个分界，该分界不在任何质数的下标跨越范围内。
                //分界起点+1；终点-1
                ans[l] += 1;
                ans[r] += -1;
            }
        }
        for (int i = 0; i + 1 < n; i += 1) {
            //如果i==0,跳过第一个if。第二个判定成功。
            //ans[i]在判定时，是ans 0到i的和
            /*
            如果ans[i]!=0。可以把+-1看做左右括号。
            1、当括号在i之前（包括i）完全匹配，则+-1的和一定为零
            2、假设存在当和为零时，但不能匹配。和为零则左右括号数一样，那只能是属于不同范围
            假设前括号是范围A的，后括号是范围B。因为前括号一定在后括号之前出现，所以，不可能
            存在一个没有前括号的后括号。
            所以使用一个不能代表任何确切范围的+-1来计算，是可行的*/
            if (i) ans[i] += ans[i - 1];
            if (ans[i] == 0) return i;
        }
        return -1;
    }
};
```

