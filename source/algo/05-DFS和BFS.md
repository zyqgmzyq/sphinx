# DFS和BFS

## 一、BFS

### 先进先出的数据结构：队列

在 FIFO 数据结构中，**将首先处理添加到队列中的第一个元素**。队列是典型的 FIFO 数据结构。插入（insert）操作也称作入队（enqueue），新元素始终被添加在队列的末尾。 删除（delete）操作也被称为出队（dequeue)。 你只能移除第一个元素。

### 广度优先搜索 BFS

使用 BFS 的两个主要方案：**遍历或找出最短路径**。通常，这发生在树或图中。BFS 也可以用于更抽象的场景中。在特定问题中执行 BFS 之前确定结点和边缘非常重要。通常，结点将是实际结点或是状态，而边缘将是实际边缘或可能的转换。

### 模板一

```c++
int BFS(Node root, Node target) {
    Queue<Node> queue;
    int step=0;
    add root to queue;
    
    while(queue is not empty){
        step ++;
        int size = queue.size();
        for(int i=0; i<size; i++){
            Node cur = the first node in queue;
            return setp if cur is the target;
            for(Node next:the neighbors of our){
                add next to queue;
            }
            remove the first node from queue;
        }
    }
    return -1;          // there is no path from root to target
}
```

### 模板二

```c++
int BFS(Node root, Node target) {
    Queue<Node> queue;  // store all nodes which are waiting to be processed
    Set<Node> used;     // store all the used nodes
    int step = 0;       // number of steps neeeded from root to current node
    // initialize
    add root to queue;
    add root to used;
    // BFS
    while (queue is not empty) {
        step = step + 1;
        // iterate the nodes which are already in the queue
        int size = queue.size();
        for (int i = 0; i < size; ++i) {
            Node cur = the first node in queue;
            return step if cur is target;
            for (Node next : the neighbors of cur) {
                if (next is not in used) {
                    add next to queue;
                    add next to used;
                }
            }
            remove the first node from queue;
        }
    }
    return -1;          // there is no path from root to target
}
```



## [1. leetcode-101 对称二叉树](https://leetcode-cn.com/problems/symmetric-tree/)   *

### 题目描述

给定一个二叉树，检查它是否是镜像对称的。例如，二叉树 `[1,2,2,3,4,4,3]` 是对称的。但是 `[1,2,2,null,3,null,3]` 则不是镜像对称的:



### 解题思路

- 引入一个队列，初始化时把根节点入队两次。每次提取两个结点并比较它们的值（队列中每两个连续的结点应该是相等的，而且它们的子树互为镜像）。
- 将两个结点的左右子结点按相反的顺序插入队列中。当队列为空时，或者我们检测到树不对称（即从队列中取出两个不相等的连续结点）时，该算法结束。



### 代码

```c++
/**
 * Definition for a binary tree node.
 * struct TreeNode {
 *     int val;
 *     TreeNode *left;
 *     TreeNode *right;
 *     TreeNode(int x) : val(x), left(NULL), right(NULL) {}
 * };
 */
class Solution {
public:
    bool check (TreeNode* p, TreeNode *q)
    {
        queue<TreeNode *> que;
        que.push(p);
        que.push(q);

        while (!que.empty()) {
            p = que.front();
            que.pop();
            q = que.front();
            que.pop();
            if (!p && !q) {
               continue;
            }
            if (!p || !q || p->val != q->val) {
                return false;
            }

            que.push(p->left);
            que.push(q->right);
            que.push(p->right);
            que.push(q->left);
        }
        return true;
    }

    bool isSymmetric(TreeNode* root) {
        return check(root, root);
    }
};
```



## [2. leetcode-102 二叉树的层序遍历](https://leetcode-cn.com/problems/binary-tree-level-order-traversal/)    **

### 题目描述

给你一个二叉树，请你返回其按 **层序遍历** 得到的节点值。 （即逐层地，从左到右访问所有节点）。

实例： 二叉树：`[3,9,20,null,null,15,7]`, 

返回其层次遍历结果：

```c++
  [[3],
  [9,20],
  [15,7]]
```



### 解题思路

广度优先搜索



### 代码

```c++
/**
 * Definition for a binary tree node.
 * struct TreeNode {
 *     int val;
 *     TreeNode *left;
 *     TreeNode *right;
 *     TreeNode(int x) : val(x), left(NULL), right(NULL) {}
 * };
 */
class Solution 
{
public:
    vector<vector<int>> levelOrder(TreeNode* root) 
    {
        vector<vector<int>> ret;
        queue<TreeNode *> que;
        que.push(root);
        if (root == nullptr) {
            return ret;
        }

        while (!que.empty()) {
            int length = que.size();
            vector<int> nums;
            for (int i = 0; i < length; i++) {
                TreeNode *p = que.front();
                if (p->left != nullptr) {
                    que.push(p->left);
                }
                if (p->right != nullptr) {
                    que.push(p->right);
                }
                nums.push_back(p->val);
                que.pop();
            }
            ret.push_back(nums);
        }
        return ret;
    }
};
```



## [3. leetcode-103 二叉树的锯齿形层次遍历](https://leetcode-cn.com/problems/binary-tree-zigzag-level-order-traversal/)    **

### 题目描述

给定一个二叉树，返回其节点值的锯齿形层次遍历。（即先从左往右，再从右往左进行下一层遍历，以此类推，层与层之间交替进行）。

示例：给定二叉树 [3,9,20,null,null,15,7],

返回锯齿形层次遍历如下：

```c++
  [[3],
  [20,9],
  [15,7]]
```



### 解题思路

和上一题类似，需要注意的是奇数行和偶数行应该遵循不同的遍历规则，因此需要用双端队列来实现。



### 代码

```c++
/**
 * Definition for a binary tree node.
 * struct TreeNode {
 *     int val;
 *     TreeNode *left;
 *     TreeNode *right;
 *     TreeNode(int x) : val(x), left(NULL), right(NULL) {}
 * };
 */
class Solution
{
public:
    vector<vector<int>> zigzagLevelOrder(TreeNode* root)
    {
        vector<vector<int>> ret;
        deque<TreeNode *> deq;
        deq.push_front(root);
        if (root == nullptr) {
            return ret;
        }
        int k = 1;

        while (!deq.empty()) {
            int length = deq.size();
            vector<int> nums;
            for (int i = 0; i < length; i++) {
                TreeNode *p;
                if (k % 2 != 0) {
                    p = deq.front();
                    deq.pop_front();
                    if (p->left != nullptr) {
                        deq.push_back(p->left);
                    }
                    if (p->right != nullptr) {
                        deq.push_back(p->right);
                    }
                } else {
                    p = deq.back();
                    deq.pop_back();
                    if (p->right != nullptr) {
                        deq.push_front(p->right);
                    }
                    if (p->left != nullptr) {
                        deq.push_front(p->left);
                    }
                }
                nums.push_back(p->val);
            }
            ret.push_back(nums);
            k++;
        }
        return ret;
    }
};
```



## [4. leetcode-127 单词接龙](https://leetcode-cn.com/problems/word-ladder/)    **

### 题目描述

给定两个单词（beginWord 和 endWord）和一个字典，找到从 beginWord 到 endWord 的最短转换序列的长度。转换需遵循如下规则：每次转换只能改变一个字母。 转换过程中的中间单词必须是字典中的单词。
说明:如果不存在这样的转换序列，返回 0。所有单词具有相同的长度。所有单词只由小写字母组成。字典中不存在重复的单词。你可以假设 beginWord 和 endWord 是非空的，且二者不相同。



输入: beginWord = "hit", endWord = "cog", wordList = ["hot","dot","dog","lot","log","cog"]

输出: 5  

解释: 一个最短转换序列是 "hit" -> "hot" -> "dot" -> "dog" -> "cog", 返回它的长度 5。



### 解题思路一

广度优先搜索求解

注意: 使用unordered_set<string> visited用来标记单词是否被访问过，如果已经被访问过，说明已经有对应路径存在，因此跳过访问



### 代码一

```c++
class Solution 
{
public:
	int ladderLength(string beginWord, string endWord, vector<string>& wordList) 
	{
		unordered_set<string> hashset(wordList.begin(), wordList.end());
		unordered_set<string> visited;
		int ret = 1;
		if (hashset.count(endWord) == 0) {
			return 0;
		}
		queue<string> que;
		que.push(beginWord);
		visited.insert(beginWord);
		
		while (!que.empty()) {
			int num = que.size();
			while (num--){
				string frontWord = que.front();
				que.pop();
				for (int i = 0; i < beginWord.size(); i++) {
					string word = frontWord;
					for (char ch = 'a'; ch <= 'z'; ch++){
						word[i] = ch;
						if (hashset.count(word) <= 0 || visited.count(word) > 0) continue;
						if (word == endWord) {
							return ret + 1;
						}
						que.push(word);
						visited.insert(word);
					} 
				}
			}
			ret++;
		}
		return 0;
	}
};
```



### 解题思路二

看看大佬们写的双向广度优先搜索，下次自己写肯定还是写不来。菜是原罪！！！



### 代码二

```c++
class Solution {
public:
	int ladderLength(string beginWord, string endWord, vector<string>& wordList) {
		unordered_set<string> hashset(wordList.begin(), wordList.end());
		if(hashset.count(endWord) == 0) {
			return 0;
		}
		unordered_set<string> fowward = {beginWord};
		unordered_set<string> backward = {endWord};
		int length = beginWord.size(); 
		int ret = 1;  

		while(fowward.size() && backward.size()){
			// 一种小的优化策略，每次都选小的set开始expand，并且把小的设为forward
			if(fowward.size() > backward.size())
				swap(fowward, backward);

			unordered_set<string> q;
			for (auto c: fowward){
				for(int i = 0; i < length; i++){
					char tmp = c[i];  // 记录一下，因为后面要变回来，类似回溯
					for(char character='a'; character <= 'z'; character++){ 
						c[i] = character;
						if(backward.count(c))  
							return ret + 1;
						if(!hashset.count(c))
							continue;  // 字典中不存在，continue
						q.insert(c);
						hashset.erase(c);
					}
					c[i] = tmp;
				}
			}
			swap(q, fowward);
			ret++;
		}
		return 0;
	}
};
```



## [5. leetcode-1162 地图分析](https://leetcode-cn.com/problems/as-far-from-land-as-possible/)            **

### 题目描述

你现在手里有一份大小为 N x N 的「地图」（网格） grid，上面的每个「区域」（单元格）都用 0 和 1 标记好了。其中 0 代表海洋，1 代表陆地，请你找出一个海洋区域，这个海洋区域到离它最近的陆地区域的距离是最大的。我们这里说的距离是「曼哈顿距离」（ Manhattan Distance）：(x0, y0) 和 (x1, y1) 这两个区域之间的距离是 |x0 - x1| + |y0 - y1| 。如果我们的地图上只有陆地或者海洋，请返回 -1。

 

```c++
输入：[[1,0,1],[0,0,0],[1,0,1]]
输出：2
解释：海洋区域 (1, 1) 和所有陆地区域之间的距离都达到最大，最大距离为 2。
```



### 解题思路一

对每一个海洋进行广度优先搜索，超时 34/35，蠢兮兮才会写出这样的代码。。。。。。



### 代码一

```c++
class Solution 
{
public:
	vector<int> dx = {-1, 1, 0, 0};
	vector<int> dy = {0, 0, -1, 1};
	static const int MAX_N = 105;
	int m, n;
	bool vis[MAX_N][MAX_N];

	bool isValid(int x, int y) 
	{
		if (x < 0 || x >= m || y < 0 || y >= n) {
			return false;
		} 
		return true;
	}

	int bfs(int x, int y, vector<vector<int>>& grid)
	{
		queue<vector<int>> que;
		memset(vis, 0, sizeof vis);
		que.push({x, y});
		vis[x][y] = true;
		int ret = 0;
		while (!que.empty()) {
			int num = que.size();
			while (num--)
			{
				vector<int> indexs = que.front();
				que.pop();
				for (int j = 0; j < 4; j++) {
					int index_x = indexs[0] + dx[j];
					int index_y = indexs[1] + dy[j];
					if (!isValid(index_x, index_y)) continue; 
					if (!vis[index_x][index_y]) {
						vis[index_x][index_y] = true;
						que.push({index_x, index_y});
						if (grid[index_x][index_y] == 1) {
							return ret + 1;
						}
					}
				}
			}
			ret++;
		}
		return -1;
	}

	int maxDistance(vector<vector<int>>& grid) 
	{
		int retVal = -1;
		m = grid.size();
		n = grid[0].size();
		for (int i = 0; i < m; i++) {
			for (int j = 0; j < n; j++) {
				if (grid[i][j] == 0) {
					retVal = max(retVal, bfs(i, j, grid));
				}
			}
		}
		return retVal;
	}
};
```





### 解题思路二

多源广度优先搜索，变换了一下思路，把陆地作为源点

- 先遍历一遍矩阵，把所有陆地先放进队列中
- 然后套模板二



### 代码二

```c++
class Solution 
{
public:
	vector<int> dx = {-1, 1, 0, 0};
	vector<int> dy = {0, 0, -1, 1};
	int m, n;
	queue<vector<int>> que;

	bool isValid(int x, int y) 
	{
		if (x < 0 || x >= m || y < 0 || y >= n) {
			return false;
		} 
		return true;
	}

	int maxDistance(vector<vector<int>>& grid) 
	{
		m = grid.size();
		n = grid[0].size();
		for (int i = 0; i < m; i++) {
			for (int j = 0; j < n; j++) {
				if (grid[i][j] == 1) {
					que.push({i, j});
				}
			}
		}
		if (que.empty() || que.size() == m * n) return -1;

		int retVal = -1; // 由于BFS的第一层遍历是从陆地开始，因此遍历完第一层之后 retVal 应该是0
		while (!que.empty()) {
			int num = que.size();
			while (num--)
			{
				vector<int> indexs = que.front();
				que.pop();
				for (int j = 0; j < 4; j++) {
					int index_x = indexs[0] + dx[j];
					int index_y = indexs[1] + dy[j];
					if (!isValid(index_x, index_y) || grid[index_x][index_y] != 0) {
						continue;
 					}
					grid[index_x][index_y] = 2;
					que.push({index_x, index_y});
				}
			}
			retVal++;
		}
		// 最终走了多少层才把海洋遍历完
		return retVal;
	}
};
```





## 二、DFS

### 后进先出的数据结构：栈

在 LIFO 数据结构中，**将首先处理添加到队列中的最新元素**。栈是一个 LIFO 数据结构。通常，插入操作在栈中被称作入栈 push ，总是在堆栈的末尾添加一个新元素。但是，删除操作，退栈 pop ，将始终删除队列中相对于它的最后一个元素。



### 深度优先搜索（DFS）

深度优先搜索（DFS）是用于在树/图中遍历/搜索的另一种重要算法。也可以在更抽象的场景中使用。正如树的遍历中所提到的，我们可以用 DFS 进行 前序遍历，中序遍历和后序遍历。在这三个遍历顺序中有一个共同的特性：**除非我们到达最深的结点，否则我们永远不会回溯**。这也是 DFS 和 BFS 之间最大的区别，BFS永远不会深入探索，除非它已经在当前层级访问了所有结点。

 

在大多数情况下，我们在能使用 BFS 时也可以使用 DFS。但是有一个重要的区别：遍历顺序。与 BFS 不同，更早访问的结点可能不是更靠近根结点的结点。因此，你在 DFS 中找到的第一条路径可能不是最短路径。



### 模板一

```c++
bool DFS(Node cur, Node target, Set<Node> visited){
    return true if cur if target;
    for(next : each neighbpr of cur){
        if(next is not in visited){
            add next to visited;
            return true if DFS(next, target, visited );
        }
    }
    return false;
}
```



### 模板二

```c++
bool DFS(Node cur, Node target){
    Set<Node> visited;
    Stack<Node> s;
    add root to s;
    while(s is not empty){
        Node cur = the top element in s;
        return true if cur is target;
        for(Node next:each neighbpr of cur){
            if(next is not in visited){
                add next to visited;
                add next to s;
            } 
        }
        remove cur from s;
    }

    return false;
}
```



## [1. leetcode-20 有效的括号](https://leetcode-cn.com/problems/valid-parentheses/) *

### 题目描述 
给定一个只包括 '('，')'，'{'，'}'，'['，']' 的字符串，判断字符串是否有效。有效字符串需满足：左括号必须用相同类型的右括号闭合。左括号必须以正确的顺序闭合。注意空字符串可被认为是有效字符串。

输入: "()[]{}"
输出: true



### 栈

- 采用栈，遇到左括号压栈
- 遇到右括号判断当前栈是否为空，为空返回false；不为空取栈顶元素，若与当前右括号不匹配返回false，否则继续循环；
- 遍历完所有字符之和判断栈是否为空，为空返回ture，否则返回false ；

### 代码
```c++
class Solution {
public:
    bool isValid(string s) {
        stack<char> tack;
        if(s.size()==0) return true;
        for(auto c:s){
            switch(c){
                case ')':
                    if(tack.empty())return false;
                    else if(tack.top()=='(')tack.pop();
                    else tack.push(c);
                    break;
                case '}':
                    if(tack.empty())return false;
                    else if(tack.top()=='{')tack.pop();
                    else tack.push(c);
                    break;
                case ']':
                    if(tack.empty())return false;
                    else if(tack.top()=='[')tack.pop();
                    else tack.push(c);
                    break;
                default:
                    tack.push(c);
                    break;
            }

        }

    return tack.empty() ? true : false;
    }
};
```



## [2. leetcode-22 括号生成](https://leetcode-cn.com/problems/generate-parentheses/) **

### 题目描述

数字 n 代表生成括号的对数，请你设计一个函数，用于能够生成所有可能的并且 有效的 括号组合。

 

输入：n = 3
输出：[
       "((()))",
       "(()())",
       "(())()",
       "()(())",
       "()()()"
     ]



### 深度优先搜索

```c++
class Solution {
public:
    void dfs(vector<string> &ret, string s, int left, int right, int n){
        if(right>left || left>n) return;
        if(right==n){
            ret.push_back(s);
            return ;
        }
        dfs(ret, s+"(", left+1, right, n);
        dfs(ret, s+")", left, right+1, n);
    }

    vector<string> generateParenthesis(int n) {
        vector<string> ret;
        if(n==0) return ret;
        string s="";
        dfs(ret, s, 0, 0, n);
        return ret;
    }
};
```



## [3.Leetcode-695 岛屿的最大面积](https://leetcode-cn.com/problems/max-area-of-island/) **

### 题目描述

给定一个包含了一些 0 和 1的非空二维数组 grid , 一个 岛屿 是由四个方向 (水平或垂直) 的 1 (代表土地) 构成的组合。你可以假设二维矩阵的四个边缘都被水包围着。找到给定的二维数组中最大的岛屿面积。(如果没有岛屿，则返回面积为0。)

[[0,0,1,0,0,0,0,1,0,0,0,0,0],
 [0,0,0,0,0,0,0,1,1,1,0,0,0],
 [0,1,1,0,1,0,0,0,0,0,0,0,0],
 [0,1,0,0,1,1,0,0,1,0,1,0,0],
 [0,1,0,0,1,1,0,0,1,1,1,0,0],
 [0,0,0,0,0,0,0,0,0,0,1,0,0],
 [0,0,0,0,0,0,0,1,1,1,0,0,0],
 [0,0,0,0,0,0,0,1,1,0,0,0,0]]

对于上面这个给定矩阵应返回 `6`。注意答案不应该是11，因为岛屿只能包含水平或垂直的四个方向的‘1’。

### 深度优先搜索

- 我们想知道网格中每个连通形状的面积，然后取最大值。

- 如果我们在一个土地上，以 4 个方向探索与之相连的每一个土地（以及与这些土地相连的土地），那么探索过的土地总数将是该连通形状的面积。

- 为了确保每个土地访问不超过一次，我们每次经过一块土地时，将这块土地的值置为 0。这样我们就不会多次访问同一土地。

```c++
class Solution {
    public:
    int dfs(vector<vector<int>>& grid, int x, int y){
        int m=grid.size();
        int n=grid[0].size();
        if(x<0||x>=m||y<0||y>=n||grid[x][y]==0) return 0;
        int sum=1;
        grid[x][y] = 2;
        sum += dfs(grid, x+1, y);
        sum += dfs(grid, x-1, y);
        sum += dfs(grid, x, y-1);
        sum += dfs(grid, x, y+1);
        return sum;
    }

    int maxAreaOfIsland(vector<vector<int>>& grid) {
        int ret=0;
        for(int i=0;i<grid.size();i++){
            for(int j=0;j<grid[0].size();j++){
                if(grid[i][j]==1) ret = max(ret, dfs(grid, i, j));
            }
        }
        return ret;
    }
};
```

