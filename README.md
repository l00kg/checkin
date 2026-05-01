# checkin

一个可扩展的多站点签到项目，使用 `uv` 管理。

## 特点
- 支持多个站点适配器
- NodeSeek 站点已内置
- V2EX 站点支持用 `A2` + 对应浏览器的 `user_agent` 领取每日登录奖励
- 直接把 cookie 写进配置文件，方便下次复用（NodeSeek 必须用移动端 `user_agent`；V2EX 的 `user_agent` 必须和 cookie 对应的浏览器环境一致）
- 预留以后新增其他站点签到的扩展点

## 安装

```bash
cd /root/checkin
uv sync
```

## 配置

复制 `checkin.example.toml` 为 `checkin.toml`，然后把 cookie 直接写进文件。

示例：

```toml
[settings]
headless = true
channel = "chrome"

[[sites]]
name = "nodeseek"
type = "nodeseek"
url = "https://www.nodeseek.com/board"
# NodeSeek 必须使用移动端 UA
user_agent = "YOUR_NODESEEK_MOBILE_USER_AGENT"
cookies = { session = "YOUR_NODESEEK_SESSION", smac = "YOUR_NODESEEK_SMAC" }

[[sites]]
name = "v2ex"
type = "v2ex"
url = "https://www.v2ex.com/"
# V2EX 的 user_agent 必须和 A2 cookie 对应的浏览器环境一致
user_agent = "YOUR_V2EX_USER_AGENT"
cookies = { A2 = "YOUR_V2EX_A2" }
```

## 运行

签到 NodeSeek：

```bash
uv run checkin checkin nodeseek --config checkin.toml
```

签到 V2EX：

```bash
uv run checkin checkin v2ex --config checkin.toml
```

签到所有站点：

```bash
uv run checkin checkin --all --config checkin.toml
```

输出会显示本次签到是否成功，以及返回的提示信息。
