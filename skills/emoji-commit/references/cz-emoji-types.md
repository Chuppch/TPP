# cz-emoji 完整类型参考

cz-emoji 中所有 70+ commit 类型。

## 目录
- [常用类型](#常用类型)
- [依赖管理](#依赖管理)
- [CI/CD 与构建](#cicd-与构建)
- [代码质量与重构](#代码质量与重构)
- [特定改进](#特定改进)
- [基础设施与 DevOps](#基础设施与-devops)
- [数据与数据库](#数据与数据库)
- [监控与分析](#监控与分析)
- [文档与注释](#文档与注释)
- [平台特定](#平台特定)
- [其他](#其他)

---

## 常用类型

| Emoji | Code | Type | 描述 |
|-------|------|------|------|
| ✨ | `:sparkles:` | feature | 引入新功能 |
| 🐛 | `:bug:` | fix | 修复 bug |
| ♻️ | `:recycle:` | refactoring | 重构代码 |
| 🎨 | `:art:` | style | 改进代码结构/格式 |
| 💄 | `:lipstick:` | ui | 更新 UI 和样式文件 |
| 📝 | `:memo:` | docs | 编写文档 |
| ⚡️ | `:zap:` | perf | 提升性能 |
| ✅ | `:white_check_mark:` | test | 添加测试 |
| 🔧 | `:wrench:` | config | 修改配置文件 |
| 🔒 | `:lock:` | security | 修复安全问题 |
| 🚑 | `:ambulance:` | quickfix | 紧急修复 |
| 🚀 | `:rocket:` | deploy | 部署相关 |
| 🔥 | `:fire:` | prune | 删除代码或文件 |
| 🚨 | `:rotating_light:` | lint | 移除 linter 警告 |
| 🚧 | `:construction:` | wip | 进行中的工作 |

## 依赖管理

| Emoji | Code | Type | 描述 |
|-------|------|------|------|
| ⬆️ | `:arrow_up:` | upgrade | 升级依赖 |
| ⬇️ | `:arrow_down:` | downgrade | 降级依赖 |
| 📌 | `:pushpin:` | pushpin | 固定依赖版本 |
| ➕ | `:heavy_plus_sign:` | dep-add | 添加依赖 |
| ➖ | `:heavy_minus_sign:` | dep-rm | 移除依赖 |
| 📦 | `:package:` | dep-up | 更新编译文件或包 |

## CI/CD 与构建

| Emoji | Code | Type | 描述 |
|-------|------|------|------|
| 👷 | `:construction_worker:` | ci | 添加 CI 构建系统 |
| 💚 | `:green_heart:` | fix-ci | 修复 CI 构建 |
| 🔖 | `:bookmark:` | release | 发布/版本标签 |

## 代码质量与重构

| Emoji | Code | Type | 描述 |
|-------|------|------|------|
| ⏪ | `:rewind:` | revert | 回滚变更 |
| 🔀 | `:twisted_rightwards_arrows:` | merge | 合并分支 |
| ✏️ | `:pencil2:` | typo | 修复拼写错误 |
| 🚚 | `:truck:` | mv | 移动或重命名文件 |
| 💥 | `:boom:` | breaking | 引入破坏性变更 |
| ⚰️ | `:coffin:` | coffin | 移除死代码 |
| 🗑️ | `:wastebasket:` | wastebasket | 废弃需要清理的代码 |

## 特定改进

| Emoji | Code | Type | 描述 |
|-------|------|------|------|
| 🌐 | `:globe_with_meridians:` | i18n | 国际化和本地化 |
| 💬 | `:speech_balloon:` | texts | 更新文本和字面量 |
| 🍱 | `:bento:` | assets | 添加或更新资源 |
| 💫 | `:dizzy:` | animation | 添加或更新动画和过渡效果 |
| ♿️ | `:wheelchair:` | access | 改进无障碍访问 |
| 🚸 | `:children_crossing:` | ux | 改进用户体验/可用性 |
| 📱 | `:iphone:` | iphone | 响应式设计相关 |
| 🔍 | `:mag:` | seo | 改进 SEO |
| 🏷️ | `:label:` | types | 添加或更新类型（Flow, TypeScript） |

## 基础设施与 DevOps

| Emoji | Code | Type | 描述 |
|-------|------|------|------|
| 🐳 | `:whale:` | docker | Docker 相关工作 |
| ☸️ | `:wheel_of_dharma:` | k8s | Kubernetes 相关工作 |
| 🧱 | `:bricks:` | bricks | 基础设施相关变更 |
| 🏗 | `:building_construction:` | arch | 架构变更 |

## 数据与数据库

| Emoji | Code | Type | 描述 |
|-------|------|------|------|
| 🗃 | `:card_file_box:` | db | 数据库相关变更 |
| 🌱 | `:seedling:` | seed | 添加或更新种子文件 |

## 监控与分析

| Emoji | Code | Type | 描述 |
|-------|------|------|------|
| 📈 | `:chart_with_upwards_trend:` | analytics | 添加分析或追踪代码 |
| 🔊 | `:loud_sound:` | log-add | 添加日志 |
| 🔇 | `:mute:` | log-rm | 移除日志 |
| 🩺 | `:stethoscope:` | stethoscope | 添加或更新健康检查 |

## 文档与注释

| Emoji | Code | Type | 描述 |
|-------|------|------|------|
| 💡 | `:bulb:` | docs-code | 源代码文档 |
| 📄 | `:page_facing_up:` | license | 添加或更新许可证 |

## 平台特定

| Emoji | Code | Type | 描述 |
|-------|------|------|------|
| 🍎 | `:apple:` | osx | 修复 macOS 相关问题 |
| 🐧 | `:penguin:` | linux | 修复 Linux 相关问题 |
| 🏁 | `:checkered_flag:` | windows | 修复 Windows 相关问题 |
| 🤖 | `:robot:` | android | 修复 Android 相关问题 |
| 🍏 | `:green_apple:` | ios | 修复 iOS 相关问题 |

## 其他

| Emoji | Code | Type | 描述 |
|-------|------|------|------|
| 🎉 | `:tada:` | init | 初始提交 |
| 👽 | `:alien:` | compat | 因外部 API 变更更新代码 |
| 👌 | `:ok_hand:` | review | 因代码审查更新代码 |
| 👥 | `:busts_in_silhouette:` | contrib-add | 添加贡献者 |
| 🙈 | `:see_no_evil:` | see-no-evil | 添加或更新 .gitignore 文件 |
| 📸 | `:camera_flash:` | camera-flash | 添加或更新快照 |
| ⚗ | `:alembic:` | experiment | 实验新事物 |
| 🚩 | `:triangular_flag_on_post:` | flags | 添加、更新或移除功能标志 |
| 🛂 | `:passport_control:` | passport-control | 授权、角色和权限相关代码 |
| 🩹 | `:adhesive_bandage:` | adhesive-bandage | 非关键问题的简单修复 |
| 🧐 | `:monocle_face:` | monocle-face | 数据探索/检查 |
| 🧪 | `:test_tube:` | test-tube | 添加失败的测试 |
| 👔 | `:necktie:` | necktie | 添加或更新业务逻辑 |
| 🧑‍💻 | `:technologist:` | technologist | 改进开发者体验 |
| 🤡 | `:clown_face:` | clown-face | Mock 相关 |
| 🥚 | `:egg:` | egg | 添加彩蛋 |
| 🍻 | `:beers:` | beer | 醉酒写代码 |
| 💩 | `:poop:` | poo | 写了需要改进的烂代码 |
