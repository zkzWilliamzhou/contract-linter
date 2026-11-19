# contract-linter 使用指南

## 安装

```bash
# 方式1: pip 安装
pip install contract-linter

# 方式2: 从源码安装
git clone https://github.com/contract-linter/contract-linter.git
cd contract-linter
pip install -e .
```

## 基本用法

### 检查单个文件
```bash
contract-linter check myfile.cpp
```

### CI 模式（遇到警告则退出）
```bash
contract-linter check --ci-mode myfile.cpp
```

### JSON 输出格式
```bash
contract-linter check --format json myfile.cpp
```

## 检查类型

### 1. 前置条件一致性
```cpp
// 输入
int transfer(Account& from, Account& to, int amount) 
    pre(amount > 0) 
    pre(from.balance >= amount);

// 输出
✓ pre(amount > 0) - 简单条件
⚠️  pre(from.balance >= amount) - 依赖外部状态
```

### 2. 后置条件可达性
```cpp
// 输入
int divide(int a, int b) 
    pre(b != 0) 
    post(r: r == a / b);  // 问题：无法在整除时满足

// 输出
✗ post(r: r == a / b) - 整除不保证后置条件
```

### 3. 契约复杂度
```cpp
// 输入
void process() pre(
    a > 0 && b < 10 && c == 5 && 
    d != 0 && e || f && g
);

// 输出
⚠️  复杂度: 12 层嵌套 超过阈值(5)
💡  建议: 提取子契约
```

## CI 集成

### GitHub Actions
```yaml
# .github/workflows/contract.yml
name: Contract Analysis
on: [push, pull_request]

jobs:
  contract-check:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
    - name: Install contract-linter
      run: pip install contract-linter
    - name: Check contracts
      run: |
        find . -name "*.cpp" -exec contract-linter check --ci-mode {} +
```

### GitLab CI
```yaml
# .gitlab-ci.yml
contract-analysis:
  stage: test
  image: python:3.11
  script:
    - pip install contract-linter
    - contract-linter check --ci-mode src/
```

### pre-commit Hook
```bash
# .git/hooks/pre-commit
#!/bin/bash
contract-linter check --ci-mode $(git diff --cached --name-only --diff-filter=ACMR | grep '\.cpp$') || exit 1
```

## 输出说明

| 级别 | 说明 |
|------|------|
| ERROR | 契约矛盾/逻辑错误 |
| WARNING | 潜在问题/复杂度 |
| INFO | 建议/最佳实践 |

## 规则配置

创建 `.contract-linter.yaml`：

```yaml
# 忽略特定文件
ignore:
  - '*_test.cpp'
  - 'third_party/'

# 复杂度阈值
max-complexity: 5

# 警告列表
warnings:
  - raw-pointer-usage
  - const-cast
  - delete-pattern

# 错误列表
errors:
  - contract-conflict
  - unreachable-code
```

## 与 clang-tidy 集成

```bash
# 生成JSON输出，供clang-tidy消费
contract-linter check --format json myfile.cpp > warnings.json
clang-tidy -p build -extra-arg="-imports=warnings.json"
```

## 高级用法

### 批量分析
```bash
# 整个项目
contract-linter check src/ tests/

# 按修改文件
git diff --name-only HEAD~1 | grep '\.cpp$' | xargs contract-linter check
```

### 生成报告
```bash
contract-linter report --format html -o report.html src/
```

### 契约覆盖率
```bash
# 显示函数/契约覆盖率
contract-linter coverage src/
```