# 二分查找

## [1. leetcode-35 搜索插入位置](https://leetcode-cn.com/problems/search-insert-position/) *

### 1.1 题目描述

给定一个排序数组和一个目标值，在数组中找到目标值，并返回其索引。如果目标值不存在于数组中，返回它将会被按顺序插入的位置。你可以假设数组中无重复元素。

输入: [1,3,5,6], 5
输出: 2

### 1.2 解题思路

二分查找，注意边界即可。

### 1.3 代码

```cpp
class Solution {
public:
    int searchInsert(vector<int>& nums, int target) {
        int left=0;
        int right=nums.size()-1;
        if(target<nums[0]) return 0;
        if(target>nums[right]) return right+1;
        while(left<=right){
            int mid = left + (right - left) / 2;
            if(nums[mid]==target) return mid;
            else if(nums[mid]>target) right = mid - 1;
            else left = mid + 1;
        }
        return left;
    }
};
```



## [2. leetcode-33. 搜索旋转排序数组](https://leetcode-cn.com/problems/search-in-rotated-sorted-array/) **

### 2.1 题目描述

假设按照升序排序的数组在预先未知的某个点上进行了旋转。( 例如，数组 [0,1,2,4,5,6,7] 可能变为 [4,5,6,7,0,1,2] )。搜索一个给定的目标值，如果数组中存在这个目标值，则返回它的索引，否则返回 -1 。你可以假设数组中不存在重复的元素。你的算法时间复杂度必须是 O(log n) 级别。

输入: nums = [4,5,6,7,0,1,2], target = 0
输出: 4

### 2.2 解题思想

简要来说：

- nums[left] <= nums[mid]（left - mid不包含旋转）,如果nums[left] <= target <= nums[mid] 时 right向前规约，否则left向后规约
- nums[mid] < nums[left]（left - mid包含旋转），nums[mid] <= target <=  nums[right] 时 left 向后规约（target 在旋转位置到 mid 之间），否则right向前规约

### 2.3 代码

```cpp
class Solution {
public:
    int search(vector<int>& nums, int target) {
        int left = 0;
        int right = nums.size() - 1;

        while (left <= right) {
            int mid = left + (right - left) / 2;
            if (nums[mid] == target) {
                return mid;
            }
            if (nums[left] <= nums[mid]) {
                if ((nums[left] <= target) && (target < nums[mid])) {      // 注意这个等号
                    right = mid - 1;
                } else {
                    left = mid + 1;
                }
            } else {
                if ((nums[mid] < target) && (target <= nums[right])) {
                    left = mid + 1;
                } else {
                    right = mid - 1;
                }
            } 
        }

        return -1;
    }
};

```



## [3. leetcode34 在排序数组中查找元素的第一个和最后一个位置](https://leetcode-cn.com/problems/find-first-and-last-position-of-element-in-sorted-array/) **

### 3.1 题目描述

给定一个按照升序排列的整数数组 nums，和一个目标值 target。找出给定目标值在数组中的开始位置和结束位置。你的算法时间复杂度必须是 O(log n) 级别。如果数组中不存在目标值，返回 [-1, -1]。

输入: nums = [5,7,7,8,8,10], target = 8
输出: [3,4]

### 3.2 解题思想

二分查找，这篇写的很好

https://leetcode-cn.com/problems/find-first-and-last-position-of-element-in-sorted-array/solution/er-fen-cha-zhao-suan-fa-xi-jie-xiang-jie-by-labula/

### 3.3 代码

```cpp
class Solution {
public:
    vector<int> searchRange(vector<int>& nums, int target) {
        if (nums.size() == 0) {
            return {-1, -1};
        }
        vector<int> ans;
        int left = 0;
        int right = nums.size() - 1;
        while (left < right) {
            int mid = left + (right - left) / 2;
            if (nums[mid] < target) {
                left = mid + 1;
            } else {
                right = mid;
            }
        }
        ans.push_back(left);

        if (nums[left] != target) {
            return {-1,-1};
        }

        left = 0;
        right = nums.size() - 1;
        while (left <= right) {
            int mid = left + (right - left) / 2;
            if (nums[mid] <= target) {
                left = mid + 1;
            } else {
                right = mid - 1;
            }
        }
        ans.push_back(right);
        return ans;
    }
};
```



## [4. leetcode4 - 寻找两个有序数组的中位数 ](https://leetcode-cn.com/problems/median-of-two-sorted-arrays/) ***

### 4.1 题目描述

给定两个大小为 m 和 n 的有序数组 nums1 和 nums2。请你找出这两个有序数组的中位数，并且要求算法的时间复杂度为 O(log(m + n))。你可以假设 nums1 和 nums2 不会同时为空。

输入：nums1 = [1, 3]    nums2 = [2]

输出：则中位数是 2.0

### 4.2 解题思路

二分查找，这篇写的很好！ https://leetcode.com/problems/median-of-two-sorted-arrays/discuss/2471/Very-concise-O(log(min(MN)))-iterative-solution-with-detailed-explanation 



### 4.3 代码

```cpp
class Solution {
public:
    double findMedianSortedArrays(vector<int>& nums1, vector<int>& nums2) {
        int m = nums1.size();
        int n = nums2.size();
        if (m > n) {
            return findMedianSortedArrays(nums2, nums1);
        }
        int left = 0;
        int right = m;

        while (left <= right) {
            int cut1 = (left + right) / 2;
            int cut2 = (m + n) / 2 - cut1;

            int l1 = (cut1 == 0) ? INT_MIN : nums1[cut1 - 1];
            int r1 = (cut1 == m) ? INT_MAX : nums1[cut1];
            int l2 = (cut2 == 0) ? INT_MIN : nums2[cut2 - 1];
            int r2 = (cut2 == n) ? INT_MAX : nums2[cut2];

            if (l1 > r2) {
                right = cut1 - 1;
            } else if (r1 < l2) {
                left = cut1 + 1;
            } else {
                return (m + n) % 2 ? min(r1, r2) : (max(l1, l2) + min(r1, r2)) / 2.0;
            }
        }
        return 0.0;
    }
};
```

## [5. leetcode74 - 搜索二维矩阵](https://leetcode-cn.com/problems/search-a-2d-matrix/) **

### 5.1 题目描述

编写一个高效的算法来判断 m x n 矩阵中，是否存在一个目标值。该矩阵具有如下特性：

每行中的整数从左到右按升序排列。
每行的第一个整数大于前一行的最后一个整数。

输入：matrix = [[1,3,5,7],[10,11,16,20],[23,30,34,60]], target = 3
输出：true


### 5.2 解题思路

由于每一行有序且每行的第一个数大于前一行，所以可以resize成一维数组，然后再进行二分查找


### 5.3 代码

```cpp
class Solution {
public:
    bool searchMatrix(vector<vector<int>>& matrix, int target) {
        int m = matrix.size();
        int n = matrix[0].size();
        int low = 0;
        int high = m * n - 1;
        while (low <= high) {
            int mid = (high - low) / 2 + low;
            int x = matrix[mid / n][mid % n];
            if (x < target) {
                low = mid + 1;
            } else if (x > target) {
                high = mid - 1;
            } else {
                return true;
            }
        }
        return false;
    }
};
```

## [6.leetcode2448-使数组相等的最小开销](https://leetcode.cn/problems/minimum-cost-to-make-array-equal/) 

### 6.1 题目描述

给你两个下标从 0 开始的数组 nums 和 cost ，分别包含 n 个 正 整数。你可以执行下面操作 任意 次：

将 nums 中 任意 元素增加或者减小 1 。对第 i 个元素执行一次操作的开销是 cost[i] 。

请你返回使 nums 中所有元素 相等 的 最少 总开销。

输入：nums= [1,3,5,2], cost = [2,3,1,14]
输出：8
解释：我们可以执行以下操作使所有元素变为 2 ：

- 增加第 0 个元素 1 次，开销为 2 。
- 减小第 1 个元素 1 次，开销为 3 。
- 减小第 2 个元素 3 次，开销为 1 + 1 + 1 = 3 。
  总开销为 2 + 3 + 3 = 8 。
  这是最小开销。


### 6.2 解题思路

把nums中元素转换后取得最小开销的目标值为x，x的取值范围为 `[min(nums), max(nums)]` ，

且相对应的开销cost最大值一定为两端点 `max(cost(min(nums), max(nums)))`，开销值在x取值范围内呈现先减后增趋势，

即`cost(min) >= cost(min + 1) >= ... >= cost(x - 1) >= cost(x) <= cost(x + 1) <= ... <= cost(max)`，

x取min或max时呈现单增或单减，可以**二分查找对应的 x 和 x + 1 增减趋势变化点**

### 6.3 代码

```c
class Solution
{
public:
    long long minCost(vector<int> &nums, vector<int> &cost)
    {
        int n = nums.size();
        long long ret = 0;
        int left = *min_element(nums.begin(), nums.end());
        int right = *max_element(nums.begin(), nums.end());
        int mid;

        while (left <= right) {
            mid = left + (right - left) / 2;
            long long c = 0, cr = 0;

            for (int i = 0; i < n; i++) {
                c += (long long)abs(nums[i] - mid) * cost[i];
                cr += (long long)abs(nums[i] - (mid + 1)) * cost[i];
            }
            if (c < cr) {
                right = mid - 1;
            }
            else {
                left = mid + 1;
            }
        }

        for (int i = 0; i < n; i++) {
            ret += (long long)abs(nums[i] - left) * cost[i];
        }

        return ret;
    }
};
```

