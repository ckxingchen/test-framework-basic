# Test Framework Basic

**使用 YAML 编写 Web 与 HTTP 自动化测试。**

Test Framework Basic 是一个关键字驱动的自动化测试框架，AI时代的首选框架, 提供 **10 类、45 个基础关键字**。通过基础动作、业务流程和测试用例分层组织脚本，支持 Excel 数据驱动、前后置处理、结果断言与测试报告。

适合搭建接口回归、Web 冒烟测试，以及学习和实践关键字驱动测试。环境要求：**Python 3.12**；使用 Web 自动化时需准备对应浏览器。

[快速开始](#quick-start) · [项目结构](#structure) · [编写脚本](#writing) · [命令行参数](#cli) · [报告与日志](#reports) · [进阶版框架](#advanced)

## 功能概览

| 功能 | 说明 |
|---|---|
| Web 自动化 | 页面访问、元素点击与输入、文本及属性读取、iframe、上传下载、截图和基础断言 |
| HTTP 自动化 | 通用请求、Session/Cookie、表单、JSON、文件上传和响应数据保存 |
| 业务封装 | 使用 Business YAML 组合可复用的登录、查询等功能 |
| 测试断言 | 相等、不等、字符串比较、包含、大小、长度与正则检查 |
| 数据处理 | 字符串、列表、字典、JSON、文件、时间与变量 |
| Excel 数据驱动 | 一份用例使用多行数据执行，通过列名引用输入和预期结果 |
| 前后置处理 | 测试集、测试用例两个级别的初始化与清理 |
| Python 辅助函数 | 在项目函数库中补充数据处理等辅助能力 |
| 测试报告 | HTML、Allure、Web 失败录像与 Trace，以及 JSON 格式测试结果 |
| 命令行执行 | 创建项目、生成关键字模板、运行整个项目或指定用例 |

框架采用串行执行，关键字名称、参数、默认值与使用限制见[自动化脚本编写指南](docs/自动化脚本编写指南.md)。

<a id="quick-start"></a>
## 快速开始

### 1. 安装运行环境

在框架根目录执行，以下命令以 Windows PowerShell 为例：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

仅运行 HTTP 与通用数据处理用例时，无需安装浏览器。使用 Web 自动化时，默认配置选择 Chrome；首次使用可按需安装：

```powershell
python -m playwright install chrome
python -m playwright install ffmpeg
```

已有 Chrome 时可以直接使用 `browser = chrome`。FFmpeg 用于录像；Firefox、WebKit 等浏览器按实际配置安装。默认 HTML 报告不需要 Allure CLI；生成 Allure 报告时需额外准备 Allure CLI 及其运行环境。

### 2. 加载关键字并创建项目

```powershell
# 查看命令帮助
python runmain/cli.py -help

# 生成45个基础关键字的YAML模板
python runmain/cli.py -l

# 创建自己的测试项目，同名项目不会被覆盖
python runmain/cli.py -c my_project
```

`action/` 是自动生成的关键字参考模板，执行 `-l` 时会重建。业务流程和测试用例应维护在自己的 `testsuits/<项目名>/` 中。

### 3. 编写第一个用例

新建 `testsuits/my_project/testcase/01入门/01字符串拼接.yaml`：

```yaml
info:
- desc: 字符串拼接测试
  params:
    id: basic-001
    title: 验证标题拼接结果
config: []
step:
- action: StrAction
  method: str_join
  desc: 拼接标题
  params:
    str_var1: "自动化-"
    str_var2: "001"
    result: actual_title
- action: CheckAction
  method: equal
  desc: 验证拼接结果
  params:
    real_value: ${actual_title}
    expect_value: "自动化-001"
```

执行下面的命令即可运行。这个例子只做数据处理，选择 HTTP 运行类型后无需访问外部服务或启动浏览器：

```powershell
python runmain/cli.py -r my_project "01入门/01字符串拼接.yaml" --auto_type http --report_type html
```

执行完成后，在 `testsuits/my_project/report/html/auto_reports.html` 查看报告。显式传入的运行配置会写回当前项目 INI。

<a id="structure"></a>
## 项目结构

```text
<框架根目录>/
├─ core/                         # YAML解析、执行、收集、日志与报告
├─ keywords/                     # 基础关键字实现
│  ├─ web/                       # Web页面与元素操作
│  ├─ http/                      # HTTP请求与会话
│  ├─ check/                     # 通用断言
│  └─ handler/                   # 通用数据处理
├─ runmain/cli.py                # 命令行入口
├─ static/template/              # 用例、业务、项目及报告模板
├─ action/                       # -l生成的关键字模板
├─ testsuits/
│  └─ <项目名>/
│     ├─ config/配置文件.ini
│     ├─ business/               # 可复用业务流程
│     ├─ testcase/
│     │  ├─ <测试集>/*.yaml
│     │  └─ casedata/
│     │     ├─ datadriver/        # Excel数据
│     │     ├─ file/              # 测试附件
│     │     └─ lib/               # Python辅助函数
│     ├─ log/                    # 运行日志
│     └─ report/                 # 报告与失败取证
├─ docs/                         # 使用文档
├─ tests/                        # 框架回归测试
├─ requirements.txt
└─ LICENSE
```

所有路径均相对于框架根目录。测试 YAML 放在 `testcase/` 的测试集子目录中，不直接散放在 `testcase/` 根目录。

<a id="writing"></a>
## 编写脚本

### Action → Business → TestCase

| 层级 | 负责内容 | 示例 |
|---|---|---|
| Action | 单个基础操作 | 输入文本、发送请求、提取JSON、比较结果 |
| Business | 一个可复用的业务功能 | 登录、查询、提交表单 |
| TestCase | 场景编排、数据与预期检查 | 调用登录业务，然后验证页面标题 |

**功能模块优先封装业务关键字。** 先在 `business/` 下组织功能步骤，再由 TestCase 传入数据并调用。业务 YAML 当前不支持嵌套调用其他 Business。

### 变量与返回值

- `${变量名}` 引用前面步骤保存的局部变量。
- 有返回值的基础关键字使用 `params.result` 指定变量名。
- HTTP 请求使用 `result_code/result_json/result_text/result_content` 分别保存状态码、JSON、文本与二进制内容。
- `DataDriver.列名` 引用当前 Excel 数据行的字段。

HTTP 状态码以字符串保存。响应不是 JSON 时，不启用 `result_json`。用例结束后会清理局部变量和对应 Page/Session，测试用例应独立准备自己的运行状态。

### 数据驱动与前后置

Excel 放在项目 `testcase/casedata/datadriver/` 下，第一行是表头。用例通过 `config` 中的 `parametrize` 策略指定文件与工作表。

在测试集目录中，可按需添加以下文件，内容使用 `step` 列表：

| 文件 | 执行时机 |
|---|---|
| `测试集前置.yml` | 当前测试集开始前 |
| `测试集后置.yml` | 当前测试集结束后 |
| `测试用例前置.yml` | 每个用例或数据驱动行执行前 |
| `测试用例后置.yml` | 每个用例或数据驱动行执行后 |

完整的 YAML 结构、Business 参数路径、数据转换规则及全部关键字参数，见[自动化脚本编写指南](docs/自动化脚本编写指南.md)。

## 示例项目

项目提供 Web 和 HTTP 两套登录示例：

| 项目 | 类型 | 用例 | 数据文件 |
|---|---|---|---|
| `01gjxt_web` | Web | `01登录/01用户登录测试.yaml` | `登录数据驱动.xlsx` |
| `02gjxt_http` | HTTP | `01登录/01用户登录测试.yaml` | `登录数据驱动.xlsx` |

两个示例均通过 `business/01登录/稿件系统登录.yaml` 封装登录，通过 Excel 的 `用户名/密码/预期结果` 三列组织数据；HTTP 示例还提供四类前后置文件。

示例面向稿件系统，仓库不附带被测网站。运行前，修改对应项目的 `config/配置文件.ini`，将 `test_url` 指向自己的测试环境，并填写专用测试账号及预期标题。其他系统应按实际页面或接口调整业务步骤。

```powershell
# 执行整个示例项目
python runmain/cli.py -r 01gjxt_web
python runmain/cli.py -r 02gjxt_http

# 执行指定测试集
python runmain/cli.py -r 01gjxt_web "01登录"

# 执行单个用例
python runmain/cli.py -r 02gjxt_http "01登录/01用户登录测试.yaml"
```

<a id="cli"></a>
## 命令行参数

| 参数 | 用途 | 示例 |
|---|---|---|
| `-help` / `--help` | 查看帮助 | `python runmain/cli.py -help` |
| `-c` / `--create` | 创建项目 | `python runmain/cli.py -c my_project` |
| `-l` / `--load` | 加载关键字并生成模板 | `python runmain/cli.py -l` |
| `-r` / `--run` | 运行项目、测试集或用例 | `python runmain/cli.py -r 01gjxt_web "01登录"` |

省略用例路径时运行整个项目；路径相对于项目 `testcase/`。选择多个不同目录或文件时，用英文分号分隔，并将完整路径参数放在引号中。

运行时支持以下项目配置覆盖：

| 参数 | 可用值或含义 |
|---|---|
| `--auto_type` | `web`、`http` |
| `--report_type` | `html`、`allure` |
| `--test_url` | 被测环境地址 |
| `--log_level` | `DEBUG`、`INFO`、`WARNING`、`ERROR` |
| `--is_email` | 布尔开关，如 `yes`、`no` |

```powershell
python runmain/cli.py -r 02gjxt_http "01登录" --auto_type http --report_type html --log_level INFO --is_email no
```

覆盖参数只与 `-r` 一起使用，显式设置会写回当前项目 INI。邮件默认关闭，启用前需填写邮件配置。

<a id="reports"></a>
## 报告与日志

| 内容 | 项目内位置 |
|---|---|
| 运行日志 | `log/` |
| HTML报告 | `report/html/auto_reports.html` |
| Allure报告 | `report/allure/report/` |
| 结构化用例结果 | `report/case_results.json` |
| HTML失败产物 | `report/html/artifacts/` |
| Allure失败产物 | `report/allure/artifacts/` |

Web 录像和 Trace 分别通过 `[WEB自动化配置]` 的 `record_video/record_trace` 控制。页面截图可使用 `WebAction.screenshot` 指定保存路径。

## 开发验证

```powershell
python -m pytest -o addopts= tests --basetemp=.tmp/tests -q
```

回归测试使用本机 HTTP 服务和无头 Chrome，覆盖 CLI、登录示例、业务参数化、会话隔离、前后置、结果导出与失败取证。测试服务自动启动，无需部署稿件系统；Web 回归需要 Chrome 和 FFmpeg。

`-o addopts=` 用于避免将 YAML 执行专用 hooks 加载到外层 Python 回归测试。

## License

本项目采用 [Apache License 2.0](LICENSE)，使用[官方标准许可文本](https://www.apache.org/licenses/LICENSE-2.0.txt)，不添加定制条款。第三方依赖遵循各自的许可协议。

<a id="advanced"></a>
## 进阶版框架

当测试需求扩展到桌面应用、多进程执行、数据库或自定义关键字插件时，可了解 [Test Framework KW](https://github.com/ckxingchen/test-framework-kw)。

| 进阶能力 | 功能介绍 |
|---|---|
| 更完整的Web关键字 | 多标签页、浏览器原生弹窗、JavaScript执行、更多等待、交互与断言 |
| 客户端自动化 | 鼠标键盘、图片定位、相对位置操作和中文输入 |
| 多进程执行 | Web/HTTP并发、测试集目录分组、Worker运行及结果汇总；客户端串行运行 |
| 外部关键字插件 | 加载Python插件，新增Action或在签名兼容的前提下覆盖已有关键字 |
| 数据库关键字 | SQLite、MySQL、PostgreSQL查询与数据操作 |
| SSH与远程操作 | 远程Shell、SFTP上传下载、远程GUI程序操作 |
| Windows系统操作 | 本地命令、文件管理和进程启停 |
| OCR识别 | Windows环境下的图片与Base64图片文字识别 |
| 更多通用处理 | 补充字符串、列表、JSON及数据断言能力 |
| CLI程序打包 | Windows/Linux的CLI打包脚本及部署说明 |

访问[进阶版仓库](https://github.com/ckxingchen/test-framework-kw)，查看使用文档、配置要求和示例。客户端、OCR及系统操作的可用性取决于执行环境，按对应模块说明准备依赖。

### 进交流群WX: ckxc529
