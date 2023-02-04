# 几数之和

## [1. leetcode-1 两数之和  ](https://leetcode-cn.com/problems/two-sum)*

### 1.1 题目描述
给定一个整数数组 nums 和一个目标值 target，请你在该数组中找出和为目标值的那 两个 整数，并返回他们的数组下标。你可以假设每种输入只会对应一个答案。但是，你不能重复利用这个数组中同样的元素。

### 1.2 解题思路
使用一个HashMap，来建立数字和其坐标位置之间的映射，扫描一遍，对其中的每一个整数nums[i]，查找target-nums[i]在map中是否存在即可。若存在，则输出i与 target-nums[i]的下标即可.

### 1.3 代码

```cpp
class Solution {
public:
    vector<int> twoSum(vector<int>& nums, int target) {
        vector<int> res;
        unordered_map<int, int> hashmap;
        for(int i=0;i<nums.size();i++){
            if(hashmap.count(target-nums[i])>0){
                res.push_back(hashmap[target-nums[i]]);
                res.push_back(i);
                break;
            }else{
                hashmap[nums[i]] = i;
            }
        }
        return res;
    }
};
```



## [2. leetcode-371 两整数之和](https://leetcode-cn.com/problems/sum-of-two-integers/) *

### 2.1 题目描述
不使用运算符 + 和 - ，计算两整数 a 、b 之和。

### 2.2 解题思路

 不断的异或和与，异或的结果是不含进位的加，与得到的是每一位的进位，让结果和进位继续异或（无进位加），直到进位为0

### 2.3 代码

```cpp
class Solution {
public:
    int getSum(int a, int b)  {
        while(b){
            // 防止 AddressSanitizer 对有符号左移的溢出保护处理
            auto c = ((unsigned int)a&b) << 1;
            //求两数相加的进位，与运算和左移运算，得相加之后进位所在位得值
            a = a^b;       //异或操作：不进位加法
            b = c;
        }
        return a;
    }
};
```



## [3. leetcode-167 两数之和 II - 输入有序数组](https://leetcode-cn.com/problems/two-sum-ii-input-array-is-sorted/) *

### 3.1 题目描述
给定一个已按照升序排列 的有序数组，找到两个数使得它们相加之和等于目标数。函数应该返回这两个下标值 index1 和 index2，其中 index1 必须小于 index2。返回的下标值（index1 和 index2）不是从零开始的。你可以假设每个输入只对应唯一的答案，而且你不可以重复使用相同的元素。

输入: numbers = [2, 7, 11, 15], target = 9
输出: [1,2]
解释: 2 与 7 之和等于目标数 9 。因此 index1 = 1, index2 = 2 。

### 3.2 解题思路

双指针法，使用两个指针，初始分别位于第一个元素和最后一个元素位置，比较这两个元素之和与目标值的大小。如果和等于目标值，我们发现了这个唯一解。如果比目标值小，我们将较小元素指针增加一。如果比目标值大，我们将较大指针减小一。

### 3.3 代码

```cpp
class Solution {
public:
    vector<int> twoSum(vector<int>& numbers, int target) {
        vector<int> res;
        int i=0, j=numbers.size()-1;
        while(i<j){
            int sum = numbers[i] + numbers[j];
            if(sum==target){
                res.push_back(i+1);
                res.push_back(j+1);
                break;
            }else if(sum<target) i++;
            else j--;
        }
        return res;
    }
};
```



## [4. leetcode-15 三数之和](https://leetcode-cn.com/problems/3sum/) **

### 4.1 题目描述
给定一个包含 n 个整数的数组 nums，判断 nums 中是否存在三个元素 a，b，c ，使得 a + b + c = 0 ？找出所有满足条件且不重复的三元组。注意：答案中不可以包含重复的三元组。例如, 给定数组 nums = [-1, 0, 1, 2, -1, -4]，满足要求的三元组集合为：
[[-1, 0, 1],
[-1, -1, 2]]

### 4.2 解题思路
采用三指针法
- 先把数组排序好
- 先固定一个值，然后采用双指针，三个值的和为0则保存，如果大于0则右指针左移，如果小于0则左指针右移。

可以做个剪枝优化，有以下几种情况需要优化。
1. 遍历到正数直接break，因为数字已经是有序的了，如果第一个要固定的数是正的话，那之后的数字也必然是正的，无需考虑。
2. 其次，如果在前几个固定的数中已经使用到后面为正数的数了，我们也不需要把这些正数作为固定的数，因为这些数在之前的解使用过了。
3. 从第二个数起，如果和前面的数字相等，就跳过。我们不想把相同数字固定两次。

### 4.3 代码
```cpp
class Solution {
public:
    vector<vector<int>> threeSum(vector<int>& nums) {
        vector<vector<int>> res;
        int n=nums.size();
        if(n<3) return res;

        sort(nums.begin(), nums.end());
        for(int i=0;i<n-2;i++){
            int left=i+1;
            int right=n-1;
            if(nums[i]>0) return res;
            if(i>0 && nums[i-1]==nums[i]) continue;
            while(left<right){
                int sum = nums[i] + nums[left] + nums[right];
                if(sum<0) left++;
                else if(sum>0) right--;
                else{
                    res.push_back({nums[i], nums[left++], nums[right--]});
                    while(left < right && nums[left-1]==nums[left]) left++;
                    while(left < right && nums[right+1]==nums[right]) right--;
                }
            }
        }
        return res;
    }
};
```



## [5. leetcode-16 最近的三数之和 ](https://leetcode-cn.com/problems/3sum-closest)**

### 5.1 题目描述
给定一个包括 n 个整数的数组 nums 和 一个目标值 target。找出 nums 中的三个整数，使得它们的和与 target 最接近。返回这三个数的和。假定每组输入只存在唯一答案。例如，给定数组 nums = [-1，2，1，-4], 和 target = 1.与 target 最接近的三个数的和为 2. (-1 + 2 + 1 = 2).


### 5.2 解题思路
和上一题一样啊，采用三指针法
- 先把数组排序好，用res记录距离target最近的和

- 先固定一个值，然后采用双指针，三个值的和与target更近则更新res，如果sum>target则右指针左移，否则左指针右移。


### 5.3 代码
```cpp
class Solution {
public:
    int threeSumClosest(vector<int>& nums, int target) {
        int n=nums.size();
        if(n<3) return -1;
        sort(nums.begin(), nums.end());
        int res = nums[0] + nums[1] + nums[2];

        for(int i=0;i<n-2;i++){
            int left=i+1;
            int right=n-1;
            while(left<right){
                int sum = nums[i] + nums[left] + nums[right];
                if(abs(res-target)>abs(target-sum)) res = sum;
                if(sum<target) left++;
                else right--;
            }
        }
        return res;
    }
};
```



## [6. leetcode-923 三数之和的多种可能](https://leetcode-cn.com/problems/3sum-with-multiplicity) **

### 6.1 题目描述
给定一个整数数组 A，以及一个整数 target 作为目标值，返回满足 i < j < k 且 A[i] + A[j] + A[k] == target 的元组 i, j, k 的数量。

由于结果会非常大，请返回 结果除以 10^9 + 7 的余数。

输入：A = [1,1,2,2,3,3,4,4,5,5], target = 8
输出：20

解释：按值枚举（A[i]，A[j]，A[k]）：
(1, 2, 5) 出现 8 次；
(1, 3, 4) 出现 8 次；
(2, 2, 4) 出现 2 次；
(2, 3, 3) 出现 2 次。

提示：
3 <= A.length <= 3000
0 <= A[i] <= 100
0 <= target <= 300

### 6.2 解题思路
[参考](https://leetcode-cn.com/problems/two-sum/solution/golang-pai-lie-zu-he-by-resara/)
由于题目限制 0 <= A[i] <= 100， 可以比较容易的想到去遍历0到100的数，而不是遍历数组A

- 首先记录0到100的数组出现的次数

- 我们需要找到3个数相加等于target。我们可以通过数字的顺序i，j找到k。找到i，j，k之后就是简单乘法，如有数字相等，就用排列组合计算。

为什么可以用排列组合计算。我们可以考虑把A排序，比如 1 1 1 1 2 2 5 5。那么我们可以找到 1 2 5 三个数字。单个数字每个索引其实都是合法的，那么就是 4 * 2 * 2。 如果target = 3，那么应该是 1 1 1。这就是很显然的3个坑，4个数按顺序去填，c43。

### 6.3 代码
```cpp
class Solution {
public:
    int threeSumMulti(vector<int>& A, int target) {
        constexpr int kMaxN = 100;
        constexpr int kMod = 1e9 + 7;
        vector<long> c(kMaxN+1, 0);//数组分配空间
        for(int num:A) ++c[num];//计数
        long ans = 0;
        for(int i = 0; i <= target; ++i){
            for(int j = i; j <= target; ++j){
                const int k = target - i - j;
                if (k < 0 || k >= c.size() || k < j) continue;
                if(!c[i] || !c[j] || !c[k]) continue;

                if(i == j && j == k){
                    ans += c[i] * (c[i]-1)*(c[i]-2) / 6;
                }
                else if(i == j && j != k){
                    ans += c[i] * (c[i]-1) / 2 * c[k];
                }
                else if(i != j && j == k){
                    ans += c[j] * (c[j]-1) / 2 * c[i];
                }
                else{
                    ans += c[i] * c[j] * c[k];
                }
            }
        }
        return ans % kMod;
    }
};
```



## [7. leetcode-18 四数之和](https://leetcode-cn.com/problems/two-sum-ii-input-array-is-sorted/) **

### 7.1 题目描述
给定一个包含 n 个整数的数组 nums 和一个目标值 target，判断 nums 中是否存在四个元素 a，b，c 和 d ，使得 a + b + c + d 的值与 target 相等？找出所有满足条件且不重复的四元组。注意：答案中不可以包含重复的四元组。

给定数组 nums = [1, 0, -1, 0, -2, 2]，和 target = 0。
满足要求的四元组集合为：
[
  [-1,  0, 0, 1],
  [-2, -1, 1, 2],
  [-2,  0, 0, 2]
]


### 7.2 解题思路
和三数之和差不多的思路，先固定两个数字，然后采用双指针。
- 先把数组排序好

- 先固定一个值，然后采用双指针，四个值的和为0则保存，如果大于0则右指针左移，如果小于0则左指针右移。

- 注意：因为不能有重复的数字出现，因此固定第一个数字时，从第二个数起（i>0），如果和前面的数字相等，就跳过。我们不想把相同数字固定两次；固定第二个数字时，需要满足j-i>1。


### 7.3 代码
```cpp
class Solution {
public:
    vector<vector<int>> fourSum(vector<int>& nums, int target) {
        int n=nums.size();
        vector<vector<int>> res;
        if(n<4) return res;
        sort(nums.begin(), nums.end());

        for(int i=0;i<n-3;i++){
            if(i>0 && nums[i-1]==nums[i]) continue;
            for(int j=i+1;j<n-2;j++){
                int left = j+1;
                int right = n-1;
                if(j-i>1 && nums[j-1]==nums[j]) continue; // 注意 j - i > 1
                while(left<right){
                    int sum = nums[i] + nums[j] + nums[left] + nums[right];
                    if(sum<target) left++;
                    else if(sum>target) right--;
                    else{
                        res.push_back({nums[i], nums[j], nums[left++], nums[right--]});
                        while(left<right && nums[left-1]==nums[left]) left++;
                        while(left<right && nums[right+1]==nums[right]) right--;
                    }
                }
            }
        }
        return res;
    }
};
```



## [8. leetcode-454 四数相加 II ](https://leetcode-cn.com/problems/4sum-ii)**

### 8.1 题目描述
给定四个包含整数的数组列表 A , B , C , D ,计算有多少个元组 (i, j, k, l) ，使得 A[i] + B[j] + C[k] + D[l] = 0。为了使问题简单化，所有的 A, B, C, D 具有相同的长度 N，且 0 ≤ N ≤ 500 。所有整数的范围在 -228 到 228 - 1 之间，最终结果不会超过 231 - 1 。

输入:
A = [ 1, 2]
B = [-2,-1]
C = [-1, 2]
D = [ 0, 2]
输出:2

解释:
两个元组如下:

1. (0, 0, 0, 1) -> A[0] + B[0] + C[0] + D[1] = 1 + (-2) + (-1) + 2 = 0

2. (1, 1, 0, 0) -> A[1] + B[1] + C[0] + D[0] = 2 + (-1) + (-1) + 0 = 0



### 8.2 解题思路
- 建立一个hashmap,记录AB数组的组合和以及出现的次数

- 计算CD数组的组合和，在hashmap中查找相反数

### 8.3 代码
```cpp
class Solution {
public:
    int fourSumCount(vector<int>& A, vector<int>& B, vector<int>& C, vector<int>& D) {
        int ans = 0;
        unordered_map<int,int> hashmap;
        for(auto a : A){
            for(auto b : B){
                int sum = a + b;
                hashmap[sum] ++;
            }
        }
        for(auto c : C){
            for(auto d : D){
                int need = -(c + d);
                if(hashmap.count(need))  
                     ans = ans + hashmap[need];
            }
        }
        return ans;
    }
};
```