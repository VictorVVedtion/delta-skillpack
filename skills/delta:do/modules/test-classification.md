# 测试分类标准 v1.0

## 核心原则

**基于代码行为分类，而非文件名、目录名或命名约定**

---

## 分类决策树

```
          测试文件分析
               │
               ▼
    ┌────────────────────────┐
    │ 检查代码中是否存在：     │
    │ - mock.NewXxx()         │
    │ - mockgen 生成的接口    │
    │ - testify/mock          │
    │ - unittest.mock         │
    │ - jest.mock()           │
    └────────────────────────┘
               │
         ┌─────┴─────┐
         ▼           ▼
       存在         不存在
         │           │
         ▼           ▼
    ┌────────┐  ┌────────────────────┐
    │单元测试│  │ 检查是否启动服务：   │
    └────────┘  │ - http.ListenAndServe │
                │ - grpc.NewServer      │
                │ - app.Start()         │
                │ - server.listen()     │
                └────────────────────┘
                          │
                    ┌─────┴─────┐
                    ▼           ▼
                  不存在        存在
                    │           │
                    ▼           ▼
              ┌────────┐  ┌────────────────────┐
              │集成测试│  │ 检查是否通过公开接口： │
              └────────┘  │ - http.NewRequest     │
                          │ - grpc.Dial           │
                          │ - websocket.Dial      │
                          │ - fetch/axios         │
                          └────────────────────┘
                                    │
                              ┌─────┴─────┐
                              ▼           ▼
                            不存在        存在
                              │           │
                              ▼           ▼
                        ┌────────┐  ┌────────┐
                        │集成测试│  │E2E测试 │
                        └────────┘  └────────┘
```

---

## 测试类型定义

### 单元测试 (Unit Test)

**本质特征**：
- 测试单个函数/方法的隔离行为
- 使用 Mock/Stub 替代所有外部依赖
- 不启动任何服务或数据库
- 执行时间通常 < 100ms

**代码特征检测**：

```go
// Go 语言 - 单元测试标志
import "github.com/stretchr/testify/mock"
import "github.com/golang/mock/gomock"
mockCtrl := gomock.NewController(t)
mock.NewXxx()
```

```python
# Python - 单元测试标志
from unittest.mock import Mock, patch, MagicMock
@patch('module.function')
mock_object = Mock()
```

```typescript
// TypeScript/JavaScript - 单元测试标志
jest.mock('module')
jest.fn()
vi.mock('module')  // vitest
sinon.stub()
```

### 集成测试 (Integration Test)

**本质特征**：
- 测试多个模块的协作行为
- 可能使用内存数据库
- 可能启动部分服务（但非完整系统）
- 直接调用内部 API，而非通过公开接口

**代码特征检测**：

```go
// Go 语言 - 集成测试标志
db, _ := sql.Open("sqlite3", ":memory:")
store := badger.NewMemStore()
keeper := NewKeeper(db, codec)
keeper.PlaceOrder(ctx, order)  // 直接调用 Keeper，非通过 HTTP
```

```python
# Python - 集成测试标志
@pytest.fixture
def db():
    return create_engine("sqlite:///:memory:")

def test_integration(db):
    repo = UserRepository(db)
    repo.create(user)  # 直接调用 repository
```

```typescript
// TypeScript - 集成测试标志
const db = new InMemoryDatabase()
const service = new UserService(db)
await service.createUser(userData)  // 直接调用 service
```

### E2E 测试 (End-to-End Test)

**本质特征** - **必须同时满足以下所有条件**：

1. **启动完整服务/应用/节点**
2. **通过公开接口（HTTP/gRPC/WebSocket）交互**
3. **验证端到端数据流**
4. **使用真实或近似生产环境配置**

**代码特征检测**：

```go
// Go 语言 - E2E 测试标志（必须全部存在）

// 条件 1: 启动完整服务
node := app.NewTestApp(config)
node.Start()
defer node.Stop()

// 条件 2: 通过公开接口调用
client := http.Client{}
req, _ := http.NewRequest("POST", node.URL+"/api/v1/order", body)
resp, _ := client.Do(req)

// 条件 3: 验证端到端状态
var result OrderResponse
json.Unmarshal(resp.Body, &result)
assert.Equal(t, expected.OrderID, result.OrderID)

// 条件 4: 使用真实配置
config := LoadConfig("testnet.toml")
```

```typescript
// TypeScript - E2E 测试标志

// 条件 1: 启动完整服务
const app = await createApp(testConfig)
await app.listen(3000)

// 条件 2: 通过 HTTP 调用
const response = await fetch('http://localhost:3000/api/users', {
  method: 'POST',
  body: JSON.stringify(userData)
})

// 条件 3: 验证响应
const result = await response.json()
expect(result.id).toBeDefined()

// 条件 4: 真实配置
const testConfig = loadConfig('test.env')
```

---

## 反例警示

### 假 E2E（实际是单元测试）

```go
// 文件名: orderbook_e2e_test.go  ← 文件名包含 e2e
// 但实际代码:
func TestOrderbook_E2E(t *testing.T) {
    mockKeeper := mocks.NewMockKeeper(ctrl)  // ← 使用 Mock！
    mockKeeper.EXPECT().PlaceOrder(gomock.Any()).Return(nil)

    // 结论：这是单元测试，不是 E2E！
    // 证据：使用了 Mock，没有启动真实服务
}
```

### 假 E2E（实际是集成测试）

```go
// 目录: tests/e2e/  ← 目录名包含 e2e
// 但实际代码:
func TestIntegration(t *testing.T) {
    keeper := NewKeeper(memDB, codec)
    keeper.PlaceOrder(ctx, order)  // ← 直接调用 Keeper，未通过 HTTP

    // 结论：这是集成测试，不是 E2E！
    // 证据：直接调用内部 API，没有通过公开接口
}
```

### 假 E2E（实际是延迟测试/基准测试）

```go
// 文件名: e2e_latency/main.go  ← 文件名包含 e2e
// 但实际代码:
func main() {
    client := NewAPIClient(externalURL)
    for i := 0; i < 1000; i++ {
        start := time.Now()
        client.Call("endpoint")  // ← 调用外部 API
        latencies = append(latencies, time.Since(start))
    }
    // 计算延迟统计

    // 结论：这是延迟测试/基准测试，不是 E2E！
    // 证据：只测量延迟，不验证功能正确性
}
```

---

## 分类检查清单

对每个测试文件，按顺序检查：

### Step 1: 检查 Mock 使用

```
□ 是否导入 mock 相关库？
  - Go: testify/mock, gomock
  - Python: unittest.mock, pytest-mock
  - TS/JS: jest.mock, vitest mock, sinon

□ 是否创建了 mock 对象？
  - mock.NewXxx()
  - Mock(), MagicMock()
  - jest.fn()

如果存在 Mock → 分类为"单元测试"
```

### Step 2: 检查服务启动

```
□ 是否启动完整服务/应用？
  - app.Start(), server.listen()
  - http.ListenAndServe()
  - grpc.NewServer() + Serve()

□ 是否有服务关闭逻辑？
  - defer server.Close()
  - afterAll(() => app.close())

如果没有服务启动 → 分类为"集成测试"
```

### Step 3: 检查接口调用方式

```
□ 是否通过公开接口调用？
  - http.NewRequest() + client.Do()
  - fetch(), axios
  - grpc.Dial()
  - websocket.Dial()

□ 还是直接调用内部方法？
  - keeper.PlaceOrder()
  - service.createUser()
  - repository.save()

如果通过公开接口 → 分类为"E2E 测试"
如果直接调用内部 → 分类为"集成测试"
```

---

## 分类输出模板

对每个测试文件，必须输出以下格式：

```markdown
## 测试文件分类

**文件**: `{file_path}`

**分类**: {Unit / Integration / E2E}

**代码证据**:

1. `{file}:{line}` - `{code}` — {说明为什么支持此分类}
2. `{file}:{line}` - `{code}` — {说明}
3. `{file}:{line}` - `{code}` — {说明}

**排除其他分类的原因**:

- 不是 {其他类型} 因为：{具体原因，引用代码}

**置信度**: {高 / 中 / 低}

**不确定因素**: {如有，列出无法确定的方面}
```

### 输出示例

```markdown
## 测试文件分类

**文件**: `tests/e2e/orderbook_e2e_test.go`

**分类**: Unit（单元测试）

**代码证据**:

1. `tests/e2e/orderbook_e2e_test.go:15` - `mockKeeper := mocks.NewMockKeeper(ctrl)` — 创建 Mock 对象
2. `tests/e2e/orderbook_e2e_test.go:16` - `mockKeeper.EXPECT().PlaceOrder(...)` — 设置 Mock 期望
3. `tests/e2e/orderbook_e2e_test.go:20` - `service := NewOrderService(mockKeeper)` — 使用 Mock 注入

**排除其他分类的原因**:

- 不是 E2E 因为：使用了 Mock 对象替代真实依赖，没有启动真实服务
- 不是 Integration 因为：没有任何真实组件交互，完全隔离

**置信度**: 高

**不确定因素**: 无

---

⚠️ 注意：文件名和目录名包含 "e2e" 但实际代码行为是单元测试
```

---

## 常见误判场景

| 场景 | 表面信号 | 实际分类 | 判断依据 |
|------|----------|----------|----------|
| `tests/e2e/xxx_test.go` | 目录名 e2e | 可能是任何类型 | 检查实际代码 |
| `TestXxxE2E` | 函数名包含 E2E | 可能是任何类型 | 检查实际代码 |
| `e2e_latency_test.go` | 文件名包含 e2e | 可能是基准测试 | 检查测试目的 |
| 使用真实数据库 | 看起来真实 | 集成测试（如果直接调用） | 检查调用方式 |
| 使用 TestContainer | 看起来真实 | 集成测试（如果不通过 HTTP） | 检查调用方式 |

---

## 与其他模块的关系

| 模块 | 关系 |
|------|------|
| `grounding.md` | 分类必须提供 Grounding 格式的证据 |
| `cross-validation.md` | 分类结果可能需要交叉验证 |
| `review.md` | 审查阶段使用此标准判断测试覆盖 |

---

## 版本历史

| 版本 | 变更 |
|------|------|
| v1.0 | 初始版本，定义测试分类标准和决策树 |
