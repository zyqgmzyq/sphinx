# 回溯问题

## 一、概念

[参考文章](https://www.cnblogs.com/steven_oyj/archive/2010/05/22/1741376.html)
**回溯算法**实际上一个类似枚举的搜索尝试过程，主要是在搜索尝试过程中寻找问题的解，当发现已不满足求解条件时，就“回溯”返回，尝试别的路径。回溯法是一种选优搜索法，按选优条件向前搜索，以达到目标。但当探索到某一步时，发现原先选择并不优或达不到目标，就退回一步重新选择，这种走不通就退回再走的技术为回溯法，而满足回溯条件的某个状态的点称为“回溯点”。

许多复杂的，规模较大的问题都可以使用回溯法，有“通用解题方法”的美称。

## 二、基本思想

在包含问题的所有解的解空间树中，按照深度优先搜索的策略，从根结点出发深度探索解空间树。当探索到某一结点时，要先判断该结点是否包含问题的解，如果包含，就从该结点出发继续探索下去，如果该结点不包含问题的解，则逐层向其祖先结点回溯。（其实回溯法就是对隐式图的深度优先搜索算法）。

- 若用回溯法求问题的所有解时，要回溯到根，且根结点的所有可行的子树都要已被搜索遍才结束。

- 而若使用回溯法求任一个解时，只要搜索到问题的一个解就可以结束。

## 三、用回溯法解题的一般步骤：

1. 针对所给问题，确定问题的解空间：首先应明确定义问题的解空间，问题的解空间应至少包含问题的一个（最优）解。
2. 确定结点的扩展搜索规则
3. 以深度优先方式搜索解空间，并在搜索过程中用剪枝函数避免无效搜索。

## 四、算法模板

```cpp
/**
* dfs模板.
* @param[in] input 输入数据指针
* @param[out] path 当前路径，即中间结果
* @param[out] result 最终结果
* @param[inout] cur or gap 标记当前位置或距离目标的距离
*/
void dfs(type &input, type &path, type &result, int cur or gap) {
    if (数据非法) return 0; // 终止条件
    if (满足条件) {
        将path 放入result
    }
    if (可以剪枝) return;
    for(...) { // 执行所有可能的扩展动作
        执行动作，修改path
        dfs(input, path, result, cur + 1 or gap--, );
        恢复path //向前回溯
    }
}
```



## 五、检测一下是不是真的会了呢

### [1.leetcode401-二进制手表 ](https://leetcode-cn.com/problems/binary-watch) *

####  题目描述
二进制手表顶部有 4 个 LED 代表小时（0-11），底部的 6 个 LED 代表分钟（0-59）。每个 LED 代表一个 0 或 1，最低位在右侧。
例如，上面的二进制手表读取 “3:25”。给定一个非负整数 n 代表当前 LED 亮着的数量，返回所有可能的时间。

输入: n = 1
返回: ["1:00", "2:00", "4:00", "8:00", "0:01", "0:02", "0:04", "0:08", "0:16", "0:32"]

#### 回溯法
这个题目可以归于有多少 n个1的二进制组合。转换为字符串即可。 这里将 0 - 9，划分一下 0 - 3 是 小时， 6 - 9 是分钟计算。
- 结束条件: num==0且h,m合法

- 退出条件: h或m非法

  ```cpp
  class Solution {
      public:
      void readBinaryWatch(vector<string> &res, int h, int m, int num, int cur){
          if(num==0 && h>=0 && m>=0){
              string s = to_string(h) + (m<10 ? ":0" : ":") + to_string(m);
              res.push_back(s);
          }
          for(int i=cur;i<10;i++){
              if(i<=3){
                  h += pow(2, i);
                  if(h>11){
                      h -= pow(2, i);
                      continue;
                  }
              }else{
                  m += pow(2, i-4);
                  if(m>59) return;
              }
  
              readBinaryWatch(res, h, m, num-1, i+1);
              if(i<=3) h -= pow(2, i);
              else m -= pow(2, i-4);
          }
      }
      vector<string> readBinaryWatch(int num) {
          vector<string> res;
          if(num<0 || num>8) return res;
          readBinaryWatch(res, 0, 0, num, 0);
          return res;
      }
  };
  ```
  
  

#### bitset法


```cpp
class Solution {
    public:
    vector<string> readBinaryWatch(int num) {//bitset STL模板
        vector<string> times;
        for (int i = 0; i < 12; i++) {
            bitset<4> h(i);//4位的二进制数
            for (int j = 0; j < 60; j++) {
                bitset<6> m(j);//6位的二进制数
                if (h.count() + m.count() == num)//h.count()函数判断h中1的个数
                    times.push_back(to_string(i) + (j < 10? ":0": ":") + to_string(j));
            }
        }
        return times;
    }
};
```



### [2.leetcode39-组合总数 ](https://leetcode-cn.com/problems/combination-sum) **
####  题目描述
给定一个无重复元素的数组 candidates 和一个目标数 target ，找出 candidates 中所有可以使数字和为 target 的组合。candidates 中的数字可以无限制重复被选取。

说明：所有数字（包括 target）都是正整数。解集不能包含重复的组合。 


输入: candidates = [2,3,6,7], target = 7

所求解集为: [[7], [2,2,3]]

#### 回溯法
解空间是任意选取的任意个数字组成的数组.遍历数组中的值，如果nums[i] < target , 尝试把nums[i]作为一个加数，把目标值减去nums[i]，下一次递归从i+1开始遍历数组寻找下一个加数;如果target=0，说明找到了一组加数;否则把上一个加数从list中去掉.
- 结束条件: target==0
- 退出条件: target<0

  ```cpp
  class Solution {
      public:
      void dfs(vector<vector<int>> &res, vector<int> &temp, vector<int> candidates, int target, int index){
          if(target<0) return ;
          if(target==0){
              res.push_back(temp);
          }
          for(int i=index; i < candidates.size(); i++){
              target -= candidates[i];
              temp.push_back(candidates[i]);
              dfs(res, temp, candidates, target, i);
              target += candidates[i];
              temp.pop_back();
          }
      }
  
      vector<vector<int>> combinationSum(vector<int>& candidates, int target) {
          vector<vector<int>> res;
          vector<int> temp;
          dfs(res, temp, candidates, target, 0);
          return res;
      }
  };
  ```



### [3.leetcode40-组合总数 II](https://leetcode-cn.com/problems/combination-sum-ii) **

####  题目描述
给定一个数组 candidates 和一个目标数 target ，找出 candidates 中所有可以使数字和为 target 的组合。candidates 中的每个数字在每个组合中只能使用一次。说明：所有数字（包括目标数）都是正整数。解集不能包含重复的组合。 

输入: candidates = [10,1,2,7,6,1,5], target = 8,所求解集为:
[[1, 7],
  [1, 2, 5],
  [2, 6],
  [1, 1, 6]]

#### 回溯法
和上一题基本相同,唯一需要注意的是每个数字只许使用一次且不能有重复组合.可先对数组排序,保留深度方向上相同的数字（也就是多个重复数字时可用，比如[1,1,1],第一个‘1’使用过后，第二和第三个依然可以使用），剔除水平方向相同的（也就是同一层中相同的枝应该剪掉）。

- 结束条件: target==0
- 退出条件: target<0

#### 代码

```cpp
class Solution {
    public:
    void dfs(vector<vector<int>> &res, vector<int> &temp, vector<int> candidates, int target, int index){
        if(target<0) return;
        if(target==0){
            res.push_back(temp);
        }
        for(int i=index; i<candidates.size()&&candidates[i]<=target;i++){
            if(i>index&&candidates[i-1]==candidates[i]) continue;
            target -= candidates[i];
            temp.push_back(candidates[i]);
            dfs(res, temp, candidates, target, i+1);
            target += candidates[i];
            temp.pop_back();
        }
    }

    vector<vector<int>> combinationSum2(vector<int>& candidates, int target) {
        vector<vector<int>> res;
        vector<int> temp;

        if(candidates.size()==0) return res;
        sort(candidates.begin(), candidates.end());
        dfs(res, temp, candidates, target, 0);
        return res;
    }
};
```


### [4.leetcode46-全排列](https://leetcode-cn.com/problems/permutations) **

####  题目描述
给定一个没有重复数字的序列，返回其所有可能的全排列。

输入: [1,2,3]
输出:
[[1,2,3],
  [1,3,2],
  [2,1,3],
  [2,3,1],
  [3,1,2],
  [3,2,1]]

#### 回溯法

- 对现有序列 x 进行遍历，拿到每一个遍历值放在当前位上
- 将该遍历到的值抽离序列 x，生成一个新的序列 y
- 继续对序列 y 执行这一过程


#### 代码
```cpp
class Solution {
public:
    void dfs(vector<vector<int>> &res, vector<int> &nums, int left, int right){
        if(left==right){
            res.push_back(nums);
        }
        for(int i=left;i<=right;i++){
            swap(nums[i], nums[left]);
            dfs(res, nums, left+1, right);
            swap(nums[i], nums[left]);
        }
    }

    vector<vector<int>> permute(vector<int>& nums) {
        vector<vector<int>> res;
        dfs(res, nums, 0, nums.size()-1);
        return res;
    }
};
```



### [5.leetcode47-全排列II](https://leetcode-cn.com/problems/permutations-ii) **

####  题目描述
给定一个可包含重复数字的序列，返回所有不重复的全排列。

输入: [1,1,2]
输出:
[[1,1,2],
  [1,2,1],
  [2,1,1]]


#### 回溯法
[这篇写的很详细](https://www.cnblogs.com/grandyang/p/4359825.html)

#### 代码一

```cpp
class Solution {
    public:
    vector<vector<int>> permuteUnique(vector<int>& nums) {
        vector<vector<int>> res;
        sort(nums.begin(), nums.end());
        permute(nums, 0, res);
        return res;
    }
    void permute(vector<int> nums, int start, vector<vector<int>>& res) {
        if (start >= nums.size()) res.push_back(nums);
        for (int i = start; i < nums.size(); ++i) {
            if (i != start && nums[i] == nums[start]) continue;
            swap(nums[i], nums[start]);
            permute(nums, start + 1, res);
        }
    }
};
```

#### 代码二

```cpp
class Solution {
    public:
    vector<vector<int>> permuteUnique(vector<int>& nums) {
        for (int v : nums) um[v]++;
        vector<int> perm;
        helper(perm, nums.size());
        return ret;
    }

    void helper(vector<int> &perm, int num) {
        if (perm.size() == num) {
            ret.push_back(perm);
            return;
        }

        for (auto &it : um) {
            if (it.second > 0) {
                it.second--;
                perm.push_back(it.first);
                helper(perm, num);
                perm.pop_back();
                it.second++;
            }
        }
    }

    private:
    unordered_map<int, int> um;
    vector<vector<int>> ret;
};
```
#### 代码三
```cpp
class Solution {
public:
	vector<vector<int>> ans;

	void trackback(vector<int>& nums, int start) {
		if (start == nums.size()) {
			ans.push_back(nums);
			return;
		}
		for (int i = start; i < nums.size(); i++) {
    		sort(nums.begin() + start, nums.end());  
			if (i > start && nums[i] == nums[i - 1]) {
                continue;
            }
			swap(nums[i], nums[start]);
			trackback(nums, start + 1);
			swap(nums[i], nums[start]);
		}
	}

	vector<vector<int>> permuteUnique(vector<int>& nums) {
		trackback(nums, 0);
		return ans;
	}
};
```

### [6.leetcode78-子集](https://leetcode-cn.com/problems/subsets) **

####  题目描述
给定一组不含重复元素的整数数组 nums，返回该数组所有可能的子集（幂集）。说明：解集不能包含重复的子集。

输入: nums = [1,2,3]
输出:
[ [3],
  [1],
  [2],
  [1,2,3],
  [1,3],
  [2,3],
  [1,2],
  []]

#### 回溯法
添加一个数，递归，删除之前的数，下次循环。

```cpp
class Solution {
    public:
    void dfs(vector<vector<int>> &res, vector<int> &temp, vector<int> nums, int index){
        res.push_back(temp);
        for(int i=index; i<nums.size();i++){
            temp.push_back(nums[i]);
            dfs(res, temp, nums, i+1);
            temp.pop_back();
        }
    }

    vector<vector<int>> subsets(vector<int>& nums) {
        vector<vector<int>> res;
        vector<int> temp;
        dfs(res, temp, nums, 0);
        return res;
    }
};
```

### [7.leetcode51-N皇后](https://leetcode-cn.com/problems/n-queens) ***
####  题目描述
n 皇后问题研究的是如何将 n 个皇后放置在 n×n 的棋盘上，并且使皇后彼此之间不能相互攻击。给定一个整数 n，返回所有不同的 n 皇后问题的解决方案。每一种解法包含一个明确的 n 皇后问题的棋子放置方案，该方案中 'Q' 和 '.' 分别代表了皇后和空位。

输入: 4
输出: [
 [".Q..",  // 解法 1
  "...Q",
  "Q...",
  "..Q."],

 ["..Q.",  // 解法 2
  "Q...",
  "...Q",
  ".Q.."]]
解释: 4 皇后问题存在两个不同的解法。

#### 回溯法
用set记录列, 正对角,负对角是否已经摆放过皇后，如果是则跳过啊！

如何判断是否在对角上呢?
  - 正对角就是相加之和一样的
  - 负对角就是相减只差一样的

#### 代码

```cpp
class Solution {
    public:
    void dfs(int row, vector<vector<string>> &res, vector<string> &temp, 
             unordered_set<int> &cols, unordered_set<int> &hills, unordered_set<int> dales, int n){
        if(row==n){
            res.push_back(temp);
            return ;
        }
        for(int col=0;col<n;col++){
            if(cols.count(col)>0 || hills.count(col+row)>0 || dales.count(row-col)>0) continue;
            cols.insert(col);
            hills.insert(col+row);
            dales.insert(row-col);
            temp[row][col] = 'Q';
            dfs(row+1, res, temp, cols, hills, dales, n);
            cols.erase(col);
            hills.erase(col+row);
            dales.erase(row-col);
            temp[row][col] = '.';
        }
    }

    vector<vector<string>> solveNQueens(int n) {
        vector<vector<string>> res;
        vector<string> temp(n, string(n, '.'));
        unordered_set<int> cols;
        unordered_set<int> hills;
        unordered_set<int> dales;
        dfs(0, res, temp, cols, hills, dales, n);
        return res;
    }
};
```


### [8.leetcode52-N皇后II](https://leetcode-cn.com/problems/n-queens-ii) ***
####  题目描述
n 皇后问题研究的是如何将 n 个皇后放置在 n×n 的棋盘上，并且使皇后彼此之间不能相互攻击。给定一个整数 n，返回 n 皇后不同的解决方案的数量。

输入: 4         输出: 2
解释: 4 皇后问题存在如下两个不同的解法。
[[".Q..",  // 解法 1
  "...Q",
  "Q...",
  "..Q."],

 ["..Q.",  // 解法 2
  "Q...",
  "...Q",
  ".Q.."]]

#### 回溯法
和上一题一样，这里如果满足情况加1即可，比上题简单一些！
```cpp
class Solution {
    public:
    void dfs(unordered_set<int> &cols, unordered_set<int> &hills, unordered_set<int> &dales, int &res, int row, int n){
        if(row==n){
            res++;
            return ;
        }
        for(int i=0;i<n;i++){
            if(cols.count(i)>0 || hills.count(i+row)>0 || dales.count(row-i)>0) continue;
            cols.insert(i);
            hills.insert(i+row);
            dales.insert(row-i);
            dfs(cols, hills, dales, res, row+1, n);
            cols.erase(i);
            hills.erase(i+row);
            dales.erase(row-i);
        }
    }

    int totalNQueens(int n) {
        unordered_set<int> cols;
        unordered_set<int> hills;
        unordered_set<int> dales;
        int res=0;

        dfs(cols, hills, dales, res, 0, n);
        return res;
    }
};
```

### [9.leetcode17-电话号码的字母组合](https://leetcode-cn.com/problems/letter-combinations-of-a-phone-number) **

#### 题目描述

给定一个仅包含数字 2-9 的字符串，返回所有它能表示的字母组合。给出数字到字母的映射如下（与电话按键相同）。注意 1 不对应任何字母。

输入："23"
输出：["ad", "ae", "af", "bd", "be", "bf", "cd", "ce", "cf"].

#### 代码

```cpp
class Solution {
    map<char, string> hashmap={{'2', "abc"},{'3', "def"},{'4', "ghi"},{'5', "jkl"},{'6', "mno"},{'7', "pqrs"},{'8', "tuv"},{'9', "wxyz"}};
    public:
    void dfs(vector<string> &res, vector<string> strs, string &s, int n){
        if(n == strs.size()){
            res.push_back(s);
            return;
        }
        for(int i=0;i<strs[n].size();i++){
            s += strs[n][i];
            dfs(res, strs, s, n+1);
            s.pop_back();
        }
    }

    vector<string> letterCombinations(string digits) {
        vector<string> res;
        if(digits.size()==0) return res;
        vector<string> strs;
        for(char s:digits) strs.push_back(hashmap[s]);
        string s;
        dfs(res, strs, s, 0);
        return res;
    }
};
```

### [10.leetcode22-括号生成](https://leetcode-cn.com/problems/generate-parentheses) **

####  题目描述
给出 n 代表生成括号的对数，请你写出一个函数，使其能够生成所有可能的并且有效的括号组合。例如，给出 n = 3，生成结果为：
["((()))",
  "(()())",
  "(())()",
  "()(())",
  "()()()"]


#### 代码
```cpp
class Solution {
public:
    void dfs(vector<string> &res, string temp, int left, int right, int n){
        if(left<right||left>n) return ;
        if(right==n){
            res.push_back(temp);
            return ;
        }
        dfs(res, temp+"(", left+1, right, n);
        dfs(res, temp+")", left, right+1, n);
    }

    vector<string> generateParenthesis(int n) {
        vector<string> res;
        if(n==0) return res;
        string temp="";
        dfs(res, temp, 0, 0, n);
        return res;
    }
};
```

### [11.leetcode77-组合](https://leetcode-cn.com/problems/combinations/) **

####  题目描述
给定两个整数 n 和 k，返回 1 ... n 中所有可能的 k 个数的组合。

输入: n = 4, k = 2
输出:
[[2,4],
  [3,4],
  [2,3],
  [1,2],
  [1,3],
  [1,4],]

#### 代码
```cpp
class Solution {
public:
    void dfs(vector<vector<int>> &ret, vector<int> &temp, int n, int k, int index) {
        if (temp.size() + (n - index + 1) < k) {
            return;
        }

        if (temp.size() == k) {
            ret.push_back(temp);
            return;
        }

        for (int i = index; i <= n; i++) {
            temp.push_back(i);
            dfs(ret, temp, n, k, i + 1);
            temp.pop_back();
        }
    }

    vector<vector<int>> combine(int n, int k) {
        vector<vector<int>> ret;
        vector<int> temp;

        dfs(ret, temp, n, k, 1);

        return ret;
    }
};
```

### [12. leetcode-37 解数独](https://leetcode-cn.com/problems/sudoku-solver)  ***

#### 题目描述
编写一个程序，通过填充空格来解决数独问题。

一个数独的解法需遵循如下规则：

数字 1-9 在每一行只能出现一次。
数字 1-9 在每一列只能出现一次。
数字 1-9 在每一个以粗实线分隔的 3x3 宫内只能出现一次。
空白格用 '.' 表示。

#### 解题思路
[参考](https://leetcode-cn.com/problems/sudoku-solver/solution/37-jie-shu-du-hui-su-sou-suo-suan-fa-xiang-jie-by-/i)

#### 代码

```c++
class Solution {
public:
    void solveSudoku(vector<vector<char>> &board)
    {
        solvesudokuDFS(board, 0, 0);
    }

     bool solvesudokuDFS(vector<vector<char>> &board, int i, int j)
    {
        if (i == 9) {
            return true;
        }
        if (j >= 9) {
            return solvesudokuDFS(board, i + 1, 0);
        }
        if (board[i][j] == '.') {
            for (int k = 1; k <= 9; ++k) {
                board[i][j] = (char)k + '0';
                if (isvalid(board, i, j)) {
                    if (solvesudokuDFS(board, i, j + 1)) {
                        return true;
                    }
                }
                board[i][j] = '.';
            }
        } else {
            return solvesudokuDFS(board, i, j + 1);
        }
        return false;
    }

    bool isvalid (vector<vector<char> >&board, int i, int j)
    {
        for (int col = 0; col < 9; ++col) {
            if ((col != j) && (board[i][j] == board[i][col])) {
                return false;
            }
        }
        for (int row = 0; row < 9; ++row) {
            if ((row != i) && (board[i][j] == board[row][j])) {
                return false;
            }
        }
        for (int l = i / 3 * 3; l < i / 3 * 3 + 3; ++l) {
            for (int m = j / 3 * 3; m < j / 3 * 3 + 3; ++m) {
                if ((l != i) && (m != j) && (board[i][j] == board[l][m])) {
                    return false;
                }
            }
        }
        return true;
    }
};
```
